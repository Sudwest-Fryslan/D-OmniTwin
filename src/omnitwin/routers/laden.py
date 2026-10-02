"""
Laad-API /api/laden/v1 (#205)
=============================
Implementatie van `docs/api/laden/openapi.yaml` (spec eerst; die spec is ook wat
`GET /api/laden/v1/openapi.json` serveert, niet de door FastAPI gegenereerde). De laadstraat
zelf staat in `omnitwin.laden`; deze router is de dunne HTTP-laag.

Rechten (Keycloak, `omnitwin.oidc`):
- registreren en wijzigen (POST/PUT/PATCH /datasets): realm-rol `beheerder`;
- leveren: `dataset:{datasetId}:laden` of `datasets:laden`;
- lezen van een dataset, zijn leveringen en versies: `beheerder`, `datasets:laden` of
  `dataset:{datasetId}:laden`. Een levering (`GET /leveringen/{id}`) mag daarnaast de client
  lezen die hem leverde; anders 404 (de client hoort niet te weten dat hij bestaat);
- `GET /datasets`: met token de datasets waarop de client rechten heeft; de catalogusweergave
  (`Accept: application/ld+json`) mag anoniem en toont dan alleen datasets met
  `dct:accessRights` PUBLIC;
- `/openapi.json` en `/profielen`: anoniem.

Elke response heeft `API-Version` (middleware in `registreer`), fouten zijn Problem Details.
"""

from __future__ import annotations

import asyncio
import base64
import copy as kopie
import datetime as dt
import functools
import json
import logging
import uuid
from pathlib import Path
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from omnitwin.config import instellingen
from omnitwin.laden import opslag, verwerker
from omnitwin.laden.catalogus import catalogus, is_publiek
from omnitwin.laden.db import transactie
from omnitwin.laden.lezen import kale_mediatype
from omnitwin.laden.problemen import HTTP_CODE, MEDIATYPE, Fout, Probleem, probleem
from omnitwin.laden.profielen import PROFIELEN, profiel
from omnitwin.laden.registratie import OPENAPI, laad_openapi, valideer_registratie
from omnitwin.oidc import Principal, principal_optioneel, vereis_rol

logger = logging.getLogger("omnitwin.laden.api")

PREFIX = "/api/laden/v1"
router = APIRouter(prefix=PREFIX, tags=["Laad-API"])

EINDSTATUS = ("gevalideerd", "gepubliceerd", "afgekeurd", "mislukt")
LOOPT = ("ontvangen", "bezig")
IDEMPOTENTIE_DAGEN = 7
RETRY_AFTER = 2
LEZEN = ("beheerder", "datasets:laden", "dataset:{dataset_id}:laden")
LEVEREN = ("dataset:{dataset_id}:laden", "datasets:laden")
LD_JSON = "application/ld+json"


# ── specificatie ─────────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def specificatie() -> dict:
    return laad_openapi(OPENAPI)


def api_versie() -> str:
    return str(specificatie()["info"]["version"])


# ── hulpfuncties ─────────────────────────────────────────────────────────────

def _iso(t) -> str | None:
    if t is None:
        return None
    if isinstance(t, dt.datetime):
        if t.tzinfo is None:
            t = t.replace(tzinfo=dt.timezone.utc)
        return t.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")
    return str(t)


def _link(href: str) -> dict:
    return {"href": href}


def levering_kort(r: dict) -> dict:
    return {"id": str(r["id"]), "datasetId": r["dataset_id"], "status": r["status"], "modus": r["modus"],
            "alleenValideren": r["alleen_valideren"], "versie": r["versie"], "ontvangenOp": _iso(r["ontvangen_op"]),
            "afgerondOp": _iso(r["klaar_op"])}


def levering_uit(r: dict, fouten: list[dict] | None = None) -> dict:
    uit = levering_kort(r)
    uit.update({"idempotencyKey": r["idempotency_key"], "sha256": r["sha256"], "mediatype": r["mediatype"],
                "grootte": r["grootte"]})
    if r.get("client_id"):
        uit["client"] = r["client_id"]
    if r["status"] not in LOOPT:
        uit["aantallen"] = r["aantallen"] or {}
    if fouten is not None:
        uit["fouten"] = fouten
        uit["foutenAfgekapt"] = r["fouten_aantal"] > len(fouten)
    links = {"self": _link(f"{PREFIX}/leveringen/{r['id']}"), "dataset": _link(f"{PREFIX}/datasets/{r['dataset_id']}")}
    if r["status"] == "gepubliceerd" and r["versie"]:
        links["bestand"] = _link(f"{PREFIX}/datasets/{r['dataset_id']}/versies/{r['versie']}/bestand")
    uit["_links"] = links
    return uit


def dataset_uit(r: dict, laatste: dict | None) -> dict:
    uit = {"id": r["id"]}
    if r.get("bron_id"):
        uit["bronId"] = r["bron_id"]
    uit.update({"beschrijving": r["beschrijving"], "laadprofiel": r["laadprofiel"], "actueleVersie": r["huidige_versie"],
                "aangemaaktOp": _iso(r["aangemaakt_op"]), "gewijzigdOp": _iso(r["gewijzigd_op"])})
    if laatste:
        uit["laatsteLevering"] = levering_kort(laatste)
    uit["_links"] = {"self": _link(f"{PREFIX}/datasets/{r['id']}"),
                     "leveringen": _link(f"{PREFIX}/datasets/{r['id']}/leveringen"),
                     "versies": _link(f"{PREFIX}/datasets/{r['id']}/versies"),
                     "profiel": _link(f"{PREFIX}/profielen/{r['profiel']}")}
    return uit


def _fout_uit(r: dict) -> dict:
    return Fout(r["code"], r["melding"], r.get("resource"), r.get("regel"), r.get("veld")).als_probleem()


def _pagina_links(pad: str, pagina: int, grootte: int, meer: bool, extra: dict | None = None) -> dict:
    q = {k: v for k, v in (extra or {}).items() if v is not None}

    def url(p):
        return f"{pad}?{urlencode({**q, 'pagina': p, 'paginaGrootte': grootte})}"
    links = {"self": _link(url(pagina))}
    if meer:
        links["next"] = _link(url(pagina + 1))
    if pagina > 1:
        links["prev"] = _link(url(pagina - 1))
    return links


def mag_lezen(p: Principal | None, dataset_id: str) -> bool:
    return bool(p) and bool(p.rollen & {"beheerder", "datasets:laden", f"dataset:{dataset_id}:laden"})


def _json_body(raw: bytes) -> object:
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise Probleem(400, "ongeldig-verzoek", "De body is geen geldige JSON (UTF-8).")


def _registratie_fouten(reg: dict) -> None:
    fouten = valideer_registratie(reg, specificatie())
    if fouten:
        raise Probleem(422, "registratie-ongeldig", f"De registratie voldoet niet aan DatasetRegistratie "
                       f"({len(fouten)} fouten).",
                       fouten=[{"type": "https://github.com/TLaan/D-OmniTwin/blob/main/docs/api/laden/README.md#"
                                        "schema-ongeldig", "code": "schema-ongeldig", "title": "Schema ongeldig",
                                "detail": f} for f in fouten[:100]])


# ── database (in de threadpool) ──────────────────────────────────────────────

def _haal_dataset(cur, dataset_id: str) -> dict | None:
    cur.execute("SELECT * FROM laden.datasets WHERE id = %s", (dataset_id,))
    return cur.fetchone()


def _laatste_levering(cur, dataset_id: str) -> dict | None:
    cur.execute("SELECT * FROM laden.leveringen WHERE dataset_id = %s ORDER BY ontvangen_op DESC LIMIT 1", (dataset_id,))
    return cur.fetchone()


def _dataset_of_404(cur, dataset_id: str) -> dict:
    ds = _haal_dataset(cur, dataset_id)
    if not ds:
        raise Probleem(404, "niet-gevonden", f"Dataset {dataset_id} bestaat niet.")
    return ds


def _db_dataset(dataset_id: str) -> dict:
    with transactie() as cur:
        ds = _dataset_of_404(cur, dataset_id)
        return dataset_uit(ds, _laatste_levering(cur, dataset_id))


def _db_registreer(reg: dict) -> dict:
    with transactie() as cur:
        if _haal_dataset(cur, reg["id"]):
            raise Probleem(409, "dataset-bestaat", f"Dataset {reg['id']} bestaat al; wijzig hem met PUT of PATCH.")
        cur.execute("""INSERT INTO laden.datasets (id, bron_id, beschrijving, laadprofiel, profiel)
                       VALUES (%s, %s, %s, %s, %s) RETURNING *""",
                    (reg["id"], reg.get("bronId"), json.dumps(reg["beschrijving"], ensure_ascii=False),
                     json.dumps(reg["laadprofiel"], ensure_ascii=False), reg["laadprofiel"]["profiel"]))
        return dataset_uit(cur.fetchone(), None)


def _profiel_vast(oud: dict, nieuw: dict) -> bool:
    lo, ln = oud["laadprofiel"] or {}, nieuw["laadprofiel"] or {}
    return lo.get("profiel") != ln.get("profiel") or (lo.get("sleutelvelden") or None) != (ln.get("sleutelvelden") or None)


def _db_vervang(dataset_id: str, reg: dict) -> dict:
    with transactie() as cur:
        ds = _dataset_of_404(cur, dataset_id)
        cur.execute("SELECT 1 FROM laden.versies WHERE dataset_id = %s LIMIT 1", (dataset_id,))
        if cur.fetchone() and _profiel_vast(ds, reg):
            raise Probleem(409, "profiel-vast", "Profiel en sleutelvelden liggen vast na de eerste publicatie; "
                           "registreer een nieuwe dataset.")
        cur.execute("""UPDATE laden.datasets SET bron_id = %s, beschrijving = %s, laadprofiel = %s, profiel = %s,
                              gewijzigd_op = now() WHERE id = %s RETURNING *""",
                    (reg.get("bronId"), json.dumps(reg["beschrijving"], ensure_ascii=False),
                     json.dumps(reg["laadprofiel"], ensure_ascii=False), reg["laadprofiel"]["profiel"], dataset_id))
        return dataset_uit(cur.fetchone(), _laatste_levering(cur, dataset_id))


def _db_huidige_registratie(dataset_id: str) -> dict:
    with transactie() as cur:
        ds = _dataset_of_404(cur, dataset_id)
    reg = {"id": ds["id"], "beschrijving": ds["beschrijving"], "laadprofiel": ds["laadprofiel"]}
    if ds.get("bron_id"):
        reg["bronId"] = ds["bron_id"]
    return reg


def merge_patch(doel, patch):
    """JSON Merge Patch (RFC 7396)."""
    if not isinstance(patch, dict):
        return kopie.deepcopy(patch)
    uit = kopie.deepcopy(doel) if isinstance(doel, dict) else {}
    for k, v in patch.items():
        if v is None:
            uit.pop(k, None)
        else:
            uit[k] = merge_patch(uit.get(k), v)
    return uit


# ── routes: specificatie en profielen ────────────────────────────────────────

@router.get("/openapi.json", include_in_schema=False)
def haal_specificatie():
    return JSONResponse(specificatie(), headers={"Access-Control-Allow-Origin": "*"})


@router.get("/profielen")
def lijst_profielen():
    return {"profielen": [profiel(c) for c in PROFIELEN]}


@router.get("/profielen/{profiel_id}")
def haal_profiel(profiel_id: str):
    if profiel_id not in PROFIELEN:
        raise Probleem(404, "niet-gevonden", f"Profiel {profiel_id} bestaat niet.")
    return profiel(profiel_id)


# ── routes: datasets ─────────────────────────────────────────────────────────

@router.get("/datasets")
def lijst_datasets(request: Request, profiel_: str | None = Query(None, alias="profiel"),
                   pagina: int = Query(1, ge=1), pagina_grootte: int = Query(20, ge=1, le=100, alias="paginaGrootte"),
                   principal: Principal | None = Depends(principal_optioneel)):
    ld = LD_JSON in request.headers.get("accept", "")
    if principal is None and not ld:
        raise Probleem(401, "niet-geauthenticeerd", "Bearer-token ontbreekt.", headers={"WWW-Authenticate": "Bearer"})
    if profiel_ is not None and profiel_ not in PROFIELEN:
        raise Probleem(400, "ongeldig-verzoek", f"Onbekend profiel; kies uit {', '.join(PROFIELEN)}.")
    with transactie() as cur:
        cur.execute("SELECT * FROM laden.datasets WHERE (%(p)s::text IS NULL OR profiel = %(p)s) ORDER BY id",
                    {"p": profiel_})
        alle = [dict(r) for r in cur.fetchall()]
        zichtbaar = [d for d in alle if mag_lezen(principal, d["id"]) or (ld and is_publiek(d["beschrijving"]))]
        if ld:
            basis = str(request.base_url).rstrip("/")
            return JSONResponse(catalogus(zichtbaar, basis), media_type=LD_JSON)
        start = (pagina - 1) * pagina_grootte
        deel = zichtbaar[start:start + pagina_grootte]
        uit = [dataset_uit(d, _laatste_levering(cur, d["id"])) for d in deel]
    return {"datasets": uit, "_links": _pagina_links(f"{PREFIX}/datasets", pagina, pagina_grootte,
                                                      start + pagina_grootte < len(zichtbaar), {"profiel": profiel_})}


@router.post("/datasets", status_code=201)
async def registreer_dataset(request: Request, principal: Principal = Depends(vereis_rol("beheerder"))):
    reg = _json_body(await request.body())
    if not isinstance(reg, dict):
        raise Probleem(400, "ongeldig-verzoek", "De body moet een JSON-object zijn (DatasetRegistratie).")
    _registratie_fouten(reg)
    uit = await run_in_threadpool(_db_registreer, reg)
    logger.info("Dataset %s geregistreerd door %s", reg["id"], principal.client_id or principal.onderwerp)
    return JSONResponse(uit, status_code=201, headers={"Location": f"{PREFIX}/datasets/{reg['id']}"})


@router.get("/datasets/{dataset_id}")
def haal_dataset(dataset_id: str, principal: Principal = Depends(vereis_rol(*LEZEN))):
    return _db_dataset(dataset_id)


@router.put("/datasets/{dataset_id}")
async def vervang_dataset(dataset_id: str, request: Request, principal: Principal = Depends(vereis_rol("beheerder"))):
    reg = _json_body(await request.body())
    if not isinstance(reg, dict):
        raise Probleem(400, "ongeldig-verzoek", "De body moet een JSON-object zijn (DatasetRegistratie).")
    if reg.get("id") != dataset_id:
        raise Probleem(400, "ongeldig-verzoek", "id in de body is niet gelijk aan de datasetId in het pad.")
    _registratie_fouten(reg)
    return await run_in_threadpool(_db_vervang, dataset_id, reg)


@router.patch("/datasets/{dataset_id}")
async def wijzig_dataset(dataset_id: str, request: Request, principal: Principal = Depends(vereis_rol("beheerder"))):
    if kale_mediatype(request.headers.get("content-type")) != "application/merge-patch+json":
        raise Probleem(415, "mediatype-past-niet", "PATCH verwacht application/merge-patch+json (RFC 7396).")
    patch = _json_body(await request.body())
    if not isinstance(patch, dict):
        raise Probleem(400, "ongeldig-verzoek", "De body moet een JSON-object zijn (JSON Merge Patch).")
    reg = merge_patch(await run_in_threadpool(_db_huidige_registratie, dataset_id), patch)
    if reg.get("id") != dataset_id:
        raise Probleem(400, "ongeldig-verzoek", "id kan niet gewijzigd worden.")
    _registratie_fouten(reg)
    return await run_in_threadpool(_db_vervang, dataset_id, reg)


# ── routes: leveringen ───────────────────────────────────────────────────────

def _bool(w: str | None, naam: str, standaard: bool = False) -> bool:
    if w is None:
        return standaard
    if w.lower() in ("true", "1"):
        return True
    if w.lower() in ("false", "0"):
        return False
    raise Probleem(400, "ongeldig-verzoek", f"{naam} moet true of false zijn.")


def _limiet(mediatype: str) -> int:
    m = instellingen().laden_max_bytes
    return max(m // 10, 1024 * 1024) if mediatype == "application/json" else m


def _digest_klopt(kop: str, sha256_hex: str) -> bool:
    for deel in kop.split(","):
        naam, _, waarde = deel.strip().partition("=")
        if naam.strip().lower() == "sha-256":
            try:
                return base64.b64decode(waarde.strip().strip(":")).hex() == sha256_hex
            except ValueError:
                return False
    return True  # geen sha-256 in de header: niets te controleren


def _db_nieuwe_levering(ds_id: str, ontvangen: opslag.Ontvangen, mediatype: str, bestandsnaam: str, sleutel: str | None,
                        alleen_valideren: bool, client_id: str | None, dcat: dict | None) -> tuple[dict, bool]:
    """(levering, nieuw). Idempotentie: zelfde sleutel + zelfde inhoud = bestaande levering."""
    with transactie() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext('laden:ontvangst:' || %s))", (ds_id,))
        if sleutel:
            cur.execute("""UPDATE laden.leveringen SET idempotency_key = NULL WHERE dataset_id = %s
                           AND idempotency_key = %s AND ontvangen_op < now() - make_interval(days => %s)""",
                        (ds_id, sleutel, IDEMPOTENTIE_DAGEN))
            cur.execute("SELECT * FROM laden.leveringen WHERE dataset_id = %s AND idempotency_key = %s", (ds_id, sleutel))
            bestaand = cur.fetchone()
            if bestaand:
                if bestaand["sha256"] != ontvangen.sha256:
                    raise Probleem(422, "idempotency-key-hergebruikt", "Deze Idempotency-Key is binnen 7 dagen al "
                                   "gebruikt voor een levering met andere inhoud.",
                                   levering=f"{PREFIX}/leveringen/{bestaand['id']}")
                if bestaand["status"] in LOOPT:
                    raise Probleem(409, "levering-loopt", "Een levering met deze Idempotency-Key is nog in behandeling.",
                                   headers={"Location": f"{PREFIX}/leveringen/{bestaand['id']}",
                                            "Retry-After": str(RETRY_AFTER)},
                                   levering=f"{PREFIX}/leveringen/{bestaand['id']}")
                return dict(bestaand), False
        lid = str(uuid.uuid4())
        opslag.bewaar(ontvangen, ds_id, lid, bestandsnaam)
        try:
            cur.execute("""INSERT INTO laden.leveringen (id, dataset_id, alleen_valideren, idempotency_key, sha256,
                               bestandsnaam, mediatype, grootte, dcat, client_id)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING *""",
                        (lid, ds_id, alleen_valideren, sleutel, ontvangen.sha256, bestandsnaam, mediatype,
                         ontvangen.grootte, json.dumps(dcat, ensure_ascii=False) if dcat else None, client_id))
            return dict(cur.fetchone()), True
        except BaseException:
            p = opslag.pad(ds_id, lid, bestandsnaam)
            p.chmod(0o600)
            p.unlink(missing_ok=True)
            raise


def _db_levering(lid: str) -> tuple[dict | None, list[dict]]:
    with transactie() as cur:
        cur.execute("SELECT * FROM laden.leveringen WHERE id = %s", (lid,))
        r = cur.fetchone()
        if not r:
            return None, []
        cur.execute("SELECT resource, regel, veld, code, melding FROM laden.fouten WHERE levering_id = %s ORDER BY id "
                    "LIMIT 1000", (lid,))
        return dict(r), [_fout_uit(f) for f in cur.fetchall()]


def _levering_response(r: dict, fouten: list[dict], status: int) -> JSONResponse:
    headers = {"Location": f"{PREFIX}/leveringen/{r['id']}"}
    if r["status"] in LOOPT:
        headers["Retry-After"] = str(RETRY_AFTER)
    return JSONResponse(levering_uit(r, fouten if r["status"] not in LOOPT else None), status_code=status,
                        headers=headers)


def _afgekeurd_probleem(r: dict, fouten: list[dict], versie: int | None) -> JSONResponse:
    loc = f"{PREFIX}/leveringen/{r['id']}"
    detail = (f"{r['fouten_aantal']} fout(en); niets gepubliceerd" +
              (f", versie {versie} blijft actief." if versie else "."))
    doc = probleem(422, "levering-afgekeurd", detail, instance=loc, levering=loc, fouten=fouten)
    return JSONResponse(doc, status_code=422, media_type=MEDIATYPE, headers={"Location": loc})


async def _ontvang(request: Request, mediatype: str) -> tuple[opslag.Ontvangen, str, str, dict | None]:
    """(ontvangen bestand, mediatype, bestandsnaam, dcat). Streamt naar schijf; 413 boven de limiet."""
    ct = kale_mediatype(request.headers.get("content-type"))
    if ct == "multipart/form-data":
        form = await request.form()
        try:
            bestand = form.get("bestand")
            if bestand is None or not hasattr(bestand, "read"):
                raise Probleem(400, "ongeldig-verzoek", "multipart/form-data zonder deel 'bestand'.")
            mt = kale_mediatype(getattr(bestand, "content_type", None))
            if mt in ("", "application/octet-stream"):
                mt = {".zip": "application/zip", ".gpkg": "application/geopackage+sqlite3", ".csv": "text/csv",
                      ".json": "application/json"}.get(Path(bestand.filename or "").suffix.lower(), mt)
            dcat = None
            if form.get("dcat") is not None:
                d = form.get("dcat")
                inhoud = (await d.read()) if hasattr(d, "read") else str(d).encode()
                if len(inhoud) > 1024 * 1024:
                    raise Probleem(413, "te-groot", "Deel dcat is groter dan 1 MB.")
                dcat = _json_body(inhoud)
                if not isinstance(dcat, dict):
                    raise Probleem(400, "ongeldig-verzoek", "Deel dcat moet een JSON-LD-object zijn.")
            await bestand.seek(0)
            try:
                ontvangen = await run_in_threadpool(opslag.ontvang_bestand, bestand.file, _limiet(mt))
            except opslag.TeGroot:
                raise Probleem(413, "te-groot", "Het bestand is groter dan de limiet van deze installatie.")
            return ontvangen, mt, opslag.veilige_bestandsnaam(bestand.filename, mt), dcat
        finally:
            await form.close()
    lengte = request.headers.get("content-length")
    if lengte and lengte.isdigit() and int(lengte) > _limiet(ct):
        raise Probleem(413, "te-groot", "De body is groter dan de limiet van deze installatie.")
    schrijver = await run_in_threadpool(opslag.Schrijver, _limiet(ct))
    try:
        async for blok in request.stream():
            if blok:
                schrijver.schrijf(blok)  # klein en snel: bestand schrijven per blok
    except opslag.TeGroot:
        raise Probleem(413, "te-groot", "De body is groter dan de limiet van deze installatie.")
    except BaseException:
        schrijver.weg()
        raise
    return schrijver.klaar(), ct, opslag.veilige_bestandsnaam(None, ct), None


@router.post("/datasets/{dataset_id}/leveringen")
async def lever_dataset(dataset_id: str, request: Request,
                        principal: Principal = Depends(vereis_rol(*LEVEREN))):
    q = request.query_params
    if q.get("modus", "vervangen") != "vervangen":
        raise Probleem(400, "ongeldig-verzoek", "Alleen modus vervangen wordt ondersteund (v1).")
    alleen_valideren = _bool(q.get("alleenValideren"), "alleenValideren")
    wacht = _bool(q.get("wacht"), "wacht")
    sleutel = request.headers.get("idempotency-key")
    if sleutel is not None and not (0 < len(sleutel) <= 255):
        raise Probleem(400, "ongeldig-verzoek", "Idempotency-Key moet 1 tot 255 tekens zijn.")
    ds = await run_in_threadpool(_db_dataset_rij, dataset_id)
    toegestaan = PROFIELEN[ds["profiel"]]["mediatypes"]
    ct = kale_mediatype(request.headers.get("content-type"))
    if ct != "multipart/form-data" and ct not in toegestaan:
        raise Probleem(415, "mediatype-past-niet", f"{ct or 'geen Content-Type'} past niet bij profiel {ds['profiel']} "
                       f"(toegestaan: {', '.join(toegestaan)}).")
    ontvangen, mt, naam, dcat = await _ontvang(request, ct)
    try:
        if mt not in toegestaan:
            raise Probleem(415, "mediatype-past-niet", f"{mt or 'onbekend'} past niet bij profiel {ds['profiel']} "
                           f"(toegestaan: {', '.join(toegestaan)}).")
        digest = request.headers.get("content-digest")
        if digest and not _digest_klopt(digest, ontvangen.sha256):
            raise Probleem(400, "ongeldig-verzoek", "Content-Digest komt niet overeen met de body.")
        r, nieuw = await run_in_threadpool(_db_nieuwe_levering, dataset_id, ontvangen, mt, naam, sleutel,
                                           alleen_valideren, principal.client_id, dcat)
    finally:
        opslag.verwijder_tijdelijk(ontvangen)
    if not nieuw:
        r, fouten = await run_in_threadpool(_db_levering, str(r["id"]))
        return _levering_response(r, fouten, 200)
    verwerker.bied_aan(str(r["id"]))
    logger.info("Levering %s op %s ontvangen (%s, %d bytes, client %s)", r["id"], dataset_id, mt, r["grootte"],
                principal.client_id)
    if wacht:
        eind = asyncio.get_running_loop().time() + instellingen().laden_wacht_seconden
        while asyncio.get_running_loop().time() < eind:
            await asyncio.sleep(0.5)
            r, fouten = await run_in_threadpool(_db_levering, str(r["id"]))
            if r["status"] in EINDSTATUS:
                break
        if r["status"] in ("gepubliceerd", "gevalideerd"):
            return _levering_response(r, fouten, 201)
        if r["status"] == "afgekeurd":
            return _afgekeurd_probleem(r, fouten, ds["huidige_versie"])
        if r["status"] == "mislukt":
            loc = f"{PREFIX}/leveringen/{r['id']}"
            return JSONResponse(probleem(500, "serverfout", "Technische fout bij het verwerken; niets gepubliceerd. "
                                         "Opnieuw leveren mag.", instance=loc, levering=loc, fouten=fouten),
                                status_code=500, media_type=MEDIATYPE, headers={"Location": loc})
    return _levering_response(r, [], 202)


def _db_dataset_rij(dataset_id: str) -> dict:
    with transactie() as cur:
        return dict(_dataset_of_404(cur, dataset_id))


@router.get("/datasets/{dataset_id}/leveringen")
def lijst_leveringen(dataset_id: str, status: str | None = Query(None), sinds: dt.datetime | None = Query(None),
                     pagina: int = Query(1, ge=1), pagina_grootte: int = Query(20, ge=1, le=100, alias="paginaGrootte"),
                     principal: Principal = Depends(vereis_rol(*LEZEN))):
    if status is not None and status not in (*LOOPT, *EINDSTATUS):
        raise Probleem(400, "ongeldig-verzoek", "Onbekende status.")
    with transactie() as cur:
        _dataset_of_404(cur, dataset_id)
        cur.execute("""SELECT * FROM laden.leveringen WHERE dataset_id = %(ds)s
                       AND (%(st)s::text IS NULL OR status = %(st)s)
                       AND (%(sinds)s::timestamptz IS NULL OR ontvangen_op >= %(sinds)s)
                       ORDER BY ontvangen_op DESC LIMIT %(n)s OFFSET %(off)s""",
                    {"ds": dataset_id, "st": status, "sinds": sinds, "n": pagina_grootte + 1,
                     "off": (pagina - 1) * pagina_grootte})
        rijen = cur.fetchall()
    return {"leveringen": [levering_kort(r) for r in rijen[:pagina_grootte]],
            "_links": _pagina_links(f"{PREFIX}/datasets/{dataset_id}/leveringen", pagina, pagina_grootte,
                                    len(rijen) > pagina_grootte,
                                    {"status": status, "sinds": sinds.isoformat() if sinds else None})}


@router.get("/datasets/{dataset_id}/versies")
def lijst_versies(dataset_id: str, pagina: int = Query(1, ge=1),
                  pagina_grootte: int = Query(20, ge=1, le=100, alias="paginaGrootte"),
                  principal: Principal = Depends(vereis_rol(*LEZEN))):
    with transactie() as cur:
        _dataset_of_404(cur, dataset_id)
        cur.execute("""SELECT v.*, (SELECT l.sha256 FROM laden.leveringen l WHERE l.id = v.levering_id) AS sha256
                       FROM laden.versies v WHERE v.dataset_id = %s ORDER BY v.versie DESC LIMIT %s OFFSET %s""",
                    (dataset_id, pagina_grootte + 1, (pagina - 1) * pagina_grootte))
        rijen = cur.fetchall()
    versies = []
    for v in rijen[:pagina_grootte]:
        enkel = len(v["levering_ids"]) == 1
        item = {"versie": v["versie"], "actueel": v["actief"], "leveringIds": [str(x) for x in v["levering_ids"]],
                "gepubliceerdOp": _iso(v["gepubliceerd_op"]), "aantalRegels": v["aantal_regels"],
                "sha256": v["sha256"] if enkel else None}
        if enkel:
            item["_links"] = {"bestand": _link(f"{PREFIX}/datasets/{dataset_id}/versies/{v['versie']}/bestand")}
        versies.append(item)
    return {"versies": versies, "_links": _pagina_links(f"{PREFIX}/datasets/{dataset_id}/versies", pagina,
                                                         pagina_grootte, len(rijen) > pagina_grootte)}


def _db_versie_bestand(dataset_id: str, versie: str) -> dict:
    if versie != "actueel" and not (versie.isdigit() and int(versie) > 0):
        raise Probleem(400, "ongeldig-verzoek", "versie is een positief getal of 'actueel'.")
    with transactie() as cur:
        _dataset_of_404(cur, dataset_id)
        if versie == "actueel":
            cur.execute("SELECT * FROM laden.versies WHERE dataset_id = %s AND actief", (dataset_id,))
        else:
            cur.execute("SELECT * FROM laden.versies WHERE dataset_id = %s AND versie = %s", (dataset_id, int(versie)))
        v = cur.fetchone()
        if not v:
            raise Probleem(404, "niet-gevonden", f"Versie {versie} van {dataset_id} bestaat niet.")
        if len(v["levering_ids"]) != 1:
            raise Probleem(409, "versie-meerdere-leveringen",
                           "Deze versie bestaat uit meerdere leveringen (vervangbereik kleiner dan de dataset); "
                           "haal per levering het bestand op, zie /versies.")
        cur.execute("SELECT * FROM laden.leveringen WHERE id = %s", (v["levering_ids"][0],))
        return dict(cur.fetchone())


@router.get("/datasets/{dataset_id}/versies/{versie}/bestand")
def haal_versie_bestand(dataset_id: str, versie: str, principal: Principal = Depends(vereis_rol(*LEZEN))):
    lv = _db_versie_bestand(dataset_id, versie)
    pad = opslag.pad(dataset_id, str(lv["id"]), lv["bestandsnaam"])
    if lv["bestand_verwijderd_op"] or not pad.is_file():
        raise Probleem(404, "niet-gevonden", "Het bestand van deze versie is niet meer bewaard (bewaartermijn).")
    digest = base64.b64encode(bytes.fromhex(lv["sha256"])).decode()
    return FileResponse(pad, media_type=lv["mediatype"], filename=lv["bestandsnaam"],
                        headers={"Content-Digest": f"sha-256=:{digest}:"})


@router.get("/leveringen/{levering_id}")
def haal_levering(levering_id: uuid.UUID, principal: Principal | None = Depends(principal_optioneel)):
    if principal is None:
        raise Probleem(401, "niet-geauthenticeerd", "Bearer-token ontbreekt.", headers={"WWW-Authenticate": "Bearer"})
    r, fouten = _db_levering(str(levering_id))
    if not r or not (mag_lezen(principal, r["dataset_id"]) or (principal.client_id and principal.client_id == r["client_id"])):
        raise Probleem(404, "niet-gevonden", "Levering bestaat niet.")
    return _levering_response(r, fouten, 200)


# ── koppeling met de app: API-Version, Problem Details, verwerker ────────────

class ApiVersieMiddleware:
    """Zet API-Version op elke response onder /api/laden/v1 (ook op fouten van de auth-laag)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope["path"].startswith(PREFIX):
            return await self.app(scope, receive, send)
        versie = api_versie().encode()

        async def stuur(bericht):
            if bericht["type"] == "http.response.start":
                headers = [(k, v) for k, v in bericht.get("headers", []) if k.lower() != b"api-version"]
                headers.append((b"api-version", versie))
                bericht = {**bericht, "headers": headers}
            await send(bericht)

        await self.app(scope, receive, stuur)


def _problem_response(request: Request, status: int, code: str, detail: str, headers: dict | None = None,
                      **extra) -> JSONResponse:
    h = dict(headers or {})
    h["API-Version"] = api_versie()
    return JSONResponse(probleem(status, code, detail, instance=request.url.path, **extra), status_code=status,
                        media_type=MEDIATYPE, headers=h)


def registreer(app) -> None:
    """Router, middleware, foutafhandeling en verwerker aan de app koppelen (main.py)."""
    from omnitwin.fouten import HEADER, nieuwe_correlatie_id
    app.include_router(router)
    app.add_middleware(ApiVersieMiddleware)

    async def bij_probleem(request: Request, exc: Probleem):
        return _problem_response(request, exc.status, exc.code, exc.detail, exc.headers, **exc.extra)

    vorige_http = app.exception_handlers.get(StarletteHTTPException)
    vorige_validatie = app.exception_handlers.get(RequestValidationError)
    vorige_fout = app.exception_handlers.get(Exception)

    async def bij_http(request: Request, exc: StarletteHTTPException):
        if request.url.path.startswith(PREFIX):
            return _problem_response(request, exc.status_code, HTTP_CODE.get(exc.status_code, "ongeldig-verzoek"),
                                     str(exc.detail), getattr(exc, "headers", None))
        if vorige_http:
            return await vorige_http(request, exc)
        from fastapi.exception_handlers import http_exception_handler
        return await http_exception_handler(request, exc)

    async def bij_validatie(request: Request, exc: RequestValidationError):
        if request.url.path.startswith(PREFIX):
            velden = sorted({".".join(str(x) for x in e.get("loc", [])[1:]) for e in exc.errors()})
            return _problem_response(request, 400, "ongeldig-verzoek",
                                     f"Ongeldige parameter(s): {', '.join(v for v in velden if v) or 'onbekend'}.")
        if vorige_validatie:
            return await vorige_validatie(request, exc)
        from fastapi.exception_handlers import request_validation_exception_handler
        return await request_validation_exception_handler(request, exc)

    async def bij_fout(request: Request, exc: Exception):
        if request.url.path.startswith(PREFIX):
            cid = nieuwe_correlatie_id()
            logger.error("%s %s → 500 [%s]", request.method, request.url.path, cid, exc_info=exc)
            return _problem_response(request, 500, "serverfout", f"Er ging iets mis op de server. Meld deze code aan "
                                     f"de beheerder: {cid}", {HEADER: cid}, correlatieId=cid)
        return await vorige_fout(request, exc)

    app.add_exception_handler(Probleem, bij_probleem)
    app.add_exception_handler(StarletteHTTPException, bij_http)
    app.add_exception_handler(RequestValidationError, bij_validatie)
    if vorige_fout:
        app.add_exception_handler(Exception, bij_fout)

    @app.on_event("startup")
    async def _start_verwerker():
        await run_in_threadpool(verwerker.start)

    @app.on_event("shutdown")
    async def _stop_verwerker():
        verwerker.stop()

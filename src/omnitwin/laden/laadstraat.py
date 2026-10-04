"""
Laadstraat: een levering verwerken
==================================
ruw bewaren (bij ontvangst, `omnitwin.laden.opslag`) → **valideren** → **staging** →
**atomisch publiceren**. Alles na het lezen gebeurt in één databasetransactie per levering:
staging, de controles in SQL, de publicatie binnen het vervangbereik, de nieuwe versie en de
status. Bij een fout (afgekeurd of technisch) gaat de hele transactie terug en blijft de vorige
versie actief. Leveringen op één dataset worden na elkaar verwerkt (advisory lock), ook met
meerdere backend-processen.

Statussen (openapi `LeveringStatus`): ontvangen → bezig → gepubliceerd | gevalideerd (alleenValideren)
| afgekeurd (inhoud) | mislukt (techniek; opnieuw leveren mag).

Een levering waarvan het bestand gelijk is (sha256) aan dat van een levering in de actieve
versie, wordt geregistreerd als gepubliceerd zonder nieuwe versie (`aantallen.ongewijzigd`).
"""

from __future__ import annotations

import json
import logging
import traceback
import uuid

from omnitwin.config import instellingen
from omnitwin.fouten import nieuwe_correlatie_id
from omnitwin.laden import opslag
from omnitwin.laden import p_definities as pdef
from omnitwin.laden import p_geo as pgeo
from omnitwin.laden import p_waarnemingen as pwrn
from omnitwin.laden.basis import Afkeuring, Context, Fouten, afkeuren
from omnitwin.laden.db import LAAD_TIMEOUT_MS, slot_dataset, slot_waarnemingen, transactie
from omnitwin.laden.lezen import Onleesbaar, lees
from omnitwin.laden.problemen import MAX_FOUTEN, Fout

logger = logging.getLogger("omnitwin.laden")

ENIGE_RESOURCE = {"waarnemingen": "waarnemingen"}
TOEGESTAAN = {
    "waarnemingen": ("application/geopackage+sqlite3", "application/zip", "text/csv", "application/json"),
    "definities": ("application/geopackage+sqlite3", "application/zip", "application/json"),
    "gebiedsindeling": ("application/geopackage+sqlite3", "application/zip"),
    "kaartlaag": ("application/geopackage+sqlite3", "application/zip"),
}


def claim(levering_id: str) -> tuple[dict, dict] | None:
    """Zet een ontvangen levering op bezig. None als een ander proces hem al heeft."""
    with transactie() as cur:
        cur.execute("""UPDATE laden.leveringen SET status = 'bezig', gestart_op = now()
                       WHERE id = %s AND status = 'ontvangen' RETURNING *""", (levering_id,))
        lv = cur.fetchone()
        if not lv:
            return None
        cur.execute("SELECT * FROM laden.datasets WHERE id = %s", (lv["dataset_id"],))
        return dict(lv), dict(cur.fetchone())


def _rond_af(cur, lid: str, status: str, aantallen: dict, versie: int | None = None,
             fouten: Fouten | None = None) -> None:
    if fouten:
        cur.execute("DELETE FROM laden.fouten WHERE levering_id = %s", (lid,))
        import psycopg2.extras
        psycopg2.extras.execute_values(cur, """INSERT INTO laden.fouten (levering_id, resource, regel, veld, code, melding)
                                               VALUES %s""",
                                       [(lid, f.resource, f.regel, f.veld, f.code, f.melding[:1000])
                                        for f in fouten.lijst[:MAX_FOUTEN]])
    cur.execute("""UPDATE laden.leveringen SET status = %s, aantallen = %s, versie = %s, fouten_aantal = %s,
                          klaar_op = now() WHERE id = %s""",
                (status, json.dumps(aantallen), versie, fouten.totaal if fouten else 0, lid))


def _afgekeurd(lid: str, afk: Afkeuring, aantallen: dict) -> None:
    a = {**aantallen, **afk.aantallen}
    a.setdefault("fout", afk.fouten.foute_regels)
    a.update(gepubliceerd=0, vervangen=0)
    with transactie() as cur:
        _rond_af(cur, lid, "afgekeurd", _openbaar(a), fouten=afk.fouten)


def _mislukt(lid: str, cid: str) -> None:
    f = Fouten()
    f.voeg(Fout("serverfout", f"Technische fout bij het verwerken; meld code {cid} aan de beheerder. "
                "Niets gepubliceerd; opnieuw leveren mag."))
    try:
        with transactie() as cur:
            _rond_af(cur, lid, "mislukt", {"gepubliceerd": 0}, fouten=f)
    except Exception:  # pragma: no cover - database weg
        logger.exception("Levering %s niet op mislukt gezet", lid)


def _openbaar(a: dict) -> dict:
    """Aantallen zonder interne sleutels (_...)."""
    return {k: v for k, v in a.items() if not k.startswith("_")}


def _ongewijzigd(cur, lv: dict, ds: dict) -> dict | None:
    """Levering in de actieve versie met hetzelfde bestand (sha256)? Dan geen nieuwe versie."""
    cur.execute("""SELECT l.id, l.aantallen, v.versie FROM laden.versies v
                   JOIN laden.leveringen l ON l.id = ANY(v.levering_ids)
                   WHERE v.dataset_id = %s AND v.actief AND l.sha256 = %s AND l.id <> %s
                   ORDER BY l.klaar_op DESC LIMIT 1""", (ds["id"], lv["sha256"], lv["id"]))
    return cur.fetchone()


def _versie(cur, ctx: Context, resultaat: dict) -> int:
    cur.execute("SELECT coalesce(max(versie), 0) + 1 AS v FROM laden.versies WHERE dataset_id = %s", (ctx.dataset_id,))
    v = cur.fetchone()["v"]
    cur.execute("UPDATE laden.versies SET actief = false WHERE dataset_id = %s AND actief", (ctx.dataset_id,))
    cur.execute("""INSERT INTO laden.versies (dataset_id, versie, levering_id, levering_ids, actief, aantal_regels)
                   VALUES (%s, %s, %s, %s::uuid[], true, %s)""",
                (ctx.dataset_id, v, ctx.levering_id, resultaat["_levering_ids"], resultaat["_aantal_regels"]))
    return v


def _beschrijving_bij(cur, ctx: Context, dcat: dict | None, versie: int) -> None:
    """dcat.jsonld uit de levering, plus dct:modified en de distributie (D-OmniTwin zet die zelf)."""
    besch = dict(ctx.dataset["beschrijving"] or {})
    if isinstance(dcat, dict):
        besch.update({k: v for k, v in dcat.items() if k not in ("@context", "@id", "dct:modified", "dcat:distribution")})
    from omnitwin.laden.catalogus import distributie
    besch["dct:modified"] = _nu_iso(cur)
    besch["dcat:distribution"] = [distributie(ctx.dataset_id, versie, ctx.levering)]
    cur.execute("UPDATE laden.datasets SET beschrijving = %s, huidige_versie = %s, gewijzigd_op = now() WHERE id = %s",
                (json.dumps(besch, ensure_ascii=False), versie, ctx.dataset_id))


def _nu_iso(cur) -> str:
    cur.execute("SELECT to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"') AS t")
    return cur.fetchone()["t"]


def verwerk(levering_id: str) -> str | None:
    """Verwerk één levering. Geeft de eindstatus (None als een ander proces hem verwerkt)."""
    geclaimd = claim(levering_id)
    if not geclaimd:
        return None
    lv, ds = geclaimd
    ctx = Context(levering=lv, dataset=ds, max_bytes=instellingen().laden_max_bytes)
    lid, aantallen, bron = str(lv["id"]), {}, None
    try:
        profiel = ds["profiel"]
        if lv["mediatype"] not in TOEGESTAAN[profiel]:
            raise afkeuren("mediatype-past-niet", f"{lv['mediatype']} past niet bij profiel {profiel}")
        if not lv["alleen_valideren"]:
            with transactie() as cur:
                zelfde = _ongewijzigd(cur, lv, ds)
                if zelfde:
                    a = {**(zelfde["aantallen"] or {}), "ongewijzigd": True, "vervangen": 0}
                    _rond_af(cur, lid, "gepubliceerd", a, versie=zelfde["versie"])
                    return "gepubliceerd"
        try:
            bron = lees(opslag.pad(ds["id"], lid, lv["bestandsnaam"]), lv["mediatype"],
                        ENIGE_RESOURCE.get(profiel), ctx.max_bytes)
        except Onleesbaar as e:
            raise afkeuren("formaat-ongeldig", str(e))
        return _verwerk_profiel(ctx, bron, profiel, aantallen)
    except Afkeuring as afk:
        _afgekeurd(lid, afk, aantallen)
        return "afgekeurd"
    except Exception:
        cid = nieuwe_correlatie_id()
        logger.error("Levering %s mislukt [%s]\n%s", lid, cid, traceback.format_exc())
        _mislukt(lid, cid)
        return "mislukt"
    finally:
        if bron:
            bron.sluit()
        if profiel_is_kaartlaag(ds):
            pgeo.kaartlaag_klaar(ctx, geslaagd=False)  # na een geslaagde commit al omgewisseld


def profiel_is_kaartlaag(ds: dict) -> bool:
    return ds.get("profiel") == "kaartlaag"


def _verwerk_profiel(ctx: Context, bron, profiel: str, aantallen: dict) -> str:
    lid = ctx.levering_id
    # 1. Valideren in Python (geen database nodig)
    if profiel == "waarnemingen":
        with transactie() as cur:
            prefixen = pwrn.prefixen(cur)
        data, fouten, a = pwrn.controleer(bron, ctx, prefixen)
    elif profiel == "definities":
        data, fouten, a = pdef.controleer(bron, ctx)
    elif profiel == "gebiedsindeling":
        data, fouten, a = pgeo.controleer_gebiedsindeling(bron, ctx)
    else:
        data, fouten, a = pgeo.controleer_kaartlaag(bron, ctx)
    aantallen.update(a)

    # 2-4. Staging, controles in SQL en publiceren: één transactie
    with transactie(timeout_ms=LAAD_TIMEOUT_MS) as cur:
        slot_dataset(cur, ctx.dataset_id)
        if profiel == "waarnemingen":
            pwrn.stage(cur, data)
            pwrn.db_controles(cur, ctx, fouten)
        elif profiel == "definities":
            pdef.stage(cur, ctx, data)
            pdef.db_controles(cur, ctx, fouten)
        elif profiel == "gebiedsindeling":
            pgeo.stage_gebiedsindeling(cur, ctx, data)
            pgeo.db_controles_gebiedsindeling(cur, ctx, fouten)
        if fouten:
            aantallen.update(fout=max(aantallen.get("fout", 0), fouten.foute_regels))
            aantallen["geldig"] = aantallen.get("gelezen", 0) - aantallen["fout"]
            raise Afkeuring(fouten)
        if ctx.levering["alleen_valideren"]:
            cur.connection.rollback()  # staging weg, niets gepubliceerd
            cur.execute("SET LOCAL ROLE laden_schrijver")
            _rond_af(cur, lid, "gevalideerd", _openbaar({**aantallen, "gepubliceerd": 0, "vervangen": 0}))
            return "gevalideerd"
        if profiel == "waarnemingen":
            slot_waarnemingen(cur)
            resultaat = pwrn.publiceer(cur, ctx)
        elif profiel == "definities":
            cur.execute("SELECT DISTINCT CAST(uuid AS text) AS uuid FROM laden.staging_indicatoren "
                        "WHERE levering_id = %(lv)s", {"lv": ctx.levering_id})
            ctx.extra["herbereken_embeddings"] = [r["uuid"] for r in cur.fetchall()]
            resultaat = pdef.publiceer(cur, ctx)
        elif profiel == "gebiedsindeling":
            resultaat = pgeo.publiceer_gebiedsindeling(cur, ctx)
        else:
            resultaat = pgeo.publiceer_kaartlaag(cur, ctx, data)
        aantallen.update(resultaat)
        if profiel in ("waarnemingen", "definities"):
            # Toegang van de geraakte indicatoren en hun waarden volgt de datasets (#254, V032)
            cur.execute("SELECT public.herbereken_toegang_dataset(%s)", (ctx.dataset_id,))
        versie = _versie(cur, ctx, resultaat)
        _beschrijving_bij(cur, ctx, bron.dcat or ctx.levering.get("dcat"), versie)
        _rond_af(cur, lid, "gepubliceerd", _openbaar(aantallen), versie=versie)
    if profiel == "kaartlaag":
        pgeo.kaartlaag_klaar(ctx, geslaagd=True)
        ctx.extra.pop("kaartlaag_klaar", None)
    if ctx.extra.get("herbereken_embeddings"):
        _herbereken_embeddings(ctx.extra.pop("herbereken_embeddings"))
    try:
        with transactie() as cur:
            opslag.ruim_op(cur)
    except Exception:  # bewaartermijn is geen reden om de levering te laten mislukken
        logger.exception("Opruimen volgens de bewaartermijn mislukt")
    return "gepubliceerd"


def _herbereken_embeddings(indicator_uuids: list[str]) -> None:
    """Na een geslaagde publicatie van definities: embeddings van nieuwe of gewijzigde
    indicatoren bijwerken, zodat de assistent ze vindt (#233). Geen reden om de levering
    te laten mislukken: bij een fout (bijv. model niet beschikbaar) alleen loggen; db-init
    berekent ontbrekende embeddings later alsnog."""
    try:
        from omnitwin.database import SessionLocal
        from omnitwin.services.indicator_embeddings import herbereken_embeddings
        db = SessionLocal()
        try:
            r = herbereken_embeddings(db, indicator_uuids)
            logger.info("Embeddings na levering: %s berekend, %s ongewijzigd",
                        r.get("berekend"), r.get("ongewijzigd"))
        finally:
            db.close()
    except Exception:
        logger.exception("Embeddings herberekenen na levering mislukt (%d indicatoren)",
                         len(indicator_uuids))


def nieuw_id() -> str:
    return str(uuid.uuid4())

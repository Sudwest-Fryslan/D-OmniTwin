"""
Profielen gebiedsindeling (→ gebieden) en kaartlaag (→ lokale kaartlaag)
========================================================================
Contract: `docs/api/laden/profielen/gebiedsindeling.md` en `kaartlaag.md`. Beide leveren een
GeoPackage (los of als resource in een Data Package-zip) met de featuretabel
`laadprofiel.doel.featureTabel`, in EPSG:28992 of EPSG:4326.

gebiedsindeling: gebieden van één gebiedstype (`doel.gebiedstypeId`). Code = `codePrefix` +
sleutelveld. Geometrie (Multi)Polygon, geldig en niet leeg; opgeslagen als MultiPolygon in
EPSG:28992. `gemeente_code` (4 cijfers, moet in `gemeenten` staan; anders leeg en geteld) en
`actief` zijn optioneel; overige attributen gaan naar gebieden.metadata (bestaande metadata,
zoals de watervlag, blijft staan). Vervangen: alle gebieden van het gebiedstype; een gebied dat
verdwijnt en nog waarden heeft wordt inactief, zonder waarden wordt het verwijderd.

kaartlaag (pre-release, gekozen en gedocumenteerd in docs/api/laden/README.md): de GeoPackage
wordt na validatie de lokale kaartlaag `data-upload/laden/<dataset>.gpkg` (volume uploads) en
één rij in externe_kaartlagen (bron_type 'lokaal'), zoals een upload in het beheer. De laag staat
aan; `toegang` volgt de dataset (`dct:accessRights` PUBLIC = openbaar, anders intern: alleen met de
rol lezer of beheerder, #254). De eigen tabel in schema `laag` met OGC API Features (profiel
kaartlaag.md) volgt later.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import re
import shutil
from pathlib import Path

from omnitwin.laden.basis import Afkeuring, Context, Fouten, afkeuren
from omnitwin.laden.catalogus import toegang_van
from omnitwin.laden.lezen import Bron, gpkg_lagen
from omnitwin.laden.p_waarnemingen import plausibel
from omnitwin.laden.problemen import Fout

logger = logging.getLogger("omnitwin.laden.geo")
CRS_TOEGESTAAN = (28992, 4326)
SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")
UPLOAD_MAP = Path("data-upload")  # zoals routers/externe_lagen.py (werkmap /app, volume uploads)


def _json_waarde(w):
    if isinstance(w, (dt.date, dt.datetime, dt.time)):
        return w.isoformat()
    if isinstance(w, bytes):
        return None
    return w


def lees_features(bron: Bron, ctx: Context, fouten: Fouten) -> tuple[list[dict], int | None, str]:
    """Features uit de featuretabel: [{'regel', 'props', 'geom' (shapely)}], EPSG en resource-naam."""
    try:
        import fiona
        from shapely.geometry import shape
    except ImportError:  # pragma: no cover - zit in de image
        raise afkeuren("formaat-ongeldig", "GeoPackage-ondersteuning (fiona) ontbreekt op de server")
    doel = ctx.laadprofiel.get("doel") or {}
    tabel = doel.get("featureTabel")
    if bron.gpkg is None:
        raise afkeuren("formaat-ongeldig", "geen GeoPackage in de levering (los of als resource in de zip)")
    lagen = gpkg_lagen(bron.gpkg)
    if tabel not in lagen:
        raise afkeuren("formaat-ongeldig", f"featureTabel {tabel} ontbreekt in de GeoPackage "
                       f"(tabellen: {', '.join(sorted(lagen)) or 'geen'})", resource=tabel)
    features = []
    try:
        with fiona.open(bron.gpkg, layer=tabel) as src:
            epsg = src.crs.to_epsg() if src.crs else None
            if epsg not in CRS_TOEGESTAAN:
                raise afkeuren("crs-niet-ondersteund", f"CRS EPSG:{epsg} wordt niet ondersteund; gebruik EPSG:28992 "
                               "of EPSG:4326", resource=tabel)
            velden = list(src.schema["properties"])
            for i, f in enumerate(src, start=1):
                props = {k: _json_waarde(v) for k, v in dict(f.properties or {}).items()}
                geom = None
                if f.geometry is None:
                    fouten.voeg(Fout("geometrie-ongeldig", "geometrie ontbreekt", tabel, i, "geometrie"))
                else:
                    geom = shape(f.geometry)
                    if geom.is_empty or not geom.is_valid:
                        fouten.voeg(Fout("geometrie-ongeldig", "lege of ongeldige geometrie (niet gerepareerd)",
                                         tabel, i, "geometrie"))
                features.append({"regel": i, "props": props, "geom": geom})
    except Afkeuring:
        raise
    except Exception as e:  # fiona/GDAL: onleesbare tabel
        raise afkeuren("formaat-ongeldig", f"featureTabel {tabel} is niet te lezen ({type(e).__name__})", resource=tabel)
    ctx.extra["velden"] = velden
    return features, epsg, tabel


def _sleutels(features, veld, tabel, fouten, prefix=""):
    gezien = {}
    for f in features:
        w = f["props"].get(veld)
        if w in (None, ""):
            fouten.voeg(Fout("schema-ongeldig", f"{veld} is leeg", tabel, f["regel"], veld))
            f["code"] = None
            continue
        code = str(int(w)) if isinstance(w, float) and w == int(w) else str(w)
        if prefix and not code.startswith(prefix):
            code = prefix + code
        f["code"] = code
        eerder = gezien.setdefault(code, f["regel"])
        if eerder != f["regel"]:
            fouten.voeg(Fout("dubbele-sleutel", f"regel {f['regel']} heeft dezelfde sleutel als regel {eerder}",
                             tabel, f["regel"], veld))


# ── gebiedsindeling ──────────────────────────────────────────────────────────

def controleer_gebiedsindeling(bron: Bron, ctx: Context) -> tuple[dict, Fouten, dict]:
    fouten = Fouten()
    doel = ctx.laadprofiel.get("doel") or {}
    features, epsg, tabel = lees_features(bron, ctx, fouten)
    velden = ctx.extra["velden"]
    for v in (doel.get("sleutelveld"), doel.get("labelveld")):
        if v not in velden:
            raise afkeuren("schema-ongeldig", f"veld {v} ontbreekt in {tabel}", resource=tabel, veld=v)
    _sleutels(features, doel["sleutelveld"], tabel, fouten, doel.get("codePrefix") or "")
    for f in features:
        if f["geom"] is not None and f["geom"].geom_type not in ("Polygon", "MultiPolygon"):
            fouten.voeg(Fout("geometrie-ongeldig", "alleen Polygon of MultiPolygon", tabel, f["regel"], "geometrie"))
        if f["props"].get(doel["labelveld"]) in (None, ""):
            fouten.voeg(Fout("schema-ongeldig", f"{doel['labelveld']} is leeg", tabel, f["regel"], doel["labelveld"]))
    n = len(features)
    aantallen = {"gelezen": n, "fout": fouten.foute_regels, "geldig": n - fouten.foute_regels, "crs": f"EPSG:{epsg}"}
    return {"features": features, "epsg": epsg, "tabel": tabel}, fouten, aantallen


def stage_gebiedsindeling(cur, ctx: Context, data: dict) -> None:
    import psycopg2.extras
    from shapely.geometry import MultiPolygon
    doel = ctx.laadprofiel["doel"]
    eigen = {doel["sleutelveld"], doel["labelveld"], "gemeente_code", "actief"}
    rijen = []
    for f in data["features"]:
        if f["geom"] is None or not f.get("code") or f["geom"].geom_type not in ("Polygon", "MultiPolygon"):
            continue
        g = f["geom"] if f["geom"].geom_type == "MultiPolygon" else MultiPolygon([f["geom"]])
        p = f["props"]
        gm = p.get("gemeente_code")
        gm = (str(int(gm)).zfill(4) if isinstance(gm, (int, float)) else str(gm)) if gm not in (None, "") else None
        actief = p.get("actief")
        meta = {k: v for k, v in p.items() if k not in eigen and v is not None}
        rijen.append((ctx.levering_id, f["regel"], f["code"], str(p[doel["labelveld"]])[:255],
                      gm if gm and re.fullmatch(r"\d{4}", gm) else None,
                      True if actief is None else bool(actief), psycopg2.extras.Json(meta) if meta else None,
                      g.wkb, data["epsg"]))
    psycopg2.extras.execute_values(cur, """
        INSERT INTO laden.staging_gebieden (levering_id, regel, id, naam, gemeente_code, actief, metadata, geom)
        VALUES %s""", rijen,
        template="(%s, %s, %s, %s, %s, %s, %s, ST_Multi(ST_Transform(ST_GeomFromWKB(%s, %s), 28992)))",
        page_size=500)


def db_controles_gebiedsindeling(cur, ctx: Context, fouten: Fouten) -> None:
    doel = ctx.laadprofiel["doel"]
    p = {"lv": ctx.levering_id, "gt": doel["gebiedstypeId"]}
    cur.execute("SELECT 1 FROM public.gebiedstypes WHERE id = %(gt)s", p)
    if not cur.fetchone():
        fouten.voeg(Fout("gebiedstype-onbekend", "het gebiedstype van de registratie (doel.gebiedstypeId) bestaat "
                         "niet; lever eerst de definities of vul de stuurdata aan"))
        return
    cur.execute("""SELECT s.regel FROM laden.staging_gebieden s JOIN public.gebieden g ON g.id = s.id
                   WHERE s.levering_id = %(lv)s AND g.gebiedstype_id <> %(gt)s ORDER BY s.regel LIMIT 1000""", p)
    for r in cur.fetchall():
        fouten.voeg(Fout("dubbele-sleutel", "deze gebiedscode bestaat al bij een ander gebiedstype; gebruik "
                         "codePrefix", None, r["regel"], doel["sleutelveld"]))


def publiceer_gebiedsindeling(cur, ctx: Context) -> dict:
    doel = ctx.laadprofiel["doel"]
    p = {"lv": ctx.levering_id, "gt": doel["gebiedstypeId"]}
    cur.execute("SELECT count(*) AS n FROM public.gebieden WHERE gebiedstype_id = %(gt)s AND actief", p)
    vorig = cur.fetchone()["n"]
    cur.execute("""UPDATE laden.staging_gebieden s SET gemeente_code = NULL
                   WHERE s.levering_id = %(lv)s AND s.gemeente_code IS NOT NULL
                     AND NOT EXISTS (SELECT 1 FROM public.gemeenten m WHERE m.code = s.gemeente_code)""", p)
    gemeente_onbekend = cur.rowcount
    cur.execute("""
        INSERT INTO public.gebieden AS g (id, gebiedstype_id, naam, geom, metadata, actief, gemeente_code)
        SELECT s.id, %(gt)s, s.naam, s.geom, s.metadata, s.actief, s.gemeente_code
        FROM laden.staging_gebieden s WHERE s.levering_id = %(lv)s
        ON CONFLICT (id) DO UPDATE SET
            naam = EXCLUDED.naam,
            geom = EXCLUDED.geom,
            actief = EXCLUDED.actief,
            gemeente_code = coalesce(EXCLUDED.gemeente_code, g.gemeente_code),
            metadata = coalesce(g.metadata, '{}'::jsonb) || coalesce(EXCLUDED.metadata, '{}'::jsonb)
        WHERE g.gebiedstype_id = EXCLUDED.gebiedstype_id""", p)
    gepubliceerd = cur.rowcount
    # Verdwenen gebieden: met waarden inactief, zonder waarden weg
    cur.execute("""
        UPDATE public.gebieden g SET actief = false
        WHERE g.gebiedstype_id = %(gt)s AND g.actief
          AND NOT EXISTS (SELECT 1 FROM laden.staging_gebieden s WHERE s.levering_id = %(lv)s AND s.id = g.id)
          AND EXISTS (SELECT 1 FROM public.gebied_data d WHERE d.gebied_id = g.id)""", p)
    inactief = cur.rowcount
    cur.execute("""
        DELETE FROM public.gebieden g
        WHERE g.gebiedstype_id = %(gt)s
          AND NOT EXISTS (SELECT 1 FROM laden.staging_gebieden s WHERE s.levering_id = %(lv)s AND s.id = g.id)
          AND NOT EXISTS (SELECT 1 FROM public.gebied_data d WHERE d.gebied_id = g.id)""", p)
    verwijderd = cur.rowcount
    cur.execute("DELETE FROM laden.staging_gebieden WHERE levering_id = %(lv)s", p)
    plausibel(ctx.laadprofiel, gepubliceerd, vorig)
    uit = {"gepubliceerd": gepubliceerd, "vervangen": vorig, "inactief": inactief, "verwijderd": verwijderd,
           "_aantal_regels": gepubliceerd, "_levering_ids": [ctx.levering_id]}
    if gemeente_onbekend:
        uit["gemeenteOnbekend"] = gemeente_onbekend
    return uit


# ── kaartlaag ────────────────────────────────────────────────────────────────

def controleer_kaartlaag(bron: Bron, ctx: Context) -> tuple[dict, Fouten, dict]:
    fouten = Fouten()
    doel = ctx.laadprofiel.get("doel") or {}
    features, epsg, tabel = lees_features(bron, ctx, fouten)
    velden = ctx.extra["velden"]
    for v in velden:
        if len(v) > 63 or not SNAKE.match(v):
            fouten.voeg(Fout("schema-ongeldig", "attribuutnaam niet in snake_case of langer dan 63 tekens",
                             tabel, None, v))
    for v in (doel.get("sleutelveld"), doel.get("labelveld")):
        if v and v not in velden:
            raise afkeuren("schema-ongeldig", f"veld {v} ontbreekt in {tabel}", resource=tabel, veld=v)
    _sleutels(features, doel["sleutelveld"], tabel, fouten)
    typen = {f["geom"].geom_type.replace("Multi", "") for f in features if f["geom"] is not None}
    if len(typen) > 1:
        fouten.voeg(Fout("geometrie-ongeldig", f"meer dan één geometrietype ({', '.join(sorted(typen))})", tabel))
    n = len(features)
    aantallen = {"gelezen": n, "fout": fouten.foute_regels, "geldig": n - fouten.foute_regels, "crs": f"EPSG:{epsg}"}
    return {"features": features, "epsg": epsg, "tabel": tabel, "gpkg": bron.gpkg}, fouten, aantallen


def kaartlaag_pad(dataset_id: str) -> Path:
    return UPLOAD_MAP / "laden" / f"{dataset_id}.gpkg"


def publiceer_kaartlaag(cur, ctx: Context, data: dict) -> dict:
    """Rij in externe_kaartlagen bijwerken en het bestand klaarzetten; `klaar` zet het na de commit op zijn plek."""
    besch = ctx.dataset["beschrijving"] or {}
    doel = ctx.laadprofiel["doel"]
    plausibel(ctx.laadprofiel, len(data["features"]), 0)
    rel = f"laden/{ctx.dataset_id}.gpkg"
    p = {"naam": str(besch.get("dct:title") or ctx.dataset_id)[:100], "beschrijving": besch.get("dct:description"),
         "url": rel, "typename": data["tabel"], "toegang": toegang_van(besch), "id": ctx.dataset.get("kaartlaag_id"),
         "ds": ctx.dataset_id}
    if p["id"]:
        cur.execute("""UPDATE public.externe_kaartlagen SET naam = %(naam)s, beschrijving = %(beschrijving)s,
                       bron_type = 'lokaal', url = %(url)s, typename = %(typename)s, srsname = 'EPSG:28992',
                       filter_type = 'alles', actief = true, toegang = %(toegang)s, updated_at = now()
                       WHERE id = %(id)s RETURNING id""", p)
        rij = cur.fetchone()
        p["id"] = rij["id"] if rij else None
    if not p["id"]:
        cur.execute("""INSERT INTO public.externe_kaartlagen (naam, beschrijving, laag_type, bron_type, url, typename,
                           srsname, filter_type, actief, toegang)
                       VALUES (%(naam)s, %(beschrijving)s, 'selectie', 'lokaal', %(url)s, %(typename)s, 'EPSG:28992',
                               'alles', true, %(toegang)s) RETURNING id""", p)
        p["id"] = cur.fetchone()["id"]
        cur.execute("UPDATE laden.datasets SET kaartlaag_id = %(id)s WHERE id = %(ds)s", p)
    # Bestand naast het doel klaarzetten; pas na de commit omwisselen (os.replace is atomisch)
    doelpad = kaartlaag_pad(ctx.dataset_id)
    doelpad.parent.mkdir(parents=True, exist_ok=True)
    tijdelijk = doelpad.with_suffix(f".{ctx.levering_id}.deel")
    shutil.copyfile(data["gpkg"], tijdelijk)
    ctx.extra["kaartlaag_klaar"] = (tijdelijk, doelpad, p["id"])
    n = len(data["features"])
    return {"gepubliceerd": n, "vervangen": 0, "kaartlaagId": p["id"], "_aantal_regels": n,
            "_levering_ids": [ctx.levering_id]}


def kaartlaag_klaar(ctx: Context, geslaagd: bool) -> None:
    klaar = ctx.extra.get("kaartlaag_klaar")
    if not klaar:
        return
    tijdelijk, doelpad, laag_id = klaar
    if geslaagd:
        os.replace(tijdelijk, doelpad)
        try:  # cache van de kaartlaag in dit proces vervalt
            from omnitwin.routers.externe_lagen import _wfs_cache
            _wfs_cache.pop(laag_id, None)
        except Exception:  # pragma: no cover
            pass
    else:
        Path(tijdelijk).unlink(missing_ok=True)

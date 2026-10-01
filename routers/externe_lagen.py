"""
Externe Kaartlagen API Router
==============================
Endpoints voor het beheren en serveren van externe geo-lagen (WFS/WMS/lokaal).
Bevat een WFS proxy met 24u cache en lokale GPKG/GeoJSON leesfunctie.

Sprint 18 Track B — Extern Lagen Beheersysteem

Endpoints (public):
- GET  /api/externe-lagen              → Actieve lagen (voor frontend toggles)
- GET  /api/externe-lagen/{id}/features → WFS proxy of lokaal bestand (GeoJSON, cached 24u)
- POST /api/externe-lagen/{id}/buurten  → CBS-buurten via ST_Contains(centroid)

Endpoints (admin):
- GET    /api/admin/externe-lagen              → Alle lagen (incl. inactief)
- POST   /api/admin/externe-lagen              → Nieuwe laag aanmaken
- PUT    /api/admin/externe-lagen/{id}         → Laag bijwerken
- DELETE /api/admin/externe-lagen/{id}         → Laag verwijderen
- GET    /api/admin/externe-lagen/lokale-bestanden → Beschikbare bestanden in data-upload/
- POST   /api/admin/externe-lagen/upload       → Bestand uploaden naar data-upload/
"""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, field_validator
from typing import Optional
from pathlib import Path
import httpx
import time
import re
import json
import logging

from src.database import get_db
from routers.auth import vereis_admin

logger = logging.getLogger(__name__)

# ============================================================================
# Data-upload directory voor lokale bestanden
# ============================================================================
DATA_UPLOAD_DIR = Path("data-upload")

# ============================================================================
# Provincie bounding boxes (Rijksdriehoek / EPSG:28992)
# ============================================================================
PROVINCIE_BBOXEN = {
    "Fryslân":          "90000,535000,250000,640000",
    "Groningen":        "210000,575000,280000,620000",
    "Drenthe":          "195000,520000,265000,580000",
    "Overijssel":       "175000,470000,270000,540000",
    "Flevoland":        "130000,475000,190000,530000",
    "Gelderland":       "130000,415000,230000,490000",
    "Utrecht":          "115000,440000,170000,475000",
    "Noord-Holland":    "95000,465000,165000,560000",
    "Zuid-Holland":      "50000,410000,130000,475000",
    "Zeeland":          "10000,365000,80000,415000",
    "Noord-Brabant":    "80000,370000,200000,420000",
    "Limburg":          "160000,310000,210000,420000",
    "Nederland":        "7000,289000,300000,629000",
}

# ============================================================================
# In-memory WFS cache — {laag_id: (timestamp, geojson_dict)}
# ============================================================================
_wfs_cache: dict = {}
CACHE_TTL_SEC = 86400  # 24 uur

# ============================================================================
# Pydantic models
# ============================================================================

_VALID_HEX_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')

class ExterneKaartlaagCreate(BaseModel):
    naam: str
    beschrijving: Optional[str] = None
    laag_type: str = "selectie"
    bron_type: str = "WFS"
    url: str
    typename: Optional[str] = None
    srsname: str = "EPSG:28992"
    versie: str = "2.0.0"
    filter_type: str = "provincie"
    filter_waarde: Optional[str] = None
    koppel_veld: Optional[str] = None
    kleur_lijn: str = "#8B5CF6"
    kleur_fill: str = "#8B5CF6"
    opacity: float = 0.15
    actief: bool = True
    volgorde: int = 0

    @field_validator("laag_type")
    @classmethod
    def check_laag_type(cls, v: str) -> str:
        if v not in ("selectie", "data_koppel"):
            raise ValueError("laag_type moet 'selectie' of 'data_koppel' zijn")
        return v

    @field_validator("bron_type")
    @classmethod
    def check_bron_type(cls, v: str) -> str:
        if v not in ("WFS", "WMS", "GeoJSON", "lokaal"):
            raise ValueError("bron_type moet 'WFS', 'WMS', 'GeoJSON' of 'lokaal' zijn")
        return v

    @field_validator("filter_type")
    @classmethod
    def check_filter_type(cls, v: str) -> str:
        if v not in ("bbox", "provincie", "alles"):
            raise ValueError("filter_type moet 'bbox', 'provincie' of 'alles' zijn")
        return v

    @field_validator("kleur_lijn", "kleur_fill")
    @classmethod
    def check_hex_color(cls, v: str) -> str:
        if not _VALID_HEX_RE.match(v):
            raise ValueError("Kleur moet hex-formaat zijn (#RRGGBB)")
        return v

    @field_validator("opacity")
    @classmethod
    def check_opacity(cls, v: float) -> float:
        if not 0 <= v <= 1:
            raise ValueError("Opacity moet tussen 0 en 1 liggen")
        return v


class ExterneKaartlaagUpdate(BaseModel):
    naam: Optional[str] = None
    beschrijving: Optional[str] = None
    laag_type: Optional[str] = None
    bron_type: Optional[str] = None
    url: Optional[str] = None
    typename: Optional[str] = None
    srsname: Optional[str] = None
    versie: Optional[str] = None
    filter_type: Optional[str] = None
    filter_waarde: Optional[str] = None
    koppel_veld: Optional[str] = None
    kleur_lijn: Optional[str] = None
    kleur_fill: Optional[str] = None
    opacity: Optional[float] = None
    actief: Optional[bool] = None
    volgorde: Optional[int] = None


class BuurtenRequest(BaseModel):
    """WKT geometry van een extern laag-feature voor ST_Intersects."""
    wkt: str

    @field_validator("wkt")
    @classmethod
    def check_wkt(cls, v: str) -> str:
        # Basis WKT validatie: moet beginnen met een geldig geometrie-type
        upper = v.strip().upper()
        valid_prefixes = ("POLYGON", "MULTIPOLYGON", "POINT", "LINESTRING")
        if not any(upper.startswith(p) for p in valid_prefixes):
            raise ValueError("WKT moet beginnen met POLYGON, MULTIPOLYGON, POINT of LINESTRING")
        return v


# ============================================================================
# Router definitie
# ============================================================================
router = APIRouter(tags=["Externe Kaartlagen"])

# Beheer-routes (/api/admin/externe-lagen/*): apart router met admin-check (#65)
admin_router = APIRouter(prefix="/api/admin/externe-lagen", tags=["Externe Kaartlagen"], dependencies=[Depends(vereis_admin)])


# ============================================================================
# Hulpfuncties: lokaal bestand lezen + WFS ophalen
# ============================================================================

def _load_local_file(filename: str, layer_name: str = None) -> dict:
    """
    Lees een lokaal GPKG/GeoJSON bestand uit data-upload/ en converteer naar
    GeoJSON FeatureCollection in WGS84 (EPSG:4326).
    """
    import fiona
    from shapely.geometry import shape, mapping

    filepath = DATA_UPLOAD_DIR / filename
    if not filepath.exists():
        raise HTTPException(404, f"Lokaal bestand niet gevonden: {filename}")

    # Veiligheidscheck: pad mag niet buiten data-upload/ vallen
    try:
        filepath.resolve().relative_to(DATA_UPLOAD_DIR.resolve())
    except ValueError:
        raise HTTPException(400, "Ongeldig bestandspad")

    allowed_extensions = {'.gpkg', '.geojson', '.json'}
    if filepath.suffix.lower() not in allowed_extensions:
        raise HTTPException(400, f"Bestandstype '{filepath.suffix}' niet ondersteund")

    try:
        # Bepaal layer
        layers = fiona.listlayers(str(filepath))
        open_layer = layer_name if layer_name and layer_name in layers else layers[0]

        features = []
        with fiona.open(str(filepath), layer=open_layer) as src:
            src_crs = str(src.crs).upper() if src.crs else ""
            needs_transform = "28992" in src_crs or "RD" in src_crs

            for feat in src:
                geom = shape(feat["geometry"])
                props = dict(feat.get("properties", {}))

                if needs_transform:
                    # Gebruik bestaande _transform_rd_to_wgs84 logica
                    geom_geojson = mapping(geom)
                    # We transformeren de coords inline
                    features.append({
                        "type": "Feature",
                        "geometry": geom_geojson,
                        "properties": props
                    })
                else:
                    features.append({
                        "type": "Feature",
                        "geometry": mapping(geom),
                        "properties": props
                    })

        geojson = {"type": "FeatureCollection", "features": features}

        # RD → WGS84 transformatie als nodig
        if needs_transform:
            geojson = _transform_rd_to_wgs84(geojson)

        logger.info("Lokaal bestand geladen: %s (layer=%s, %d features, transform=%s)",
                    filename, open_layer, len(features), needs_transform)
        return geojson

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Fout bij laden lokaal bestand %s: %s", filename, e)
        raise HTTPException(500, f"Fout bij laden van {filename}: {str(e)}")


async def _fetch_wfs(row) -> dict:
    """WFS request uitvoeren en GeoJSON ophalen + RD→WGS84 transformatie."""
    params = {
        "service": "WFS",
        "version": row.versie or "2.0.0",
        "request": "GetFeature",
        "typeName": row.typename,
        "outputFormat": "application/json",
        "srsName": row.srsname or "EPSG:28992",
    }

    # Filter toevoegen
    if row.filter_type == "provincie":
        bbox_str = PROVINCIE_BBOXEN.get(row.filter_waarde)
        if bbox_str:
            params["bbox"] = f"{bbox_str},{row.srsname or 'EPSG:28992'}"
    elif row.filter_type == "bbox" and row.filter_waarde:
        params["bbox"] = f"{row.filter_waarde},{row.srsname or 'EPSG:28992'}"
    # 'alles' → geen bbox filter

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(row.url, params=params)
            resp.raise_for_status()
            geojson = resp.json()
    except httpx.TimeoutException:
        raise HTTPException(504, f"Timeout bij ophalen van {row.naam} (>60s)")
    except httpx.HTTPStatusError as e:
        raise HTTPException(502, f"WFS fout bij {row.naam}: HTTP {e.response.status_code}")
    except Exception as e:
        logger.error("WFS proxy fout voor laag %s: %s", row.naam, e)
        raise HTTPException(502, f"Fout bij ophalen van {row.naam}")

    # Transformeer naar WGS84 als srsname = EPSG:28992
    if (row.srsname or "EPSG:28992") == "EPSG:28992":
        geojson = _transform_rd_to_wgs84(geojson)

    return geojson


# ============================================================================
# Public endpoints
# ============================================================================

@router.get("/api/externe-lagen")
async def get_actieve_lagen(db: Session = Depends(get_db)):
    """
    Haal alle actieve externe kaartlagen op (voor frontend toggle-rendering).
    Geen authenticatie nodig — alleen actieve lagen, geen connectie-details.
    """
    rows = db.execute(text("""
        SELECT id, naam, beschrijving, laag_type, bron_type,
               kleur_lijn, kleur_fill, opacity, volgorde
        FROM externe_kaartlagen
        WHERE actief = true
        ORDER BY volgorde, naam
    """)).fetchall()

    return {
        "lagen": [
            {
                "id": r.id,
                "naam": r.naam,
                "beschrijving": r.beschrijving,
                "laag_type": r.laag_type,
                "bron_type": r.bron_type,
                "kleur_lijn": r.kleur_lijn,
                "kleur_fill": r.kleur_fill,
                "opacity": r.opacity,
                "volgorde": r.volgorde
            } for r in rows
        ],
        "totaal": len(rows)
    }


@router.get("/api/externe-lagen/{laag_id}/features")
async def get_laag_features(laag_id: int, db: Session = Depends(get_db)):
    """
    WFS proxy: haal features op voor een externe laag.
    Response wordt 24u gecached per laag_id.
    """
    # Laag ophalen (alleen actieve)
    row = db.execute(text("""
        SELECT id, naam, bron_type, url, typename, srsname, versie,
               filter_type, filter_waarde
        FROM externe_kaartlagen
        WHERE id = :id AND actief = true
    """), {"id": laag_id}).fetchone()

    if not row:
        raise HTTPException(404, f"Kaartlaag {laag_id} niet gevonden of niet actief")

    # Cache check
    cached = _wfs_cache.get(laag_id)
    if cached and (time.time() - cached[0]) < CACHE_TTL_SEC:
        logger.info("Cache hit voor externe laag %d (%s)", laag_id, row.naam)
        return cached[1]

    # Routing op bron_type
    if row.bron_type == "lokaal":
        geojson = _load_local_file(row.url, row.typename)
    elif row.bron_type == "WFS":
        geojson = await _fetch_wfs(row)
    else:
        raise HTTPException(501, f"Bron type '{row.bron_type}' wordt nog niet ondersteund")

    # Metadata toevoegen
    feature_count = len(geojson.get("features", []))
    geojson["metadata"] = {
        "laag_id": laag_id,
        "laag_naam": row.naam,
        "bron": row.url,
        "bron_type": row.bron_type,
        "typename": row.typename,
        "filter": f"{row.filter_type}={row.filter_waarde}" if row.filter_type else None,
        "features_count": feature_count,
        "crs": "EPSG:4326"
    }

    # Cache opslaan
    _wfs_cache[laag_id] = (time.time(), geojson)
    logger.info("%s features opgehaald voor laag %d (%s): %d features",
                row.bron_type, laag_id, row.naam, feature_count)

    return geojson


@router.post("/api/externe-lagen/{laag_id}/buurten")
async def get_buurten_voor_feature(
    laag_id: int,
    body: BuurtenRequest,
    db: Session = Depends(get_db)
):
    """
    Selecteer CBS-buurten waarvan het zwaartepunt (centroid) binnen de
    gegeven geometrie valt. Dit is preciezer dan ST_Intersects+buffer
    voor kleinere selectie-polygonen zoals woonplaatsen.

    Body: { "wkt": "POLYGON((...))"}  — geometrie in EPSG:4326 (WGS84)
    Backend transformeert naar EPSG:28992 (RD) voor de spatial query.
    """
    # Verifieer dat de laag bestaat en actief is
    laag = db.execute(text(
        "SELECT id, naam FROM externe_kaartlagen WHERE id = :id AND actief = true"
    ), {"id": laag_id}).fetchone()

    if not laag:
        raise HTTPException(404, f"Kaartlaag {laag_id} niet gevonden of niet actief")

    # Centroid-based selectie: een buurt wordt geselecteerd als zijn
    # zwaartepunt binnen de woonplaats-geometrie valt.
    # Dit voorkomt randoverlap-selectie bij kleinere polygonen.
    # WKT komt in WGS84 (4326) vanuit de frontend, transformeer naar RD (28992)
    try:
        rows = db.execute(text("""
            SELECT g.id, g.naam
            FROM gebieden g
            JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
            WHERE gt.code = 'CBS_BUURT'
              AND g.actief = true
              AND ST_Contains(
                    ST_Transform(ST_GeomFromText(:wkt, 4326), 28992),
                    ST_Centroid(g.geom)
              )
            ORDER BY g.naam
        """), {"wkt": body.wkt}).fetchall()
    except Exception as e:
        logger.error("Spatial query fout voor laag %d: %s", laag_id, e)
        raise HTTPException(500, "Fout bij uitvoeren van ruimtelijke query")

    buurten = [{"id": r.id, "naam": r.naam} for r in rows]

    return {
        "laag_id": laag_id,
        "laag_naam": laag.naam,
        "buurten": buurten,
        "totaal": len(buurten),
        "methode": "centroid"
    }


# ============================================================================
# Admin CRUD endpoints
# ============================================================================

@admin_router.get("")
async def admin_get_alle_lagen(
    db: Session = Depends(get_db),
):
    """Alle externe kaartlagen ophalen (inclusief inactieve) voor admin beheer."""
    rows = db.execute(text("""
        SELECT id, naam, beschrijving, laag_type, bron_type,
               url, typename, srsname, versie,
               filter_type, filter_waarde, koppel_veld,
               kleur_lijn, kleur_fill, opacity, actief, volgorde,
               created_at, updated_at
        FROM externe_kaartlagen
        ORDER BY volgorde, naam
    """)).fetchall()

    return {
        "lagen": [
            {
                "id": r.id,
                "naam": r.naam,
                "beschrijving": r.beschrijving,
                "laag_type": r.laag_type,
                "bron_type": r.bron_type,
                "url": r.url,
                "typename": r.typename,
                "srsname": r.srsname,
                "versie": r.versie,
                "filter_type": r.filter_type,
                "filter_waarde": r.filter_waarde,
                "koppel_veld": r.koppel_veld,
                "kleur_lijn": r.kleur_lijn,
                "kleur_fill": r.kleur_fill,
                "opacity": r.opacity,
                "actief": r.actief,
                "volgorde": r.volgorde,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            } for r in rows
        ],
        "totaal": len(rows)
    }


@admin_router.post("")
async def admin_create_laag(
    data: ExterneKaartlaagCreate,
    db: Session = Depends(get_db),
):
    """Nieuwe externe kaartlaag aanmaken."""
    result = db.execute(text("""
        INSERT INTO externe_kaartlagen
            (naam, beschrijving, laag_type, bron_type, url, typename,
             srsname, versie, filter_type, filter_waarde, koppel_veld,
             kleur_lijn, kleur_fill, opacity, actief, volgorde)
        VALUES
            (:naam, :beschrijving, :laag_type, :bron_type, :url, :typename,
             :srsname, :versie, :filter_type, :filter_waarde, :koppel_veld,
             :kleur_lijn, :kleur_fill, :opacity, :actief, :volgorde)
        RETURNING id
    """), {
        "naam": data.naam,
        "beschrijving": data.beschrijving,
        "laag_type": data.laag_type,
        "bron_type": data.bron_type,
        "url": data.url,
        "typename": data.typename,
        "srsname": data.srsname,
        "versie": data.versie,
        "filter_type": data.filter_type,
        "filter_waarde": data.filter_waarde,
        "koppel_veld": data.koppel_veld,
        "kleur_lijn": data.kleur_lijn,
        "kleur_fill": data.kleur_fill,
        "opacity": data.opacity,
        "actief": data.actief,
        "volgorde": data.volgorde,
    })
    new_id = result.fetchone()[0]
    db.commit()

    # Invalideer cache voor nieuwe laag
    _wfs_cache.pop(new_id, None)

    logger.info("Nieuwe externe laag aangemaakt: [%d] %s", new_id, data.naam)
    return {"id": new_id, "naam": data.naam, "status": "aangemaakt"}


@admin_router.put("/{laag_id}")
async def admin_update_laag(
    laag_id: int,
    data: ExterneKaartlaagUpdate,
    db: Session = Depends(get_db),
):
    """Bestaande externe kaartlaag bijwerken."""
    # Verifieer dat laag bestaat
    existing = db.execute(text(
        "SELECT id FROM externe_kaartlagen WHERE id = :id"
    ), {"id": laag_id}).fetchone()
    if not existing:
        raise HTTPException(404, f"Kaartlaag {laag_id} niet gevonden")

    # Dynamische update query opbouwen
    updates = ["updated_at = NOW()"]
    params = {"id": laag_id}

    # Veilig: alleen expliciete velden, geen string-concatenatie met user input
    allowed_fields = {
        "naam", "beschrijving", "laag_type", "bron_type", "url", "typename",
        "srsname", "versie", "filter_type", "filter_waarde", "koppel_veld",
        "kleur_lijn", "kleur_fill", "opacity", "actief", "volgorde"
    }
    for field_name in allowed_fields:
        value = getattr(data, field_name, None)
        if value is not None:
            updates.append(f"{field_name} = :{field_name}")
            params[field_name] = value

    if len(updates) <= 1:
        raise HTTPException(400, "Geen velden om bij te werken")

    query = f"UPDATE externe_kaartlagen SET {', '.join(updates)} WHERE id = :id RETURNING id"
    db.execute(text(query), params)
    db.commit()

    # Invalideer cache voor deze laag
    _wfs_cache.pop(laag_id, None)

    logger.info("Externe laag %d bijgewerkt", laag_id)
    return {"id": laag_id, "status": "bijgewerkt"}


@admin_router.delete("/{laag_id}")
async def admin_delete_laag(
    laag_id: int,
    db: Session = Depends(get_db),
):
    """Externe kaartlaag verwijderen."""
    result = db.execute(text(
        "DELETE FROM externe_kaartlagen WHERE id = :id RETURNING id, naam"
    ), {"id": laag_id})
    row = result.fetchone()
    db.commit()

    if not row:
        raise HTTPException(404, f"Kaartlaag {laag_id} niet gevonden")

    # Cache opruimen
    _wfs_cache.pop(laag_id, None)

    logger.info("Externe laag verwijderd: [%d] %s", row.id, row.naam)
    return {"id": row.id, "naam": row.naam, "status": "verwijderd"}


# ============================================================================
# Admin: Lokale bestanden beheer
# ============================================================================

@admin_router.get("/lokale-bestanden")
async def admin_lokale_bestanden(
):
    """Lijst beschikbare bestanden in data-upload/ met metadata."""
    import fiona

    if not DATA_UPLOAD_DIR.exists():
        return {"bestanden": [], "totaal": 0}

    bestanden = []
    for f in sorted(DATA_UPLOAD_DIR.iterdir()):
        if f.suffix.lower() in ('.gpkg', '.geojson', '.json') and f.is_file():
            try:
                layers = fiona.listlayers(str(f))
                # Haal metadata van eerste layer
                with fiona.open(str(f), layer=layers[0]) as src:
                    bestanden.append({
                        "bestandsnaam": f.name,
                        "grootte_kb": round(f.stat().st_size / 1024, 1),
                        "layers": layers,
                        "features": len(src),
                        "crs": str(src.crs) if src.crs else None,
                        "geometry_type": src.schema.get("geometry", "onbekend"),
                    })
            except Exception as e:
                logger.warning("Kan bestand %s niet lezen: %s", f.name, e)
                bestanden.append({
                    "bestandsnaam": f.name,
                    "grootte_kb": round(f.stat().st_size / 1024, 1),
                    "fout": str(e),
                })

    return {"bestanden": bestanden, "totaal": len(bestanden)}


@admin_router.post("/upload")
async def admin_upload_bestand(
    bestand: UploadFile = File(...),
):
    """Upload een GPKG of GeoJSON bestand naar data-upload/."""
    import fiona

    # Valideer bestandstype
    allowed = {'.gpkg', '.geojson', '.json'}
    suffix = Path(bestand.filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(400, f"Bestandstype '{suffix}' niet toegestaan. Gebruik: {', '.join(allowed)}")

    # Veilige bestandsnaam (geen pad-traversal)
    safe_name = Path(bestand.filename).name
    if not safe_name or safe_name.startswith('.'):
        raise HTTPException(400, "Ongeldige bestandsnaam")

    filepath = DATA_UPLOAD_DIR / safe_name

    # Maximale bestandsgrootte: 50MB
    MAX_SIZE = 50 * 1024 * 1024
    contents = await bestand.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(413, f"Bestand te groot (max {MAX_SIZE // (1024*1024)}MB)")

    # Opslaan
    DATA_UPLOAD_DIR.mkdir(exist_ok=True)
    filepath.write_bytes(contents)

    # Valideer dat fiona het kan lezen
    try:
        layers = fiona.listlayers(str(filepath))
        with fiona.open(str(filepath), layer=layers[0]) as src:
            meta = {
                "bestandsnaam": safe_name,
                "grootte_kb": round(len(contents) / 1024, 1),
                "layers": layers,
                "features": len(src),
                "crs": str(src.crs) if src.crs else None,
                "geometry_type": src.schema.get("geometry", "onbekend"),
            }
    except Exception as e:
        # Ongeldig bestand: verwijder weer
        filepath.unlink(missing_ok=True)
        raise HTTPException(400, f"Bestand kon niet geopend worden als geo-bestand: {str(e)}")

    logger.info("Bestand geüpload: %s (%d features, %s)",
                safe_name, meta["features"], meta["crs"])
    return {"status": "geüpload", **meta}


# ============================================================================
# RD → WGS84 transformatie (EPSG:28992 → EPSG:4326)
# ============================================================================

def _transform_rd_to_wgs84(geojson: dict) -> dict:
    """
    Transformeer GeoJSON coördinaten van Rijksdriehoek (EPSG:28992) naar WGS84 (EPSG:4326).
    Gebruikt de benaderingsformules van Schreutelkamp & Strang (2009).
    Nauwkeurigheid: ~1m (voldoende voor visualisatie).
    """
    # Referentiepunt Amersfoort
    X0 = 155000.0
    Y0 = 463000.0
    PHI0 = 52.15517440
    LAM0 = 5.38720621

    # Coëfficiënten latitude (Kp)
    Kp = [
        (0, 1, 3235.65389),
        (2, 0, -32.58297),
        (0, 2, -0.24750),
        (2, 1, -0.84978),
        (0, 3, -0.06550),
        (2, 2, -0.01709),
        (1, 0, -0.00738),
        (4, 0, 0.00530),
        (2, 3, -0.00039),
        (4, 1, 0.00033),
        (1, 1, -0.00012),
    ]

    # Coëfficiënten longitude (Kq)
    Kq = [
        (1, 0, 5260.52916),
        (1, 1, 105.94684),
        (1, 2, 2.45656),
        (3, 0, -0.81885),
        (1, 3, 0.05594),
        (3, 1, -0.05607),
        (0, 1, 0.01199),
        (3, 2, -0.00256),
        (1, 4, 0.00128),
        (0, 2, 0.00022),
        (2, 0, -0.00022),
        (5, 0, 0.00026),
    ]

    def rd_to_wgs84(x: float, y: float):
        dx = 1e-5 * (x - X0)
        dy = 1e-5 * (y - Y0)

        phi = PHI0
        for p, q, k in Kp:
            phi += k * (dx ** p) * (dy ** q) / 3600.0

        lam = LAM0
        for p, q, k in Kq:
            lam += k * (dx ** p) * (dy ** q) / 3600.0

        return [round(lam, 7), round(phi, 7)]

    def transform_coords(coords):
        """Recursief coördinaten transformeren."""
        if not coords:
            return coords
        # Diepste niveau: [x, y]
        if isinstance(coords[0], (int, float)):
            return rd_to_wgs84(coords[0], coords[1])
        return [transform_coords(c) for c in coords]

    # Features transformeren
    features = geojson.get("features", [])
    for feature in features:
        geom = feature.get("geometry")
        if geom and "coordinates" in geom:
            geom["coordinates"] = transform_coords(geom["coordinates"])

    return geojson

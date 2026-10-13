"""
Router: 3D BAG Panden
POST /api/3dbag/buildings — On-demand 3D gebouwmodellen via 3DBAG REST API

Architectuur:
1. Frontend stuurt gebied_ids (max 3) + optionele indicator_uuid
2. Backend berekent BBOX via PostGIS ST_Envelope(ST_Collect)
3. REST API call naar api.3dbag.nl (CityJSONFeatures met LoD 0 footprint + hoogte-attributen)
4. Decode CityJSON geometrie naar GeoJSON polygonen (RD New → WGS84 via pyproj)
5. Drielaagse kleurstrategie: bouwjaar → energielabel → buurt-indicator
6. Retourneert standaard GeoJSON FeatureCollection naar deck.gl

Copyright: © 3DBAG by 3DGI and TU Delft (CC BY 4.0)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

try:
    from pyproj import Transformer

    _rd_to_wgs84 = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
except ImportError:  # pragma: no cover
    Transformer = None
    _rd_to_wgs84 = None
from omnitwin.database import get_db
from typing import List, Optional
import requests
import logging

from omnitwin.services.logging_service import AppLogger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/3dbag", tags=["3D BAG Panden"])

# ============================================================================
# Request / Response Models
# ============================================================================


class BAG3DRequest(BaseModel):
    gebied_ids: List[str] = Field(
        ..., min_length=1, max_length=3, description="CBS buurt-IDs (bijv. BU00800000). Maximaal 3."
    )
    indicator_uuid: Optional[str] = Field(None, description="Actieve indicator UUID voor kleurstrategie")


# ============================================================================
# Kleurstrategie constanten
# ============================================================================

# Mode A: Bouwjaar (direct uit 3DBAG response)
BOUWJAAR_KLEUR = [
    (1900, "#8B0000"),  # Voor 1900 — donkerrood
    (1945, "#c0392b"),  # 1900–1945 — rood
    (1960, "#e74c3c"),  # 1945–1960 — lichtrood
    (1975, "#e67e22"),  # 1960–1975 — oranje
    (1990, "#f1c40f"),  # 1975–1990 — geel
    (2005, "#2ecc71"),  # 1990–2005 — groen
    (9999, "#27ae60"),  # Na 2005 — donkergroen
]


def bouwjaar_kleur(jaar) -> str:
    """Bepaal kleur op basis van bouwjaar."""
    if jaar is None:
        return "#888888"
    try:
        jaar = int(jaar)
    except (ValueError, TypeError):
        return "#888888"
    for drempel, kleur in BOUWJAAR_KLEUR:
        if jaar <= drempel:
            return kleur
    return "#27ae60"


# Mode B: Energielabel (toekomstig — lookup in ep_online tabel)
ENERGIELABEL_KLEUR = {
    "A+++": "#1a6b1a",
    "A++": "#1e8a1e",
    "A+": "#2eb82e",
    "A": "#3dce3d",
    "B": "#a8d450",
    "C": "#f0d000",
    "D": "#f0a000",
    "E": "#e06000",
    "F": "#c83000",
    "G": "#a00000",
}

# Indicator codes die pand-niveau kleuring activeren
BOUWJAAR_INDICATOR_CODES = {"gemiddeld_bouwjaar", "pct_voor_1945"}
ENERGIELABEL_INDICATOR_CODES = {"pct_energielabel", "gem_energielabel"}

# ============================================================================
# BBOX berekening
# ============================================================================


def get_bbox_for_gebieden(db: Session, gebied_ids: List[str]) -> dict:
    """
    Berekent de bounding box van een set gebieden via PostGIS.
    Retourneert BBOX in EPSG:28992 (RD New) voor de 3DBAG API call.
    """
    result = db.execute(
        text("""
        SELECT 
            ST_XMin(env) as minx,
            ST_YMin(env) as miny,
            ST_XMax(env) as maxx,
            ST_YMax(env) as maxy
        FROM (
            SELECT ST_Envelope(ST_Collect(geom)) AS env
            FROM gebieden
            WHERE id = ANY(:ids)
              AND geom IS NOT NULL
        ) sub
    """),
        {"ids": gebied_ids},
    ).fetchone()

    if not result or result.minx is None:
        raise HTTPException(status_code=404, detail="Geen gebieden gevonden voor opgegeven IDs")

    return {
        "minx": result.minx,
        "miny": result.miny,
        "maxx": result.maxx,
        "maxy": result.maxy,
    }


# ============================================================================
# 3DBAG REST API & CityJSON Decoding (EPSG:28992 -> EPSG:4326)
# ============================================================================

REST_API_BASE = "https://api.3dbag.nl/collections/pand/items"
REST_API_TIMEOUT = 25  # seconden per request (verruimd voor grotere/dichtbevolkte buurten)
MAX_PAGES = 30  # Maximaal aantal pagina's (volledige wijk ophalen)


def _decode_cityjson_geometry(boundaries: list, vertices: list, scale: list, translate: list) -> list:
    """
    Converteert CityJSON boundary indices recursief naar GeoJSON WGS84 polygon rings.

    CityJSON vertices zijn integers:
        x_rd = vertex[0] * scale[0] + translate[0]
        y_rd = vertex[1] * scale[1] + translate[1]
    Daarna transformeren naar WGS84 (EPSG:4326) voor Deck.gl.
    """
    if not boundaries:
        return []

    # Als het eerste element een integer is, is dit een vertex ring
    if isinstance(boundaries[0], int):
        coords = []
        for idx in boundaries:
            if idx < len(vertices):
                v = vertices[idx]
                x_rd = v[0] * scale[0] + translate[0]
                y_rd = v[1] * scale[1] + translate[1]
                if _rd_to_wgs84 is not None:
                    lon, lat = _rd_to_wgs84.transform(x_rd, y_rd)
                    coords.append([round(lon, 7), round(lat, 7)])
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])
        return coords

    # Recursief verwerken voor diepere geneste arrays (MultiSurface / Surface / Rings)
    return [_decode_cityjson_geometry(child, vertices, scale, translate) for child in boundaries]


def _extract_polygon_rings(decoded: list) -> list:
    """
    Normaliseert een willekeurige diepte van CityJSON decoded boundaries naar
    een valide GeoJSON Polygon coordinate structuur (lijst van ringen: [ [ [lon, lat], ... ] ]).
    """
    if not decoded or not isinstance(decoded, list):
        return []

    # Navigeer omlaag tot we een lijst van ringen (Surface) vinden
    curr = decoded
    while isinstance(curr, list) and len(curr) > 0:
        if isinstance(curr[0], list) and len(curr[0]) > 0:
            first_elem = curr[0][0]
            # Als first_elem een getal is: curr is één ring [ [lon, lat], ... ] -> wrap in surface
            if isinstance(first_elem, (int, float)):
                return [curr]
            # Als first_elem een punt [lon, lat] is: curr is een Surface (lijst van ringen)
            if isinstance(first_elem, list) and len(first_elem) >= 2 and isinstance(first_elem[0], (int, float)):
                return curr

        # Dieper afdalen (bij MultiSurface of Solid)
        curr = curr[0]

    return []


def _cityjson_feature_to_geojson(feature: dict, default_transform: dict = None) -> list:
    """
    Converteert een CityJSONFeature naar een lijst van GeoJSON features.
    Haalt LoD 0 footprint / LoD 1.2 geometrie en relevante pand-attributen op.
    """
    # Transform kan direct op feature staan (CityJSONSeq/CityJSONFeature) of fallback
    transform = (
        feature.get("transform")
        or (feature.get("metadata", {}).get("transform") if isinstance(feature.get("metadata"), dict) else None)
        or default_transform
        or {}
    )
    scale = transform.get("scale", [0.001, 0.001, 0.001])
    translate = transform.get("translate", [0, 0, 0])
    vertices = feature.get("vertices", [])
    city_objects = feature.get("CityObjects", {})

    geojson_features = []

    for obj_id, obj in city_objects.items():
        # Filter op Building of BuildingPart type of root pand object
        obj_type = obj.get("type", "")
        if obj_type not in ("Building", "BuildingPart") and not obj_id.startswith("NL.IMBAG.Pand."):
            continue

        attrs = obj.get("attributes", {})

        # Zoek footprint geometrie (LoD 0 footprint heeft voorkeur, anders LoD 1.2 / 2.2)
        footprint_geom = None
        for geom in obj.get("geometry", []):
            if geom.get("type") in ("MultiSurface", "CompositeSurface", "Solid", "MultiSolid"):
                if footprint_geom is None or str(geom.get("lod", "")) in ("0", "0.0", "1.2"):
                    footprint_geom = geom

        if not footprint_geom:
            continue

        boundaries = footprint_geom.get("boundaries", [])
        if not boundaries:
            continue

        try:
            decoded = _decode_cityjson_geometry(boundaries, vertices, scale, translate)
            coords = _extract_polygon_rings(decoded)

            if not coords:
                continue

            # Hoogtebepaling uit 3DBAG attributen (dakhoogte 50 percentile of max)
            dak_h = attrs.get("b3_h_dak_50p") or attrs.get("b3_h_dak_max") or attrs.get("h_dak")
            maaiveld_h = attrs.get("b3_h_maaiveld") or attrs.get("h_maaiveld") or 0.0

            geojson_features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": coords},
                    "properties": {
                        "identificatie": attrs.get("identificatie", obj_id),
                        "oorspronkelijkbouwjaar": attrs.get("oorspronkelijkbouwjaar") or attrs.get("bouwjaar"),
                        "status": attrs.get("status"),
                        "b3_h_dak_50p": dak_h,
                        "b3_h_maaiveld": maaiveld_h,
                    },
                }
            )
        except Exception as err:
            logger.debug(f"Kon CityJSON object {obj_id} niet decoden: {err}")
            continue

    return geojson_features


def fetch_buildings_from_api(bbox: dict, max_pages: int = MAX_PAGES) -> dict:
    """
    Haalt gebouwen op via de 3DBAG REST API (api.3dbag.nl).
    Ondersteunt BBOX querying, limit parameter en paginering via links.next.
    """
    current_url = REST_API_BASE
    current_params = {
        "bbox": f"{bbox['minx']:.1f},{bbox['miny']:.1f},{bbox['maxx']:.1f},{bbox['maxy']:.1f}",
        "limit": 500,  # Haal direct tot 500 panden per request op voor complete buurten
    }

    all_features = []
    page = 0

    try:
        while current_url and page < max_pages:
            page += 1
            response = requests.get(current_url, params=current_params if page == 1 else None, timeout=REST_API_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            # Root transform als fallback voor alle features
            root_transform = data.get("transform") or (
                data.get("metadata", {}).get("transform") if isinstance(data.get("metadata"), dict) else None
            )

            # Verwerk features
            raw_features = data.get("features", [])
            for raw_feat in raw_features:
                all_features.extend(_cityjson_feature_to_geojson(raw_feat, default_transform=root_transform))

            # Zoek 'next' link voor volgende pagina als er meer data is
            next_url = None
            for link in data.get("links", []):
                if link.get("rel") == "next" and link.get("href"):
                    next_url = link["href"]
                    break

            if next_url and next_url != current_url and len(all_features) < 3000:
                current_url = next_url
            else:
                break

    except requests.exceptions.Timeout:
        AppLogger.warning("3DBAG REST API timeout — service reageert traag", category="KAART")
        # Als we al features hebben opgehaald, retourneren we die ipv 503
        if not all_features:
            raise HTTPException(
                status_code=503,
                detail="3DBAG service (TU Delft) is tijdelijk overbelast. Probeer het over enkele ogenblikken opnieuw.",
            )
    except requests.exceptions.RequestException as e:
        AppLogger.error(f"3DBAG REST API fout: {e}", category="KAART")
        if not all_features:
            raise HTTPException(status_code=503, detail="3DBAG service (TU Delft) is tijdelijk niet bereikbaar.")

    return {"type": "FeatureCollection", "features": all_features}


# ============================================================================
# Kleur-verrijking
# ============================================================================


def get_indicator_code(db: Session, indicator_uuid: str) -> Optional[str]:
    """Haal de indicator code op voor kleurmode-detectie."""
    result = db.execute(text("SELECT code FROM indicatoren WHERE uuid = :uuid"), {"uuid": indicator_uuid}).fetchone()
    return result.code if result else None


def enrich_features_with_color(
    features: list, db: Session, indicator_uuid: Optional[str], gebied_ids: List[str]
) -> list:
    """
    Verrijkt elke feature met indicator_color op basis van drielaagse strategie.
    Mode A (bouwjaar) → Mode B (energielabel) → Mode C (buurt spatial fallback)
    """
    kleur_mode = "geen"
    indicator_code = None

    if indicator_uuid:
        indicator_code = get_indicator_code(db, indicator_uuid)

    # Detecteer kleur-mode
    if indicator_code and indicator_code in BOUWJAAR_INDICATOR_CODES:
        kleur_mode = "bouwjaar"
    elif indicator_code and indicator_code in ENERGIELABEL_INDICATOR_CODES:
        kleur_mode = "energielabel"
    elif indicator_uuid:
        kleur_mode = "buurt"

    # Mode C: batch buurt-kleuren ophalen (één query, niet per pand)
    buurt_kleuren = {}
    if kleur_mode == "buurt":
        try:
            rows = db.execute(
                text("""
                SELECT DISTINCT ON (g.id) g.id as gebied_id, gd.waarde
                FROM gebieden g
                JOIN gebied_data gd ON gd.gebied_id = g.id
                WHERE gd.indicator_uuid = CAST(:ind AS uuid)
                  AND g.id = ANY(:ids)
                  AND COALESCE(gd.scenario_id, 'current') = 'current'
                ORDER BY g.id, gd.jaar DESC NULLS LAST, gd.datum DESC NULLS LAST
            """),
                {"ind": indicator_uuid, "ids": gebied_ids},
            ).fetchall()
            buurt_kleuren = {r.gebied_id: {"waarde": float(r.waarde) if r.waarde else None} for r in rows}

            # Bereken kleuren via simple gradient (groen → rood)
            waarden = [v["waarde"] for v in buurt_kleuren.values() if v["waarde"] is not None]
            if waarden:
                min_val, max_val = min(waarden), max(waarden)
                for gid, info in buurt_kleuren.items():
                    if info["waarde"] is not None and max_val > min_val:
                        norm = (info["waarde"] - min_val) / (max_val - min_val)
                        # Groen (lage score) → Rood (hoge score) gradient
                        r = int(min(255, norm * 2 * 255))
                        g = int(min(255, (1 - norm) * 2 * 255))
                        info["kleur"] = f"#{r:02x}{g:02x}50"
                    elif info["waarde"] is not None and max_val == min_val:
                        # Bug #42 Fix: Neutrale kleur (Geo Gold) als er maar 1 buurt/waarde is
                        info["kleur"] = "#fbbf24"
                    else:
                        info["kleur"] = "#888888"
        except Exception as e:
            AppLogger.warning(f"Buurt-kleur query fout: {e}", category="KAART")
            buurt_kleuren = {}

    # Verrijk elke feature
    for feature in features:
        props = feature.get("properties", {})

        if kleur_mode == "bouwjaar":
            bouwjaar = props.get("oorspronkelijkbouwjaar")
            props["indicator_color"] = bouwjaar_kleur(bouwjaar)
            props["indicator_waarde"] = bouwjaar

        elif kleur_mode == "energielabel":
            props["indicator_color"] = "#888888"
            props["indicator_waarde"] = None

        elif kleur_mode == "buurt":
            if len(buurt_kleuren) == 1:
                enige = list(buurt_kleuren.values())[0]
                props["indicator_color"] = enige["kleur"]
                props["indicator_waarde"] = enige["waarde"]
            elif len(buurt_kleuren) > 1:
                eerste = list(buurt_kleuren.values())[0]
                props["indicator_color"] = eerste["kleur"]
                props["indicator_waarde"] = eerste["waarde"]
            else:
                props["indicator_color"] = "#888888"
                props["indicator_waarde"] = None

        else:
            props["indicator_color"] = "#888888"
            props["indicator_waarde"] = None

        props["kleur_mode"] = kleur_mode

    return features


# ============================================================================
# Endpoint
# ============================================================================


@router.post("/buildings")
def get_3d_buildings(request: BAG3DRequest, db: Session = Depends(get_db)):
    """
    Haalt 3D gebouwen op voor maximaal 3 geselecteerde gebieden.
    Retourneert GeoJSON FeatureCollection met hoogte-attributen en indicator-kleur.

    © 3DBAG by 3DGI and TU Delft (CC BY 4.0)
    """
    AppLogger.info(f"3DBAG request voor {len(request.gebied_ids)} gebieden: {request.gebied_ids}", category="KAART")

    # Stap 1: BBOX berekenen via PostGIS
    bbox = get_bbox_for_gebieden(db, request.gebied_ids)
    AppLogger.info(
        f"3DBAG BBOX (RD): {bbox['minx']:.0f},{bbox['miny']:.0f} → {bbox['maxx']:.0f},{bbox['maxy']:.0f}",
        category="KAART",
    )

    # Stap 2: 3DBAG REST API ophalen
    geojson = fetch_buildings_from_api(bbox)
    features = geojson.get("features", [])
    AppLogger.info(f"3DBAG {len(features)} panden opgehaald van REST API", category="KAART")

    if not features:
        raise HTTPException(status_code=404, detail="Geen 3D panden gevonden in het geselecteerde gebied op 3DBAG.")

    # Stap 3: Kleurverrijking
    enriched = enrich_features_with_color(
        features=features,
        db=db,
        indicator_uuid=request.indicator_uuid,
        gebied_ids=request.gebied_ids,
    )

    return {
        "type": "FeatureCollection",
        "features": enriched,
        "metadata": {
            "bbox_rd": bbox,
            "panden_count": len(enriched),
            "kleur_mode": enriched[0]["properties"].get("kleur_mode", "geen") if enriched else "geen",
            "copyright": "© 3DBAG by 3DGI and TU Delft (CC BY 4.0)",
        },
    }


@router.get("/health")
def bag3d_health():
    """Health check voor 3D BAG service."""
    return {"status": "healthy", "service": "3D BAG Panden API (api.3dbag.nl)"}

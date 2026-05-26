"""
Router: 3D BAG Panden
POST /api/3dbag/buildings — On-demand 3D gebouwmodellen via 3DBAG WFS

Architectuur:
1. Frontend stuurt gebied_ids (max 3) + optionele indicator_uuid
2. Backend berekent BBOX via PostGIS ST_Envelope(ST_Collect)
3. WFS call naar data.3dbag.nl (LoD 1.2 footprints met hoogte-attributen)
4. Drielaagse kleurstrategie: bouwjaar → energielabel → buurt-indicator
5. Retourneert standaard GeoJSON FeatureCollection naar deck.gl

Copyright: © 3DBAG by 3DGI and TU Delft (CC BY 4.0)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database import get_db
from typing import List, Optional
import requests
import logging

from services.logging_service import AppLogger

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/3dbag",
    tags=["3D BAG Panden"]
)

# ============================================================================
# Request / Response Models
# ============================================================================

class BAG3DRequest(BaseModel):
    gebied_ids: List[str] = Field(..., min_length=1, max_length=3,
        description="CBS buurt-IDs (bijv. BU00800000). Maximaal 3.")
    indicator_uuid: Optional[str] = Field(None,
        description="Actieve indicator UUID voor kleurstrategie")

# ============================================================================
# Kleurstrategie constanten
# ============================================================================

# Mode A: Bouwjaar (direct uit 3DBAG WFS response)
BOUWJAAR_KLEUR = [
    (1900, "#8B0000"),   # Voor 1900 — donkerrood
    (1945, "#c0392b"),   # 1900–1945 — rood
    (1960, "#e74c3c"),   # 1945–1960 — lichtrood
    (1975, "#e67e22"),   # 1960–1975 — oranje
    (1990, "#f1c40f"),   # 1975–1990 — geel
    (2005, "#2ecc71"),   # 1990–2005 — groen
    (9999, "#27ae60"),   # Na 2005 — donkergroen
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
    "A+++": "#1a6b1a", "A++": "#1e8a1e", "A+": "#2eb82e",
    "A": "#3dce3d", "B": "#a8d450", "C": "#f0d000",
    "D": "#f0a000", "E": "#e06000", "F": "#c83000",
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
    Retourneert BBOX in EPSG:28992 (RD New) voor de WFS call.
    """
    result = db.execute(text("""
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
    """), {"ids": gebied_ids}).fetchone()

    if not result or result.minx is None:
        raise HTTPException(status_code=404, detail="Geen gebieden gevonden voor opgegeven IDs")

    return {
        "minx": result.minx,
        "miny": result.miny,
        "maxx": result.maxx,
        "maxy": result.maxy,
    }

# ============================================================================
# 3DBAG WFS ophalen
# ============================================================================

WFS_BASE_URL = "https://data.3dbag.nl/api/BAG3D/wfs"
WFS_TIMEOUT = 15  # seconden

def fetch_buildings_from_wfs(bbox: dict, limit: int = 1000) -> dict:
    """
    Haalt gebouwen op via de 3DBAG WFS (LoD 1.2) als standaard GeoJSON.
    Input BBOX in EPSG:28992, output geometrie in EPSG:4326.
    """
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeName": "BAG3D:lod12",
        "outputFormat": "application/json",
        "bbox": f"{bbox['minx']},{bbox['miny']},{bbox['maxx']},{bbox['maxy']},EPSG:28992",
        "srsName": "EPSG:4326",
        "count": str(limit),
    }

    try:
        response = requests.get(WFS_BASE_URL, params=params, timeout=WFS_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="3DBAG WFS timeout — probeer het later opnieuw")
    except requests.exceptions.RequestException as e:
        AppLogger.error(f"WFS fout: {e}", category="KAART")
        raise HTTPException(status_code=502, detail=f"3DBAG WFS niet bereikbaar: {str(e)}")

# ============================================================================
# Kleur-verrijking
# ============================================================================

def get_indicator_code(db: Session, indicator_uuid: str) -> Optional[str]:
    """Haal de indicator code op voor kleurmode-detectie."""
    result = db.execute(text(
        "SELECT code FROM indicatoren WHERE uuid = :uuid"
    ), {"uuid": indicator_uuid}).fetchone()
    return result.code if result else None


def enrich_features_with_color(
    features: list,
    db: Session,
    indicator_uuid: Optional[str],
    gebied_ids: List[str]
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
            rows = db.execute(text("""
                SELECT g.id as gebied_id, gd.waarde
                FROM gebieden g
                JOIN gebied_data gd ON gd.gebied_id = g.id
                WHERE gd.indicator_uuid = CAST(:ind AS uuid)
                  AND g.id = ANY(:ids)
                ORDER BY gd.jaar DESC
            """), {"ind": indicator_uuid, "ids": gebied_ids}).fetchall()
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
            # Toekomstig: lookup in ep_online tabel op basis van pand-ID
            # Voor nu: fallback naar grijs
            pand_id = props.get("identificatie", "")
            props["indicator_color"] = "#888888"
            props["indicator_waarde"] = None

        elif kleur_mode == "buurt":
            # Spatial match: pand in welke buurt? Gebruik BBOX/centroïd heuristiek
            # Simpele aanpak voor PoC: alle panden in de BBOX krijgen dezelfde kleur
            # als er slechts 1 buurt is, anders grijs (nader uit te werken)
            if len(buurt_kleuren) == 1:
                enige = list(buurt_kleuren.values())[0]
                props["indicator_color"] = enige["kleur"]
                props["indicator_waarde"] = enige["waarde"]
            elif len(buurt_kleuren) > 1:
                # Bij meerdere buurten: pakken we de eerste als fallback
                # Ideaal: PostGIS spatial join per pand
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
async def get_3d_buildings(
    request: BAG3DRequest,
    db: Session = Depends(get_db)
):
    """
    Haalt 3D gebouwen op voor maximaal 3 geselecteerde gebieden.
    Retourneert GeoJSON FeatureCollection met hoogte-attributen en indicator-kleur.

    © 3DBAG by 3DGI and TU Delft (CC BY 4.0)
    """
    AppLogger.info(f"3DBAG request voor {len(request.gebied_ids)} gebieden: {request.gebied_ids}", category="KAART")

    # Stap 1: BBOX berekenen via PostGIS
    bbox = get_bbox_for_gebieden(db, request.gebied_ids)
    AppLogger.info(f"3DBAG BBOX (RD): {bbox['minx']:.0f},{bbox['miny']:.0f} → {bbox['maxx']:.0f},{bbox['maxy']:.0f}", category="KAART")

    # Stap 2: WFS ophalen
    geojson = fetch_buildings_from_wfs(bbox)
    features = geojson.get("features", [])
    AppLogger.info(f"3DBAG {len(features)} panden opgehaald van WFS", category="KAART")

    if not features:
        raise HTTPException(status_code=404, detail="Geen panden gevonden in het geselecteerde gebied")

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
        }
    }


@router.get("/health")
async def bag3d_health():
    """Health check voor 3D BAG service."""
    return {"status": "healthy", "service": "3D BAG Panden API"}

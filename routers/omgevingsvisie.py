"""
Omgevingsvisie Deelgebieden API Router
=======================================
Endpoints voor de Omgevingsvisie deelgebieden als interactief selectieframe.
Gebruikers kunnen deelgebieden aanklikken om automatisch alle onderliggende
CBS-buurten te selecteren (via -10m inward buffer strategie).

Endpoints:
- GET /api/omgevingsvisie/deelgebieden           → GeoJSON van alle deelgebieden
- GET /api/omgevingsvisie/deelgebieden/{id}/buurten → Buurt-IDs binnen deelgebied
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from src.database import get_db

router = APIRouter(
    prefix="/api/omgevingsvisie",
    tags=["Omgevingsvisie Deelgebieden"]
)


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/deelgebieden")
async def get_deelgebieden(db: Session = Depends(get_db)):
    """
    Haal alle omgevingsvisie-deelgebieden op als GeoJSON FeatureCollection.
    Geometrie in WGS84 (EPSG:4326) voor directe rendering in deck.gl.

    **Gebruik (frontend):**
    ```javascript
    const res = await fetch('/api/omgevingsvisie/deelgebieden');
    const geojson = await res.json();
    // Gebruik als data voor een GeoJsonLayer overlay
    ```
    """
    query = text("""
        SELECT
            id,
            naam,
            deelgebied,
            ST_AsGeoJSON(geom_wgs84)::json as geometry,
            ST_Area(geom) / 1e6 as oppervlakte_km2
        FROM omgevingsvisie_deelgebieden
        ORDER BY id
    """)

    try:
        rows = db.execute(query).fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "id": row.id,
            "geometry": row.geometry,
            "properties": {
                "id": row.id,
                "naam": row.naam,
                "deelgebied": row.deelgebied,
                "oppervlakte_km2": round(row.oppervlakte_km2, 1)
            }
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "totaal": len(features),
            "bron": "Gemeente Súdwest-Fryslân — Omgevingsvisie",
            "crs": "EPSG:4326"
        }
    }


@router.get("/deelgebieden/{deelgebied_id}/buurten")
async def get_buurten_in_deelgebied(
    deelgebied_id: int,
    buffer_m: int = Query(-10, description="Inward buffer in meters (negatief = erosie)"),
    db: Session = Depends(get_db)
):
    """
    Haal CBS-buurten op die binnen een omgevingsvisie-deelgebied vallen.

    Gebruikt een **inward buffer** (-10m default) om grensoverlap te voorkomen:
    aangrenzende buurten op de grens van twee deelgebieden worden niet dubbel
    geselecteerd dankzij de erosie van het selectiepolygoon.

    **Args:**
    - `deelgebied_id`: ID van het deelgebied (1-6)
    - `buffer_m`: Buffer in meters (default -10, negatief = inward/erosie)

    **Returns:**
    - `buurten`: Lijst van {id, naam} objecten
    - `totaal`: Aantal gevonden buurten
    - `deelgebied`: Naam van het geselecteerde deelgebied

    **Gebruik (frontend):**
    ```javascript
    const res = await fetch(`/api/omgevingsvisie/deelgebieden/${id}/buurten`);
    const { buurten } = await res.json();
    buurten.forEach(b => state.selectedGebiedIds.add(b.id));
    ```
    """
    # Controleer of deelgebied bestaat
    check = db.execute(
        text("SELECT naam, deelgebied FROM omgevingsvisie_deelgebieden WHERE id = :id"),
        {"id": deelgebied_id}
    ).fetchone()

    if not check:
        raise HTTPException(
            status_code=404,
            detail=f"Deelgebied met ID {deelgebied_id} niet gevonden (beschikbaar: 1-6)"
        )

    # Buffer moet negatief zijn (inward), forceer dit
    buffer_val = -abs(buffer_m) if buffer_m != 0 else -10

    # Spatial query: buurten die intersecten met gebufferd deelgebied
    query = text("""
        SELECT g.id, g.naam
        FROM gebieden g
        JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
        WHERE gt.code = 'CBS_BUURT'
          AND g.gemeente_code = '1900'
          AND g.actief = true
          AND ST_Intersects(
                g.geom,
                ST_Buffer(
                    (SELECT geom FROM omgevingsvisie_deelgebieden WHERE id = :deelgebied_id),
                    :buffer
                )
          )
        ORDER BY g.naam
    """)

    try:
        rows = db.execute(query, {
            "deelgebied_id": deelgebied_id,
            "buffer": buffer_val
        }).fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Spatial query error: {str(e)}")

    buurten = [{"id": row.id, "naam": row.naam} for row in rows]

    return {
        "deelgebied": check.deelgebied,
        "deelgebied_naam": check.naam,
        "buffer_m": buffer_val,
        "buurten": buurten,
        "totaal": len(buurten)
    }

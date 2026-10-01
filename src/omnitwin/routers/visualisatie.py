"""
Visualisatie API Router
Manages color palettes, visualization profiles, and config for the map frontend.
Based on: docs/visual/kaartkleuring_visualisatie_d_omn_itwin.md (v1.1)
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from omnitwin.database import get_db
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
import os

router = APIRouter(prefix="/api/visualisatie", tags=["Visualisatie"])

# Beheer-routes (/api/visualisatie/admin/*): apart router met admin-check (#65)
from omnitwin.routers.auth import vereis_admin

admin_router = APIRouter(prefix="/api/visualisatie/admin", tags=["Visualisatie"], dependencies=[Depends(vereis_admin)])

# ============================================================================
# Pydantic Models
# ============================================================================
class ColorSchemaBase(BaseModel):
    id: int
    naam: str
    beschrijving: Optional[str] = None
    colors: dict
    palette_type: Optional[str] = "sequential"
    classificatie: Optional[str] = "quantile"
    klassen: Optional[int] = 5
    nodata_kleur: Optional[str] = "#d1d5db"
    is_actief: bool = True

class ColorSchemaCreate(BaseModel):
    naam: str
    beschrijving: Optional[str] = None
    colors: dict
    palette_type: str = "sequential"
    classificatie: str = "quantile"
    klassen: int = 5
    nodata_kleur: str = "#d1d5db"

class ColorSchemaUpdate(BaseModel):
    naam: Optional[str] = None
    beschrijving: Optional[str] = None
    colors: Optional[dict] = None
    palette_type: Optional[str] = None
    classificatie: Optional[str] = None
    klassen: Optional[int] = None
    nodata_kleur: Optional[str] = None
    is_actief: Optional[bool] = None

class VisualisatieProfiel(BaseModel):
    id: int
    naam: str
    beschrijving: Optional[str] = None
    indicator_pattern: Optional[str] = None
    color_schema_id: Optional[int] = None
    classificatie_override: Optional[str] = None
    klassen_override: Optional[int] = None
    midpoint_waarde: Optional[float] = None
    is_actief: bool = True

class ProfielCreate(BaseModel):
    naam: str
    beschrijving: Optional[str] = None
    indicator_pattern: Optional[str] = None
    color_schema_id: Optional[int] = None
    classificatie_override: Optional[str] = None
    klassen_override: Optional[int] = None
    midpoint_waarde: Optional[float] = None

class ProfielUpdate(BaseModel):
    naam: Optional[str] = None
    beschrijving: Optional[str] = None
    indicator_pattern: Optional[str] = None
    color_schema_id: Optional[int] = None
    classificatie_override: Optional[str] = None
    klassen_override: Optional[int] = None
    midpoint_waarde: Optional[float] = None
    is_actief: Optional[bool] = None

# ============================================================================
# Public Endpoints (No Auth - Used by Map Frontend)
# ============================================================================

@router.get("/paletten")
def get_paletten(db: Session = Depends(get_db)):
    """Get all active color palettes. Public endpoint for map frontend."""
    result = db.execute(text("""
        SELECT id, naam, beschrijving, colors, palette_type,
               classificatie, klassen, nodata_kleur, is_actief
        FROM color_schemas
        WHERE is_actief = true
        ORDER BY id
    """))
    
    paletten = []
    for row in result.mappings():
        paletten.append({
            "id": row["id"],
            "naam": row["naam"],
            "beschrijving": row["beschrijving"],
            "colors": row["colors"],
            "palette_type": row["palette_type"],
            "classificatie": row["classificatie"],
            "klassen": row["klassen"],
            "nodata_kleur": row["nodata_kleur"],
            "is_actief": row["is_actief"]
        })
    
    return {"paletten": paletten, "total": len(paletten)}

@router.get("/config/{indicator_uuid}")
def get_indicator_viz_config(indicator_uuid: UUID, db: Session = Depends(get_db)):
    """Get the visualization config for a specific indicator.
    Resolves: indicator → color_schema → palette config.
    Falls back to profile pattern matching if no direct schema assigned.
    """
    # 1. Check if indicator has a direct color_schema assignment
    result = db.execute(text("""
        SELECT i.uuid, i.naam, i.score_type, i.color_schema_id,
               cs.naam as schema_naam, cs.colors, cs.palette_type,
               cs.classificatie, cs.klassen, cs.nodata_kleur
        FROM indicatoren i
        LEFT JOIN color_schemas cs ON i.color_schema_id = cs.id
        WHERE i.uuid = :uuid
    """), {"uuid": str(indicator_uuid)}).mappings().first()
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Indicator {indicator_uuid} not found")
    
    # If indicator has a direct schema assigned, use it
    if result["color_schema_id"]:
        return {
            "indicator_uuid": result["uuid"],
            "indicator_naam": result["naam"],
            "score_type": result["score_type"],
            "source": "direct",
            "palette": {
                "id": result["color_schema_id"],
                "naam": result["schema_naam"],
                "colors": result["colors"],
                "palette_type": result["palette_type"],
                "classificatie": result["classificatie"],
                "klassen": result["klassen"],
                "nodata_kleur": result["nodata_kleur"]
            }
        }
    
    # 2. Fallback: match via visualisatie_profielen pattern
    profiel = db.execute(text("""
        SELECT vp.*, cs.naam as schema_naam, cs.colors, cs.palette_type,
               cs.classificatie as schema_classificatie, cs.klassen as schema_klassen,
               cs.nodata_kleur
        FROM visualisatie_profielen vp
        LEFT JOIN color_schemas cs ON vp.color_schema_id = cs.id
        WHERE vp.is_actief = true
          AND LOWER(:naam) LIKE LOWER(vp.indicator_pattern)
        ORDER BY LENGTH(vp.indicator_pattern) DESC
        LIMIT 1
    """), {"naam": result["naam"]}).mappings().first()
    
    if profiel:
        return {
            "indicator_uuid": result["uuid"],
            "indicator_naam": result["naam"],
            "score_type": result["score_type"],
            "source": "profile_match",
            "profile_naam": profiel["naam"],
            "palette": {
                "id": profiel["color_schema_id"],
                "naam": profiel["schema_naam"],
                "colors": profiel["colors"],
                "palette_type": profiel["palette_type"],
                "classificatie": profiel["classificatie_override"] or profiel["schema_classificatie"],
                "klassen": profiel["klassen_override"] or profiel["schema_klassen"],
                "nodata_kleur": profiel["nodata_kleur"],
                "midpoint_waarde": float(profiel["midpoint_waarde"]) if profiel["midpoint_waarde"] else None
            }
        }
    
    # 3. Ultimate fallback: default sequential-blue
    default_schema = db.execute(text("""
        SELECT * FROM color_schemas WHERE naam = 'sequential-blue' LIMIT 1
    """)).mappings().first()
    
    if default_schema:
        return {
            "indicator_uuid": result["uuid"],
            "indicator_naam": result["naam"],
            "score_type": result["score_type"],
            "source": "default",
            "palette": {
                "id": default_schema["id"],
                "naam": default_schema["naam"],
                "colors": default_schema["colors"],
                "palette_type": default_schema["palette_type"],
                "classificatie": default_schema["classificatie"],
                "klassen": default_schema["klassen"],
                "nodata_kleur": default_schema["nodata_kleur"]
            }
        }
    
    # Absolute fallback
    return {
        "indicator_uuid": result["uuid"],
        "indicator_naam": result["naam"],
        "score_type": result["score_type"],
        "source": "hardcoded_fallback",
        "palette": {
            "id": None,
            "naam": "fallback",
            "colors": {"min": "#deebf7", "mid": "#4292c6", "max": "#08306b"},
            "palette_type": "sequential",
            "classificatie": "quantile",
            "klassen": 5,
            "nodata_kleur": "#d1d5db"
        }
    }

# ============================================================================
# Admin Endpoints (Auth Required)
# ============================================================================

@admin_router.get("/paletten")
def get_all_paletten(
    db: Session = Depends(get_db),
):
    """Get ALL color palettes (incl. inactive) for admin management."""
    result = db.execute(text("""
        SELECT id, naam, beschrijving, colors, palette_type,
               classificatie, klassen, nodata_kleur, is_actief,
               created_at, updated_at
        FROM color_schemas
        ORDER BY id
    """))
    
    paletten = []
    for row in result.mappings():
        paletten.append({
            "id": row["id"],
            "naam": row["naam"],
            "beschrijving": row["beschrijving"],
            "colors": row["colors"],
            "palette_type": row["palette_type"],
            "classificatie": row["classificatie"],
            "klassen": row["klassen"],
            "nodata_kleur": row["nodata_kleur"],
            "is_actief": row["is_actief"]
        })
    
    return {"paletten": paletten, "total": len(paletten)}

@admin_router.post("/paletten")
def create_palette(
    data: ColorSchemaCreate,
    db: Session = Depends(get_db),
):
    """Create a new color palette."""
    # Validate klassen (max 7)
    if data.klassen > 7:
        raise HTTPException(status_code=400, detail="Maximum 7 klassen toegestaan (standaard document)")
    
    try:
        import json
        result = db.execute(text("""
            INSERT INTO color_schemas (naam, beschrijving, colors, palette_type, classificatie, klassen, nodata_kleur)
            VALUES (:naam, :beschrijving, CAST(:colors AS jsonb), :palette_type, :classificatie, :klassen, :nodata_kleur)
            RETURNING id, naam, beschrijving, colors, palette_type, classificatie, klassen, nodata_kleur, is_actief
        """), {
            "naam": data.naam,
            "beschrijving": data.beschrijving,
            "colors": json.dumps(data.colors),
            "palette_type": data.palette_type,
            "classificatie": data.classificatie,
            "klassen": data.klassen,
            "nodata_kleur": data.nodata_kleur
        })
        db.commit()
        
        row = result.mappings().first()
        return dict(row)
    except Exception:
        db.rollback()
        raise  # centrale foutafhandeling: 409/422/500 zonder SQL naar buiten (#203)

@admin_router.put("/paletten/{palette_id}")
def update_palette(
    palette_id: int,
    data: ColorSchemaUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing color palette."""
    # Build dynamic update
    updates = []
    params = {"id": palette_id}
    
    for field in ["naam", "beschrijving", "palette_type", "classificatie", "klassen", "nodata_kleur", "is_actief"]:
        value = getattr(data, field, None)
        if value is not None:
            updates.append(f"{field} = :{field}")
            params[field] = value
    
    if data.colors is not None:
        import json
        updates.append("colors = CAST(:colors AS jsonb)")
        params["colors"] = json.dumps(data.colors)
    
    if data.klassen is not None and data.klassen > 7:
        raise HTTPException(status_code=400, detail="Maximum 7 klassen toegestaan")
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("updated_at = NOW()")
    
    try:
        result = db.execute(text(f"""
            UPDATE color_schemas SET {', '.join(updates)}
            WHERE id = :id
            RETURNING id, naam, beschrijving, colors, palette_type, classificatie, klassen, nodata_kleur, is_actief
        """), params)
        db.commit()
        
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Palette {palette_id} not found")
        
        return dict(row)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise  # centrale foutafhandeling: 409/422/500 zonder SQL naar buiten (#203)

# ============================================================================
# Profiles Admin Endpoints
# ============================================================================

@admin_router.get("/profielen")
def get_profielen(
    db: Session = Depends(get_db),
):
    """Get all visualization profiles."""
    result = db.execute(text("""
        SELECT vp.id, vp.naam, vp.beschrijving, vp.indicator_pattern,
               vp.color_schema_id, cs.naam as schema_naam,
               vp.classificatie_override, vp.klassen_override,
               vp.midpoint_waarde, vp.is_actief
        FROM visualisatie_profielen vp
        LEFT JOIN color_schemas cs ON vp.color_schema_id = cs.id
        ORDER BY vp.id
    """))
    
    profielen = []
    for row in result.mappings():
        profielen.append({
            "id": row["id"],
            "naam": row["naam"],
            "beschrijving": row["beschrijving"],
            "indicator_pattern": row["indicator_pattern"],
            "color_schema_id": row["color_schema_id"],
            "schema_naam": row["schema_naam"],
            "classificatie_override": row["classificatie_override"],
            "klassen_override": row["klassen_override"],
            "midpoint_waarde": float(row["midpoint_waarde"]) if row["midpoint_waarde"] else None,
            "is_actief": row["is_actief"]
        })
    
    return {"profielen": profielen, "total": len(profielen)}

@admin_router.post("/profielen")
def create_profiel(
    data: ProfielCreate,
    db: Session = Depends(get_db),
):
    """Create a new visualization profile."""
    try:
        result = db.execute(text("""
            INSERT INTO visualisatie_profielen 
                (naam, beschrijving, indicator_pattern, color_schema_id,
                 classificatie_override, klassen_override, midpoint_waarde)
            VALUES (:naam, :beschrijving, :indicator_pattern, :color_schema_id,
                    :classificatie_override, :klassen_override, :midpoint_waarde)
            RETURNING id, naam, beschrijving, indicator_pattern, color_schema_id,
                      classificatie_override, klassen_override, midpoint_waarde, is_actief
        """), {
            "naam": data.naam,
            "beschrijving": data.beschrijving,
            "indicator_pattern": data.indicator_pattern,
            "color_schema_id": data.color_schema_id,
            "classificatie_override": data.classificatie_override,
            "klassen_override": data.klassen_override,
            "midpoint_waarde": data.midpoint_waarde
        })
        db.commit()
        
        row = result.mappings().first()
        return dict(row)
    except Exception:
        db.rollback()
        raise  # centrale foutafhandeling: 409/422/500 zonder SQL naar buiten (#203)

@admin_router.put("/profielen/{profiel_id}")
def update_profiel(
    profiel_id: int,
    data: ProfielUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing visualization profile."""
    updates = []
    params = {"id": profiel_id}
    
    for field in ["naam", "beschrijving", "indicator_pattern", "color_schema_id",
                  "classificatie_override", "klassen_override", "midpoint_waarde", "is_actief"]:
        value = getattr(data, field, None)
        if value is not None:
            updates.append(f"{field} = :{field}")
            params[field] = value
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("updated_at = NOW()")
    
    try:
        result = db.execute(text(f"""
            UPDATE visualisatie_profielen SET {', '.join(updates)}
            WHERE id = :id
            RETURNING id, naam, beschrijving, indicator_pattern, color_schema_id,
                      classificatie_override, klassen_override, midpoint_waarde, is_actief
        """), params)
        db.commit()
        
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Profiel {profiel_id} not found")
        
        return dict(row)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise  # centrale foutafhandeling: 409/422/500 zonder SQL naar buiten (#203)

@admin_router.delete("/profielen/{profiel_id}")
def delete_profiel(
    profiel_id: int,
    db: Session = Depends(get_db),
):
    """Delete a visualization profile."""
    try:
        result = db.execute(text("""
            DELETE FROM visualisatie_profielen WHERE id = :id RETURNING id
        """), {"id": profiel_id})
        db.commit()
        
        row = result.mappings().first()
        if not row:
            raise HTTPException(status_code=404, detail=f"Profiel {profiel_id} not found")
        
        return {"deleted": True, "id": profiel_id}
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise  # centrale foutafhandeling: 409/422/500 zonder SQL naar buiten (#203)

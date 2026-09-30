"""
Admin API Router for Beheerscherm (Admin Panel)
Manages indicators, score types, color schemas, and Kompas configurations.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from pydantic import BaseModel, UUID4
from src.database import get_db
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY', '')

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# ============================================================================
# Authentication
# ============================================================================
from routers.auth import check_auth_or_key

# We aliassen check_auth_or_key naar verify_admin_key zodat we niet elke 
# endpoint hoeven te herschrijven in deze file.
def verify_admin_key(request: Request, db: Session = Depends(get_db)):
    """Verifies admin access using the new Hybrid Session/Key model."""
    return check_auth_or_key(request, db)

# ============================================================================
# Pydantic Models
# ============================================================================
class ScoreType(BaseModel):
    code: str
    naam: str
    beschrijving: str
    voorbeelden: str

class ColorSchema(BaseModel):
    id: int
    naam: str
    beschrijving: Optional[str]
    colors: dict
    is_actief: bool

class ColorSchemaCreate(BaseModel):
    naam: str
    beschrijving: Optional[str] = None
    colors: dict

class IndicatorBase(BaseModel):
    uuid: str
    naam: str
    omschrijving: Optional[str]
    bron: Optional[str]
    eenheid: Optional[str]
    score_type: str
    color_schema_id: Optional[int]
    color_schema_naam: Optional[str]
    admin_notes: Optional[str]

class IndicatorUpdate(BaseModel):
    naam: Optional[str] = None
    omschrijving: Optional[str] = None
    bron: Optional[str] = None
    eenheid: Optional[str] = None
    score_type: Optional[str] = None
    color_schema_id: Optional[int] = None
    admin_notes: Optional[str] = None

class OntologieValidatie(BaseModel):
    ontologische_beschrijving: str
    ontologie_status: str  # 'draft' | 'beoordeeld_ai' | 'goedgekeurd_mens'

class LLMConfig(BaseModel):
    api_url: str
    model_name: str

class SystemPrompt(BaseModel):
    naam: str
    beschrijving: Optional[str] = None
    prompt_text: str
    is_actief: bool

class SystemPromptUpdate(BaseModel):
    prompt_text: str
    beschrijving: Optional[str] = None
    is_actief: Optional[bool] = None

# ============================================================================
# LLM Config & System Prompts Endpoints
# ============================================================================
@router.get("/llm/config", response_model=LLMConfig)
async def get_llm_config(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get active LLM Config."""
    result = db.execute(text("SELECT api_url, model_name FROM llm_config ORDER BY id DESC LIMIT 1"))
    row = result.fetchone()
    if not row:
        return {"api_url": "http://localhost:11434", "model_name": "qwen3:30b"}
    return {"api_url": row[0], "model_name": row[1]}

@router.put("/llm/config", response_model=LLMConfig)
async def update_llm_config(
    config: LLMConfig,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Update active LLM Config."""
    db.execute(text("""
        INSERT INTO llm_config (api_url, model_name)
        VALUES (:api, :model)
    """), {"api": config.api_url, "model": config.model_name})
    db.commit()
    return config

@router.get("/llm/models")
def get_ollama_models(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Fetch available models from the configured Ollama instance."""
    import requests
    
    result = db.execute(text("SELECT api_url FROM llm_config ORDER BY id DESC LIMIT 1"))
    row = result.fetchone()
    api_url = row[0] if row else "http://localhost:11434"
    
    try:
        response = requests.get(f"{api_url}/api/tags", timeout=5)
        response.raise_for_status()
        data = response.json()
        models = [m['name'] for m in data.get('models', [])]
        return {"models": models}
    except Exception as e:
        # Fallback to current configured model if API is offline
        current_model = db.execute(text("SELECT model_name FROM llm_config ORDER BY id DESC LIMIT 1")).fetchone()
        return {"models": [current_model[0] if current_model else "qwen3:30b"], "error": str(e)}

@router.get("/prompts", response_model=List[SystemPrompt])
async def get_system_prompts(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get all system prompts."""
    result = db.execute(text("SELECT naam, beschrijving, prompt_text, is_actief FROM system_prompts ORDER BY id DESC"))
    rows = result.fetchall()
    return [
        SystemPrompt(
            naam=row[0],
            beschrijving=row[1],
            prompt_text=row[2],
            is_actief=row[3]
        ) for row in rows
    ]

@router.put("/prompts/{naam}", response_model=SystemPrompt)
async def update_system_prompt(
    naam: str,
    data: SystemPromptUpdate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Update a specific system prompt."""
    
    updates = ["prompt_text = :prompt"]
    params = {"naam": naam, "prompt": data.prompt_text}
    
    if data.beschrijving is not None:
        updates.append("beschrijving = :desc")
        params["desc"] = data.beschrijving
    
    if data.is_actief is not None:
        updates.append("is_actief = :actief")
        params["actief"] = data.is_actief
        
    query = f"UPDATE system_prompts SET {', '.join(updates)} WHERE naam = :naam RETURNING naam, beschrijving, prompt_text, is_actief"
    
    result = db.execute(text(query), params)
    row = result.fetchone()
    db.commit()
    
    if not row:
        raise HTTPException(404, f"Prompt {naam} niet gevonden")
        
    return SystemPrompt(
        naam=row[0],
        beschrijving=row[1],
        prompt_text=row[2],
        is_actief=row[3]
    )

# ============================================================================
# Hierarchy Endpoints
# ============================================================================
@router.get("/score-types", response_model=List[ScoreType])
async def get_score_types(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get all valid score types with descriptions."""
    result = db.execute(text("SELECT * FROM v_score_types"))
    rows = result.fetchall()
    return [
        ScoreType(
            code=row[0],
            naam=row[1],
            beschrijving=row[2],
            voorbeelden=row[3]
        ) for row in rows
    ]

# ============================================================================
# Color Schema Endpoints
# ============================================================================
@router.get("/color-schemas", response_model=List[ColorSchema])
async def get_color_schemas(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get all available color schemas."""
    result = db.execute(text("""
        SELECT id, naam, beschrijving, colors, is_actief 
        FROM color_schemas 
        WHERE is_actief = true 
        ORDER BY id
    """))
    rows = result.fetchall()
    return [
        ColorSchema(
            id=row[0],
            naam=row[1],
            beschrijving=row[2],
            colors=row[3],
            is_actief=row[4]
        ) for row in rows
    ]

@router.post("/color-schemas", response_model=ColorSchema)
async def create_color_schema(
    data: ColorSchemaCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Create a new color schema."""
    result = db.execute(text("""
        INSERT INTO color_schemas (naam, beschrijving, colors)
        VALUES (:naam, :beschrijving, CAST(:colors AS jsonb))
        RETURNING id, naam, beschrijving, colors, is_actief
    """), {
        "naam": data.naam,
        "beschrijving": data.beschrijving,
        "colors": json.dumps(data.colors)
    })
    db.commit()
    row = result.fetchone()
    return ColorSchema(
        id=row[0], naam=row[1], beschrijving=row[2], 
        colors=row[3], is_actief=row[4]
    )

# ============================================================================
# Indicator Endpoints
# ============================================================================
@router.get("/indicatoren")
async def get_indicatoren(
    search: Optional[str] = None,
    score_type: Optional[str] = None,
    ontologie_status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get all indicators with admin info. Filter by ontologie_status for validation workflow."""
    query = """
        SELECT 
            i.uuid::text,
            i.naam,
            i.omschrijving,
            i.bron,
            i.eenheid,
            COALESCE(i.score_type, '+/+') as score_type,
            i.color_schema_id,
            cs.naam as color_schema_naam,
            i.admin_notes,
            i.ontologie_status,
            i.ontologische_beschrijving,
            i.beschrijving_ai,
            i.gevalideerd_op,
            i.is_actief,
            i.vervangen_door_id
        FROM indicatoren i
        LEFT JOIN color_schemas cs ON i.color_schema_id = cs.id
        WHERE 1=1
    """
    params = {"limit": limit, "offset": offset}
    
    if search:
        query += " AND (i.naam ILIKE :search OR i.omschrijving ILIKE :search)"
        params["search"] = f"%{search}%"
    
    if score_type:
        query += " AND i.score_type = :score_type"
        params["score_type"] = score_type
    
    if ontologie_status:
        query += " AND i.ontologie_status = :ontologie_status"
        params["ontologie_status"] = ontologie_status
    
    query += " ORDER BY i.naam LIMIT :limit OFFSET :offset"
    
    result = db.execute(text(query), params)
    rows = result.fetchall()
    
    # Get total count (with same filters)
    count_query = "SELECT COUNT(*) FROM indicatoren i WHERE 1=1"
    count_params = {}
    if search:
        count_query += " AND (i.naam ILIKE :search OR i.omschrijving ILIKE :search)"
        count_params["search"] = f"%{search}%"
    if score_type:
        count_query += " AND i.score_type = :score_type"
        count_params["score_type"] = score_type
    if ontologie_status:
        count_query += " AND i.ontologie_status = :ontologie_status"
        count_params["ontologie_status"] = ontologie_status
    total = db.execute(text(count_query), count_params).scalar()
    
    return {
        "indicatoren": [
            {
                "uuid": row[0],
                "naam": row[1],
                "omschrijving": row[2],
                "bron": row[3],
                "eenheid": row[4],
                "score_type": row[5],
                "color_schema_id": row[6],
                "color_schema_naam": row[7],
                "admin_notes": row[8],
                "ontologie_status": row[9],
                "ontologische_beschrijving": row[10],
                "beschrijving_ai": row[11],
                "gevalideerd_op": row[12].isoformat() if row[12] else None,
                "is_actief": row[13],
                "vervangen_door_id": str(row[14]) if row[14] else None
            } for row in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/indicatoren/{uuid}")
async def get_indicator(
    uuid: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get single indicator by UUID, including ontology validation fields."""
    result = db.execute(text("""
        SELECT 
            i.uuid::text,
            i.naam,
            i.omschrijving,
            i.bron,
            i.eenheid,
            COALESCE(i.score_type, '+/+') as score_type,
            i.color_schema_id,
            cs.naam as color_schema_naam,
            cs.colors as color_schema_colors,
            i.admin_notes,
            i.ontologie_status,
            i.ontologische_beschrijving,
            i.beschrijving_ai,
            i.gevalideerd_door::text,
            i.gevalideerd_op,
            i.embedding_versie,
            u.username as gevalideerd_door_naam,
            i.is_actief,
            i.vervangen_door_id,
            i.bron_systeem_api,
            i.bron_tabel_referentie,
            i.laatste_check_datum
        FROM indicatoren i
        LEFT JOIN color_schemas cs ON i.color_schema_id = cs.id
        LEFT JOIN users u ON i.gevalideerd_door = u.id
        WHERE i.uuid = :uuid
    """), {"uuid": uuid})
    row = result.fetchone()
    
    if not row:
        raise HTTPException(404, f"Indicator {uuid} not found")
    
    return {
        "uuid": row[0],
        "naam": row[1],
        "omschrijving": row[2],
        "bron": row[3],
        "eenheid": row[4],
        "score_type": row[5],
        "color_schema_id": row[6],
        "color_schema_naam": row[7],
        "color_schema_colors": row[8],
        "admin_notes": row[9],
        "ontologie_status": row[10],
        "ontologische_beschrijving": row[11],
        "beschrijving_ai": row[12],
        "gevalideerd_door": row[13],
        "gevalideerd_op": row[14].isoformat() if row[14] else None,
        "embedding_versie": row[15],
        "gevalideerd_door_naam": row[16],
        "is_actief": row[17],
        "vervangen_door_id": str(row[18]) if row[18] else None,
        "bron_systeem_api": row[19],
        "bron_tabel_referentie": row[20],
        "laatste_check_datum": row[21].isoformat() if row[21] else None
    }

@router.put("/indicatoren/{uuid}")
async def update_indicator(
    uuid: str,
    data: IndicatorUpdate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Update indicator fields."""
    # Build dynamic update query
    updates = []
    params = {"uuid": uuid}
    
    if data.naam is not None:
        updates.append("naam = :naam")
        params["naam"] = data.naam
    if data.omschrijving is not None:
        updates.append("omschrijving = :omschrijving")
        params["omschrijving"] = data.omschrijving
    if data.bron is not None:
        updates.append("bron = :bron")
        params["bron"] = data.bron
    if data.eenheid is not None:
        updates.append("eenheid = :eenheid")
        params["eenheid"] = data.eenheid
    if data.score_type is not None:
        if data.score_type not in ['+/+', '+/-', '-/+', '-/-']:
            raise HTTPException(400, "Invalid score_type. Must be +/+, +/-, -/+, or -/-")
        updates.append("score_type = :score_type")
        params["score_type"] = data.score_type
    if data.color_schema_id is not None:
        updates.append("color_schema_id = :color_schema_id")
        params["color_schema_id"] = data.color_schema_id
    if data.admin_notes is not None:
        updates.append("admin_notes = :admin_notes")
        params["admin_notes"] = data.admin_notes
    
    if not updates:
        raise HTTPException(400, "No fields to update")
    
    query = f"UPDATE indicatoren SET {', '.join(updates)} WHERE uuid = :uuid RETURNING uuid::text"
    result = db.execute(text(query), params)
    db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(404, f"Indicator {uuid} not found")
    
    # Return updated indicator
    return await get_indicator(uuid, db, True)

@router.patch("/indicatoren/{uuid}/valideer")
async def valideer_indicator_ontologie(
    uuid: str,
    data: OntologieValidatie,
    request: Request,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Valideer of keur de ontologische beschrijving van een indicator goed.
    Sprint 9 Track B: Mens-in-the-loop validatie voor AI-gegenereerde ontologieën.
    """
    # Valideer ontologie_status waarde
    valid_statuses = ['draft', 'beoordeeld_ai', 'goedgekeurd_mens']
    if data.ontologie_status not in valid_statuses:
        raise HTTPException(400, f"Ongeldige ontologie_status. Keuze uit: {valid_statuses}")
    
    # Haal user_id uit sessie (indien ingelogd)
    user_id = None
    session_token = request.cookies.get('session_token')
    if session_token:
        session_row = db.execute(
            text("SELECT user_id FROM sessions WHERE token = :token AND expires_at > NOW()"),
            {"token": session_token}
        ).fetchone()
        if session_row:
            user_id = str(session_row[0])
    
    # Update indicator
    result = db.execute(text("""
        UPDATE indicatoren SET
            ontologische_beschrijving = :beschrijving,
            ontologie_status = :status,
            gevalideerd_door = :user_id,
            gevalideerd_op = NOW()
        WHERE uuid = :uuid
        RETURNING uuid::text
    """), {
        "beschrijving": data.ontologische_beschrijving,
        "status": data.ontologie_status,
        "user_id": user_id,
        "uuid": uuid
    })
    
    if result.rowcount == 0:
        raise HTTPException(404, f"Indicator {uuid} niet gevonden")
    
    db.commit()
    
    # Return updated indicator
    return await get_indicator(uuid, db, True)

@router.get("/ontologie/status")
async def get_ontologie_validatiestatus(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Haal de totale validatie-voortgang op (Dashboard widget).
    Retourneert per ontologie_status het aantal indicatoren.
    """
    result = db.execute(text("SELECT * FROM v_ontologie_validatiestatus"))
    rows = result.fetchall()
    
    status_map = {row[0]: row[1] for row in rows}
    total = sum(status_map.values())
    goedgekeurd = status_map.get('goedgekeurd_mens', 0)
    
    return {
        "statussen": status_map,
        "totaal": total,
        "goedgekeurd": goedgekeurd,
        "percentage_gereed": round(goedgekeurd / total * 100, 1) if total > 0 else 0
    }

# ============================================================================
# Hierarchy Endpoints
# ============================================================================
@router.get("/hierarchie/tree")
async def get_hierarchy_tree(
    config_id: int = 1,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get full hierarchy tree for visualization."""
    """Get full hierarchy tree for visualization."""
    from services.kompas_service import KompasService
    
    service = KompasService(db)
    # Reuse the robust logic from KompasService which includes Titels (Quadrants)
    hierarchy_data = service.get_hierarchie(config_id)
    
    if not hierarchy_data or "hierarchie" not in hierarchy_data:
        raise HTTPException(404, f"Cluster configuration {config_id} not found")

    # The service returns a Root node with children (Titels)
    root_node = hierarchy_data["hierarchie"]
    raw_tree = root_node.get("children", [])
    
    # Transform keys to match frontend expectation (name -> naam, ensure id)
    def transform_node(node, prefix="node", index=0):
        # Generate ID if missing (KompasService nodes might lack unique IDs for D3)
        node_id = node.get("uuid") or f"{prefix}-{index}"
        
        new_node = {
            "id": node_id,
            "naam": node.get("name", "Naamloos"), # Frontend expects 'naam'
            "type": node.get("type", "unknown"),
            "children": [],
            "score_type": node.get("score_type"), # Preserve extra fields
            "volgorde": node.get("volgorde", index)
        }
        
        # Recurse
        if "children" in node:
            for i, child in enumerate(node["children"]):
                child_prefix = f"{node_id}-{i}"
                new_node["children"].append(transform_node(child, child_prefix, i))
                
        return new_node

    tree = [transform_node(node, "titel", i) for i, node in enumerate(raw_tree)]
    
    # Calculate stats recursively
    def count_nodes(nodes, type_filter):
        count = 0
        for node in nodes:
            if node.get("type") == type_filter:
                count += 1
            if "children" in node:
                count += count_nodes(node["children"], type_filter)
        return count

    stats = {
        "themas": count_nodes(tree, "thema"),
        "onderdelen": count_nodes(tree, "onderdeel"),
        "indicatoren": hierarchy_data.get("total_indicators", 0)
    }

    return {
        "config_id": config_id,
        "tree": tree,
        "stats": stats
    }

# ============================================================================
# Health Check
# ============================================================================
@router.get("/health")
async def admin_health(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Admin API health check."""
    # Check database connectivity
    result = db.execute(text("SELECT COUNT(*) FROM indicatoren"))
    indicator_count = result.scalar()
    
    schema_result = db.execute(text("SELECT COUNT(*) FROM color_schemas"))
    schema_count = schema_result.scalar()
    
    return {
        "status": "healthy",
        "auth": "valid",
        "database": "connected",
        "indicatoren": indicator_count,
        "color_schemas": schema_count
    }

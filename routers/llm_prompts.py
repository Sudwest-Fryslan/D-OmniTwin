from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
from uuid import UUID

from src.database import get_db
from schemas.llm import SystemPromptCreate, SystemPromptUpdate, SystemPromptResponse

router = APIRouter(
    prefix="/api/admin/prompts",
    tags=["Admin", "LLM Prompts"]
)

@router.get("/", response_model=List[Dict[str, Any]])
def get_prompts(db: Session = Depends(get_db)):
    """Haal alle system prompts op"""
    query = text("""
        SELECT id, naam, beschrijving, prompt_text, is_actief, aangemaakt_op, laatst_gewijzigd
        FROM system_prompts
        ORDER BY naam
    """)
    result = db.execute(query)
    return [dict(row._mapping) for row in result]

@router.get("/{prompt_id}", response_model=Dict[str, Any])
def get_prompt(prompt_id: UUID, db: Session = Depends(get_db)):
    """Haal 1 system prompt op bij ID"""
    query = text("""
        SELECT id, naam, beschrijving, prompt_text, is_actief, aangemaakt_op, laatst_gewijzigd
        FROM system_prompts WHERE id = :id
    """)
    result = db.execute(query, {"id": prompt_id}).fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Prompt niet gevonden")
    return dict(result._mapping)

@router.post("/", response_model=Dict[str, Any])
def create_prompt(prompt: SystemPromptCreate, db: Session = Depends(get_db)):
    """Maak een nieuwe system prompt aan"""
    try:
        query = text("""
            INSERT INTO system_prompts (naam, beschrijving, prompt_text, is_actief)
            VALUES (:naam, :beschrijving, :prompt_text, :is_actief)
            RETURNING id, naam, beschrijving, prompt_text, is_actief, aangemaakt_op, laatst_gewijzigd
        """)
        result = db.execute(query, prompt.dict())
        db.commit()
        return dict(result.fetchone()._mapping)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")

@router.put("/{prompt_id}", response_model=Dict[str, Any])
def update_prompt(prompt_id: UUID, prompt: SystemPromptUpdate, db: Session = Depends(get_db)):
    """Update een bestaande system prompt"""
    # Haal huidige op
    current = get_prompt(prompt_id, db)
    
    update_data = prompt.dict(exclude_unset=True)
    if not update_data:
        return current
        
    set_clause = ", ".join([f"{k} = :{k}" for k in update_data.keys()])
    update_data["id"] = prompt_id
    
    try:
        query = text(f"""
            UPDATE system_prompts 
            SET {set_clause}
            WHERE id = :id
            RETURNING id, naam, beschrijving, prompt_text, is_actief, aangemaakt_op, laatst_gewijzigd
        """)
        result = db.execute(query, update_data)
        db.commit()
        return dict(result.fetchone()._mapping)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")

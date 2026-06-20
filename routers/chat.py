"""
Router: D-Omni Assistant Chat
POST /api/chat — Intent-based chat endpoint met Command Dispatch JSON

Architectuur:
1. Gebruikersvraag → AISearchService (semantisch zoeken in indicatoren)
2. Intent Classificatie (rule-based)
3. LLM Narrative (korte toelichting, max 80 woorden)
4. Command Dispatch JSON response (acties + indicatoren)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from src.database import get_db
from services.ai_search_service import AISearchService
from services.llm_service import LLMService
from typing import List, Dict, Any, Optional
import re
import logging

from services.logging_service import AppLogger

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/chat",
    tags=["D-Omni Assistant"]
)

# ============================================================================
# Request / Response Models
# ============================================================================

class ChatRequest(BaseModel):
    vraag: str = Field(..., min_length=2, max_length=1000, description="De vraag van de gebruiker")
    context: Optional[Dict[str, Any]] = Field(None, description="Optionele kaartcontext (huidig_gebied_id, etc.)")

class ActieKnop(BaseModel):
    type: str  # TOON_OP_KAART, SELECTEER_BUURTEN, MAAK_RAPPORT, SELECTEER_GEMEENTE, SELECTEER_GEBIEDSTYPE, SELECTEER_KOMPAS, OPEN_KOMPAS, INFO_KAART, INFO_KOMPAS, INFO_RAPPORT, OPEN_WIKI
    label: str
    indicator_uuid: Optional[str] = None
    gemeente_code: Optional[str] = None
    gebiedstype_id: Optional[str] = None
    config_id: Optional[int] = None
    filters: Optional[Dict[str, Any]] = None
    thema: Optional[str] = None

class IndicatorResultaat(BaseModel):
    uuid: str
    naam: str
    beschrijving: Optional[str] = None
    categorie: Optional[str] = None
    eenheid: Optional[str] = None
    score_type: Optional[str] = None
    relevantie: float  # 0-1 cosine similarity score

class ChatResponse(BaseModel):
    intent: str
    narrative: str
    acties: List[ActieKnop]
    indicatoren: List[IndicatorResultaat]
    debug: Optional[Dict[str, Any]] = None

# ============================================================================
# Intent Classificatie (Rule-Based)
# ============================================================================

# --- HELP_ONBOARDING: Deterministic (geen LLM nodig) ---
HELP_ONBOARDING_PATTERNS = [
    r"wat\s+kan\s+jij", r"wat\s+kun\s+je", r"wat\s+doe\s+jij",
    r"hoe\s+gebruik\s+ik", r"hoe\s+werkt\s+(dit|deze|de\s+app)",
    r"waar\s+moet\s+ik\s+beginnen", r"hoe\s+begin\s+ik",
    r"mogelijkheden", r"functies", r"functionaliteit",
    r"^help$", r"^help\b", r"handleiding", r"uitleg",
    r"wat\s+zijn\s+je\s+mogelijkheden", r"hoe\s+kan\s+ik\s+jou\s+(inzetten|gebruiken)",
    r"wat\s+kan\s+deze\s+app", r"wat\s+kan\s+ik\s+hier\s+doen"
]

def is_help_onboarding(vraag: str) -> bool:
    """Detecteert of een vraag een help/onboarding-vraag is (vóór LLM-aanroep)."""
    vraag_lower = vraag.lower().strip()
    return any(re.search(p, vraag_lower) for p in HELP_ONBOARDING_PATTERNS)

def get_help_onboarding_response() -> ChatResponse:
    """Retourneert een vaste, instant response voor help-vragen. Geen LLM nodig."""
    return ChatResponse(
        intent="HELP_ONBOARDING",
        narrative=(
            "Welkom! Ik ben de D-Omni Assistent. Ik help je de leefomgeving "
            "te verkennen via data, kaarten en analyses. "
            "Hier is wat ik voor je kan doen:"
        ),
        acties=[
            ActieKnop(type="INFO_KAART",   label="🗺️ Kaart & Gebieden verkennen"),
            ActieKnop(type="INFO_KOMPAS",  label="🧭 Het D-Omni Kompas begrijpen"),
            ActieKnop(type="INFO_RAPPORT", label="📄 Rapporten & Analyses genereren"),
            ActieKnop(type="OPEN_WIKI",    label="📖 Volledige Handleiding openen"),
        ],
        indicatoren=[],
        debug={"mode": "deterministic_onboarding"}
    )

# --- Overige intents (LLM-driven) ---
INTENT_PATTERNS = {
    "TOON_OP_KAART": [
        r"toon\b", r"laat\s+zien", r"kaart", r"kleur", r"visualiseer",
        r"op de kaart", r"in de kaart"
    ],
    "SELECTEER_BUURTEN": [
        r"selecteer", r"filter", r"laagste", r"hoogste", r"grootste",
        r"minste", r"welke\s+buurten", r"welke\s+wijken", r"top\s+\d+",
        r"onderste", r"bovenste"
    ],
    "MAAK_RAPPORT": [
        r"rapport", r"samenvatting", r"analyse\b", r"exporteer",
        r"maak\s+een\s+rapport", r"genereer\s+rapport"
    ],
    "ANALYSEER_GEBIED": [
        r"hoe\s+scoort", r"hoe\s+staat", r"vergelijk", r"benchmark",
        r"presteer"
    ],
    "VERBIND_THEMAS": [
        r"verbind", r"samenhang", r"relatie\s+tussen", r"correlatie",
        r"verband", r"koppel"
    ],
}

def classify_intent(vraag: str) -> str:
    """
    Classificeert de intent op basis van patronen in de vraag.
    Retourneert de meest passende intent of 'ZOEK_INDICATOREN' als fallback.
    """
    vraag_lower = vraag.lower()
    
    # Tel matches per intent
    intent_scores = {}
    for intent, patterns in INTENT_PATTERNS.items():
        score = sum(1 for p in patterns if re.search(p, vraag_lower))
        if score > 0:
            intent_scores[intent] = score
    
    if not intent_scores:
        return "ZOEK_INDICATOREN"
    
    # Retourneer intent met meeste matches
    return max(intent_scores, key=intent_scores.get)

# ============================================================================
# Actie-knoppen generatie op basis van intent + indicatoren
# ============================================================================

def generate_acties(intent: str, indicatoren: List[Dict[str, Any]], vraag: str) -> List[ActieKnop]:
    """Genereert actie-knoppen op basis van intent en gevonden indicatoren."""
    acties = []
    
    # Altijd: eerste indicator "Toon op kaart" (als er indicatoren zijn)
    if indicatoren:
        top = indicatoren[0]
        acties.append(ActieKnop(
            type="TOON_OP_KAART",
            label=f"🗺 Toon: {top['naam']}",
            indicator_uuid=top["uuid"]
        ))
    
    # Bij selectie-intent: filter-actie
    if intent in ("SELECTEER_BUURTEN", "ZOEK_INDICATOREN", "VERBIND_THEMAS") and indicatoren:
        # Detecteer of gebruiker "laagste" of "hoogste" wil
        vraag_lower = vraag.lower()
        if any(w in vraag_lower for w in ["laagste", "minste", "weinig", "onderste", "slecht"]):
            percentiel = "P0-P25"
            label_prefix = "Laagste 25%"
        elif any(w in vraag_lower for w in ["hoogste", "meeste", "veel", "bovenste", "best"]):
            percentiel = "P75-P100"
            label_prefix = "Hoogste 25%"
        else:
            percentiel = "P0-P25"
            label_prefix = "Selectie"
        
        acties.append(ActieKnop(
            type="SELECTEER_BUURTEN",
            label=f"📋 {label_prefix}: {indicatoren[0]['naam']}",
            indicator_uuid=indicatoren[0]["uuid"],
            filters={"percentiel": percentiel}
        ))
    
    # Bij rapport-intent of als er meerdere indicatoren zijn
    if intent == "MAAK_RAPPORT" or (intent == "VERBIND_THEMAS" and len(indicatoren) >= 2):
        # Probeer een thema af te leiden uit de categorieën
        categorieen = list(set(i.get("categorie", "") for i in indicatoren[:4] if i.get("categorie")))
        thema_label = " & ".join(categorieen[:2]) if categorieen else "Analyse"
        
        acties.append(ActieKnop(
            type="MAAK_RAPPORT",
            label=f"📄 Rapport: {thema_label}",
            thema=thema_label.lower().replace(" ", "_")
        ))
    
    # Extra indicatoren op kaart (2e en 3e)
    for ind in indicatoren[1:3]:
        acties.append(ActieKnop(
            type="TOON_OP_KAART",
            label=f"🗺 Toon: {ind['naam']}",
            indicator_uuid=ind["uuid"]
        ))
    
    return acties

# ============================================================================
# Chat Endpoint
# ============================================================================

@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    D-Omni Assistant: Verwerkt een Nederlandstalige vraag en retourneert
    een Command Dispatch JSON met intent, narrative, actie-knoppen en
    gevonden indicatoren.
    """
    vraag = request.vraag.strip()
    context = request.context or {}
    
    AppLogger.info(f"Chat vraag ontvangen: '{vraag[:80]}'", category="LLM_CHAT")
    
    # ------------------------------------------------
    # Stap 0: Help/Onboarding — instant, geen LLM nodig
    # ------------------------------------------------
    if is_help_onboarding(vraag):
        AppLogger.info("HELP_ONBOARDING intent — deterministic response", category="LLM_CHAT")
        return get_help_onboarding_response()
    
    # ------------------------------------------------
    # Stap 1: Semantisch zoeken naar relevante indicatoren
    # ------------------------------------------------
    search_service = AISearchService(db)
    search_results = search_service.search_indicators(vraag, limit=8)
    
    # Check op foutmeldingen (bijv. AI model niet geladen)
    if search_results and "error" in search_results[0]:
        AppLogger.error(f"Fout bij zoeken indicatoren: {search_results[0]['error']}", category="LLM_CHAT")
        raise HTTPException(status_code=503, detail="AI zoekfunctionaliteit tijdelijk niet beschikbaar.")
        
    # Filter op minimale relevantie (score > 0.25)
    relevant_results = [r for r in search_results if r.get("score", 0) > 0.25]
    
    if not relevant_results:
        # Fallback: gebruik alle resultaten maar meld lage relevantie
        relevant_results = search_results[:5]
    
    # ------------------------------------------------
    # Stap 2 & 3: Intelligent Intent & Action Dispatching (LLM-driven)
    # ------------------------------------------------
    llm_service = LLMService(db)
    intelligent_response = llm_service.detect_intent_and_actions(
        vraag=vraag,
        indicatoren=relevant_results,
        context=context
    )
    
    if intelligent_response:
        intent = intelligent_response["intent"]
        narrative = intelligent_response["narrative"]
        acties_data = intelligent_response["acties"]
        
        # Mappen van LLM actie-dicts naar ActieKnop Pydantic modellen
        acties = []
        for a in acties_data:
            try:
                acties.append(ActieKnop(
                    type=a.get("type", "ZOEK_RESULTATEN"),
                    label=a.get("label", "Bekijk info"),
                    indicator_uuid=a.get("indicator_uuid"),
                    gemeente_code=a.get("gemeente_code"),
                    gebiedstype_id=a.get("gebiedstype_id"),
                    config_id=a.get("config_id"),
                    filters=a.get("filters"),
                    thema=a.get("thema")
                ))
            except Exception:
                continue
                
        debug_info = {
            "mode": "intelligent_dispatcher",
            "model": intelligent_response.get("debug", {}).get("model")
        }
    else:
        # FALLBACK: Oude rule-based logica als LLM faalt of ongeldige JSON geeft
        AppLogger.warning("Intelligent dispatcher faalde, terugval naar legacy mode", category="LLM_CHAT")
        intent = classify_intent(vraag)
        acties = generate_acties(intent, relevant_results, vraag)
        
        try:
            llm_response = llm_service.generate_chat_narrative(
                vraag=vraag,
                indicatoren=relevant_results,
                intent=intent,
                context=context
            )
            narrative = llm_response.get("text", "")
        except Exception:
            indicator_namen = ", ".join(r["naam"] for r in relevant_results[:3])
            narrative = f"Ik heb {len(relevant_results)} relevante indicatoren gevonden: {indicator_namen}."
            
        debug_info = {"mode": "legacy_fallback", "intent": intent}

    # ------------------------------------------------
    # Stap 4: Response samenstellen
    # ------------------------------------------------
    indicatoren_out = [
        IndicatorResultaat(
            uuid=r["uuid"],
            naam=r["naam"],
            beschrijving=r.get("beschrijving"),
            categorie=r.get("categorie"),
            eenheid=r.get("eenheid"),
            score_type=r.get("score_type"),
            relevantie=r.get("score", 0)
        )
        for r in relevant_results
    ]
    
    return ChatResponse(
        intent=intent,
        narrative=narrative,
        acties=acties,
        indicatoren=indicatoren_out,
        debug=debug_info
    )


@router.get("/health")
async def chat_health():
    """Health check voor de Chat API."""
    return {"status": "healthy", "service": "D-Omni Assistant Chat API"}

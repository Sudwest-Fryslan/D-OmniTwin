"""
Router: D-Omni Assistant Chat
POST /api/chat — Intent-based chat endpoint met Command Dispatch JSON

Architectuur:
0. Datavraag ("welke buurt ligt het verst van een koele plek") → cijfers uit de database,
   het taalmodel formuleert alleen met die cijfers (services/chat_datavraag.py, #149)
1. Gebruikersvraag → AISearchService (semantisch zoeken in indicatoren)
2. Intent Classificatie (rule-based)
3. LLM Narrative (korte toelichting, max 80 woorden)
4. Command Dispatch JSON response (acties + indicatoren)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from omnitwin.database import get_db
from omnitwin.grenzen import beperk_llm
from omnitwin.services.ai_search_service import AISearchService
from omnitwin.services.llm_service import LLMService
from omnitwin.services.gemeente_validatie import valideer_gemeente_acties
from omnitwin.services.chat_datavraag import beantwoord_datavraag
from typing import List, Dict, Any, Optional
import re
import logging

from omnitwin.services.logging_service import AppLogger

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
    type: str  # TOON_OP_KAART, SELECTEER_BUURTEN, MAAK_RAPPORT, SELECTEER_GEMEENTE, SELECTEER_GEBIEDSTYPE, SELECTEER_KOMPAS, OPEN_KOMPAS, INFO_KAART, INFO_KOMPAS, INFO_RAPPORT, OPEN_WIKI, SEND_MESSAGE
    label: str
    rol_code: Optional[str] = None
    indicator_uuid: Optional[str] = None
    gemeente_code: Optional[str] = None
    gebiedstype_id: Optional[str] = None
    config_id: Optional[int] = None
    filters: Optional[Dict[str, Any]] = None
    thema: Optional[str] = None
    gebied_ids: Optional[List[str]] = None  # datavraag (#149): deze gebieden selecteren

class IndicatorResultaat(BaseModel):
    uuid: str
    naam: str
    beschrijving: Optional[str] = None
    categorie: Optional[str] = None
    eenheid: Optional[str] = None
    score_type: Optional[str] = None
    relevantie: float  # 0-1 cosine similarity score

class BronRegel(BaseModel):
    indicator: str
    bron: str
    jaren: List[int] = []

class Gegeven(BaseModel):
    """Eén cijfer waarop een antwoord op een datavraag steunt (#149)."""
    indicator_uuid: str
    indicator: str
    gebied_id: str
    gebied: str
    waarde: float
    jaar: Optional[int] = None
    eenheid: Optional[str] = None
    richting: str
    rang_hoog: int
    aantal_gebieden: int
    demo: bool = False

class ChatResponse(BaseModel):
    intent: str
    narrative: str
    acties: List[ActieKnop]
    indicatoren: List[IndicatorResultaat]
    bronnen: Optional[List[BronRegel]] = None
    gegevens: Optional[List[Gegeven]] = None
    # #149: de kaart beweegt mee na een datavraag (gebiedstype, indicator, selectie, inzoomen)
    kaart_actie: Optional[Dict[str, Any]] = None
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

def get_help_onboarding_response(db: Session) -> ChatResponse:
    """Retourneert een vaste, instant response voor help-vragen, met actieve profielen uit de DB."""
    try:
        from sqlalchemy import text
        scenarios = db.execute(text(
            "SELECT rol_code, rol_naam, beschrijving FROM chat_scenarios "
            "WHERE is_actief = true ORDER BY volgorde"
        )).fetchall()
        
        acties = [
            ActieKnop(
                type="SEND_MESSAGE",
                label=f"👤 {s.rol_naam}",
                rol_code=s.rol_code
            )
            for s in scenarios
        ]
    except Exception as e:
        AppLogger.error(f"Error loading chat scenarios: {e}", category="LLM_CHAT")
        acties = []

    acties.append(ActieKnop(type="OPEN_WIKI", label="📖 Volledige Handleiding openen"))

    return ChatResponse(
        intent="HELP_ONBOARDING",
        narrative=(
            "Welkom! Ik ben de D-Omni Assistent. Ik help je de leefomgeving "
            "te verkennen via data, kaarten en analyses. "
            "Vanuit welk perspectief wil je de data bekijken?"
        ),
        acties=acties,
        indicatoren=[],
        debug={"mode": "deterministic_onboarding"}
    )

def match_scenario(vraag: str, context: dict, db: Session):
    """Matcht een deterministisch scenario op basis van rol_code of trigger_keywords."""
    rol_code = context.get("rol_code")
    from sqlalchemy import text
    if rol_code:
        try:
            scenario = db.execute(text(
                "SELECT * FROM chat_scenarios WHERE rol_code = :code AND is_actief = true"
            ), {"code": rol_code}).fetchone()
            if scenario:
                return scenario
        except Exception as e:
            AppLogger.error(f"Error matching scenario by rol_code: {e}", category="LLM_CHAT")
            
    # Fallback: vrije tekst match op trigger_keywords
    vraag_lower = vraag.lower().strip()
    try:
        scenarios = db.execute(text("SELECT * FROM chat_scenarios WHERE is_actief = true")).fetchall()
        for scenario in scenarios:
            keywords = scenario.trigger_keywords or []
            if any(kw in vraag_lower for kw in keywords):
                return scenario
    except Exception as e:
        AppLogger.error(f"Error matching scenario by keywords: {e}", category="LLM_CHAT")
        
    return None

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
# Datavraag (#149): grounded antwoord met cijfers uit de database
# ============================================================================

def datavraag_acties(resultaat: Dict[str, Any]) -> List[ActieKnop]:
    """Toon op kaart (indicator + gebieden), Open Kompas en Rapport, met de bestaande actietypes."""
    gebied_ids = resultaat.get("gebied_ids") or None
    gebiedstype_id = resultaat.get("gebiedstype_id")
    gemeente_code = resultaat.get("gemeente_code")
    acties = []
    for f in resultaat.get("feiten", [])[:2]:
        acties.append(ActieKnop(
            type="TOON_OP_KAART",
            label=f"🗺 Toon op kaart: {f['indicator']}",
            indicator_uuid=f["indicator_uuid"],
            gebied_ids=gebied_ids,
            gebiedstype_id=gebiedstype_id,
            gemeente_code=gemeente_code,
        ))
    if not acties:
        for t in resultaat.get("indicatoren", [])[:1]:
            acties.append(ActieKnop(type="TOON_OP_KAART", label=f"🗺 Toon op kaart: {t.naam}",
                                    indicator_uuid=t.uuid))
    if gebied_ids:
        acties.append(ActieKnop(type="OPEN_KOMPAS", label="🧭 Open Kompas", gebied_ids=gebied_ids,
                                gebiedstype_id=gebiedstype_id, gemeente_code=gemeente_code))
        acties.append(ActieKnop(type="MAAK_RAPPORT", label="📄 Rapport", gebied_ids=gebied_ids))
    return acties


def beantwoord_datavraag_route(vraag: str, context: Dict[str, Any], db: Session) -> Optional[ChatResponse]:
    """ChatResponse voor een datavraag, of None (dan de gewone navigatieroute)."""
    zoeker = {}

    def zoek(tekst: str):
        # AI-zoeken pas laden als het nodig is (model laden kost tijd)
        if "service" not in zoeker:
            zoeker["service"] = AISearchService(db)
        return zoeker["service"].search_indicators(tekst, limit=5)

    llm = LLMService(db)
    llm_call = getattr(llm, "_call_llm", None) or llm._call_ollama  # #88: _call_llm kiest de aanbieder

    def vraag_llm(systeem: str, gebruiker: str):
        systeem = llm.get_system_prompt("chat_datavraag", systeem)
        return llm_call(systeem, gebruiker, context_name="Chat Datavraag")

    resultaat = beantwoord_datavraag(vraag, context, db, zoek, vraag_llm)
    if resultaat is None:
        return None

    feiten = resultaat["feiten"]
    gegevens = [
        Gegeven(
            indicator_uuid=f["indicator_uuid"], indicator=f["indicator"], gebied_id=w["gebied_id"],
            gebied=w["gebied"], waarde=w["waarde"], jaar=w.get("jaar"), eenheid=f["eenheid"] or None,
            richting=f["richting"], rang_hoog=w["rang_hoog"], aantal_gebieden=f["aantal_gebieden"],
            demo=w["demo"],
        )
        for f in feiten for w in f["waarden"]
    ]
    bronnen = [BronRegel(indicator=f["indicator"], bron=f["bron"], jaren=[j for j in f["jaren"] if j])
               for f in feiten]
    indicatoren_out = [
        IndicatorResultaat(uuid=t.uuid, naam=t.naam, relevantie=round(min(t.score, 1.0), 4))
        for t in resultaat["indicatoren"]
    ]
    AppLogger.info(
        f"DATAVRAAG: {len(feiten)} indicator(en), {len(resultaat['gebied_ids'])} gebied(en), "
        f"llm={resultaat['llm_gebruikt']}, verworpen getallen={resultaat['ongegrond']}",
        category="LLM_CHAT")
    return ChatResponse(
        intent="DATAVRAAG",
        narrative=resultaat["narrative"],
        acties=datavraag_acties(resultaat),
        indicatoren=indicatoren_out,
        bronnen=bronnen,
        gegevens=gegevens,
        kaart_actie=({
            "gebiedstype_id": resultaat.get("gebiedstype_id"),
            "gemeente_code": resultaat.get("gemeente_code"),
            "indicator_uuid": feiten[0]["indicator_uuid"],
            "indicator": feiten[0]["indicator"],
            "gebied_ids": resultaat["gebied_ids"],
        } if feiten and resultaat.get("gebied_ids") else None),
        debug={
            "mode": "datavraag",
            "llm_gebruikt": resultaat["llm_gebruikt"],
            "model": resultaat.get("model"),
            # getallen die het model verzon; dan is het antwoord de vaste tekst uit de cijfers
            "verworpen_getallen": resultaat["ongegrond"],
            "llm_fout": resultaat.get("llm_fout", False),
            "herkend": resultaat["herkend"],
            "gebieden_bron": resultaat["gebieden_bron"],
        },
    )


# ============================================================================
# Chat Endpoint
# ============================================================================

# LLM_RATE_LIMIT per minuut per IP (#203)
@router.post("", response_model=ChatResponse, dependencies=[Depends(beperk_llm)])
def chat(
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
    # Stap 0a: Help/Onboarding — instant, geen LLM nodig
    # ------------------------------------------------
    if is_help_onboarding(vraag):
        AppLogger.info("HELP_ONBOARDING intent — deterministic response", category="LLM_CHAT")
        return get_help_onboarding_response(db)

    # ------------------------------------------------
    # Stap 0b: Datavraag — antwoord met cijfers uit de database (#149).
    # Een gekozen rol (knop) gaat voor; geen datavraag → gewone route hieronder.
    # ------------------------------------------------
    if not context.get("rol_code"):
        try:
            datavraag = beantwoord_datavraag_route(vraag, context, db)
        except Exception as e:
            db.rollback()
            AppLogger.error(f"Datavraag mislukt, terugval op navigatie: {e}", category="LLM_CHAT")
            datavraag = None
        if datavraag is not None:
            return datavraag

    # ------------------------------------------------
    # Stap 0c: Check of een scenario is getriggerd
    # ------------------------------------------------
    scenario = match_scenario(vraag, context, db)
    if scenario:
        AppLogger.info(f"SCENARIO getriggerd: {scenario.rol_code}", category="LLM_CHAT")
        acties_db = scenario.acties or []
        acties = []
        for a in acties_db:
            try:
                acties.append(ActieKnop(**a))
            except Exception:
                pass
                
        return ChatResponse(
            intent="SCENARIO_" + scenario.rol_code.upper(),
            narrative=scenario.narrative,
            acties=acties,
            indicatoren=[],
            debug={"mode": "deterministic_scenario", "rol_code": scenario.rol_code}
        )
    
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

        # Gemeentekeuze van het model controleren tegen de database (#140)
        try:
            aantal_voor = len(acties_data or [])
            acties_data = valideer_gemeente_acties(acties_data, db)
            if len(acties_data) < aantal_voor:
                AppLogger.warning(
                    f"{aantal_voor - len(acties_data)} ongeldige SELECTEER_GEMEENTE-actie(s) weggelaten",
                    category="LLM_CHAT")
        except Exception as e:
            db.rollback()
            AppLogger.error(f"Gemeentevalidatie mislukt, gemeente-acties weggelaten: {e}", category="LLM_CHAT")
            acties_data = [a for a in (acties_data or [])
                           if not (isinstance(a, dict) and a.get("type") == "SELECTEER_GEMEENTE")]
        
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
def chat_health():
    """Health check voor de Chat API."""
    return {"status": "healthy", "service": "D-Omni Assistant Chat API"}

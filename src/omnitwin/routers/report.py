"""
Rapporten (/api/report/*) zijn publiek: ze tonen niet meer dan een anonieme
bezoeker in de app ziet (#65). Daarom:
- debug_info (systeemprompts, model) alleen voor een ingelogde beheerder;
- AI-teksten kort gecachet, zodat herhaald opvragen niet steeds een
  LLM-aanroep start. Dit is geen rate-limit: andere gebieden starten nog
  steeds een aanroep.
- AI-samenvattingen alleen met AI-usecase B open (#307); dicht: het rapport zonder
  AI-tekst, met een melding op die plek (`ai_uit`).
"""
import threading
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from omnitwin import ai_vrijgave
from omnitwin.database import get_db
from omnitwin.fouten import GebruikersFout
from omnitwin.grenzen import beperk_llm
from omnitwin.services.report_service import ReportDataService
from omnitwin.services.llm_service import LLMService
from omnitwin.oidc import AuthProbleem
from omnitwin.routers.auth import huidige_gebruiker


def _is_beheerder(request: Request, db: Session) -> bool:
    try:
        return bool(huidige_gebruiker(request, db).get("is_admin"))
    except (HTTPException, AuthProbleem):  # niet ingelogd, of ongeldig bearer-token
        return False


# Kleine in-memory cache per worker voor AI-teksten (sleutel -> (tijd, waarde))
_AI_CACHE: Dict[tuple, tuple] = {}
_AI_CACHE_TTL = 3600
_AI_CACHE_MAX = 256
_AI_CACHE_LOCK = threading.Lock()


def _cache_get(key: tuple):
    with _AI_CACHE_LOCK:
        hit = _AI_CACHE.get(key)
        if hit and time.monotonic() - hit[0] < _AI_CACHE_TTL:
            return hit[1]
        _AI_CACHE.pop(key, None)
        return None


def _cache_put(key: tuple, value) -> None:
    with _AI_CACHE_LOCK:
        if len(_AI_CACHE) >= _AI_CACHE_MAX:
            _AI_CACHE.pop(min(_AI_CACHE, key=lambda k: _AI_CACHE[k][0]))
        _AI_CACHE[key] = (time.monotonic(), value)


# ─── Pydantic Models ────────────────────────────────────────────────────────

class MultiGebiedRequest(BaseModel):
    """Request model voor Multi-Gebiedsdossier endpoints."""
    gebied_ids: List[str] = Field(..., min_length=1, max_length=200, description="CBS buurt-IDs")
    referentie: str = Field('gemeente', description="'gemeente' of 'fryslan'")
    gemeente_code: Optional[str] = Field(None, description="Gemeentecode voor de referentie (standaard: die van de eigen organisatie, GET /api/organisatie)")
    deelgebied_naam: Optional[str] = Field(None, description="Label voor de rapportheader")
    thema: Optional[str] = Field(None, description="Thema filter (bijv. 'Kwaliteit van Leven')")

class ThemaAnalyseRequest(BaseModel):
    """Request model voor Thema-Analyse rapport."""
    gebied_ids: List[str] = Field(..., min_length=1, max_length=200)
    referentie: str = Field('gemeente')
    gemeente_code: Optional[str] = Field(None, description="Gemeentecode voor de referentie (standaard: die van de eigen organisatie, GET /api/organisatie)")
    deelgebied_naam: Optional[str] = Field(None)
    categorie: Optional[str] = Field(None, description="Niveau 0: bijv. 'Kwaliteit fysieke leefomgeving'")
    thema_naam: Optional[str] = Field(None, description="Niveau 1: bijv. 'Verkeer'")
    onderdeel_naam: Optional[str] = Field(None, description="Niveau 2: bijv. 'Bereikbaarheid en parkeren'")

class DeelgebiedAnalyseRequest(BaseModel):
    """Request model voor Woonplaats- & Deelgebiedsanalyse (Sjabloon F)."""
    gebied_ids: List[str] = Field(..., min_length=1, max_length=500, description="CBS buurt-IDs")
    referentie: str = Field('gemeente', description="'gemeente' of 'fryslan'")
    gemeente_code: Optional[str] = Field(None, description="Gemeentecode (optioneel, wordt automatisch afgeleid indien niet meegegeven)")
    deelgebied_naam: Optional[str] = Field(None, description="Label voor het deelgebied of woonplaats (bijv. 'Sneek')")


router = APIRouter(
    prefix="/api/report",
    tags=["Report"]
)

@router.get("/data/{gebied_id}", response_model=Dict[str, Any])
def get_report_data(gebied_id: str, db: Session = Depends(get_db)):
    """
    Fase 1: Genereert de geaggregeerde payload.
    Berekent Z-scores per indicator voor een gebied en filtert de uitschieters.
    """
    service = ReportDataService(db)
    try:
        return service.generate_report_payload(gebied_id)
    except GebruikersFout as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/narrative/{gebied_id}", response_model=Dict[str, Any], dependencies=[Depends(beperk_llm)])
def generate_report_narrative(gebied_id: str, request: Request, db: Session = Depends(get_db)):
    """
    Fase 2: Roept Ollama aan om een narrative (Executive Summary) te genereren
    op basis van de data uit Fase 1 per kwadrant.
    """
    # AI-usecase B dicht (#307): geen taalmodel, ook niet uit de cache
    if not ai_vrijgave.poort(ai_vrijgave.B, "Rapport: samenvatting", taak=f"Rapportsamenvatting gebied {gebied_id}"):
        return {"gebied_id": gebied_id, "ai_summary": ai_vrijgave.melding(ai_vrijgave.B),
                "domain_summaries": {}, "status": "ai_uit", "ai_uit": True}
    report_service = ReportDataService(db)
    llm_service = LLMService(db)
    beheerder = _is_beheerder(request, db)
    cache_key = ("narrative", gebied_id)
    cached = _cache_get(cache_key)
    if cached is not None and not beheerder:
        return cached

    try:
        data_payload = report_service.generate_report_payload(gebied_id)
        llm_fout = False

        domain_summaries_text = {}
        domain_responses = {}
        debug_logs = []
        
        # 1. Genereer per kwadrant/domein een samenvatting
        for domain_name, indicators in data_payload.get("significante_domeinen", {}).items():
            result = llm_service.generate_domain_summary(domain_name, indicators)
            llm_fout = llm_fout or result.get("error", False)
            domain_summaries_text[domain_name] = result["text"]
            domain_responses[domain_name] = result["text"]
            debug_logs.append(result["debug"])
            
        # 2. Genereer de overkoepelende samenvatting als er domein data is
        overall_summary_text = "Geen significante afwijkingen gevonden om samen te vatten."
        if domain_summaries_text:
            overall_result = llm_service.generate_overall_summary(domain_summaries_text, data_payload.get("metadata", {}))
            overall_summary_text = overall_result["text"]
            llm_fout = llm_fout or overall_result.get("error", False)
            debug_logs.append(overall_result["debug"])

        antwoord = {
            "gebied_id": gebied_id,
            "ai_summary": overall_summary_text,
            "domain_summaries": domain_responses,
            "status": "success",
            "ai": {"usecase": ai_vrijgave.B} if domain_summaries_text and not llm_fout else None,  # #312: label AI
        }
        if not llm_fout:
            _cache_put(cache_key, antwoord)
        if beheerder:
            return {**antwoord, "debug_info": debug_logs}
        return antwoord

    except GebruikersFout as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── Sjabloon C: Benchmark Vergelijker ───────────────────────────────────────

@router.get("/benchmark", response_model=Dict[str, Any])
def get_benchmark_data(
    gebied_a: str = Query(..., description="Gebied ID van het referentiegebied"),
    mode: str = Query("gebieden", description="Vergelijkingsmodus: 'gebieden', 'gemeente' of 'fryslan'"),
    gebieden_b: Optional[str] = Query(None, description="Komma-gescheiden lijst van vergelijkingsgebied IDs (max 5)"),
    referentie_gemeente: Optional[str] = Query(None, description="Gemeente code voor gemeente-gemiddelde modus"),
    db: Session = Depends(get_db)
):
    """
    Sjabloon C — Benchmark Vergelijker.
    Vergelijkt Gebied A met een referentie op basis van 3 modi:
    - 'gebieden': specifieke gebieden (1-op-1 of 1-op-n, max 5)
    - 'gemeente': gemiddelde van alle buurten in een gemeente
    - 'fryslan': gemiddelde van alle buurten in Fryslân
    """
    service = ReportDataService(db)
    try:
        gebieden_b_list = [g.strip() for g in gebieden_b.split(",") if g.strip()] if gebieden_b else []
        return service.generate_benchmark_payload(
            gebied_id_a=gebied_a,
            mode=mode,
            gebieden_b=gebieden_b_list,
            referentie_gemeente=referentie_gemeente
        )
    except GebruikersFout as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/benchmark/narrative", response_model=Dict[str, Any], dependencies=[Depends(beperk_llm)])
def get_benchmark_narrative(
    request: Request,
    gebied_a: str = Query(..., description="Gebied ID van het referentiegebied"),
    mode: str = Query("gebieden", description="Vergelijkingsmodus"),
    gebieden_b: Optional[str] = Query(None, description="Komma-gescheiden vergelijkingsgebied IDs"),
    referentie_gemeente: Optional[str] = Query(None, description="Gemeente code"),
    db: Session = Depends(get_db)
):
    """
    AI narrative voor de benchmark vergelijking.
    Genereert een analyse van de belangrijkste delta's via Ollama.
    """
    if not ai_vrijgave.poort(ai_vrijgave.B, "Rapport: benchmark", taak=f"Benchmarksamenvatting gebied {gebied_a}"):
        return {"gebied_a": {"id": gebied_a, "naam": gebied_a}, "referentie_label": "",
                "ai_narrative": ai_vrijgave.melding(ai_vrijgave.B), "status": "ai_uit", "ai_uit": True}
    report_service = ReportDataService(db)
    llm_service = LLMService(db)
    beheerder = _is_beheerder(request, db)

    try:
        gebieden_b_list = [g.strip() for g in gebieden_b.split(",") if g.strip()] if gebieden_b else []
        cache_key = ("benchmark", gebied_a, mode, tuple(gebieden_b_list), referentie_gemeente)
        cached = _cache_get(cache_key)
        if cached is not None and not beheerder:
            return cached
        benchmark_data = report_service.generate_benchmark_payload(
            gebied_id_a=gebied_a,
            mode=mode,
            gebieden_b=gebieden_b_list,
            referentie_gemeente=referentie_gemeente
        )
        
        result = llm_service.generate_benchmark_narrative(benchmark_data)
        
        antwoord = {
            "gebied_a": benchmark_data["gebied_a"],
            "referentie_label": benchmark_data["referentie_label"],
            "ai_narrative": result["text"],
            "status": "success",
            "ai": None if result.get("error") else {"usecase": ai_vrijgave.B},  # #312
        }
        if not result.get("error"):
            _cache_put(cache_key, antwoord)
        if beheerder:
            return {**antwoord, "debug_info": [result["debug"]]}
        return antwoord
    except GebruikersFout as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Sjabloon A: Executive Summary ──────────────────────────────────────────

@router.get("/executive/{gebied_id}", response_model=Dict[str, Any])
def get_executive_data(gebied_id: str, db: Session = Depends(get_db)):
    """
    Sjabloon A — Executive Summary (1-pager).
    Retourneert top 3 kansen en top 3 risico's.
    """
    service = ReportDataService(db)
    try:
        return service.generate_executive_payload(gebied_id)
    except GebruikersFout as e:
        raise HTTPException(status_code=404, detail=str(e))


# ─── Sjabloon D: Multi-Gebiedsdossier ────────────────────────────────────────

@router.post("/multi-gebied", response_model=Dict[str, Any])
def get_multi_gebied_data(payload: MultiGebiedRequest, db: Session = Depends(get_db)):
    """
    Multi-Gebiedsdossier — Analyse payload.
    Berekent per buurt de indicator met de sterkste z-score afwijking,
    genereert een thema-aggregaat en rangschikt de uitschieters.
    """
    service = ReportDataService(db)
    try:
        return service.generate_multi_gebied_payload(
            gebied_ids=payload.gebied_ids,
            referentie=payload.referentie,
            gemeente_code=payload.gemeente_code,
            deelgebied_naam=payload.deelgebied_naam,
            thema=payload.thema
        )
    except GebruikersFout as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/multi-gebied/geojson", response_model=Dict[str, Any])
def get_multi_gebied_geojson(payload: MultiGebiedRequest, db: Session = Depends(get_db)):
    """
    Multi-Gebiedsdossier — GeoJSON voor choropleth.
    Retourneert een FeatureCollection met geometrieën en kleurcodering per buurt.
    """
    service = ReportDataService(db)
    try:
        return service.generate_multi_gebied_geojson(
            gebied_ids=payload.gebied_ids,
            referentie=payload.referentie,
            gemeente_code=payload.gemeente_code,
            thema=payload.thema
        )
    except GebruikersFout as e:
        raise HTTPException(status_code=400, detail=str(e))

# ─── Sjabloon E: Thema-Analyse ───────────────────────────────────────────────

@router.post("/thema-analyse", response_model=Dict[str, Any])
def get_thema_analyse_data(payload: ThemaAnalyseRequest, db: Session = Depends(get_db)):
    """
    Thema-Analyse — Analyse payload.
    Berekent de z-scores en waarden voor alle indicatoren binnen het 
    opgegeven thema/subthema zonder de top-3 limiet te forceren.
    """
    service = ReportDataService(db)
    try:
        return service.generate_thema_analyse_payload(
            gebied_ids=payload.gebied_ids,
            referentie=payload.referentie,
            gemeente_code=payload.gemeente_code,
            deelgebied_naam=payload.deelgebied_naam,
            categorie=payload.categorie,
            thema_naam=payload.thema_naam,
            onderdeel_naam=payload.onderdeel_naam
        )
    except GebruikersFout as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/thema-analyse/geojson", response_model=Dict[str, Any])
def get_thema_analyse_geojson(payload: ThemaAnalyseRequest, db: Session = Depends(get_db)):
    """
    Thema-Analyse — GeoJSON voor choropleth.
    Retourneert een FeatureCollection met geometrieën en kleurcodering gebaseerd
    op het gemiddelde z-score van alle indicatoren binnen de thema selectie.
    """
    service = ReportDataService(db)
    try:
        return service.generate_thema_analyse_geojson(
            gebied_ids=payload.gebied_ids,
            referentie=payload.referentie,
            gemeente_code=payload.gemeente_code,
            categorie=payload.categorie,
            thema_naam=payload.thema_naam,
            onderdeel_naam=payload.onderdeel_naam
        )
    except GebruikersFout as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Sjabloon F: Woonplaats- & Deelgebiedsanalyse ─────────────────────────────

@router.post("/deelgebied", response_model=Dict[str, Any])
def get_deelgebied_analyse_data(payload: DeelgebiedAnalyseRequest, db: Session = Depends(get_db)):
    """
    Sjabloon F: Woonplaats- & Deelgebiedsanalyse.
    Berekent een gewogen stads-/deelgebiedsgemiddelde op basis van inwoneraantallen,
    geaggregeerd per thema met Top 10 uitschieters (aandachtspunten en kansen),
    buurt-drilldowns en methodologische verantwoording.
    """
    service = ReportDataService(db)
    try:
        return service.generate_deelgebied_payload(
            gebied_ids=payload.gebied_ids,
            referentie=payload.referentie,
            gemeente_code=payload.gemeente_code,
            deelgebied_naam=payload.deelgebied_naam
        )
    except GebruikersFout as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/deelgebied/kaart", response_model=Dict[str, Any])
def get_deelgebied_kaart(payload: DeelgebiedAnalyseRequest, db: Session = Depends(get_db)):
    """
    Genereert een inline SVG choropleet van de geselecteerde buurten,
    ingekleurd op de gewogen gemiddelde Z-score per buurt.
    Retourneert {"svg": "<svg ...>...</svg>"}
    """
    service = ReportDataService(db)
    try:
        svg = service.generate_deelgebied_svg_kaart(
            gebied_ids=payload.gebied_ids,
            referentie=payload.referentie,
            gemeente_code=payload.gemeente_code,
            deelgebied_naam=payload.deelgebied_naam
        )
        return {"svg": svg}
    except GebruikersFout as e:
        raise HTTPException(status_code=400, detail=str(e))

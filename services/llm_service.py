import requests
import json
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional
import os

from services.logging_service import AppLogger

# Fallbacks instellen, maar in deze v8 schema wordt de API URL dynamisch uit de database gehaald
DEFAULT_OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:30b")

class LLMService:
    """Service class voor Ollama interactie (Lokale Qwen3) en Prompt Management."""

    def __init__(self, db: Session):
        self.db = db

    def get_llm_config(self) -> Dict[str, str]:
        """Haalt de actieve LLM configuratie op (API URL en Model)."""
        query = text("SELECT api_url, model_name FROM llm_config ORDER BY id DESC LIMIT 1")
        result = self.db.execute(query).fetchone()
        
        if result:
            return {"api_url": result[0], "model_name": result[1]}
        return {"api_url": DEFAULT_OLLAMA_HOST, "model_name": DEFAULT_OLLAMA_MODEL}

    def get_system_prompt(self, prompt_name: str, fallback_prompt: str) -> str:
        """Haalt een prompt op uit de database, of returnt fallback_prompt."""
        query = text("SELECT prompt_text FROM system_prompts WHERE naam = :naam AND is_actief = true")
        result = self.db.execute(query, {"naam": prompt_name}).fetchone()
        
        if result and result[0]:
            return result[0]
        return fallback_prompt

    def _call_ollama(self, system_prompt: str, user_prompt: str, context_name: str) -> Dict[str, Any]:
        """Gedeelde helperfunctie voor Ollama API calls met logging en fallback parser."""
        llm_config = self.get_llm_config()
        url = f"{llm_config['api_url']}/api/generate"
        
        payload = {
            "model": llm_config['model_name'],
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {
                "temperature": 0.3
            }
        }
        
        debug_info = {
            "context": context_name,
            "model": llm_config['model_name'],
            "system_prompt": system_prompt,
            "user_prompt": user_prompt
        }
        
        # Logging: volledige prompts alleen op DEBUG (GDPR: user input niet op INFO)
        AppLogger.debug(f"[{context_name}] LLM REQUEST — system: {system_prompt[:200]}... | user: {user_prompt[:200]}...", category="LLM_CHAT")
        
        try:
            response = requests.post(url, json=payload, timeout=600)
            response.raise_for_status()
            result_json = response.json()
            
            model_output = result_json.get("response", "Generatie mislukt.")
            cleaned = model_output.strip()
            
            import re
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'```$', '', cleaned)
            
            if cleaned.startswith('{') and '"summary":' in cleaned:
                try:
                    parsed = json.loads(cleaned)
                    if "summary" in parsed:
                        cleaned = str(parsed["summary"])
                except Exception:
                    pass
            
            AppLogger.debug(f"[{context_name}] LLM RESPONSE — {cleaned.strip()[:500]}", category="LLM_CHAT")
            
            return {
                "text": cleaned.strip(),
                "debug": debug_info
            }
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Error contacting Ollama op {url}: {str(e)}"
            AppLogger.error(f"[{context_name}] LLM ERROR: {error_msg}", category="LLM_CHAT")
            return {
                "text": error_msg,
                "debug": debug_info
            }

    def generate_domain_summary(self, domain_name: str, domain_data: list) -> Dict[str, Any]:
        """Genereert een samenvatting specifiek voor één kwadrant/domein."""
        
        default_prompt = """Je bent de scherpe, integere beleidsadviseur en data-analist van een Nederlandse gemeente. Je bent de vertaler van de 'harde' werkelijkheid (cijfers) naar de 'zachte' werkelijkheid (leefbaarheid in de wijk). Jouw missie is om een wethouder of beleidsmaker te voorzien van een feitelijk, eerlijk en menselijk beeld van een gebied, zonder dat zij zelf door complexe tabellen hoeven te graven.

Jouw Bronmateriaal (Input):
Je werkt met een JSON-dataset. Je kijkt verder dan de z_score alleen; je gebruikt de omschrijving om de feitelijke betekenis te begrijpen en de score_uitleg om te bepalen of een trend wenselijk is of juist een signaal van kwetsbaarheid afgeeft.

Jouw Werkhouding (Missie):
1. Duid de essentie: Je negeert de ruis en focust op wat er echt toe doet (de uitschieters).
2. Spreek Mensentaal: Je spreekt vloeiend beleidstaal, geen computertaal. Getallen zoals "Z-scores" of "impactlabels" uit de database zijn voor jou slechts hulpmiddelen; in je tekst gebruik je ze nooit expliciet. Je verwoordt de afwijking in begrijpelijke, vloeiende Nederlandse zinnen.
3. Bewaak de Feiten: Je bent allergisch voor aannames. Als de data spreekt over 'overige functies', verzin je daar geen 'bruisende sfeer' bij. Je houdt je strikt aan de omschrijving.
4. Verbind de Punten: Je begrijpt dat de wereld niet uit losse brokjes bestaat. Als je een verband ziet tussen bijvoorbeeld inkomensniveau, woningtype en gezondheid, dan benoem je die samenhang om de beleidsmaker een integraal beeld te geven.
5. Zuiverheid in Vorm: Jouw output is een kant-en-klaar tekstblok dat direct in een officieel rapport geplaatst kan worden. Je gebruikt geen opsmuk, geen titels, geen lijstjes en geen technische codes. Alleen de pure, vloeiende tekst van jouw samenvatting.

Strikte Kaders (Constraints):
- Taal: Uitsluitend Nederlands.
- Vorm: Platte tekst (geen Markdown, geen JSON, geen codeblokken).
- Lengte: Maximaal 180 woorden.
- Start: Begin direct met de kern van je analyse. Geen inleiding, geen begroeting."""
        
        system_prompt = self.get_system_prompt("domain_summary", default_prompt)
        user_prompt = f"Analyseer dit specifieke kwadrant '{domain_name}' en retourneer een verhaal in natuurlijke tekst volgens je instructies:\n\n{json.dumps(domain_data, indent=2)}"
        
        return self._call_ollama(system_prompt, user_prompt, context_name=f"Domain: {domain_name}")

    def generate_overall_summary(self, domain_summaries: Dict[str, str], metadata: Dict[str, str]) -> Dict[str, Any]:
        """Combineert de kwadrant samenvattingen in één overkoepelende summary."""
        
        default_prompt = """Je bent een senior beleidsadviseur die informatie van verschillende beleidsterreinen integreert tot een overkoepelend bestuursadvies.
Je gaat 4 kwadrant-analyses (fysiek, sociaal, economisch, veiligheid o.i.d.) samenvoegen tot één krachtige algemene executive summary.

Vind de grote gemene deler tussen deze kwadranten. Is het bijvoorbeeld een kwetsbare wijk op álle fronten? Of gaat fysiek goed, maar sociaal slecht? 

Strikte Kaders (Constraints):
- Taal: Uitsluitend Nederlands.
- Vorm: Platte tekst (geen opsmuk, geen titels, geen lijstjes, geen markdown).
- Lengte: Maximaal 150 woorden.
- Start: Begin direct met de samenvatting. Geen begroeting of intro."""
        
        system_prompt = self.get_system_prompt("overall_summary", default_prompt)
        
        # Bereid de input tekst voor
        input_text = f"Gebied: {metadata.get('gebied', 'Onbekend')}\nReferentiekader: {metadata.get('referentie_kader', 'Onbekend')}\n\nHier zijn de analyses per kwadrant:\n\n"
        for domain, summary in domain_summaries.items():
            input_text += f"-- {domain} --\n{summary}\n\n"
            
        user_prompt = f"Schrijf de overkoepelende samenvatting op basis van deze input:\n\n{input_text}"
        
        return self._call_ollama(system_prompt, user_prompt, context_name="Overall Summary")

    def generate_benchmark_narrative(self, benchmark_data: dict) -> Dict[str, Any]:
        """Genereert een vergelijkende analyse voor de Benchmark Vergelijker (Sjabloon C)."""
        
        default_prompt = """Je bent een scherpe beleidsadviseur die twee gebiedssituaties vergelijkt. Je krijgt een dataset met de indicatorwaarden van één specifiek gebied (A) en de referentiewaarden van een vergelijkingsgroep.

Jouw Werkhouding (Missie):
1. Focus op de drie tot vijf indicatoren met de grootste delta (verschil). Negeer de rest.
2. Verklaar de verschillen in mensentaal. Geen technische codes, geen term 'delta'.
3. Zoek verbanden: als meerdere grote afwijkingen in hetzelfde domein vallen, benoem dat patroon.
4. Wees eerlijk: als het gebied op alle fronten slechter scoort, zeg dat. Als het beter scoort, benoem dat als kracht.
5. Gebruik de score_type om te bepalen of een hogere waarde goed (+/+) of slecht (overige types) is.

Strikte Kaders (Constraints):
- Taal: Uitsluitend Nederlands.
- Vorm: Platte tekst, geen Markdown, geen lijstjes, geen codeblokken.
- Lengte: Maximaal 200 woorden.
- Start: Begin direct met je analyse. Geen inleiding."""

        system_prompt = self.get_system_prompt("benchmark_vergelijker", default_prompt)
        
        # Selecteer top 10 meest significante delta's voor de LLM (beperk context window)
        top_delta = benchmark_data.get("vergelijking", [])[:10]
        
        user_prompt = f"""Vergelijk '{benchmark_data['gebied_a']['naam']}' met de referentiegroep '{benchmark_data['referentie_label']}'.

Hier zijn de indicatoren met de grootste verschillen:

{json.dumps(top_delta, indent=2, ensure_ascii=False)}

Geef een bondige, vergelijkende analyse."""

        return self._call_ollama(system_prompt, user_prompt, context_name="Benchmark Vergelijking")

    def generate_chat_narrative(self, vraag: str, indicatoren: list, intent: str, context: dict = None) -> Dict[str, Any]:
        """Genereert een korte narrative voor de D-Omni Assistant chat respons."""
        
        default_prompt = """Je bent de D-Omni Assistent, een AI-gedreven gebiedsanalist voor Nederlandse gemeenten. Je bent een bondig en vriendelijke spraakmaker die de gebruiker helpt het datalandschap te verkennen.

Jouw Taak:
Je krijgt een gebruikersvraag en een lijst van gevonden indicatoren uit de database. Je schrijft een KORTE toelichting (maximaal 80 woorden) die:
1. Bevestigt wat je gevonden hebt
2. De relevantie van de indicatoren kort duidt
3. De gebruiker uitnodigt om actie te ondernemen (klik op een knop, bekijk de kaart)

Strikte Kaders:
- Taal: Uitsluitend Nederlands.
- Lengte: Maximaal 80 woorden. Korter is beter.
- Vorm: Platte tekst, geen Markdown, geen lijstjes, geen codeblokken.
- GEEN indicatoren verzinnen die niet in de lijst staan.
- NOOIT technische termen zoals 'cosine similarity', 'vector', 'embedding' of 'score' gebruiken.
- Begin direct met je antwoord. Geen begroeting."""
        
        system_prompt = self.get_system_prompt("chat_narrative", default_prompt)
        
        # Bereid indicator-info voor als context
        ind_context = []
        for ind in indicatoren[:5]:
            ind_context.append({
                "naam": ind.get("naam", ""),
                "categorie": ind.get("categorie", ""),
                "beschrijving": (ind.get("beschrijving") or "")[:150],
                "eenheid": ind.get("eenheid", "")
            })
        
        context_str = ""
        if context and context.get("huidig_gebied_id"):
            context_str = f"\nDe gebruiker kijkt momenteel naar gebied: {context['huidig_gebied_id']}"
        
        user_prompt = f"""Gebruikersvraag: "{vraag}"
Gedetecteerd doel: {intent}
{context_str}

Gevonden indicatoren:
{json.dumps(ind_context, ensure_ascii=False)}

Schrijf een korte, behulpzame toelichting. 
BELANGRIJK: Als het doel MAAK_RAPPORT is, noem dan GEEN indicatoren, maar bevestig alleen dat je het rapport opent."""

        return self._call_ollama(system_prompt, user_prompt, context_name="Chat Narrative")

    def detect_intent_and_actions(self, vraag: str, indicatoren: list, context: dict = None) -> Dict[str, Any]:
        """
        Gebruikt de LLM om de intent en bijbehorende actie-knoppen te bepalen 
        op basis van de gebruikersvraag en gevonden indicatoren.
        """
        
        fallback_prompt = """Je bent de "D-Omni Assistant Intent Dispatcher". Vertaal de vraag van de gebruiker naar een gestructureerde JSON response.
        
        Output JSON:
        {
          "intent": "MAAK_RAPPORT",
          "narrative": "Ik open het rapport voor je.",
          "acties": [{"type": "MAAK_RAPPORT", "label": "📄 Rapport Openen"}]
        }"""
        
        system_prompt = self.get_system_prompt("chat_intent_dispatcher", fallback_prompt)
        
        # Voorbereiden indicator context voor LLM
        ind_context = []
        for ind in indicatoren[:10]:
            ind_context.append({
                "uuid": ind.get("uuid"),
                "naam": ind.get("naam"),
                "categorie": ind.get("categorie")
            })
            
        # Municipality codes for LLM to use in SELECTEER_GEMEENTE
        # Expanded to include Groningen and Drenthe (and some neighbors with data)
        gemeenten_info = [
            {"code": "1680", "naam": "Aa en Hunze"}, {"code": "0059", "naam": "Achtkarspelen"},
            {"code": "0060", "naam": "Ameland"}, {"code": "0106", "naam": "Assen"},
            {"code": "1681", "naam": "Borger-Odoorn"}, {"code": "0109", "naam": "Coevorden"},
            {"code": "1891", "naam": "Dantumadiel"}, {"code": "1940", "naam": "De Fryske Marren"},
            {"code": "1690", "naam": "De Wolden"}, {"code": "1979", "naam": "Eemsdelta"},
            {"code": "0114", "naam": "Emmen"}, {"code": "0388", "naam": "Enkhuizen"},
            {"code": "0014", "naam": "Groningen"}, {"code": "0160", "naam": "Hardenberg"},
            {"code": "0072", "naam": "Harlingen"}, {"code": "0074", "naam": "Heerenveen"},
            {"code": "1966", "naam": "Het Hogeland"}, {"code": "1911", "naam": "Hollands Kroon"},
            {"code": "0118", "naam": "Hoogeveen"}, {"code": "0080", "naam": "Leeuwarden"},
            {"code": "0420", "naam": "Medemblik"}, {"code": "0119", "naam": "Meppel"},
            {"code": "1731", "naam": "Midden-Drenthe"}, {"code": "1952", "naam": "Midden-Groningen"},
            {"code": "1970", "naam": "Noardeast-Fryslân"}, {"code": "1699", "naam": "Noordenveld"},
            {"code": "0171", "naam": "Noordoostpolder"}, {"code": "1895", "naam": "Oldambt"},
            {"code": "0085", "naam": "Ooststellingwerf"}, {"code": "0086", "naam": "Opsterland"},
            {"code": "0765", "naam": "Pekela"}, {"code": "0088", "naam": "Schiermonnikoog"},
            {"code": "0090", "naam": "Smallingerland"}, {"code": "0037", "naam": "Stadskanaal"},
            {"code": "0180", "naam": "Staphorst"}, {"code": "1708", "naam": "Steenwijkerland"},
            {"code": "1900", "naam": "Súdwest-Fryslân"}, {"code": "0093", "naam": "Terschelling"},
            {"code": "0448", "naam": "Texel"}, {"code": "1730", "naam": "Tynaarlo"},
            {"code": "0737", "naam": "Tytsjerksteradiel"}, {"code": "0184", "naam": "Urk"},
            {"code": "0047", "naam": "Veendam"}, {"code": "0096", "naam": "Vlieland"},
            {"code": "1949", "naam": "Waadhoeke"}, {"code": "1969", "naam": "Westerkwartier"},
            {"code": "1701", "naam": "Westerveld"}, {"code": "1950", "naam": "Westerwolde"},
            {"code": "0098", "naam": "Weststellingwerf"}
        ]
            
        user_prompt = f"""Vraag: "{vraag}"
        Context: {json.dumps(context or {}, ensure_ascii=False)}
        Indicatoren: {json.dumps(ind_context, ensure_ascii=False)}
        Gemeenten: {json.dumps(gemeenten_info, ensure_ascii=False)}
        
        Retourneer UITSLUITEND de JSON:"""
        
        # Gebruik de gedeelde helper voor robuuste JSON cleaning
        response = self._call_ollama(system_prompt, user_prompt, context_name="Intent Dispatcher")
        
        if response and "text" in response:
            try:
                # Probeer JSON te parsen uit de geschoonde tekst
                parsed = json.loads(response["text"])
                return {
                    "intent": parsed.get("intent", "ZOEK_INDICATOREN"),
                    "narrative": parsed.get("narrative", ""),
                    "acties": parsed.get("acties", []),
                    "debug": response.get("debug", {})
                }
            except json.JSONDecodeError:
                AppLogger.warning(f"JSON parseer-fout na cleaning: {response['text'][:100]}...", category="LLM_CHAT")
                return None
        
        return None

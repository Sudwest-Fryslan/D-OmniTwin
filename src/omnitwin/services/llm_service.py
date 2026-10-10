import requests
import json
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional
import re
from urllib.parse import urlsplit

from omnitwin import ai_logboek, ai_vrijgave
from omnitwin.config import instellingen
from omnitwin.services.logging_service import AppLogger
from omnitwin.services.gemeente_validatie import laad_gemeenten

# Fallbacks instellen, maar in deze v8 schema wordt de API URL dynamisch uit de database gehaald
DEFAULT_OLLAMA_HOST = instellingen().ollama_host
DEFAULT_OLLAMA_MODEL = instellingen().ollama_model

# api_type in llm_config (migratie v20, ADR 0001):
#   'ollama' = Ollama-eigen API (/api/generate), het oorspronkelijke gedrag
#   'openai' = OpenAI Chat Completions (/v1/chat/completions): Ollama /v1, vLLM, LiteLLM, ...
API_TYPES = ("ollama", "openai")
DEFAULT_API_TYPE = "ollama"
LLM_TIMEOUT = 600

_THINK_BLOK = re.compile(r"<think>.*?</think>", flags=re.DOTALL)


def denken_aan() -> bool:
    """LLM_THINK (.env): denk-modus van redeneermodellen (Qwen3, DeepSeek-R1) aan of uit.

    Standaard uit: de teksten zijn kort (chat ≤ 80 woorden) en hebben geen redeneerstap
    nodig, terwijl denken duizenden tokens en minuten kost (ADR 0001).
    """
    return instellingen().llm_think


def reasoning_effort() -> Optional[str]:
    """Waarde voor reasoning_effort in het OpenAI-pad, of None om het veld weg te laten.

    Standaard 'none' (Ollama /v1 zet dan denken uit). LLM_REASONING_EFFORT= (leeg) laat het
    veld weg, voor servers die het niet kennen; met LLM_THINK=true wordt het nooit meegestuurd.
    """
    if denken_aan():
        return None
    return instellingen().llm_reasoning_effort or None


def veilige_host(api_url: str) -> str:
    """scheme://host[:poort] zonder pad of inloggegevens, voor meldingen aan de gebruiker."""
    parts = urlsplit(api_url or "")
    if not parts.netloc:
        return api_url
    return f"{parts.scheme}://{parts.netloc.rpartition('@')[2]}"


def openai_base_url(api_url: str) -> str:
    """Basis-URL voor de OpenAI-API: voegt /v1 toe, tenzij die er al op staat."""
    base = (api_url or "").rstrip("/")
    return base if base.endswith("/v1") else f"{base}/v1"


def openai_headers() -> Dict[str, str]:
    """Authorization-header uit LLM_API_KEY (alleen .env, nooit de database)."""
    key = instellingen().llm_api_key
    return {"Authorization": f"Bearer {key}"} if key else {}


def strip_think(model_output: str) -> str:
    """Verwijdert <think>…</think>-blokken (Qwen3 denk-modus) uit modeloutput."""
    if not model_output:
        return ""
    cleaned = _THINK_BLOK.sub("", model_output)
    # Losse sluittag: denkblok zonder openingstag (sommige chat-templates)
    if "</think>" in cleaned:
        cleaned = cleaned.rsplit("</think>", 1)[1]
    return cleaned.replace("<think>", "").strip()


def clean_model_output(model_output: str) -> str:
    """Code-fences weghalen en een {"summary": ...}-antwoord uitpakken."""
    cleaned = model_output.strip()
    cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
    cleaned = re.sub(r'```$', '', cleaned)

    if cleaned.startswith('{') and '"summary":' in cleaned:
        try:
            parsed = json.loads(cleaned)
            if "summary" in parsed:
                cleaned = str(parsed["summary"])
        except Exception:
            pass
    return cleaned.strip()


def _bron_ids(items) -> list:
    """Indicator-id's uit een lijst indicatoren (voor het AI-logboek)."""
    ids = []
    for i in items or []:
        if isinstance(i, dict):
            w = i.get("uuid") or i.get("indicator_uuid") or i.get("id")
            if w:
                ids.append(str(w))
    return ids


class LLMService:
    """Service class voor LLM-interactie (Ollama of OpenAI-compatibel) en Prompt Management."""

    def __init__(self, db: Session):
        self.db = db

    def get_llm_config(self) -> Dict[str, str]:
        """Haalt de actieve LLM configuratie op (API URL, model en API-type)."""
        # SELECT *: werkt ook op een database zonder migratie v20 (dan geldt 'ollama')
        query = text("SELECT * FROM llm_config ORDER BY id DESC LIMIT 1")
        result = self.db.execute(query).mappings().fetchone()

        if result:
            api_type = result.get("api_type") or DEFAULT_API_TYPE
            return {"api_url": result["api_url"], "model_name": result["model_name"], "api_type": api_type}
        return {"api_url": DEFAULT_OLLAMA_HOST, "model_name": DEFAULT_OLLAMA_MODEL, "api_type": DEFAULT_API_TYPE}

    def get_system_prompt(self, prompt_name: str, fallback_prompt: str) -> str:
        """Haalt een prompt op uit de database, of returnt fallback_prompt."""
        query = text("SELECT prompt_text FROM system_prompts WHERE naam = :naam AND is_actief = true")
        result = self.db.execute(query, {"naam": prompt_name}).fetchone()
        
        if result and result[0]:
            return result[0]
        return fallback_prompt

    def _call_llm(self, system_prompt: str, user_prompt: str, context_name: str, *, usecase: str,
                  taak: Optional[str] = None, bronnen: Optional[list] = None) -> Dict[str, Any]:
        """Roept de geconfigureerde LLM aan via het juiste API-type (zie ADR 0001).

        Elke aanroep van het taalmodel gaat hierdoor: `usecase` (A, B, C of ai_vrijgave.BUITEN) is
        verplicht. Is die usecase niet vrijgegeven (#307), dan geen aanroep maar een weigering
        (error=True, geweigerd=True). Elke aanroep en weigering komt in het AI-logboek (#313):
        taak (standaard de prompt, afgekapt), bronnen (indicator-id's), model en resultaat.
        """
        taak = user_prompt if taak is None else taak
        if not ai_vrijgave.poort(usecase, context_name, taak=taak):
            return {"text": ai_vrijgave.melding(usecase), "error": True, "geweigerd": True,
                    "debug": {"context": context_name, "usecase": usecase, "geweigerd": True}}
        llm_config = self.get_llm_config()
        if llm_config.get("api_type") == "openai":
            res = self._call_openai(llm_config, system_prompt, user_prompt, context_name)
        else:
            res = self._call_ollama(system_prompt, user_prompt, context_name, llm_config=llm_config)
        fout = bool(res.get("error"))
        ai_logboek.schrijf(usecase, context_name, ai_logboek.FOUT if fout else ai_logboek.UITGEVOERD,
                           taak=taak, bronnen=bronnen, model=llm_config.get("model_name"),
                           modelversie=res.get("modelversie"),
                           resultaat=None if fout else res.get("text"),
                           foutmelding=res.get("text") if fout else None)
        return res

    def _call_ollama(self, system_prompt: str, user_prompt: str, context_name: str,
                     llm_config: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Gedeelde helperfunctie voor Ollama API calls met logging en fallback parser."""
        llm_config = llm_config or self.get_llm_config()
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
        if not denken_aan():
            # Denk-modus uit (Ollama ≥ 0.9; oudere versies en niet-denkende modellen negeren
            # dit). Met LLM_THINK=true geen veld: dan beslist het model, zoals voorheen.
            payload["think"] = False

        debug_info = {
            "context": context_name,
            "model": llm_config['model_name'],
            "system_prompt": system_prompt,
            "user_prompt": user_prompt
        }
        
        # Logging: volledige prompts alleen op DEBUG (GDPR: user input niet op INFO)
        AppLogger.debug(f"[{context_name}] LLM REQUEST — system: {system_prompt[:200]}... | user: {user_prompt[:200]}...", category="LLM_CHAT")
        
        try:
            response = requests.post(url, json=payload, timeout=LLM_TIMEOUT)
            response.raise_for_status()
            result_json = response.json()

            model_output = result_json.get("response", "Generatie mislukt.")
            # Sommige modellen geven ook met think=false een (leeg) <think>-blok terug
            cleaned = clean_model_output(strip_think(model_output))

            AppLogger.debug(f"[{context_name}] LLM RESPONSE — {cleaned[:500]}", category="LLM_CHAT")

            return {
                "text": cleaned,
                "debug": debug_info,
                "error": False,
                # wat de server zelf als model noemt (Ollama geeft geen digest in /api/generate)
                "modelversie": result_json.get("model"),
            }

        except requests.exceptions.RequestException as e:
            # Details (interne URL, foutmelding) alleen in de log, niet in de response (#65)
            AppLogger.error(f"[{context_name}] LLM ERROR: Error contacting Ollama op {url}: {e}", category="LLM_CHAT")
            return {
                "text": "De AI-samenvatting is nu niet beschikbaar.",
                "debug": debug_info,
                "error": True,
            }

    def _call_openai(self, llm_config: Dict[str, str], system_prompt: str, user_prompt: str,
                     context_name: str) -> Dict[str, Any]:
        """OpenAI Chat Completions (/v1/chat/completions); zelfde contract als _call_ollama."""
        url = f"{openai_base_url(llm_config['api_url'])}/chat/completions"

        # Denk-modus uit (zie denken_aan): 'think' is geen standaardveld in de OpenAI-API.
        # reasoning_effort=none zet het uit bij Ollama /v1; Qwen3 krijgt daarnaast de
        # eigen schakelaar /no_think, voor servers die reasoning_effort negeren (vLLM).
        effort = reasoning_effort()
        systeem = system_prompt
        if not denken_aan() and "qwen3" in (llm_config['model_name'] or "").lower():
            systeem = f"{system_prompt}\n\n/no_think" if system_prompt else "/no_think"

        messages = []
        if systeem:
            messages.append({"role": "system", "content": systeem})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": llm_config['model_name'],
            "messages": messages,
            "stream": False,
            "temperature": 0.3,  # zelfde waarde als de Ollama-optie
        }
        if effort:
            payload["reasoning_effort"] = effort

        debug_info = {
            "context": context_name,
            "model": llm_config['model_name'],
            "api_type": "openai",
            "system_prompt": system_prompt,
            "user_prompt": user_prompt
        }

        # Logging: volledige prompts alleen op DEBUG (GDPR: user input niet op INFO)
        AppLogger.debug(f"[{context_name}] LLM REQUEST (openai) — system: {system_prompt[:200]}... | user: {user_prompt[:200]}...", category="LLM_CHAT")

        # Meldingen naar de gebruiker zonder pad, sleutel of interne fouttekst; detail alleen in de log
        host = veilige_host(llm_config['api_url'])
        try:
            response = requests.post(url, json=payload, headers=openai_headers(), timeout=LLM_TIMEOUT)
            response.raise_for_status()
            antwoord = response.json()
            model_output = antwoord["choices"][0]["message"].get("content") or ""
            modelversie = antwoord.get("system_fingerprint") or antwoord.get("model")
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            if status in (401, 403):
                melding = f"LLM-server op {host} weigert toegang ({status}); controleer LLM_API_KEY"
            else:
                melding = f"LLM-server op {host} gaf een fout ({status})"
            AppLogger.error(f"[{context_name}] LLM ERROR: {melding}: {e}", category="LLM_CHAT")
            return {"text": melding, "debug": debug_info, "error": True}
        except (ValueError, KeyError, IndexError, TypeError, AttributeError) as e:
            # Vóór RequestException: requests' JSONDecodeError is ook een RequestException
            melding = f"Onverwacht antwoord van LLM-server op {host}"
            AppLogger.error(f"[{context_name}] LLM ERROR: {melding}: {e}", category="LLM_CHAT")
            return {"text": melding, "debug": debug_info, "error": True}
        except requests.exceptions.RequestException as e:
            melding = f"LLM-server niet bereikbaar op {host}"
            AppLogger.error(f"[{context_name}] LLM ERROR: {melding}: {e}", category="LLM_CHAT")
            return {"text": melding, "debug": debug_info, "error": True}

        cleaned = clean_model_output(strip_think(model_output))
        AppLogger.debug(f"[{context_name}] LLM RESPONSE — {cleaned[:500]}", category="LLM_CHAT")
        return {"text": cleaned, "debug": debug_info, "error": False, "modelversie": modelversie}

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
        
        return self._call_llm(system_prompt, user_prompt, context_name=f"Domain: {domain_name}", usecase=ai_vrijgave.B,
                              taak=f"Domeinsamenvatting '{domain_name}'", bronnen=_bron_ids(domain_data))

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
        
        return self._call_llm(system_prompt, user_prompt, context_name="Overall Summary", usecase=ai_vrijgave.B,
                              taak=f"Totaalsamenvatting gebied {metadata.get('gebied', 'onbekend')}")

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

        return self._call_llm(system_prompt, user_prompt, context_name="Benchmark Vergelijking", usecase=ai_vrijgave.B,
                              taak=f"Benchmark '{benchmark_data['gebied_a']['naam']}' met '{benchmark_data['referentie_label']}'",
                              bronnen=_bron_ids(top_delta))

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

        return self._call_llm(system_prompt, user_prompt, context_name="Chat Narrative", usecase=ai_vrijgave.A,
                              taak=vraag, bronnen=_bron_ids(indicatoren[:5]))
    def validate_duplicates(self, indicators: list) -> Dict[str, Any]:
        """
        Valideert een groep potentiële duplicaten.
        Retourneert een dict met 'is_duplicaat' (bool) en 'ai_advies' (str).
        """
        default_prompt = """Je bent een data-steward voor een Nederlandse gemeente. Je krijgt een lijst van indicatoren die mogelijk duplicaten van elkaar zijn.
Je taak is puur om te valideren of dit inderdaad duplicaten (of sterke overlap) zijn.

Je antwoord moet uitsluitend in valide JSON formaat zijn:
{
  "is_duplicaat": true,
  "ai_advies": "Korte, verhelderende tekst over waarom dit duplicaten zijn en eventueel de nuanceverschillen."
}

Strikte Kaders:
- Retourneer uitsluitend de JSON structuur, zonder markdown of extra tekst eromheen.
- is_duplicaat is true als de indicatoren conceptueel hetzelfde meten of sterke overlap hebben, anders false.
- Het ai_advies is kort en in het Nederlands."""

        system_prompt = self.get_system_prompt("validate_duplicates", default_prompt)
        
        # Bereid de context voor
        ind_context = []
        for ind in indicators:
            ind_context.append({
                "naam": ind.get("naam"),
                "bron": ind.get("bron"),
                "omschrijving": ind.get("omschrijving")
            })
            
        user_prompt = f"Beoordeel of de volgende indicatoren duplicaten zijn:\n\n{json.dumps(ind_context, ensure_ascii=False)}\n\nGeef je antwoord uitsluitend in JSON."
        
        # Valt niet onder AI-usecase A, B of C: de poort weigert dit altijd (#307)
        response = self._call_llm(system_prompt, user_prompt, context_name="Validate Duplicates",
                                  usecase=ai_vrijgave.BUITEN, taak="Duplicaten beoordelen",
                                  bronnen=_bron_ids(indicators))
        if response.get("geweigerd"):
            return {"is_duplicaat": False, "ai_advies": response["text"]}
        
        if response and "text" in response:
            try:
                parsed = json.loads(response["text"])
                return {
                    "is_duplicaat": parsed.get("is_duplicaat", False),
                    "ai_advies": parsed.get("ai_advies", "Geen advies.")
                }
            except json.JSONDecodeError:
                AppLogger.warning(f"JSON parseer-fout in validate_duplicates: {response['text'][:100]}...", category="LLM_CHAT")
        
        return {
            "is_duplicaat": False,
            "ai_advies": "Fout bij validatie door AI."
        }


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
            
        # Gemeenten voor SELECTEER_GEMEENTE: uit de database, alleen gemeenten met
        # geladen gebieden (#140). routers/chat.py valideert de keuze van het model.
        try:
            gemeenten_info = [{"code": c, "naam": n} for c, n in laad_gemeenten(self.db, alleen_met_gebieden=True).items()]
        except Exception as e:
            self.db.rollback()
            AppLogger.warning(f"Gemeentelijst niet geladen: {e}", category="LLM_CHAT")
            gemeenten_info = []
            
        user_prompt = f"""Vraag: "{vraag}"
        Context: {json.dumps(context or {}, ensure_ascii=False)}
        Indicatoren: {json.dumps(ind_context, ensure_ascii=False)}
        Gemeenten: {json.dumps(gemeenten_info, ensure_ascii=False)}
        (SELECTEER_GEMEENTE alleen met een code en naam uit deze lijst. Een woonplaats of buurt is geen gemeente.)
        
        Retourneer UITSLUITEND de JSON:"""
        
        # Gebruik de gedeelde helper voor robuuste JSON cleaning
        response = self._call_llm(system_prompt, user_prompt, context_name="Intent Dispatcher", usecase=ai_vrijgave.A,
                                  taak=vraag, bronnen=_bron_ids(indicatoren[:10]))
        if response.get("error"):
            return None
        
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

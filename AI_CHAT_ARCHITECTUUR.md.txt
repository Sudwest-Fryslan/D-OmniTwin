# D-OmniTwin — AI Chat & Zoek Interface: Architectuur Deep-Dive

**Document versie:** 1.0  
**Datum:** 20 maart 2026  
**Sprint:** 10 — D-Omni Assistent  
**Applicatie versie:** 2.1.0  
**Doelgroep:** Software developers, solution architects

---

## 1. Inleiding & Filosofie

D-OmniTwin is een interactieve gebiedsmonitor die werkt met 217 ruimtelijke indicatoren (groen, gezondheid, veiligheid, wonen, etc.) voor 1.721 Nederlandse buurten en wijken. De kaart, datapanel en het D-Omni Kompas zijn primair muis-gedreven interfaces.

De **D-Omni Assistent** is ontworpen als **"alternatieve muis"**: een gebruiker stelt een vraag in gewone Nederlandse taal en de assistent stuurt zelfstandig de kaart, het Kompas en de rapport-module aan. Het vervangt niet de bestaande UI — het vergroot de toegankelijkheid voor gebruikers die niet weten welke indicatoren relevant zijn voor hun vraag.

> **Kernprincipe:** De AI bepaalt welke data zichtbaar wordt, de gebruiker beslist of hij de actie bevestigt. Alle interacties via de chat zijn omkeerbaar en niet-destructief.

---

## 2. Systeem-overzicht

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          BROWSER (Vanilla JS)                                │
│                                                                              │
│  ┌─────────────────────┐     EventBus (pub/sub)     ┌──────────────────────┐ │
│  │   ChatPanel          │ ──INDICATOR_SELECTED──►   │    app.js            │ │
│  │   (chat.js)          │                            │  handleIndicator     │ │
│  │                      │ ──INDICATOR_SELECTED──►   │  Selection()         │ │
│  │  POST /api/chat  ◄──►│         │                  └────────┬─────────────┘ │
│  │                      │         │                           │ laadKaartData │
│  └─────────────────────┘         │                           ▼               │
│                                  │                  ┌──────────────────────┐ │
│                                  └──INDICATOR_SELECTED──►  KompasViz       │ │
│                                       (_isSyncing guard)   (kompas.js)     │ │
│                                                            navigateTo       │ │
│                                                            Indicator(uuid)  │ │
│                                                     └──────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
                                        │
                                 POST /api/chat
                                        │
┌──────────────────────────────────────▼────────────────────────────────────┐
│                          BACKEND (FastAPI / Python)                        │
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐   │
│  │  routers/chat.py  —  POST /api/chat                                │   │
│  │                                                                    │   │
│  │  1. AISearchService.search_indicators(vraag, limit=8)              │   │
│  │       └─► sentence-transformers → pgvector (cosine similarity)    │   │
│  │                                                                    │   │
│  │  2. classify_intent(vraag)  [rule-based regex]                     │   │
│  │       └─► TOON_OP_KAART | SELECTEER_BUURTEN | MAAK_RAPPORT |      │   │
│  │           ANALYSEER_GEBIED | VERBIND_THEMAS | ZOEK_INDICATOREN     │   │
│  │                                                                    │   │
│  │  3. LLMService.generate_chat_narrative(vraag, indicatoren, intent) │   │
│  │       └─► Ollama API → qwen3:30b (lokaal) → max 80 woorden NL     │   │
│  │                                                                    │   │
│  │  4. generate_acties(intent, indicatoren, vraag)                    │   │
│  │       └─► TOON_OP_KAART + SELECTEER_BUURTEN + MAAK_RAPPORT knoppen│   │
│  │                                                                    │   │
│  │  5. ChatResponse → { intent, narrative, acties[], indicatoren[] }  │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌───────────────────────────────────────────────────────────────────────────┐
│                          DATABASE (PostgreSQL + PostGIS + pgvector)       │
│                                                                           │
│  indicatoren          indicator_embeddings     llm_config                 │
│  ├ uuid               ├ indicator_uuid         ├ api_url                  │
│  ├ naam               ├ embedding (vector)     └ model_name               │
│  ├ omschrijving       └ created_at                                        │
│  ├ beschrijving_ai                             system_prompts             │
│  ├ ontologische_beschrijving                   ├ naam (= "chat_narrative") │
│  ├ categorie                                   ├ prompt_text              │
│  ├ eenheid                                     └ is_actief                │
│  ├ score_type                                                             │
│  └ ontologie_status                                                       │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Backend Components

### 3.1 `routers/chat.py` — De Orkestrator

Het enige publieke endpoint voor de chat interface:

```
POST /api/chat
Content-Type: application/json

{
  "vraag": "Welke buurten hebben weinig openbaar groen?",
  "context": {
    "huidig_gebied_id": "BU01000001",   // optioneel
    "huidige_indicator_uuid": "..."      // optioneel
  }
}
```

De `context` velden zijn optioneel en worden alleen als tekst doorgegeven aan de LLM prompt — ze veranderen niet de search-logica. Dit is een bewuste designkeuze: de semantische zoekvraag staat los van de huidige kaartstand.

**Verwerkingsstroom (5 stappen):**

| Stap | Component | Functie | Latentie (typisch) |
|------|-----------|---------|-------------------|
| 1 | `AISearchService` | Vectoriseer vraag + zoek indicatoren | 80–200 ms |
| 2 | `classify_intent()` | Regex-patronen → intent string | < 1 ms |
| 3 | `LLMService` | Ollama API call → NL toelichting | 2–15 sec |
| 4 | `generate_acties()` | Construct actie-knoppen | < 1 ms |
| 5 | `ChatResponse` | Serialiseer via Pydantic | < 1 ms |

> **Let op:** Stap 3 (LLM) bepaalt de totale latentie. Bij een koud Ollama-model (first token) kan dit oplopen tot 20+ sec. Er is een fallback narrative ingebouwd als Ollama niet bereikbaar is.

---

### 3.2 `services/ai_search_service.py` — Semantisch Zoeken

De zoekservice gebruikt **sentence-transformers** lokaal in het FastAPI-proces:

```python
# Singleton model — één keer laden per server-start
_model = SentenceTransformer('all-MiniLM-L6-v2')

# Per zoekaanvraag:
query_vector = _model.encode(query_text).tolist()  # 384-dimensionale vector
```

De database query gebruikt pgvector's `<=>` operator (cosine distance):

```sql
SELECT
    i.uuid, i.naam,
    COALESCE(
        NULLIF(i.ontologische_beschrijving, ''),  -- 1e voorkeur: menselijk gevalideerd
        NULLIF(i.beschrijving_ai, ''),             -- 2e voorkeur: AI gegenereerd
        i.omschrijving                             -- fallback: technische omschrijving
    ) as beschrijving,
    (e.embedding <=> CAST(:vector AS vector)) as distance
FROM indicatoren i
JOIN indicator_embeddings e ON i.uuid = e.indicator_uuid
ORDER BY distance ASC
LIMIT :limit
```

**Score-berekening:** `score = 1 - distance` (cosine similarity, range 0–1)  
Scores > 0.25 worden als relevant beschouwd. Lagere scores gaan mee als fallback maar krijgen geen actie-knop voor "Selecteer" acties.

**Model-eigenschappen:**

| Eigenschap | Waarde |
|-----------|--------|
| Model | `all-MiniLM-L6-v2` (Sentence Transformers) |
| Vectordimensie | 384 |
| Taalondersteuning | Meertalig (NL werkt goed) |
| Laadtijd (koud) | ~3–5 sec (eenmalig bij server-start) |
| Inferentietijd | ~50–150 ms per query |
| Bestandsgrootte | ~28 MB |

---

### 3.3 `services/llm_service.py` — Narrative Generator

De LLM-service communiceert met een **lokale Ollama instantie** via HTTP:

```
POST http://localhost:11434/api/generate
{
  "model": "qwen3:30b",     // configureerbaar via llm_config tabel
  "system": "<system_prompt>",
  "prompt": "<user_prompt>",
  "stream": false,
  "options": { "temperature": 0.3 }
}
```

**Configuratie-hiërarchie** (meest specifiek wint):
1. `llm_config` tabel in PostgreSQL (via admin panel instelbaar)
2. Environment variabelen: `OLLAMA_HOST`, `OLLAMA_MODEL`
3. Hardcoded fallback: `http://localhost:11434`, `qwen3:30b`

**System prompt voor chat narrative** (`system_prompts` tabel, naam = `chat_narrative`):
- Max 80 woorden output
- Uitsluitend Nederlands
- Platte tekst (geen Markdown, geen lijstjes)
- Nooit technische termen zoals "cosine similarity" of "embedding"
- Direkt beginnen, geen begroeting

De prompt wordt per chat-request opgebouwd met:
- De gebruikersvraag
- De gedetecteerde intent
- Optionele kaartcontext (huidig_gebied_id)
- Top-5 gevonden indicatoren met naam, categorie en beschrijving (max 150 tekens)

---

### 3.4 Intent Classifier — `classify_intent()`

De classifier is **rule-based** (geen ML) en wordt bewust eenvoudig gehouden. Hij telt regex-matches per intent-categorie en kiest de winnaar:

```python
INTENT_PATTERNS = {
    "TOON_OP_KAART":      [r"toon\b", r"kaart", r"visualiseer", ...],
    "SELECTEER_BUURTEN":  [r"selecteer", r"laagste", r"welke\s+buurten", ...],
    "MAAK_RAPPORT":       [r"rapport", r"samenvatting", r"exporteer", ...],
    "ANALYSEER_GEBIED":   [r"hoe\s+scoort", r"vergelijk", r"benchmark", ...],
    "VERBIND_THEMAS":     [r"verbind", r"samenhang", r"correlatie", ...],
}
```

Geen match → fallback `ZOEK_INDICATOREN`

De intent stuurt welke **actie-knoppen** worden gegenereerd, niet de zoekopdracht zelf. De semantische zoektocht loopt altijd volledig door, ongeacht de intent.

---

### 3.5 API Response Contract — `ChatResponse`

```json
{
  "intent": "SELECTEER_BUURTEN",
  "narrative": "Ik heb de indicator 'Afstand tot openbaar groen' gevonden, die...",
  "acties": [
    {
      "type": "TOON_OP_KAART",
      "label": "🗺 Toon: Afstand tot openbaar groen",
      "indicator_uuid": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    },
    {
      "type": "SELECTEER_BUURTEN",
      "label": "📋 Laagste 25%: Afstand tot openbaar groen",
      "indicator_uuid": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "filters": { "percentiel": "P0-P25" }
    }
  ],
  "indicatoren": [
    {
      "uuid": "3fa85f64-...",
      "naam": "Afstand tot openbaar groen",
      "beschrijving": "Gemiddelde wegafstand...",
      "categorie": "Kwaliteit fysieke leefomgeving",
      "eenheid": "km",
      "score_type": "-/+",
      "relevantie": 0.87
    }
  ],
  "debug": {
    "intent": "SELECTEER_BUURTEN",
    "zoekresultaten": 8,
    "llm_model": "qwen3:30b"
  }
}
```

**Actie-types:**

| Type | Trigger | Frontend Actie |
|------|---------|----------------|
| `TOON_OP_KAART` | Altijd voor top-indicator | `EventBus.emit('INDICATOR_SELECTED')` |
| `SELECTEER_BUURTEN` | Intent = SELECTEER/ZOEK/VERBIND | `EventBus.emit('INDICATOR_SELECTED')` + filter hint |
| `MAAK_RAPPORT` | Intent = MAAK_RAPPORT / VERBIND_THEMAS met ≥2 indicatoren | Open `/admin/rapport/{id}` of `/admin/rapport/benchmark` |

---

## 4. Frontend Components

### 4.1 `static/js/core/event-bus.js` — De Ruggegraat

De `EventBus` is een **globale pub/sub singleton** (`window.EventBus`) die alle frontend-componenten ontkoppelt. Geen enkel component roept direct methoden aan op een ander component.

```javascript
class EventBus {
    on(eventName, callback) { ... }   // subscribe
    off(eventName, callback) { ... }  // unsubscribe
    emit(eventName, data) { ... }     // publish → alle subscribers
}
window.EventBus = new EventBus();
```

**Geregistreerde event-listeners per component:**

| Component | Luistert naar | Zendt uit |
|-----------|--------------|-----------|
| `app.js` | `INDICATOR_SELECTED` | `INDICATOR_SELECTED` (bij kaart-klik) |
| `chat.js` | _(geen)_ | `INDICATOR_SELECTED` (bij actie-klik) |
| `kompas.js` | `INDICATOR_SELECTED` | `INDICATOR_SELECTED` (na navigatie) |

> **Kritisch:** Omdat zowel `app.js` als `kompas.js` luisteren naar en uitzenden van `INDICATOR_SELECTED`, is er een anti-loop mechanisme essentieel (zie §4.4).

---

### 4.2 `static/js/chat.js` — De ChatPanel Klasse

De ChatPanel is een **vanilla JS klasse** die het volledige chat-zijpaneel beheert. Er is bewust gekozen voor geen framework (geen React/Vue) om de bestaande applicatie niet te verstoren.

**State:**
```javascript
class ChatPanel {
    isOpen: boolean       // paneel open/dicht
    isLoading: boolean    // wacht op API response
    panelEl, messagesEl, inputEl, sendBtn, toggleBtn, closeBtn
}
```

**Lifecycle van een gebruikersvraag:**

```
User typt → Enter / Send-knop
    │
    ▼
sendVraag(tekst)
    ├── addUserMessage(tekst)       → blauw bubble rechts
    ├── addLoadingIndicator()       → 3 pulserende dots
    │
    ├── fetch('POST /api/chat', { vraag, context })
    │       │
    │       ├── [success] addAssistantMessage(response)
    │       │       ├── narrative tekst
    │       │       ├── actie-knoppen → _handleActie()
    │       │       └── indicator-lijst → _handleIndicatorClick()
    │       │
    │       └── [error] addErrorMessage(error.message)
    │
    └── isLoading = false
```

**Kaartcontext ophalen (`_getKaartContext`):**

De chat stelt de huidige kaartsituatie beschikbaar aan de LLM via:
```javascript
_getKaartContext() {
    return {
        huidig_gebied_id:         window.state?.selectedGebiedId,
        huidige_indicator_uuid:   window.state?.currentIndicator
    };
}
```

Deze context beïnvloedt alleen de LLM-toelichting (de assistent weet welk gebied de gebruiker bekijkt), niet de semantische zoekresultaten.

---

### 4.3 Actie-Handlers — Van Chat naar Kaart

**`_handleActie(btn)`:**

```javascript
switch (type) {
    case 'TOON_OP_KAART':
        EventBus.emit('INDICATOR_SELECTED', { uuid, name });
        // → app.js laadt de indicator op de kaart
        // → kompas.js navigeert naar de indicator (als venster open)
        break;

    case 'SELECTEER_BUURTEN':
        EventBus.emit('INDICATOR_SELECTED', { uuid, name });
        // filters (percentiel) zijn momenteel informationeel in de label
        // toekomstig: kaartfilter toepassen
        break;

    case 'MAAK_RAPPORT':
        const ids = window.state?.selectedGebiedIds || [];
        if (ids.length === 0)    → open('/admin/rapport/benchmark')
        if (ids.length === 1)    → open(`/admin/rapport/${ids[0]}`)
        if (ids.length >= 2)     → open(`/admin/rapport/benchmark?gebied_a=${a}&gebieden_b=${rest}`)
        break;
}
```

**`_handleIndicatorClick(item)`:**

Klikken op een indicator in de scrollbare lijst doet hetzelfde als een `TOON_OP_KAART` actie-knop: emit `INDICATOR_SELECTED`. Het enige verschil is dat het selecte item visueel wordt gemarkeerd (`.active` CSS class).

---

### 4.4 `static/js/kompas.js` — Chat↔Kompas Sync & Anti-Loop Guard

Het Kompas heeft een `navigateToIndicator(uuid)` methode die al bestond voor de AI-zoekfunctie in het Kompas zelf. Deze methode:

1. Zoekt de indicator in de D3-boom via `_findNodeByUuid(root, uuid)`
2. Zoomt naar de **parent node** (thema-kwadrant) via `_zoomFn()`
3. Wacht 800ms op de zoom-animatie
4. Opent het detail-paneel (`expandDetails()`)
5. Synchroniseert naar de kaart via `syncIndicatorToMap()`

**Het loop-probleem:**

`syncIndicatorToMap()` emit zelf ook `INDICATOR_SELECTED`. Zonder guard ontstaat een
oneindige keten:

```
Chat emit → kompas navigeert → syncIndicatorToMap → emit → kompas navigeert → ...
```

**De fix — `_isSyncing` guard:**

```javascript
kompasViz._isSyncing = false;

EventBus.on('INDICATOR_SELECTED', (data) => {
    if (!kompasViz.root) return;          // Kompas niet geladen
    if (kompasViz._isSyncing) return;     // LOOP GUARD ← hier stopt de keten
    
    const kompasWindow = document.getElementById('kompas-window');
    if (kompasWindow.style.display === 'none') return;  // Venster niet open

    kompasViz._isSyncing = true;
    kompasViz.navigateToIndicator(data.uuid);
    setTimeout(() => { kompasViz._isSyncing = false; }, 1200);  // Reset na animatie
});
```

De 1200ms timeout is bewust ruimer dan de 800ms zoom-animatie om race conditions te vermijden.

---

### 4.5 `app.js` — `handleIndicatorSelection()`

De centrale handler in de hoofd-applicatie reageert op elk `INDICATOR_SELECTED` event:

1. Synchroniseert de UI-dropdown (kaart configuratie paneel)
2. Roept `loadKaartData(indicatorUuid, gebiedstype)` aan
3. Update de legenda (kleurschaal, min/max, coverage)
4. Laadt data voor het detail-paneel (als een gebied is geselecteerd)

Deze functie is niet gewijzigd voor de chat integratie — de EventBus zorgt voor transparante koppeling.

---

## 5. Database Schema (relevant voor AI)

### `indicator_embeddings` — Vector Store

```sql
CREATE TABLE indicator_embeddings (
    indicator_uuid UUID REFERENCES indicatoren(uuid),
    embedding      vector(384),    -- pgvector extensie
    created_at     TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ON indicator_embeddings 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

De embeddings zijn voorberekend via een offline ETL-script dat alle indicatoren doorheen `all-MiniLM-L6-v2` jaagt. Dit hoeft maar één keer te gebeuren (tenzij nieuwe indicatoren worden toegevoegd).

### `llm_config` — LLM Configuratie

```sql
CREATE TABLE llm_config (
    id         SERIAL PRIMARY KEY,
    api_url    TEXT DEFAULT 'http://localhost:11434',
    model_name TEXT DEFAULT 'qwen3:30b',
    created_at TIMESTAMP DEFAULT NOW()
);
```

Wordt beheerd via het Admin Panel (LLM Config pagina). De laatste record (hoogste id) wint.

### `system_prompts` — Prompt Management

```sql
CREATE TABLE system_prompts (
    id         SERIAL PRIMARY KEY,
    naam       TEXT UNIQUE,    -- bijv. 'chat_narrative'
    prompt_text TEXT,
    is_actief  BOOLEAN DEFAULT true
);
```

De prompt `chat_narrative` stuurt de LLM-output voor de chat. Te bewerken via het Admin Panel zonder code-deployment.

### Beschrijvingsprioriteit in `indicatoren`

```sql
-- Zoekvolgorde (COALESCE):
i.ontologische_beschrijving   -- 1e: menselijk gevalideerd en geredigeerd
i.beschrijving_ai             -- 2e: gegenereerd door Qwen3:30b (via "Hek en Bron" filosofie)
i.omschrijving                -- 3e: originele technische CBS/RIVM omschrijving
```

---

## 6. Deployment & Afhankelijkheden

### Externe Diensten

| Dienst | Type | Vereist? | Configuratie |
|--------|------|----------|-------------|
| **Ollama** | Lokale LLM server | Ja (voor narrative) | Draaien op `localhost:11434` |
| **qwen3:30b** (of kleiner) | LLM model | Ja | `ollama pull qwen3:30b` |
| **pgvector** | PostgreSQL extensie | Ja (voor zoeken) | `CREATE EXTENSION vector;` |

### Python Dependencies (relevant)

```
sentence-transformers>=2.2  # Embeddings genereren
requests                    # Ollama API calls
sqlalchemy                  # Database ORM
fastapi                     # HTTP server
pydantic>=2                 # Request/response validatie
```

### Startup gedrag

Bij de eerste `/api/chat` aanvraag na een server-herstart:
1. `SentenceTransformer('all-MiniLM-L6-v2')` wordt geladen (~3–5 sec, eenmalig)
2. Model wordt als globale singleton gehouden — volgende aanvragen zijn snel

Het is aan te raden om het model te **pre-warmen** bij server-start (op te nemen in `main.py` lifespan handler).

---

## 7. Sequentiediagram — Complete Gebruikersflow

```
Gebruiker      ChatPanel        /api/chat        AISearch        Ollama         EventBus        Kaart        Kompas
    │               │               │               │               │               │               │            │
    │ typ + Enter   │               │               │               │               │               │            │
    ├──────────────►│               │               │               │               │               │            │
    │               │ addUserMsg    │               │               │               │               │            │
    │               │ addLoading    │               │               │               │               │            │
    │               │               │               │               │               │               │            │
    │               ├─POST /api/chat────────────────►               │               │               │            │
    │               │               │ search(vraag) │               │               │               │            │
    │               │               ├──────────────►│               │               │               │            │
    │               │               │   encode query│               │               │               │            │
    │               │               │   pgvector    │               │               │               │            │
    │               │               │◄── results────┤               │               │               │            │
    │               │               │               │               │               │               │            │
    │               │               │ classify_intent               │               │               │            │
    │               │               │               │               │               │               │            │
    │               │               │ generate_narrative            │               │               │            │
    │               │               ├───────────────────────────────►               │               │            │
    │               │               │               │    Ollama /api/generate      │               │            │
    │               │               │               │    (2–15 sec)               │               │            │
    │               │               │◄───────────────────────────────┤               │               │            │
    │               │               │               │               │               │               │            │
    │               │               │ generate_acties               │               │               │            │
    │               │               │               │               │               │               │            │
    │               │◄─ChatResponse─┤               │               │               │               │            │
    │               │               │               │               │               │               │            │
    │               │ render UI     │               │               │               │               │            │
    │◄──────────────┤  (narrative + knoppen + lijst)│               │               │               │            │
    │               │               │               │               │               │               │            │
    │ Klik knop     │               │               │               │               │               │            │
    ├──────────────►│               │               │               │               │               │            │
    │               │ _handleActie  │               │               │               │               │            │
    │               ├────────────────────────────────────────────────►emit(INDICATOR_SELECTED)       │            │
    │               │               │               │               │               │               │            │
    │               │               │               │               │               ├──────────────►│            │
    │               │               │               │               │               │ loadKaartData │            │
    │               │               │               │               │               │               │            │
    │               │               │               │               │               ├───────────────────────────►│
    │               │               │               │               │               │               │navigateTo  │
    │               │               │               │               │               │               │Indicator() │
    │               │               │               │               │               │               │(+800ms)    │
```

---

## 8. Bekende Beperkingen & Toekomstige Stappen

### Huidige beperkingen

| Beperking | Impact | Toekomstige aanpak |
|-----------|--------|-------------------|
| **Request/Response** (geen streaming) | Gebruiker wacht 2–15 sec tot spinner verdwijnt | SSE streaming via `EventSource` |
| **Rule-based intent classifier** | Complexe vragen met meerdere intents missen nuance | LLM-aided intent classificatie (twee-staps) |
| **SELECTEER_BUURTEN** niet uitgevoerd | Actie-knop geeft alleen visuele feedback, filtert kaart niet | Kaartfilter API koppelen aan `filters.percentiel` |
| **Geen conversatie-geheugen** | Elke vraag staat los — geen follow-up vragen mogelijk | Session-based chat history (backend of localStorage) |
| **Model koud / warm** | Eerste aanvraag na herstart is traag | Pre-warm model bij server-startup |
| **Embeddings niet auto-bijgewerkt** | Nieuwe indicatoren missen in zoekresultaten tot re-embed | Trigger bij indicator-CRUD in admin panel |

### Mogelijke uitbreidingen

1. **Multi-intent responses** — één vraag triggert zowel een kaartupdate als een rapport
2. **Conversatieflow** — follow-up vragen als "en hoe is dat in de stad?" met context van vorige beurt
3. **Actieverificatie** — gebruiker kan acties "ongedaan maken" via een undo-knop in de chat
4. **Kaartfilter integratie** — `SELECTEER_BUURTEN` past actief de kaartweergave aan (highlight + zoom)
5. **Chat als doorzoekbare log** — exporteer de chatsessie als onderdeel van het PDF-rapport

---

## 9. File Referentie

| Bestand | Rol | Regels |
|---------|-----|--------|
| `routers/chat.py` | API endpoint, intent classifier, actie-generator | 263 |
| `services/ai_search_service.py` | pgvector zoeken, embedding generatie | 91 |
| `services/llm_service.py` | Ollama communicatie, prompt management | 231 |
| `static/js/chat.js` | Frontend chat UI (ChatPanel klasse) | 341 |
| `static/js/core/event-bus.js` | Pub/sub communicatie-laag | 49 |
| `static/js/kompas.js` | D3 sunburst + navigateToIndicator + anti-loop | 1926 |
| `static/js/app.js` | Kaart + handleIndicatorSelection | ~2200 |
| `templates/index.html` | HTML structuur chat-paneel + tab-knop | ~700 |
| `static/css/styles.css` | Chat-styling (glassmorphism, animaties) | ~2100 (+300) |

---

*Document gegenereerd op basis van broncode d.d. 20 maart 2026 — Sprint 10, versie 2.1.0*

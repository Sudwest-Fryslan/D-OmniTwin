# D-OmniTwin 🌍🔐

**The Omni Twin** - Digitale spiegel van de fysieke leefomgeving

**Status:** Sessie 2026-04-10 ✅ — Multi-Gebiedsdossier geïntegreerd + Bugfixes doorgevoerd
**Versie:** 2.2.0 (Dag 55)
**Security Status:** 🟡 MEDIUM RISK (API key auth, CORS locked, Security headers active)

---

## 🧩 Componenten Overzicht

| Component | Technologie | Port | Status |
|-----------|-------------|------|--------|
| **Main App** | FastAPI + deck.gl + D3.js | 8000 | ✅ Production Ready |
| **Admin Panel** | React + TypeScript | 3000 | ✅ MVP Ready |
| **Database** | PostgreSQL + PostGIS | 5432 | ✅ Operationeel |

### Main App Features
- 🗺️ **Interactieve Kaart** - Mapbox + deck.gl 3D visualisatie
- 🧭 **Kompas Visualisatie** - D3.js sunburst met 12 thema's, 217 indicatoren
- 📊 **Multi-Gebied Analyse** - Shift+Click selectie of via Omgevingsvisie-deelgebieden, nieuwe rapportage-modal
- 🗺️⃣ **Omgevingsvisie Selectielaag** - 6 deelgebieden SWF als klikbaar selectieframe (CBS-buurten via -10m buffer)
- 🤖 **D-Omni Assistent** - Intent-based AI chat interface (lokaal Ollama, gemma4:e4b)
- 🎨 **Classic Premium UI** - Dark theme met gradient accents

### Admin Panel Features
- 🔐 **API Key Auth** - Beveiligde toegang tot beheer
- ✏️ **Indicator Editor** - Bewerk naam, omschrijving, score type, kleurschema
- 📈 **Dashboard** - Stats en Kompas hiërarchie overzicht
- 📄 **Multi-Gebiedsdossier** - Uitgebreide D3-stijl react rapportmodule voor multi-selectie van buurten

---

## Recent Voltooid

### Dag 55 (10-04-2026): Multi-Gebiedsdossier & Optimalisaties 🗺️📊
**Focus:** Afronding rapportmodule voor Multi-gebied selecties en integratie van directe verbeteringen vanuit kwaliteitscontrole.

- ✅ **Backend Analyse** (`routers/report.py`, `services/report_service.py`): Nieuwe POST-endpoints (`/multi-gebied`, `/geojson`), generatie van dynamische payload voor thema-aggregatie, Z-scores, kleurcoderingen, en dynamisch bereik (min/max/gemiddelde).
- ✅ **Frontend Panel** (`MultiGebiedPage.tsx`): Interactieve SVG choropleth-kaart met Z-score afwijkingen, Ranked Uitschietertabel en Thema-aggregaat bars.
- ✅ **UI/UX Fixes:**
    - Introductie van een divergerend **Colorblind-safe** z-score palet.
    - Oplossen van een mouse-hover *flicker bug* via specifieke CSS/layout vastlegging.
    - Volledige integratie via modals van de interactielaag in de `app.js` (Multi-select fallback).
- ✅ **Data Opschoning:** Automatische detectie en filtering van "water-buurten" via metadata velden om ruis te voorkomen in statistische overzichten.
**Focus:** Uitbreiden van AI chat-acties naar de UI, integratie van beheertoegang in de hoofdapp en server performance optimalisaties.

- ✅ **Track A — Intelligente Chat Acties** (`chat.js`, `app.js`, `kompas.js`, `chat.py`, `llm_service.py`):
    - Nieuwe actie-types: `SELECTEER_GEMEENTE`, `SELECTEER_GEBIEDSTYPE`, `SELECTEER_KOMPAS`, `OPEN_KOMPAS`.
    - Context-uitbreiding: De assistent bevat nu de meta-data van **49 gemeenten** (Fryslân, Groningen, Drenthe).
    - EventBus integratie met manual event dispatching voor naadloze UI-synchronisatie.
    - Robuuste Pydantic modellen in de backend voor volledige data-doorgifte van LLM naar frontend.
    - Naam-gebaseerde fallback voor gebiedstype-selectie bij ontbrekende UUIDs.
- ✅ **Track D — Performance & Developer Experience** (`run_dev.py`, `llm_service.py`):
    - Lazy loading van `SentenceTransformer` AI-modellen (30% snellere server start).
    - Geoptimaliseerde Uvicorn reload (uitsluiten van `node_modules`, `admin-panel`).
    - Introductie `run_dev.py` script voor een gestroomlijnde development loop.
- ✅ **Track E — Admin Integratie** (`index.html`, `styles.css`):
    - Auth-aware **"Beheer" knop** in de hoofdapp header.
    - Dynamische routing naar `/admin/login` of `/admin/dashboard`.
    - UX Verbetering: "Terug naar Dashboard" → "Sluit rapport" (gebruik van `window.close()`).

### Dag 43 (20-03-2026): Sprint 10 — D-Omni Assistent Chat Interface 🤖💬
**Focus:** Implementatie van een intent-based AI chat zijpaneel dat de kaart, het Kompas en rapport-generatie aanstuurt via natuurlijke taal.

- ✅ **Fase 0 — AI Search Priority Fix** (`services/ai_search_service.py`):
    - COALESCE beschrijvings-voorkeur: menselijk gevalideerd → AI-gegenereerd → standaard omschrijving.
    - `ontologie_status`, `eenheid` en `score_type` beschikbaar in zoekresultaten.
- ✅ **Fase 1 — Backend Chat Endpoint** (`routers/chat.py`, `services/llm_service.py`):
    - Nieuw `POST /api/chat` endpoint met Command Dispatch JSON structuur.
    - Rule-based intent classifier: `VERKEN_INDICATORS`, `VERGELIJK_GEBIEDEN`, `MAAK_RAPPORT`, `ALGEMEEN`.
    - `generate_chat_narrative()` in `LLMService` — beknopte NL-toelichting (≤80 woorden) op basis van gevonden indicatoren.
- ✅ **Fase 2 — Frontend Chat Zijpaneel** (`static/js/chat.js`, `templates/index.html`, `static/css/styles.css`):
    - `ChatPanel` klasse: open/close/toggle, loading dots, chat-historiek (groeit omhoog).
    - cpu.svg toggle-knop (inline SVG) in de verticale tab-balk — thema-aware.
    - Glassmorphism rechts-zijpaneel (380px breed), identieke stijl als Kaart Configuratie.
    - Actie-knoppen dispatchen `INDICATOR_SELECTED` via EventBus naar kaart én Kompas.
    - `MAAK_RAPPORT`: opent gebiedsdossier of benchmark op basis van huidige kaart-selectie.
- ✅ **Chat↔Kompas Sync** (`static/js/kompas.js`):
    - Kompas luistert naar `INDICATOR_SELECTED` en navigeert automatisch naar het juiste kwadrant.
    - `_isSyncing` guard voorkomt event-loop (Bug #36 gefixt).

### Dag 42 (18-03-2026): AI Ontologie Kwaliteitsfix 🧠✨
**Focus:** Implementatie van de "Hek en Bron" filosofie voor prompt engineering en herstel van 51 indicatoren.

- ✅ **"Hek en Bron" Filosofie:** Documentatie van de identiteit-gedreven prompt-strategie (`docs/6-ai-parallel-track/ai-integratie/prompt_engineering_filosofie.md`).
- ✅ **Targeted Re-generatie:** 51 indicatoren met technische ruis (RDF/OWL) succesvol hersteld naar verhalende Nederlandse tekst met het Qwen-30b model.
- ✅ **AI Audit Tooling:** Ontwikkeling van `src/utils/ai_audit.py` voor automatische kwaliteitscontrole van AI-output.

### Dag 41 (17-03-2026): CBS 2024 Geografie & ETL Data Gaten 🗺️🔋
**Focus:** Implementatie van de 2024 buurtindeling voor Northern Provinces en het structureel dichten van datagaten voor Smallingerland en De Fryske Marren.

## 📈 Resultaat
De noordelijke provincies (Fryslân, Groningen, Drenthe) zijn nu volledig "up-to-date" met de nieuwste 2024 grenzen én een diepe historische data-stand (2020-2025). 
- **Groningen**: ~65.000 records geïmporteerd.
- **Drenthe**: ~85.000 records geïmporteerd.
- **Totaal Noord-Nederland**: 100% dekking op RIVM en CBS Kerncijfers voor actieve gebieden.
- **Stabiliteit**: De kaart-API is bug-vrij voor records zonder geometrie.

- ✅ **CBS 2024 Boundary Import:**
    - Succesvolle import van de 2024 buurtgeometrieën voor Fryslân, Groningen en Drenthe uit landelijke GPKG.
    - Resolutie van overlappende geometrieën in Smallingerland door deactivering van verouderde buurtcodes.
- ✅ **Noordelijke Provincies Data-expansie (Groningen & Drenthe):**
    - **RIVM & CBS**: Volledige import voor Groningen (10 gemeenten, ~65k records) en Drenthe (12 gemeenten, ~85k records).
    - **100% Gebiedsdekking**: Alle actieve buurten in het Noorden zijn nu voorzien van sociaal-economische en gezondheidsindicatoren.
- ✅ **ETL Data Gaten gedicht (Fryslân focus):**
### Belangrijkste resultaten:
1.  **2024 Geografie**: Import van 2024 buurten voor Groningen, Friesland en Drenthe. Oude geometrieën in Smallingerland zijn gedeactiveerd.
2.  **Noordelijke Expansie**: Groningen en Drenthe zijn nu volledig voorzien van data (~150.000 nieuwe records in totaal). Groningen stad spant de kroon met 16k+ records.
3.  **SQL Fix**: De kaart-API (`get_kaart_data_v2`) is robuuster gemaakt door records zonder geometrie over te slaan.
4.  **Data Gaten**:
    *   **PC6-to-Buurt**: Mapping geüpdatet via CBS 2025 relatie-CSV (448k codes).
    *   **ETL**: RIVM, BAG en EP-Online her-geïmporteerd voor Fryslân (Smallingerland/DFM focus).
5.  **Coverage**: Energielabel coverage berekend voor 954 Friese buurten.
    - **PC6 Mapping Update**: Een nieuwe `pc6_buurt_mapping.json` gegenereerd op basis van de CBS 2025 relatie-tabel (448.646 codes).
    - **RIVM Her-import**: Alle Gezondheidsmonitor data voor Smallingerland gematcht aan de nieuwe 2024 indeling.
    - **BAG & EP-Online**: Bouwjaar, woonoppervlakte en energielabels succesvol geïmporteerd voor de nieuwe gebieden in Smallingerland en De Fryske Marren.
- ✅ **Kaart-Service Stabiliteit:**
    - Fix voor een kritieke `NULL geometry` fout in de GeoJSON response van de kaart-API (`get_kaart_data_v2`).
- ✅ **Documentatie Update:**
    - Samenvatting Dag 41 en bijgewerkte TODO.md / BUGFIX.md.


### Dag 39 (15-03-2026): Sprint 8F — AI Search Navigation & Data Lineage 🧭🤖
**Focus:** Optimalisatie van de AI-zoekervaring, contextualiteit in het Kompas en 100% data coverage.

- ✅ **AI Search Expansion (100% Coverage):**
    - Alle **280 indicatoren** zijn nu voorzien van een AI-ontologische beschrijving d.m.v. lokale Ollama inferentie.
    - Vectorisatie van de volledige set voltooid; alle indicatoren zijn semantisch doorzoekbaar via `pgvector`.
    - Het standaard aantal zoekresultaten is verhoogd van 5 naar 10.
- ✅ **Kompas UI & Navigatie ("De kers op de taart"):**
    - **Contextuele Zoom:** Bij het selecteren van een zoekresultaat zoomt het Kompas automatisch naar het **Thema-niveau** (parent) van de indicator. Hierdoor ziet de gebruiker direct de hiërarchische context.
    - **Z-Index Reparatie:** Tooltips zijn nu altijd zichtbaar over het Kompas venster (z-index 11000).
    - **Stability Fix:** Het Kompas venster opent nu altijd binnen de zichtbare viewport, ongeacht de opgeslagen schermpositie.
- ✅ **Data Lineage Fundament:**
    - Introductie van de `bronnen` en `indicator_metadata` tabellen voor volledige herleidbaarheid van data-assets.

### Dag 38 (06-03-2026): Bugfix — 3D Extrusie Visualisatie & Belichting 🎮✨
**Focus:** Herstellen van de defecte 3D-weergave van gebieden op de kaart.

- ✅ **Bug #25 Fix — Camera Reset & WebGL Corruptie:**
    - Introductie van een `onViewStateChange` deck.gl listener die actief de camerahoek opslaat, zodat het aanvinken van de 3D-toggle de kaart niet meer reset naar de oceaan.
    - Oplossen van de triangulatie-artifacten (corrupte vlakken) door de 2D en 3D laag-ID's afzonderlijk te benoemen, wat de WebGL buffer beschermt tijdens the transition.
- ✅ **Materiaal & Belichtingsfixes (Transparantie):**
    - Verwijdering van een defecte FPS-monitor (`checkPerformance`) die 3D belichting bij kleine frame-drops definitief uitschakelde, wat resulteerde in grijze/doorzichtige schaduw-vlakken.
    - Vervangen van experimentele `_SunLight` door stabiele `DirectionalLight` voor scherper contrast.
    - Instellen van een `matte` (0 shininess) renderer in 3D en uitschakelen van de polygon-doorzichtigheid (`opacity: 255`) zodat de ingekleurde dataranges perfect bewaard blijven ongeacht de inkijkhoek.

### Dag 37 (05-03-2026): Bugfix — Ngrok Tunneling Compatibiliteit 🔧🌐
**Focus:** Applicatie volledig functioneel maken via ngrok tunneling.

- ✅ **Bug #22 Fix — Rapport Routing via ngrok:**
    - Hardcoded `isLocalhost` check in `app.js` verwijderd; gebruikt nu universele relatieve URLs.
    - Verouderde admin panel build (`static/admin-panel/`) ververst — React Router kende benchmark-route niet.
- ✅ **CORS Regex voor Ngrok:**
    - `allow_origin_regex` in `main.py` accepteert nu automatisch `*.ngrok-free.dev` origins (alleen in DEBUG mode).
- ✅ **Build & Deploy Workflow:**
    - `.agents/workflows/build-admin-panel.md` aangemaakt zodat de admin panel build bij toekomstige wijzigingen nooit vergeten wordt.

### Dag 36 (03-03-2026): Sprint 8E — Kleur-Transformatie "Triple Threat" Palet 🎨
**Focus:** Visuele revisie naar de "Deep Data" identiteit, CSS tokenisatie, map-highlights en light mode optimalisaties.

- ✅ **CSS Tokenisatie (`styles.css` & `admin.css`):**
    - Uniforme design-tokens toegekend voor de applicatie (`--brand-main`, `--brand-action`, `--brand-accent`, `--brand-nature`).
    - Volledige sanering van hardcoded `SWF-rood` actieknoppen voor `Trust Blue` (interfaces) en `Nature Green` (milieu-statussen).
- ✅ **Geïntegreerde Highlights (`app.js`):**
    - Deck.gl map-selecties accentueren nu de objecten in de `Geo Gold` merk-kleur. Hovering reageert via vergelijkbare tinten per het nieuwe design.
- ✅ **Kompas- en Paneel Integraties:**
    - Panel subheaders renderen nu met een strakke Trust Blue → Geo Gold gradient (`--primary-color`, `--accent-color`).
    - D3.js Sunburst `kompas.js` leunt niet langer op statische fallbacks en toont nu `var(--text-primary)` labels om contrast tussen Dark Mode/Light Mode in the main window the beschermen.
- ✅ **Bugfixes Light Mode (Bug #20 / #21):**
    - Ontbrekende leesbaarheid op basis van donkere contrast-overlappingen via CSS opgelost (waaronder `brightness(0) invert(1)` voor het dark-colored navigatie PNG logo en thema-detectie iteraties voor D3 text vulling).

### Dag 35 (02-03-2026): Sprint 8D — Benchmark Kaart-integratie & Bugfixes 🗺️⚖️
**Focus:** Typeahead fixeren, rapport-knop uitbreiden, Benchmark publiek toegankelijk maken.

- ✅ **Bug #17 Fix — Typeahead (Stap 1 & 2):**
    - Nieuw `GET /api/gebieden/zoek?q=<term>` endpoint in `routers/gemeenten.py` — full-text zoekopdracht zonder verplichte gemeente_code.
    - `gebiedenAPI.zoekGebieden(q)` toegevoegd in `api.ts`; verouderde `getGebieden()` vervangen.
- ✅ **BenchmarkPage Upgrade (Stap 3):**
    - Live debounced search (300ms) vervangt de gebroken pre-load van alle gebieden.
    - URL pre-populatie: `?gebied_a=BU...&gebieden_b=BU...,BU...` laat de kaart direct een Benchmark openen met pre-ingevulde gebieden.
- ✅ **Bug #11 Fix — Rapport-knop Modal (Stap 4 & 5):**
    - Single selectie: keuze-overlay (📄 Gebiedsdossier / ⚖️ Benchmark Vergelijker).
    - Multi-selectie (Shift+Klik): direct naar Benchmark met alle IDs als queryparams.
    - Toelichting in `templates/index.html` bijgewerkt.
- ✅ **Bug #18 Fix — Benchmark Publiek Toegankelijk:**
    - `<ProtectedRoute>` wrapper verwijderd van `/admin/rapport/benchmark` route in `App.tsx`.
- ✅ **Bug #19 Fix — Gemeente Dropdown Leesbaarheid:**
    - Expliciete donkere achtergrond + lichte tekst op `<option>` elementen in BenchmarkPage.

### Dag 34 (28-02-2026): Sprint 8C — Benchmark Vergelijker & Executive Summary ⚖️📋
**Focus:** Rapportage sjablonen uitbreiden met gebiedsvergelijking en executive summary.

- ✅ **Sjabloon C: Benchmark Vergelijker (Backend + Frontend):**
    - `generate_benchmark_payload()` met 3 vergelijkingsmodi: 1-op-n gebieden (max 5), gemeente-gemiddelde, Fryslân-gemiddelde.
    - Nieuwe endpoints: `GET /api/report/benchmark`, `GET /api/report/benchmark/narrative`.
    - `BenchmarkPage.tsx`: Typeahead GebiedSelector, 3-modus tabs, delta tabel per kwadrant, AI vergelijkingsnarrative.
    - Sidebar navigatie uitgebreid met ⚖️ Benchmark link.
- ✅ **Sjabloon A: Executive Summary (Backend):**
    - `generate_executive_payload()` filtert top 3 kansen en top 3 risico's uit bestaande Z-score data.
    - Endpoint: `GET /api/report/executive/{gebied_id}`.
- ✅ **LLM Prompt:**
    - Nieuwe `benchmark_vergelijker` system prompt voor vergelijkende AI analyse.
- ⏳ **Openstaand:** Executive frontend pagina, handmatige UI test BenchmarkPage, n-op-n benchmark (backlog).

### Dag 33 (24-02-2026): Sprint 7 — Multi-Gebied Analyse & Kompas Upgrade 📊🗺️
**Focus:** Volledig nieuwe multi-area selectie en vergelijkingsvisualisatie.

- ✅ **Multi-Select op de Kaart:**
    - Shift+Click / Ctrl+Click voor het toevoegen van meerdere gebieden aan selectie.
    - Floating selectie-badge met gebied-teller en clear-knop (`map-pin-plus.svg` icoon).
    - Alle geselecteerde gebieden worden groen gehighlight op de kaart.
- ✅ **Kompas Aggregatie (`kompas.js`):**
    - `loadMultiGebiedData()` fetcht data voor alle gebieden parallel en merget de hiërarchie-trees.
    - `_mergeHierarchies()` berekent recursief gewogen gemiddelden per indicator.
    - Kompas-info toont ``📊 Regio A, Regio B... — Gemiddelde van N gebieden``.
- ✅ **Vergelijkende Barcharts:**
    - Bij multi-select toont het Kompas detailpaneel horizontale barcharts per indicator.
    - Top 5 gebieden gesorteerd op waarde; `+N meer (gem: X.XX)` voor overige.
    - Het detail-paneel en zoom-niveau van de sunburst blijven behouden bij het toevoegen van een extra gebied.
- ✅ **Wiskundig Fundament & Data Engineering:**
    - Python script `scripts/ai/normalisation.py` gebouwd voor veilige Min-Max normalisatie `[0.01, 1.00]`. Voorkomt catastrofale zero's bij geometrische Kompas-aggregatie.
- ✅ **Semantisch Vector Zoeken:**
    - PostgreSQL is lokaal geüpgrade met `pgvector` en draait op OS niveau, gereed om de indicator en taxonomie-metadata te ontleden in Cosine Similarity zoekqueries.

### Dag 31 (22-02-2026): Rapportage Opschoning & PDF Export 📄✅
**Focus:** Sprint 8B - Afronding functionaliteiten rondom AI-rapportage

- ✅ **Publieke Toegang & Routing:**
    - Alias `/publiek-rapport` en `/rapport` zijn nu fallback-ready en afgeschermd van het verplichte React Admin loginscherm.
- ✅ **PDF Export & Print CSS:**
    - Verbeterd contrast voor dark-mode tabellen d.m.v. `:root` overrides in `@media print`.
    - Dynamische bestandsnaam-generatie in de React print handler (`<type>_<code>_<gemeente>_<datum>-export.pdf` inclusief the anti-leesteken validaties).
- ✅ **Data Correcties:**
    - Fix impact-interpretaties voor omgekeerde z-scores (`+/-`, `-/-`).
    - Opruimen ongekoppelde "spook"-indicatoren uit the database.
    - Gemeentenaam i.p.v. Code via SQL JOIN.

### Dag 28 (20-02-2026): AI Rapportagemodule Backend (Fase 1 & 2) 🤖📄
**Focus:** Sprint 8 - Modulaire API voor Data Aggregatie en Lokale Ollama Integratie.

- ✅ **Fase 1: Data Rekenlaag (Pre-Processing):**
    - Nieuwe `ReportDataService` die *on-the-fly* Z-scores en gemiddeldes (∆) per gebied berekent.
    - Slimme filtering die enkel de statistische "uitschieters" (Z-score > 1.0) doorlaat voor de prompt, om context-overload bij de LLM te voorkomen.
    - Endpoint: `/api/report/data/{gebied_id}`.
- ✅ **Fase 2: Narrative Engine (Lokale Ollama Qwen3):**
    - Database migratie `schema_v7_llm_prompts.sql` uitgevoerd voor het dynamisch inpluggen van System Prompts via de Admin API.
    - Nieuwe CRUD Service `/api/admin/prompts` aangemaakt voor dashboard beheer.
    - Timeout van de API koppeling verhoogd naar 120s voor zware lokale inferentie (Qwen3:30b).
    - Endpoint: `/api/report/narrative/{gebied_id}` genereert en formatteert feilloze JSON summaries.

### Dag 27 (16-02-2026): Data Verificatie & Legend Sync 🔧✨
**Focus:** Sprint 5E - Gemeente data verificatie en Kompas-Legenda synchronisatie

- ✅ **Gemeente Code Verificatie:**
    - Database codes correct (Smallingerland=0090, De Fryske Marren=1940)
    - Script `scripts/verify_gemeente_codes.py` gemaakt
    - CBS import herhaald → data nu beschikbaar
- ✅ **Bug #9 Fixed: Legenda Sync:**
    - Root cause: twee duplicate `updateLegenda()` functies in `app.js`
    - Geconsolideerd tot één robuuste versie met null-safe DOM access
    - Expliciete sync na Kompas indicator selectie
- ⏳ **Openstaand:** Legenda kleurbalk matcht nog niet indicator palette (hardcoded gradient)

### Dag 26 (15-02-2026): Visualisatie Standaard 🎨✨
**Focus:** Sprint 5D - Database-driven color palettes and visualization profiles

- ✅ **Database Schema v6:**
    - Extended `color_schemas` met palette_type, classificatie, klassen, nodata_kleur
    - 8 standaard palettes (sequential, diverging, specialized)
    - `visualisatie_profielen` table met pattern matching voor auto-config
- ✅ **Backend Integration:**
    - New `/api/visualisatie` router (public + admin endpoints)
    - `ColorScaleService` met 4 classification methods
    - Map backend renders dynamic colors from database
- ✅ **Admin Panel:**
    - `KleurschemasPage` met live color previews
    - Color picker modal met real-time gradient interpolatie
    - Profile editor voor indicator → palette mapping

### Dag 25 (15-02-2026): BAG Integratie & Dashboard Finalization 🏘️📊
**Focus:** Afronding BAG Fryslân en Admin Dashboard (Sprint 5C & 5F)

- ✅ **BAG Data Integratie:**
    - 6 Nieuwe indicatoren (Woonfunctie, Bouwjaar, Oppervlakte, etc.)
    - ~18k records toegevoegd, 97% dekking (100% in focusgemeenten)
    - Robuuste ETL script (`run_bag_import.py`) met spatial joins
- ✅ **Admin Dashboard V1.0:**
    - Data Export (CSV) functionaliteit live
    - Visualisatie van data quality en coverage per kwadrant

### Dag 20 (10-02-2026): Nieuwe Datasets & Metadata 📚✨
**Focus:** Inventarisatie & Documentatie van BAG, Postcodegebieden, en EP-Online.

- ✅ **Uitgebreide Documentatie:**
    - Metadata voor 4 cruciale datasets (BAG, PC4, PC6, EP-Online).
    - Verwerkingsplannen en ETL pipelines uitgewerkt.
    - 9 Nieuwe indicatoren gedefinieerd en gemapped naar Kompas.
- ✅ **Bugfix Kompas Service:**
    - Robuuste afhandeling van JSON velden (thresholds) toegevoegd voor bredere driver compatibiliteit.

### Dag 14 (01-02-2026): Beheerscherm MVP + Security Foundation 🛠️
**Focus:** Admin Panel voor Kompas beheer

- ✅ **Backend Admin API:**
    - 6 endpoints: health, score-types, color-schemas, indicatoren, hierarchie/tree
    - API key authenticatie (`X-Admin-Key` header)
    - Database uitbreiding: `color_schemas` tabel, `score_type` kolom
- ✅ **React Admin Panel:**
    - TypeScript + React Router + Zustand state
    - Login, Dashboard, Indicatoren pagina's
    - D-OmniTwin matching dark theme styling
    - API service layer met auth interceptor
- ✅ **Security Hardening (Punt 0):**
    - Environment variables (`.env`)
    - CORS lockdown
    - CSP + Security headers

### Dag 18 (08-02-2026): RIVM Data & Map Fixes 🏥🛠️
**Focus:** Uitbreiding databronnen en UX bugfixes

- ✅ **RIVM Data Integratie:**
    - Directe koppeling met RIVM/CBS OData (dataderden.cbs.nl)
    - Import van Gezondheidsmonitor (Roken, BMI, Eenzaamheid) op buurtniveau
    - ETL pipeline upgrade voor custom endpoints
- ✅ **UX Verbeteringen:**
    - Fix voor "dode zone" op kaart onder menu's (`pointer-events` CSS fix)

### Dag 19 (09-02-2026): Energielabels & Metadata 🏷️⚡
**Focus:** Data dekking en kwaliteit

- ✅ **Energielabel Import (Heel Friesland):**
    - Streaming XML import van RVO EP-Online (8GB)
    - 100% dekking voor "Gemiddeld energielabel" (was 17%)
    - Nieuwe indicator "Percentage met energielabel"
- ✅ **Metadata Verrijking:**
    - Automatische koppeling met CBS definities
    - Verbeterde omschrijvingen en eenheden
- ✅ **Bugfixes:**
    - Kaartlaag API (500 error) gefixt
    - Data correctie "Huishoudens totaal"

**Risk Reduction:** 🟢 LOW (stable version 1.4.2)

## ⚖️ Licenties & Hergebruik (Dual Licensing)

D-OmniTwin is een project dat streeft naar maximale maatschappelijke impact door een combinatie van (1) een bewezen methodiek en (2) een krachtige referentie-implementatie. Om dit te faciliteren hanteren wij een dual-licensing model:

1.  **De Software (EUPL 1.2)**
    Alle broncode in deze repository (Python backend, React/JS frontend, database-schema's en ETL-scripts) is gelicentieerd onder de [European Union Public License v1.2](./LICENSE). Dit garandeert dat de software open blijft en verbeteringen terugvloeien naar de gemeenschap, terwijl commerciële partijen de code wel kunnen gebruiken in hun dienstverlening (mits met behoud van openheid van de afgeleide werken).

2.  **De Methodiek & Documentatie (CC BY 4.0)**
    Het "gedachtegoed" — waaronder de D-OmniTwin methodiek, de Kompas-hiërarchie, alle documenten in de `/docs` map, de structuur van de indicatoren en de AI-prompting filosofie — is beschikbaar onder de [Creative Commons Attribution 4.0 International](./LICENSE-DOCS) licentie.

    *Wat dit betekent:* Je bent vrij om de methodiek te kopiëren, te verspreiden en commercieel in te zetten (bijv. in rapporten of presentaties), mits je een gepaste bronvermelding geeft (bijv: "D-OmniTwin Methodiek ontwikkeld door [Naam/Gemeente]").

Zie [NOTICE.md](./NOTICE.md) voor informatie over third-party licenties.

---

## 📁 Structuur
- `docs/`: Project documentatie + security guides.
- `data/`: Data bestanden.
- `scripts/`: Import, analyse en validatie scripts.
- `templates/`: HTML templates.
- `static/`: Frontend assets (JS/CSS).

## 🚀 Snel Opstarten

### Prerequisites
- Python 3.12+
- Node.js 18+ en npm 9+
- PostgreSQL 14+ met PostGIS
- Git

---

### 1. Environment Setup
```bash
# Clone repository (indien nieuw)
git clone <repo-url> && cd D-OmniTwin

# Python virtual environment
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Environment variables
cp .env.example .env  # OF: touch .env
nano .env
```

**Minimale `.env` configuratie:**
```env
# Database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=omnitwin_db
DATABASE_USER=omnitwin_user
DATABASE_PASSWORD=<your-password>

# Security
SECRET_KEY=<generate-with-openssl-rand-base64-32>
CORS_ORIGINS=http://localhost:8000,http://localhost:3000

# Mapbox
MAPBOX_TOKEN=<your-mapbox-token>

# Admin Panel
ADMIN_API_KEY=<generate-with-python-secrets.token_hex(32)>
```

---

### 2. Database Setup
```bash
# PostgreSQL database + user aanmaken
sudo -u postgres psql -c "CREATE USER omnitwin_user WITH PASSWORD 'your-password';"
sudo -u postgres psql -c "CREATE DATABASE omnitwin_db OWNER omnitwin_user;"
sudo -u postgres psql -d omnitwin_db -c "CREATE EXTENSION postgis;"

# Geconsolideerd schema laden (alle tabellen + views)
psql -U omnitwin_user -d omnitwin_db -f data/schema_latest.sql

# Data import
python scripts/import_gebiedsmonitor_config.py
```

---

### 3. Main App Starten
```bash
# Activeer environment
source .venv/bin/activate

# Start FastAPI server (geoptimaliseerd)
python run_dev.py
```

> [!TIP]
> **Waarom `run_dev.py`?** Dit script is slimmer dan een standaard `uvicorn` commando:
> 1. **Lazy Loading**: AI-modellen worden pas geladen als de chat wordt geopend (30% snellere start).
> 2. **Optimized Reload**: Voorkomt onnodige herstarts door `node_modules` en `admin-panel` uit te sluiten van de file-watcher.

**Toegang:**
- 🌐 **App:** http://localhost:8000
- 📚 **API Docs:** http://localhost:8000/docs

---

### 4. Admin Panel Starten (Optioneel)
```bash
# In nieuw terminal venster
cd admin-panel
npm install  # Alleen eerste keer
npm start
```

**Toegang:**
- 🔐 **Admin Panel:** http://localhost:3000/admin
- **Login:** Gebruik `ADMIN_API_KEY` uit `.env`

---

### 5. Alles Tegelijk (Development)
```bash
# Terminal 1: Backend
source .venv/bin/activate && python run_dev.py

# of de oude manier:
source .venv/bin/activate && uvicorn main:app --reload

# Terminal 2: Admin Panel  
cd admin-panel && npm start
```

## 🔒 Security

**Current Status (v1.3.0):**
- ✅ Environment-based secrets management
- ✅ CORS lockdown naar specifieke origins
- ✅ Security headers (CSP, X-Frame-Options, XSS Protection)
- ⏳ Database SSL/TLS (planned - Punt 0 completion)
- ⏳ HTTPS/TLS reverse proxy (Fase 1)
- ⏳ Authentication system (Fase 2)

## 📖 Documentatie
- **[README.md](/README.md)** - Project overview (dit document).
- **[BUILD.md](/BUILD.md)** - Installatie & Setup Guide.
- **[TODO.md](/TODO.md)** - Roadmap, sprints en taken.
- **[ROADMAP.md](/ROADMAP.md)** - Lange-termijn planning en features.
- **[ARCHITECTURE_TECHNICAL_OPERATION.md](/ARCHITECTURE_TECHNICAL_OPERATION.md)** - Technische architectuur.
- **[DATABASE_ARCHITECTUUR.md](/docs/7-projectmanagement/logs/DATABASE_ARCHITECTUUR_ANALYSE.md)** - Database Analyse & ERD.
- **[DATABASE_SETUP.md](/docs/7-projectmanagement/logs/DATABASE_INITIALISATIE_HANDLEIDING.md)** - Database Initialisatie Handleiding.
- **[Security Quick Wins Guide](/docs/7-projectmanagement/logs/SECURITY_QUICK_WINS.md)** - Emergency Patch stappenplan.
- **[DATASET_METADATA_NIEUWE_BRONNEN.md](/docs/7-projectmanagement/logs/DATASET_METADATA_NIEUWE_BRONNEN.md)** - Metadata van nieuwe datasets (BAG, EP-Online, PC4/PC6).
- **[VERWERKINGSPLAN_NIEUWE_DATASETS.md](/docs/7-projectmanagement/logs/VERWERKINGSPLAN_NIEUWE_DATASETS.md)** - ETL pipelines en verwerkingsstrategie.
- **[NIEUWE_INDICATOREN_MAPPING.md](/docs/7-projectmanagement/logs/NIEUWE_INDICATOREN_MAPPING.md)** - Mapping van 9 nieuwe indicatoren op het Kompas.

---

---

## 🤖 D-Omni Assistent — Lokale AI Integratie

D-OmniTwin bevat een ingebouwde AI-assistent die werkt als een **"alternatieve muis"**: de gebruiker stelt in gewone taal een vraag en de assistent stuurt de kaart, het Kompas en de rapportage aan.

### Architectuur

```
┌─────────────────────────────────────────────────────────┐
│  Gebruiker                                              │
│  "Welke buurten hebben weinig groen?"                   │
└──────────────────────┬──────────────────────────────────┘
                       │ POST /api/chat
┌──────────────────────▼──────────────────────────────────┐
│  Intent Router  (routers/chat.py)                       │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Intent Classifier (rule-based)                 │    │
│  │  VERKEN_INDICATORS │ VERGELIJK_GEBIEDEN          │    │
│  │  MAAK_RAPPORT      │ ALGEMEEN                   │    │
│  └──────────────┬──────────────────────────────────┘    │
│                 │                                       │
│  ┌──────────────▼──────────┐  ┌──────────────────────┐  │
│  │  AISearchService        │  │  LLMService          │  │
│  │  pgvector similarity    │  │  Ollama Qwen3:30b    │  │
│  │  ≤10 indicatoren        │  │  ≤80 woorden NL      │  │
│  └──────────────┬──────────┘  └──────────┬───────────┘  │
│                 └──────────────┬──────────┘              │
│                                │ Command Dispatch JSON   │
└────────────────────────────────┼────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────┐
│  ChatPanel  (static/js/chat.js)                         │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Narrative tekst  +  Actie-knoppen  +  Indicator-  │  │
│  │  lijst (scrollbaar, klikbaar)                      │  │
│  └─────────────┬──────────────────────┬───────────────┘  │
│               │ INDICATOR_SELECTED   │ MAAK_RAPPORT      │
│          EventBus                EventBus                │
│        ┌──────▼──────┐        ┌───────▼─────────┐       │
│        │  Kaart       │        │  Rapport Admin  │       │
│        │  (app.js)    │        │  /admin/rapport │       │
│        └──────┬───────┘        └─────────────────┘       │
│               │ INDICATOR_SELECTED (met _isSyncing guard) │
│        ┌──────▼───────┐                                   │
│        │  Kompas       │                                  │
│        │  (kompas.js) │ navigateToIndicator(uuid)         │
│        └──────────────┘                                   │
└────────────────────────────────────────────────────────- ─┘
```

### Intent Types

| Intent | Trigger-woorden | Acties |
|--------|-----------------|--------|
| `VERKEN_INDICATORS` | groen, leefbaarheid, kinderdagverblijf... | Toont indicatoren op kaart + Kompas |
| `VERGELIJK_GEBIEDEN` | vergelijk, benchmark, verschil... | Opent Benchmark pagina met selectie |
| `MAAK_RAPPORT` | rapport, dossier, exporteer... | Opent gebiedsdossier of benchmark |
| `ALGEMEEN` | alle andere vragen | Narratief antwoord zonder acties |

### Technische Details

- **LLM:** Lokale [Ollama](https://ollama.ai/) instantie met `qwen3:30b` (configureerbaar via `llm_config` tabel)
- **Vector Search:** `pgvector` (cosine similarity) op `indicator_embeddings` tabel
- **Beschrijvingsprioriteit:** menselijk gevalideerd → AI-gegenereerd → standaard omschrijving
- **Chat Zijpaneel:** Vanilla JS `ChatPanel` klasse, glassmorphism styling, thema-aware
- **EventBus:** Ontkoppeld commando-systeem — chat spreekt nooit direct met kaart of Kompas

### Instellingen

```bash
# Ollama starten (vereist)
ollama serve
ollama pull qwen3:30b  # of een kleiner model

# Model configuratie via Admin Panel → LLM Config
# OF via environment variabelen (fallback):
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3:30b
```

---

## 📊 API Endpoints Overzicht

### Public API (Main App)
| Endpoint | Method | Beschrijving |
|----------|--------|-------------|
| `/api/gebiedsmonitor/gebieden` | GET | Alle gebieden |
| `/api/gebiedsmonitor/indicatoren` | GET | Indicator metadata |
| `/api/kompas/configuraties` | GET | Kompas configuraties |
| `/api/kompas/hierarchie` | GET | Kompas hiërarchie |
| `/api/kaart/v2/data` | GET | Kaart GeoJSON data |
| `/api/chat` | POST | D-Omni Assistent chat |

### Admin API (Beveiligd - `X-Admin-Key` header)
| Endpoint | Method | Beschrijving |
|----------|--------|-------------|
| `/api/admin/health` | GET | API health check |
| `/api/admin/score-types` | GET | Score type opties |
| `/api/admin/color-schemas` | GET | Kleurschema's |
| `/api/admin/indicatoren` | GET | Indicatorenlijst |
| `/api/admin/indicatoren/{uuid}` | GET/PUT | Indicator CRUD |
| `/api/admin/hierarchie/tree` | GET | Kompas tree data |

---

**Versie:** 2.2.0
**Laatste Update:** 25 maart 2026


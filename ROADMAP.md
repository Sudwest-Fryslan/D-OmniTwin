# Feature Roadmap - D-OmniTwin Gebiedsmonitor

**Status:** 2026-06-30 (Dag 79) — Sprint 18 ✅ Afgerond | Sprint 19 📌 Gepland  
**Visie:** Van prototype naar productie-klaar, AI-gedreven gebiedsmonitor platform

---

## Current Status: MVP ✅

### Wat Werkt Nu (Dag 15 - 30 jan 2026)

![3D Kaart Prototype](file:///home/tl_admin/.gemini/antigravity/brain/28bf6700-acd3-4a0b-96c8-4b84484d1e1e/uploaded_image_1_1768646713724.png)

✅ **Backend API** (FastAPI)
- 5 RESTful endpoints
- Dynamic indicator filtering
- GeoJSON generatie met WGS84 conversie
- 1,721 gebieden, 226 indicatoren

✅ **Frontend Visualisatie** (deck.gl 3D)
- 3D kaart met extrusie
- Color scale (Blue → Yellow → Red)
- Gebiedstype/indicator selectie
- 3D toggle + height scale slider (1x-100x)
- Click handler voor gebied details

✅ **Database** (PostgreSQL/PostGIS)
- Schema v2.0
- Spatial indexing (GIST)
- RD New geometrieën (EPSG:28992)
- 100% geometrie coverage validated
- **Nieuw (Dag 18):** RIVM Gezondheidsdata (2012-2024) geïntegreerd via OData
- **Nieuw (Dag 23):** Admin Dashboard Beta (Data Quality & Coverage monitor) - **Operationeel (Dag 24)**

✅ **Data Integratie**
- CBS Kerncijfers (op buurtniveau)
- RIVM Gezondheidsmonitor (Roken, BMI, Eenzaamheid, etc.)
- Automatische ETL pipeline met custom endpoints
- **Nieuw (Dag 21):** Smart CBS Import (Targeted updates) & Dataset 50140NED toegevoegd
- **Nieuw (Dag 21):** Project Structuur Refactoring (`ETL/` folder)
- **Nieuw (Dag 25):** BAG Fryslân Integratie (Woonfuncties, Bouwjaar, Oppervlakte) ✅
- **Nieuw (Dag 25):** Admin Dashboard & Export Features ✅

---

## Prioritized Feature Development

### 🎯 Phase 1: Core User Experience (Hoge Prioriteit)

**Target:** Maak het platform intuïtief en visueel aantrekkelijk

#### 1.1 UI Redesign - Fullscreen Kaart met Verticale Tabs

**Rationale:** Kaart moet centraal staan, niet verborgen achter sidebar

![Huidige Layout](file:///home/tl_admin/.gemini/antigravity/brain/28bf6700-acd3-4a0b-96c8-4b84484d1e1e/uploaded_image_1_1768646713724.png)

**Nieuwe Layout:**
```
┌────┐ ┌──────────────────────────────────────────┐
│ 🗺  │ │                                          │
│ 📊 │ │         FULLSCREEN 3D KAART              │
│ 📤 │ │         (deck.gl)                        │
│ 📥 │ │                                          │
│ 📍 │ │                                          │
└────┘ └──────────────────────────────────────────┘
```

**Deliverables:**
- [ ] Verticale tab bar component (React/Vue of Vanilla JS)
- [ ] Collapsible panels met smooth animations
- [ ] Icon-only collapsed state (40px breed)
- [ ] 5 Panels: Legenda, Layers, Upload, Export, Kompas

**Technisch:**
- CSS Grid voor layout
- CSS transitions voor slide-in animations
- Z-index management voor overlays

**Tijd:** 8-12 uur  
**Priority:** 🔴 CRITICAL

---

### 🔓 Phase 8: Open Source Release & EUPL Decoupling (Sprint 14)

**Visie:** De source code openstellen voor samenwerking, door strikte scheiding aan te brengen tussen (1) Methodiek, (2) Referentie-Applicatie, en (3) Toolkit. Wij gebruiken een dual-licensing model (EUPL 1.2 & CC BY 4.0).

**Fases (Gebaseerd op de EUPL Audit 29-03-2026):**
- [x] **Fase 0 - Juridisch:** Licenties aangemaakt, `LICENSE` en `README` afgestemd (`Voltooid 29-03`).
- [ ] **Fase 1 - Security Audit (🔴 BLOCKER):** Git-history cleanen van alle `.env` en hardcoded secrets, `.env.example` uitbrengen.
- [ ] **Fase 2 - Technische Decoupling:** ETL scripts abstract maken, AI optioneel maken (feature flag), Docker Compose opzet.
- [ ] **Fase 3 - Documentatie Overhaul:** Herpositioneren README, methodiek in `METHODOLOGY.md` uitschrijven, `CONTRIBUTING.md` toevoegen.
- [ ] **Fase 4 - Publicatie Launch:** Plaatsing op public host (GitHub/GitLab), `publiccode.yml` aanmaken en release v1.0.0-beta taggen.

**Tijd:** ~30-40 uur  
**Priority:** 🔴 HIGH (Voorwaarde voor adoptie & subsidie)

---

### 📊 Sprint 19: Van Data naar Inzicht (Gepland)

**Visie:** D-OmniTwin transformeren van een data-exploratie platform naar een inzicht-gedreven besluitvormingsinstrument.  
**Aanleiding:** Gebruikersreview juni 2026 — consistente bevinding over alle 5 gebruikersprofielen.  
**Spec:** [`docs/7-projectmanagement/archief/sprint-19-plan_data-naar-inzicht.md`](./docs/7-projectmanagement/archief/sprint-19-plan_data-naar-inzicht.md)

#### Track A — Signalering: Automatische Uitschieters
- [ ] Stijgers & Dalers per indicator (top 3 stijgers + top 3 dalers)
- [ ] Afwijkingssignalering t.o.v. gemeenteén provinciaal gemiddelde

#### Track B — Prioritering: Inzicht per Buurt
- [ ] Top 5 risico’s per buurt (thema-overstijgend, o.b.v. z-score)
- [ ] Provinciaal gemiddelde als extra referentielijn in benchmark & trendgrafiek

#### Track C — Context: Scores in Gewone Taal
- [ ] Contextuele score-uitleg: z-score → *Aandacht / Gemiddeld / Goed* label
- [ ] Geleide gebruikersroute per doelgroep (rolkeuze bij onboarding)

#### Track D — AI-Ondersteuning
- [ ] AI-samenvatting per buurt via Ollama (lokaal, AVG-proof)

**Effort:** ~15-20 uur (4 sessies)  
**Priority:** 🔴 HIGH — direct gebruikerswaarde  
**Aanleiding:** [UX-bevindingen](./docs/4-ux-design/gebruikerservaringen/UX-bevindingen_gebruikersreview_2026-06.md)

---



**Rationale:** Gebruikers moeten direct zien wat de kleuren betekenen

**Features:**
- [ ] **Dynamic Color Scale:**
    - Blue (laag) → Yellow (midden) → Red (hoog)
    - Min/max waarde labels
    - Gradient visual
    - Eenheid tonen (aantal, %, m², etc.)
  - [ ] WMS/WFS Services aanbieden
    - [ ] D-OmniTwin als WMS server voor externe tools (QGIS, ArcGIS)
- [ ] Geocoding & Reverse Geocoding

## Fase 7: Beheeromgeving & Metadata
- [ ] **Beheer Interface:** 
    - [ ] CRUD voor scoring regels (`-=-`, `+=+`, etc.)
    - [ ] **AI-Audit & Herstel Dashboard:**
        - [ ] Automatische detectie van 'technische' of foutieve AI-outputs (via `src/utils/ai_audit.py`).
        - [ ] "Herstel-knop" om indicators via de 'Bron'-promp opnieuw te genereren.
    - [ ] Metadata beheer
    - [ ] **Configuratie Icoon Beheer:** Mogelijkheid om iconen (SVG/Images) te koppelen aan een kompas configuratie (ipv hardcoded emojis).
- [ ] **Advanced Data Viz:**
    - [ ] Trendlijnen (tijdreeksen) in detail panel (bottom bar).
    - [ ] "Wat zie ik?" metadata uitleg.
- [ ] **Data Coverage Indicator:**
    - "138 van 965 gebieden (14% coverage)"
    - Visual bar chart coverage
- [ ] **Interactive Legend:**
    - Click legend item → filter kaart
    - Slider om data range te beperken

**Technisch:**
- SVG voor gradient rendering
- D3.js scale functions voor color mapping
- State sync met kaart filters

**Tijd:** 6-8 uur  
**Priority:** 🔴 HIGH

---

#### 1.3 Light/Dark Theme Toggle

**Rationale:** Accessibility en gebruikersvoorkeuren

**Features:**
- [ ] Toggle in header (🌞/🌙 icon)
- [ ] localStorage persistence
- [ ] System preference detection (`prefers-color-scheme`)
- [ ] Smooth theme transitions
- [ ] Mapbox style switch (`light-v10` ↔ `dark-v10`)

**CSS Variables:**
```css
:root[data-theme="dark"] {
  --bg-primary: #0f172a;
  --text-primary: #f8fafc;
  --map-bg: #1e293b;
}
```

**Tijd:** 4-6 uur  
**Priority:** 🟡 MEDIUM

---

### 🧭 Phase 2: D-Omni Kompas Integration (Medium Prioriteit)

**Visie:** Kompas is het centrale navigatie-element voor indicatoren

![Kompas Screenshot](file:///home/tl_admin/.gemini/antigravity/brain/28bf6700-acd3-4a0b-96c8-4b844d1e1e/uploaded_image_0_1768646713724.png)

#### 2.1 Sunburst Visualisatie (D3.js)

**Interactie Flow:**
1. Gebruiker klikt gebied op kaart
2. Kompas verschijnt in Tab 5 (Kompas panel)
3. Kompas toont alle indicatoren voor dat gebied
4. Gebruiker klikt indicator in kompas
5. Kaart update met die indicator

**of:**

1. Gebruiker opent Kompas tab
2. Selecteert gebied via dropdown
3. Kompas toont data
4. Klik indicator → kaart update

**Features:**
- [ ] **D3.js Sunburst Chart:**
    - Hierarchie: Categorie → Dimensie → Indicator
    - Color-coded categories
    - Smooth drill-down/up animations
    - Tooltip met indicator details
- [ ] **Config-Driven:**
    - Gebruik `new_config_gebiedsmonitor_ind-geb-rel.json`
    - Dynamische hiërarchie obv config
    - Customizable categorieën
- [ ] **Data Integration:**
    - Toon alleen indicatoren met data voor dit gebied
    - Grijs uitgrauwen missing data segments
    - Size obv indicator waarde (optioneel)

**Technisch:**
- D3.js v7 (latest)
- SVG rendering
- State management: sync met kaart
- Responsive sizing

**Tijd:** 16-20 uur  
**Priority:** 🟡 MEDIUM-HIGH

---

#### 2.1B Multi-Gebied Kompas Analyse 🆕

**Rationale:** Gebruikers willen meerdere gebieden (buurten) selecteren en als één geheel analyseren in het Kompas.

**Use Case:**
1. Gebruiker selecteert 5 buurten op de kaart (multi-select via Ctrl+Click)
2. Kompas toont geaggregeerde gemiddelden van die 5 buurten
3. Per indicator: optellen waarden / aantal buurten = gemiddelde
4. Kleuring in Kompas op basis van dit gemiddelde
5. Trendlijnen vervangen door bar chart (per buurt, laatste jaar)

**Features:**
- [ ] **Multi-Selectie op Kaart:**
    - Ctrl+Click om meerdere gebieden toe te voegen aan selectie
    - Visual highlight van geselecteerde gebieden (groene outline)
    - "X geselecteerd" indicator in UI
    - Clear selectie button
- [ ] **Geaggregeerde Kompas:**
    - Gemiddelde waarde berekening: `AVG(waarde)` over geselecteerde gebieden
    - Score berekening op basis van gemiddelde
    - Gebiedsnaam weergave: "5 gebieden geselecteerd" in centrum
- [ ] **Benchmark Visualisatie:**
    - Per buurt vs gemiddelde vergelijking
    - Visual indicator: boven/onder gemiddelde (↑ groen, ↓ rood)
    - Tabel weergave met individuele buurtnamen + waarden
- [ ] **Bar Chart voor Trends:**
    - Vervangt line chart bij multi-selectie
    - X-as: Gebiedsnamen (ingekort indien >5)
    - Y-as: Waarde laatste jaar
    - Gemiddelde lijn over de bars heen
    - Tooltip: volledige naam + exacte waarde

**Backend Wijzigingen:**
```python
# Nieuwe endpoint
POST /api/kompas/multi-gebied
{
  "gebied_ids": ["BU19000000", "BU19000001", ...],
  "indicator_uuid": "..."
}

# Response
{
  "gemiddelde": 45.2,
  "gebieden": [
    {"id": "BU19000000", "naam": "Abbega", "waarde": 42.0, "vs_gemiddelde": -3.2},
    {"id": "BU19000001", "naam": "Achlum", "waarde": 48.5, "vs_gemiddelde": +3.3}
  ],
  "score": {
    "waarde": 45.2,
    "kleur": "#fbbf24",
    "percentiel": "P50-P75"
  }
}
```

**Frontend Wijzigingen:**
- `kaart.js`: Multi-select state management
- `kompas.js`: Detectie multi-gebied mode → switch bar chart
- `detail-panel.js`: Tabel voor gebied-vergelijking

**Technisch:**
- D3.js bar chart component
- SQL aggregatie queries (`AVG`, `COUNT`, `STDDEV` voor spreiding)
- State sync tussen kaart selectie en Kompas data

**Tijd:** 12-16 uur  
**Priority:** 🟡 MEDIUM  
**Dependencies:** Phase 2.1 Kompas Visualisatie moet compleet zijn

---

#### 2.2 Kompas API Endpoints

**Backend ondersteuning voor kompas:**

```python
# Nieuwe endpoints
GET  /api/kompas/gebied/{gebied_id}
GET  /api/kompas/config
POST /api/kompas/config  # Upload custom config
```

**Response structure:**
```json
{
  "gebied": {
    "id": "BU19000000",
    "naam": "Abbega"
  },
  "hierarchie": {
    "categories": [
      {
        "naam": "Verkeer",
        "color": "#10b981",
        "dimensies": [
          {
            "naam": "Mobiliteit",
            "indicatoren": [
              {
                "uuid": "...",
                "naam": "Auto bezit",
                "waarde": 450,
                "eenheid": "aantal",
                "jaar": 2024
              }
            ]
          }
        ]
      }
    ]
  }
}
```

**Tijd:** 8-10 uur  
**Priority:** 🟡 MEDIUM

#### 2.3 Sprint 4C: Kompas & UI Refinement (Voltooid)

**Focus:** Visuele rust en duidelijkheid in het Kompas

**Features:**
- [x] **Grafiek Overlay Redesign:** Huidige grafiek hindert het zicht; alternatief ontwerp nodig.
- [x] **Centrum Tekst:** Duidelijke weergave van gebiedsnaam en status.
- [x] **Indicator Context:** Tooltips/beschrijvingen bij indicatoren ("Wat betekent dit cijfer?").
- [x] **Clean-up:** Verwijderen van ongebruikte UI elementen ("Gebied" artifacts).

**Priority:** 🔴 HIGH (User Feedback)

---

### 🗺️ Phase 3: Basemap Layers (Medium Prioriteit)

#### 3.1 Mapbox Tile Integration

**Doel:** Professionele basemap in plaats van grijze achtergrond

**Features:**
- [ ] Mapbox API key configuratie
- [ ] Style selector:
    - Light (standaard)
    - Dark
    - Satellite
    - Streets
- [ ] Synchroniseren met theme (light/dark auto-switch)

**Implementatie:**
```javascript
// deck.gl mapStyle property
mapStyle: 'mapbox://styles/mapbox/light-v10'
```

**Trade-offs:**
- ✅ PRO: Professional look, snel te implementeren
- ⚠️ CON: Mapbox API key nodig (gratis: 50k req/maand)

**Tijd:** 3-4 uur  
**Priority:** 🟡 MEDIUM

---

#### 3.2 PDOK WMS/WMTS Layers (Optioneel)

**Nederlandse alternatief zonder API key**

**Layers:**
- [ ] BRT Achtergrondkaart (topografisch)
- [ ] Luchtfoto's (actueel)
- [ ] Kadastrale percelen

**Implementatie:**
- deck.gl `TileLayer` met WMTS endpoint
- PDOK  service URL: `https://service.pdok.nl/brt/achtergrond kaart/wmts/v2_0`

**Tijd:** 6-8 uur  
**Priority:** 🟢 LOW (nice-to-have)

---

### 📊 Phase 4: Data Management (Low-Medium Prioriteit)

#### 4.1 Data Export Features

**User Story:** Gebruiker wil data downloaden voor rapportage

**Features:**
- [ ] **Screenshot Kaart:**
    - High-res PNG export (1920x1080 of hoger)
    - Include legenda in screenshot
    - [x] **Interaction:** "Toon op kaart" robust sync & Green highlighting
    - [ ] **Text Alignment:** Horizontaal uitlijnen (niveau 1 & 2), max 3 regels, max 2 niveau's diep tonen.
    - [ ] **Config Selectie:** Verplaatsen naar "Open Kompas" popover (Image 1) om ruimte te besparen.
    - [ ] **Controls:** 3D/2D toggle en extrusie slider toevoegen aan Kompas venster.
    - [ ] **Visual:** Map transparency 60-80%.
    - [ ] **Scoring:** Nieuwe kleurschaal (Blauw spectrum, 8 bins van 12.5%) conform Image 2.
    - [ ] Optionele indicator selectie (gebieden tonen zonder indicator)
    - deck.gl canvas to blob
- [ ] **GeoJSON Export:**
    - Download huidige visible gebieden
    - Include indicator data in properties
    - Browser download via blob
- [ ] **CSV Export:**
    - Tabular data van zichtbare gebieden
    - Kolommen: gebied_id, naam, indicator_naam, waarde, jaar
- [ ] **Kompas SVG Export:**
    - Voor gebruik in rapporten/presentaties

**Tijd:** 6-8 uur  
**Priority:** 🟡 MEDIUM

---

#### 4.2 Data Upload Features

**User Story:** Gebruiker wil eigen data visualiseren

**Features:**
- [ ] **GeoJSON Upload:**
    - Drag-drop interface
    - Validation: check SRID, geometry type
    - Preview op kaart als temporary layer
    - Option: save to database
- [ ] **CSV Upload:**
    - Column mapping wizard
    - Match geometrie via gebied_id/naam
    - Preview table voor import

**Security:**
- File size limits (max 10MB)
- MIME type validation
- Sanitize user inputs

**Tijd:** 10-12 uur  
**Priority:** 🟢 LOW

---

### 🤖 Phase 5: AI Rapportage & Vergelijking (Nieuwe Sprint 8 - VOLTOOID ✅)

**Context:** Implementatie van de modulaire AI-aangedreven rapportagemodule.
**Architectuur:** 3-Lagen (Pre-processing, LLM Narrative, React Frontend).

#### Fase 1: Data Aggregatie & Pre-LLM (De Rekenlaag) - ✅ VOLTOOID
- **Doel:** "Data Overload" voor de LLM voorkomen.
- **Features:**
    - Delta-berekening: Z-scores en afwijkingen per indicator (t.o.v. gemeente/historie).
    - Filtering: Alleen significante uitschieters (top 10%) behouden.
    - JSON Payload constructie afgestemd op LLM context windows.

#### Fase 2: Narrative Engine (Lokale Qwen 30B) - ✅ VOLTOOID
- **Doel:** Genereren van gestructureerde teksten en het duiden van verbanden.
- **Features:**
    - Ollama API integratie voor lokale inferentie (AVG-proof).
    - Prompt constructie obv het D-Omni Kompas taxonomie-anker.
    - JSON-only output generatie (executive summary, domain insights).

#### Fase 3: Dynamische Frontend Sjablonen (React) - ✅ VOLTOOID
- **Doel:** Visuele, deelbare rapportages obv de AI output.
- **Features:**
    - Componenten ontwikkelen: `MapSnapshot` (Mapbox Static API), `TrendChart`, `LLMSummary`.
    - Sjabloon A: Executive Summary implementeren in React.
    - **SVG Export Integratie:** D3 Sunburst componenten direct serialiseren naar SVG voor haarscherpe rapporten (printkwaliteit).
    - **Print CSS:** Strikte `@media print` rules (sidebar/header verbergen) voor PDF export.
    - Rich text Clipboard API integratie (voor copy/paste naar Word).

#### Fase 4: Vergelijkingsmodus (Bonus / Sprint 8b)
- **Doel:** Geavanceerde A/B vergelijking van gebieden (bijv. Buurt vs Gemeentegemiddelde).
- **Features:**
    - **Docking System:** UI ondersteuning om rapportage-panels 'vast te zetten' in een 2-column layout naast de kaart (zodat de kaart altijd centraal overzicht houdt).
    - **State Management:** Uitgebreide React state (`comparisonMode`, `primaryGebiedId`, `secondaryGebiedId`).
    - Synchrone kaart interactie (Linked Views).

#### 5.3 Beheeromgeving
- **Doel:** Beheer van complexe scoring regels en relaties.
- **Features:**
    - Interface voor bewerken van indicator relaties.
    - Configuratie van weegfactoren.

### 🔍 Phase 6: AI & RAG Kompas (Parallelle Track)

**Context:** Direct en intuïtief zoeken via (Lokale) AI en semantiek op het D-OmniTwin Kompas. Deze track loopt iteratief en onafhankelijk naast de verdere Core-ontwikkeling van Phase 7.

#### Track B.1: Wiskundige Herstructurering & Normalisatie
- **Methodologie:** Implementeren van objectieve wegingsmodellen (Entropy / CRITIC) via Python in plaats van de huidige statische wegingen, zodat de Single Source of Truth wiskundig is onderbouwd vóórdat het een AI-index wordt.

#### Track B.2: Semantisch Zoeken (Vectorlaag)
- Zoekbalk implementeren (fuzzy search / synoniemen) om indicatoren via trefwoorden in de database (`pgvector`) te vinden en het Kompas automatisch open te klappen.

#### Track B.3: D-Omni Assistant (NLQ & Ollama)
- "Chat" integratie met open/lokale LLM's (RAG architectuur).
- Omzetten van natuurlijke vragen naar de juiste API-events in het React frontend framework.
- Focus: Privacy-aware, 100% offline AI nodes.
- **Nieuw:** Persoonlijke Chat Historie Accounts (met export-functionaliteit en automatische 30-dagen policy / data-retentie om privacy te waarborgen).

**Documentatie:** Zie `docs/7-projectmanagement/logs/verkenning_ai_zoekfunctie_kompas.md`, de RAG-blauwdruk en het complete plan `docs/7-projectmanagement/logs/plan_aanpak_ai_parallel_track.md`.
**Prioriteit:** 🟢 PARALLEL (Loopt naast Sprint 9/Beheeromgeving)

---

### 🚀 Phase 7: Advanced Features (Low Prioriteit - Future)

#### 6.1 Time Slider (UPGRADED TO SPRINT 16)
- [ ] **Implementation:** 
    - Historical data transition (2012-2024).
    - Modern semi-transparent Time Slider UI with Play-Pause and Scrubbing.
    - Deck.gl transitions for height and color.
- **Sprint 16: Time Traveler - Indicator History**

#### 6.2 Advanced Selection Tools
- Draw polygon on map → stats
- Radius selection (within X km)

**Tijd:** 8-10 uur

---

#### 6.3 Kaart Viewport Gedrag — Vrije-Zone Centreren (Sprint 16)

**Rationale:** Het Kompas-venster, het linkerpaneel en de chat-zijbalk kunnen de geselecteerde buurt visueel bedekken. Het huidige `flyToGebied()` centreert altijd op het midden van het volledig scherm, zonder rekening te houden met overlappende UI-elementen.

**Gewenst gedrag:** Bij klik op een buurt → kaart centreert in het **grootste vrije, onbedekte kaartgebied** (links of rechts van het Kompas-venster, rekening houdend met alle open panelen).

**Aanpak:**
- `getFreezone()`: berekent real-time de vrije zone op basis van tab bar (70px), linkerpaneel (360px indien open), chat panel (380px indien open) en Kompas-venster positie via `getBoundingClientRect()`
- `flyToGebied()`: gebruikt deck.gl `padding` in `viewState` om het effectieve viewport-centrum te verschuiven naar de vrije zone
- `fitBounds()` guard: ontkoppeld van `displayOnMap()` re-renders via `state.initialDataLoaded` flag

**Details:** Zie `TODO.md` → Sprint 16  
**Tijd:** ~3–5 uur  
**Priority:** 🟡 MEDIUM

---


## Implementation Timeline

### Sprint 1 (Week 1): Core UX
- UI Redesign verticale tabs
- Legenda systeem
- Light/Dark theme
- **Output:** Professionele, intuïtieve UI

### Sprint 2 (Week 2): Kompas
- D3.js Sunburst implementatie
- Kompas API endpoints
- Integratie met kaart
- **Output:** Werkend kompas met indicator selectie

### Sprint 3 (Week 3): Basemaps & Polish
- Mapbox integration
- Export features
- Bug fixes & optimization
- **Output:** Production-ready v1.0

### Sprint 4 (Week 4-5): Kompas & Polish (Voltooid)
- D3.js Sunburst
- UI Polish (Flexbox layout, Info toggle)
- Bugfixing & Performance

### Sprint 4C (Week 6): Kompas Refinement (Voltooid)
- Grafiek overlay fix
- Context & Beschrijvingen
- Visual tuning
- Zoom scaling & Center interaction

### Sprint 5 (Next): Data Verrijking & Beheer
- **Databron Definities:** Koppelen van metadata/definities aan indicatoren.
- **Beheerscherm-kompas:** Interface voor het beheren van indicator-relaties en wegingen. (🔴 HIGH PRIORITY)
- **RIVM Data Integratie:** ✅ VOLTOOID (Dag 18) - Gezondheidsdata toegevoegd.
- **Metadata Management:** Koppeling met officiële bronnen en definities (RIVM/CBS) via `enrich_metadata.py`.
- Data Upload (GeoJSON/CSV)
- Rapportage module

### Sprint 5B (Week 8): Data Expansie & Integratie (Q1 2026)

**Focus:** Verbreding van de gebiedsmonitor met externe bronnen

#### 5B.1 Energielabels (Voltooid)
- ✅ **Import & Dekking:** 100% van Friese huishoudens voorzien van energielabel data (RVO).
- [ ] **Kompas Integratie:** Koppelen van indicatoren ("Percentage met energielabel") aan het domein 'Wonen' -> 'Technische kwaliteit'.
- [ ] **Visualisatie:** Weergave van energielabel verdeling per buurt.

#### 5B.2 Leefbaarometer
- [ ] **Data Import:** Ophalen van leefbaarheidsdata (fysieke omgeving, veiligheid, voorzieningen).
- [ ] **Mapping:** Koppelen aan relevante Kompas domeinen (Leefbaarheid, Sociale cohesie).
- [ ] **Score Normalisatie:** Integratie in het bestaande scoresysteem.

#### 5B.3 Politie Data (Veiligheid)
- [ ] **Misdaadcijfers:** Integreren van inbraak, geweld en overlast data op buurtniveau.
- [ ] **Veiligheidsbeleving:** Koppelen van subjectieve veiligheidscijfers.
- [ ] **Privacy:** Aggregatie waar nodig om herleidbaarheid te voorkomen.

#### 5B.4 BAG Fryslân Integratie (Nieuw - 10-02-2026)
- [ ] **Data Import:** Importeren van BAG verblijfsobjecten en panden voor Fryslân.
- [ ] **Kerngegevens:** Gebruiksdoel (functie), Bouwjaar (energie-transitie), Oppervlakte
- [ ] **Indicator Generatie:**
    - Gemiddeld bouwjaar woningen per buurt/PC4
    - Percentage woningen voor 1945 (energie-renovatie potentie)
    - Gemiddelde woonoppervlakte
    - Diversiteit gebruiksfuncties (wonen/winkel/kantoor mix)
    - Huishoudens telling (woonfunctie VBO's) → koppeling met EP-Online coverage
- [ ] **Kompas Koppeling:** Integreren onder dimensie 'Wonen' → 'Technische Kwaliteit' + 'Ruimte'
- [ ] **Visualisatie:** Kaart kleuring op bouwjaar (historische kernen vs nieuwbouw)

> [!IMPORTANT]
> **Data Gaten:** Let op! Wijken/buurten in **Smallingerland (0090)** en **De Fryske Marren (1940)** missen bouwjaar data. Dit moet specifiek worden onderzocht en opgelost tijdens de BAG import (mogelijk via alternatieve koppeling of fallback).

**Prioriteit:** 🔴 HOOG (Cruciaal voor energie-transitie analyses)  
**Effort:** 10-12 uur (ETL pipeline + aggregatie scripts)  
**Documentatie:** zie `docs/7-projectmanagement/logs/DATASET_METADATA_NIEUWE_BRONNEN.md`, `docs/7-projectmanagement/logs/NIEUWE_INDICATOREN_MAPPING.md`
**Context:** Uitbreiding van woningindicatoren met BAG gebouwkenmerken  
**Basis:** DATASET_METADATA_NIEUWE_BRONNEN.md + NIEUWE_INDICATOREN_MAPPING.md  
**Status:** ✅ VOLTOOID (15-02-2026)
- ✅ `scripts/run_bag_import.py` operational (fixed bugs/encodings)
- ✅ 6 nieuwe BAG-gebaseerde indicatoren in database
- ✅ Kompas integratie getest en functioneel
- ✅ EP-Online coverage indicator met BAG denominateur

#### 5B.5 Postcode Analyses: PC4-niveau Aggregatie (BACKLOG - Was Sprint 5D)
- [ ] **PC4 Gebiedstype:** Toevoegen als nieuw aggregatieniveau (tussen buurt en gemeente)
- [ ] **Import Postcodegebieden:** 950 PC4 gebieden voor Fryslân
- [ ] **Aggregatie Pipeline:** Buurt-data automatisch aggregeren naar PC4 niveau
- [ ] **Rationale Verschiving:** Prioriteit gegeven aan Visualisatie Standaarden (Sprint 5D)
- [ ] **Use Case:** Regionale vergelijkingen die   gemeentegrenzen overschrijden
- [ ] **Frontend:** Dropdown uitbreiden met PC4 optie naast Buurt/Wijk/Gemeente
- [ ] **Provincie Grens:** Visuele kaartlaag (boundary overlay, geen data-aggregatie)

**Prioriteit:** 🟡 MEDIUM (Verschoven naar Backlog/Sprint 5G)  
**Effort:** 6-8 uur (Database schema + frontend dropdown)  
**Documentatie:** zie `docs/7-projectmanagement/logs/VERWERKINGSPLAN_NIEUWE_DATASETS.md`

**Priority Sprint 5B Totaal:** 🔴 HIGH (Cruciaal voor compleet beeld van gebiedskwaliteit)

### Sprint 5D: Visualisatie Standaard (Nieuw - Week 10)
**Context:** Verbeterslag voor kaartvisualisatie, legenda en kleurschema's.
**Basis:** `docs/7-projectmanagement/logs/PLAN_KAARTVISUALISATIE.md` (In development)
**Prioriteit:** 🔴 HIGH

---

### 🎨 Sprint 8E: Kleur-Transformatie "Triple Threat" Palet (03-03-2026) ✅ VOLTOOID

**Context:** Vervangen van gefragmenteerd kleurgebruik door een unified "Deep Data" identiteit.  
**Basis:** `docs/4-ux-design/visual/kleur_translatie_tabel_deep_data.md` + `docs/4-ux-design/visual/Concept-collor-overhaul.html`  
**Plan:** `SPRINT_KLEUR_TRANSFORMATIE.md`  
**Prioriteit:** 🔴 HIGH  
**Effort:** 7–12 uur

#### De Drie Pijlers

| Kleur         | Hex       | Rol                                           |
|---------------|-----------|-----------------------------------------------|
| Trust Blue    | `#3182CE` | Interface, navigatie, primaire acties (CTA)   |
| Nature Green  | `#48BB78` | Milieu-indicatoren, duurzaamheid, status OK   |
| Geo Gold      | `#ECC94B` | Highlights, π-node, actieve kaartselectie     |

#### Fases

- [x] **Fase 1:** CSS Tokenisatie — centrale kleur-tokens in `styles.css` en `admin.css`
- [x] **Fase 2:** Rood Sanering — rood alleen voor fouten/kritieke meldingen
- [x] **Fase 3:** Geo Gold Implementatie — kaartselectie, 3D pieken, logo accent
- [x] **Fase 4:** Kaartkleurschalen bijwerken via Admin Panel kleurschema's
- [x] **Fase 5:** Dark Mode Hue-Consistency — zelfde hue, alleen luminance wisselt




#### 🔜 Fase 4: Frontend Client Integration (In Progress)
- [x] `app.js` - Legend sync: `updateLegenda()` geconsolideerd (Bug #9 FIXED)
- [x] `app.js` - Kompas → Legend sync via `handleIndicatorSelection`
- [ ] `app.js` - Legend kleuren matchen met indicator kleurschema (palette uit backend)
- [ ] `app.js` - Fetch config from `/api/visualisatie/config/{uuid}`
- [ ] Transitie animaties bij schema wijziginguratie.

#### Fase 1: Architectuur
- Database tables voor `visualisatie_profielen` en `kleur_paletten`.
- Backend endpoints voor configuratie.

#### Fase 2: Frontend Logic
- Centralized `ColorScaleService` (D3 based).
- Dynamic `deck.gl` styling based on config.

#### Fase 3: UI Improvements
- Interactive Legend component (histogram capable).
- Enhanced Tooltips.

### ⏳ Sprint 10 & 11: API voor Data Vulling & ETL Beheer (Nieuwe Roadmap Order)

**Context:** Vervanging van batch Python scripts door web-based upload API voor betere gebruikservaring en controle.

#### 10.1 Upload API Endpoints (Sprint 10) - 2 weken
- [ ] **CSV Metingen Upload:**
    - `POST /api/upload/csv/metingen`: Upload metingen voor gebied_data tabel
    - MIME type validatie, pandas parsing, foreign key validation
    - Transactioneel insert met rollback bij fouten
- [ ] **GeoJSON Gebieden Upload:**
    - `POST /api/upload/geojson/gebieden`: Upload nieuwe gebieden
    - Geometry validation, SRID transformatie (WGS84 → RD New)
    - Automatic centroid calculation
- [ ] **Excel Indicator Metadata Upload:**
    - `POST /api/upload/excel/indicatoren`: Bulk indicator metadata update
    - Column mapping wizard
    - Duplicate detection

#### 10.2 Async Processing Queue (Sprint 10) - 1 week
- [ ] **Background Task Queue:**
    - Celery of RQ setup met Redis backend
    - Worker processes voor file processing
    - Job status tracking (`GET /api/jobs/{job_id}`)
- [ ] **Progress Feedback:**
    - Real-time progress updates (WebSocket of polling)
    - Error reporting per row
    - Downloadable error report (CSV)

#### 10.3 Validation Pipeline (Sprint 10) - 1 week
- [ ] **Multi-layer Validation:**
    - File level: MIME type, size limit (max 10MB), encoding check
    - Schema level: Column presence, data types, required fields
    - Business logic: Foreign key existence, value ranges
    - Security: Virus scan (ClamAV), SQL injection prevention
- [ ] **Error Handling:**
    - Graceful degradation (partial imports with error report)
    - Detailed error messages (row number, column, reason)

#### 10.4 Admin Panel Upload UI (Sprint 10) - 2 weken
- [ ] **Upload Interface:**
    - Drag-drop file upload component
    - Preview data table (first 10 rows)
    - Column mapping wizard (CSV → DB columns)
    - Progress bar met cancel option
- [ ] **Job Management:**
    - Upload history lijst
    - Re-run failed jobs
    - Download error reports

#### 10.5 Migration Strategy (Sprint 10-11) - 1 week
- [ ] **Parallel Operation:**
    - API endpoints + legacy scripts beide beschikbaar
    - Testing periode (2 weken)
    - Performance comparison
- [ ] **Script Deprecation:**
    - Move scripts naar `scripts/legacy/`
    - Update documentatie
    - Training voor gebruikers

**Rationale:**
- ❌ **Huidige situatie:** Command-line scripts, geen real-time feedback, niet web-based
- ✅ **Met API:** User-friendly, validatie feedback, access control, audit logging
- 📊 **Impact:** Drastisch verbeterde data management workflow

**Dependencies:**
- Celery/RQ + Redis (background processing)
- python-magic (MIME detection)
- ClamAV (virus scanning)
- React components voor admin panel

**Priority:** 🟡 MEDIUM-HIGH
**Total Effort:** 6 weken
**Enables:** Self-service data uploads, betere data quality

---

## Technical Dependencies

### Frontend Libraries to Add

```json
{
  "d3": "^7.8.5",           // Voor sunburst
  "file-saver": "^2.0.5",   // Voor downloads
  "papaparse": "^5.4.1"     // Voor CSV parsing
}
```

### Backend Additions

- Config JSON parser voor kompas hierarchie
- File upload endpoints (multipart/form-data)
- Export endpoints voor CSV/GeoJSON

---

## Success Metrics

**Phase 1 Success:**
- ✅ Users can navigate without instructions
- ✅ Kaart vult >80% van scherm
- ✅ < 2 sec legenda load time

**Phase 2 Success:**
- ✅ Kompas → Kaart interaction <500ms
- ✅ All 226 indicatoren accessible via kompas
- ✅ Users prefer kompas over dropdown

**Phase 3 Success:**
- ✅ Basemap loads <1 sec
- ✅ Theme switch <200ms transition

---

### 🌐 Phase 9: Dataspace Orchestration (Innovation Track)
**Visie:** D-OmniTwin als federatieve orkestratielaag bovenop Data Spaces (FRLDS / FDS).

- [ ] **Sprint 18: Dataspace-Native PoC**
    - Onderzoek API-koppeling met Fryslân Data Space (FRLDS).
    - Ontkoppelen van lokale indicator-tabellen naar federatieve bronnen.
- [ ] **Sprint 19: Dynamisch Kompas v3**
    - Het Kompas-model onafhankelijk maken van de database-schema's (agnostische mappings).
- [ ] **Sprint 20: AI Narratieven voor Burgers**
    - LLM-vertaling voor lokale context op basis van live federatieve data.
- [ ] **Sprint 21: Innovatiebudget Validatie**
    - Pilots in 3 gemeenten (Súdwest-Fryslân, Leeuwarden, Tytsjerksteradiel).

---


**Documentatie:** Zie BRAINDUMP.md voor gedetailleerde technische overwegingen  
**Tracking:** Updates in TODO.md per sprint

---

## 🌟 Lange Termijn Visie: D-OmniTwin als AI-Gedreven Gebiedsassistent

*Toegevoegd: 16-03-2026 — Stip op de horizon voor het gehele platform*

D-OmniTwin evolueert van een **kaartvisualisatiesysteem** naar een **AI-gedreven Gebiedsassistent** waarbij de grens tussen data verkennen en data begrijpen verdwijnt. De drie pijlers voor deze transitie:

### Pijler 1: Intelligente Beheeromgeving
Het Admin Panel wordt niet alleen een plek om indicatoren te configureren, maar ook de **kwaliteitsbewaker van alle AI-output**.
- Ontologie Validatie Workflow: Elke indicator doorloopt een `AI-gegenereerd → In Review → Goedgekeurd` status.
- Audit Trail: Volledige traceerbaarheid van wie wat wanneer heeft goedgekeurd.
- AI als reviewer: LLM signaleert inconsistenties *voordat* de beheerder ze ziet.

### Pijler 2: Intent-Based Interactie (Chat → App)
De D-Omni Assistant Chat is niet een chatbot die tekst oplepelt. Het is een **alternatieve muis** die:
- Via **Command Dispatch JSON** de kaart, het Kompas en de rapportmodule direct aanstuurt.
- Actie-knoppen toont op basis van de gebruikersvraag (bijv. *"Hoe groen is mijn buurt?"* → knop *"Toon: Oppervlakte groen op kaart"*).
- Rapporten triggert gefocust op het gestelde thema (*"Maak rapport: Klimaat & Groen"*).

### Pijler 3: Sluitende Feedback Loop
Gebruikersinteracties verrijken het systeem:
- Positief/negatief feedback per chat-response.
- Negatieve feedback → Indicator terug naar validatiequeue in Admin Panel.
- Op termijn: fine-tuning dataset voor een domein-specifiek Fries gemeentemodel.

### Technische Mijlpalen (volgorde):
1. **Sprint 9 (Voltooid):** Ontologie Validatie-workflow in Admin Panel + Aggregatielagen.
2. **Sprint 10 (Voltooid):** `POST /api/chat` met Command Dispatch output + frontend actie-knoppen + Chat↔Kompas sync.
3. **Sprint 11B (Voltooid):** UX-Overhaul — 5 tracks (A t/m E) geïmplementeerd. Onboarding, feedback micro-interacties, indicator accordion, WCAG en AI-governance. Squash merge `2fbb00c` → `main`. Closes #7.
4. **Sprint 12 (Volgende):** 3D BAG Integratie — realistische pandmodellen via deck.gl Tile3DLayer + pand-niveau indicator koppeling.
5. **Sprint 13:** Feedback Loop UI (👍/👎) + koppeling aan validatieworkflow + Chat SSE streaming.
6. **Sprint 14+:** Aggregatielagen (PC6, PC4, Woonplaats) + finetuning dataset opbouw.

---

## 🎨 Sprint 11: Chat Afronding & Visuele Overhaul *(Gepland)*

**Doel:** De chat-assistent afronden als volwaardige stuur-'muis' en het plan uitstippelen voor een complexe visuele overhaul.

**Scope:**
- **Track A: Chat:** Verdere ontwikkeling van intent-herkenning en actie-uitgevoering vanuit de AI.
- **Track B: Visual:** Kaders en gedachtes verkennen vanuit het user-document voor de visuele vernieuwing.

---

## 🏙️ Sprint 12: 3D BAG Integratie *(Gepland)*

**Doel:** Realistische 3D gebouwmodellen als extra kaartlaag via de open 3DBAG dataset van TU Delft (deck.gl Tile3DLayer).

**Scope:**

### Track A: Tile3DLayer PoC (Fase 0)
- `@loaders.gl/3d-tiles` installeren
- Statische `Tile3DLayer` met LoD1.2 over de basemap
- Toggle-knop in de verticale tab-balk
- Verificatie op Leeuwarden binnenstad (zoom 14+)

### Track B: LoD-selectie & Indicator Koppeling (Fase 1)
- LoD-kiezer in de UI: LoD1.2 (snel) / LoD2.2 (detail)
- Auto-switch op basis van zoomniveau (< 14 = LoD1.2)
- BAG `identificatie` ↔ onze `indicatoren` koppeling
- `getColor()` op basis van energielabel of bouwjaar

### Track C: Pand-niveau Interactie (Fase 2)
- Hover-tooltip: naam, bouwjaar, oppervlak (3D BAG REST API)
- Klik-context naar D-Omni Assistent chat
- Copyright notice: `© 3DBAG by 3DGI and TU Delft`

**Afhankelijkheden:** deck.gl v8+, `@loaders.gl/3d-tiles`, EP-Online data in DB (✅ aanwezig)  
**Details:** Zie `BRAINDUMP.md` → *3D BAG Integratie* sectie

---

## ✅ Sprint 17: Configureerbare Logging Infrastructuur *(Afgerond — Dag 69, 26 mei 2026)*

**Doel:** Gedifferentieerde, configureerbare logging op alle facetten van de applicatie — instelbaar per module via de beheeromgeving, persistent in PostgreSQL, zichtbaar via admin panel dashboard.  
**GitHub Issue:** #9  
**Branch:** `feature/sprint-17-logging` → gemerged naar `main` (commit `4ed45bd`)  
**Spec:** [`docs/5-secops/logging/sprint-17-logging-spec.md`](./docs/5-secops/logging/sprint-17-logging-spec.md)

### Fasering

| Fase | Scope | Status |
|------|-------|--------|
| **17A** | Fundament: `AsyncLogQueue`, `AppLogger`, `app_logs` DB schema, `RequestLoggingMiddleware`, `print()` sanering | ✅ Afgerond (`d8b1552`) |
| **17B** | Module logging (Auth, Chat, BAG3D), log viewer admin panel (Log Stream tab, config editor) | ✅ Afgerond (`8d90932`) |
| **17C** | Gebruik & Gezondheid dashboard, dagelijkse cleanup service, p95 stats, top endpoints | ✅ Afgerond (`481a43d`) |
| **17C e-mail** | E-mail alerts bij ERROR/CRITICAL | ⏳ On hold — Issue #10 — wacht op SMTP-server |

### Categorieën
`SERVER` · `API` · `AUTH` · `KOMPAS` · `KAART` · `RAPPORT` · `LLM_CHAT` · `DATABASE` · `ADMIN`

### Open punt
⚠️ **E-mail alerts (Issue #10)** — Must-have voor deelbare versie. Design: eigen SMTP-server, volledig configureerbaar via `.env`. Zie `TODO.md` blocker sectie.

**Priority:** 🔴 HIGH (SecOps fundament)  
**Effort:** 3 sessies gerealiseerd

---

## 🚧 Sprint 18: IJsselmeerkust als Besluitinstrument *(Gepland — 2026-06-02)*

**Doel:** D-OmniTwin transformeren van een *verkenningsinstrument* naar een *besluitondersteunend instrument* — getoetst aan de casus IJsselmeerkust & Wadden (Makkum, Workum, Koudum).  
**GitHub Issue:** Aan te maken  
**Branch:** `feature/sprint-18-ijsselmeerkust` (aan te maken)  
**Spec:** [`docs/7-projectmanagement/archief/sprint-18-plan_ijsselmeerkust-besluitinstrument.md`](./docs/7-projectmanagement/archief/sprint-18-plan_ijsselmeerkust-besluitinstrument.md)  
**Afgeleid van:** NM-001 gap-analyse + TC-06-001 (E2E Beleidsadviseur IJsselmeerkust)

### Tracks

| Track | Deliverable | Testcase |
|-------|-------------|----------|
| **A1** | Bronvermelding + peildatum per indicator (Kompas) | TC-02-001 stap 3 |
| **A2** | Z-score uitleg (contexttooltip) | TC-02-001 stap 4 |
| **A3** | Trendlijn (≥ 2 meetmomenten) in Kompas-detailpaneel | TC-02-001 stap 6 |
| **B1** | BAG woonplaatsen importeren (`bag_woonplaatsen` tabel) | TC-01-003 Track B |
| **B2** | Woonplaatsen toggle in Kaartlagen-paneel | TC-01-003 Track B |
| **B3** | Kompas aggregeert op woonplaatsniveau | TC-01-003 Track B |
| **C1** | Benchmarktabel kernen naast elkaar | TC-02-001 stap 5 |
| **C2** | Gemeentegemiddelde SWF als referentielijn | TC-02-001 |
| **D1** | `HELP_ONBOARDING` beleidsadviseur-scenario | TC-06-001 fase 1 |
| **D2** | Startflow: hint tot eerste selectie | TC-01-001 |
| **E** | TC-06-001 volledig doorlopen + alle testcases bijwerken | TC-06-001 |
| **F** | G3 Info tooltip Top Uitschieters | Sprint 18 quickwin |

### Bewust buiten scope
- Bereikbaarheidsdata / OV-analyse (FRLDS fase 2)
- Openbare ruimte / groen (gemeentelijke BOR)
- Dataspace-integratie (Sprint 19-22)

**Status:** ✅ **Afgerond** — Dag 79 (30-06-2026). Alle tracks inclusief multi-gebied benchmark geïmplementeerd. Worktree gesynchroniseerd en opgeruimd.  
**Priority:** 🔴 HIGH (gebruikersvalidatie-fundament)  
**Effort:** 4 sessies gerealiseerd

---

## 💡 Braindump Kandidaten voor Toekomstige Sprints *(Dag 79 — 30-06-2026)*

> Ideeën vanuit de braindump die voldoende rijp zijn om in aanmerking te komen voor opname in een toekomstige sprint. Zie `braindump.md` voor de volledige uitwerking.

| Idee | Prioriteit | Kandidaat Sprint | Koppeling |
|------|-----------|------------------|-----------|
| **Lege indicatoren verbergen** in Kompas & Zoekfunctie | 🔴 HOOG | Sprint 19 of 20 | Beheer / UX — kleine technische ingreep, grote UX-winst |
| **Ontologieteksten genereren vanuit beheer** (op basis van metadata) | 🔴 HOOG | Sprint 20 | Uitbreiding van Sprint 18 Track A ontologie-validatielus |
| **Metadata ophalen bij de bron** vanuit admin panel | 🟡 MIDDEL | Sprint 20-21 | Koppeling met CBS OData / RIVM API, beheerder keurt diff goed |
| **Gebruikersprofielen met sessie-geheugen** | 🟡 MIDDEL | Sprint 21+ | Auth-uitbreiding: saved reports, zoekhistorie, AI-chat (30 dgn) |
| **Indicatorselectie via gebruikersvragen** in rapport | 🟡 MIDDEL | Sprint 21+ | Rapport-wizard + ontologie-tag mapping |
| **Correlatie-analyse via lokale AI** | 🟢 LAAG | Sprint 22+ | Pearson/Spearman backend + LLM-duiding, strict AI-disclaimer |
| **Data Virtualisatie & update-meldingen** | 🟢 LAAG | Sprint 22+ | Architectuurverkenning — If-Modified-Since + admin notificaties |
| **Slimmer gebruik 3D BAG** | 🟢 LAAG | Sprint 12 (heropenen) | Onderzoeksvraag: pand-niveau koppeling energielabel/bouwjaar |


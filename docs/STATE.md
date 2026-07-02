# STATE.md — D-OmniTwin Systeemstatus
> **Rol:** Single Source of Truth voor de huidige systeemstatus
> **Beheer:** Project-manager skill | Updaten na elke sprint, release of architectuurwijziging
> **Prioriteit:** Dit bestand is LEIDEND bij conflicten met andere documentatie

---

## 🔖 Versie & Release

| Veld | Waarde |
|------|--------|
| **Huidige versie** | v1.0.0-beta (pre-release) |
| **Sprint** | Sprint 18 — IJsselmeerkust als Besluitinstrument ✅ Afgerond | 
| **Laatste update** | 2026-07-02 (Dag 80) |
| **Bijgewerkt door** | Project-manager skill (Antigravity) |

---

## ✅ Actieve componenten

| Component | Status | Notitie |
|-----------|--------|---------|
| **FastAPI backend** | 🟢 Actief | `run_dev.py` draait, WSL/Ubuntu |
| **Mapbox + Deck.gl frontend** | 🟢 Actief | Classic Premium UI |
| **CBS buurt-data** | 🟢 Geïmporteerd | Fryslân 942 buurten (initiatie dataset) |
| **RIVM indicatoren** | 🟢 Actief | Meerdere jaren beschikbaar |
| **AI Chat Interface** | 🟢 Actief | HELP_ONBOARDING intent actief (deterministic, geen LLM) |
| **Help / Wiki Pagina** | 🟢 Actief | `/static/help.html` |
| **Externe Kaartlagen Beheer** | 🟢 Actief | BAG Woonplaatsen (WFS) & Lokale GPKG uploads (`data-upload/`) via admin panel |
| **3D BAG visualisatie** | 🟡 Beta | LoD 2.5D, Bug #42 open |
| **Admin Panel** | 🟢 Actief | Build via `/build-admin-panel` workflow |
| **Ontologie generatie** | 🟢 Actief | Fence & Source philosophy geïmplementeerd |
| **Multi-Gebiedsdossier rapport** | 🟢 Actief | Voltooid incl. bugfixes en colorblind-safe visualisatie |
| **Initiatie Dataset (init_data/)** | 🟢 Compleet | 942 Friese buurten, **235 indicatoren** (gesaneerd + nieuw formaat), scripts + GETTING_STARTED.md |
| **OV Haltes ETL (Issue #11)** | 🟢 Actief | FR/GR/DR: 6.945 nodes → 4.324 clusters → 961 buurten × 5 indicatoren (OV_HALTES_*) in `gebied_data`. Kompas: Bereikbaarheid en parkeren. |
| **Onboarding Modal + Contextuele Tooltips** | 🟢 Actief | Sprint 11B Track A ✅ — welkomstmodal, 4 contexttooltips, `window.EventBus` fix |
| **Error Toast Notificaties** | 🟢 Actief | Sprint 11B — `showError()` geüpgraded van `alert()` naar glassmorphism toast |
| **Feedback & Micro-interacties** | 🟢 Actief | Sprint 11B Track B ✅ — empty state, inline spinner, indicator badge, hover cursor |
| **Indicator Accordion + Zoekfunctie** | 🟢 Actief | Sprint 11B Track C ✅ — Kompas-thema groepering, debounce zoek, highlight |
| **Visualisatie WCAG & Outline Selectie** | 🟢 Actief | Sprint 11B Track D ✅ — goud outline, legenda hints, contrast fixes |
| **LLM Trust & Governance Laag** | 🟢 Actief | Sprint 11B Track E ✅ — bronlabel (rule-based/AI), disclaimer |
| **Kompas Data Ontologie UI** | 🟢 Actief | Sprint 18 ✅ — tabblad in detailpaneel met validatiestatus en oranje labels |
| **Viewport Vrije-Zone Centreren** | 🟢 Actief | Sprint 16 ✅ — `getFreezone()`, `flyToGebied()` offset, `fitBounds()` guard. Closes #8 |
| **Logging Infrastructuur** | 🟢 Actief | Sprint 17 ✅ — `AsyncLogQueue`, `app_logs` DB, log viewer admin panel, dagelijkse cleanup. E-mail alerts on hold (Issue #10) |
| **Time Slider** | 🔴 Gepland | Sprint 17+ — Indicator Historie & 3D Transities |
| **Data Lineage** | 🔴 Gepland | Sprint 8F — nog niet gestart |
| **Dataspace Orchestrator (inc. FRLDS)** | 🔵 Visie/Concept | Innovatiebudget 2026 |

---

## 🔄 Recente wijzigingen (laatste 3 sessies)

| Datum | Wijziging | Impact |
|-------|-----------|--------|
| 2026-07-02 | **Sprint 18 Track D Voltooid (Dag 80)** | Dynamische Profielen & Deterministische Scenario's (Showcase IJsselmeerkust) geïmplementeerd. Chatbot integratie met frontend (gebied selectie, kompas openen via chat acties). Unicodes/Variation selector bugs in JS Regex opgelost. |
| 2026-06-30 | **Sprint 18 Afgerond — Dag 79** | Multi-gebied benchmark (Track C) geïmplementeerd en getest. Alle sprint 18 code gesynchroniseerd naar `main` (worktree was op F-schijf gekoppeld). Bugfix: `gemeenten` API 500-error door ontbrekende `id`-kolom opgelost. `fiona` package toegevoegd aan requirements. Worktree `D-OmniTwin-sprint18` volledig opgeruimd (E én F schijf). |
| 2026-06-23 | **Omgeving & Git Herstel (Dag 78)** | `.venv` opgebouwd na schijfmigratie. Dependencies hersteld. `sentence-transformers` mandatory gemaakt. Git `.venv` symlink negeer-fout in `.gitignore` opgelost voor main én worktrees. |
| 2026-06-20 | **Sprint 18 Track A Voltooid (Dag 77)** | Ontologie UI, trendlijnen en bronvermeldingen geïmplementeerd. Bugfix AI chat (`KeyError 'uuid'`) wegens defecte `sympy` dependency in `.venv` opgelost. Git `pre-commit` hook toegevoegd om `.venv` map te beveiligen. |

---

## ⚠️ Bekende issues

| Issue | Ernst | Domein | Status |
|-------|-------|--------|--------|
| **E-mail alerts (Issue #10)** | Hoog | SecOps/Logging | 🔴 On hold — SMTP-server vereist. Must-have voor deelbare versie. Design: eigen server, configureerbaar via `.env`. |
| Data Lineage nog niet geïmplementeerd | Hoog | Data Engineering | Gepland Sprint 8F |
| Bug #42: 3D pand-kleuring bij single-buurt | Middel | Frontend | Open (Sprint 12) |
| Viewport edge case: Kompas gecentreerd + Chat open | Laag | Frontend | Gedocumenteerd in TODO.md Sprint 16. Workaround: Kompas verschuiven. |

---

## 🚨 Risico's

| Risico | Kans | Impact | Mitigatie |
|--------|------|--------|-----------|
| Sprint 11B introduceert UX-schuld in monolithische `app.js` | Middel | Hoog | Werkafspraak: nieuwe code als losse init-functies + EventBus (vastgelegd in plan) |
| Rootbestanden (README, TODO, ROADMAP) raken verouderd | Middel | Hoog | State.md als leidend document aanhouden |
| Skills werken zonder STATE.md-context | Middel | Middel | Standaard werkwijze nu in alle skills |
| Applicatie wordt gezien als verplicht product/SaaS | Middel | Hoog | Strikte positionering als open methodiek + referentie (EUPL) |
| FRLDS PoC vereist iSHARE-registratie vooraf | Hoog | Hoog | Vroeg starten met DataFryslân contact + IAMA |

---

## 🗺️ Roadmap focus (actief)

| **Sprint** | Focus | Verwacht |
|--------|-------|---------|
| **18** | IJsselmeerkust als Besluitinstrument — duiding, BAG woonplaatsen, benchmarking, Track F quickwins | ✅ Afgerond (Dag 79 — alle tracks incl. multi-gebied benchmark) |
| **19** | Van Data naar Inzicht — signalering, prioritering, contextuele scores, AI-samenvatting | 📌 Gepland (na Sprint 18) |
| **#11 (OV ETL)** | OV Haltes ETL — OSM data FR/GR/DR → Kompas indicatoren | ✅ Voltooid — merge `7443b51` |
| **17** | Configureerbare Logging Infrastructuur | ✅ Voltooid — merge `4ed45bd`, closes #9 (deels) |
| **17C e-mail** | E-mail alerts bij ERROR/CRITICAL | ⏳ On hold — Issue #10, wacht op SMTP |
| **12** | 3D BAG Integratie & Bug #42 | 🔜 Na Sprint 19 |
| **15** | Kompas UI Uitbreiding - Ontologie & Data Tabs | Na Sprint 12 |
| **13** | Architectuur Gaps & Security Hardening | Q2 2026 |
| **14** | Open Source Decoupling (EUPL) | Q2 2026 |
| **8F** | Data Lineage & Dataspace Orchestrator | Q3 2026 |
| **19-22** | Dataspace-Native Orchestration (FRLDS / FDS) | Q3/Q4 2026 |

---

## 🏗️ Architectuurprincipes (niet wijzigen zonder overleg)

- **docs/** = kennisdatabase (source of truth)
- **.agents/** = query engines (gedrag & orchestratie)
- **Positionering:** D-OmniTwin is een *open methodiek + referentie-implementatie* (EUPL licentie), geen commercieel SaaS platform of vendor-locked product.
- **Scheiding:** agents lezen docs, schrijven nooit vrij naar docs zonder expliciete instructie
- **Classic Premium UI** standaard bewaken bij alle frontend wijzigingen
- **EventBus** als enige communicatiekanaal tussen `app.js` en `kompas.js`

---

## 📋 Update-instructies voor project-manager

Na elke sprint of sessie, update minimaal:
1. `Versie & Release` tabel (datum + sprint)
2. `Actieve componenten` (status per component)
3. `Recente wijzigingen` (nieuwe regel toevoegen, oudste verwijderen)
4. `Bekende issues` (toevoegen/afsluiten)
5. `Roadmap focus` (sprint voortgang bijwerken)

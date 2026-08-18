# STATE.md — D-OmniTwin Systeemstatus
> **Rol:** Single Source of Truth voor de huidige systeemstatus
> **Beheer:** Project-manager skill | Updaten na elke sprint, release of architectuurwijziging
> **Prioriteit:** Dit bestand is LEIDEND bij conflicten met andere documentatie

---

## 🔖 Versie & Release

| Veld | Waarde |
|------|--------|
| **Huidige versie** | v1.0.0-beta (pre-release) |
| **Sprint** | Sprint 22 (Data Engineering & ETL Dataspace Track) |
| **Laatste update** | 2026-07-20 |
| **Bijgewerkt door** | Project-manager skill (Antigravity) |

---

## ✅ Actieve componenten

| Component | Status | Notitie |
|-----------|--------|---------|
| **API Gateway (Traefik)** | 🟢 Actief | Port 80, reverse proxy voor microservices |
| **Data API (PostgREST)** | 🟢 Actief | Port 3000, Dataspace compliant data endpoint |
| **Geo API (pg_featureserv)** | 🟢 Actief | Port 9000, OGC API Features endpoint |
| **FastAPI backend** | 🟢 Actief | Hybride AI/Rapportage logic, Port 8000 |
| **Docker Compose** | 🟢 Actief | Primary orchestration engine |
| **MapLibre + Deck.gl frontend** | 🟢 Actief | Classic Premium UI |
| **CBS buurt-data** | 🟢 Geïmporteerd | Fryslân 931 buurten |
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
| **Thema-Analyse Visualisatie** | 🟢 Actief | Sprint 19B / Track F ✅ — D3 Diverging Bar Chart en Boomstructuur Filter (Issue #15) |
| **Time Slider** | 🟢 Actief | Sprint 19 Migratie ✅ — Hybride TimeSlider, Indicator Historie & Play/Pauze |
| **Indicatoren Bron (Excel Jantina)** | 🟡 In Analyse | 812 indicatoren geïdentificeerd, 11 aanwezig (1,4% dekking). Stap 2 volgt. Bestand: `data/sociaaldomein/` |
| **ETL Dataspace Gap Analyse** | 🟢 Gedocumenteerd | `docs/3-data-engineering/etl_dataspace_gap_analyse.md` — D-OmniTwin als datamart-consumer van FRLDS |
| **Data Lineage** | 🔴 Gepland | Sprint 8F / 22 — nog niet gestart |
| **Dataspace Orchestrator (inc. FRLDS)** | 🔵 Visie/Concept | Innovatiebudget 2026. RFC issue klaargezet voor partners. |

---

## 🔄 Recente wijzigingen (laatste 3 sessies)

| Datum | Wijziging | Impact |
|-------|-----------|--------|
| 2026-07-20 | **Sprint 22 Data Engineering Track gestart** | ETL/Dataspace gap-analyse afgerond. D-OmniTwin hergepositioneerd als datamart-consumer (Gold laag). 812 indicatoren in Excel geïdentificeerd vs 11 aanwezig. Stap 1 (bronvergelijking) voltooid. |
| 2026-07-20 | **Sprint 21 Data Kwaliteit & Deduplicatie** | Deduplicatie pipeline voltooid: pg_trgm & pgvector matching, LLM validatie (AI Advies), en interactieve Admin UI met merge, groepeer en uitsluiting (uitzonderingen) acties via checkboxes. Issue #16 opgelost. |
| 2026-07-15 | **Sprint 23 Gepland / Issue 17 Voltooid** | Dynamische PDF/Print export layouts voor rapportages succesvol doorgevoerd. Sprint 23 (Backend Performance Optimalisatie) formeel op de ROADMAP en TODO geplaatst. |

---

## ⚠️ Bekende issues

| Issue | Ernst | Domein | Status |
|-------|-------|--------|--------|
| **Dashboard Backend (FastAPI)** | `routers/dashboard.py` | 🟢 Actief | Dashboards, statistieken & admin key auth. Auth scope gefixt voor admin panels via web UI cookies. |
| **Data Importer** | `admin-panel/src/pages/DataUpload.js`| 🟡 In Ontwikkeling | UI om CBS bestanden handmatig te uploaden en asynchroon te parsen (Voor Externe Kaartlagen is de upload al wel gerealiseerd via UI). |
| **Kaart & Kompas Rendering** | `static/js/app.js` & `kompas.js` | 🟢 Actief | Integratie van MultiPolygons voltooid. Dubbele geometrieën opgelost (`actief/inactief` db veld). |
| **E-mail alerts (Issue #10)** | Hoog | SecOps/Logging | 🔴 On hold — SMTP-server vereist. Must-have voor deelbare versie. |
| Bug #42: 3D pand-kleuring bij single-buurt | Middel | Frontend | Open (Sprint 12) |

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

| **22** | Data Engineering Track — ETL & Dataspace | 🔵 Actief — Stap 1 ✅ (bronvergelijking), Stap 2 volgt (metadata discovery per indicator) |
| **21** | Data Kwaliteit & Deduplicatie | ✅ Afgerond (UI checkboxes, AI matching, pg_trgm, uitzonderingen) |
| **18** | IJsselmeerkust als Besluitinstrument — duiding, BAG woonplaatsen, benchmarking, Track F quickwins | ✅ Afgerond (Dag 79 — alle tracks incl. multi-gebied benchmark) |
| **19** | Dataspace Architectuur Migratie — Docker, PostgREST, pg_featureserv, Traefik | ✅ Deels Afgerond (Fase 1, 2 en 4 voltooid) |
| **19B / Track F**| Van Data naar Inzicht (Issue #15) — Thema-Analyse, Boomstructuur Filter | ✅ Afgerond (Dag 86) |
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

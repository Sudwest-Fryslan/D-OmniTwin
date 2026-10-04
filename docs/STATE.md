# STATE.md — D-OmniTwin Systeemstatus (historisch)

> **Historisch document, niet leidend.** Dit is een momentopname van de systeemstatus tot en met de voorbereiding van release 0.1.0 (sprintperiode tot sprint 22). Het wordt niet meer bijgewerkt en klopt op een aantal punten niet meer: zo is PostgREST sinds 0.1.0 afgeschermd met eigen rollen (#57), staat de code sinds 0.2.0 in `src/omnitwin/` en `db/` (#182), en gebruikt de beheeromgeving alleen de sessie, geen API-key.
>
> De actuele stand staat in:
> - [`CHANGELOG.md`](../CHANGELOG.md): wat er per versie veranderd is; `[Unreleased]` is wat er op `main` staat;
> - [`VERSION`](../VERSION): het versienummer;
> - de [GitHub-issues](https://github.com/TLaan/D-OmniTwin/issues): wat openstaat;
> - de [installatiegids](9-beheer/installatie.md): installatie, beheer en beveiliging.

---

## 🔖 Versie & Release

| Veld | Waarde |
|------|--------|
| **Huidige versie** | 0.1.0 (eerste release in voorbereiding; bron: `VERSION`, zie [releasebeleid](9-beheer/releasebeleid.md)) |
| **Sprint** | Sprint 22 (Data Engineering & Lineage) ✅ Afgerond |
| **Volgende sprint** | Sprint 23 — De Gebruikers Sprint (Multi-Tenant Identity & Keycloak) 📌 Gepland |
| **Laatste update** | 2026-10-01 (Dag 101) |
| **Bijgewerkt door** | Antigravity (Project Manager) |

---

## ✅ Actieve componenten

| Component | Status | Notitie |
|-----------|--------|---------|
| **API Gateway (Traefik)** | 🟢 Actief | Port 80, reverse proxy voor microservices |
| **CI/CD Pipeline (GitHub Actions)** | 🟢 Actief | Issue #28 / PR #49 gemerged naar main — GitHub Actions workflow (`ci.yml`) met Python 3.11 en 3.12 unit-tests matrix, slanke `requirements-ci.txt`, `pyproject.toml` markers, 24 unit tests voor `KompasScoringService` en Docker build verificatie. |
| **Data API (PostgREST)** | 🟢 Actief | Port 3000, Dataspace compliant data endpoint |
| **Geo API (pg_featureserv)** | 🟢 Actief | Port 9000, OGC API Features endpoint |
| **FastAPI backend** | 🟢 Actief | Hybride AI/Rapportage logic, Port 8000 |
| **Docker Compose** | 🟢 Actief | Primary orchestration engine |
| **MapLibre + Deck.gl frontend** | 🟢 Actief | Classic Premium UI |
| **CBS buurt-data** | 🟢 Geïmporteerd | Fryslân 931 buurten |
| **RIVM indicatoren** | 🟢 Actief | Meerdere jaren beschikbaar |
| **AI Chat Interface** | 🟢 Actief | HELP_ONBOARDING intent actief (deterministic, geen LLM) |
| **Help / Wiki Pagina** | 🟢 Actief | `/static/help.html` |
| **Externe Kaartlagen Beheer & Rendering** | 🟢 Actief | Sprint 22 Track D ✅ — Standalone rendering (zonder CBS buurten), compacte UI, inline toelichting via ℹ️, scrollbegrenzing (max 5 items). PDOK WFS (Natura 2000, Bodemdaling, Monumenten, BAG Woonplaatsen). |
| **3D BAG visualisatie** | 🟢 Actief | LoD 0/1.2 via 3DBAG REST API (`api.3dbag.nl`), CityJSON decoding naar WGS84, Bug #56 gefixt (Issue #39). |
| **Admin Panel** | 🟢 Actief | Build via `/build-admin-panel` workflow |
| **Ontologie generatie** | 🟢 Actief | Fence & Source philosophy geïmplementeerd |
| **Woonplaats- & Deelgebiedsanalyse rapport** | 🟢 Actief | Issue #44 / PR #45 gemerged naar main — Gewogen stadsanalyse per thema op basis van inwoneraantallen, Top 10 uitschieters (aandachtspunten en kansen), geharmoniseerde kwadranttelling (totaal + sterke uitschieters), buurt-drilldown, ontologie en methodologische verantwoording. D3 Z-score afwijkingskaart met flexbox indeling (~48% breedte) en paarse contour. Endpoint POST `/api/report/deelgebied` & `/admin/rapport/deelgebied`. |
| **Multi-Gebiedsdossier rapport** | 🟢 Actief | Voltooid incl. bugfixes en colorblind-safe visualisatie |
| **Initiatie Dataset (init_data/)** | 🟢 Compleet | 942 Friese buurten, **235 indicatoren** (gesaneerd + nieuw formaat), scripts + GETTING_STARTED.md (nu in `docs/archief/`) |
| **Sample Dataset & Auto-init** | 🟢 Actief | Issue #52, #60 (PR #53, #80, #86) — 12 SWF-buurten, Bolsward-Zuidoost demodata, Frictionless datapakket (`datapackage.json`), container-entrypoint (`docker-entrypoint.sh init`). |
| **Integratietestsuite** | 🟢 Actief | Issue #62 (PR #70) — `tests/integration/test_sample_stack.py` toetst verse stack, 6 tests groen, 2 xfailed (#54/#57). |
| **Toegankelijkheid (WCAG 2.1 AA)** | 🟢 Actief | Issue #67 (PR #75) — Skiplink (`.skip-link`), toetsenbordfocus (`:focus-visible`), formulierenlabels en WCAG-contrast. |
| **Overheidsstandaarden** | 🟢 Actief | Issue #56, #61 (PR #76, #87) — `publiccode.yml`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md`, `docs/9-beheer/installatie.md`. |
| **Testcases & Use Cases** | 🟢 Gepubliceerd | Issue #64 (PR #77) — In [`docs/testcases/`](./testcases/) (TC-06-001, TC-06-003, NM-001, Gebruikersreview). |
| **OV Haltes ETL (Issue #11)** | 🟢 Actief | FR/GR/DR: 6.945 nodes → 4.324 clusters → 961 buurten × 5 indicatoren (OV_HALTES_*) in `gebied_data`. Kompas: Bereikbaarheid en parkeren. |
| **Onboarding Modal + Contextuele Tooltips** | 🟢 Actief | Sprint 11B Track A ✅ — welkomstmodal, 4 contexttooltips, `window.EventBus` fix |
| **Error Toast Notificaties** | 🟢 Actief | Sprint 11B — `showError()` geüpgraded van `alert()` naar glassmorphism toast |
| **Feedback & Micro-interacties** | 🟢 Actief | Sprint 11B Track B ✅ — empty state, inline spinner, indicator badge, hover cursor |
| **Indicator Accordion + Zoekfunctie** | 🟢 Actief | Sprint 11B Track C ✅ — Kompas-thema groepering, debounce zoek, highlight |
| **Visualisatie WCAG & Outline Selectie** | 🟢 Actief | Sprint 11B Track D ✅ — goud outline, legenda hints, contrast fixes |
| **LLM Trust & Governance Laag** | 🟢 Actief | Sprint 11B Track E ✅ — bronlabel (rule-based/AI), disclaimer |
| **Kompas Data Ontologie UI** | 🟢 Actief | Sprint 18 ✅ — tabblad in detailpaneel met validatiestatus en oranje labels |
| **Viewport Vrije-Zone Centreren** | 🟢 Actief | Sprint 16 ✅ — `getFreezone()`, `flyToGebied()` offset, `fitBounds()` guard. Closes #8 |
| **Logging Infrastructuur** | 🟢 Actief | Sprint 17 ✅ — `AsyncLogQueue`, `app_logs` DB, log viewer admin panel, dagelijkse cleanup. E-mail alerts on hold (Issue #47) |
| **Thema-Analyse Visualisatie** | 🟢 Actief | Sprint 19B / Track F ✅ — D3 Diverging Bar Chart en Boomstructuur Filter (Issue #15) |
| **Time Slider** | 🟢 Actief | Sprint 19 Migratie ✅ — Hybride TimeSlider, Indicator Historie & Play/Pauze |
| **Gebiedsagenda IJsselmeerkust Usecase** | 🟢 Gedocumenteerd | `docs/testcases/gebiedsagenda_ijselmeerkust/` — Spiegeling, TC-06-003 E2E testcase, 85% datadekking. |
| **Indicatoren Bron (Excel Jantina)** | ⏸️ Backlog | 812 indicatoren geparkeerd als Nice-to-Have (gebruikersonderzoek vereist). |
| **ETL Dataspace Gap Analyse** | 🟢 Gedocumenteerd | `docs/3-data-engineering/etl_dataspace_gap_analyse.md` — D-OmniTwin als datamart-consumer van FRLDS |
| **Data Lineage & Bronvermelding** | 🟢 Actief | Sprint 22 Track C ✅ Voltooid — 244 indicatoren (100%) voorzien van lineage, externe bronlinks en peildata. Spec: `docs/3-data-engineering/Data_Lineage_Bronvermelding_Spec.md` |
| **Dataspace Orchestrator (inc. FRLDS)** | 🔵 Visie/Concept | Innovatiebudget 2026. RFC issue klaargezet voor partners. |
| **Auth-laag (Keycloak BFF)** | 📌 Gepland Sprint 23 | Vervangt huidige sessie+API-key auth. Spec: `docs/5-secops/security/Keycloak_MultiTenant_RBAC_Spec.md` |
| **Multi-Tenancy Datamodel** | 📌 Gepland Sprint 23 | `organizations` tabel + `organization_id` FK op `indicatoren`, `externe_kaartlagen`, `kompas_configuraties`, `users`. PostgreSQL RLS als vanglaag. |
| **PostgREST beveiliging** | ⚠️ Open risico | Huidige setup volledig open via Traefik. Wordt gesloten in Sprint 23 via ForwardAuth middleware. |

---

## 🔄 Recente wijzigingen (laatste 3 sessies)

| 2026-10-01 | **Fundament vóór Publicatie & Overheidsstandaarden (#71)** | Grote consolidatie-release: 16 PR's gemerged. Sample dataset bootstrap (#52, PR #53), Frictionless datapakket (#60, PR #86), reproduceerbare integratietestsuite (#62, PR #70), WCAG 2.1 AA a11y (#67, PR #75), developer.overheid.nl standaarden (publiccode.yml, SECURITY, quickstart, #56/#61, PR #76), beheerinstallatiegids (#21, PR #87), Mapbox ontkoppeld (#55, PR #72), backend opschoning (#68, PR #73), PostGIS deelgebied functie (PR #85), en testcases & use cases gepubliceerd in docs/testcases/ (#64, PR #77). |
| 2026-09-25 | **CI/CD Pipeline & Unit Test Foundation (Issue #28)** | Eerste geautomatiseerde CI pipeline via GitHub Actions. Slanke `requirements-ci.txt`, `pyproject.toml` met testmarkers, 24/24 groene unit tests voor scoring logica zonder DB, en Docker build check. PR #49 gemerged naar main. |
| 2026-09-25 | **Consolidatie bugs en backlog naar GitHub Issues (Issue #24)** | Single Source of Truth geactiveerd. Bug #55 omgezet naar Issue #46, e-mail alerts verankerd in Issue #47. Bug #42 geverifieerd als reeds opgelost. PR #45 (Issue #44 Deelgebiedsrapport) gemerged naar main. |

---

## ⚠️ Bekende issues

| Issue | Ernst | Domein | Status |
|-------|-------|--------|--------|
| **Dashboard Backend (FastAPI)** | `routers/dashboard.py` | 🟢 Actief | Dashboards, statistieken & admin key auth. Auth scope gefixt voor admin panels via web UI cookies. |
| **Data Importer** | `admin-panel/src/pages/DataUpload.js`| 🟡 In Ontwikkeling | UI om CBS bestanden handmatig te uploaden en asynchroon te parsen (Voor Externe Kaartlagen is de upload al wel gerealiseerd via UI). |
| **Kaart & Kompas Rendering** | `static/js/app.js` & `kompas.js` | 🟢 Actief | Integratie van MultiPolygons voltooid. Dubbele geometrieën opgelost (`actief/inactief` db veld). |
| **E-mail alerts (Issue #47)** | Hoog | SecOps/Logging | 🔴 On hold — SMTP-server vereist. Must-have voor deelbare versie. |
| **Print-dialoog UI bevriezing (Issue #46)** | Middel | Frontend/UX | 🟡 Open — `window.open` met `noopener,noreferrer` isoleren. |
| **Skiplink browser-cache (Issue #106)** | Laag | Frontend/A11y | 🟢 Opgelost — Hard refresh lost styling op; skiplink netjes verborgen. |

---

## 🚨 Risico's

| Risico | Kans | Impact | Mitigatie |
|--------|------|--------|-----------|
| Sprint 11B introduceert UX-schuld in monolithische `app.js` | Middel | Hoog | Werkafspraak: nieuwe code als losse init-functies + EventBus (vastgelegd in plan) |
| Rootbestanden (README, TODO, ROADMAP) raken verouderd | Middel | Hoog | State.md als leidend document aanhouden |
| Skills werken zonder STATE.md-context | Middel | Middel | Standaard werkwijze nu in alle skills |
| Applicatie wordt gezien als verplicht product/SaaS | Middel | Hoog | Strikte positionering als open methodiek + referentie (EUPL) |
| FRLDS PoC vereist iSHARE-registratie vooraf | Hoog | Hoog | Vroeg starten met DataFryslân contact + IAMA |
| **PostgREST volledig open (beveiligingsgat)** | Hoog | Kritiek | ⚠️ Actief risico tot Sprint 23 — Traefik ForwardAuth + RLS sluiten dit af |
| **Multi-tenancy migratie breekt bestaande admin API-keys** | Middel | Hoog | Deprecatie-pad: `X-Admin-Key` blijft tijdelijk actief met `AUTH_DEPRECATED` log; ETL migreert naar Client Credentials |

---

## 🗺️ Roadmap focus (actief)

| **71** | Fundament vóór Publicatie & Overheidsstandaarden (#71) | ✅ Voltooid (Dag 101 — 16 PR's gemerged: sample stack #52/#60, integratietests #62, developer.overheid.nl #56/#61, WCAG 2.1 AA #67) |
| **23** | Multi-Tenant Identity, Keycloak & RBAC — De Gebruikers Sprint | 📌 Gepland — Spec klaar, ROADMAP + TODO bijgewerkt. Uitvoering start direct. |
| **28** | CI/CD Pipeline & Test Automatisering (GitHub Actions) | ✅ Fundament gerealiseerd (PR #49) — Unit tests (3.11/3.12) + Docker build check groen. |
| **22** | Data Engineering Track — Lineage & Bronvermelding | ✅ Afgerond — Track A, C, D ✅, Track B ⏸️ (Backlog / Gebruikersonderzoek) |
| **21** | Data Kwaliteit & Deduplicatie | ✅ Afgerond (UI checkboxes, AI matching, pg_trgm, uitzonderingen) |
| **18** | IJsselmeerkust als Besluitinstrument — duiding, BAG woonplaatsen, benchmarking, Track F quickwins | ✅ Afgerond (Dag 79 — alle tracks incl. multi-gebied benchmark) |
| **19** | Dataspace Architectuur Migratie — Docker, PostgREST, pg_featureserv, Traefik | ✅ Deels Afgerond (Fase 1, 2 en 4 voltooid) |
| **19B / Track F**| Van Data naar Inzicht (Issue #15) — Thema-Analyse, Boomstructuur Filter | ✅ Afgerond (Dag 86) |
| **17** | Configureerbare Logging Infrastructuur | ✅ Voltooid — merge `4ed45bd`, closes #9 (deels) |
| **17C e-mail** | E-mail alerts bij ERROR/CRITICAL | ⏳ On hold — Issue #10, wacht op SMTP |
| **12** | 3D BAG Integratie & Bug #42 | 🔜 Na Sprint 23 |
| **14** | Open Source Decoupling (EUPL) | Q3 2026 |
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

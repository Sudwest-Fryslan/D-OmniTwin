# STATE.md — D-OmniTwin Systeemstatus
> **Rol:** Single Source of Truth voor de huidige systeemstatus
> **Beheer:** Project-manager skill | Updaten na elke sprint, release of architectuurwijziging
> **Prioriteit:** Dit bestand is LEIDEND bij conflicten met andere documentatie

---

## 🔖 Versie & Release

| Veld | Waarde |
|------|--------|
| **Huidige versie** | v1.0.0-beta (pre-release) |
| **Sprint** | Sprint 22 (Data Engineering & Lineage) ✅ Afgerond |
| **Volgende sprint** | Sprint 23 — De Gebruikers Sprint (Multi-Tenant Identity & Keycloak) 📌 Gepland |
| **Laatste update** | 2026-08-26 |
| **Bijgewerkt door** | Antigravity |

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
| **Externe Kaartlagen Beheer & Rendering** | 🟢 Actief | Sprint 22 Track D ✅ — Standalone rendering (zonder CBS buurten), compacte UI, inline toelichting via ℹ️, scrollbegrenzing (max 5 items). PDOK WFS (Natura 2000, Bodemdaling, Monumenten, BAG Woonplaatsen). |
| **3D BAG visualisatie** | 🟢 Actief | LoD 0/1.2 via 3DBAG REST API (`api.3dbag.nl`), CityJSON decoding naar WGS84, Bug #56 gefixt (Issue #39). |
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
| **Gebiedsagenda IJsselmeerkust Usecase** | 🟢 Gedocumenteerd | `docs/7-projectmanagement/testcases/gebiedsagenda_ijselmeerkust/` — Spiegeling, TC-06-003 E2E testcase, 85% datadekking. |
| **Indicatoren Bron (Excel Jantina)** | ⏸️ Backlog | 812 indicatoren geparkeerd als Nice-to-Have (gebruikersonderzoek vereist). |
| **ETL Dataspace Gap Analyse** | 🟢 Gedocumenteerd | `docs/3-data-engineering/etl_dataspace_gap_analyse.md` — D-OmniTwin als datamart-consumer van FRLDS |
| **Data Lineage & Bronvermelding** | 🟢 Actief | Sprint 22 Track C ✅ Voltooid — 244 indicatoren (100%) voorzien van lineage, externe bronlinks en peildata. Spec: `docs/3-data-engineering/Data_Lineage_Bronvermelding_Spec.md` |
| **Dataspace Orchestrator (inc. FRLDS)** | 🔵 Visie/Concept | Innovatiebudget 2026. RFC issue klaargezet voor partners. |
| **Auth-laag (Keycloak BFF)** | 📌 Gepland Sprint 23 | Vervangt huidige sessie+API-key auth. Spec: `docs/5-secops/security/Keycloak_MultiTenant_RBAC_Spec.md` |
| **Multi-Tenancy Datamodel** | 📌 Gepland Sprint 23 | `organizations` tabel + `organization_id` FK op `indicatoren`, `externe_kaartlagen`, `kompas_configuraties`, `users`. PostgreSQL RLS als vanglaag. |
| **PostgREST beveiliging** | ⚠️ Open risico | Huidige setup volledig open via Traefik. Wordt gesloten in Sprint 23 via ForwardAuth middleware. |

---

## 🔄 Recente wijzigingen (laatste 3 sessies)

| 2026-08-27 | **3D BAG Panden Migratie naar REST API (Issue #39 / Bug #56)** | Kapotte WFS van TU Delft (`data.3dbag.nl`) vervangen door de officiële 3DBAG REST API (`api.3dbag.nl`). CityJSON geometry decoder ingebouwd (RD New → WGS84 polygonen via `pyproj`), paginering via `links.next` en graceful 503 error handling. |
| 2026-08-26 | **Docker Uitlevering & CI/CD Pipeline Documentatie (Issues #27 & #28)** | Twee complementaire gidsen opgesteld in `docs/9-beheer/`: (1) `stappenplan_docker_installatie_externe_organisatie.md` voor Docker restore via DB-dump op externe servers, en (2) `cicd_pipeline_docker_hub.md` voor GitHub Actions → Docker Hub uitlevering (SemVer, testmethodiek, productie compose). GitHub API live gekoppeld. |
| 2026-08-26 | **Systeemarchitectuur & Implementatiegids voor ICT & Informatieadvies** | Opgesteld in `docs/2-architectuur/architecture/systeemarchitectuur_en_implementatiegids_ict.md`. Bevat ASCII box-drawing diagrammen van de containerstack, Entra ID / Keycloak SSO identiteitsflow en de gemeentelijke Docker hostinginrichting. |
| 2026-08-21 | **Sprint 23 planning: Multi-Tenant Identity & Keycloak** | Sprint 23 herdefinieert van Backend Performance naar De Gebruikers Sprint. Volledig architectuur- en implementatieplan opgesteld: Keycloak als Identity Broker, 4-niveaus RBAC, BFF-patroon, PostgreSQL RLS, Entra ID Admin Consent flow, PostgREST beveiliging. Spec: `docs/5-secops/security/Keycloak_MultiTenant_RBAC_Spec.md`. ROADMAP.md en TODO.md bijgewerkt. |

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
| **PostgREST volledig open (beveiligingsgat)** | Hoog | Kritiek | ⚠️ Actief risico tot Sprint 23 — Traefik ForwardAuth + RLS sluiten dit af |
| **Multi-tenancy migratie breekt bestaande admin API-keys** | Middel | Hoog | Deprecatie-pad: `X-Admin-Key` blijft tijdelijk actief met `AUTH_DEPRECATED` log; ETL migreert naar Client Credentials |

---

## 🗺️ Roadmap focus (actief)

| **23** | Multi-Tenant Identity, Keycloak & RBAC — De Gebruikers Sprint | 📌 Gepland — Spec klaar, ROADMAP + TODO bijgewerkt. Uitvoering start direct. |
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

# STATE.md — D-OmniTwin Systeemstatus
> **Rol:** Single Source of Truth voor de huidige systeemstatus
> **Beheer:** Project-manager skill | Updaten na elke sprint, release of architectuurwijziging
> **Prioriteit:** Dit bestand is LEIDEND bij conflicten met andere documentatie

---

## 🔖 Versie & Release

| Veld | Waarde |
|------|--------|
| **Huidige versie** | v0.9.x (pre-release) |
| **Sprint** | Sprint 11B — UX-Overhaul (gepland, branch aanmaken) |
| **Laatste update** | 2026-05-14 (Dag 60) |
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
| **Omgevingsvisie Selectielaag** | 🟢 Actief | 6 deelgebieden SWF, klik-selectie CBS-buurten via -10m buffer |
| **3D BAG visualisatie** | 🟡 Beta | LoD 2.5D, Bug #42 open |
| **Admin Panel** | 🟢 Actief | Build via `/build-admin-panel` workflow |
| **Ontologie generatie** | 🟢 Actief | Fence & Source philosophy geïmplementeerd |
| **Multi-Gebiedsdossier rapport** | 🟢 Actief | Voltooid incl. bugfixes en colorblind-safe visualisatie |
| **Initiatie Dataset (init_data/)** | 🟢 Compleet | 942 Friese buurten, **235 indicatoren** (gesaneerd + nieuw formaat), scripts + GETTING_STARTED.md |
| **Onboarding Modal + Contextuele Tooltips** | 🟡 Gepland | Sprint 11B Track A — feature branch aanmaken |
| **Indicator Accordion + Zoekfunctie** | 🟡 Gepland | Sprint 11B Track C — eerste stap formele taxonomie |
| **LLM Trust & Governance Laag** | 🟡 Gepland | Sprint 11B Track E — disclaimer + rule-based interpretatie |
| **Kompas Data Ontologie UI** | 🔴 Gepland | Sprint 15 — tabblad in detailpaneel |
| **Time Slider** | 🔴 Gepland | Sprint 16 — Indicator Historie & 3D Transities |
| **Data Lineage** | 🔴 Gepland | Sprint 8F — nog niet gestart |
| **Dataspace Orchestrator (inc. FRLDS)** | 🔵 Visie/Concept | Innovatiebudget 2026 |

---

## 🔄 Recente wijzigingen (laatste 3 sessies)

| Datum | Wijziging | Impact |
|-------|-----------|--------|
| 2026-05-14 | **Sprint 11B UX-Overhaul Plan (Dag 60)** | Volledig implementatieplan opgesteld op basis van UX-review, extern advies en second opinion. Plan omvat 5 tracks (A–E): onboarding, feedback, indicatornavigatie, kleurconsistentie en LLM-governance. Designfilosofie vastgelegd. UX-documenten toegevoegd aan `docs/4-ux-design/visual/`. GitHub issue + branch staan klaar om aangemaakt te worden. |
| 2026-04-22 | **Schema Sync & Setup Wizard (Dag 59)** | `schema_latest.sql` is nu 1-op-1 met de live database (toevoeging van `visualisatie_profielen` en extra kolommen in `indicatoren` en `color_schemas`). `setup_env.py` wizard toegevoegd. Python 3.10 eisen aangescherpt en pdok download script toegevoegd voor buurten. 33 visualisatie_profielen als seed geplaatst. |
| 2026-04-20 | **Indicatoren Consolidatie (Dag 58)** | Database gesaneerd 275→235 indicatoren: 29 wees-records verwijderd, 6 naam-duplicaten gemerged (53.000+ datapunten behouden), 7 indicatoren aan Kompas gekoppeld. `indicatoren_seed.json` vernieuwd (61→235, nieuw formaat). Download-script namen gesynchroniseerd. Commit `1dbd700` gepusht. |

---

## ⚠️ Bekende issues

| Issue | Ernst | Domein | Status |
|-------|-------|--------|--------|
| Data Lineage nog niet geïmplementeerd | Hoog | Data Engineering | Gepland Sprint 8F |
| Bug #42: 3D pand-kleuring bij single-buurt | Middel | Frontend | Open (Sprint 12) |
| TODO.md heeft overlap met ROADMAP.md | Laag | Projectmanagement | Bekend, niet urgent |

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

| Sprint | Focus | Verwacht |
|--------|-------|---------|
| **11 Track A** | Chat Onboarding (HELP_ONBOARDING) | ✅ Geïmplementeerd |
| **Dag 59** | Initiatie Workflow & Schema Sync | ✅ Voltooid — commit `a8166c4` gepusht |
| **11B (huidig)** | UX-Overhaul — Tracks A t/m E | 🟡 Plan klaar — GitHub issue + branch aanmaken |
| **Jouw actie** | CBS indicatorwaarden downloaden op laptop | ⏳ Nog uit te voeren |
| **12** | 3D BAG Integratie & Bug #42 | Geparkeerd — na Sprint 11B |
| **15** | Kompas UI Uitbreiding - Ontologie & Data Tabs + Taxonomie verdieping | Na Sprint 11B |
| **16** | Time Traveler - Indicator Historie en 3D transities | Q3 2026 |
| **13** | Architectuur Gaps & Security Hardening | Q2 2026 |
| **14** | Open Source Decoupling (EUPL) | Q2 2026 |
| **8F** | Data Lineage & Dataspace Orchestrator | Q3 2026 |
| **17-20** | Dataspace-Native Orchestration (FRLDS / FDS) | Q3/Q4 2026 |

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

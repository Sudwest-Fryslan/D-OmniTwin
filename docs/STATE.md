# STATE.md — D-OmniTwin Systeemstatus
> **Rol:** Single Source of Truth voor de huidige systeemstatus
> **Beheer:** Project-manager skill | Updaten na elke sprint, release of architectuurwijziging
> **Prioriteit:** Dit bestand is LEIDEND bij conflicten met andere documentatie

---

## 🔖 Versie & Release

| Veld | Waarde |
|------|--------|
| **Huidige versie** | v0.9.x (pre-release) |
| **Sprint** | Dag 58 — Initiatie Dataset & Getting Started documentatie |
| **Laatste update** | 2026-04-13 (Dag 58) |
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
| **Initiatie Dataset (init_data/)** | 🟢 Nieuw | 942 Friese buurten, 61 indicatoren, scripts + GETTING_STARTED.md |
| **Kompas Data Ontologie UI** | 🔴 Gepland | Sprint 15 — tabblad in detailpaneel |
| **Time Slider** | 🔴 Gepland | Sprint 16 — Indicator Historie & 3D Transities |
| **Data Lineage** | 🔴 Gepland | Sprint 8F — nog niet gestart |
| **Dataspace Orchestrator (inc. FRLDS)** | 🔵 Visie/Concept | Innovatiebudget 2026 |

---

## 🔄 Recente wijzigingen (laatste 3 sessies)

| Datum | Wijziging | Impact |
|-------|-----------|--------|
| 2026-04-13 | **Initiatie Dataset + Getting Started** | `init_data/` toegevoegd (publiek, in git): 942 Friese buurten GeoJSON, 61 indicatoren seed, Kompas CSV, schema snapshot, 4 scripts, GETTING_STARTED.md. README.md Quick Start herzien. Commit `547cbf8` gepusht naar main. |
| 2026-04-11 | **Git Repository Initiatie** | Base project v0.9.x opgeschoond (security/secrets verwijderd, `.gitignore` gefilterd) en gepusht naar private GitHub (`main` branch). |
| 2026-04-12 | **Multi-Gebiedsdossier Uitbreiding (Dag 57)** | Themafilter, top-3 uitschieters, geneste tabel, Lucide iconen, bugfix #44 case-mismatch. |

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
| Rootbestanden (README, TODO, ROADMAP) raken verouderd | Middel | Hoog | State.md als leidend document aanhouden |
| Skills werken zonder STATE.md-context | Middel | Middel | Standaard werkwijze nu in alle skills |
| Applicatie wordt gezien als verplicht product/SaaS | Middel | Hoog | Strikte positionering als open methodiek + referentie (EUPL) |
| FRLDS PoC vereist iSHARE-registratie vooraf | Hoog | Hoog | Vroeg starten met DataFryslân contact + IAMA |

---

## 🗺️ Roadmap focus (actief)

| Sprint | Focus | Verwacht |
|--------|-------|---------|
| **11 Track A** | Chat Onboarding (HELP_ONBOARDING) | ✅ Geïmplementeerd |
| **Dag 58 (vandaag)** | Initiatie Dataset & Getting Started | ✅ Voltooid — gepusht naar main |
| **Jouw actie** | CBS indicatorwaarden downloaden op laptop | ⏳ Nog uit te voeren |
| **12 (huidig)** | 3D BAG Integratie & Bug #42 | Volgende sessie |
| **15** | Kompas UI Uitbreiding - Ontologie & Data Tabs | Volgende Sessie |
| **16** | Time Traveler - Indicator Historie en 3D transities | Volgende Sessie |
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

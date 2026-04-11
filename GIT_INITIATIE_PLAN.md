# 🗂️ D-OmniTwin — Git Initiatie Plan
> **Aangemaakt:** 2026-04-11 | **Skill:** Samenwerking & Adoptie Communicatie-Assistent
> **Repository:** `https://github.com/TLaan/D-OmniTwin.git` (Private)
> **Status:** `.gitignore` geconfigureerd ✅ | `git init` uitgevoerd ✅ | Remote nog niet gekoppeld

---

## 📦 Map- en Grootteoverzicht

Hieronder een overzicht van alle mappen en bestanden, inclusief grootte en of ze op Git worden gezet (of juist uitgesloten via `.gitignore`).

> **Totale projectgrootte (lokaal):** ~31 GB
> **Verwachte repository-grootte (na uitsluiting):** ~10–15 MB

### 🔴 Uitgesloten via `.gitignore` (komen NIET op Git)

| Map / Bestand | Grootte | Reden uitsluiting |
|---|---|---|
| `data/` | **22 GB** | Grote datasets (CBS, RIVM, BAG, GeoJSON, PostGIS exports) |
| `.venv/` | **7.9 GB** | Python virtual environment — platform-specifiek |
| `admin-panel/node_modules/` | **~580 MB** | NPM packages — via `admin-panel/.gitignore` |
| `admin-panel/build/` | **< 10 MB** | React build-output — via `admin-panel/.gitignore` |
| `.agents/` | **56 KB** | Intern AI-werkgeheugen (skills, workflows) — niet publiek |
| `exports/` | **92 KB** | Gegenereerde rapporten (JSON, Excel) — geen broncode |
| `.env` | **< 4 KB** | ⚠️ GEHEIMEN: wachtwoorden, API keys, tokens |
| `config.ini` | **< 4 KB** | Lokale configuratie — machine-specifiek |
| `__pycache__/` | **12 KB** | Python bytecode — automatisch gegenereerd |
| `docs/4-ux-design/` | (< 2.7 MB totaal docs) | Interne UX documentatie |
| `docs/5-secops/` | (< 2.7 MB totaal docs) | Beveiligingsoperaties — intern |
| `docs/6-ai-parallel-track/` | (< 2.7 MB totaal docs) | AI-ontwikkeltraject — intern |
| `docs/7-projectmanagement/` | (< 2.7 MB totaal docs) | Dagboek, sprints, sessielogboeken |
| `obsolete/` | **36 KB** | Verouderde bestanden (inhoud uitgesloten, map bewaard) |
| `*.log` / `logs/` | **0 KB** | Log-bestanden (nu leeg, preventief uitgesloten) |

### ✅ Worden WEL op Git gezet

| Map / Bestand | Grootte | Doel |
|---|---|---|
| `static/` | **5.3 MB** | Frontend assets: JS, CSS, images, admin-panel build |
| `docs/1-visie-concept/` | **< 2.7 MB** | Openbare methodiek (EUPL-licentieerbaar) |
| `docs/2-architectuur/` | **< 2.7 MB** | Technische referentiearchitectuur |
| `docs/3-data-engineering/` | **< 2.7 MB** | Open ETL-aanpak |
| `docs/8-communicatie/` | **< 2.7 MB** | Externe communicatie & adoptie |
| `docs/INDEX.md` | **< 5 KB** | Documentatienavigatie |
| `docs/STATE.md` | **< 6 KB** | Systeemstatus |
| `routers/` | **320 KB** | FastAPI route-handlers |
| `services/` | **244 KB** | Business logica & services |
| `scripts/` | **172 KB** | ETL-scripts, importtools |
| `ETL/` | **624 KB** | Extract-Transform-Load modules |
| `templates/` | **40 KB** | HTML Jinja2 templates |
| `schemas/` | **36 KB** | Pydantic schemas |
| `src/` | **16 KB** | Hulpmodules |
| `migrations/` | **8 KB** | Database migraties |
| `admin-panel/src/` | **< 589 MB** | React/TypeScript broncode (node_modules uitgesloten) |
| `admin-panel/package.json` | **< 4 KB** | NPM dependencies lijst |
| `admin-panel/tsconfig.json` | **< 4 KB** | TypeScript configuratie |
| `main.py` | **< 10 KB** | FastAPI applicatie entrypoint |
| `run_dev.py` | **< 4 KB** | Development server script |
| `requirements.txt` | **< 4 KB** | Python dependencies |
| `.env.example` | **< 4 KB** | ✅ Configuratie-template (geen secrets) |
| `.gitignore` | **< 4 KB** | Git uitsluitingsregels |
| `README.md` | **35 KB** | Project documentatie |
| `ROADMAP.md` | **33 KB** | Lange-termijn planning |
| `LICENSE` | **13 KB** | EUPL 1.2 licentie |
| `LICENSE-DOCS` | **12 KB** | CC BY 4.0 licentie |
| `NOTICE.md` | **< 4 KB** | Third-party licenties |
| `test_canvas.py` | **< 4 KB** | Test script (overleggen of uitsluiten) |
| `test_zscore.py` | **< 4 KB** | Test script (overleggen of uitsluiten) |

---

## ✅ Voortgang Checklist

### Fase 1 — Voorbereiding (AFGEROND)

- [x] `.gitignore` gecontroleerd op basisregels (Python, IDE, OS)
- [x] `.gitignore` uitgebreid: `exports/`, `*.log`, `logs/`
- [x] `.gitignore` uitgebreid: `.agents/`
- [x] `.gitignore` uitgebreid: `data/` (volledig, was `data/*`)
- [x] `.gitignore` uitgebreid: `docs/4-7` (interne projectmappen)
- [x] `.env.example` aangemaakt met alle sleutels (zonder echte waarden)
- [x] `exports/.gitkeep` aangemaakt
- [x] `git init` uitgevoerd
- [x] Security check gedraaid — `.env`, `data/`, `exports/` worden correct uitgesloten
- [x] GitHub repository aangemaakt: `https://github.com/TLaan/D-OmniTwin.git`

### Fase 2 — Initiële Commit (VOLGENDE STAP)

- [ ] **Remote instellen:**
  ```bash
  git remote add origin https://github.com/TLaan/D-OmniTwin.git
  git branch -M main
  ```

- [ ] **Staging inspecteren** (definitieve veiligheidscheck vóór commit):
  ```bash
  git status --short
  ```
  > ⚠️ Controleer de output: `.env`, `data/`, `.agents/`, `.venv/` mogen NIET in de lijst staan.

- [ ] **Eerste commit:**
  ```bash
  git add .
  git commit -m "feat: initial commit - D-OmniTwin base project"
  ```

- [ ] **Push naar GitHub:**
  ```bash
  git push -u origin main
  ```
  > ⚠️ Vereist authenticatie via GitHub PAT (Personal Access Token) of SSH-sleutel.
  > Genereer een PAT via: GitHub → Settings → Developer Settings → Personal Access Tokens → Fine-grained tokens

### Fase 3 — Na Eerste Push (TODO)

- [ ] GitHub repository beschrijving instellen (~350 tekens — zie eerder gegenereerde opties)
- [ ] GitHub repository topics toevoegen: `digital-twin`, `fastapi`, `deck-gl`, `eupl`, `open-data`, `smart-city`
- [ ] `README.md` controleren op verwijzingen naar `<repo-url>` (bijwerken naar de echte URL)
- [ ] Beslissen over `test_canvas.py` / `test_zscore.py` in root (verplaatsen naar `tests/` of uitsluiten)
- [ ] Besluiten of `BRAINDUMP.md` / `BUGFIX.md` op Git thuishoren (nu wel opgenomen)
- [ ] Eerste `.gitignore`-commit taggen als versionering-startpunt

---

## ⚠️ Openstaande Beslispunten

| # | Vraag | Advies |
|---|---|---|
| 1 | `test_canvas.py` / `test_zscore.py` in root | ✅ Opgelost — verplaatst naar `tests/` |
| 2 | `BRAINDUMP.md` (49 KB) op Git? | ✅ Opgelost — toegevoegd aan `.gitignore` |
| 3 | `BUGFIX.md` (46 KB) op Git? | Nuttig als openbaar changelog, prima om te bewaren |
| 4 | GitHub authenticatie via HTTPS of SSH? | SSH is veiliger voor dagelijks gebruik |
| 5 | `docs/8-communicatie/` op Git? | Staat momenteel WEL op Git — akkoord? |

---

## 🔐 Security Samenvatting

| Geheim | Uitgesloten? | Waar geregeld |
|---|---|---|
| Database wachtwoord | ✅ Ja | `.gitignore` → `.env` |
| Mapbox API Token | ✅ Ja | `.gitignore` → `.env` |
| Admin API Key | ✅ Ja | `.gitignore` → `.env` |
| Secret Key (JWT) | ✅ Ja | `.gitignore` → `.env` |
| Template aanwezig | ✅ Ja | `.env.example` op Git |

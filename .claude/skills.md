# Skills

Wat ik kan en hoe ik het aanpak per domein in dit project.

## Backend (Python/FastAPI)
Routers zijn dun. Logica zit in services. Ik wijzig zo min mogelijk en gebruik bestaande naamgeving.
Aandacht voor: Z-score referentiegroepen, kleur-inversielogica, lazy-loaded AI services.

## Database (PostgreSQL/PostGIS)
SQL schrijf ik direct en toetsbaar. Geen alias waarbij de tabelnaam niet herkenbaar terugkomt.
Aandacht voor: pgvector, GeoAlchemy2, views als `vw_gebied_kaart_basis`, water-buurt filtering.

## Frontend (Vanilla JS)
Communicatie via EventBus, state via `window.state`. Geen frameworks.
Aandacht voor: `app.js`, `kompas.js`, `chat.js` zijn grote bestanden, wijzig gericht.

## Admin UI (React/TypeScript)
Aparte codebase in `admin-panel/`. Eigen build-stap nodig.
API calls via relatieve paden, proxied naar backend op poort 8000.

## Data-engineering (ETL)
Scripts in `ETL/` en `scripts/` zijn standalone. Niet deel van de web-API.
CBS, RIVM, BAG als primaire bronnen.

## AI/LLM
Ollama lokaal (Qwen). LLM-config en system-prompts staan in de database, niet hardcoded.
Chat is rule-based intent-classificatie, LLM alleen voor narratieven (max 80 woorden).

## GitHub workflow
Altijd: issue → branch (`feature/<nr>-<naam>`) → commits → PR naar main.
gh CLI staat op: `"/c/Program Files/GitHub CLI/gh.exe"`

## Projectmanagement
STATE.md is leidend. Na elke sprint bijwerken: versie, actieve componenten, recente wijzigingen, issues, roadmap.
In observatiemodus: alleen memory bijhouden, geen projectbestanden aanpassen.

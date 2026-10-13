# D-OmniTwin Beheer (admin-panel)

React 19 + TypeScript, gebouwd met [Vite](https://vite.dev/). De web-container (nginx, `web.Dockerfile`, #408) serveert de build onder `/admin/` vanuit `static/admin-panel/` (zie `deploy/web/default.conf`).

## Scripts

| Commando | Wat |
|---|---|
| `npm start` / `npm run dev` | Vite dev server op http://localhost:3000/admin/; `/api` gaat via de proxy naar http://localhost:8000 |
| `npm run build` | productiebuild naar `build/` (zonder sourcemaps) |
| `npm run build:static` | build + kopie naar `../static/admin-panel/` (die map wordt meegecommit) |
| `npm run typecheck` | `tsc --noEmit` |
| `npm test` | Vitest, eenmalig |
| `npm run lint` | ESLint (React-hookregels) |

## Omgevingsvariabelen

Geen. De beheeromgeving werkt alleen met de sessie-cookie: log in als gebruiker met `is_admin`. De `X-Admin-Key`-header is voor scripts. Zet nooit secrets in `VITE_*`-variabelen: Vite bakt die in de bundle.

// Kopieert de Vite-build (admin-panel/build) naar static/admin-panel,
// waar FastAPI de beheeromgeving onder /admin/ serveert (zie main.py).
import { cpSync, existsSync, rmSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, '..', 'build');
const dest = resolve(here, '..', '..', 'static', 'admin-panel');

if (!existsSync(resolve(src, 'index.html'))) {
  console.error(`Geen build gevonden in ${src}; draai eerst 'npm run build'.`);
  process.exit(1);
}

rmSync(dest, { recursive: true, force: true });
cpSync(src, dest, { recursive: true });
console.log(`Build gekopieerd: ${src} -> ${dest}`);

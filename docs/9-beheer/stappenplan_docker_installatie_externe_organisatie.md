# 🚀 Stappenplan: Docker Installatie & Database Restore (Externe Organisatie)

> ⚠️ **Verouderd/aanvullend** — de actuele installatie staat in [`installatie.md`](./installatie.md) (nieuwe installatie, backup/restore, bijwerken, beveiliging). Dit stappenplan beschrijft alleen het aanvullende scenario: een complete database van een bronomgeving via een dump overzetten. Aantallen, versies en de status "Productie-gereed" hieronder zijn niet bijgewerkt.

> **Documenttype:** Technische Installatie- en Migratiehandleiding  
> **Doelgroep:** Technisch Applicatiebeheerders, DevOps Engineers, ICT-Systeembeheerders & Implementatieconsultants  
> **Status:** Actueel / Productie-gereed  
> **Licentie & Openheid:** EUPL 1.2 (Open Source Software) | CC BY 4.0 (Open Methodiek)

---

## 1. 🎯 Doelstelling & Uitgangspunten

Deze handleiding beschrijft de exacte, stapsgewijze procedure voor het installeren en in gebruik nemen van de **D-OmniTwin Docker containerstack** op de serverinfrastructuur van een externe organisatie (bijvoorbeeld een gemeente, provincie, veiligheidsregio of waterschap).

### 🔑 Kernuitgangspunt: Installatie via Database Dump
In plaats van een lege database op de doellocatie te seeden via live API-downloads (zoals CBS OData en PDOK WFS), maken we gebruik van een vooraf gegenereerd **Database Dumpbestand** (`.dump` of `.sql.gz`). 

**Voordelen van deze methode:**
1. **100% Reproduceerbaar & Consistent:** De doelorganisatie start direct met exact dezelfde 244 gevalideerde indicatoren, complete data-lineage, historische tijdreeksen (2020–2025), ruimtelijke geometrieën en Kompas-hiërarchie.
2. **Geen Externe API-Afhankelijkheden tijdens Setup:** Geen risico op falende installaties door CBS API-storingen, rate-limits of trage downloads.
3. **Snelle Implementatietijd:** Het inlezen van een dump duurt slechts enkele seconden tot minuten.

---

## 2. 🏛️ Architectuur & Containeroverzicht

De D-OmniTwin stack draait als een geïsoleerd cluster van 5 microservices binnen Docker Compose:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  DOCKER HOST SERVER (Externe Organisatie)                                              │
│                                                                                        │
│   Inkomend verkeer: Poort 80 (HTTP) of 443 (HTTPS via Proxy/WAF)                       │
│           │                                                                            │
│           ▼                                                                            │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ [traefik] Reverse Proxy & API Gateway (service: traefik, poort 80)             │   │
│   └──────┬───────────────────────────┬───────────────────────────┬─────────────────┘   │
│          │ / (Webapp) & /api/*       │ /api/data/*               │ /api/geo/*          │
│          ▼                           ▼                           ▼                     │
│   ┌────────────────────────┐  ┌──────────────┐          ┌──────────────────┐           │
│   │ [backend]              │  │ [postgrest]  │          │ [pg_featureserv] │           │
│   │ FastAPI (Poort 8000)   │  │ Data API     │          │ Geo API          │           │
│   │ BFF & Rapportages      │  │ (Poort 3000) │          │ (Poort 9000)     │           │
│   └──────────┬─────────────┘  └──────┬───────┘          └────────┬─────────┘           │
│              │                       │                           │                     │
│              └───────────────────────┼───────────────────────────┘                     │
│                                      ▼                                                 │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ [postgres] PostgreSQL 15 + PostGIS 3.4 + pgvector (alleen intern, poort 5432)  │   │
│   │ ↳ Persistent Docker Volume: pgdata                                             │   │
│   └────────────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

| Service | Compose-service | Interne Poort | Doel & Functionaliteit |
|---|---|---|---|
| **Traefik** | `traefik` | `80` | Reverse proxy, dynamic path routing, centrale toegangspoort |
| **Backend** | `backend` | `8000` | FastAPI applicatie, HTML UI, rapportagemotor, REST BFF |
| **PostgreSQL** | `postgres` | `5432` *(niet op de host)* | PostGIS ruimtelijke database, indicatorenhuis, pgvector embeddings |
| **PostgREST** | `postgrest` | `3000` | Gestandaardiseerde REST API over PostgreSQL tabellen/views |
| **pg_featureserv** | `pg_featureserv` | `9000` | OGC API Features endpoint voor snelle streaming van vector GeoJSON |

---

## 3. 📋 Overzicht van het Stappenplan

| Fase | Onderdeel | Verantwoordelijke | Locatie |
|---|---|---|---|
| **Fase 0** | [Release & Database Dump Voorbereiden](#fase-0--voorbereiding-op-de-bronomgeving) | Lead Developer / Beheerder | Ontwikkel-/Bronomgeving |
| **Fase 1** | [Doelserver & Vereisten Controleren](#fase-1--server--omgevingscontrole-op-de-doelhost) | Systeembeheerder Doelorg. | Doelserver |
| **Fase 2** | [Plaatsing & Omgevingsvariabelen (.env)](#fase-2--plaatsing--configuratie-op-de-doelhost) | DevOps / Consultant | Doelserver |
| **Fase 3** | [Docker Stack Bouwen & Database Starten](#fase-3--docker-stack-bouwen--database-starten) | DevOps / Consultant | Doelserver |
| **Fase 4** | [Database Vullen via Dumpbestand (Restore)](#fase-4--database-vullen-via-het-dumpbestand-restore) | DevOps / Database Beheerder | Doelserver |
| **Fase 5** | [Volledige Stack Starten & Health Checks](#fase-5--volledige-stack-starten--service-health-checks) | DevOps / Consultant | Doelserver |
| **Fase 6** | [Functionele & Visuele Acceptatietest](#fase-6--functionele--visuele-acceptatietesten) | Functioneel Beheerder / Gebruiker | Client Browser |
| **Fase 7** | [Productie-Hardening & Automatische Backups](#fase-7--beheer-monitoring-backup--productie-hardening) | Systeembeheerder Doelorg. | Doelserver |

---

## Fase 0 — Voorbereiding op de Bronomgeving

Voer deze stappen uit op de **ontwikkel- of bronomgeving** vóórdat het installatiepakket naar de klant/doelorganisatie wordt overgedragen.

### Stap 0.1: Admin Panel Productie Build genereren
Zorg dat de React frontend van het Admin Panel vers gebouwd is en in de `static/admin-panel` map staat:

```bash
# 1. Navigeer naar de admin-panel map en installeer dependencies
cd admin-panel
npm install

# 2. Bouw de productiebundel
npm run build

# 3. Kopieer de gebouwde bestanden naar de static backend map
rm -rf ../static/admin-panel/*
cp -r build/* ../static/admin-panel/

# 4. Controleer of de index.html aanwezig is
ls -la ../static/admin-panel/index.html
cd ..
```

---

### Stap 0.2: Database Dumpbestand exporteren
Exporteer een schone, gecomprimeerde dump van de actuele PostgreSQL/PostGIS database. 

> [!TIP]
> **Aanbevolen Formaat: PostgreSQL Custom Format (`-Fc`)**  
> Het custom binaire formaat is uiterst flexibel, gecomprimeerd en stelt `pg_restore` in staat om objecten in de juiste volgorde met foutafhandeling in te lezen.

Voer het dumpcommando uit vanaf de bronomgeving:

```bash
# Optie A (Aanbevolen): PostgreSQL Custom Format (.dump)
docker compose exec -T postgres pg_dump \
  -U omnitwin_user \
  -d omnitwin_db \
  -Fc \
  -b \
  -v \
  --no-owner \
  --no-privileges \
  -f /tmp/omnitwin_db_release.dump

# Kopieer het bestand uit de container naar de lokale schijf
docker compose cp postgres:/tmp/omnitwin_db_release.dump ./omnitwin_db_release.dump
```

```bash
# Optie B (Alternatief): Gecodificeerde Plain SQL Dump (.sql.gz)
docker compose exec -T postgres pg_dump \
  -U omnitwin_user \
  -d omnitwin_db \
  --no-owner \
  --no-privileges \
  | gzip > ./omnitwin_db_release.sql.gz
```

> **Waarom `--no-owner --no-privileges`?**  
> Hiermee voorkom je dat eigendomsrechten hardcoded worden vastgelegd op een specifieke database-rol. Bij de restore op de doelhost worden de tabellen direct eigendom van de lokale gebruiker die in de `.env` van de doelomgeving is gedefinieerd.

---

### Stap 0.3: Release-Pakket Samenstellen
Stel het leverpakket samen voor de doelorganisatie:
1. De D-OmniTwin codebase (via `git clone` van de gewenste release tag of een `.tar.gz` archief, **zonder** lokale `.venv`, `cache/` of `.env` secrets).
2. Het gegenereerde dumpbestand `omnitwin_db_release.dump`.

---

## Fase 1 — Server- & Omgevingscontrole op de Doelhost

Controleer op de doelserver van de externe organisatie of aan alle randvoorwaarden wordt voldaan.

### Stap 1.1: Systeemeisen & Hardware
* **Besturingssysteem:** Linux (Ubuntu Server 22.04 LTS / 24.04 LTS of RHEL 8 / 9).
* **Hardware:**
  * Minimaal (Pilot / Evaluatie): **4 vCPU, 8 GB RAM, 40 GB SSD**.
  * Aanbevolen (Productie & Intensief GIS-gebruik): **8 vCPU, 16 GB RAM, 80 GB SSD**.
* **Vrije schijfruimte controleren:**
  ```bash
  df -h /var/lib/docker
  ```

---

### Stap 1.2: Docker Runtime & Compose v2 controleren
Controleer of Docker Engine (versie 24.0+) en Docker Compose (versie 2.20+) geïnstalleerd zijn:

```bash
docker --version
docker compose version
```

*Indien Docker nog niet geïnstalleerd is op Ubuntu:*
```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
```

---

### Stap 1.3: Netwerk & Firewall
* **Inkomend (Inbound):**
  * Poort `80/TCP` (HTTP) en/of `443/TCP` (HTTPS) openstellen voor gebruikers / werkplekken.
  * De installatie (`docker-compose.yml`, zie `COMPOSE_FILE` in Stap 2.2) publiceert alleen poort 80. De databasepoort `5433` en het Traefik-dashboard op `8081` staan alleen in de dev-override (`docker-compose.override.yml`).
* **Uitgaand (Outbound internet):**
  * Toegang tot `https://api.pdok.nl`, `https://opendata.cbs.nl` en `https://statline.rivm.nl` via poort `443/TCP` (voor eventuele toekomstige kaart- en dataconsumptie).

---

## Fase 2 — Plaatsing & Configuratie op de Doelhost

### Stap 2.1: Projectstructuur plaatsen
Plaats de D-OmniTwin bestanden op de gewenste locatie op de doelserver (bijvoorbeeld `/opt/d-omnitwin`):

```bash
# Maak de applicatiedirectory aan
sudo mkdir -p /opt/d-omnitwin
sudo chown -R $USER:$USER /opt/d-omnitwin

# Navigeer naar de map
cd /opt/d-omnitwin

# Plaats de bestanden (via git clone of scp/tar)
# git clone https://github.com/jouw-organisatie/D-OmniTwin.git .
```

Plaats het dumpbestand in een aparte submap:
```bash
mkdir -p /opt/d-omnitwin/backups
mv /pad/naar/omnitwin_db_release.dump /opt/d-omnitwin/backups/
```

---

### Stap 2.2: Omgevingsvariabelen configureren (`.env`)
Kopieer de template en genereer unieke, sterke geheimen voor de productieomgeving:

```bash
cp .env.example .env
```

Genereer sterke secrets:
```bash
# 1. Genereer een SECRET_KEY:
openssl rand -base64 32

# 2. Genereer een ADMIN_API_KEY:
python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32

# 3. Genereer een sterk DATABASE_PASSWORD:
openssl rand -base64 24
```

Pas `.env` aan met je favoriete editor (`nano .env` of `vim .env`):

```ini
# ─── Docker Compose ──────────────────────────────────────
# Alleen de basis laden, niet de dev-override (bind-mount, open DB-poort, dashboard)
COMPOSE_FILE=docker-compose.yml

# ─── Database ────────────────────────────────────────────
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=omnitwin_db
DATABASE_USER=omnitwin_user
DATABASE_PASSWORD=<jouw-nieuw-gegenereerde-db-wachtwoord>
DATABASE_SSLMODE=prefer

# ─── API Security ─────────────────────────────────────────
SECRET_KEY=<jouw-nieuw-gegenereerde-secret-key>
CORS_ORIGINS=http://localhost,http://localhost:80,https://omnitwin.jouwgemeente.nl

# ─── App Instellingen ─────────────────────────────────────
DEBUG=false
LOG_LEVEL=INFO

# ─── Admin Panel ──────────────────────────────────────────
ADMIN_API_KEY=<jouw-nieuw-gegenereerde-admin-api-key>
ADMIN_USER=admin
ADMIN_PASSWORD=<kies-een-sterk-initieel-admin-wachtwoord>

# ─── Optionele Lokale AI ──────────────────────────────────
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL=gemma4
```

---

### Stap 2.3: Bestandsrechten beveiligen
Zorg dat het `.env` bestand strikt beveiligd is tegen onbevoegde leestoegang:

```bash
chmod 600 .env
chmod 700 backups
```

---

## Fase 3 — Docker Stack Bouwen & Database Starten

### Stap 3.1: Docker Images bouwen
Bouw de images lokaal op de server. De database image (`db.Dockerfile`) installeert automatisch `PostGIS 3.4` en de `pgvector` extensie:

```bash
docker compose build
```

---

### Stap 3.2: Eerst alleen de Database container starten
Start **uitsluitend** de PostgreSQL container, zodat de database klaar is om de dump te ontvangen:

```bash
docker compose up -d postgres
```

Controleer de opstartstatus:
```bash
docker compose ps postgres
docker compose logs -f postgres
```
*(Druk op `Ctrl+C` zodra de log aangeeft: `database system is ready to accept connections`)*.

---

### Stap 3.3: PostgreSQL Extensies Verifiëren
Zorg dat de vereiste extensies (`postgis`, `vector`, `pg_trgm`) geactiveerd zijn in de lege database:

```bash
docker compose exec -T postgres psql -U omnitwin_user -d omnitwin_db -c "
  CREATE EXTENSION IF NOT EXISTS postgis;
  CREATE EXTENSION IF NOT EXISTS vector;
  CREATE EXTENSION IF NOT EXISTS pg_trgm;
"
```

*Verificatie van de extensies:*
```bash
docker compose exec -T postgres psql -U omnitwin_user -d omnitwin_db -c "\dx"
```
Je ziet nu `plpgsql`, `postgis`, `vector` en `pg_trgm` in de lijst.

---

## Fase 4 — Database Vullen via het Dumpbestand (Restore)

### Stap 4.1: Restore commando uitvoeren

Gebruik het juiste commando afhankelijk van het dumpformaat:

#### Optie A (Aanbevolen: Custom Format `.dump` via `pg_restore`):
```bash
# Voer pg_restore uit via stdin streaming
docker compose exec -T postgres pg_restore \
  -U omnitwin_user \
  -d omnitwin_db \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  -v < /opt/d-omnitwin/backups/omnitwin_db_release.dump
```

> [!NOTE]
> `pg_restore` kan enkele niet-fatale waarschuwingen geven bij het opruimen van objecten die nog niet bestonden (`--clean`). Dit is normaal gedrag.

#### Optie B (Gecodificeerde Plain SQL `.sql.gz`):
```bash
gunzip -c /opt/d-omnitwin/backups/omnitwin_db_release.sql.gz \
  | docker compose exec -T postgres psql -U omnitwin_user -d omnitwin_db
```

---

### Stap 4.2: Post-Restore Integriteitscontroles
Voer onderstaande query uit om te verifiëren of alle tabellen, views en rijen succesvol zijn ingelezen:

```bash
docker compose exec -T postgres psql -U omnitwin_user -d omnitwin_db -c "
SELECT 'Indicatoren' AS tabel, count(*) FROM indicatoren
UNION ALL
SELECT 'Gebieden / Buurten', count(*) FROM gebieden
UNION ALL
SELECT 'Indicator Metingen (gebied_data)', count(*) FROM gebied_data
UNION ALL
SELECT 'Kompas Onderdelen', count(*) FROM kompas_onderdelen
UNION ALL
SELECT 'Views (v_kompas_hierarchie)', count(*) FROM v_kompas_hierarchie
UNION ALL
SELECT 'Gebruikers (users)', count(*) FROM users;
"
```

**Verwachte resultaten:**
* **Indicatoren:** ~244 rijen
* **Gebieden / Buurten:** ~942 rijen (voor Friese buurten)
* **Indicator Metingen:** Meerdere tienduizenden metingen
* **Kompas Onderdelen:** >200 elementen
* **Views:** Geen SQL-foutmelding

Controleer ook de ruimtelijke projectie (SRID):
```bash
docker compose exec -T postgres psql -U omnitwin_user -d omnitwin_db -c "
SELECT code, naam, ST_GeometryType(geom) AS geom_type, ST_SRID(geom) AS srid 
FROM gebieden 
LIMIT 3;
"
```
*(SRID moet `4326` of `28992` zijn)*.

---

### Stap 4.3: Beheerdersaccount & Wachtwoord configureren
De dump bevat mogelijk een bestaand beheeraccount uit de ontwikkelomgeving. Stel een nieuw, veilig wachtwoord in voor de lokale beheerder:

```bash
# Voer het beheerder setup script uit via de backend container (of direct via SQL)
# Zodra de backend draait in Stap 5.1:
docker compose up -d backend
docker compose exec backend python init_data/scripts/create_admin.py --reset-password
```

---

## Fase 5 — Volledige Stack Starten & Service Health Checks

### Stap 5.1: Alle containers starten
Start nu de volledige microservices-stack:

```bash
docker compose up -d
```

Controleer of alle services de status `Up` hebben (backend en postgres met `(healthy)`):
```bash
docker compose ps -a
```
`db-init` staat op `Exited (0)`: die initialiseert eenmalig en stopt. Bij een teruggezette dump (tabel `gebieden` bestaat) slaat hij de initialisatie over.

---

### Stap 5.2: Service Health Checks uitvoeren

Voer een complete end-to-end controle uit via de terminal op de host:

```bash
# 1. Traefik Gateway & Webapp Root
curl -s -o /dev/null -w "HTTP Status Traefik / Backend UI: %{http_code}\n" http://localhost/

# 2. FastAPI Backend API
curl -s -o /dev/null -w "HTTP Status FastAPI Docs: %{http_code}\n" http://localhost/docs

# 3. PostgREST Data API (/api/data/)
curl -s "http://localhost/api/data/indicatoren?limit=1" | grep -q "code" && echo "✅ PostgREST API: OK" || echo "❌ PostgREST API: Fout"

# 4. pg_featureserv Geo API (/api/geo/)
curl -s "http://localhost/api/geo/collections.json" | grep -q "collections" && echo "✅ pg_featureserv Geo API: OK" || echo "❌ pg_featureserv Geo API: Fout"

# 5. Admin Panel Interface
curl -s -o /dev/null -w "HTTP Status Admin Panel: %{http_code}\n" http://localhost/admin
```

**Verwachte output:**
```text
HTTP Status Traefik / Backend UI: 200
HTTP Status FastAPI Docs: 200
✅ PostgREST API: OK
✅ pg_featureserv Geo API: OK
HTTP Status Admin Panel: 200
```

---

## Fase 6 — Functionele & Visuele Acceptatietesten

Open een webbrowser op een werkplek binnen het organisatienetwerk en navigeer naar:  
👉 **`http://<server-ip-of-domeinnaam>/`**

### Acceptatiechecklist:

- [ ] **1. Kaartlaag & Geometrieën:**
  - De kaart laadt soepel (MapLibre GL).
  - Alle buurt- en gemeentegrenzen worden getoond als interactieve polygonen.
  - Hoveren over een buurt toont een tooltip met de buurtnaam.
- [ ] **2. D-Omni Kompas Visualisatie:**
  - Het D3.js sunburst-wiel rendert direct in het linkerscherm.
  - Alle 4 leefwerelddomeinen en 12 thema's zijn zichtbaar.
  - Klikken op een thema filtert de indicatorenlijst.
- [ ] **3. Detailpaneel & Indicatordata:**
  - Klik op een willekeurige buurt.
  - Het detailpaneel opent met actuele Z-scores, percentielen en grafieken.
  - Klik op het tabblad *Data Lineage* of het ℹ️ icoon: bronvermelding (CBS/RIVM/PDOK) en peildatum worden correct getoond.
- [ ] **4. Externe Kaartlagen:**
  - Open het paneel *Externe Kaartlagen*.
  - Schakel een laag in (bijv. *Natura 2000* of *Rijksmonumenten*).
  - De WFS geodata wordt via pg_featureserv/PDOK getoond over de kaart.
- [ ] **5. Admin Beheerportaal:**
  - Navigeer naar `http://<server-ip-of-domeinnaam>/admin`.
  - Log in met de `ADMIN_USER` en het in Stap 4.3 ingestelde wachtwoord.
  - Controleer of het dashboard, de indicator-editor en de logviewer functioneren.

---

## Fase 7 — Beheer, Monitoring, Backup & Productie-Hardening

### Stap 7.1: Geautomatiseerde Database Backup (Cronjob)
Richt een dagelijkse geautomatiseerde backup in met een retentieperiode van 14 dagen.

Maak een back-upscript `/opt/d-omnitwin/scripts/daily_backup.sh`:

```bash
sudo mkdir -p /opt/d-omnitwin/scripts
sudo tee /opt/d-omnitwin/scripts/daily_backup.sh > /dev/null << 'EOF'
#!/bin/bash
set -e

BACKUP_DIR="/opt/d-omnitwin/backups/daily"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/omnitwin_backup_${TIMESTAMP}.dump"
RETENTION_DAYS=14

mkdir -p "$BACKUP_DIR"

# Database dump uitvoeren
cd /opt/d-omnitwin  # docker compose werkt vanuit de projectmap
docker compose exec -T postgres pg_dump -U omnitwin_user -d omnitwin_db -Fc -b > "$BACKUP_FILE"

# Loggen
echo "[$(date)] Backup succesvol aangemaakt: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# Verwijder backups ouder dan 14 dagen
find "$BACKUP_DIR" -type f -name "omnitwin_backup_*.dump" -mtime +$RETENTION_DAYS -delete
EOF

sudo chmod +x /opt/d-omnitwin/scripts/daily_backup.sh
```

Voeg toe aan de crontab van de server (`crontab -e`):
```cron
# Dagelijkse D-OmniTwin backup om 02:30 uur 's nachts
30 2 * * * /opt/d-omnitwin/scripts/daily_backup.sh >> /opt/d-omnitwin/backups/backup.log 2>&1
```

---

### Stap 7.2: Productie Beveiligings- & SSL-Hardening Checklist

1. **SSL/TLS Terminatie (HTTPS):**
   * *Optie A (Aanbevolen bij gemeenten):* Plaats D-OmniTwin achter de bestaande gemeentelijke WAF / Reverse Proxy (zoals F5 BIG-IP, NGINX, Azure App Gateway of Cloudflare). De WAF verzorgt het officiële SSL-certificaat en routeert intern door naar poort 80 van Traefik.
   * *Optie B:* Configureer Let's Encrypt rechtstreeks in `docker-compose.yml` via Traefik HTTPS-entrypoints.
2. **Beperk Blootstelling van Beheerpoorten:**
   * Met `COMPOSE_FILE=docker-compose.yml` zijn de database (`5433`) en het Traefik-dashboard (`8081`) niet op de host bereikbaar. Is databasetoegang vanaf de host nodig, bind dan alleen op `127.0.0.1` via een eigen override-bestand:
     ```yaml
     services:
       postgres:
         ports:
           - "127.0.0.1:5433:5432"
     ```
3. **Logrotatie in Docker:**
   Voorkom dat Docker logbestanden de schijf vullen door logrotatie in `/etc/docker/daemon.json` te configureren:
   ```json
   {
     "log-driver": "json-file",
     "log-opts": {
       "max-size": "50m",
       "max-file": "3"
     }
   }
   ```
   Herstart Docker na aanpassing: `sudo systemctl restart docker`.

---

## 8. 🛠️ Troubleshooting & Veelgestelde Vragen

| Probleem / Foutmelding | Mogelijke Oorzaak | Oplossing |
|---|---|---|
| `FATAL: password authentication failed for user "omnitwin_user"` | Wachtwoord in `.env` komt niet overeen met het PostgreSQL wachtwoord. | Controleer `DATABASE_PASSWORD` in `.env`. Bij herstart met bestaand volume `pgdata` behoudt Postgres het oude wachtwoord tenzij expliciet gewijzigd. |
| `ERROR: extension "vector" does not exist` | De PostgreSQL container draait op een standaard Postgres image zonder pgvector. | Controleer of de container gebouwd is via `db.Dockerfile` (`docker compose build postgres`). |
| `pg_restore: error: input file does not appear to be a valid archive` | Het dumpbestand is een plain SQL bestand in plaats van een binary custom dump. | Gebruik `psql` i.p.v. `pg_restore` (zie [Fase 4, Optie B](#optie-b-gecodificeerde-plain-sql-sqlgz)). |
| `PostgREST API geeft 502 Bad Gateway` | PostgREST kan de database niet bereiken of wachtwoorden matchen niet. | Controleer `docker compose logs postgrest` en valideer de connectiestring in `docker-compose.yml`. |
| `Kaart blijft leeg / buurten worden niet getekend` | Geometrieën ontbreken of pg_featureserv heeft geen toegang tot de `geom` kolom. | Controleer `http://localhost/api/geo/collections.json` en voer `SELECT count(*) FROM gebieden;` uit in Postgres. |
| `Admin panel toont 'Network Error' of 401` | `ADMIN_API_KEY` in `.env` wijkt af of frontend build wijst naar onjuiste API URL. | Controleer `ADMIN_API_KEY` in `.env` en herstart `docker compose restart backend`. |

---

## 9. 📞 Contact & Technische Ondersteuning

Voor vragen over deze installatieprocedure, data-updates of architectuur-ondersteuning:
* **Technisch Project Lead & Architect:** Thijs van der Laan ([t.vanderlaan@sudwestfryslan.nl](mailto:t.vanderlaan@sudwestfryslan.nl))
* **Documentatie & Architectuurnotities:** Zie [`docs/2-architectuur/architecture/systeemarchitectuur_en_implementatiegids_ict.md`](../2-architectuur/architecture/systeemarchitectuur_en_implementatiegids_ict.md)
* **Kennisdatabase Router:** Zie [`docs/INDEX.md`](../INDEX.md)

# 🚀 Getting Started — D-OmniTwin

Welkom bij D-OmniTwin! Deze gids leidt je in **vier stappen** van een lege kloon naar een volledig werkende applicatie met echte data van de provincie Fryslân.

> **Tijdsinschatting:** ± 30 minuten (inclusief downloads)

---

## Vereisten

Zorg dat onderstaande software geïnstalleerd is voordat je begint:

| Software | Versie | Installatie |
|----------|--------|-------------|
| Python | 3.10+ | [python.org](https://www.python.org/downloads/) |
| PostgreSQL | 14+ | [postgresql.org](https://www.postgresql.org/download/) |
| PostGIS extensie | 3.x | Via apt/brew of bij PostgreSQL installer |
| pgvector extensie | latest | [github.com/pgvector/pgvector](https://github.com/pgvector/pgvector) |
| Git | any | [git-scm.com](https://git-scm.com/) |
| Node.js | 18+ | Alleen nodig voor het Admin Panel |

> [!TIP]
> **Ollama (voor AI-functies)** is optioneel. De kaart, het Kompas en de rapportage werken ook zonder. Je kunt Ollama altijd later toevoegen via het Admin Panel.

---

## Stap 1 — Repository klonen & omgeving inrichten

```bash
# Clone de repository
git clone https://github.com/jouw-org/D-OmniTwin.git
cd D-OmniTwin

# Python virtual environment aanmaken en activeren
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# Dependencies installeren
pip install -r requirements.txt

# Environment instellen via de wizard
python init_data/scripts/setup_env.py
```

De wizard helpt je met het instellen van de benodigde inloggegevens en genereert veilige wachtwoorden en API keys.
Je kunt ook handmatig `cp .env.example .env` uitvoeren en het bestand zelf aanpassen.

---

## Stap 2 — PostgreSQL database aanmaken

```bash
# Database en gebruiker aanmaken (voer uit als postgres superuser)
sudo -u postgres psql -c "CREATE USER omnitwin_user WITH PASSWORD 'jouw-wachtwoord';"
sudo -u postgres psql -c "CREATE DATABASE omnitwin_db OWNER omnitwin_user;"

# Vereiste extensies activeren
sudo -u postgres psql -d omnitwin_db -c "CREATE EXTENSION postgis;"
sudo -u postgres psql -d omnitwin_db -c "CREATE EXTENSION vector;"
```

> [!NOTE]
> **Windows/macOS:** Vervang `sudo -u postgres psql` door `psql -U postgres` en voer je postgres-wachtwoord in wanneer gevraagd.

---

## Stap 3 — Initiatie dataset downloaden

De kaart en het Kompas hebben geodata nodig. Dit zijn CBS open data bestanden (CC BY licentie).

### 3a. Buurten Fryslân downloaden (PDOK API)

De kaart heeft geometrieën nodig van alle buurten. Het download script haalt deze direct op van de PDOK WFS API:

```bash
python init_data/scripts/download_buurten_fryslan.py
```

Dit script haalt de contouren van alle 18 Friese gemeenten op (CBS gebiedsindelingen 2024), converteert ze naar het WGS84 coördinatensysteem voor de kaart, en slaat ze op als `init_data/fryslan/buurten_fryslan.geojson` (~5-10 MB).

> [!NOTE]
> Dit script vervangt het oude `extract_buurten_fryslan.py` en heeft geen lokale zware GPKG bestanden meer nodig.

### 3b. Indicatorwaarden downloaden

```bash
python init_data/scripts/download_indicatoren_fryslan.py
```

Dit haalt de CBS open data op voor de Friese buurten:
- Kerncijfers (inkomen, woningbezit, leeftijdsopbouw, opleiding)
- Gezondheidsmonitor RIVM (eenzaamheid, overgewicht, bewegen)
- Nabijheid voorzieningen (afstand tot huisarts, supermarkt, school, ...)
- Veiligheid (overlast, inbraak)

> [!NOTE]
> De downloads zijn afhankelijk van de CBS OData API. Bij een trage verbinding kan dit 5–15 minuten duren.

---

## Stap 4 — Database initialiseren en vullen

```bash
bash init_data/scripts/init_database.sh
```

Dit script voert in volgorde uit:
1. **Schema laden** — alle tabellen, views en triggers aanmaken (incl. users/sessions/api_keys)
2. **Indicatoren seeden** — 235 indicatoren met metadata en Kompas-hiërarchie
3. **Kompas laden** — de volledige hiërarchie (Titels → Thema's → Onderdelen)
4. **Buurten importeren** — GeoJSON met PostGIS geometrie
5. **Waarden importeren** — CBS indicatorwaarden per buurt
6. **Admin aanmaken** — eerste admin gebruiker + API key (interactief)

> [!TIP]
> Je kunt ook individuele stappen uitvoeren:
> ```bash
> python init_data/scripts/seed_fryslan.py --stap buurten
> python init_data/scripts/seed_fryslan.py --stap waarden
> python init_data/scripts/create_admin.py --reset-password
> ```

---

## Stap 5 — Applicatie starten

```bash
source .venv/bin/activate
python run_dev.py
```

Open in je browser: **http://localhost:8000**

Je ziet nu:
- 🗺️ **Interactieve kaart** met alle Friese buurten als choropleth
- 🧭 **D-Omni Kompas** met de volledige indicatorhiërarchie
- 📊 **Gebiedsmonitor** — klik een buurt aan voor direct inzicht
- 🤖 **D-Omni Assistent** — stel een vraag zoals *"Welke buurten in Sneek zijn het eenzaamst?"*

---

## Stap 6 — Admin Panel

Na de start kun je inloggen op het beheerportaal:

**http://localhost:8000/admin**

| Gegeven | Waarde |
|---------|--------|
| Gebruikersnaam | `admin` (of waarde van `ADMIN_USER` in `.env`) |
| Wachtwoord | ingesteld tijdens `init_database.sh` (stap 6) |
| API Key | ingesteld in `.env` als `ADMIN_API_KEY` |

Het Admin Panel geeft toegang tot:
- Indicator editor (namen, beschrijvingen, kleurschema's)
- Kompas hiërarchie beheer
- LLM configuratie (Ollama model instellen)
- Dashboard met statistieken

> [!TIP]
> Wachtwoord vergeten? Reset met:
> ```bash
> python init_data/scripts/create_admin.py --reset-password
> ```

---

## Eigen gemeente of regio toevoegen

Na de eerste start kun je data toevoegen van andere gemeenten via het ETL framework:

```bash
# Zoek een CBS dataset
cd ETL
python search_api.py -q "Gezondheid"

# Importeer data voor een gemeente (bijv. Groningen = GM0014)
python run_etl.py -ds 83739NED -gm 0014
```

Zie [`ETL/ETL_DOCUMENTATION.md`](ETL/ETL_DOCUMENTATION.md) voor de volledige handleiding.

---

## Problemen oplossen

| Fout | Oplossing |
|------|-----------|
| `psql: FATAL: password authentication failed` | Controleer `DATABASE_PASSWORD` in `.env` |
| `extension "postgis" does not exist` | Installeer PostGIS: `sudo apt install postgresql-14-postgis-3` |
| `extension "vector" does not exist` | Installeer pgvector via OS (bijv. `sudo apt install postgresql-14-pgvector`) of compileer zelf: `cd /tmp && git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git && cd pgvector && make && sudo make install` |
| `ModuleNotFoundError: No module named 'psycopg2'` | Activeer virtual environment: `source .venv/bin/activate` |
| `ModuleNotFoundError: No module named 'passlib'` | Installeer: `pip install passlib[bcrypt]` |
| `buurten_fryslan.geojson` niet gevonden | Voer `python init_data/scripts/download_buurten_fryslan.py` uit |
| Kompas is leeg | Voer seed stap kompas uit: `python init_data/scripts/seed_fryslan.py --stap kompas` |
| `relation "users" does not exist` | Schema is verouderd — voer `init_database.sh` opnieuw uit op een lege DB |
| Kan niet inloggen in Admin Panel | Voer `python init_data/scripts/create_admin.py` uit om admin aan te maken |
| PDOK download mislukt | Controleer internetverbinding. Probeer direct in browser: `https://geodata.nationaalgeoregister.nl/cbsgebiedsindelingen/wfs?service=WFS&request=GetCapabilities` |

---

## Volgende stappen

- 📖 **Architectuur:** [`docs/2-architectuur/`](docs/2-architectuur/) — technische opzet
- 🗺️ **Roadmap:** [`ROADMAP.md`](ROADMAP.md) — geplande features
- 🐛 **Bugs & fixes:** [`BUGFIX.md`](BUGFIX.md) — bekende issues
- 💬 **Vragen of samenwerking?** Open een [GitHub Discussion](../../discussions) of mail [t.vanderlaan@sudwestfryslan.nl](mailto:t.vanderlaan@sudwestfryslan.nl)

---

*D-OmniTwin — Open source digitale spiegel van de fysieke leefomgeving | EUPL 1.2*

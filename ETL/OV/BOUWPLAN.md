# ETL — OV Haltes (OpenStreetMap via Overpass API)

**Aangemaakt:** 2026-06-02  
**Bijgewerkt:** 2026-06-03 (na live data-analyse + indicator-structuuraudit)  
**Status:** ✅ Klaar voor implementatie  
**Doel:** OV-haltes (bus, tram, trein, veerboot) ophalen uit OpenStreetMap voor de provincies Fryslân, Groningen en Drenthe, koppelen aan CBS-buurten en opslaan als indicatoren in D-OmniTwin.  
**Gebaseerd op:**
- Live Overpass-analyse: 3062 nodes Fryslân, 60 nodes Leeuwarden CS
- Indicator-structuuraudit: zie [`INDICATOR_STRUCTUUR_ANALYSE.md`](./INDICATOR_STRUCTUUR_ANALYSE.md)
- Deduplicatiestrategie: zie [`STRATEGIE_ANALYSE.md`](./STRATEGIE_ANALYSE.md)

**Geïnspireerd door:** [OV - Haltes Nederland actueel (Provincie Zuid-Holland / OSM)](https://www.nationaalgeoregister.nl/geonetwork/srv/api/records/1e0876db-6991-46a5-8ff0-cc01495d9345)

---

## Achtergrond & Rationale

De NM-001 gap-analyse IJsselmeerkust identificeert "afstand tot OV-halte" en "bereikbaarheid" als een van de meest relevante ontbrekende indicatoren voor de casus Makkum/Workum/Koudum. CBS levert geen halte-gebaseerde bereikbaarheidsdata op buurtniveau. OpenStreetMap is de meest actuele en vrij beschikbare bron voor OV-halte locaties in Nederland.

**Waarom Overpass API en niet geofabrik + osm2pgsql?**

| Aanpak | Voordelen | Nadelen |
|--------|-----------|---------|
| **geofabrik + osm2pgsql** (Zuid-Holland aanpak) | Volledige OSM dataset, offline, snel bij hergebruik | Zware installatie, PBF bestand (~300MB/provincie), PostGIS osm schema vereist |
| **Overpass API** (ons plan) | Geen installatie, Python-only, filtert direct op halte-tags, gratis | Rate limits (gebruik beleefde delays), max 10k features/query (prima voor haltes) |

→ **Keuze: Overpass API via OSMPythonTools** — past in onze Python+PostGIS stack, geen extra tools. OSMPythonTools heeft ingebouwde caching en werkt vanuit de WSL-omgeving.

---

## De indicator-infrastructuur: hoe het werkt in D-OmniTwin

Voordat we de output beschrijven, is het essentieel te begrijpen hoe indicatoren in D-OmniTwin opgebouwd zijn. Elke OV-indicator doorloopt deze 4-laagse structuur:

```
kompas_configuraties      ← "Volledig Kompas" (de container)
    └── kompas_titels     ← Niveau 1: "Kwaliteit fysieke leefomgeving"
         └── kompas_themas     ← Niveau 2: "Verkeer"
              └── kompas_onderdelen  ← Niveau 3: "Bereikbaarheid en parkeren"
                   └── kompas_indicator_mapping  ← koppeling aan indicator UUID
                            ↓
                        indicatoren (uuid, naam, code, eenheid, score_type, ...)
                            ↓
                        gebied_data (gebied_id, indicator_uuid, waarde, jaar, scenario_id)
                            ↓
                        gebieden (id = CBS-code bijv. "BU00980903")
```

> **Kritisch:** In `gebied_data` heet het sleutelveld `gebied_id` (niet `buurt_code`).  
> De waarde is de CBS-code uit `gebieden.id` (bijv. `BU00980903`).

---

## Output: Wat willen we in de database?

### Tabel 1: `ov_haltes` (ruwe OSM nodes — alles bewaren)

Interne werktabel. Bevat alle ruwe OSM-nodes zoals opgehaald via Overpass.

| Kolom | Type | Beschrijving |
|-------|------|-------------|
| `osm_id` | BIGINT PK | OpenStreetMap node ID |
| `naam` | TEXT | `name` tag uit OSM |
| `ov_type` | TEXT | `bus` / `tram` / `trein` / `veerboot` / `metro` |
| `osm_pt_type` | TEXT | Ruwe OSM-tag: `platform` / `stop_position` / `station` / `ferry_terminal` / `bus_stop` |
| `network` | TEXT | Operator/netwerk (bijv. `Arriva`, `NS`) |
| `ref` | TEXT | Haltenummer |
| `gemeente_code` | TEXT | CBS gemeentecode (via ST_Within join op `gebieden`) |
| `gebied_id` | TEXT | = `gebieden.id` (CBS buurt-code, bijv. `BU00980903`) |
| `provincie` | TEXT | `FR` / `GR` / `DR` |
| `geom` | GEOMETRY(Point, 28992) | Punt in Rijksdriehoek |
| `peildatum` | DATE | Datum van Overpass-query |
| `tags` | JSONB | Volledige OSM tags |

### Tabel 2: `ov_halte_clusters` (gededupliceerde locaties — indicator-basis)

Kernbevinding: Leeuwarden CS heeft 60 OSM nodes voor 1 knooppunt. Deduplicatie via naam + OV-type + 75m spatial clustering geeft één rij per unieke wachtlocatie.

| Kolom | Type | Beschrijving |
|-------|------|-------------|
| `cluster_id` | UUID PK | `gen_random_uuid()` |
| `naam` | TEXT | Canonical naam |
| `ov_type` | TEXT | `bus` / `trein` / `tram` / `veerboot` |
| `n_platforms` | INT | Aantal OSM nodes in dit cluster |
| `gebied_id` | TEXT | = `gebieden.id` (CBS buurt-code) — via centroid ST_Within |
| `gemeente_code` | TEXT | CBS gemeentecode — via centroid ST_Within |
| `provincie` | TEXT | `FR` / `GR` / `DR` |
| `geom` | GEOMETRY(Point, 28992) | Centroid van cluster |
| `peildatum` | DATE | Datum import |

### Tabel 3: `ov_haltes_per_buurt` (staging/verificatietabel)

Handige aggregatietabel voor verificatie en debugging. De Kompas-koppeling loopt via `gebied_data`, niet via deze tabel.

| Kolom | Type | Beschrijving |
|-------|------|-------------|
| `gebied_id` | TEXT | = `gebieden.id` (CBS buurt-code) |
| `jaar` | INT | Peiljaar |
| `totaal_haltes` | INT | Alle unieke OV-clusters in buurt |
| `haltes_bus` | INT | Bushaltes |
| `haltes_tram` | INT | Tramhaltes |
| `haltes_trein` | INT | Treinhaltes |
| `haltes_veerboot` | INT | Veerboten |
| `haltes_metro` | INT | Metro |
| PRIMARY KEY | `(gebied_id, jaar)` | |

### De 5 Kompas-indicatoren

Elke OV-type wordt een aparte indicator in de `indicatoren` tabel. Plaatsing in de Kompas-hiërarchie: **Kwaliteit fysieke leefomgeving → Verkeer → Bereikbaarheid en parkeren**.

| Code | Naam | Eenheid | score_type | omschrijving |
|------|------|---------|------------|--------------|
| `OV_HALTES_TOTAAL` | Aantal OV-haltes (totaal) | `aantal` | `+/+` | Totaal unieke OV-haltelocaties per buurt (bus, trein, tram, veerboot) |
| `OV_HALTES_BUS` | Aantal bushaltes | `aantal` | `+/+` | Unieke bushaltelocaties per buurt (gededupliceerd op naam + 75m) |
| `OV_HALTES_TREIN` | Aantal treinhaltes | `aantal` | `+/+` | Treinstation-locaties per buurt (railway=station) |
| `OV_HALTES_TRAM` | Aantal tramhaltes | `aantal` | `+/+` | Tramhaltelocaties per buurt |
| `OV_HALTES_VEERBOOT` | Aantal veerboten | `aantal` | `+/+` | Veerboot-aanleglocaties per buurt (amenity=ferry_terminal) |

---

## Dataflow (volledig en correct)

```
[Overpass API via OSMPythonTools]
    │  QL query per provincie (FR/GR/DR)
    │  Tags: platform + bus_stop + station + ferry_terminal
    │  Gecached (~/.cache/OSMPythonTools)
    ▼
[Transform 1: OV-type bepalen]
    │  Prioriteit: railway=station → trein
    │             amenity=ferry_terminal → veerboot
    │             railway=tram_stop → tram
    │             highway=bus_stop / bus=yes → bus
    │             platform zonder verdere tags → bus (NL-standaard)
    ▼
[Transform 2: CRS-transformatie]
    │  WGS84 (4326) → Rijksdriehoek (28992) via pyproj
    ▼
[Load 1 — tabel: ov_haltes]
    │  INSERT ... ON CONFLICT (osm_id) DO UPDATE
    │  Alle ruwe nodes opslaan
    ▼
[Transform 3: Spatial clustering (deduplicatie)]
    │  Per provincie + ov_type:
    │    - Groepeer nodes met zelfde naam + onderlinge afstand ≤ 75m
    │    - één cluster = één unieke wachtlocatie
    │    - Centroid berekenen per cluster
    ▼
[Load 2 — tabel: ov_halte_clusters]
    │  Gededupliceerde locaties opslaan
    ▼
[Spatial Join via PostGIS]
    │  ST_Within(cluster.centroid, gebieden.geom)
    │  → gebieden.id (CBS buurt-code) koppelen als gebied_id
    │  → gemeente_code koppelen
    ▼
[Aggregatie — tabel: ov_haltes_per_buurt]
    │  GROUP BY gebied_id, jaar
    │  COUNT per ov_type uit clusters (niet ruwe nodes!)
    │  (staging tabel voor verificatie)
    ▼
[INSERT INTO gebied_data — per indicator per buurt]
    │  5 indicatoren × N buurten records
    │  gebied_id       = gebieden.id (bijv. 'BU00980903')
    │  indicator_uuid  = indicatoren.uuid (opgezocht via code)
    │  waarde          = COUNT clusters
    │  jaar            = 2026
    │  scenario_id     = 'current'          ← verplicht voor Kompas!
    │  bron            = 'OpenStreetMap / Overpass API 2026'
    ▼
[Verificatie]
    │  Verwacht na deduplicatie:
    │    Fryslân: ~800-1000 clusters (uit 3062 ruwe nodes)
    │    Groningen: ~600-800 clusters
    │    Drenthe: ~450-600 clusters
```

---

## Implementatieplan (fasering)

### Fase 1 — Database schema (`ETL/OV/migrations/schema_v14_ov_haltes.sql`)

```sql
-- Tabel 1: Ruwe OSM nodes
CREATE TABLE IF NOT EXISTS ov_haltes (
    osm_id        BIGINT PRIMARY KEY,
    naam          TEXT,
    ov_type       TEXT,
    osm_pt_type   TEXT,  -- platform/stop_position/station/ferry_terminal/bus_stop
    network       TEXT,
    ref           TEXT,
    gemeente_code TEXT,
    gebied_id     TEXT,  -- = gebieden.id (CBS buurt-code bijv. BU00980903)
    provincie     TEXT CHECK (provincie IN ('FR','GR','DR')),
    geom          geometry(Point, 28992),
    peildatum     DATE DEFAULT CURRENT_DATE,
    tags          JSONB
);
CREATE INDEX IF NOT EXISTS idx_ov_haltes_geom     ON ov_haltes USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_ov_haltes_gebied   ON ov_haltes(gebied_id);
CREATE INDEX IF NOT EXISTS idx_ov_haltes_type     ON ov_haltes(ov_type);

-- Tabel 2: Gededupliceerde clusters (indicator-basis)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE TABLE IF NOT EXISTS ov_halte_clusters (
    cluster_id    UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    naam          TEXT,
    ov_type       TEXT,
    n_platforms   INT DEFAULT 1,
    gebied_id     TEXT,  -- = gebieden.id (CBS buurt-code)
    gemeente_code TEXT,
    provincie     TEXT CHECK (provincie IN ('FR','GR','DR')),
    geom          geometry(Point, 28992),
    peildatum     DATE DEFAULT CURRENT_DATE
);
CREATE INDEX IF NOT EXISTS idx_ov_clusters_geom   ON ov_halte_clusters USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_ov_clusters_gebied ON ov_halte_clusters(gebied_id);

-- Tabel 3: Staging/verificatie per buurt per jaar
CREATE TABLE IF NOT EXISTS ov_haltes_per_buurt (
    gebied_id       TEXT,   -- = gebieden.id
    jaar            INT,
    totaal_haltes   INT DEFAULT 0,
    haltes_bus      INT DEFAULT 0,
    haltes_tram     INT DEFAULT 0,
    haltes_trein    INT DEFAULT 0,
    haltes_veerboot INT DEFAULT 0,
    haltes_metro    INT DEFAULT 0,
    PRIMARY KEY (gebied_id, jaar)
);
```

### Fase 2 — Overpass query module (`ETL/OV/overpass_client.py`)

**Library: OSMPythonTools 0.3.6** (geïnstalleerd en gevalideerd 2026-06-03)

```python
from OSMPythonTools.overpass import Overpass

overpass = Overpass()  # ingebouwde caching

PROVINCIES = {
    "FR": "Fryslân",
    "GR": "Groningen",
    "DR": "Drenthe",
}

# OSMPythonTools voegt zelf [out:json][timeout:N] toe — geen eigen headers
QUERY_TEMPLATE = '''
    area["name"="{naam}"]["admin_level"="4"]["boundary"="administrative"]->.prov;
    (
      node["public_transport"~"platform|station|halt"](area.prov);
      node["highway"="bus_stop"](area.prov);
      node["railway"~"station|halt"](area.prov);
      node["amenity"="ferry_terminal"](area.prov);
    );
    out body;
'''
```

**OV-type bepaling (definitief na live data-analyse):**

```python
def bepaal_ov_type(tags: dict) -> str:
    """
    Bepaal OV-type op basis van OSM tags.
    Volgorde: trein > veerboot > tram > metro > bus (default)
    Live data: 85% van Fryslân nodes is 'platform' zonder extra type-tags → bus fallback.
    """
    rw = tags.get("railway", "")
    hw = tags.get("highway", "")
    amenity = tags.get("amenity", "")

    if rw in ("station", "halt"):
        return "trein"
    if amenity == "ferry_terminal" or tags.get("ferry") == "yes":
        return "veerboot"
    if rw == "tram_stop" or tags.get("tram") == "yes":
        return "tram"
    if tags.get("subway") == "yes":
        return "metro"
    if hw == "bus_stop" or tags.get("bus") == "yes":
        return "bus"
    # Fallback: platform zonder extra tags → bus (NL-standaard, gevalideerd in live data)
    return "bus"
```

### Fase 2b — Spatial clustering (deduplicatie)

```python
from scipy.spatial import cKDTree
import numpy as np
import pandas as pd

def cluster_platforms(df: pd.DataFrame, radius_m: float = 75.0) -> pd.DataFrame:
    """
    Groepeert platform-nodes met dezelfde naam en ov_type die binnen radius_m meter
    van elkaar liggen tot één cluster. Geeft DataFrame terug met centroid per cluster.

    Achtergrond: Leeuwarden Busstation heeft 15 identiek genaamde stop_positions
    op het busstation-terrein. Met radius=75m clusteren die tot 1 locatie.
    """
    clusters = []
    used = set()
    coords = df[['x_rd', 'y_rd']].values  # EPSG:28992 coördinaten in meters
    namen = df['naam'].values
    typen = df['ov_type'].values

    tree = cKDTree(coords)

    for i in range(len(df)):
        if i in used:
            continue
        # Zoek alle nodes binnen radius
        idxs = tree.query_ball_point(coords[i], radius_m)
        # Filter: zelfde naam EN zelfde ov_type
        zelfde = [j for j in idxs if namen[j] == namen[i] and typen[j] == typen[i]]
        cluster_coords = coords[zelfde]
        centroid = cluster_coords.mean(axis=0)
        clusters.append({
            'naam': namen[i],
            'ov_type': typen[i],
            'n_platforms': len(zelfde),
            'x_rd': centroid[0],
            'y_rd': centroid[1],
        })
        used.update(zelfde)

    return pd.DataFrame(clusters)
```

### Fase 3 — Hoofdscript (`ETL/OV/import_ov_haltes.py`)

```
Argumenten:
  --provincies FR,GR,DR   (default: alle drie)
  --peildatum 2026-06-01  (default: vandaag)
  --dry-run               (print resultaten, schrijf niet naar DB)
  --skip-schema           (schema al aangemaakt, sla over)

Stappen in het script:
  1. Schema aanmaken (tenzij --skip-schema)
  2. Per provincie:
     a. Overpass query uitvoeren via OSMPythonTools (caching automatisch)
     b. Elementen parsen → pandas DataFrame
     c. OV-type bepalen per halte (bepaal_ov_type)
     d. Coördinaten transformeren: WGS84 → EPSG:28992 via pyproj
     e. INSERT in ov_haltes (ON CONFLICT DO UPDATE)
  3. Spatial join via PostGIS:
       UPDATE ov_haltes h
       SET gebied_id     = g.id,
           gemeente_code = g.gemeente_code
       FROM gebieden g
       WHERE ST_Within(h.geom, g.geom)
         AND g.gebiedstype_id = (SELECT id FROM gebiedstypes WHERE code = 'buurt')
  4. Spatial clustering per provincie + ov_type → INSERT in ov_halte_clusters
  5. Spatial join clusters → gebied_id koppelen (zelfde patroon als stap 3)
  6. Aggregatie berekenen → INSERT in ov_haltes_per_buurt
  7. gebied_data vullen per indicator UUID (5 indicatoren × N buurten)
  8. Verificatie-rapport afdrukken
```

### Fase 4a — Indicator seed (`ETL/OV/seed_ov_indicatoren.json`)

Dit bestand wordt toegevoegd en geladen via het bestaande `etl_03_seed_indicatoren.py` script.

```json
[
  {
    "naam": "Aantal OV-haltes (totaal)",
    "code": "OV_HALTES_TOTAAL",
    "eenheid": "aantal",
    "score_type": "+/+",
    "bron": "OpenStreetMap / Overpass API",
    "omschrijving": "Totaal unieke OV-haltelocaties per buurt (bus, trein, tram, veerboot gecombineerd). Gededupliceerd op naam + 75m proximity."
  },
  {
    "naam": "Aantal bushaltes",
    "code": "OV_HALTES_BUS",
    "eenheid": "aantal",
    "score_type": "+/+",
    "bron": "OpenStreetMap / Overpass API",
    "omschrijving": "Unieke bushaltelocaties per buurt (gededupliceerd op naam + 75m). Bron: OSM highway=bus_stop en public_transport=platform."
  },
  {
    "naam": "Aantal treinhaltes",
    "code": "OV_HALTES_TREIN",
    "eenheid": "aantal",
    "score_type": "+/+",
    "bron": "OpenStreetMap / Overpass API",
    "omschrijving": "Treinstationlocaties per buurt (OSM railway=station). Eén node per stationscomplex."
  },
  {
    "naam": "Aantal tramhaltes",
    "code": "OV_HALTES_TRAM",
    "eenheid": "aantal",
    "score_type": "+/+",
    "bron": "OpenStreetMap / Overpass API",
    "omschrijving": "Tramhaltelocaties per buurt (OSM railway=tram_stop of tram=yes)."
  },
  {
    "naam": "Aantal veerboten",
    "code": "OV_HALTES_VEERBOOT",
    "eenheid": "aantal",
    "score_type": "+/+",
    "bron": "OpenStreetMap / Overpass API",
    "omschrijving": "Veerboot-aanleglocaties per buurt (OSM amenity=ferry_terminal). Inclusief Waddenveer en IJsselmeerveer."
  }
]
```

**Laden:** `python ETL/local/etl_03_seed_indicatoren.py --bestand ETL/OV/seed_ov_indicatoren.json`

### Fase 4b — Kompas-koppeling (toevoegen aan `init_data/kompas/kompas_hierarchie.csv`)

De OV-indicatoren horen thuis onder **Kwaliteit fysieke leefomgeving → Verkeer → Bereikbaarheid en parkeren** (naast de bestaande CBS-indicatoren "Afstand treinstation" en "Afstand treinknooppunt").

**5 rijen toevoegen aan `kompas_hierarchie.csv`:**

```csv
Kwaliteit fysieke leefomgeving,Verkeer,Bereikbaarheid en parkeren,Aantal OV-haltes (totaal),J,OpenStreetMap,Aantal OV-haltes (totaal)
Kwaliteit fysieke leefomgeving,Verkeer,Bereikbaarheid en parkeren,Aantal bushaltes,J,OpenStreetMap,Aantal bushaltes
Kwaliteit fysieke leefomgeving,Verkeer,Bereikbaarheid en parkeren,Aantal treinhaltes,J,OpenStreetMap,Aantal treinhaltes
Kwaliteit fysieke leefomgeving,Verkeer,Bereikbaarheid en parkeren,Aantal tramhaltes,J,OpenStreetMap,Aantal tramhaltes
Kwaliteit fysieke leefomgeving,Verkeer,Bereikbaarheid en parkeren,Aantal veerboten,J,OpenStreetMap,Aantal veerboten
```

**Laden:** `python ETL/local/etl_05_import_kompas.py` (herbouwt de Kompas-hiërarchie volledig)

### Fase 5 — gebied_data INSERT (correct patroon)

```python
def schrijf_naar_gebied_data(cur, gebied_id: str, indicator_uuid: str,
                              waarde: int, jaar: int, bron: str):
    """
    Schrijf één indicatorwaarde naar gebied_data.
    Let op:
      - 'gebied_id' is gebieden.id (bijv. 'BU00980903'), NIET 'buurt_code'
      - scenario_id = 'current' is verplicht voor zichtbaarheid in Kompas
    """
    cur.execute("""
        INSERT INTO gebied_data
            (gebied_id, indicator_uuid, waarde, jaar, scenario_id, bron)
        VALUES (%s, %s, %s, %s, 'current', %s)
        ON CONFLICT (gebied_id, indicator_uuid, jaar, scenario_id)
        DO UPDATE SET
            waarde     = EXCLUDED.waarde,
            updated_at = CURRENT_TIMESTAMP
    """, (gebied_id, indicator_uuid, waarde, jaar, bron))


# Hulpfunctie: indicator UUID ophalen op basis van code
def get_indicator_uuid(cur, code: str) -> str:
    cur.execute("SELECT uuid FROM indicatoren WHERE code = %s", (code,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Indicator '{code}' niet gevonden — seed eerst via etl_03_seed_indicatoren.py")
    return str(row[0])
```

---

## Technische randvoorwaarden

### Dependencies (alle aanwezig ✅)

| Package | Status | Gebruik |
|---------|--------|---------|
| `OSMPythonTools` | ✅ v0.3.6 | Overpass API met caching |
| `geopandas` | ✅ v1.1.2 | GeoDataFrame + CRS transformatie |
| `pyproj` | ✅ v3.7.2 | EPSG:4326 → EPSG:28992 |
| `scipy` | ✅ v1.17.1 | cKDTree voor 75m spatial clustering |
| `psycopg2` | ✅ Aanwezig | PostgreSQL INSERT |
| `sqlalchemy` | ✅ Aanwezig | DB connectie patroon |

> Alle dependencies geverifieerd op 2026-06-03. Geen extra `pip install` nodig.

### PostGIS spatial join: `gebieden` (niet `buurten`)

De tabel heet **`gebieden`** (niet `buurten`). De buurt-code zit in `gebieden.id`.

```sql
-- Correct patroon (gevalideerd op de DB):
UPDATE ov_haltes h
SET gebied_id     = g.id,
    gemeente_code = g.gemeente_code
FROM gebieden g
JOIN gebiedstypes gt ON g.gebiedstype_id = gt.id
WHERE ST_Within(h.geom, g.geom)
  AND gt.code = 'buurt';  -- of het exacte type-ID voor buurten
```

### Rate limiting Overpass API

- OSMPythonTools handelt retries intern af
- Voeg `time.sleep(3)` toe tussen provincies (beleefdheidspause)
- Bij aanhoudende timeouts: gebruik `overpass.query(..., timeout=90)`

---

## Verificatie na import

```sql
-- 1. Haltes per provincie en type (ruwe data)
SELECT provincie, ov_type, COUNT(*) AS n_nodes
FROM ov_haltes
GROUP BY provincie, ov_type
ORDER BY provincie, n_nodes DESC;

-- 2. Clusters per provincie en type (na deduplicatie)
SELECT provincie, ov_type, COUNT(*) AS n_clusters, AVG(n_platforms) AS gem_platforms
FROM ov_halte_clusters
GROUP BY provincie, ov_type
ORDER BY provincie, n_clusters DESC;
-- Verwacht: Fryslân bus ~700-900, trein ~20-25, veerboot ~6-10

-- 3. Buurten zonder koppeling
SELECT COUNT(*) AS niet_gekoppeld
FROM ov_halte_clusters
WHERE gebied_id IS NULL;
-- Verwacht: 0

-- 4. gebied_data gevuld per indicator
SELECT i.code, COUNT(*) AS n_buurten, AVG(gd.waarde) AS gem_waarde
FROM gebied_data gd
JOIN indicatoren i ON gd.indicator_uuid = i.uuid
WHERE i.code LIKE 'OV_HALTES%'
  AND gd.scenario_id = 'current'
  AND gd.jaar = 2026
GROUP BY i.code
ORDER BY i.code;

-- 5. Spot check IJsselmeerkust: haltes in Makkum-omgeving
SELECT c.naam, c.ov_type, c.n_platforms
FROM ov_halte_clusters c
JOIN gebieden g ON c.gebied_id = g.id
WHERE g.gemeente_code = '1900'  -- Súdwest-Fryslân
ORDER BY c.ov_type, c.naam;
```

---

## Uitvoervolgorde (als alles gebouwd is)

```bash
# Stap 1: Schema aanmaken
psql $DATABASE_URL -f ETL/OV/migrations/schema_v14_ov_haltes.sql

# Stap 2: Indicatoren seeden
cd ETL/local
python etl_03_seed_indicatoren.py --bestand ../OV/seed_ov_indicatoren.json

# Stap 3: Kompas-hiërarchie bijwerken (voeg 5 rijen toe aan CSV, daarna herbouwen)
python etl_05_import_kompas.py

# Stap 4: ETL uitvoeren
cd /mnt/f/VSCode_Projects/D-OmniTwin
source .venv/bin/activate
python ETL/OV/import_ov_haltes.py --provincies FR,GR,DR --dry-run
python ETL/OV/import_ov_haltes.py --provincies FR,GR,DR

# Stap 5: Verificatie
psql $DATABASE_URL -c "SELECT i.code, COUNT(*) FROM gebied_data gd JOIN indicatoren i ON gd.indicator_uuid=i.uuid WHERE i.code LIKE 'OV%' GROUP BY i.code;"
```

---

## Bestandsstructuur

```
ETL/OV/
├── BOUWPLAN.md                          ← dit bestand
├── STRATEGIE_ANALYSE.md                 ← deduplicatie- en meetobjectstrategie
├── INDICATOR_STRUCTUUR_ANALYSE.md       ← gap-analyse indicator-infrastructuur
├── onderzoek_osm_structuur.py           ← onderzoeksscript (reproduceerbaar)
├── seed_ov_indicatoren.json             ← [te maken Fase 4a] indicator definities
├── overpass_client.py                   ← [te maken Fase 2] Overpass query module
├── import_ov_haltes.py                  ← [te maken Fase 3] Hoofdscript
└── migrations/
    └── schema_v14_ov_haltes.sql         ← [te maken Fase 1] DB schema
```

---

## Relatie met Sprint 18 (Track A3)

Deze ETL levert de data voor de bereikbaarheidsindicator die in de NM-001 gap-analyse als ontbrekend is geïdentificeerd. Na succesvolle import kunnen de volgende testcases worden bijgewerkt:
- **TC-06-001 fase 2, stap 4-6** — bereikbaarheid OV IJsselmeerkust
- **TC-07-001** — vergelijkende buurtanalyse Makkum/Workum/Koudum bereikbaarheid

---

## Referenties

- [OV Haltes NL Actueel — Provincie Zuid-Holland (nationaalgeoregister.nl)](https://www.nationaalgeoregister.nl/geonetwork/srv/api/records/1e0876db-6991-46a5-8ff0-cc01495d9345)
- [OSMPythonTools op PyPI](https://pypi.org/project/OSMPythonTools/)
- [OSM Public Transport tagging schema](https://wiki.openstreetmap.org/wiki/Public_transport)
- [Geofabrik downloads Nederland](https://download.geofabrik.de/europe/netherlands.html) — alternatieve bron (PBF bestanden per provincie)
- [`STRATEGIE_ANALYSE.md`](./STRATEGIE_ANALYSE.md) — volledig onderbouwde strategiekeuzes
- [`INDICATOR_STRUCTUUR_ANALYSE.md`](./INDICATOR_STRUCTUUR_ANALYSE.md) — gap-analyse indicator-infrastructuur

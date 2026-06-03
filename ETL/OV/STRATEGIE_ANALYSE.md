# OSM OV-Haltes: Strategieanalyse (definitief)

**Aangemaakt:** 2026-06-03  
**Status:** ✅ Definitief — gebaseerd op live Overpass-data  
**Gevalideerd met:** OSMPythonTools 0.3.6 via overpass-api.de  
**Data peildatum:** 2026-06-03

---

## Uitkomsten live data-analyse

### Leeuwarden CS (500m radius) — 60 nodes

| Naam | Type | Aantal nodes | Wat het is |
|------|------|--------------|------------|
| `"Busstation"` | platform | 17 | Elk busperron apart genummerd |
| `"Leeuwarden, Busstation"` | stop_position | 15 | Exacte stopplaats per bus |
| `"Leeuwarden"` | station + stop_position | 8 | 1 stationsgebouw + 7 treinperrons |
| `"Blokhuisplein"` | platform | 2 | Halte met richtingen A/B |
| ... | | | |
| **Totaal bus** | | **52** | |
| **Totaal trein** | | **8** | |

**Conclusie Leeuwarden:** Een naïeve tel geeft 60 nodes voor 1 knooppunt. Een beleidsadviseur zou zeggen: "Leeuwarden heeft 1 busstation, 1 treinstation." De ETL moet dit juist zien te schalen.

---

### Fryslân totaal — 3062 nodes

| Tag | Waarde | Aantal | % |
|-----|--------|--------|---|
| `public_transport` | `platform` | 2611 | 85% |
| `public_transport` | `stop_position` | 357 | 12% |
| `public_transport` | `station` | 56 | 2% |
| `public_transport` | `halt` | 1 | 0% |
| `railway` | `stop` | 31 | — |
| `railway` | `station` | 22 | — |

**Cruciale bevinding:** `platform` is de dominante tag (85%), **niet** `stop_position`.  
Dit is tegengesteld aan de aanname in v1 van het bouwplan.

**Namen-analyse:**
- 98% van nodes heeft een `name` tag → naam-gebaseerde deduplicatie is mogelijk
- 6% heeft een `ref` tag → ref alleen niet geschikt als identifier
- 1118 namen komen >1x voor (deduplicatie noodzakelijk)
- Generieke namen: "Busstation" (66x), "Station" (23x), "Centrum" (21x) → deze komen voor in **meerdere steden + meerdere platforms per locatie**

---

## Definitieve strategie: wat is een "halte"?

### Meetobject: Unieke wachtlocatie (platform-gebaseerd)

**Keuze: `platform` als primaire node-type**

Rationale:
- `platform` = de plek waar de reiziger staat en wacht → dit is de **opstaplocatie** in praktische zin
- `stop_position` = technische positie van het voertuig op het wegtracé → infrastructuur, niet relevant voor beleidsgebruik
- In Nederland taggen OSM-mappers 85% van haltes als `platform`, niet als `stop_position`

**Definitie "één halte":**
> Een unieke wachtlocatie gedefinieerd door: *naam + OV-type + geografische cluster (≤ 75m radius)*

Dit geeft:
- Leeuwarden CS busstation: "Leeuwarden, Busstation" → 1 locatie (15 stop_positions clusteren samen)
- Leeuwarden CS trein: "Leeuwarden" + `railway=station` → 1 locatie
- Afzonderlijke bushaltes verspreid door de stad → elk hun eigen cluster

### Deduplicatie-algoritme

```
Stap 1: Verzamel alle platform-nodes (public_transport=platform)
Stap 2: Voeg toe: railway=station nodes (één per complex)
Stap 3: Voeg toe: amenity=ferry_terminal nodes
Stap 4: Voeg toe: highway=bus_stop ALLEEN als geen platform binnen 75m (legacy-data)
Stap 5: Voeg toe: stop_position ALLEEN als geen platform binnen 75m (onvolledig getagde gebieden)

Deduplicatie (op Stap 1):
  - Input: alle platform-nodes met (naam, lat, lon, ov_type)
  - Cluster: nodes met ZELFDE naam + ZELFDE ov_type + onderlinge afstand ≤ 75m → 1 record
  - Output: 1 rij per cluster met:
      * canonical_naam = naam (meest voorkomend in cluster)
      * cluster_centroid = gemiddelde lat/lon
      * n_platforms = aantal nodes in cluster (te bewaren als extra veld)
      * ov_type = bus/trein/tram/veerboot/overig
```

### OV-type bepaling (geordende prioriteit)

```python
def bepaal_ov_type(tags: dict) -> str:
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
    # Fallback: platform zonder verdere tags → bus (veruit het meest voorkomend in FR/GR/DR)
    if tags.get("public_transport") in ("platform", "stop_position"):
        return "bus"
    return "overig"
```

---

## Verwachte aantallen na deduplicatie (schatting)

| Provincie | Ruwe nodes | Verwacht na deduplicatie | Onderbouwing |
|-----------|-----------|--------------------------|--------------|
| Fryslân | ~3062 | ~800 – 1000 | Factor 3-4 door platform+stop_position dubbeling + busstation-platforms |
| Groningen | ~2000 | ~600 – 800 | Vergelijkbare stedelijkheid |
| Drenthe | ~1500 | ~450 – 600 | Ruraler, minder dubbeling |
| **Totaal** | **~6500** | **~1850 – 2400** | |

---

## Waddenveer: Meenemen als `veerboot`

**Beslissing: Ja, meenemen.**

Veerdiensten in Fryslân die in OSM staan:
- Makkum ↔ Enkhuizen (`amenity=ferry_terminal` in Makkum) → **direct relevant voor IJsselmeerkust-casus**
- Harlingen ↔ Terschelling / Vlieland (Rederij Doeksen)
- Holwerd ↔ Ameland (Wagenborg)
- Stavoren ↔ Enkhuizen (ook relevant voor Zuidwest-Fryslân)

De Overpass area-query voor Fryslân pakt de eilanden correct mee (ze vallen bestuurlijk onder Fryslân). Veerboten tellen als aparte categorie `veerboot` in `ov_haltes_per_buurt`.

---

## Historische data: definitieve keuze

**Beslissing: Starten met peildatum 2026, GTFS als tijdreeks later.**

| Aanpak | Status |
|--------|--------|
| Overpass Attic (historisch OSM) | ⏳ Later — netwerk-issue WSL, complex queries |
| GTFS historisch (9292 open data) | 📋 Gepland als Fase 2 ETL/OV (`import_ov_gtfs.py`) |
| Peildatum 2026 (nu) | ✅ Start hiermee |

De `ov_haltes_per_buurt` tabel heeft al een `jaar` kolom (PRIMARY KEY op `buurt_code, jaar`) — tijdreeks later toevoegen is triviaal.

---

## OSMPythonTools: definitief als API-library

**OSMPythonTools 0.3.6** is geïnstalleerd en werkt (`pip install OSMPythonTools`).

**Voordelen t.o.v. raw `requests`:**
- ✅ Ingebouwde caching (cache-dir `~/.cache/OSMPythonTools`) — herhaalde queries gratis
- ✅ Automatische timeout/error handling
- ✅ Werkt door de WSL netwerk-blokkering die `requests.post` tegenhoudt
- ✅ Eenvoudige API: `overpass.query(ql_string, timeout=60).elements()`

**Gebruik in ETL:**
```python
from OSMPythonTools.overpass import Overpass
overpass = Overpass()

result = overpass.query('''
    area["name"="Fryslân"]["admin_level"="4"]["boundary"="administrative"]->.prov;
    (
      node["public_transport"~"platform|station|halt"](area.prov);
      node["highway"="bus_stop"](area.prov);
      node["railway"~"station|halt"](area.prov);
      node["amenity"="ferry_terminal"](area.prov);
    );
    out body;
''', timeout=60)

for element in result.elements():
    naam = element.tag('name')
    lat, lon = element.lat(), element.lon()
    tags = {k: element.tag(k) for k in ['public_transport','railway','highway','bus','train','ferry','operator','ref']}
```

---

## Bijgewerkte database-structuur

### Tabel `ov_haltes` (ruwe nodes — alles bewaren)

| Kolom | Type | Beschrijving |
|-------|------|-------------|
| `osm_id` | BIGINT PK | OSM node ID |
| `naam` | TEXT | `name` tag |
| `ov_type` | TEXT | `bus/trein/tram/veerboot/metro/overig` |
| `osm_pt_type` | TEXT | `platform/stop_position/station/ferry_terminal/bus_stop` — ruw uit OSM |
| `network` | TEXT | Operator/netwerk |
| `ref` | TEXT | Halte-referentienummer |
| `buurt_code` | TEXT | Via ST_Within join |
| `gemeente_code` | TEXT | Via ST_Within join |
| `provincie` | TEXT | `FR/GR/DR` |
| `geom` | geometry(Point, 28992) | Rijksdriehoek |
| `peildatum` | DATE | Query-datum |
| `tags` | JSONB | Volledige tag-set |

### Tabel `ov_halte_clusters` (gededupliceerde locaties — de indicator-basis)

| Kolom | Type | Beschrijving |
|-------|------|-------------|
| `cluster_id` | UUID PK | Gegenereerd |
| `naam` | TEXT | Canonical naam |
| `ov_type` | TEXT | `bus/trein/tram/veerboot` |
| `n_platforms` | INT | Aantal OSM nodes in cluster |
| `buurt_code` | TEXT | Via centroid ST_Within |
| `geom` | geometry(Point, 28992) | Centroid van cluster |
| `peildatum` | DATE | |

### Tabel `ov_haltes_per_buurt` (aggregaat per buurt — Kompas-indicator)

| Kolom | Type | Beschrijving |
|-------|------|-------------|
| `buurt_code` | TEXT | |
| `jaar` | INT | |
| `totaal_haltes` | INT | Alle unieke clusters |
| `haltes_bus` | INT | |
| `haltes_trein` | INT | |
| `haltes_tram` | INT | |
| `haltes_veerboot` | INT | |
| `haltes_metro` | INT | |
| PRIMARY KEY | `(buurt_code, jaar)` | |

---

## Samenvatting strategische beslissingen

| Vraag | Beslissing | Onderbouwing |
|-------|-----------|--------------|
| **Primaire tag** | `platform` (niet `stop_position`) | 85% van FR-data is platform; dat is waar passagiers staan |
| **Deduplicatie** | Naam + OV-type + 75m spatial clustering | Leeuwarden CS: 15 stop_positions → 1 cluster |
| **Generieke namen** | Dedupliceren op locatie, niet op naam | "Busstation" 66x in FR = ~10 bussatons + meerdere platforms per locatie |
| **Waddenveer** | Meenemen als `veerboot` | Bestuurlijk Fryslân, relevant voor IJsselmeerkust-casus |
| **Historische data** | Eén peildatum 2026 nu; GTFS tijdreeks later | Schema ondersteunt al meerdere jaren |
| **API-library** | OSMPythonTools 0.3.6 | Werkend vanuit WSL, ingebouwde caching |
| **Peiljaar** | 2026 | Prima voorstel |

---

## Volgende stap: Bouw de ETL

Strategie is volledig bepaald. De ETL kan nu gebouwd worden:

1. `ETL/OV/migrations/schema_v14_ov_haltes.sql` — DB schema
2. `ETL/OV/import_ov_haltes.py` — Hoofdscript (Overpass → cluster → PostGIS → Kompas)

Zie bijgewerkt `BOUWPLAN.md` voor implementatiedetails.

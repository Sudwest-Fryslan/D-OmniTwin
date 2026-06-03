# Analyse: Indicatoren-opbouwstructuur vs. OV ETL Bouwplan

**Aangemaakt:** 2026-06-03  
**Doel:** Gap-analyse tussen de bestaande indicator-infrastructuur en wat het OV bouwplan beschrijft

---

## 1. De werkelijke indicator-infrastructuur (uit DB)

### Kern: 4 lagen

```
kompas_configuraties      ← "Volledig Kompas" (de container)
    └── kompas_titels     ← Niveau 1: "Kwaliteit fysieke leefomgeving"
         └── kompas_themas     ← Niveau 2: "Verkeer"
              └── kompas_onderdelen  ← Niveau 3: "Bereikbaarheid en parkeren"
                   └── kompas_indicator_mapping  ← Niveau 4: koppeling aan indicator
                            ↓
                        indicatoren (uuid, naam, code, eenheid, ...)
                            ↓
                        gebied_data (gebied_id, indicator_uuid, waarde, jaar)
                            ↓
                        gebieden (id = buurt_code bijv. "BU00980903")
```

### Tabel `indicatoren` — verplichte en gebruikte kolommen

| Kolom | Type | Verplicht | Gebruikte waarden |
|-------|------|-----------|------------------|
| `uuid` | UUID | **NOT NULL** | `gen_random_uuid()` |
| `naam` | VARCHAR | **NOT NULL** | "Afstand treinknooppunt" |
| `code` | VARCHAR | NULL | `"CBS_NETTOARBEIDSPARTICIPATIE"` |
| `eenheid` | VARCHAR | NULL | `"aantal"`, `"%"`, `"m"` |
| `omschrijving` | TEXT | NULL | Volledige beschrijving |
| `bron` | VARCHAR | NULL | `"CBS Kerncijfers wijken en buurten"` |
| `score_type` | VARCHAR | NULL | `"+/+"`, `"-/+"`, `"+/-"`, `"-/-"`, `"-=-"` |
| `status` | VARCHAR | NULL (default `'O'`) | `'O'` (open/actief), `'C'` (gesloten/inactief) |
| `interpretatie_logica` | VARCHAR | NULL (default `'pos_is_pos'`) | `'pos_is_pos'` |
| `waarde_type` | VARCHAR | NULL (default `'decimal'`) | `'decimal'` |
| `categorie` | VARCHAR | NULL | Vrij veld (weinig gebruikt) |

**Niet aanwezig** in de DB: `dimensie`, `sub_dimensie`, `thema` — dit zijn Kompas-hiërarchie velden die **niet** in `indicatoren` zelf staan, maar in de aparte `kompas_*` tabellen.

### Tabel `gebied_data` — zo wordt een waarde opgeslagen

```sql
INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, bron, scenario_id)
VALUES ('BU00980903', '<uuid>', 75.0, 2023, 'CBS Kerncijfers 2023', 'current');
```

| Kolom | Type | Verplicht | Toelichting |
|-------|------|-----------|-------------|
| `gebied_id` | VARCHAR | **NOT NULL** | = `gebieden.id` = CBS buurt_code (bijv. `BU00980903`) |
| `indicator_uuid` | UUID | **NOT NULL** | FK naar `indicatoren.uuid` |
| `waarde` | NUMERIC | NULL | De meetwaarde |
| `jaar` | INT | NULL | Peiljaar |
| `scenario_id` | VARCHAR | NULL (default `'current'`) | Altijd `'current'` voor actuele data |
| `bron` | VARCHAR | NULL | Bronomschrijving |

### Tabel `gebieden` — de geografische eenheid

| Kolom | Toelichting |
|-------|-------------|
| `id` | = CBS-code bijv. `BU00980903` (buurt), `WK009809` (wijk), `GM0098` (gemeente) |
| `naam` | Naam van het gebied |
| `gebiedstype_id` | UUID → `gebiedstypes.id` |
| `gemeente_code` | CBS gemeente code |

> **Belangrijk:** `gebieden.id` is de primaire sleutel EN de CBS-code. In `gebied_data` heet dit veld `gebied_id`. **Niet** `buurt_code`.

### Kompas CSV-formaat (voor koppeling)

```csv
Title,Thema,Onderdeel,Indicator,Indicator actueel,Bron,Indicator SWF
Kwaliteit fysieke leefomgeving,Verkeer,Bereikbaarheid en parkeren,Afstand treinstation,J,"CBS",Afstand tot treinstations totaal
```

De OV-haltes indicatoren horen thuis onder:
- **Title:** `Kwaliteit fysieke leefomgeving`  
- **Thema:** `Verkeer`  
- **Onderdeel:** `Bereikbaarheid en parkeren`

---

## 2. Wat staat er in het OV Bouwplan — en wat klopt niet?

### ❌ Verschil 1: `buurt_code` ≠ `gebied_id`

**Bouwplan zegt:**
```sql
-- In ov_haltes en ov_halte_clusters:
buurt_code TEXT
gemeente_code TEXT
```

**Werkelijkheid:**
In `gebied_data` heet het `gebied_id` en de waarde is de CBS-buurt_code (`BU00980903`).  
In `gebieden` heet het `id`.

**Impact:** De spatial join moet een `gebied_id` opleveren dat overeenkomt met `gebieden.id`. In onze OV-tabellen mogen we de kolom `buurt_code` noemen (intern), maar bij het invoegen in `gebied_data` moet het veld `gebied_id` zijn.

✅ **Oplossing:** Intern `buurt_code` gebruiken in `ov_haltes`/`ov_halte_clusters`, maar bij de `gebied_data` insert expliciet mappen: `gebied_id = buurt_code`.

---

### ❌ Verschil 2: `ov_haltes_per_buurt` is niet nodig als tussenstap

**Bouwplan zegt:**  
Data gaat via `ov_haltes_per_buurt` → Kompas.

**Werkelijkheid:**  
Alle bestaande ETL's slaan data direct in `gebied_data` op per indicator. Er is **geen** aggregatietabel als tussenstap. Het patroon is:

```
ruwe data → berekening → INSERT INTO gebied_data (één rij per buurt per indicator)
```

Elke OV-type indicator (`haltes_bus`, `haltes_trein`, etc.) wordt **een aparte indicator** in de `indicatoren` tabel met een eigen UUID.

**Impact:** `ov_haltes_per_buurt` kan bestaan als staging/cache tabel, maar is strikt genomen niet nodig. Het alternatief — én het patroon dat de rest volgt — is:

```
ov_halte_clusters
    └── GROUP BY buurt + ov_type
         └── → INSERT INTO gebied_data per indicator per buurt
```

✅ **Oplossing:** `ov_haltes_per_buurt` behouden als handige staging tabel voor verificatie, maar de **definitieve** Kompas-koppeling loopt via `gebied_data`.

---

### ❌ Verschil 3: Kompas-koppeling niet uitgewerkt in bouwplan

**Bouwplan zegt:**  
`→ Kompas koppeling via gebied_data`  
Maar beschrijft **niet** hoe de indicator in de Kompas-hiërarchie wordt opgenomen.

**Werkelijkheid:**  
Een indicator is pas zichtbaar in het Kompas na twee stappen:

1. **`indicatoren` seed** — maak de indicator aan in de `indicatoren` tabel via `etl_03_seed_indicatoren.py` of direct SQL
2. **`kompas_indicator_mapping`** — koppel de indicator aan een `onderdeel_id` in de hiërarchie via de CSV (`etl_05_import_kompas.py`)

De OV-indicatoren moeten dus ook:
- Aangemeld worden in `indicatoren_seed.json` (of apart JSON-bestand)
- Opgenomen worden in `kompas_hierarchie.csv` onder `Verkeer > Bereikbaarheid en parkeren`

---

### ❌ Verschil 4: Bouwplan mist `score_type` en `eenheid` per indicator

**Bouwplan zegt:**  
```json
{ "code": "OV_HALTES_BUS", "naam": "Aantal bushaltes", ... }
```

**Werkelijkheid — verplichte velden per indicator:**
```json
{
  "naam": "Aantal bushaltes",
  "code": "OV_HALTES_BUS",
  "eenheid": "aantal",
  "score_type": "+/+",
  "bron": "OpenStreetMap / Overpass API 2026",
  "omschrijving": "Aantal unieke bushalte-locaties (gededupliceerd op 75m) per buurt"
}
```

`score_type` is verplicht voor scoring in het Kompas. Voor haltes is dit altijd `"+/+"` (meer is beter).

---

### ✅ Wat wél klopt

- De `gebieden.id` structuur (CBS-codes `BU*`) — bouwplan gebruikt dit correct als join-sleutel
- `jaar` kolom in `gebied_data` — bouwplan benoemt peiljaar correct
- `scenario_id = 'current'` — standaard voor actuele data
- Gebruik van `uuid` als koppelsleutel — correct

---

## 3. Correcte volledige dataflow (bijgewerkt)

```
[Overpass API via OSMPythonTools]
    │
    ▼
[ov_haltes] — ruwe OSM nodes per provincie
    │
    ▼
[ov_halte_clusters] — gededupliceerde wachtlocaties (naam + 75m clustering)
    │  PostGIS spatial join: ST_Within(cluster.centroid, gebieden.geom)
    │  → koppelt gebieden.id (= CBS buurt_code) aan elk cluster
    │
    ▼
[Aggregatie per buurt per ov_type]
    │  GROUP BY gebieden_id, ov_type → COUNT clusters
    │
    ▼
[ov_haltes_per_buurt] — staging tabel (optioneel, voor verificatie)
    │
    ▼
[INSERT INTO gebied_data]
    │  Per indicator (bus/trein/tram/veerboot/totaal) × per buurt:
    │
    │  gebied_id       = gebieden.id (bijv. 'BU00980903')
    │  indicator_uuid  = indicatoren.uuid voor die OV-type
    │  waarde          = COUNT clusters
    │  jaar            = 2026
    │  scenario_id     = 'current'
    │  bron            = 'OpenStreetMap / Overpass API 2026'
    │
    ▼
[indicatoren_seed.json / SQL]
    │  5 indicatoren aanmaken:
    │  OV_HALTES_BUS, OV_HALTES_TREIN, OV_HALTES_TRAM,
    │  OV_HALTES_VEERBOOT, OV_HALTES_TOTAAL
    │
    ▼
[kompas_hierarchie.csv — 5 rijen toevoegen]
    │  Title: Kwaliteit fysieke leefomgeving
    │  Thema: Verkeer
    │  Onderdeel: Bereikbaarheid en parkeren
    │  Indicator: Aantal bushaltes / treinhaltes / etc.
    │  Indicator actueel: J
    │  Bron: OpenStreetMap
    │
    ▼
[Zichtbaar in Kompas]
```

---

## 4. Benodigde aanpassingen aan het bouwplan

### A. Indicator definitie (nieuw toe te voegen aan bouwplan)

```json
[
  {
    "naam": "Aantal OV-haltes (totaal)",
    "code": "OV_HALTES_TOTAAL",
    "eenheid": "aantal",
    "score_type": "+/+",
    "bron": "OpenStreetMap / Overpass API",
    "omschrijving": "Totaal unieke OV-haltelocaties per buurt (bus, trein, tram, veerboot gecombineerd)"
  },
  {
    "naam": "Aantal bushaltes",
    "code": "OV_HALTES_BUS",
    "eenheid": "aantal",
    "score_type": "+/+",
    "bron": "OpenStreetMap / Overpass API",
    "omschrijving": "Unieke bushaltelocaties per buurt (gededupliceerd op naam + 75m)"
  },
  {
    "naam": "Aantal treinhaltes",
    "code": "OV_HALTES_TREIN",
    "eenheid": "aantal",
    "score_type": "+/+",
    "bron": "OpenStreetMap / Overpass API",
    "omschrijving": "Treinstation-locaties per buurt (railway=station)"
  },
  {
    "naam": "Aantal tramhaltes",
    "code": "OV_HALTES_TRAM",
    "eenheid": "aantal",
    "score_type": "+/+",
    "bron": "OpenStreetMap / Overpass API",
    "omschrijving": "Tramhaltelocaties per buurt"
  },
  {
    "naam": "Aantal veerboten",
    "code": "OV_HALTES_VEERBOOT",
    "eenheid": "aantal",
    "score_type": "+/+",
    "bron": "OpenStreetMap / Overpass API",
    "omschrijving": "Veerboot-aanleglocaties per buurt (amenity=ferry_terminal)"
  }
]
```

### B. Kompas CSV-rijen (toevoegen aan `kompas_hierarchie.csv`)

```csv
Kwaliteit fysieke leefomgeving,Verkeer,Bereikbaarheid en parkeren,Aantal OV-haltes (totaal),J,OpenStreetMap,Aantal OV-haltes (totaal)
Kwaliteit fysieke leefomgeving,Verkeer,Bereikbaarheid en parkeren,Aantal bushaltes,J,OpenStreetMap,Aantal bushaltes
Kwaliteit fysieke leefomgeving,Verkeer,Bereikbaarheid en parkeren,Aantal treinhaltes,J,OpenStreetMap,Aantal treinhaltes
Kwaliteit fysieke leefomgeving,Verkeer,Bereikbaarheid en parkeren,Aantal tramhaltes,J,OpenStreetMap,Aantal tramhaltes
Kwaliteit fysieke leefomgeving,Verkeer,Bereikbaarheid en parkeren,Aantal veerboten,J,OpenStreetMap,Aantal veerboten
```

### C. Juiste gebied_data INSERT (correctie bouwplan)

```python
# CORRECT — gebruik 'gebied_id' niet 'buurt_code'
cur.execute("""
    INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, scenario_id, bron)
    VALUES (%s, %s, %s, %s, 'current', %s)
    ON CONFLICT (gebied_id, indicator_uuid, jaar, scenario_id)
    DO UPDATE SET waarde = EXCLUDED.waarde, updated_at = CURRENT_TIMESTAMP
""", (buurt_id, indicator_uuid, count, 2026, 'OpenStreetMap / Overpass API 2026'))
```

---

## 5. Overzicht: bouwplan aanpassingen nodig

| # | Punt | Status in bouwplan | Actie |
|---|------|--------------------|-------|
| 1 | `gebied_id` ipv `buurt_code` in gebied_data | ❌ Fout | Corrigeer insert SQL |
| 2 | Indicator seed JSON (5 indicatoren) | ❌ Ontbreekt | Aanmaken als `ETL/OV/seed_ov_indicatoren.json` |
| 3 | Kompas CSV-rijen (5 rijen) | ❌ Ontbreekt | Toevoegen aan `init_data/kompas/kompas_hierarchie.csv` |
| 4 | `score_type` + `eenheid` per indicator | ❌ Ontbreekt | Opnemen in seed JSON |
| 5 | Staging tabel `ov_haltes_per_buurt` | ✅ Handig bewaren | Bewaren voor verificatie, niet als Kompas-koppeling |
| 6 | Kompas-hiërarchieplaatsing beschrijven | ❌ Ontbreekt | `Verkeer > Bereikbaarheid en parkeren` |
| 7 | `scenario_id = 'current'` in gebied_data | ❌ Ontbreekt | Toevoegen aan insert |

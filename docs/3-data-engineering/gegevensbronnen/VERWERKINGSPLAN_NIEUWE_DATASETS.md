# Verwerkingsplan: Nieuwe Datasets

**Datum:** 10-02-2026  
**Doel:** Opstellen van technische richtlijnen voor ETL pipelines, kwaliteitscontroles, en import procedures voor 4 nieuwe datasets.

---

## Overzicht Datasets

| Dataset | Prioriteit | Import Status | ETL Complexiteit |
|---------|-----------|---------------|------------------|
| EP-Online Energielabels | 🔴🔴 ZEER HOOG | ✅ Voltooid | HOOG (streaming 7.9GB XML) |
| CBS PC6 Koppeling | 🔴 HOOG | ✅ Operationeel | LAAG (JSON lookup) |
| BAG Fryslân | 🔴 MEDIUM-HOOG | ⏳ Gepland | MEDIUM (spatial join) |
| Postcodegebieden | 🟡 MEDIUM | ⏳ Gepland | LAAG (direct import) |

---

## 1. EP-Online Energielabels (✅ Voltooid)

### Import Strategie

**Status:** Volledig operationeel sinds 09-02-2026

**Script:** `scripts/import_energielabels.py`

**Techniek:** Streaming XML Parser (iterparse)
- **Rationale:** Bestand te groot voor memory (7.9GB), streaming voorkomt OOM errors
- **Performance:** ~45 minuten voor volledige import

### ETL Pipeline

```python
# Vereenvoudigde flow (zie import_energielabels.py voor volledige code)

1. Load PC6 → Buurt mapping (JSON)
   - File: data/cbs_pc6_huisnr_buurt/pc6_buurt_mapping.json
   - In-memory lookup dict: {"8888AA": "00981101", ...}

2. Load Buurt → Gebied_ID mapping (SQL)
   - Query: SELECT id, REPLACE(id, 'BU', '') FROM gebieden WHERE id LIKE 'BU%'
   - Translates CBS code (00981101) → gebied_id (BU00981101)

3. Stream parse XML (iterparse)
   FOR EACH <Pandcertificaat>:
     - Extract: Postcode, Energieklasse, Gebouwklasse
     - Filter: Gebouwklasse == 'W' (woonfunctie)
     - Lookup: Postcode → Buurtcode → Gebied_ID
     - Aggregate: Collect energieklasse values per buurt
     - Clear element (memory management)

4. Aggregate per buurt
   - Calculate: AVG(numeric_value of definitive labels) → gemiddeld label
   - Calculate: COUNT(definitive labels) → aantal definitieve labels
   - Calculate: COUNT(provisional labels) → aantal voorlopige labels
   - Calculate: COUNT(total labels) → totaal aantal labels

5. Insert/Update database
   - Table: gebied_data
   - Indicators: 'Gemiddeld energielabel', 'Aantal energielabels (definitief)', 'Aantal energielabels (voorlopig)', 'Aantal energielabels (totaal)'
   - Year: 2025, Scenario: current
```

### Kwaliteitscontroles

**Pre-Import:**
- [ ] XML bestand valide (schema check met xmllint)
- [ ] PC6 mapping file aanwezig en niet leeg
- [ ] Gebieden tabel heeft buurten (count > 900)

**Post-Import:**
```sql
-- 1. Coverage check: Hoeveel buurten hebben data?
SELECT COUNT(DISTINCT gebied_id) AS buurten_met_data
FROM gebied_data
WHERE indicator_uuid IN (
  SELECT uuid FROM indicatoren WHERE naam = 'Gemiddeld energielabel'
);
-- Expected: ~900 van 965 Friese buurten (93%)

-- 2. Value range check: Labels tussen A++++ en G?
SELECT MIN(waarde), MAX(waarde), AVG(waarde)
FROM gebied_data gd
JOIN indicatoren i ON i.uuid = gd.indicator_uuid
WHERE i.naam = 'Gemiddeld energielabel';
-- Expected: MIN ~2.5 (A++), MAX ~7.0 (E), AVG ~4.5 (B-C)

-- 3. Count sanity: Totaal labels klopt met verwachting?
SELECT SUM(waarde) AS totaal_labels
FROM gebied_data gd
JOIN indicatoren i ON i.uuid = gd.indicator_uuid
WHERE i.naam = 'Aantal energielabels';
-- Expected: ~167,000
```

### Update Procedure (Halfjaarlijks)

**Trigger:** RVO publiceert nieuwe dataset (februari + augustus)

**Stappen:**
```bash
# 1. Download nieuwe XML
cd data/ep-online/
wget https://www.ep-online.nl/.../ep_online_vYYYYMMDD.zip
unzip ep_online_vYYYYMMDD.zip -d extracted_vYYYYMMDD_v4_xml/

# 2. Update script path
nano scripts/import_energielabels.py
# Line 233: update xml_path to new file

# 3. Run import
python scripts/import_energielabels.py
# Expected runtime: 40-50 minuten

# 4. Verify results
psql -U omnitwin_user -d omnitwin_db -f scripts/verify_ep_online.sql

# 5. Update metadata
UPDATE indicatoren 
SET bron = 'RVO EP-Online YYYYMM'
WHERE code IN ('gemiddeld_energielabel', 'aantal_energielabels');
```

---

## 2. CBS PC6-Huisnummer Koppeling (✅ Operationeel)

### Import Strategie

**Status:** JSON mapping reeds in gebruik, geen aparte import nodig

**Gebruik:** Lookup file gebruikt door andere import scripts

### ETL Pipeline

**Simpel:** Load JSON in geheugen tijdens runtime

```python
import json

def load_pc6_mapping():
    with open('data/cbs_pc6_huisnr_buurt/pc6_buurt_mapping.json', 'r') as f:
        return json.load(f)  # {"PC6": "BuurtCode8"}

# Usage in andere scripts:
pc6_map = load_pc6_mapping()
buurtcode = pc6_map.get("8888AA")  # Returns "00981101" or None
```

### Update Procedure (Jaarlijks)

**Trigger:** CBS publiceert nieuwe indeling (augustus)

**Script:** `scripts/generate_pc6_mapping.py` (nieuw aan te maken)

```python
#!/usr/bin/env python3
"""
Generate PC6 → Buurt JSON mapping from CBS CSV export
"""
import csv
import json
import os

def main():
    csv_path = 'data/cbs_pc6_huisnr_buurt/extracted/pc6hnr20250801_gwb.csv'
    output_path = 'data/cbs_pc6_huisnr_buurt/pc6_buurt_mapping.json'
    
    mapping = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            pc6 = row['PC6']
            buurt = row['Buurt2025']
            if pc6 and buurt:
                mapping[pc6] = buurt
    
    # Write JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Mapping created: {len(mapping)} PC6 codes")

if __name__ == "__main__":
    main()
```

**Stappen:**
```bash
# 1. Download CBS dataset (jaarlijks augustus)
wget https://www.cbs.nl/.../cbs-pc6huisnr20260801_buurt.zip
unzip -d data/cbs_pc6_huisnr_buurt/extracted/

# 2. Generate JSON mapping
python scripts/generate_pc6_mapping.py

# 3. Validate coverage
python -c "import json; m=json.load(open('data/cbs_pc6_huisnr_buurt/pc6_buurt_mapping.json')); print(f'{len(m)} PC6 codes')"
# Expected: ~430,000 codes

# 4. Restart services (cache refresh)
systemctl restart omnitwin-backend
```

---

## 3. BAG Fryslân (⏳ Te Implementeren)

### Import Strategie

**Aanpak:** Selectieve import + direct aggregeren (geen tussentabel)

**Rationale:**
- ✅ Efficiënt: Vermijd opslag van 280k+ individuele VBO's, sla alleen aggregaties op
- ✅ Privacy: Geen adres-niveau data in database
- ⚠️ Trade-off: Moeilijker om later drill-down te doen naar objectniveau

**Alternatief (toekomstig):** Full import in aparte schema `bag`, queries on-demand

### ETL Pipeline (Script: `import_bag_indicators.py`)

```python
#!/usr/bin/env python3
"""
Import BAG Fryslân indicators via spatial join + aggregation
"""
import geopandas as gpd
import psycopg2
from sqlalchemy import create_engine

def get_db_engine():
    return create_engine('postgresql://user:pass@localhost/omnitwin_db')

def import_bag_indicators():
    engine = get_db_engine()
    
    # 1. Load BAG Verblijfsobjecten
    vbo = gpd.read_file('data/bag_frl/cleaned_bag_data_verblijfsobject.gpkg')
    vbo = vbo[vbo['status'] == 'Verblijfsobject in gebruik']  # Filter actieve VBO's
    
    # 2. Load Buurten geometrie
    buurten = gpd.read_file('data/geometrie/buurt_geometrie.gpkg')
    
    # 3. Spatial Join: VBO → Buurt
    vbo_buurt = gpd.sjoin(vbo, buurten, how='left', predicate='within')
    
    # 4. Aggregate per buurt: Gebruiksdoel mix
    functie_mix = vbo_buurt.groupby('gebied_id').apply(lambda df: {
        'pct_woonfunctie': (df['gebruiksdoel'].str.contains('woonfunctie').sum() / len(df) * 100),
        'pct_winkel': (df['gebruiksdoel'].str.contains('winkelfunctie').sum() / len(df) * 100),
        'pct_kantoor': (df['gebruiksdoel'].str.contains('kantoorfunctie').sum() / len(df) * 100),
        'diversiteit_index': len(df['gebruiksdoel'].unique()) / len(df)  # 0-1 scale
    }).apply(pd.Series)
    
    # 5. Load BAG Panden + join met buurten
    panden = gpd.read_file('data/bag_frl/bag_data_bag_pand.gpkg')
    panden_buurt = gpd.sjoin(panden, buurten, how='left', predicate='within')
    
    # 6. Aggregate per buurt: Bouwjaar
    bouwjaar_agg = panden_buurt.groupby('gebied_id').agg({
        'bouwjaar': ['mean', lambda x: (x < 1945).sum() / len(x) * 100]
    }).reset_index()
    bouwjaar_agg.columns = ['gebied_id', 'gem_bouwjaar', 'pct_voor_1945']
    
    # 7. Insert to database
    for idx, row in functie_mix.iterrows():
        gebied_id = idx
        # Insert indicator: % woonfunctie
        insert_gebied_data(engine, gebied_id, 'pct_woonfunctie', row['pct_woonfunctie'])
        # ... repeat for other indicators
    
    for idx, row in bouwjaar_agg.iterrows():
        insert_gebied_data(engine, row['gebied_id'], 'gemiddeld_bouwjaar', row['gem_bouwjaar'])
        insert_gebied_data(engine, row['gebied_id'], 'pct_voor_1945', row['pct_voor_1945'])
    
    print("✅ BAG indicators imported")

def insert_gebied_data(engine, gebied_id, indicator_code, waarde):
    conn = engine.raw_connection()
    cur = conn.cursor()
    
    # Get indicator UUID
    cur.execute("SELECT uuid FROM indicatoren WHERE code = %s", (indicator_code,))
    ind_uuid = cur.fetchone()[0]
    
    # Upsert
    cur.execute("""
        INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, bron)
        VALUES (%s, %s, %s, 2025, 'Kadaster BAG')
        ON CONFLICT (gebied_id, indicator_uuid, jaar, scenario_id)
        DO UPDATE SET waarde = EXCLUDED.waarde, bron = EXCLUDED.bron
    """, (gebied_id, ind_uuid, waarde))
    
    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    import_bag_indicators()
```

### Kwaliteitscontroles

**Pre-Import:**
```python
# Validatie scripts
def validate_bag_data():
    vbo = gpd.read_file('data/bag_frl/cleaned_bag_data_verblijfsobject.gpkg')
    
    # 1. Check geometrie volledigheid
    assert vbo['geometry'].isna().sum() == 0, "Missing geometries!"
    
    # 2. Check bouwjaar range
    panden = gpd.read_file('data/bag_frl/bag_data_bag_pand.gpkg')
    invalid_years = panden[(panden['bouwjaar'] < 1600) | (panden['bouwjaar'] > 2026)]
    print(f"⚠️  {len(invalid_years)} panden met onrealistisch bouwjaar")
    
    # 3. Check oppervlakte range
    invalid_opp = vbo[(vbo['oppervlakte'] <= 0) | (vbo['oppervlakte'] > 10000)]
    print(f"⚠️  {len(invalid_opp)} VBO's met extreme oppervlakte")
    
    print("✅ Validation complete")
```

**Post-Import:**
```sql
-- 1. Coverage: Alle buurten hebben BAG data?
SELECT COUNT(DISTINCT gebied_id) AS buurten_met_bag
FROM gebied_data gd
JOIN indicatoren i ON i.uuid = gd.indicator_uuid
WHERE i.code IN ('gemiddeld_bouwjaar', 'pct_woonfunctie');
-- Expected: ~965 (100% Friese buurten)

-- 2. Sanity check: Gemiddeld bouwjaar realistisch?
SELECT AVG(waarde), MIN(waarde), MAX(waarde)
FROM gebied_data gd
JOIN indicatoren i ON i.uuid = gd.indicator_uuid
WHERE i.code = 'gemiddeld_bouwjaar';
-- Expected: AVG ~1965, MIN ~1800, MAX ~2025

-- 3. Percentage voor 1945 logisch?
SELECT AVG(waarde), MAX(waarde)
FROM gebied_data gd
JOIN indicatoren i ON i.uuid = gd.indicator_uuid
WHERE i.code = 'pct_voor_1945';
-- Expected: AVG ~30%, MAX ~90% (historische kernen)
```

### Update Procedure

**Frequentie:** Maandelijks (via PDOK automatisch)

**Stappen:**
```bash
# Option A: Handmatig PDOK download
wget https://download.pdok.nl/...bag_fryslân_latest.zip
unzip -d data/bag_frl/

# Option B: GeoPandas direct van WFS (toekomstig)
# python scripts/download_bag_pdok_wfs.py --provincie Fryslân

# Re-run import
python scripts/import_bag_indicators.py

# Verify changes
psql -c "SELECT COUNT(*) FROM gebied_data WHERE bron = 'Kadaster BAG' AND updated_at > NOW() - INTERVAL '1 day'"
```

---

## 4. Bestuurlijke Postcodegebieden (⏳ Te Implementeren)

### Import Strategie

**Doel 1:** PC4 als nieuw gebiedstype
**Doel 2:** Provinciegrens als visuele laag (geen data)

### ETL Pipeline (Script: `import_postcodegebieden.py`)

```python
#!/usr/bin/env python3
"""
Import Postcode Gebieden + Provincie grens
"""
import geopandas as gpd
from sqlalchemy import create_engine

def import_pc4_gebieden():
    engine = create_engine('postgresql://user:pass@localhost/omnitwin_db')
    
    # 1. Add PC4 gebiedstype if not exists
    conn = engine.raw_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO gebiedstypes (id, naam, niveau)
        VALUES ('PC4', 'Postcode 4-cijfers', 3)
        ON CONFLICT (id) DO NOTHING
    """)
    conn.commit()
    
    # 2. Load PC4 gebieden
    pc4 = gpd.read_file('data/bestuurlijke_postcode_gebieden/postcodegebieden_fryslan.gpkg')
    
    # 3. Transform to WGS84 for GeoJSON export (frontend gebruikt EPSG:4326)
    pc4_wgs84 = pc4.to_crs(epsg=4326)
    
    # 4. Insert to gebieden tabel (inclusief gemeente_naam voor zoekingang!)
    for idx, row in pc4.iterrows():
        gebied_id = f"PC4{row['pc4']}"  # e.g. "PC48888"
        gemeente_naam = row.get('gemeente_naam', 'Onbekend')  # Vereist veld!
        
        cur.execute("""
            INSERT INTO gebieden (id, naam, gebiedstype_id, parent_id, geometry, centroid)
            VALUES (%s, %s, 'PC4', ST_GeomFromText(%s, 28992), ST_Centroid(ST_GeomFromText(%s, 28992)))
            ON CONFLICT (id) DO UPDATE SET
              geometry = EXCLUDED.geometry,
              centroid = EXCLUDED.centroid
        """, (gebied_id, f"PC4 {row['pc4']}", row['geometry'].wkt, row['geometry'].wkt))
    
    conn.commit()
    print(f"✅ Imported {len(pc4)} PC4 gebieden")
    
    # 5. Provinciegrens: Aparte tabel (geen gebiedstype)
    provincie = gpd.read_file('data/bestuurlijke_postcode_gebieden/Provincie_Fryslân.gpkg')
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kaartlagen (
          id TEXT PRIMARY KEY,
          naam TEXT,
          geometry GEOMETRY(MultiPolygon, 28992),
          layer_type TEXT
        )
    """)
    
    cur.execute("""
        INSERT INTO kaartlagen (id, naam, geometry, layer_type)
        VALUES ('provincie_fryslan', 'Provincie Fryslân', ST_GeomFromText(%s, 28992), 'boundary')
        ON CONFLICT (id) DO UPDATE SET geometry = EXCLUDED.geometry
    """, (provincie.iloc[0]['geometry'].wkt,))
    
    conn.commit()
    print("✅ Provincie grens toegevoegd als kaartlaag")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    import_pc4_gebieden()
```

### Kwaliteitscontroles

**Post-Import:**
```sql
-- 1. Check aantal PC4 gebieden
SELECT COUNT(*) FROM gebieden WHERE gebiedstype_id = 'PC4';
-- Expected: ~950

-- 2. Check geometrie validiteit
SELECT COUNT(*) FROM gebieden 
WHERE gebiedstype_id = 'PC4' AND NOT ST_IsValid(geometry);
-- Expected: 0

-- 3. Provincie grens bestaat?
SELECT * FROM kaartlagen WHERE id = 'provincie_fryslan';
-- Expected: 1 row
```

### Frontend Integratie (PC4 Aggregatieniveau + Provinciegrens)

**Belangrijke Ontwerpkeuze:**
- **GEEN** PC4-code zoekfunctie
- **WEL** Aggregatieniveau dropdown (Buurt/Wijk/PC4/Gemeente)
- **Zoekingang blijft:** Gemeentenaam (zoals nu)
- **Werking:** Gebruiker selecteert gemeente → API parameter `aggregatie_niveau=PC4` → kaart toont PC4 polygonen

**Kaart Component Wijziging:**

```javascript
// static/js/kaart.js

// Aggregatieniveau dropdown (NIET PC4 search!)
<select id="aggregatie-niveau" onchange="updateMapAggregation()">
  <option value="BU">Buurt (standaard)</option>
  <option value="WK">Wijk</option>
  <option value="PC4">Postcode 4-cijfers</option>
  <option value="GM">Gemeente</option>
</select>

// Gemeente search blijft ongewijzigd
<input type="text" id="gemeente-search" placeholder="Zoek gemeente..." />

// API call met aggregatie parameter
async function loadKaartData(gemeente_id, aggregatie_niveau) {
  const response = await fetch(
    `/api/gebiedsmonitor/kaart?gemeente_id=${gemeente_id}&aggregatie_niveau=${aggregatie_niveau}`
  );
  // Returns PC4 polygonen binnen gemeente indien aggregatie_niveau=PC4
}

// Province boundary layer
async function loadProvinceBoundary() {
  const response = await fetch('/api/kaartlagen/provincie_fryslan');
  const geojson = await response.json();
  
  const boundaryLayer = new deck.GeoJsonLayer({
    id: 'provincie-boundary',
    data: geojson,
    filled: false,
    stroked: true,
    lineWidthMinPixels: 2,
    getLineColor: [0, 0, 0, 255],  // Black border
    getLineWidth: 2
  });
  
  // Add to deck layers (bottom layer)
  deckgl.setProps({
    layers: [boundaryLayer, ...otherLayers]
  });
}
```

---

## Cross-Dataset Integratie

### Use Case 1: BAG Huishoudens als Denominateur voor EP-Online

**Doel:** Bereken percentage huishoudens met energielabel

**Query:**
```sql
CREATE VIEW v_energielabel_coverage AS
SELECT 
  b.id AS gebied_id,
  b.naam AS gebied_naam,
  
  -- BAG: Aantal woningen (VBO's met woonfunctie)
  (SELECT COUNT(*) 
   FROM bag_verblijfsobjecten vbo 
   WHERE ST_Within(vbo.geometry, b.geometry) AND vbo.woonfunctie = true
  ) AS huishoudens_bag,
  
  -- EP-Online: Aantal labels
  (SELECT waarde 
   FROM gebied_data gd 
   JOIN indicatoren i ON i.uuid = gd.indicator_uuid
   WHERE gd.gebied_id = b.id AND i.code = 'aantal_energielabels'
  ) AS aantal_labels,
  
  -- Percentage
  ROUND(
    (SELECT waarde FROM gebied_data gd JOIN indicatoren i ON i.uuid = gd.indicator_uuid
     WHERE gd.gebied_id = b.id AND i.code = 'aantal_energielabels') 
    / NULLIF((SELECT COUNT(*) FROM bag_verblijfsobjecten vbo 
              WHERE ST_Within(vbo.geometry, b.geometry) AND vbo.woonfunctie = true), 0) 
    * 100, 
  1) AS pct_met_energielabel

FROM gebieden b
WHERE b.gebiedstype_id = 'BU';
```

**Nieuwe Indicator:** "Percentage met energielabel (BAG basis)"
- Code: `pct_energielabel_bag`
- Bron: combinatie RVO + BAG
- Interpretatie: +=+ (hoger = betere coverage)

### Use Case 2: PC4 Aggregaties voor Regionale Vergelijking

**Doel:** Aggregeer buurt-data naar PC4 niveau

**Query:**
```sql
-- Bereken gemiddeld bouwjaar per PC4
INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, bron)
SELECT 
  pc4.id AS gebied_id,
  (SELECT uuid FROM indicatoren WHERE code = 'gemiddeld_bouwjaar') AS indicator_uuid,
  AVG(gd_buurt.waarde) AS waarde,
  2025 AS jaar,
  'Aggregatie van buurt-niveau' AS bron
FROM gebieden pc4
JOIN gebieden buurt ON ST_Intersects(buurt.centroid, pc4.geometry)
JOIN gebied_data gd_buurt ON gd_buurt.gebied_id = buurt.id
JOIN indicatoren i ON i.uuid = gd_buurt.indicator_uuid
WHERE pc4.gebiedstype_id = 'PC4' 
  AND buurt.gebiedstype_id = 'BU'
  AND i.code = 'gemiddeld_bouwjaar'
GROUP BY pc4.id;
```

---

## Error Handling & Logging

### Logging Standaard

**Alle import scripts moeten loggen:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/import_{dataset_name}_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Usage
logger.info(f"Starting import of {dataset_name}")
logger.warning(f"Skipped {count} invalid records")
logger.error(f"Failed to process: {error}")
```

### Error Recovery

**Transactional Imports:**
```python
def import_with_rollback():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # ... import logic ...
        
        conn.commit()
        logger.info("✅ Import successful")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Import failed, rolled back: {e}")
        raise
    finally:
        conn.close()
```

---

## Next Steps

1. ✅ EP-Online: Operationeel, halfjaarlijkse update procedure
2. ✅ CBS PC6: Operationeel, jaarlijkse update script aanmaken
3. ⏳ BAG: Ontwikkel `import_bag_indicators.py` (Sprint 5C)
4. ⏳ Postcode: Ontwikkel `import_postcodegebieden.py` + frontend laag

---

**Document Versie:** 1.0  
**Laatste Update:** 10-02-2026

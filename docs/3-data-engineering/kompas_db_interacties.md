# Kompas Visualisatie: Gegevensstroom en Database Interacties

Dit document beschrijft de volledige technische flow van hoe de Sunburst/Kompas visualisatie in de applicatie tot stand komt, van frontend requests tot onderliggende SQL iteraties in de database. De doelgroep is data scientists en backend developers die de kompas logica of scoringmechanismen verder willen uitbreiden.

---

## 1. De Stroom: Frontend naar Database

### A. Initialisatie (Welke kompassen zijn er?)
1. **Frontend:** Roept in de achtergrond `/api/kompas/configuraties` aan om de beschikbare tabbladen te maken.
2. **Backend (`routers/kompas.py`):** Routeert naar `KompasService.get_configuraties()`.
3. **Database Query:** Query op de view `v_kompas_config_stats` om meta-informatie (naam, icoon, actieve status, aantal elementen) op te halen.

### B. Interactie (Klik op een wijk/buurt)
*Dit is de zwaarste en meest cruciale bewerking in de flow.*
1. **Frontend:** Muisklik op de 3D deck.gl kaart verstuurt het geselecteerde `gebied_id` naar het component. Het component haalt de actieve kompas-configuratie op via `/api/kompas/{config_id}/gebied/{gebied_id}`.
2. **Backend (`KompasService.get_gebied_kompas`):** Dit proces is opgedeeld in vier gerelateerde sub-queries:

    - **B1. Gebied Verificatie:** Snelle query naar de tabel `gebieden` om te kijken of de locatie geldig is.
    - **B2. De Boomstructuur (`v_kompas_hierarchie`):** Haalt de volledige taxonomie van het kompas op via de `v_kompas_hierarchie` view. Deze query levert een platte lijst op met de vier niveaus: (Titel → Thema → Onderdeel → Indicator). De Python service bouwt dit om naar een geneste D3.js boomstructuur.
    - **B3. De Waarden ophalen (Lateral Join):** Het systeem moet voor de meer dan honderd indicatoren in de taxonomie de *meest recente waarde* per indicator voor dit specifieke gebied_id ophalen. Er wordt gezocht via een list op `kompas_indicator_mapping` gejoind met de `gebied_data` tabel:
      ```sql
      LEFT JOIN LATERAL (
          SELECT waarde, jaar FROM gebied_data
          WHERE indicator_uuid = i.uuid AND gebied_id = :gebied_id
          ORDER BY jaar DESC LIMIT 1
      ) gd ON true
      ```
    - **B4. De Kleuring / Thresholds Berekenen:** De applicatie gebruikt procentuele klassen (bins) om gebieden eerlijk te vergelijken. Om te weten of een gebied de kleur Groen (top 12.5%) of Rood (laagste 12.5%) krijgt, wordt er voor *elke* gerelateerde indicator een bulk-berekening uitgevoerd via PostgreSQL's ingebouwde aggregatie functies:
      ```sql
      PERCENTILE_CONT(ARRAY[0.125, 0.25, 0.375, ... , 0.875]) WITHIN GROUP (ORDER BY waarde)
      ```
      Deze data gaat door de `KompasScoringService` genaamd de "8-bin Scale", gecombineerd met regels (is hoger beter `+/+` of slechter `+/-`?).

### C. Detailweergave & Historie (Trendlijn)
Wanneer een gebruiker op het laagste niveau van de zon (Indicator) klikt:
1. **Frontend:** Vraagt om data via `/api/kompas/{config_id}/history/{gebied_id}/{indicator_uuid}`
2. **Database:** Simpel tabel-filter rechtstreeks op `gebied_data` besteld op `jaar ASC` om alle historische meetmomenten als tijdreeks aan de UI Line Chart te geven.

---

## 2. Tabel & Views Afhankelijkheden (De Datamodellen)

Als je wijzigingen doorvoert aan het Kompas, is het cruciaal om het ERD effect te snappen. De visuele weergave is afhankelijk van dit exacte gelaagde model:

* **Tafels (Hiërarchie Creatie):**
  - `kompas_configuraties` (Master node)
  - `kompas_titels` (De binnenste ring in de sunburst chart)
  - `kompas_themas` (Brede categorie-ring)
  - `kompas_onderdelen` (Diepere opsplitsing)
  - `kompas_indicator_mapping` (De brug: Koppelt een specifieke indicator uit de globale `indicatoren` tabel aan een `onderdeel`)

* **Datatabellen (Inzichten Berekening):**
  - `gebied_data` (Bevat miljoen(+) rijen met `{gebied_id, indicator_uuid, jaar, waarde}`)
  - `indicatoren` (Definities & metadata eenheden)
  - `kompas_indicator_scoring_regels` (Geeft aan met welke logica en eenheid deze in de weging meedoen en of een hogere waarde groen of rood moet kleuren)

* **Hoofd-Views (Optimalisatie Lagen):**
  - `v_kompas_hierarchie`: De centrale view die alle tabellen hierboven (minus gebied_data) omtovert tot één makkelijk in te lezen taxonomie per `config_id`. *Als je theorie toevoegt aan de DB schema's, zul je deze view in `data/schema_latest.sql` mee moeten wijzigen!*

---

## 3. De Sunburst Transformatie (Van Plat SQL naar D3.js Boom)

D3.js (gebruikt in de frontend voor de Sunburst) kan niet omgaan met platte lijsten (SQL rows). Het vereist een strikte hiërarchische JSON structuur met `name` en een `children` array voor elke ring (knoop) tot aan het diepste niveau (blatt).
De backend (via de `_build_tree_from_rows` method in `kompas_service.py`) fungeert hier als parser en groepeert de platte rij resultaten (uit `v_kompas_hierarchie`) direct om in deze verwachting.

### Python Transformatie Basis (Pseudo-Logica)
De code groepeert de tabulaire data naar geneste dictionary objecten: de Titel ("Binnenste ring") bevat een dictionary van Thema's, die Onderdelen bevat, die op hun beurt lists van Indicator UUID's ("Buitenste ring") bevatten:

```python
# Stap 1: Flat SQL view rijen groeperen per niveau (Titel -> Thema -> Onderdeel)
titels = {}
for row in rows:
    # Controleer de binnenste ring (Titel Level)
    if row.titel_id not in titels:
        titels[row.titel_id] = {
            "name": row.titel_naam,
            "type": "titel",
            "color": row.titel_kleur,
            "children": {}  # Tijdelijk dict voor snelle ID-mapping
        }
    
    # ... Geneste ifs voor Thema & Onderdeel grouping (overgeslagen voor beknoptheid) ...
    
    # Zodra de buitenste ring (Indicator Level) bereikt is:
    if row.indicator_uuid:
        # Navigeer door de zojuist aangemaakte dicts en stop de indicator als "leaf" node:
        titels[row.titel_id]["children"][row.thema_id]["children"][row.onderdeel_id]["children"].append({
            "name": row.indicator_naam,
            "type": "indicator",
            "uuid": str(row.indicator_uuid),
            "value": None,  # Wordt dynamisch gevuld bij de gebied-selectie in Stap B3/B4
            "color": None   
        })

# Stap 2: Recursief omzetten van dicts (gebruikt voor groepering) naar lijsten
# D3.js `d3.hierarchy()` verwacht uitsluitend { "name": "...", "children": [ { ... } ] }
root_children = convert_nested_dicts_to_lists(titels) 

return {
    "name": "Root",
    "type": "root",
    "children": root_children
}
```

### De impact op de Frontend (D3.js)
Dankzij dit exacte data-formaat kan de applicatie in `static/js/kompas.js` direct `d3.hierarchy(data)` en `d3.partition()` over de response aanroepen, zonder client-side overhead. Deze functies berekenen razendsnel en automatisch de hoeken (radial angles) en de diepte van elk 'partje' zonneschijn, waarna de gepaste "color" property uit de JSON rechtstreeks de SVG-paden vult.

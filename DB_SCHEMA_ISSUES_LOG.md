# Database Schema vs API Mismatch Log
**Datum:** 22 April 2026
**Probleem:** Kaart data laadt niet ("Fout bij laden van kaart data") na het selecteren van een indicator in het kompas.

## Samenvatting van het Probleem
Wanneer een gebruiker op een indicator klikt, haalt de frontend de kaart data op via `/api/gebiedsmonitor/kaart/{gebiedstype_id}`. Deze API call resulteert echter in een **HTTP 500 Internal Server Error**.

De onderliggende databasefout is:
`psycopg2.errors.InFailedSqlTransaction: current transaction is aborted, commands ignored until end of transaction block`

## De Root Cause (Oorzaak)
De error `InFailedSqlTransaction` betekent dat een *eerdere* query binnen dezelfde database-transactie is gecrasht, waardoor de hele transactie ongeldig is verklaard door PostgreSQL. Elke volgende query (zoals de `SELECT COUNT(*)` om het totaal te bepalen) klapt er dan automatisch uit.

De query die daadwerkelijk faalt zit in **`services/color_scale_service.py`** (regel ~140, functie `get_visualization_config()`).

Hier wordt de volgende query uitgevoerd:
```sql
SELECT 
    cs.id as schema_id,
    cs.naam as schema_naam,
    cs.colors,
    cs.palette_type,
    cs.classificatie,
    cs.klassen,
    cs.nodata_kleur,
    i.score_type
FROM indicatoren i
LEFT JOIN color_schemas cs ON i.color_schema_id = cs.id
WHERE i.uuid::text = :indicator_uuid AND i.color_schema_id IS NOT NULL
```

### Probleem 1: Ontbrekende Kolommen in `color_schemas`
De code verwacht de kolommen `palette_type`, `classificatie`, `klassen` en `nodata_kleur`.
Als we echter naar `init_data/schema/schema_latest.sql` kijken (rond regel 273), zien we dat de tabel `color_schemas` véél simpeler is opgebouwd en deze kolommen **niet bevat**:

```sql
CREATE TABLE IF NOT EXISTS color_schemas (
    id SERIAL PRIMARY KEY,
    naam VARCHAR(100) UNIQUE NOT NULL,
    beschrijving TEXT,
    colors JSONB NOT NULL,
    is_actief BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```
Omdat de kolommen ontbreken, gooit PostgreSQL een `UndefinedColumn` error.

### Probleem 2: Ontbrekende Tabel `visualisatie_profielen`
Als de eerste query faalt (of geen resultaat oplevert), heeft `color_scale_service.py` een fallback-mechanisme met een tweede query. Deze zoekt in de tabel `visualisatie_profielen` via een `LEFT JOIN`. 
Echter, deze hele tabel (`visualisatie_profielen`) **bestaat nergens** in `schema_latest.sql`.

### Probleem 3: Slecht Transaction Management
De reden dat dit de hele API call laat crashen (ondanks dat er een `try...except` blok om de `get_visualization_config()` query staat), is dat SQLAlchemy in dezelfde open transactie zit als de kaart data opvraag (`get_kaart_data_v2`).
Een PostgreSQL-fout binnen een transactie zorgt ervoor dat de transactie permanent in de "aborted" status schiet. De `try...except` in Python vangt de error af en returnt `None`, maar de PostgreSQL verbinding zelf weigert daarna nog query's uit te voeren totdat er een `ROLLBACK` wordt gedaan. Daardoor knalt de daaropvolgende `SELECT COUNT(*)` query eruit.

## Mogelijke Oplossingsrichtingen
Je geeft aan dat je het DB schema zelf wil oppakken, dus hier zijn de opties:

1. **Database Schema Uitbreiden (Aanbevolen)**: 
   Update `schema_latest.sql` om de `color_schemas` tabel uit te breiden met:
   - `palette_type VARCHAR`
   - `classificatie VARCHAR`
   - `klassen INTEGER`
   - `nodata_kleur VARCHAR`
   Voeg daarnaast ook de `visualisatie_profielen` tabel toe als de logica in `color_scale_service.py` hier echt afhankelijk van is (of verwijder die specifieke query in de code als de tabel obsoleet is).
   
2. **Backend Code Versimpelen**:
   Pas de SQL queries in `services/color_scale_service.py` aan zodat deze alléén de velden ophalen die nu in het schema zitten, en geef `classificatie`, `klassen`, en `nodata_kleur` een vaste fallback-waarde mee in de Python code.

Zodra het database schema in sync is gebracht met de verwachtingen van `color_scale_service.py` (of andersom), zal de `InFailedSqlTransaction` fout verdwijnen en zullen de kaartkleuren bij het klikken op een indicator weer perfect inladen.

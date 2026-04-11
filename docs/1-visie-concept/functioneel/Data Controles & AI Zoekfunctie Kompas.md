# Implementatieplan: Data Controles & AI Zoekfunctie Kompas

Dit plan beschrijft de architectuur en stappen voor de volgende twee hoofdthema's:
1. **Sprint 8F: Data Validatie & Lineage (Controles)**
2. **AI Track: Ontologische Beschrijvingen & Kompas AI Zoekfunctie**

## Doelstellingen

- **Data Lineage:** Precies weten waar data vandaan komt, uit welke tabel, wanneer het voor het laatst is geüpdatet, en of er nieuwe data bij de bron beschikbaar is.
- **Ontologische Beschrijvingen:** Het structureren van indicator metadata in een format dat door AI en semantische zoekalgoritmes begrepen wordt.
- **Slimme Zoekfunctie (Light-Weight AI):** Een zoekbalk voor het Kompas waarmee gebruikers in natuurlijke taal (of via kernwoorden) indicatoren kunnen vinden.

## Proposed Changes

### 1. Data Validatie & Controles (Sprint 8F)
We introduceren velden in de database om de herkomst en actualiteit van data te volgen.

#### Database Baseline
Actuele analyse van de database (`schema_latest.sql` t/m `schema_v8_llm_config.sql`) toont aan dat zowel de `indicatoren` tabel als de `gebied_data` tabel reeds een algemeen `bron` veld bevatten. Dit is echter te generiek.

#### [MODIFY] Database Schema (Nieuwe Migratie: `data/schema_v9_data_lineage.sql`)
- Voeg extra kolommen toe aan `indicatoren` ter uitbreiding van de lineage:
  - `bron_systeem_api` (bijv. 'CBS OData', 'BAG API', 'RIVM Endpoint')
  - `bron_tabel_referentie` (bijv. tabelnaam, OData dataset code of URL endpoint)
  - `laatste_update_bron` (Datum/Timestamp van wanneer de bron data voor het laatst zelf is bijgewerkt)
  - `laatste_check_datum` (Moment dat ons eigen batch-script/service voor het laatst de bron gecontroleerd heeft)
  - `waarde_type` (e.g. float, int, string - ter ondersteuning van the 'waarde' in gebied_data)

#### [NEW] Backend Data Controle Service (`services/data_controle_service.py`)
- Service met functies zoals `check_cbs_updates()`, `check_rivm_updates()` die API's van de bronnen raadplegen en de `laatste_update_bron` vergelijken met de data in onze DB.

#### [MODIFY] Admin Panel (`admin-panel/src/pages/IndicatorenPage.tsx`)
- Toon de 'Data Lineage' metadata per indicator.
- Voeg een knop toe: "Check voor Bron Updates".

---

### 2. AI Track: Ontologische Beschrijvingen & Embeddings

Om de semantische zoekfunctie mogelijk te maken, moeten we de database uitrusten met vectoren.

#### [MODIFY] Database Schema (Vector Support & Governance)
- Voeg kolommen toe aan `indicatoren`:
  - `ontologische_beschrijving` (TEXT): De beschrijving voor AI zoeken.
  - `ontologie_status` (VARCHAR): Status van de beschrijving ('draft', 'beoordeeld_ai', 'goedgekeurd_mens').
  - `ontologie_beoordeeld_door` (VARCHAR): Wie/welke user de beschrijving heeft goedgekeurd.
  - `ontologie_beoordeeld_op` (TIMESTAMP): Datum van menselijke goedkeuring.
- Enable de `pgvector` extensie in PostgreSQL (`CREATE EXTENSION IF NOT EXISTS vector;`).
- Tabel toevoegen `indicator_embeddings` met relatie tot `indicatoren.uuid` en een vector kolom voor de embedding (bijv. `embedding vector(384)` voor compacte sentence transformers).

#### [NEW] AI Verrijkingsscript (`scripts/ai/genereer_ontologie.py`)
- Python script dat de huidige indicatornaam, categorie en beschrijving via een lokale LLM (Ollama) met de prompt-instructies uit `richtlijn_ontologische_systeemprompts.md` omzet in een formele ontologische beschrijving. Deze krijgen de status 'draft' of 'beoordeeld_ai'.

#### [MODIFY] Admin Panel (`admin-panel/src/pages/IndicatorenPage.tsx`)
- Voeg een workflow toe in het CMS voor de beheerder om "AI Voorstellen" voor ontologische beschrijvingen te reviewen. 
- "Man-in-the-middle" audit-log: beheerder kan de beschrijving aanpassen en vervolgens op "Gezien en Goedgekeurd" klikken, waarna de status op 'goedgekeurd_mens' springt.

#### [NEW] Vectorisatie Script (`scripts/ai/genereer_embeddings.py`)
- Script dat de ontologische beschrijvingen omzet in numerieke vectoren m.b.v. een lightweight NLP model (bijv. `all-MiniLM-L6-v2` via `sentence-transformers`) en deze opslaat in de DB. Dit script mag *alleen* de "goedgekeurd_mens" beschrijvingen vectoriseren.

---

### 3. AI Track: Chat/Zoek Interface Kompas

#### [NEW] Backend Endpoint (`routers/ai_search.py`)
- `GET /api/kompas/search?q={query}`
- Retouneert de top 5 meest relevante indicatoren op basis van *Cosine Similarity* tussen de query embedding en de database embeddings. 

#### [MODIFY] Frontend Kompas (`static/js/kompas.js` & HTML structuur)
- Voeg een visuele zoekbalk toe ("Waar ben je naar op zoek?").
- Fetch resultaten van `/api/kompas/search`.
- Bij klik op een resultaat: simuleer een `SELECT_NODE` actie voor de D3 Sunburst chart, zodat deze direct navigeert naar de gekozen dimensie/indicator en de desbetreffende kaartlaag activeert.

### 4. AI Track: Ontologie Testen & Governance (SPARQL)
Om de kwaliteit en structuur van de door de LLM gegenereerde ontologieën te bewaken (voordat/nadat we ze integreren of in een triplestore zoals Apache Jena/GraphDB laden), implementeren we structurele validatie.

#### [NEW] Validatie Pipeline (`scripts/ai/validate_ontology.py` of Test Suite)
- Validatie-script integreren dat RDF/OWL output toetst aan de hand van SPARQL queries:
  - Controleer subclass hiërarchieën (`rdfs:subClassOf`).
  - Verifieer Domain/Range definities bij ObjectProperties.
  - Detecteer circulaire referenties en wees-klassen (orphan classes).

## Verification Plan

### Automated Tests
- Test het `GET /api/kompas/search` endpoint met mock-query's zoals "bomen" of "verkeer" en controleer of de geretourneerde indicatoren logisch zijn. (Unit test in `pytest`).
- Test de data controle service: `check_cbs_updates()` moet succesvol connecten met de OpenData API en een boolean teruggeven of er nieuwe data is.
- **Ontologie SPARQL Tests:** Automatische suite die checks draait op de gegenereerde `.ttl` (Turtle) bestanden m.b.v. een Python RDF-library (zoals `rdflib`), waarbij de [SPARQL Testqueries](file:///mnt/f/VSCode_Projects/D-OmniTwin/docs/6-ai-parallel-track/ai-integratie/sparql_ontologie_testqueries.md) worden uitgevoerd om semantische correctheid te borgen.

### Manual Verification
- **Admin Panel:** Ga naar de indicatoren, bekijk de nieuwe velden voor bron-informatie en ontologische beschrijvingen. Verifieer dat wijzigingen via de UI correct in de DB landen.
- **Kompas Zoeken:** Typ 'groen' in de nieuwe AI zoekbalk op de front-end. Verifieer dat het Kompas vloeiend uitvouwt naar het thema "Klimaat & Groen" -> "Oppervlakte groen" zonder dat de rest van de UI breekt.

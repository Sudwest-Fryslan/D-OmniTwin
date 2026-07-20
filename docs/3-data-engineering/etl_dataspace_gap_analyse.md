# 🔍 Gap Analyse & Verrijkt Ontwerp: ETL / Dataspace Beheerpagina
**D-OmniTwin | Data Engineering Track**
*Analyse datum: Juli 2026 | Basis: etl_dataspace_analyse.md + BRAINDUMP.md + ETL_DOCUMENTATION.md + ARCHITECTURE_TECHNICAL_OPERATION.md*

---

## ⚠️ Wat mist er in het oorspronkelijke plan? (De Gaps)

Het eerste plan zet goede stappen, maar schiet op 5 cruciale punten tekort:

### Gap 1: Geen Datawarehouse Architectuur Lagenmodel — én een verkeerd perspectief op de app zelf
Het plan beschrijft scripts en taken, maar mist een **gelaagd datamodel** dat data van rauw naar bruikbaar beweegt. Momenteel slaan we CBS OData direct op in de productie-tabellen. Dit is fragiel: een kapotte import overschrijft live data, er is geen historisch spoor, en er is geen kwaliteitscontrole tussendoor.

**Wat ontbreekt:** Een *Medallion Architecture* (Bronze → Silver → Gold), waarbij elke laag een specifieke verantwoordelijkheid heeft.

> **💡 Aanvullende gedachte (architectureel perspectief-shift):**
> De huidige `indicatoren` tabel + `gebied_data` tabel in D-OmniTwin zijn **zelf al een Gold-laag** — een **datamart**, speciaal gebouwd voor deze applicatie. In Kimball-terminologie: dit is de *Data Mart* fase (Staging → Transform → **Data Mart**).
>
> Dat betekent dat **D-OmniTwin niet de eigenaar is van de volledige Bronze→Gold pipeline**. De app is een *consument* van een bredere data infrastructuur. De Bronze en Silver lagen — het ruwe inladen, schonen en conformeren van CBS, RIVM, BAG data — horen thuis in de **Friese Data Space (FRLDS)** of een bredere gedeelde data-infrastructuur van de provincie/gemeenten.
>
> **Consequentie:** De ETL Beheerpagina die we bouwen heeft twee gescheiden verantwoordelijkheden:
> 1. **Datamart beheer (intern):** Beheren wat wij als D-OmniTwin uit de data space consumeren, hoe we het mappen naar ons Kompas-model, en hoe we het serveren aan de frontend.
> 2. **Dataspace connectiviteit (extern):** Configureren van verbindingen naar de upstream data space(s) en het ophalen van gecureerde data producten vanuit die space.
>
> De Bronze/Silver verwerking *zou* idealiter niet in onze applicatie zitten maar in de data space zelf — wij consumeren enkel gecertificeerde, gekwalificeerde **Data Producten**.

### Gap 2: Data Virtualisatie is Niet Uitgewerkt
De BRAINDUMP noemt de Dataspace Orchestrator-visie (data bij de bron laten), maar het eerste plan vertaalt dit slechts als "externe API's mappen aan indicatoren". Er is **geen concreet model** voor hoe je data-at-rest (onze DB) combineert met data-in-motion (live FRLDS/CBS calls) in één uniforme semantische laag.

**Wat ontbreekt:** Een *Virtual Data Layer* met data contracts, connector-configuraties, en een caching-strategie per bron.

### Gap 3: Geen Data Lineage & Observability
We weten momenteel niet *wanneer* een indicator is ververst, *waar* de data vandaan komt, *hoeveel records* er verwerkt zijn, of *waarom* een run gefaald is. De `LogViewerPage.tsx` toont logs, maar er is geen structureel data-kwaliteitsmodel.

**Wat ontbreekt:** Een `data_lineage` tabel, run-statistieken per bronkoppeling, en een data freshness-indicator per Kompas-indicator.

### Gap 4: Geen Semantic Layer / Data Contract
Externe bronnen (CBS, RIVM, BAG) hebben hun eigen kolomnamen en eenheden. De huidige `cbs_mapping_v3.json` is de enige brug, maar dit is een handmatig, fragiel JSON-bestand zonder validatie, versioning, of UI.

**Wat ontbreekt:** Een beheerde *Semantische Laag* in de database — de mapping van externe kolomnamen naar Kompas-indicatoren, inclusief transformatieregels (bijv. "deel door 1000", "keer 100 voor percentage"), opgeslagen in de DB en beheerbaar via de UI.

### Gap 5: Externe Lagen en ETL zijn Gescheiden Werelden
De `ExterneKaartlagenPage.tsx` beheert WFS/WMS lagen voor *visualisatie*. De ETL-pipeline laadt *data*. In de Dataspace-visie zijn dit twee kanten van dezelfde medaille: een externe WFS-bron is tegelijkertijd een **visualisatielaag** én een **databron** voor indicatoren. Het plan behandelt ze los.

**Wat ontbreekt:** Een uniform *Bronnenregister* (Data Source Registry) dat één plek biedt voor alle externe verbindingen, ongeacht of ze voor visualisatie of data-import gebruikt worden.

---

## 🏗️ Verrijkt Architectuurvoorstel: D-OmniTwin als Data Space Consumer

### 🔄 Perspectief-shift: Medallion vs. Kimball — en waar D-OmniTwin zit

| Laag | Medallion | Kimball | D-OmniTwin positie |
|------|-----------|---------|--------------------|
| Ruw | **Bronze** | **Staging** | ❌ Hoort in de Friese Data Space |
| Schoon | **Silver** | **Transform / Conform** | ❌ Hoort in de Friese Data Space |
| Bruikbaar | **Gold** | **Data Mart** | ✅ **Dit zijn wij** — `indicatoren` + `gebied_data` |
| Virtueel | **Virtual Layer** | *(geen equivalent)* | ✅ **Dit willen we bouwen** — FRLDS connector |

D-OmniTwin is **geen data warehouse** — het is een **data product applicatie** die gecureerde data consumeert vanuit een bredere data space en deze serveert via het Kompas-model. De `indicatoren` tabel is onze **eigen datamart**, afgestemd op onze specifieke analytische use case (buurt-niveau, Z-score percentiel, Kompas-hiërarchie).

### Het Nieuwe Architectuurplaatje

```
╔══════════════════════════════════════════════════════════════════╗
║          FRIESE DATA SPACE / FEDERATIEF DATASTELSEL (FDS)        ║
║                                                                  ║
║  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────────────────┐  ║
║  │   CBS   │  │  RIVM   │  │   BAG   │  │ Kadaster / PDOK   │  ║
║  └────┬────┘  └────┬────┘  └────┬────┘  └─────────┬─────────┘  ║
║       │            │            │                  │             ║
║  ┌────▼────────────▼────────────▼──────────────────▼──────────┐ ║
║  │             BRONZE / STAGING LAAG                          │ ║
║  │   (Ruwe ingestie, onveranderd, bij de bron of in FDS)      │ ║
║  └──────────────────────────┬──────────────────────────────────┘ ║
║                             │                                    ║
║  ┌──────────────────────────▼──────────────────────────────────┐ ║
║  │             SILVER / CONFORM LAAG                           │ ║
║  │   (Gecureerde Data Producten, gestandaardiseerd,            │ ║
║  │    iSHARE/EDC gecertificeerd, vindbaar in catalogus)        │ ║
║  └──────────────────────────┬──────────────────────────────────┘ ║
╚═════════════════════════════╪════════════════════════════════════╝
                              │  ← Data Product API / Connector
╔═════════════════════════════▼════════════════════════════════════╗
║                    D-OMNITWIN APPLICATIE                         ║
║                                                                  ║
║  ┌──────────────────────────────────────────────────────────┐   ║
║  │         GOLD / DATA MART  (onze eigen laag)              │   ║
║  │   indicatoren tabel  ←── Kompas-specifiek model          │   ║
║  │   gebied_data tabel  ←── Buurt × Indicator × Jaar        │   ║
║  │   Z-score berekeningen, Materialized Views                │   ║
║  └──────────────────────────────────────────────────────────┘   ║
║                              │                                   ║
║  ┌───────────────────────────▼──────────────────────────────┐   ║
║  │         VIRTUAL LAYER  (on-demand, geen kopie)           │   ║
║  │   Directe FRLDS / OData queries voor live data            │   ║
║  │   Gecached op basis van TTL per bron                      │   ║
║  └──────────────────────────────────────────────────────────┘   ║
║                              │                                   ║
║  ┌───────────────────────────▼──────────────────────────────┐   ║
║  │         FASTAPI + REACT ADMIN PANEL + FRONTEND            │   ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 🌍 Verkenning: Bestaande Dataspace Marketplace Tooling

In plaats van de Bronze/Silver pipeline volledig zelf te bouwen, kunnen we aansluiten op bestaande infrastructure. Hieronder een overzicht van relevante tools en platforms:

### Nederlandse / Europese Dataspace Initiatieven

| Platform | Type | Relevantie voor D-OmniTwin | Status |
|----------|------|---------------------------|--------|
| **FRLDS** (Fryslân Regionaal Data Space) | Regionale data space | ⭐⭐⭐ Direct — dit is onze primaire upstream bron | Pilot fase |
| **FDS** (Federatief Datastelsel) | Nationaal NL | ⭐⭐⭐ Landelijke CBS/BAG/BRP ontsluiting | In opbouw |
| **PDOK** | Geo-data platform NL | ⭐⭐⭐ Al in gebruik (WFS/WMS) | Productie |
| **iSHARE** | Trust framework / data contracts | ⭐⭐ Authenticatie & autorisatie voor data sharing | Productie |
| **Eclipse Dataspace Connector (EDC)** | Technische connector (GAIA-X) | ⭐⭐ Standaard voor EU dataspace interoperabiliteit | Actief |
| **TNO Trusted Data Vault** | Persoonlijke/gevoelige data | ⭐ Minder relevant voor geo-indicatoren | Pilot |

### Technische Data Catalogus & Marketplace Tools

| Tool | Wat het doet | Overweging |
|------|-------------|------------|
| **OpenMetadata** | Data catalogus, lineage, quality | Open source, zelf te hosten — vervangt onze handmatige lineage tabel |
| **Apache Atlas** | Enterprise data governance | Zwaarder, meer voor grote organisaties |
| **DataHub (LinkedIn)** | Data discovery & catalogus | Populair, goede community, REST API |
| **Great Expectations** | Data quality / validatie pipeline | Kan als Silver-laag kwaliteitscheck draaien |
| **dbt (data build tool)** | SQL-gebaseerde transformaties (Kimball) | Uitstekend voor onze staging → datamart transformaties |

### Aanbeveling: Pragmatisch Begin

```
Korte termijn:  D-OmniTwin beheert zelf een lichte Bronze/Silver staging
                (etl_bronnen + etl_runs tabellen zoals beschreven)
                → Pragmatisch, nul extra infra, snel bruikbaar

Middellange    Aansluiting op FRLDS als die beschikbaar komt:
 termijn:       D-OmniTwin vraagt gecureerde Data Producten op via API
                Eigen ETL scripts worden overbodig voor gecertificeerde bronnen

Lange termijn:  Eclipse EDC connector + iSHARE trust framework
                D-OmniTwin als volwaardige dataspace participant
                Data Producten publiceren (Kompas scores) terug naar de space
```

> **💡 Interessante gedachte:** D-OmniTwin kan in de toekomst niet alleen data *consumeren* uit de Friese Data Space, maar ook data *produceren* — bijvoorbeeld de berekende Z-scores en Kompas-percentielscores als een Data Product publiceren, zodat andere gemeentelijke applicaties hier ook gebruik van kunnen maken.

---

## 📐 Nieuw Databaseschema: Data Platform Uitbreiding

### `etl_bronnen` — Bronnenregister (vervangt losse config + ExterneKaartlagen)
```sql
CREATE TABLE etl_bronnen (
    id           SERIAL PRIMARY KEY,
    naam         VARCHAR(100) NOT NULL,          -- "CBS Kerncijfers 2024"
    bron_type    VARCHAR(20) NOT NULL,           -- 'odata', 'wfs', 'wms', 'lokaal', 'frlds'
    url          TEXT NOT NULL,
    auth_type    VARCHAR(20) DEFAULT 'none',     -- 'none', 'api_key', 'oauth2'
    auth_config  JSONB,                          -- versleutelde credentials
    refresh_strategie VARCHAR(20) DEFAULT 'handmatig',
    cron_schema  VARCHAR(50),                   -- bijv. '0 2 * * 1'
    actief       BOOLEAN DEFAULT true,
    gemaakt_op   TIMESTAMPTZ DEFAULT NOW(),
    -- Brug naar ExterneKaartlagen (dezelfde bron, twee doelen)
    externe_kaartlaag_id INTEGER REFERENCES externe_kaartlagen(id)
);
```

### `etl_runs` — Job Tracking (observability ruggengraat)
```sql
CREATE TABLE etl_runs (
    id           SERIAL PRIMARY KEY,
    bron_id      INTEGER REFERENCES etl_bronnen(id),
    taak_naam    VARCHAR(200) NOT NULL,
    status       VARCHAR(20) DEFAULT 'in_wachtrij',  -- 'bezig', 'voltooid', 'gefaald'
    gestart_op   TIMESTAMPTZ,
    voltooid_op  TIMESTAMPTZ,
    records_gelezen    INTEGER DEFAULT 0,
    records_geladen    INTEGER DEFAULT 0,
    records_overgeslagen INTEGER DEFAULT 0,
    records_fouten     INTEGER DEFAULT 0,
    configuratie JSONB,   -- parameters waarmee gestart
    foutmelding  TEXT,
    log_locatie  TEXT
);
```

### `etl_semantic_mapping` — Semantische Laag (vervangt cbs_mapping_v3.json)
```sql
CREATE TABLE etl_semantic_mapping (
    id              SERIAL PRIMARY KEY,
    bron_id         INTEGER REFERENCES etl_bronnen(id),
    bron_kolom_naam VARCHAR(200) NOT NULL,   -- "PersonenAutos_Per_Huishouden"
    bron_eenheid    VARCHAR(50),
    indicator_uuid  UUID REFERENCES indicatoren(uuid),
    -- Transformatieregels
    transformatie        VARCHAR(50) DEFAULT 'direct',  -- 'direct','delen_door','keer','percentage'
    transformatie_factor DECIMAL,
    min_waarde      DECIMAL,
    max_waarde      DECIMAL,
    actief          BOOLEAN DEFAULT true,
    gemaakt_op      TIMESTAMPTZ DEFAULT NOW(),
    notities        TEXT
);
```

### `data_lineage` — Traceerbaarheid per indicator-waarde
```sql
CREATE TABLE data_lineage (
    id              BIGSERIAL PRIMARY KEY,
    gebied_data_id  BIGINT REFERENCES gebied_data(id),
    etl_run_id      INTEGER REFERENCES etl_runs(id),
    bron_id         INTEGER REFERENCES etl_bronnen(id),
    mapping_id      INTEGER REFERENCES etl_semantic_mapping(id),
    geladen_op      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 🌐 Data Virtualisatie: Hybride Implementatiestrategie

### Niveau 1: Gecachede Virtualisatie (On-Demand Refresh)
Data wordt bij de bron opgehaald *wanneer nodig* en tijdelijk gebufferd (Bronze → Silver). Na een configureerbare TTL wordt de cache automatisch ongeldig.

### Niveau 2: Federated Query (Echte Dataspace)
Voor FRLDS: de data verlaat nooit de bron. De FastAPI backend is de *query router*:

```python
@router.get("/api/dataspace/query")
async def federated_query(indicator_uuid: str, gebiedscodes: List[str], bron_id: int):
    bron = await get_bron(bron_id)
    if bron.bron_type == 'frlds':
        return await frlds_connector.query(bron, indicator_uuid, gebiedscodes)
    elif bron.bron_type == 'odata':
        return await odata_connector.query(bron, indicator_uuid, gebiedscodes)
```

---

## 🎨 Uitgebreid UI Ontwerp: 5-Tab Data Platform Pagina

### Tab 1: 🔌 Bronnenregister
- Lijst alle geregistreerde bronnen (CBS, RIVM, BAG, FRLDS, lokaal)
- Per bron: status-badge (🟢 Vers / 🟡 Verouderd / 🔴 Fout), laatste sync-tijdstip
- Verbindingstest knop — valideert bereikbaarheid en haalt metadata op
- **Nieuw:** Koppeling met ExterneKaartlagen (één bron = visualisatie + data)

### Tab 2: 🗺️ Semantische Mapping Editor *(Gap 4 oplossing)*
- **Links:** kolomnamen van geselecteerde externe bron (via discovery API)
- **Rechts:** Kompas-indicatoren (zoekbaar)
- Drag-and-drop of dropdown om bron → indicator te koppelen
- Transformatieregels instellen per koppeling (factor, eenheid-omrekening)
- Preview: realtime voorbeeld van getransformeerde waarden

### Tab 3: ⚙️ ETL Pijplijnen (DAG View)
- React Flow DAG per pijplijn: `Extract → Validate → Transform → Load → Notify`
- Live voortgang via Server-Sent Events (SSE)
- Node detail paneel: logs, record-counts, duur, retry-knop
- Kleurcodering: 🟩 Voltooid | 🟦 Bezig | 🟥 Error | ⬜ In wachtrij

### Tab 4: 📊 Data Observability *(Gap 3 oplossing — compleet nieuw)*
- **Freshness Matrix:** indicatoren × bronnen × laatste update-timestamp
- **Kwaliteitsscores:** % geslaagd, outliers, null-percentages per run
- **Data Lineage Explorer:** klik op indicator-waarde → zie welke run, bron en mapping
- **Trend grafieken:** records per run over tijd (anomalie-detectie)

### Tab 5: 💾 Export & Seed
- Config Seedfile: indicatoren + hiërarchie + kleurschema's + semantische mappings als JSON
- Data snapshot: `gebied_data` voor gekozen jaar als CSV/Parquet
- Rollback: herstel naar vorige snapshot op basis van `etl_runs`

---

## 🔧 Task Runner: Gefaseerde Aanpak

```
Fase 1 (Nu):       FastAPI BackgroundTask + etl_runs tabel (nul extra infra)
Fase 2 (Later):    Celery + Redis (bij >5 gelijktijdige bronnen)
Fase 3 (Toekomst): Airflow of Prefect (complexe DAG-afhankelijkheden)
```

**SSE voor live log-streaming** (eenvoudiger dan WebSockets):
```python
@router.get("/api/etl/runs/{run_id}/stream")
async def stream_run_logs(run_id: int):
    async def event_generator():
        while True:
            logs = await get_new_logs(run_id)
            for log in logs:
                yield f"data: {log.json()}\n\n"
            await asyncio.sleep(0.5)
    return EventSourceResponse(event_generator())
```

---

## 🗺️ Implementatie Roadmap

### Sprint A — Fundament (2-3 sessies)
- [ ] DB schema: `etl_bronnen`, `etl_runs`, `etl_semantic_mapping`, `data_lineage`
- [ ] FastAPI router `/api/etl/*` (CRUD bronnen, starten runs, logs ophalen)
- [ ] Bestaande ExterneKaartlagen koppelen aan `etl_bronnen`
- [ ] Tab 1 "Bronnenregister" in Admin Panel

### Sprint B — Pijplijnen & Mapping (3-4 sessies)
- [ ] Bestaande ETL scripts omzetten naar BackgroundTask-modules
- [ ] Semantische Mapping editor (Tab 2) — vervangt `cbs_mapping_v3.json`
- [ ] DAG View (Tab 3) met React Flow + SSE log-streaming

### Sprint C — Observability & Virtualisatie (3-4 sessies)
- [ ] Data Freshness dashboard (Tab 4)
- [ ] Data Lineage koppeling in `gebied_data`
- [ ] Virtual Data Connector PoC met CBS OData

### Sprint D — Dataspace (Toekomst)
- [ ] FRLDS connector (OAuth2, federated query)
- [ ] Data contract validatie per bron
- [ ] Multi-tenant bron isolatie

---

## 💡 Verfijnde Open Vragen

1. **Medallion staging:** Bronze laag als PostgreSQL-tabellen (eenvoudig, alles in één DB) of file-based staging (Parquet in `data/staging/`)?
2. **Eerste virtuele bron:** CBS OData (laagste risico, al bekend) of direct FRLDS pilot?
3. **Mapping Editor prioriteit:** Is de Semantische Mapping editor (Tab 2) waardevoller als eerste bouw dan de DAG-visualisatie (Tab 3)?
4. **ExterneKaartlagen migratie:** Volledig samenvoegen met Bronnenregister, of de visualisatie-beheer pagina apart houden?

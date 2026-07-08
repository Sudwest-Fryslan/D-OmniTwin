# Master Document: Deep Research Prompts voor D-OmniTwin

## Instructie voor gebruik

Dit is een modulaire architectuurstudie. Voer Prompt 0 (Context) in als
systeem-prompt. Voer daarna de modules sequentieel in voor het beste,
meest diepgaande resultaat.

Let op: door de vereiste diepgang is het aanbevolen elke module als een
aparte Deep Research iteratie te draaien.

------------------------------------------------------------------------

# PROMPT 0: Systeem Context (Altijd als eerste invoeren)

## Context & Doel

Je treedt op als Lead Enterprise/Solution Architect. Wij ontwikkelen
D-OmniTwin: een open-source, AI-native Digital Twin Platform voor de
fysieke leefomgeving van Nederlandse gemeenten.

Onze aanvraag voor het Innovatiebudget Digitale Overheid 2026 is
toegekend, waarmee we ons huidige prototype (v1.0.0) doorontwikkelen
naar een robuuste federatieve voorziening.

## Wat D-OmniTwin is

Een intelligent beslis- en verkenplatform.

Het hart is het **D-Omni Kompas**: een dynamische D3.js sunburst
visualisatie van meer dan 200 indicatoren die zich opbouwt vanuit
metadata.

Daarnaast bevat het platform een contextbewuste lokale AI-assistent die
data vertaalt naar beleidsnarratieven.

## Wat D-OmniTwin nadrukkelijk niet is

D-OmniTwin is:

-   Geen traditioneel BI-platform.
-   Geen centraal Data Lake.
-   Geen vervanging van bestaande bronsystemen.

Het fungeert als een intelligente interactie-, analyse- en
orkestratielaag bovenop federatieve databronnen.

Adviseer dus geen gecentraliseerde data-warehousing oplossingen zoals
Snowflake of Azure Synapse.

## Ontwerpfilosofie

### Eenvoud regeert

Voeg alleen componenten toe wanneer zij aantoonbaar architectonische
waarde toevoegen. Vermijd over-engineering.

### Beheerbaarheid

De oplossing moet door een klein gemeentelijk DevOps-team beheerd kunnen
worden. Geen onnodig complexe clusters als het eenvoudiger kan.

### Principes

-   Open Source First
-   API First
-   Metadata & Semantics First
-   GIS First (PostGIS/deck.gl)
-   AI Ready
-   Federate before Replicate
-   Vendor lock-in vermijden

## Bestaande Stack

-   Traefik
-   FastAPI
-   PostgreSQL/PostGIS
-   pg_featureserv
-   deck.gl
-   Docker

## Taak

Bevestig dat je deze context begrijpt en klaar bent voor Module 0.5.

------------------------------------------------------------------------

# PROMPT 0.5: Module 0.5 - State of the Art & Wereldwijde Referenties

## De uitdaging

Voordat we technologie selecteren, moeten we leren van wat er al is.
D-OmniTwin opereert in het snijvlak van Urban Digital Twins en
federatieve dataspaces.

## Jouw taak

Onderzoek wereldwijde en Europese referentiearchitecturen die
inhoudelijk vergelijkbaar zijn met onze ambities.

Analyseer initiatieven zoals:

-   Gaia-X
-   FIWARE
-   Destination Earth
-   Living-in.EU
-   OGC
-   INSPIRE
-   Data Spaces Support Centre (DSSC)

Bekijk daarnaast koplopers zoals Helsinki, Singapore en Rotterdam.

Beantwoord:

-   Wat zijn de belangrijkste architecturale lessen (successen én
    valkuilen) van deze initiatieven?
-   Hoe combineren zij federatieve data, semantiek en ruimtelijke
    GIS-weergave?
-   Welke concepten zijn direct herbruikbaar voor D-OmniTwin?

Genereer een overzicht van direct toepasbare architectuurprincipes.

------------------------------------------------------------------------

# PROMPT 1: Module 1 - Dataspace Orchestrator & Distributed Computing

## De uitdaging

Ontwerp de orchestratielaag die koppelt met regionale (FRLDS) en
landelijke (FDS) dataspaces, zonder een data-lake te bouwen.

## Jouw taak

### Orchestratie & Trade-offs

Vergelijk oplossingen voor:

-   Data virtualisatie:
    -   Trino
    -   DuckDB
    -   PostgreSQL FDW

tegenover:

-   Pure API-orchestratie:
    -   GraphQL
    -   Backend-for-Frontend (BFF) in FastAPI

Bespreek expliciet de trade-offs:

-   Waarom wel Trino?
-   Waarom niet FDW?
-   Waarom geen GraphQL?

### Performance & Distributed Computing

Onderzoek en adviseer over:

-   CQRS
-   Materialized Views
-   Eventual Consistency
-   Query Pushdown
-   Predicate Pushdown
-   Spatial Indexing (PostGIS)
-   Tile Caching (pg_featureserv)

Hoe garanderen we sub-seconde responstijden voor AI en GIS over een
federatief netwerk?

### Minimum Viable Architecture (MVA)

Ontwerp:

1.  De ideale eindarchitectuur.
2.  Een pragmatische MVA.

Wat is de meest haalbare setup die in 2026 directe waarde levert met een
klein team?

------------------------------------------------------------------------

# PROMPT 2: Module 2 - De Semantische Laag & Het D-Omni Kompas

## De uitdaging

Het D-Omni Kompas is niet zomaar een UI, maar een dynamisch Kennismodel.
Het bouwt zichzelf op vanuit metadata. Dit is het belangrijkste
onderscheidend vermogen.

AI gaat hierop redeneren.

## Jouw taak

Ontwerp een pragmatische maar krachtige Semantic Layer.

### Fundament

Onderzoek:

-   Taxonomie
-   Ontologie
-   Indicator Modeling
-   Knowledge Graphs

Hoe modelleren we dit zonder onnodige complexiteit?

### Standaarden & Technologie

Vergelijk:

-   JSON-LD
-   RDF
-   SHACL
-   DCAT-AP
-   Gemeentelijk Gegevensmodel (GGM)

Beantwoord:

Kunnen we dit binnen of naast onze PostgreSQL-stack oplossen zonder te
verdrinken in een ontologisch moeras?

### Governance & Versies

Ontwerp:

-   Versionering van indicatoren
-   Semantische governance
-   Omgaan met wijzigende bronnen binnen de dataspace
-   Semantic search

------------------------------------------------------------------------

# PROMPT 3: Module 3 - Intelligence Layer: De AI-Native Assistent

## De uitdaging

De AI is geen extra service, maar een primaire gebruiker van het
Kennismodel (Kompas).

De lokale LLM moet complexe Z-scores vertalen naar deterministische,
juridisch veilige beleidsnarratieven.

## Jouw taak

Ontwerp een veilige, toekomstbestendige AI-architectuur.

### Tooling & Orchestratie

Onderzoek integratie met:

-   MCP (Model Context Protocol)
-   Tool Calling
-   Agent Memory

### Beheer & Veiligheid

Ontwerp:

-   Prompt Registry
-   Prompt Governance
-   Explainability (XAI)

### Determinisme & Controle

Onderzoek:

-   Guard Rails
-   Human in the Loop
-   AI Observability

Hoe voorkomen we hallucinerende overheden?

------------------------------------------------------------------------

# PROMPT 4: Module 4 - Synthese & De 3 Horizonten

## De uitdaging

Breng Module 0.5 t/m 3 samen in concrete architectuurplaten en een
roadmap.

## Jouw taak

Ontwerp drie architectuurhorizonten inclusief C4 Container diagrammen in
Mermaid.js.

## Architectuur A - Pragmatisch (2026)

Focus:

-   Minimum Viable Architecture
-   Beheersbaar voor 3 developers
-   Huidige stack
-   Minimale toevoegingen voor pilot

## Architectuur B - Strategisch (2028)

Focus:

-   Integratie met landelijke FDS
-   Volwassen iSHARE autorisatie
-   Migratie naar Kubernetes
-   Robuuste semantische laag

## Architectuur C - Visionair (2032)

Focus:

-   Volledig AI-driven agentic workflows
-   Decentrale knowledge graphs over Europa
-   DSSC-integratie
-   Voorspellende Digital Twin-capaciteiten

------------------------------------------------------------------------

# PROMPT 5: Module 5 - Kritische Review (Red Teaming)

## De uitdaging

We moeten onze eigen aannames kritisch toetsen voordat we bouwen.

## Jouw rol

Verander van persona.

Je bent nu een onafhankelijke, zeer kritische Senior Enterprise
Architect / Auditor.

Je hebt de voorgestelde architecturen uit Module 4 gelezen.

## Risico-analyse

Onderzoek:

-   Wat is het grootste single point of failure?
-   Welke aannames over dataspaces en open-source AI zijn naïef of
    gevaarlijk voor een overheid?

## Alternatieven

Forceer minimaal drie alternatieve ontwerpkeuzes die radicaal afwijken
van de huidige koers, maar mogelijk veiliger of goedkoper zijn.

## Conclusie

Geef een keihard, eerlijk advies aan de CDO van Súdwest-Fryslân:

Is dit klaar voor ontwikkeling, of moeten we terug naar de tekentafel?

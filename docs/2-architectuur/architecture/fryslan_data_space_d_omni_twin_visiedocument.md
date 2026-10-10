# Strategisch en Technisch Visiedocument
## De Fryslân Data Space (FRLDS) als motor voor D-OmniTwin

**Versie:** 0.1 (Concept)  
**Datum:** 28 maart 2026  

**Doelgroep:** Data Architecten, Data Scientists, Data Engineers en Specialisten Adoptie & Samenwerking

---

## Executive Summary: De Digitale Tweeling ontmoet de Digitale Terp

D-OmniTwin fungeert momenteel als een krachtige, interactieve spiegel van de fysieke leefomgeving in Noord-Nederland. De huidige architectuur leunt echter op gecentraliseerde ETL-processen (open data via CBS, RIVM, BAG). Dit bereikt zijn grenzen wanneer we contextrijke, fijnmazige en privacygevoelige regionale data willen ontsluiten.

De strategie *"Een terp voor Friese data 2030"* en de daaruit voortvloeiende Fryslân Data Space (FRLDS) bieden het ontbrekende fundament. Waar D-OmniTwin de ultieme presentatie- en interactielaag is (via deck.gl en de AI-chat), vormt de FRLDS de soevereine, federatieve datalaag.

Door deze twee te integreren transformeert D-OmniTwin van een statisch dashboard naar een proactief, ethisch geborgd en hyperlokaal beleidsinstrument.

---

## 1. Waardepropositie per Discipline

### Voor de Data Architect: Van Data Lake naar Data Space

De integratie dwingt een verschuiving af van een gecentraliseerde PostgreSQL database (waar alle data naartoe gekopieerd is) naar een gedecentraliseerd model (Gaia-X / IDS principes).

**De potentie:**  
D-OmniTwin hoeft gevoelige data (zoals uit het sociaal domein) niet meer op te slaan. De applicatie acteert als een Participant binnen het iSHARE Trust Framework.

**Impact op architectuur:**  
De FastAPI backend krijgt een IDS/iSHARE-connector. Bij een query in de D-OmniTwin kaart haalt de backend via real-time authorisatie uitsluitend de benodigde *need-to-know* data op bij de FRL1000 brondataset.

---

### Voor de Data Engineer: Streaming Context in plaats van Batch ETL

**De potentie:**  
Minder onderhoud aan complexe web-scrapers en API-koppelingen voor incidentele datasets. Via het iSHARE Participant Registry wordt data-uitwisseling gestandaardiseerd via Linked Data en API-specificaties.

**Uitdaging:**  
Het mappen van de D-OmniTwin ontologie (217 indicatoren, 12 thema's) op de gedistribueerde FRL1000 dataset. De `gebiedsmonitor_service.py` moet worden omgebouwd om federatieve API-calls synchroon te verwerken met lokale caching.

---

### Voor de Data Scientist: Synergie tussen Qwen3 en FRLLLM

D-OmniTwin maakt lokaal gebruik van een Ollama instance (`qwen3:30b`) en `pgvector` voor het chat-zijpaneel.

**De potentie:**  
Deze lokale AI kan worden verrijkt of deels vervangen door het Fryslân Large Language Model (FRLLLM). Omdat FRLLLM is getraind op de Friese context en taal, kan het via Retrieval-Augmented Generation (RAG) de FRL1000 microdata interpreteren en via D-OmniTwin presenteren in de "OmgevingsChat".

**Kwaliteit:**  
De ontologische beschrijvingen in de OmniTwin database (nu soms AI-gegenereerd) kunnen worden gevalideerd of vervangen door de gecureerde FRL1000 context.

---

### Voor Communicatie, Samenwerking & Adoptie: Het Coöperatiemodel

**De potentie:**  
Gemeenten zijn vaak huiverig om data in een centraal "dashboard" te laden. Doordat D-OmniTwin de infrastructuur van DataFryslân (een coöperatie en geregistreerde DGA-dataintermediair) gebruikt, verdwijnt deze juridische en politieke frictie.

**Borging:**  
Gemeenten weten dat hun data de bron niet verlaat en uitsluitend via Accession Agreements in D-OmniTwin getoond wordt. De inzet van AI wordt per AI-usecase getoetst volgens het AI-beleid van de organisatie (bij SWF: aanmelding bij de AI Officer, IAMA/DPIA waar nodig) en gaat pas aan na een vastgelegde verklaring (zie https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/307).

---

## 2. Voorgestelde Doelarchitectuur (High-Level)

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ D-OMNITWIN (Interactielaag)                                             │
│ ┌───────────────┐  ┌──────────────────┐  ┌──────────────────────────┐   │
│ │ Kaart (deck.gl)│ │ D-Omni Kompas    │  │ AI Chat Zijpaneel        │   │
│ └──────┬────────┘  └────────┬─────────┘  └────────────┬─────────────┘   │
│        │ HTTP/REST          │                         │                 │
│ ┌──────▼────────────────────▼─────────────────────────▼─────────────┐   │
│ │ FASTAPI BACKEND                                                   │   │
│ │ ┌──────────────────┐  ┌──────────────────┐ ┌────────────────────┐ │   │
│ │ │ Vector Search    │  │ LLM Router       │ │ iSHARE / IDS       │ │   │
│ │ │ (pgvector)       │  │ (Qwen3 → FRLLLM) │ │ Connector Client   │ │   │
│ │ └──────────────────┘  └──────────────────┘ └─────────┬──────────┘ │   │
│ └──────────────────────────────────────────────────────┼────────────┘   │
└────────────────────────────────────────────────────────┼────────────────┘
                                                         │ Geautoriseerde
                                                         │ API Calls (iSHARE)
┌────────────────────────────────────────────────────────▼────────────────┐
│ FRYSLÂN DATA SPACE (FRLDS - Soevereine Datalaag)                        │
│ ┌──────────────────┐  ┌──────────────────┐ ┌────────────────────────┐   │
│ │ Participant      │  │ FRL1000          │ │ FRLLLM (AI Model)      │   │
│ │ Registry (iSHARE)│  │ Longitudinale    │ │ Contextuele Generatie  │   │
│ │ & Authorisatie   │  │ Microdata        │ │ (RAG implementatie)    │   │
│ └──────────────────┘  └────────┬─────────┘ └─────────┬──────────────┘   │
│                                │                     │                  │
│                    ┌───────────▼─────────────────────▼──────────┐       │
│                    │ Friese Gemeenten / Provincie / Partners    │       │
│                    │ (Lokale Nodes via IDS Dataconnectors)      │       │
│                    └────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Concrete Innovatie Use-Cases voor D-OmniTwin

### Use-Case A: Fijnmazige Klimaatadaptatie & Landbouw

**Huidige situatie:**  
Toont enkel CBS open data over groenvoorziening of oppervlaktewater op buurtniveau.

**Met FRLDS:**  
Via iSHARE-connecties delen agrariërs (geanonimiseerd en via tijdelijke delegatie) real-time data over bodemkwaliteit en biomassaproductie uit de FRL1000.

D-OmniTwin visualiseert dit als een 3D-polygon (via deck.gl), waardoor beleidsmakers via de Kompas-tool exact zien welke polders de hoogste potentie hebben voor bio-energie, gecombineerd met netcongestie-data.

---

### Use-Case B: Vroegsignalering Sociaal Domein (Zorg & Armoede)

**Huidige situatie:**  
Gemeentelijke armoedecijfers zijn vaak twee jaar oud, wat leidt tot reactief beleid.

**Met FRLDS:**  
D-OmniTwin krijgt – exclusief voor geautoriseerde wijkteams – toegang tot gepseudonimiseerde doorsnedes van Wmo-, jeugdzorg- en schuldhulptrajecten.

De AI-assistent (gekoppeld aan FRLLLM) synthetiseert deze data om patronen van draaglast en draagkracht te signaleren, zonder privacy van inwoners te schenden.

---

## 4. Actielijst & Roadmap (Proof of Concept)

### Sprint 1–2: Adoptie & Legal

- Registratie van D-OmniTwin als geautoriseerde participant binnen DataFryslân
- Opzetten van een IAMA voor de koppeling tussen AI-chat en FRL1000 data

### Sprint 3–4: Data Engineering & Architectuur

- Ontwikkelen van `ishare_service.py` binnen de FastAPI backend
- Implementeren van veilige handshakes met het iSHARE registry
- Mapping van 10 kritieke indicatoren naar FRL1000 datastromen

### Sprint 5–6: AI & Data Science

- Implementatie hybride LLM-configuratie:
  - Snelle intent-classificatie via lokale Qwen3
  - Complexe queries via FRLLLM (RAG)

---

## Conclusie

D-OmniTwin is technologisch volwassen genoeg om als interface te dienen voor het Friese databeleid.

Door de FRLDS als backend te gebruiken:

- worden schaalproblemen van ETL opgelost
- blijft data bij de bron (data-soevereiniteit)
- wordt privacy structureel geborgd
- ontstaat een actueel en beleidsrelevant systeem

Dit maakt D-OmniTwin tot een daadwerkelijk soeverein, datagedreven en maatschappelijk verantwoord instrument.


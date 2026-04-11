# Strategisch en Technisch Visiedocument
## Fryslân Data Space (FRLDS) in het bredere Dataspace-landschap

**Versie:** 0.2 (Herijkt)  
**Datum:** 28 maart 2026  

**Doelgroep:** Data Architecten, Data Scientists, Data Engineers en Specialisten Adoptie & Samenwerking

---

## Executive Summary: Van Applicatie naar Dataspace-gedreven Ecosysteem

De huidige positionering van D-OmniTwin als centrale applicatie is technisch sterk, maar conceptueel nog onvoldoende verankerd in het bredere dataspace-landschap.

Op basis van de onderliggende architectuur en de strategische analyse van de FRLDS ontstaat een belangrijk inzicht:

> **FRLDS is niet “de backend van D-OmniTwin”, maar één specifieke dataspace binnen een breder federatief ecosysteem van dataspaces.**

D-OmniTwin moet daarom niet primair gezien worden als een applicatie op één dataspace, maar als een **dataspace-agnostische interactielaag** die meerdere dataspaces kan ontsluiten.

De FRLDS is daarin een cruciale eerste implementatie (regionaal, context-rijk), maar staat naast andere dataspaces zoals:

- Nationale dataspaces (bijv. Federatief Datastelsel – FDS)
- Domeinspecifieke dataspaces (zorg, energie, mobiliteit)
- Regionale dataspaces (zoals Groningen)

Deze herpositionering vormt de ontbrekende basis in het huidige voorstel.

---

## 1. De Ontbrekende Basis: Het Dataspace-denkkader

### 1.1 Van Data Platform naar Dataspace Ecosysteem

De huidige D-OmniTwin architectuur is klassiek opgebouwd als een gecentraliseerd data platform:

- PostgreSQL + PostGIS + pgvector als centrale opslag  
- ETL pipelines (CBS, RIVM, BAG)  
- Backend die alle data “bezit” en serveert  

➡️ Dit is in lijn met traditionele data lakes, maar staat haaks op dataspace-principes.

Volgens de FRLDS-architectuur (Gaia-X / IDS / iSHARE):

- Data blijft bij de bron  
- Toegang wordt contractueel en dynamisch geregeld  
- Data-uitwisseling is federatief en context-gedreven  fileciteturn0file1

### 1.2 Dataspaces als bouwblokken

Een dataspace is:

- Geen database
- Geen platform
- Maar een **afsprakenstelsel + infrastructuur voor datadeling**

Belangrijke componenten:

- Identity & Trust (iSHARE)
- Data Usage Control (IDS contracts)
- Federatieve toegang (API + Linked Data)

➡️ Dit betekent dat architectuurdenken moet verschuiven van:

**“Waar staat mijn data?” → “Onder welke voorwaarden kan ik data gebruiken?”**

---

## 2. Positionering van FRLDS binnen het landschap

### 2.1 FRLDS als regionale executielaag

De FRLDS is volgens de analyse:

- Geen vervanger van nationale infrastructuren
- Maar een **regionale, context-rijke executielaag** fileciteturn0file1

Concreet:

| Laag | Rol |
|------|-----|
| Europees | Gaia-X / Data Governance Act |
| Nationaal | Federatief Datastelsel (FDS) |
| Regionaal | **FRLDS (DataFryslân)** |
| Applicatie | D-OmniTwin |

➡️ Belangrijk inzicht:

**FRLDS voegt context en microdata toe waar FDS generieke basisdata levert.** fileciteturn0file1

### 2.2 FRLDS componenten (herijkt)

- Data Commons via coöperatiemodel  
- FRL1000 (longitudinale microdata)  
- FRLLLM (contextueel taalmodel)  
- iSHARE trust framework  
- IDS connectors per deelnemer  fileciteturn0file1

➡️ Dit bevestigt dat FRLDS een **volwaardige dataspace is**, geen dataset of platform.

---

## 3. Implicaties voor D-OmniTwin Architectuur

### 3.1 Huidige situatie (bevestigd)

Uit de systeemarchitectuur:

- Centrale PostgreSQL database met indicatoren en waarden  fileciteturn0file0  
- Backend services die data aggregeren en serveren  fileciteturn0file0  
- AI (Qwen3 + pgvector) lokaal geïntegreerd  fileciteturn0file0  

➡️ Dit is een **monolithisch data-consumptiemodel**.

### 3.2 Gewenste situatie: Dataspace-native D-OmniTwin

D-OmniTwin evolueert naar:

> **Federatieve query- en interactielaag over meerdere dataspaces**

Nieuwe rol van componenten:

| Component | Nieuwe rol |
|----------|-----------|
| FastAPI backend | Orchestrator van dataspace calls |
| Database | Cache / versneller (niet bron) |
| AI layer | Federatieve interpretatie (RAG over dataspaces) |
| Kaart/Kompas | Visualisatie van multi-source data |

### 3.3 Nieuwe kerncomponent: Dataspace Orchestrator

Toevoegen van:

- `dataspace_router.py`
- `policy_engine`
- `identity & consent handling`

Functie:

- Bepalen **welke dataspace** wordt aangesproken
- Afhandelen van autorisatie (iSHARE)
- Samenvoegen van resultaten

---

## 4. Van Eén Dataspace naar Multi-Dataspace Strategie

### 4.1 Typologie van dataspaces

Om jouw doel (“zicht op mogelijke dataspaces”) concreet te maken:

#### 1. Publieke / Overheids Dataspaces
- FRLDS (Fryslân)
- FDS (NL)

#### 2. Domein Dataspaces
- Zorg (sociaal domein)
- Energie (netbeheer, opwek)
- Mobiliteit

#### 3. Regionale Ecosystemen
- Groningen dataspace
- Interprovinciale samenwerkingen

#### 4. Private / Publiek-private Dataspaces
- Agrarische ketens
- Woningcorporaties

➡️ FRLDS is dus één node in een netwerk.

---

## 5. Herijkte Doelarchitectuur

### Kernverschuiving

Van:

- D-OmniTwin ↔ FRLDS

Naar:

- D-OmniTwin ↔ **Dataspace Ecosysteem**
  - FRLDS
  - FDS
  - Domein dataspaces

### Conceptueel model

```
D-OmniTwin (UI + AI)
        │
        ▼
Dataspace Orchestrator (FastAPI)
        │
 ┌──────┼───────────────┐
 ▼      ▼               ▼
FRLDS   FDS     Domein Dataspaces
```

---

## 6. Toetsing aan bijlagen (kritische reflectie)

### Sterk in huidig voorstel

- Goede koppeling D-OmniTwin ↔ FRLDS
- Sterke AI-integratie (Qwen3 + FRLLLM)
- Heldere use-cases

### Ontbrekende elementen (nu expliciet gemaakt)

1. **Geen dataspace-abstractie**
   - FRLDS wordt gepositioneerd als dé oplossing
   - Terwijl het één van meerdere is

2. **Geen positionering t.o.v. FDS**
   - Terwijl dit expliciet complementair is fileciteturn0file1

3. **Te veel focus op techniek, te weinig op stelsel**
   - Dataspaces = governance + afspraken

4. **D-OmniTwin nog te veel als datahouder**
   - Moet verschuiven naar data-consument/orchestrator

---

## 7. Conclusie

De kerncorrectie is fundamenteel maar krachtig:

> **Je bouwt geen applicatie op een dataspace — je bouwt een applicatie die met dataspaces kan werken.**

Daarmee wordt:

- FRLDS = eerste, strategisch belangrijke implementatie
- D-OmniTwin = schaalbare interface voor meerdere dataspaces

En precies dát maakt jouw verhaal toekomstvast en opschaalbaar richting 2030.

---

## 8. Aanbevolen volgende stap

Werk een **dataspace-strategiepagina** uit waarin je:

- Concrete dataspaces inventariseert
- Per dataspace:
  - type data
  - governance
  - technische toegang
- En koppelt aan D-OmniTwin use-cases

Als je wilt, kan ik die volgende stap ook direct voor je uitwerken (inclusief visuele praatplaat).


# Technische Blauwdruk: Het Intelligente Kompas als Index voor LLM

Dit document biedt een integrale technische samenvatting van het voorgestelde systeem, waarbij de hiërarchische structuur van het **D-Omni Kompas** fungeert als het kwantitatieve en semantische fundament (**"Het Skelet"**) voor een lokaal Large Language Model (**"De Stem"**).

---

## 1. Conceptuele Architectuur: Skeleton & Voice

De kern van het systeem rust op de scheiding tussen feitelijke datastructuur en interpretatieve intelligentie:

- **Het Skelet (Wiskundige & Ontologische laag):** Een harde, hiërarchische structuur waarin data wordt genormaliseerd, gewogen en gerelateerd. Dit vormt de **Single Source of Truth**.

- **De Stem (LLM laag):** Een lokale AI-engine die deze structuur gebruikt als navigatie-index (RAG) om data te duiden, trends te verklaren en vragen van gebruikers te beantwoorden zonder te hallucineren.

---

## 2. Het Wiskundige Fundament (Kwantitatieve Laag)

Om heterogene datasets in één kompas te kunnen vangen, is een strikt wiskundig proces noodzakelijk.

### 2.1 Normalisatie & Transformatie

Datasets van verschillende aard (bijv. NO₂ concentraties in µg/m³ versus subjectieve bewonersenquêtes op een schaal van 1–10) worden getransformeerd naar een unitair domein **[0, 1]**.

Kwantitatieve (harde) en kwalitatieve (zachte) data krijgen hierbij hun eigen transformatieregels:

- Lineair
- Logaritmisch
- Ordinaal naar interval

---

### 2.2 Objectieve Weging (Methodieken)

In plaats van enkel subjectieve weging, wordt gebruikgemaakt van statistische methoden om de belangrijkheid van een indicator te bepalen:

- **Entropy-weging**  
  Meet de spreiding (informatiewaarde) binnen een dataset. Indicatoren met een hogere variatie krijgen een groter gewicht.

- **CRITIC (Criteria Importance Through Intercriteria Correlation)**  
  Bepaalt gewichten op basis van:
  - Contrastintensiteit
  - Onafhankelijkheid ten opzichte van andere criteria

- **Multivariate Analyse (PCA / LCA)**  
  Voor:
  - Reduceren van dimensionaliteit
  - Uitsluiten van dubbeltellingen

---

### 2.3 Aggregatie-algoritmes

Data stroomt van indicatoren naar thema’s en domeinen via:

- **Gewogen Rekenkundig Gemiddelde**  
  Voor lineaire opbouw.

- **Geometrische Aggregatie**  
  Voorkomt dat extreme scores andere indicatoren maskeren.

  Formule:

  $\prod x_i^{w_i}$

---

## 3. Ontologische Architectuur (Semantische Laag)

De structuur functioneert als een **Knowledge Graph**.

### 3.1 Semantische Annotatie

Elke dataset krijgt metadata via:

- JSON‑LD
- RDF

Voorbeeld:

- `fijnstof_pm25`
- Domein: Gezondheid
- Subcategorie: Luchtkwaliteit

Hierdoor begrijpt de AI de betekenis van data.

---

### 3.2 Taxonomie vs Ontologie

**Ontologie**

Een multidimensionaal relatienetwerk.

Voorbeeld:

Verkeersdrukte ↔ Geluidsbeleving

**Taxonomie**

De hiërarchische boomstructuur zichtbaar in de Sunburst visualisatie.

Functies:

- Navigatiestructuur
- Index voor AI

---

## 4. Uitvoerige Implementatiegids

---

### 4.1 Datastructuur (Single Source of Truth)

De backend genereert een gestandaardiseerd JSON‑object.

Functies:

- Input voor frontend visualisatie
- Input voor LLM context

Voorbeeld:

```json
{
  "id": "domein_fysieke_leefomgeving",
  "name": "Kwaliteit fysieke leefomgeving",
  "score_normalized": 0.68,
  "weight_aggregated": 0.35,
  "semantic_tags": ["milieu", "infrastructuur", "ruimte"],
  "children": [
    {
      "id": "thema_openbare_ruimte",
      "name": "Openbare Ruimte",
      "score_normalized": 0.82,
      "methodology": "CRITIC",
      "children": [
        {
          "id": "ind_groenvoorziening",
          "name": "M2 Groen per inwoner",
          "value_raw": 45.2,
          "unit": "m2",
          "score_normalized": 0.91,
          "weight": 0.12,
          "trend": "+5%",
          "data_type": "kwantitatief"
        }
      ]
    }
  ]
}
```

---

### 4.2 Python Backend Pipeline (Wiskundige Engine)

Technologie:

- pandas
- numpy
- scipy

#### Fase 1: Ingestie

- CSV
- SQL
- Missing value imputatie

#### Fase 2: Kwantificering

**Stap A: Min‑Max normalisatie**

$$
X_{norm} = \frac{X - X_{min}}{X_{max} - X_{min}}
$$

**Stap B: Entropy berekening**

Per indicator.

**Stap C: Gewicht berekening**

Methoden:

- Entropy
- CRITIC

---

#### Fase 3: Graph Bouw

Aggregatie van blad naar wortel.

Voorbeeld:

Geometrische aggregatie:

$$
\prod x_i^{w_i}
$$

Resultaat:

Kompas structuur JSON

---

### 4.3 API Specificaties

Framework:

- FastAPI
- Flask

Endpoints:

**GET /api/v1/kompas/tree**

Volledige structuur

**GET /api/v1/kompas/node/{id}**

Node detail

**POST /api/v1/llm/query**

LLM query endpoint

---

### 4.4 Lokale LLM & RAG Integratie

Doel:

Privacy‑vriendelijke AI interpretatie.

Technologie:

- Ollama
- vLLM
- Llama‑3
- Mistral

---

#### Stap 1: Query

Voorbeeld:

Waarom scoort fysieke leefomgeving slecht?

---

#### Stap 2: Data Retrieval

Zoek:

- juiste domein
- slechtst scorende indicatoren

---

#### Stap 3: Prompt constructie

Voorbeeld:

```
Je bent een data‑analist.

Score fysieke leefomgeving: 0.42

Negatieve indicatoren:

Luchtkwaliteit score: 0.21 gewicht: 0.4

Verkeersdrukte score: 0.30 gewicht: 0.2

Gebruik alleen deze data.
```

---

#### Stap 4: LLM Output

Resultaat:

- begrijpelijke uitleg
- wiskundig onderbouwd
- geen hallucinaties

---

## 5. Gefaseerde Aanpak voor Onderzoekstraject

---

### Maand 1‑2

Focus:

- Normalisatie
- Entropy
- CRITIC

Resultaat:

Python model

---

### Maand 3‑4

Focus:

- Aggregatie
- JSON structuur
- API

Resultaat:

Single Source of Truth

---

### Maand 5

Focus:

Proof of Concept LLM

Resultaat:

Werkende RAG demonstratie

---

## Conclusie

Het Kompas fungeert als:

- wiskundige waarheid
- semantische index
- AI navigatiestructuur

Hiermee ontstaat een transparant, uitlegbaar en betrouwbaar AI‑gedreven beslissysteem.

---

**Einde document**


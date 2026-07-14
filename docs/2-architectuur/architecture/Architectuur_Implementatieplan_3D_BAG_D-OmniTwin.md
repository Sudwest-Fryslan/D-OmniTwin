# Architectuur & Implementatieplan: 3D BAG in D-OmniTwin

> **Architectuurprincipe:** *Data staat centraal; visualisatie is een afgeleide.*

Dit document beschrijft de architectuur, ontwerpkeuzes en implementatie-roadmap voor het inladen en visualiseren van 3D-gebouwdata binnen D-OmniTwin met **Deck.gl** en **MapLibre**.

---

# 1. Visie & de rol van 3D

Binnen D-OmniTwin moet worden gewaakt voor een **3D-first**-benadering. Een gebouw is primair een **semantisch data-object**; de 3D-weergave is slechts één mogelijke visualisatie daarvan.

## 1.1 Het D-OmniTwin Data-object

```text
Gebouw (Data-object)
│
├── Administratief (BAG, BGT, WOZ)
├── Real-time (Sensoren, Energie)
├── Context (Indicatoren, Vergunningen, Documenten)
└── Visualisatie (3D-geometrie: LoD1.2 / LoD2.2)
```

## 1.2 Doel van 3D

### Scenario A – Visuele context (huidige focus)

LoD 1.2 biedt ruimtelijk inzicht en herkenning zonder af te leiden van de analyse. Dit is de standaard voor versie 1.

### Scenario B – Functionele analyse (toekomst)

Pas wanneer analyses afhankelijk zijn van dakvlakken (zoals zonnepotentie, bezonning of klimaatadaptatie) ontstaat een functionele noodzaak voor LoD 2.2.

## 1.3 Objectidentiteit

Alle koppelingen verlopen via de unieke **BAG-identificatie**. De geometrie is vervangbaar; de identiteit niet.

```text
BAG-ID
   ↓
Indicatoren
   ↓
WOZ / Sensoren
   ↓
3D-geometrie (Rendering)
```

---

# 2. Technische ontwerpprincipes

## 2.1 Triggerstrategie

3D wordt uitsluitend geladen wanneer:

- de gebruiker één of meerdere buurten selecteert **of** expliciet de 3D-weergave activeert;
- **én** het zoomniveau minimaal **16** bedraagt.

## 2.2 Level of Detail

| Zoom | Weergave |
|------:|----------|
| <14 | Geen gebouwen |
| 15 | 2D-footprints |
| 16–17 | LoD 1.2 extrusie (mits trigger actief) |
| ≥18 | Optioneel LoD 2.2 (Fase 2) |

## 2.3 BBOX-strategie

- Viewport + configureerbare buffer.
- Startwaarde: **25%** buffer.
- Buffer blijft configureerbaar zodat deze later op basis van monitoring kan worden geoptimaliseerd.

## 2.4 Performancebudget

Niet het aantal gebouwen, maar het **aantal vertices** bepaalt de belasting.

Wanneer het ingestelde vertex-budget wordt overschreden:

- wordt automatisch teruggeschakeld naar een lager detailniveau; of
- worden objecten progressief geladen.

## 2.5 Caching

**Frontend**

- LRU-cache (20 recente BBOX-opvragingen).

**Backend**

- Redis-cache of HTTP-caching voor veelgevraagde datasets.

## 2.6 Data-driven styling

**Standaard**

- Backend levert ruwe waarden.
- Deck.gl verzorgt de kleurtoekenning (`getFillColor`) client-side.

**Uitzondering**

Backend bepaalt de kleur uitsluitend wanneer reproduceerbare visualisaties vereist zijn (bijvoorbeeld PDF-exporten).

## 2.7 Fail-safe

Wanneer een 3D-bron tijdelijk niet beschikbaar is (bijvoorbeeld PDOK, WFS of 3D Tiles), schakelt D-OmniTwin automatisch terug naar 2D BAG-footprints. Hierdoor blijft de functionele analyse altijd beschikbaar.

## 2.8 Monitoring

Minimaal monitoren:

- gemiddelde laadtijd per BBOX-request;
- aantal vertices;
- requests per minuut;
- cache-hitratio (frontend/backend);
- payloadgrootte;
- geheugengebruik;
- FPS tijdens rendering.

---

# 3. LoD 2.2 versus WFS

LoD 2.2 is niet het probleem; de transportlaag is dat wel.

Het transporteren van grote LoD 2.2-datasets via **WFS + GeoJSON** is onvoldoende schaalbaar voor webtoepassingen vanwege payloadgrootte en parsingkosten in de browser.

Voor LoD 2.2 wordt daarom gekozen voor **OGC 3D Tiles** in combinatie met **Deck.gl Tile3DLayer**.

---

# 4. Gefaseerde roadmap

## Fase 1 – Visuele context (v1.0)

- LoD 1.2 extrusie
- Triggerlogica conform §2.1
- BBOX + buffer
- Vertex-budget
- Frontend caching
- Client-side styling
- Geen LoD 2.2

## Fase 1.5 – Optimalisatie

- Analyse monitoringgegevens
- Optimaliseren buffer- en vertexinstellingen
- UX-validatie bij eindgebruikers
- Vaststellen of LoD 2.2 daadwerkelijk meerwaarde biedt

## Fase 2 – Functionele analyse

Wordt uitsluitend gestart wanneer concrete use-cases daarom vragen.

- OGC 3D Tiles
- Deck.gl Tile3DLayer
- LoD 2.2 of hoger
- Dakvlakgebaseerde analyses
- Integratie met toekomstige BIM/Digital Twin-functionaliteit

---

# Conclusie

Voor D-OmniTwin is **LoD 1.2** de meest passende keuze voor de eerste implementatie. Deze levert voldoende ruimtelijke context, beperkte belasting op browser en netwerk en sluit aan bij de huidige gebruikersbehoefte.

Investeringen in **LoD 2.2** worden pas gedaan zodra functionele analyses aantoonbaar afhankelijk zijn van dakgeometrie. Daarmee blijft de architectuur schaalbaar, beheersbaar en in lijn met het uitgangspunt dat **data leidend is en visualisatie ondersteunend**.

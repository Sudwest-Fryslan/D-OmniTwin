# Architectuur & Implementatieplan: 3D BAG in D-OmniTwin

**Architectuurprincipe: Data staat centraal; visualisatie is een afgeleide.**

Dit document beschrijft de architectuur, ontwerpkeuzes en implementatie-roadmap voor het inladen en visualiseren van 3D-gebouwdata binnen D-OmniTwin (via Deck.gl en MapLibre).

## 1. Visie & De Rol van 3D in de Architectuur

Binnen D-OmniTwin moet gewaakt worden voor een "3D-first" valkuil. Een gebouw is in de basis **geen 3D-model**, maar een **semantisch data-object**.

### 1.1 Het D-OmniTwin Data-Object

De 3D-geometrie is slechts één van de vele eigenschappen (of visualisatielagen) van dit object:

    Gebouw (Data-Object)
    │
    ├── Administratief (BAG, BGT, WOZ)
    ├── Real-time (Sensoren, Energie)
    ├── Context (Indicatoren, Vergunningen, Documenten)
    └── Visualisatie (3D-geometrie: LoD1.2 / LoD2.2)

### 1.2 Het Doel van 3D: Visuele Context vs. Functionele Analyse

We maken expliciet onderscheid in het *waarom* we 3D laden:

* **Scenario A: Visuele context (Huidige Focus):** De gebruiker wil ruimtelijk gevoel en herkenning bij het bekijken van data (bijv. bouwjaar of energielabel per buurt). Hiervoor is **LoD 1.2 (geëxtrudeerde footprints)** perfect. Het is lichtgewicht en leidt niet af van de daadwerkelijke data.

* **Scenario B: Functionele analyse (Toekomst):** Zodra we analyses doen op dakvlakken (zonnepotentie, bezonning, wateropvang), is er functionele noodzaak voor daken. Pas dán is **LoD 2.2** relevant.

### 1.3 Objectidentiteit (De BAG-ID Koppeling)

De geometrie zelf is verwisselbaar. Alle 3D-objecten worden uitsluitend gekoppeld op basis van hun unieke BAG-identificatie. Dit garandeert dat data correct door het systeem vloeit, ongeacht het detailniveau van de visualisatie:

    BAG-ID 
      ↓
    Indicatoren 
      ↓
    WOZ / Sensoren 
      ↓
    3D-geometrie (Rendering)

## 2. Technische Ontwerpprincipes & Spelregels

Om te voorkomen dat GPU, netwerk en browsergeheugen onnodig volstromen, hanteren we strikte regels voor het inladen van 3D-data.

### 2.1 Wanneer laden we 3D? (Trigger Strategie)

3D-data wordt **nooit** standaard ingeladen op het volledige overzicht. Om tegenstrijdigheden te voorkomen, hanteren we de volgende strikte logica voor activering:

3D wordt alleen geladen en geëxtrudeerd indien:

* `(Gebruiker selecteert een buurt OF Gebruiker activeert de 3D-toggle expliciet)`
* **EN**
* `Zoomniveau >= 16`

### 2.2 Level of Detail (LoD) Zoom-Strategie

We implementeren dynamische detailniveaus gebaseerd op het zoomniveau (MapLibre `zoom`):

* **Zoom < 14:** Geen gebouwen (data verborgen/niet geladen).
* **Zoom 15:** 2D footprints (platte polygonen, puur voor locatie).
* **Zoom 16 - 17:** LoD 1.2 extrusie (blokken op basis van hoogte-attribuut, mits voldaan aan trigger in 2.1).
* **Zoom 18+:** *Optioneel (Fase 2)* LoD 2.2 rendering.

### 2.3 Bounding Box (BBOX) & Laad-Strategie

We stappen af van een harde limiet op het aantal gebouwen (`limit=10000`).

* **De Strategie:** Viewport + Buffer.
* **Uitvoering:** We sturen de huidige BBOX van het scherm naar de backend, inclusief een buffer (**initieel 25%, configureerbaar** om tuning mogelijk te maken) rondom de viewport.
* **Voordeel:** Dit voorkomt dat bij elke kleine pan-beweging (pannen) een nieuwe API-request nodig is, wat zorgt voor een veel vloeiendere gebruikerservaring.

### 2.4 Performance Budget (Vertices)

De complexiteit van polygonen varieert enorm.

* We hanteren een performance-budget gebaseerd op het **maximaal aantal vertices** per request/render, in plaats van een abstract aantal gebouwen.
* **Ingrijpen:** Wanneer het maximale vertex-budget wordt overschreden, wordt automatisch teruggevallen naar een lager detailniveau (bijv. 2D footprints) of worden objecten progressief geladen.

### 2.5 Caching Strategie

* **Frontend:** Een LRU (Least Recently Used) cache voor de laatste 20 opgevraagde BBOX-tegels.
* **Backend:** Redis-caching op veelgevraagde buurten of standaard API HTTP-caching.

### 2.6 Data-driven Styling (Kleur)

* **Default (Frontend):** De backend levert ruwe waarden. Deck.gl (`getFillColor`) berekent de kleur gradients dynamisch op de GPU. Dit is sneller en staat dynamisch filteren toe.
* **Uitzondering (Backend):** Backend-kleuring wordt alleen toegepast wanneer strikte *reproduceerbaarheid* vereist is (bijv. PDF-rapportages waarbij legenda's vastgespijkerd moeten zijn).

### 2.7 Fail-safe

Wanneer 3D-data niet beschikbaar is (PDOK traag, WFS uitgevallen, Tile-service onbereikbaar), schakelt D-OmniTwin automatisch en geruisloos terug naar **2D BAG-footprints**. Hierdoor blijft de functionele analyse van de indicatoren altijd beschikbaar voor de gebruiker.

### 2.8 Monitoring & Telemetrie

Om in latere fases datagedreven te kunnen optimaliseren, monitoren we standaard de volgende metrics bij het laden van 3D:

* Gemiddelde laadtijd per BBOX-request
* Aantal ingeladen vertices
* Aantal requests per minuut
* Cache hit ratio (Frontend/Backend)
* Payloadgrootte (MB's)
* Geheugenverbruik & FPS tijdens het renderen

## 3. Het "LoD 2.2 vs. WFS" Vraagstuk

De aanname dat "LoD 2.2 te zwaar is" behoeft nuance. LoD 2.2 geometrie op zichzelf is niet het probleem; **de transportlaag is het probleem**.
WFS + GeoJSON is fundamenteel ongeschikt om grote hoeveelheden complexe 3D-geometrie over het web te transporteren en in JavaScript te parsen. Voor LoD 2.2 is in de toekomst een gespecialiseerd format zoals **OGC 3D Tiles** noodzakelijk.

## 4. Gefaseerde Roadmap

Op basis van bovenstaande architectuur splitsen we de realisatie op in drie duidelijke fasen.

### Fase 1: Visuele Context (v1.0 - Huidige iteratie)

De focus ligt op stabiliteit, context en herkenning voor de gebruiker.

* **Model:** Extruded LoD 1.2 (2D polygonen met hoogte).
* **Triggers:** Volgens logica in 2.1 (Buurt/Actie + Zoom).
* **Data-fetch:** Viewport + configureerbare buffer (25%) middels BBOX loading.
* **Performance:** Frontend LRU Cache en vertex-budget.
* **Styling:** Client-side kleurberekening.
* **Besluit:** Géén LoD 2.2 daken.

### Fase 1.5: Optimalisatie & Telemetrie

Voordat de stap naar zwaardere modellen wordt gezet, consolideren we de architectuur.

* **Acties:** Analyseren van de verzamelde monitoring (FPS drops, cache-hits, API belasting).
* **Tuning:** Fijnstellen van de viewport buffer en vertex-budgetten.
* **UX:** Gebruikersfeedback verzamelen over de toegevoegde waarde van de 3D-weergave.

### Fase 2: Functionele Analyse (Toekomstvisie)

Wordt pas geïnitieerd zodra specifieke use-cases (bijv. klimaatadaptatie, bezonningsstudies, zonnepanelen-potentieel) ruimtelijke dakvlak-analyses vereisen.

* **Techniek:** Implementatie van OGC 3D Tiles via PDOK/TU Delft.
* **Rendering:** Overschakelen van `GeoJsonLayer` naar Deck.gl's `Tile3DLayer`.
* **Model:** LoD 2.2 (of hoger indien vereist door de BIM/Digital Twin use-case).
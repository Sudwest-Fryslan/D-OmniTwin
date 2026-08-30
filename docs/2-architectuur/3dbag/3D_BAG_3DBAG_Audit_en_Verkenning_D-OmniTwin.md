# 3D BAG / 3DBAG in D-OmniTwin — technische audit, gaps en verkenningsrichtingen

**Doel:** deze notitie gebruiken als context en werkdocument voor een agent die de 3DBAG-integratie van D-OmniTwin verder onderzoekt, valideert en optimaliseert.

**Bronbasis:**
- Officiële 3DBAG-documentatie: https://docs.3dbag.nl/nl/delivery/webservices/#3d-tiles
- Huidige D-OmniTwin-router: `bag3d.py`
- Bestaand architectuur- en implementatieplan: `Architectuur_Implementatieplan_3D_BAG_D-OmniTwin.md`

> **Belangrijk:** onderscheid altijd tussen wat rechtstreeks uit de officiële 3DBAG-bron volgt, wat uit de bestaande D-OmniTwin-code/documentatie volgt en wat een architecturale aanbeveling of hypothese is.

---

# 1. Kernconclusie

De huidige D-OmniTwin-integratie gebruikt de 3DBAG-service, maar benut de **3D Tiles-service niet**.

De huidige route is:

```text
Frontend
   ↓
D-OmniTwin FastAPI
   ↓
PostGIS → BBOX
   ↓
3DBAG API / CityJSONFeatures
   ↓
Python CityJSON decode
   ↓
GeoJSON Polygonen + hoogte-attributen
   ↓
Deck.gl
```

De router gebruikt momenteel:

```text
https://api.3dbag.nl/collections/pand/items
```

en verwerkt CityJSONFeatures naar GeoJSON.

Daarmee is de huidige oplossing technisch gezien vooral een **2D/2.5D-adapter**, niet een native 3D Tiles-integratie.

De officiële 3DBAG-documentatie beschrijft een aparte 3D Tiles-distributie die juist bedoeld is voor het streamen van grote heterogene 3D-geodata. 3DBAG stelt dezelfde tiles beschikbaar voor extern gebruik. De drie LoD's — **LoD1.2, LoD1.3 en LoD2.2** — worden als afzonderlijke tilesets aangeboden.

**Voor D-OmniTwin is daarom de belangrijkste architecturale verkenningsrichting:**

> Gebruik 3D Tiles als native visualisatie-/streaminglaag en houd D-OmniTwin verantwoordelijk voor de semantische data, indicatoren, analyses en styling.

---

# 2. Officiële feiten uit de 3DBAG-documentatie

De officiële documentatie stelt:

- 3DBAG heeft een 3D API die gebouwen met 3D-geometrie en attributen in CityJSONFeatures levert.
- De API ondersteunt een enkel gebouw op basis van BAG-identificatie of gebouwen binnen een BBOX.
- Bij meer dan 10 gebouwen worden API-resultaten gepagineerd.
- De 3DBAG API is momenteel nog niet OGC-compliant.
- De API ondersteunt momenteel EPSG:7415.
- 3D Tiles wordt door 3DBAG gebruikt voor de eigen viewer en wordt ook extern beschikbaar gesteld.
- LoD1.2, LoD1.3 en LoD2.2 zijn aparte 3D Tilesets.
- De tiles gebruiken 3D Tiles v1.1.
- Tileset en content gebruiken EPSG:4978.
- De content is binaire glTF (`.glb`).
- glTF-assets bevatten metadata per gebouw via `EXT_mesh_features` en `EXT_structural_metadata`.
- Gebouwen zijn in de tilesets uniform gekleurd.
- glTF-bestanden gebruiken compressie via `KHR_mesh_quantization` en `EXT_meshopt_compression`.
- De tileset gebruikt explicit tiling en external tilesets.
- Volgens de huidige documentatie zijn er momenteel geen beperkingen in gebruiksvolume, maar dit kan in de toekomst veranderen.
- De copyright notice is verplicht.

Deze eigenschappen maken 3D Tiles bijzonder relevant voor D-OmniTwin.

---

# 3. Wat de huidige router doet

## 3.1 Request

De router accepteert:

```python
class BAG3DRequest(BaseModel):
    gebied_ids: List[str]
    indicator_uuid: Optional[str]
```

De frontend geeft maximaal drie CBS-buurt-ID's door.

## 3.2 BBOX

PostGIS berekent een envelope van de geselecteerde gebieden:

```sql
ST_Envelope(ST_Collect(geom))
```

in EPSG:28992.

## 3.3 3DBAG API

De backend vraagt de 3DBAG REST API op met:

```text
bbox=minx,miny,maxx,maxy
```

## 3.4 CityJSON decode

De backend:

1. leest CityJSON vertices;
2. past `scale` en `translate` toe;
3. converteert RD New naar WGS84;
4. decodeert boundary indices;
5. zoekt Building-objecten;
6. maakt GeoJSON Polygonen.

## 3.5 Output

De backend retourneert:

```text
FeatureCollection
    Feature
        Polygon
        BAG-ID
        bouwjaar
        status
        dakhoogte
        maaiveldhoogte
        indicator_color
        indicator_waarde
```

De feitelijke 3D-geometrie wordt daarmee gereduceerd tot een 2D-polygonale representatie met hoogte-attributen.

---

# 4. Waarom de huidige aanpak kwetsbaar is

## 4.1 REST API als renderingbackend

De frontend is afhankelijk van:

```text
3DBAG → Python → decode → GeoJSON → browser
```

Dit introduceert:

- backend CPU-belasting;
- backend memorygebruik;
- extra latency;
- extra serialisatie;
- extra netwerkverkeer;
- eigen CityJSON-parser;
- eigen geometrische verwerking;
- extra foutoppervlak.

Voor een webviewer is dat niet ideaal.

## 4.2 Hard-coded API endpoint

De router gebruikt:

```python
REST_API_BASE = "https://api.3dbag.nl/collections/pand/items"
```

Dat maakt de integratie afhankelijk van de huidige API-vorm.

De officiële documentatie noemt de 3DBAG API bovendien nog niet OGC-compliant.

## 4.3 Eigen CityJSON decoder

De functie:

```python
_decode_cityjson_geometry(...)
```

implementeert zelf het decoderen van CityJSON-geometrie.

Dat is veel onderhoud voor functionaliteit die voor pure webvisualisatie mogelijk helemaal niet nodig is wanneer native 3D Tiles wordt gebruikt.

## 4.4 Geometrieverlies

De router maakt uiteindelijk:

```json
{
  "type": "Polygon"
}
```

Daarmee wordt de oorspronkelijke 3D-geometrie niet rechtstreeks aan de browser geleverd.

## 4.5 Beperkte paginering

De router gebruikt:

```python
MAX_PAGES = 3
```

en stopt bovendien zodra ongeveer 100 features zijn verzameld.

Dit is geschikt als snelle UI-beperking, maar betekent dat de huidige implementatie geen volledige ruimtelijke dataset kan representeren.

## 4.6 Energielabelmodus is nog niet geïmplementeerd

De architectuur bevat een energielabelmodus, maar de huidige code retourneert hiervoor:

```python
indicator_color = "#888888"
indicator_waarde = None
```

Dit is dus nog een stub.

## 4.7 Buurtkleur bij meerdere gebieden

De huidige kleurverrijking kan meerdere buurten ophalen, maar gebruikt vervolgens voor meerdere gebouwen dezelfde eerste buurtkleur.

De code doet conceptueel:

```python
eerste = list(buurt_kleuren.values())[0]
props["indicator_color"] = eerste["kleur"]
```

Dit kan functioneel onjuist zijn wanneer meerdere buurten tegelijk geselecteerd zijn.

---

# 5. Belangrijkste architectuurverschuiving

De gewenste richting is:

```text
                         D-OmniTwin
                              │
                 ┌────────────┴────────────┐
                 │                         │
             Analyse                 Visualisatie
                 │                         │
              PostGIS              ┌────────┴────────┐
                 │                 │                 │
                 │               2D BAG           3D BAG
                 │                 │                 │
                 │              GeoJSON         Tile3DLayer
                 │                                   │
                 └─────────────────┬─────────────────┘
                                   │
                            D-OmniTwin data
                                   │
                              GPU styling
```

De 3D-geometrie hoeft niet noodzakelijk via de D-OmniTwin-backend te lopen.

Een veel interessantere route is:

```text
Browser
   │
   └── Deck.gl Tile3DLayer
             │
             └── 3DBAG tileset.json
```

De D-OmniTwin-backend blijft dan verantwoordelijk voor:

- BAG-gerelateerde eigen data;
- indicatoren;
- semantische koppelingen;
- analyses;
- autorisatie indien nodig;
- configuratie;
- eventuele fallback;
- monitoring.

---

# 6. Waarom 3D Tiles hier waarschijnlijk beter past

3D Tiles is ontworpen voor streaming van grote 3D-geospatial datasets.

In plaats van:

```text
BBOX → hele dataset → backend → browser
```

wordt de viewport de feitelijke query:

```text
camera
  ↓
Tile3DLayer
  ↓
tileset
  ↓
relevante tiles
  ↓
GPU
```

Bij navigeren kan de client andere tiles laden.

Bij zoomen kan detailniveau veranderen.

Bij pannen kunnen nieuwe tiles worden geladen.

De tiling-structuur en compressie van 3DBAG zijn hier expliciet op ingericht.

Dit sluit goed aan op het bestaande D-OmniTwin-principe:

> Niet het aantal gebouwen, maar geometrische complexiteit en vertex-/renderingbelasting bepalen de performance.

---

# 7. Nieuwe LOD-strategie

Het bestaande architectuurplan noemt vooral:

```text
LoD1.2
LoD2.2
```

De officiële 3DBAG-distributie biedt echter:

```text
LoD1.2
LoD1.3
LoD2.2
```

Daarom moet **LoD1.3 expliciet worden meegenomen in de benchmark**.

Een eerste hypothese:

```text
zoom < 15
    → 2D

zoom 15–16
    → LoD1.2

zoom 16–18
    → LoD1.3

zoom > 18
    → LoD2.2
```

Maar LOD moet niet alleen op zoomniveau worden bepaald.

Een betere strategie is:

```text
                 LOD policy
                    │
          ┌─────────┴─────────┐
          │                   │
       camera              use case
          │                   │
       zoom/FOV          visualisatie/analyse
          │                   │
          └─────────┬─────────┘
                    ↓
                 LOD keuze
```

Voorbeelden:

- visuele context → LoD1.2;
- rijkere gebouwcontext → LoD1.3;
- dakvlak-/zonnepotentieanalyse → LoD2.2.

---

# 8. LoD1.3 is waarschijnlijk een belangrijke ontbrekende onderzoekslijn

Het huidige D-OmniTwin-plan maakt een vrij grote sprong:

```text
LoD1.2 → LoD2.2
```

Maar LoD1.3 kan mogelijk de optimale middenweg zijn.

Daarom expliciet benchmarken:

| Eigenschap | LoD1.2 | LoD1.3 | LoD2.2 |
|---|---:|---:|---:|
| Visuele herkenning | testen | testen | testen |
| Payload | meten | meten | meten |
| Tiles | meten | meten | meten |
| FPS | meten | meten | meten |
| GPU memory | meten | meten | meten |
| Picking | testen | testen | testen |
| Dakdetail | laag | midden | hoog |
| Analysepotentie | laag | midden | hoog |

Niet vooraf aannemen dat LoD2.2 noodzakelijk is.

---

# 9. Metadata is waarschijnlijk de grootste nieuwe kans

De officiële 3DBAG-documentatie vermeldt dat de glTF-assets gebouwmetadata bevatten via:

```text
EXT_mesh_features
EXT_structural_metadata
```

Dit moet worden onderzocht.

De cruciale vraag:

> Kunnen we vanuit Deck.gl / de gebruikte 3D Tiles-stack een geselecteerd 3DBAG-object koppelen aan zijn BAG-identificatie?

Als dat kan, ontstaat:

```text
klik op 3D gebouw
       ↓
BAG-ID
       ↓
D-OmniTwin datastore
       ↓
indicatoren / WOZ / energie /
vergunningen / sensoren / etc.
```

Dit is veel interessanter dan alleen "een 3D gebouw tonen".

Het maakt het 3D-object een visuele representatie van het D-OmniTwin data-object.

---

# 10. Objectidentiteit blijft centraal

Het bestaande architectuurdocument gebruikt:

```text
BAG-ID
   ↓
Indicatoren
   ↓
WOZ / sensoren
   ↓
3D-geometrie
```

Dat principe moet worden behouden.

De geometrie is vervangbaar.

De semantische identiteit niet.

Daarom moet worden onderzocht:

1. welke metadata 3DBAG in de tiles levert;
2. hoe deze metadata in Deck.gl beschikbaar komt;
3. of picking rechtstreeks een BAG-ID kan opleveren;
4. of er een stabiele mapping is tussen 3DBAG metadata en D-OmniTwin objectidentiteit;
5. hoe omgegaan wordt met ontbrekende of gewijzigde metadata.

---

# 11. Data-driven styling moet naar de client

Het bestaande architectuurplan stelt terecht:

> Backend levert ruwe waarden; Deck.gl verzorgt kleurtoekenning client-side.

Dat principe moet worden doorgetrokken naar 3D Tiles.

Gewenst patroon:

```text
3DBAG
   │
   └── geometry + BAG metadata
                │
                ▼
          D-OmniTwin
                │
          indicatorwaarde
                │
                ▼
          GPU / styling
                │
                ▼
           3D gebouw
```

Hierdoor kan dezelfde geometrie dynamisch worden gekleurd op basis van:

- bouwjaar;
- energielabel;
- WOZ;
- energiegebruik;
- klimaatindicator;
- wateroverlast;
- zonnepotentie;
- andere D-OmniTwin-indicatoren.

Zonder opnieuw 3D-geometrie op te halen.

---

# 12. Potentieel doelbeeld

```text
                    3DBAG
                      │
              3D Tiles 1.1
                      │
                      ▼
               Tile3DLayer
                      │
          ┌───────────┴───────────┐
          │                       │
      Geometry                Metadata
          │                       │
          │                    BAG-ID
          │                       │
          └───────────┬───────────┘
                      │
                      ▼
                 D-OmniTwin
                      │
              ┌───────┴────────┐
              │                │
         Indicatoren        Analyse
              │                │
              └───────┬────────┘
                      ▼
                GPU styling
                      │
                      ▼
                  3D gebouw
```

Dit past veel beter bij:

> Data staat centraal; visualisatie is een afgeleide.

---

# 13. Eigen backend-proxy: alleen wanneer nodig

Een directe frontendverbinding met 3DBAG is architectonisch interessant:

```text
Frontend
   │
   └── Tile3DLayer
            │
            └── 3DBAG
```

Voordelen:

- minder backend CPU;
- minder backend bandwidth;
- minder latency;
- geen CityJSON parsing;
- geen GeoJSON serialisatie;
- native tile streaming;
- native browser caching;
- minder eigen code.

Maar bouw in D-OmniTwin wel een abstractielaag, bijvoorbeeld:

```text
ThreeDBagProvider
```

zodat later kan worden gewisseld tussen:

```text
3DBAG direct
3DBAG proxy
eigen cache
eigen tiles
```

zonder dat de rest van de applicatie hiervan afhankelijk wordt.

---

# 14. BBOX-strategie opnieuw beoordelen

De huidige implementatie:

```text
gebied_ids
   ↓
PostGIS
   ↓
BBOX
   ↓
3DBAG API
```

is logisch voor de REST API.

Voor 3D Tiles hoeft dit niet noodzakelijk.

De tileset vormt zelf een ruimtelijke hiërarchie.

Daarom kan de viewport de selectie sturen:

```text
viewport
   ↓
tileset spatial hierarchy
   ↓
relevante tiles
```

De huidige BBOX-logica kan dan eventueel worden behouden voor:

- initialisatie;
- gebiedsbeperking;
- UX;
- autorisatie;
- fallback;
- analytics.

Maar niet noodzakelijk meer als primaire 3D-query.

---

# 15. Tile-index als aanvullende onderzoekslijn

3DBAG stelt naast de tilesets ook een tile-index beschikbaar als FlatGeobuf.

Dit verdient een aparte technische verkenning.

Mogelijk patroon:

```text
D-OmniTwin
   │
   │ ruimtelijke selectie
   ▼
3DBAG tile index
   │
   ▼
relevante 3D Tiles
   │
   ▼
Tile3DLayer
```

Dit kan interessant zijn wanneer D-OmniTwin expliciet wil afdwingen:

> laad alleen 3D voor geselecteerde buurten/gebieden.

Onderzoek dit pas nadat de native 3D Tiles-route is gevalideerd.

---

# 16. Performanceonderzoek

Niet alleen theoretisch beoordelen.

Voer een gecontroleerde benchmark uit.

## Testgebieden

Minimaal:

1. kleine buurt;
2. grote buurt;
3. dicht stedelijk gebied;
4. centrum Sneek;
5. meerdere buurten;
6. groot viewportgebied.

## Testvarianten

```text
A. huidige CityJSON → GeoJSON route
B. native 3D Tiles LoD1.2
C. native 3D Tiles LoD1.3
D. native 3D Tiles LoD2.2
```

## Meetwaarden

Minimaal:

- time-to-first-building;
- time-to-interactive;
- totale payload;
- aantal HTTP requests;
- aantal geladen tiles;
- aantal zichtbare gebouwen;
- CPU;
- GPU memory;
- browser memory;
- FPS;
- FPS tijdens pan;
- FPS tijdens zoom;
- FPS tijdens rotate;
- picking latency;
- cache-hitgedrag;
- netwerkbelasting;
- backend CPU;
- backend memory.

Het bestaande architectuurplan noemt al:

- gemiddelde laadtijd;
- aantal vertices;
- requests/minuut;
- cache-hitratio;
- payloadgrootte;
- geheugengebruik;
- FPS.

Die metrics moeten behouden blijven.

---

# 17. Test metadata/picking expliciet

Dit is een aparte acceptance test.

## Test

```text
3D gebouw aanklikken
       ↓
Tile3DLayer picking
       ↓
feature / metadata
       ↓
BAG-ID
       ↓
D-OmniTwin lookup
```

Acceptance criteria:

- BAG-ID betrouwbaar beschikbaar;
- geen afhankelijkheid van geometrische positie;
- geen fragiele parsing van interne objectnamen;
- meerdere gebouwen selecteerbaar;
- hover en click werken;
- selectie blijft correct bij LOD-wissel;
- selectie blijft correct na tile reload;
- metadata werkt bij verschillende LOD's.

---

# 18. Stylingonderzoek

De officiële 3DBAG-tiles zijn uniform gekleurd.

Daarom moet worden onderzocht hoe D-OmniTwin daar bovenop een data-driven style kan leggen.

Onderzoek minimaal:

1. Deck.gl `Tile3DLayer`;
2. picking;
3. feature metadata;
4. `getColor`/vergelijkbare stylingmogelijkheden;
5. shader-based styling indien nodig;
6. eventuele limitations van glTF/3D Tiles metadata;
7. performance van dynamische styling;
8. impact van veel verschillende kleuren/materials.

Niet automatisch aannemen dat gewone GeoJSON-achtige `getFillColor`-logica één-op-één werkt op 3D Tiles.

---

# 19. Fallbackarchitectuur

De bestaande architectuur heeft terecht een fail-safe:

```text
3D source unavailable
        ↓
2D BAG footprints
```

Dit principe moet behouden blijven.

Maar de nieuwe fallback-hiërarchie kan worden:

```text
             3D visualisatie
                    │
          ┌─────────┴──────────┐
          │                    │
     3D Tiles             fallback
          │                    │
      LoD2.2                 LoD1.3
          │                    │
      LoD1.3                 LoD1.2
          │                    │
      LoD1.2                 2D BAG
          │                    │
          └──────────┬─────────┘
                     ▼
                 2D footprint
```

Dit voorkomt dat een externe 3D-service de functionele analyse blokkeert.

---

# 20. Nieuwe voorgestelde roadmap

Het bestaande plan zou ik herstructureren.

## Fase 1 — Native 3D Tiles foundation

Doel:

- Tile3DLayer integreren;
- 3DBAG LoD1.2 streamen;
- camera-/zoomtrigger;
- basis caching;
- fallback naar 2D.

## Fase 1.1 — Metadata & picking

Onderzoeken:

- BAG-ID;
- feature metadata;
- selectie;
- hover;
- koppeling met D-OmniTwin.

## Fase 1.2 — LoD1.3

Benchmarken:

- kwaliteit;
- performance;
- gebruikerswaarde.

## Fase 1.5 — Performance optimisation

Optimaliseren:

- LOD thresholds;
- screen-space error;
- viewport;
- caching;
- tile loading;
- GPU budget;
- memory.

## Fase 2 — LoD2.2

Alleen activeren wanneer concrete use cases dit rechtvaardigen:

- zonnepotentie;
- dakvlakanalyses;
- bezonning;
- schaduwanalyse;
- klimaatadaptatie;
- toekomstige Digital Twin-functionaliteit.

---

# 21. Wat NIET doen

Niet als eindarchitectuur:

```text
3DBAG
  ↓
Python
  ↓
CityJSON decode
  ↓
GeoJSON
  ↓
Deck.gl
```

voor alle 3D-visualisatie.

Deze route kan wel behouden blijven als:

- fallback;
- specifieke objectquery;
- server-side export;
- analyse;
- debugging;
- data-extractie.

Maar niet als primaire streaminglaag.

Ook niet:

- alle 3DBAG-geometrie vooraf downloaden;
- alles naar GeoJSON converteren;
- alle gebouwen tegelijk in browsergeheugen laden;
- server-side kleur voor iedere indicator berekenen;
- LOD uitsluitend op zoom baseren;
- LoD2.2 automatisch overal activeren.

---

# 22. Concrete technische backlog

## Prioriteit P0 — servicecompatibiliteit

- [ ] Exact vaststellen welke 3DBAG-versie nu actief is.
- [ ] Huidige REST endpoint testen.
- [ ] Vaststellen waarom de bestaande integratie na de recente service-update niet meer werkt.
- [ ] API response vóór/na wijziging vergelijken.
- [ ] Nieuwe schema-/attribuutverschillen vastleggen.
- [ ] Fallbackgedrag testen.

## Prioriteit P0 — 3D Tiles proof of concept

- [ ] 3DBAG LoD1.2 tileset direct laden.
- [ ] Deck.gl Tile3DLayer integreren.
- [ ] Camera/viewport gedrag testen.
- [ ] 3DBAG tileset zonder eigen backend proxy laden.
- [ ] Browser network traffic inspecteren.
- [ ] Eerste performance benchmark uitvoeren.

## Prioriteit P1 — LOD

- [ ] LoD1.2 benchmark.
- [ ] LoD1.3 benchmark.
- [ ] LoD2.2 benchmark.
- [ ] LOD thresholds bepalen.
- [ ] Performancebudget bepalen.

## Prioriteit P1 — metadata

- [ ] `EXT_mesh_features` inspecteren.
- [ ] `EXT_structural_metadata` inspecteren.
- [ ] BAG-ID bepalen.
- [ ] Deck.gl picking testen.
- [ ] BAG-ID → D-OmniTwin lookup testen.
- [ ] LOD-onafhankelijke objectidentiteit testen.

## Prioriteit P1 — styling

- [ ] Uniforme 3DBAG kleur overschrijven.
- [ ] Indicatorwaarde koppelen.
- [ ] Client-side kleurstrategie testen.
- [ ] GPU-performance meten.
- [ ] Meerdere indicatoren dynamisch wisselen.

## Prioriteit P2 — tile index

- [ ] FlatGeobuf tile index onderzoeken.
- [ ] Ruimtelijke preselectie testen.
- [ ] Relatie tussen gebiedselectie en tiles bepalen.

## Prioriteit P2 — productiearchitectuur

- [ ] `ThreeDBagProvider` abstraction ontwerpen.
- [ ] Direct/proxy/cache strategie bepalen.
- [ ] Observability toevoegen.
- [ ] Circuit breaker/fallback toevoegen.
- [ ] Cachebeleid vastleggen.
- [ ] Serviceversies configureerbaar maken.

---

# 23. Gewenste eindarchitectuur

De voorkeursrichting is:

```text
                           D-OmniTwin
                                │
                ┌───────────────┴────────────────┐
                │                                │
             Data layer                     Visualization
                │                                │
             PostGIS                    MapLibre / Deck.gl
                │                                │
       ┌────────┴────────┐               ┌───────┴────────┐
       │                 │               │                │
   BAG/indicators    analytics       2D BAG           3D BAG
                                                       │
                                                  Tile3DLayer
                                                       │
                                                  3DBAG 3D Tiles
                                                       │
                                      ┌────────────────┴─────────────┐
                                      │                              │
                                  Geometry                       Metadata
                                      │                              │
                                      │                           BAG-ID
                                      │                              │
                                      └──────────────┬───────────────┘
                                                     │
                                                     ▼
                                               D-OmniTwin
                                                     │
                                               indicatoren
                                                     │
                                                     ▼
                                               GPU styling
```

Dit levert een duidelijke scheiding:

**3DBAG**
- levert geometrie;
- levert 3D Tiles;
- levert gebouwmetadata.

**D-OmniTwin**
- bepaalt betekenis;
- koppelt indicatoren;
- voert analyses uit;
- bepaalt visualisatie;
- beheert gebruikerscontext;
- bepaalt welke use case actief is.

**Browser/GPU**
- streamt;
- rendert;
- styled;
- selecteert.

---

# 24. Belangrijkste onderzoeksvragen voor een agent

Een agent die dit verder onderzoekt moet deze vragen in deze volgorde beantwoorden:

### A. Compatibiliteit

1. Wat is momenteel de exacte actieve 3DBAG tilesetversie?
2. Welke tileset-URLs zijn officieel beschikbaar?
3. Welke wijzigingen zijn recent aangebracht?
4. Waarom faalt de huidige CityJSON-integratie na de recente update?

### B. 3D Tiles

5. Hoe is de tileset-hiërarchie opgebouwd?
6. Hoe groot zijn de tiles?
7. Hoeveel gebouwen zitten gemiddeld per tile?
8. Welke `geometricError`/LOD-strategie wordt gebruikt?
9. Hoe werken external tilesets?
10. Hoe goed werkt dit met Deck.gl Tile3DLayer?

### C. Metadata

11. Welke metadata zit exact in `EXT_mesh_features`?
12. Welke metadata zit exact in `EXT_structural_metadata`?
13. Hoe wordt BAG-identificatie gerepresenteerd?
14. Kan Deck.gl dit uitlezen?
15. Is picking stabiel over LOD-wisselingen heen?

### D. Styling

16. Kan D-OmniTwin de uniforme 3DBAG kleur vervangen?
17. Welke Deck.gl API is hiervoor geschikt?
18. Is een custom shader nodig?
19. Wat is de performance-impact van dynamische styling?
20. Kunnen honderden/duizenden gebouwen tegelijk data-driven worden gestyled?

### E. Performance

21. Wat is de performance van LoD1.2?
22. Wat is de performance van LoD1.3?
23. Wat is de performance van LoD2.2?
24. Welke instelling bepaalt het beste performance/quality trade-off?
25. Hoeveel browser memory wordt gebruikt?
26. Hoeveel GPU memory?
27. Hoe werkt caching?
28. Wat gebeurt er bij snel pannen/zoomen?
29. Hoeveel requests ontstaan?
30. Wat gebeurt er bij meerdere gelijktijdige gebruikers?

### F. Architectuur

31. Is directe frontend→3DBAG de beste route?
32. Wanneer is een backend proxy nuttig?
33. Is een lokale cache zinvol?
34. Kan de tile index worden gebruikt voor preselectie?
35. Hoe bouwen we een abstraction zodat de provider later vervangen kan worden?

---

# 25. Voorlopige conclusie

De huidige implementatie is een bruikbare eerste adapter, maar benut de 3DBAG-capaciteiten niet optimaal.

De belangrijkste conclusie is:

> **Niet de bestaande CityJSON→GeoJSON-route verder uitbouwen als primaire 3D-renderingarchitectuur, maar native 3D Tiles serieus als nieuwe basislaag onderzoeken.**

De vermoedelijk sterkste combinatie voor D-OmniTwin is:

```text
3DBAG 3D Tiles
        +
BAG metadata
        +
D-OmniTwin semantische data
        +
Deck.gl GPU rendering
        +
2D BAG fallback
```

Daarmee blijft het architectuurprincipe overeind:

> **Data staat centraal; visualisatie is een afgeleide.**

De grootste technische onzekerheden die eerst empirisch moeten worden bewezen zijn:

1. **metadata/BAG-ID beschikbaarheid;**
2. **picking;**
3. **data-driven styling;**
4. **LoD1.2 versus LoD1.3 versus LoD2.2 performance;**
5. **directe frontendverbinding versus proxy;**
6. **impact van de recente 3DBAG-service-update op de huidige API.**

Pas nadat deze punten zijn getest, moet de definitieve productiearchitectuur worden vastgelegd.

---

# 26. Agent-instructie

Gebruik bij vervolgonderzoek altijd de officiële 3DBAG-documentatie als primaire bron:

```text
https://docs.3dbag.nl/nl/delivery/webservices/#3d-tiles
```

Maak onderscheid tussen:

- **Bronfeit:** rechtstreeks ondersteund door officiële 3DBAG-documentatie.
- **Codefeit:** vastgesteld uit de bestaande `bag3d.py`.
- **Architectuurfeit:** vastgesteld uit het bestaande D-OmniTwin-plan.
- **Hypothese:** voorgestelde richting die nog empirisch getest moet worden.

Doe geen aannames over:

- actuele tilesetversies;
- metadata-inhoud;
- BAG-ID mapping;
- Deck.gl picking;
- stylingmogelijkheden;
- performance;
- endpointstabiliteit;

zonder dit te verifiëren.

Bij wijzigingen aan de 3DBAG-service moet eerst worden vastgesteld **wat precies is gewijzigd**, voordat de bestaande code wordt aangepast.

De primaire onderzoeksvraag is niet:

> "Hoe repareren we de huidige API-integratie?"

maar:

> **"Wat is de technisch beste manier om de huidige en toekomstige 3DBAG 3D-capaciteiten maximaal te benutten in D-OmniTwin, met behoud van performance, semantische koppeling en architectonische onafhankelijkheid?"**

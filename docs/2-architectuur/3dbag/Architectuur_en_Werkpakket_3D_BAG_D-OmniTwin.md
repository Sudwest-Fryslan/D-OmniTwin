# Architectuur & Werkpakket: 3D BAG Panden Integratie in D-OmniTwin

**Documentstatus:** Geconsolideerde Architectuurblauwdruk & Definitief Werkpakket (v2.0)  
**Datum:** 28 augustus 2026  
**Auteurs:** AI Architecture Team & D-OmniTwin Core Team  
**Relevante Repository:** `D-OmniTwin` (`Sudwest-Fryslan/D-OmniTwin`)  
**Primaire Externe Bron:** [3DBAG Webservices Documentatie (TU Delft / 3DGI)](https://docs.3dbag.nl/nl/delivery/webservices/#3d-tiles)  
**Gerelateerde Bestanden:** `bag3d.py`, `static/js/app.js`, `docs/STATE.md`

---

## Inhoudsopgave

1. [Executive Summary & Kernconclusie](#1-executive-summary--kernconclusie)
2. [Visie & Architectuur-Guardrails D-OmniTwin](#2-visie--architectuur-guardrails-d-omnitwin)
3. [Audit van de Huidige Situatie (`bag3d.py`)](#3-audit-van-de-huidige-situatie-bag3dpy)
4. [Officiële 3DBAG 3D Tiles Specificaties (TU Delft / 3DGI)](#4-officiële-3dbag-3d-tiles-specificaties-tu-delft--3dgi)
5. [Doelarchitectuur: Geometrie en Semantiek Ontkoppeld](#5-doelarchitectuur-geometrie-en-semantiek-ontkoppeld)
6. [Technische Gaps & Oplossingsrichtingen](#6-technische-gaps--oplossingsrichtingen)
7. [LOD-Strategie & Performancebudget](#7-lod-strategie--performancebudget)
8. [Code Blauwdrukken (Backend & Frontend)](#8-code-blauwdrukken-backend--frontend)
9. [Governance, Resilience, Security & Fallback](#9-governance-resilience-security--fallback)
10. [Werkpakket 3D BAG Panden Integratie (Backlog & Taken)](#10-werkpakket-3d-bag-panden-integratie-backlog--taken)
11. [Acceptatiecriteria & Empirisch Validatieprotocol](#11-acceptatiecriteria--empirisch-validatieprotocol)

---

## 1. Executive Summary & Kernconclusie

De huidige 3D BAG-integratie in D-OmniTwin (`bag3d.py`) functioneert als een **backend-gedreven 2.5D-adapter**. De backend berekent bij buurtselectie een BBOX via PostGIS, bevraagt de 3DBAG REST API (`/collections/pand/items`), decodeert CityJSONFeatures met een custom Python parser naar GeoJSON Polygonen en stuurt deze verrijkt met hoogte en kleur naar de browser voor extrusie in Deck.gl.

### Waarom de huidige route is gebroken en onhoudbaar is
1. **Upstream Schema- en API-wijzigingen:** 3DBAG migreert naar OGC API Features standaarden. Wijzigingen in responsschema's of paginering laten custom Python-decoders direct crashen.
2. **Backend Server-Load:** Geometrie ophalen, transformeren en serialiseren via Python kost onnodige CPU-tijd, geheugen en veroorzaakt latency.
3. **Geometrieverlies:** Echte 3D-dakvormen (zoals dakschuinten en nokken) worden gereduceerd tot platte 2.5D footprints met hoogte-attributen.
4. **Schaalbaarheid:** Paginering is begrensd (`MAX_PAGES = 3`, max ~100 gebouwen), waardoor grote gebieden niet representatief getoond kunnen worden.

### Het Nieuwe Paradigma: Native 3D Tiles + Semantische Lookup
De gewenste architectuur kiest voor een **volledige ontkoppeling tussen 3D-geometrie en semantische data**:
- **3D Geometrie (3D Tiles v1.1):** Wordt door Deck.gl / MapLibre direct via binaire glTF (`.glb`) gestreamd vanaf de servers van 3DBAG / TU Delft.
- **Semantische Data (D-OmniTwin):** Wordt door FastAPI geleverd als een compacte lookup-tabel (`BAG-ID -> RGBA kleur & indicatorwaarde`).
- **GPU Data-Join & Picking:** Browser/Deck.gl voegt de geometrie en thematische indicatoren real-time samen en verzorgt gebouwselectie via `EXT_mesh_features` en `EXT_structural_metadata`.

```
                        +----------------------------------+
                        |      D-OmniTwin Frontend         |
                        |      (Deck.gl / MapLibre)        |
                        +-----------------+----------------+
                                          |
                     +--------------------+--------------------+
                     |                                         |
                     v                                         v
   +----------------------------------+      +----------------------------------+
   + 3D Tiles Streaming (.glb)        +      + Semantische Lookup Data          +
   + Bron: TU Delft / 3DBAG           +      + Bron: D-OmniTwin FastAPI         +
   + (LoD1.2 / LoD1.3 / LoD2.2)       +      + (BAG-ID -> Indicatoren / RGBA)   +
   +----------------------------------+      +----------------------------------+
                     |                                         |
                     +--------------------+--------------------+
                                          v
                        +----------------------------------+
                        |   GPU Rendering & Dynamic Style  |
                        |   + Interactive Feature Picking  |
                        +----------------------------------+
```

---

## 2. Visie & Architectuur-Guardrails D-OmniTwin

D-OmniTwin is een **gemeentelijk dataspace-platform / regie- en betekenislaag** voor Nederlandse gemeenten (gestart in Súdwest-Fryslân). Binnen dit platform geldt een strikt architectuurprincipe rond visualisatie:

> **Architectuurprincipe:** Data staat centraal; visualisatie is een afgeleide.

### Belangrijkste uitgangspunten:
- **Geen "3D-First" Valkuil:** Een gebouw is primair een **semantisch data-object** met een unieke sleutel (`BAG-ID`). De 3D-geometrie is slechts één van de mogelijke representaties.
- **Dataspace & Common Ground Alignment:** Bron blijft bron. D-OmniTwin slaat geen kopieën van externe 3D-geometrieën op als dat niet nodig is, maar koppelt indicatoren (WOZ, energielabel, demografie, sensoren, klimaat) aan de unieke ruimtelijke sleutel.
- **Methodiek & Referentie-implementatie:** D-OmniTwin wordt gepositioneerd als herbruikbare methodiek en referentie-implementatie voor gemeenten. Afhankelijkheden van specifieke servers of propriëtaire formats moeten vermeden worden.
- **Strikte Ontkoppeling:** Wijzigingen in 3D-visualisatielagen mogen nooit de analytische 2D-functionaliteit of het Kompas (12 thematische kwadranten) verstoren.

---

## 3. Audit van de Huidige Situatie (`bag3d.py`)

### 3.1 Huidige Dataflow (2.5D Adapter)
```text
Browser (Selecteert Buurten)
   ↓ POST /api/3dbag/buildings (gebied_ids)
FastAPI Backend (bag3d.py)
   ↓ PostGIS ST_Envelope(ST_Collect(geom))
BBOX Berekening (EPSG:28992)
   ↓ GET https://api.3dbag.nl/collections/pand/items?bbox=...
3DBAG REST API
   ↓ JSON (CityJSONFeatures)
Python Custom Decoder (_decode_cityjson_geometry)
   ↓ Coördinaat transformatie RD -> WGS84 + Extrusie berekening
GeoJSON FeatureCollection (Polygonen met dakhoogte & maaiveldhoogte)
   ↓ HTTP Response JSON
Deck.gl PolygonLayer / GeoJsonLayer (Extrudeert in Browser)
```

### 3.2 Geïdentificeerde Beperkingen & Knelpunten
| Aspect | Huidige Implementatie (`bag3d.py`) | Risico / Probleem |
| :--- | :--- | :--- |
| **API Endpoint** | Hardcoded REST API endpoint `https://api.3dbag.nl/collections/pand/items` | Kwetsbaar voor OGC API migraties en schema-aanpassingen door 3DBAG. |
| **Parsing** | Eigen Python CityJSON decoder | Onderhoudsgevoelig; breekt bij nieuwe CityJSON versies of attributen. |
| **Geometrie** | Converteert 3D meshes naar 2D GeoJSON polygonen met hoogte | Verlies van dakschuinten, nokken en dakkapellen (geen echte 3D representatie). |
| **Paginering** | Limiet van `MAX_PAGES = 3` en ~100 features | Grote buurten worden slechts gedeeltelijk geladen. |
| **Performance** | Server-side CPU & RAM zwaar belast | Hoge geheugendruk op FastAPI bij meerdere gelijktijdige verzoeken. |
| **Kleurlogica** | Server-side verrijking met buurtkleuren | Logica bevat bug waarbij eerste buurtkleur op alle panden wordt toegepast. |
| **Energielabel** | Stub-implementatie (`#888888`) | Functionaliteit voor energielabels is nog niet werkend. |

---

## 4. Officiële 3DBAG 3D Tiles Specificaties (TU Delft / 3DGI)

Volgens de officiële documentatie van de TU Delft en 3DGI biedt 3DBAG een volwaardige 3D Tiles webservice die uitstekend geschikt is voor directe client-side streaming:

- **OGC Standaard:** 3D Tiles v1.1.
- **Tiling Structuur:** Explicit tiling met externe hiërarchische sub-tilesets (`tileset.json`).
- **Coördinatenreferentiesysteem (CRS):** EPSG:4978 (WGS 84 ECEF). Deck.gl en MapLibre verzorgen de transformatie naar de camera-viewport.
- **Geometrieformaat:** Binaire glTF (`.glb`) embedded binnen de 3D Tiles.
- **Compressie:** Ondersteunt `KHR_mesh_quantization` en `EXT_meshopt_compression` voor minimale bandbreedte.
- **Feature Metadata:** glTF-bestanden bevatten gebouwattributen per pand via de extensies `EXT_mesh_features` en `EXT_structural_metadata`.
- **Kleurstelling Bron:** Gebouwen worden neutraal/uniform gekleurd aangeboden vanuit de bron.
- **Beschikbare LoD's (Level of Detail):**
  - **LoD1.2:** Blokmodellen met gemiddelde of maximale hoogte (`.../lod12/tileset.json`).
  - **LoD1.3:** Blokmodellen met gedetailleerde goot- en nokhoogtes (`.../lod13/tileset.json`).
  - **LoD2.2:** Gedetailleerde 3D-geometrie inclusief geobjectiveerde dakvlakken (`.../lod22/tileset.json`).

---

## 5. Doelarchitectuur: Geometrie en Semantiek Ontkoppeld

### 5.1 Architectuurschema
```text
                               ┌──────────────────────────────────┐
                               │       D-OmniTwin Frontend        │
                               │   (MapLibre GL / Deck.gl v9)     │
                               └────────────────┬─────────────────┘
                                                │
                      ┌─────────────────────────┴─────────────────────────┐
                      │                                                   │
                      ▼                                                   ▼
       ┌──────────────────────────────┐                    ┌──────────────────────────────┐
       │   3DBAG 3D Tiles Webservice  │                    │   D-OmniTwin FastAPI Backend │
       │   (TU Delft / 3DGI CDN)      │                    │   (/api/3dbag/styling-data)  │
       └──────────────┬───────────────┘                    └──────────────┬───────────────┘
                      │                                                   │
                      │  OGC 3D Tiles v1.1 (.glb)                         │  JSON Lookup Table
                      │  EPSG:4978 (WGS84 ECEF)                           │  { BAG-ID: [R,G,B,A] }
                      │                                                   │
                      └─────────────────────────┬─────────────────────────┘
                                                │
                                                ▼
                               ┌──────────────────────────────────┐
                               │       Deck.gl Tile3DLayer        │
                               ├──────────────────────────────────┤
                               │ 1. Streamt & Cacht 3D Tiles      │
                               │ 2. Leest BAG-ID via loaders.gl   │
                               │ 3. Matcht BAG-ID met Lookup      │
                               │ 4. Past Client/GPU Styling toe   │
                               │ 5. Handelt Click/Hover events af │
                               └──────────────────────────────────┘
```

### 5.2 Verdeling van Verantwoordelijkheden
1. **3DBAG (TU Delft / 3DGI):** Responsible for spatial indexing, 3D geometry generation, tile streaming, and base building metadata.
2. **D-OmniTwin Backend (FastAPI):** Geometrievrij! Vraagt PostGIS / indicator-tabellen te bevragen en levert uitsluitend een lichtgewicht mapping tussen `identificatie` (BAG-ID) en `[R, G, B, A]` kleurinformatie + indicatorwaarde.
3. **D-OmniTwin Frontend (Deck.gl / MapLibre):** Handelt de tegel-lifecycle af, past de LOD policy toe, voert de data-join uit in browsergeheugen/GPU, en stuurt de interactie (click/hover) aan.

---

## 6. Technische Gaps & Oplossingsrichtingen

De overgang naar 3D Tiles brengt drie specifieke technische uitdagingen met zich mee die empirisch gevalideerd moeten worden.

### Gap 1: Feature-Level Styling in Deck.gl `Tile3DLayer`
* **Probleem:** Anders dan bij `GeoJsonLayer` heeft `Tile3DLayer` in Deck.gl geen standaard `getFillColor: (feature) => ...` accessor voor individuele meshes binnen een glTF-tegel. `Tile3DLayer` rendert standaard de gehele 3D mesh met bronmaterials.
* **Oplossingsrichtingen:**
  - **Strategie A (Mesh Feature Uniforms via loaders.gl - Aanbevolen):** Met `@loaders.gl/3d-tiles` en `@loaders.gl/gltf` worden de `EXT_mesh_features` feature-IDs uitgelezen en via een GPU lookup-texture of uniform buffer gekoppeld aan de kleurentabel.
  - **Strategie B (3D Context + Gesynchroniseerde 2D Data-Overlay - Pragmatisch):** 3DBAG Tiles worden neutraal (lichtgrijs met schaduw/ambient occlusion) gerenderd voor ruimtelijke massa. Een transparante 2D Vector/GeoJSON-laag kleurt het grondvlak of de gebouw-footprint op basis van de actieve indicator.
  - **Strategie C (Custom Shader Injection):** Overschrijven van de fragment shader van `Tile3DLayer` (`_subLayerProps`) om op basis van attribute arrays of uniforms de geëxtraheerde feature-kleur in te spuiten.

### Gap 2: Objectidentiteit & Feature Picking
* **Probleem:** Bij een klik op een `Tile3DLayer` geeft Deck.gl standaard een `Tile3DHeader` als `info.object`, niet direct een gebouw-feature met `info.object.properties.identificatie`.
* **Oplossing:** Configureer loaders.gl opties expliciet in de `Tile3DLayer`:
  ```javascript
  loadOptions: {
    '3d-tiles': { loadGLTF: true },
    gltf: { loadMeshFeatures: true, loadStructuralMetadata: true }
  }
  ```
  In `onClick` en `onHover` wordt via `info.featureId` en de `structuralMetadata` tabel de unieke BAG-identificatie (`NL.IMBAG.Pand.xxxx`) opgevraagd.

### Gap 3: LOD Hot-Swapping
* **Probleem:** Omdat LoD1.2, LoD1.3 en LoD2.2 als gescheiden tilesets door 3DBAG worden aangeboden, kan de frontend niet leunen op interne tileset-refinement van één enkele tileset.
* **Oplossing:** D-OmniTwin beheert een **LOD Policy Engine** die de zichtbaarheid (`visible: boolean`) van de afzonderlijke `Tile3DLayer` instanties stuurt op basis van camera-afstand, pitch en de actieve functionele analyse.

---

## 7. LOD-Strategie & Performancebudget

### 7.1 Dynamic LOD Switching Matrix

| Visualisatiemodus | Zoomniveau (MapLibre) | Actieve 3D/2D Laag | Bron URL / Endpoint | Functioneel Doel |
| :--- | :--- | :--- | :--- | :--- |
| **Macro Context** | `< 15.0` | 2D Vector Tiles (MVT) | `/api/tiles/panden/{z}/{x}/{y}.pbf` | Stadsdeelniveau, maximale FPS |
| **Standaard 3D** | `15.0 - 16.5` | 3D Tiles **LoD1.2** | `.../lod12/tileset.json` | Snelle extrusie met platte daken, minimale payload |
| **Rijke Context** | `16.5 - 18.0` | 3D Tiles **LoD1.3** | `.../lod13/tileset.json` | Dakschuinten, nok- en goothoogtes; herkenning |
| **Analyse Modus** | $\ge 18.0$ (of toggle) | 3D Tiles **LoD2.2** | `.../lod22/tileset.json` | Gedetailleerde daken; zonnepotentie & bezonning |

### 7.2 Performancebudget & Kwaliteits-Metrics
De performance van de 3D-viewer wordt getoetst aan de volgende meetbare grenswaarden:

- **Time to First Building (TTFB):** $< 1.5$ seconde na gebiedselectie.
- **Frame Rate (FPS):**
  - Idle / Stilstaand: $\ge 60\text{ FPS}$
  - Pan / Rotate / Zoom: $\ge 45\text{ FPS}$ (minimaal $30\text{ FPS}$ op mobiel/budget hardware).
- **Geheugenbudget:**
  - GPU Memory Toename: $< 350\text{ MB}$ voor een gemiddelde woonbuurt.
  - Maximum Memory Cache Size (`maximumMemoryCacheSize`): 512 MB.
- **Screen-Space Error Control:** `maximumScreenSpaceError` ingesteld op `16` voor LoD1.2/1.3 en `8` voor LoD2.2.

---

## 8. Code Blauwdrukken (Backend & Frontend)

### 8.1 Backend FastAPI Router (`routers/router_3dbag_data.py`)

Deze nieuwe router vervangt de oude geometrie-berekeningen in `bag3d.py`. Het levert uitsluitend een compacte lookup-tabel.

```python
"""
3DBAG Semantische Data Provider Router voor D-OmniTwin
Retourneert uitsluitend semantische indicatoren en kleur-lookups per BAG-ID.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict
import logging

from src.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/3dbag",
    tags=["3D BAG Semantische Data Provider"]
)

# ============================================================================
# Schemas
# ============================================================================

class StylingDataRequest(BaseModel):
    gebied_ids: List[str] = Field(..., min_length=1, max_length=10, description="CBS Buurt-IDs")
    indicator_uuid: Optional[str] = Field(None, description="UUID van de actieve indicator")
    jaar: Optional[int] = Field(None, description="Peiljaar voor de gegevens")

class PandStylingRecord(BaseModel):
    waarde: Optional[float] = None
    kleur: List[int] = Field(..., description="RGBA vector: [R, G, B, A] (0-255)")
    label: Optional[str] = None

# ============================================================================
# Dynamic Color Scale Helpers
# ============================================================================

BOUWJAAR_DREMPELS = [
    (1900, [139, 0, 0, 255]),     # Donkerrood
    (1945, [192, 57, 43, 255]),   # Rood
    (1960, [231, 76, 60, 255]),   # Lichtrood
    (1975, [230, 126, 34, 255]),  # Oranje
    (1990, [241, 196, 15, 255]),  # Geel
    (2005, [46, 204, 113, 255]),  # Lichtgroen
    (9999, [39, 174, 96, 255]),   # Donkergroen
]

def resolve_bouwjaar_kleur(jaar: Optional[int]) -> List[int]:
    if not jaar:
        return [128, 128, 128, 180] # Grijs neutraal
    for drempel, rgba in BOUWJAAR_DREMPELS:
        if jaar <= drempel:
            return rgba
    return [39, 174, 96, 255]

# ============================================================================
# Endpoints
# ============================================================================

@router.post("/styling-data", response_model=Dict[str, PandStylingRecord])
async def get_3d_styling_data(
    payload: StylingDataRequest,
    db: Session = Depends(get_db)
):
    """
    Levert een compacte Lookup Table voor Deck.gl.
    Sleutel: BAG Identificatie (bijv. 'NL.IMBAG.Pand.0363100012165538')
    Waarde: RGBA-kleurvector en indicatorwaarde.
    """
    lookup: Dict[str, PandStylingRecord] = {}

    try:
        query = text("""
            SELECT 
                p.identificatie,
                p.bouwjaar,
                pd.waarde as indicator_waarde
            FROM panden p
            LEFT JOIN pand_indicatoren pd 
                ON pd.pand_identificatie = p.identificatie 
                AND pd.indicator_uuid = :indicator_uuid
            WHERE p.buurt_id = ANY(:buurt_ids)
        """)
        
        rows = db.execute(query, {
            "buurt_ids": payload.gebied_ids,
            "indicator_uuid": payload.indicator_uuid
        }).fetchall()

        for row in rows:
            val = float(row.indicator_waarde) if row.indicator_waarde is not None else (float(row.bouwjaar) if row.bouwjaar else None)
            kleur = resolve_bouwjaar_kleur(row.bouwjaar)
            
            lookup[row.identificatie] = PandStylingRecord(
                waarde=val,
                kleur=kleur,
                label=str(row.bouwjaar) if row.bouwjaar else "Onbekend"
            )

        return lookup

    except Exception as e:
        logger.error(f"Fout bij genereren 3D styling lookup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Fout bij ophalen semantische stylingdata.")

@router.get("/config")
async def get_3dbag_config():
    """Centraal configuratiebeheer voor 3DBAG endpoints en releaseversie."""
    return {
        "provider": "3DBAG (TU Delft / 3DGI)",
        "version": "v20250903",
        "tilesets": {
            "lod12": "https://data.3dbag.nl/v20250903/cesium3dtiles/lod12/tileset.json",
            "lod13": "https://data.3dbag.nl/v20250903/cesium3dtiles/lod13/tileset.json",
            "lod22": "https://data.3dbag.nl/v20250903/cesium3dtiles/lod22/tileset.json"
        },
        "crs": "EPSG:4978",
        "attribution": "© 3DBAG by 3DGI and TU Delft (CC BY 4.0)"
    }
```

### 8.2 Frontend Deck.gl Layer Integration (`static/js/layers/bag3d_layer.js`)

```javascript
/**
 * 3DBAG Native Tile3DLayer Integratie voor D-OmniTwin
 */
import { Tile3DLayer } from '@deck.gl/geo-layers';
import { Tiles3DLoader } from '@loaders.gl/3d-tiles';

/**
 * Fabrieksfunctie voor de 3DBAG Tile3DLayer
 */
export function create3DBagLayer({
  lod = 'lod12',
  tilesetConfig,
  indicatorLookup = {},
  visible = true,
  onBuildingClick,
  onBuildingHover
}) {
  return new Tile3DLayer({
    id: `3dbag-layer-${lod}`,
    data: tilesetConfig.tilesets[lod],
    loader: Tiles3DLoader,
    visible: visible,
    pickable: true,
    
    // Performance parameters
    maximumScreenSpaceError: lod === 'lod22' ? 8 : 16,
    maximumMemoryCacheSize: 512,
    
    // Loaders.gl configuratie voor glTF metadata extensies
    loadOptions: {
      '3d-tiles': {
        loadGLTF: true,
        decodeQuantizedPositions: true
      },
      gltf: {
        loadMeshFeatures: true,
        loadStructuralMetadata: true,
        postProcess: true
      }
    },

    // Interactie & Metadata Resolutie
    onClick: (info) => {
      if (!info || !info.object) return;
      const bagId = extractBagIdFromTileFeature(info);
      if (bagId && onBuildingClick) {
        onBuildingClick(bagId, indicatorLookup[bagId]);
      }
    },

    onHover: (info) => {
      if (!info || !info.object) return;
      const bagId = extractBagIdFromTileFeature(info);
      if (onBuildingHover) {
        onBuildingHover(bagId, info.x, info.y);
      }
    }
  });
}

/**
 * Hulpfunctie om BAG-identificatie robuust uit EXT_mesh_features te halen
 */
function extractBagIdFromTileFeature(info) {
  // 1. Direct uit feature properties (indien geparseerd)
  if (info.object?.properties?.identificatie) {
    return info.object.properties.identificatie;
  }
  
  // 2. Uit structural metadata tabel via feature ID
  if (info.object?.structuralMetadata && info.featureId !== undefined) {
    const table = info.object.structuralMetadata.tables?.[0];
    if (table && table.identificatie) {
      return table.identificatie[info.featureId];
    }
  }

  // 3. Fallback op object identifier string uit header
  if (typeof info.object?.id === 'string' && info.object.id.startsWith('NL.IMBAG.Pand.')) {
    return info.object.id;
  }

  return null;
}
```

---

## 9. Governance, Resilience, Security & Fallback

### 9.1 Fallbackhiërarchie (Graceful Degradation)
Als de externe 3DBAG 3D Tiles webservice onbereikbaar is of een fout retourneert, degradeert D-OmniTwin automatisch volgens het onderstaande schema zonder de functionele 2D-analyse of Kompas-kaarten te blokkeren:

```text
                  [ 3D Visualisatie Request ]
                               │
                               ▼
                   [ 3D Tiles LoD2.2 Available? ]
                   ├── JA  ──> Render LoD2.2 Mesh
                   └── NEE ──> [ 3D Tiles LoD1.3 Available? ]
                               ├── JA  ──> Render LoD1.3 Mesh
                               └── NEE ──> [ 3D Tiles LoD1.2 Available? ]
                                           ├── JA  ──> Render LoD1.2 Mesh
                                           └── NEE ──> [ Fallback naar 2D BAG Footprints ]
                                                       (Render 2D Extruded GeoJSON)
```

### 9.2 Attributie & Auteursrecht
Conform de gebruiksvoorwaarden van 3DBAG (CC BY 4.0) dient op het kaartscherm in de attributie-overlay expliciet de volgende bronvermelding te worden opgenomen:
> **"© 3DBAG by 3DGI and TU Delft (CC BY 4.0)"**

### 9.3 Releaseversiebeheer
3DBAG publiceert regelmatig nieuwe versies (bijv. `v20250903`). Endpoint-URL's mogen **niet** hardcoded in frontend-scripts staan, maar worden centraal opgehaald via de `/api/3dbag/config` endpoint of milieuvoorkeuren (`.env`).

### 9.4 Security & Web Standards
- **CORS / CSP:** Verifieer dat Content Security Policy header (`connect-src`) de domeinen `https://data.3dbag.nl` en `https://api.3dbag.nl` toestaat.
- **Provider Abstraction (`ThreeDBagProvider`):** De frontend gebruikt een provider-interface zodat in de toekomst probleemloos kan worden overgeschakeld naar een eigen proxy of lokale cache indien 3DBAG volumelimieten zou invoeren.

---

## 10. Werkpakket 3D BAG Panden Integratie (Backlog & Taken)

Het onderstaande werkpakket vormt de concrete backlog voor de realisatie van de v2.0 3D BAG-architectuur in D-OmniTwin.

```text
                                 [ WERKPAKKET OVERZICHT ]
                                             │
      ┌──────────────────┬───────────────────┼───────────────────┬──────────────────┐
      │                  │                   │                   │                  │
      ▼                  ▼                   ▼                   ▼                  ▼
  [ Fase 0 ]         [ Fase 1 ]          [ Fase 2 ]          [ Fase 3 ]         [ Fase 4 ]
  Audit & Oorzaak    Foundation &        Metadata, Picking   LOD Policy &       LoD2.2 & Prod
  Bestaande Breuk    Ontkoppeling        & Styling           Performance        Hardening
```

---

### Fase 0: Audit & Oorzaak Bestaande Breuk (P0 - Direct)
- [ ] **TAAK 0.1:** Reproduceer het falen van de huidige `bag3d.py` router tegen de actuele upstream 3DBAG REST API.
- [ ] **TAAK 0.2:** Leg de exacte schema- of pagineringswijziging in de upstream API vast ( CityJSONFeatures response vergelijken).
- [ ] **TAAK 0.3:** Markeer de oude CityJSON decodering in `bag3d.py` als deprecated en bereid de router voor op de nieuwe `/api/3dbag/styling-data` specificatie.

### Fase 1: Native 3D Tiles Foundation & Ontkoppeling (P0 - Sprint 1)
- [ ] **TAAK 1.1:** Implementeer de nieuwe FastAPI endpoints `/api/3dbag/styling-data` en `/api/3dbag/config` in backend (geometrievrije functionaliteit).
- [ ] **TAAK 1.2:** Voeg centrale omgevingsvariabelen toe voor 3DBAG releaseversie (`THREEDBAG_VERSION=v20250903`).
- [ ] **TAAK 1.3:** Integreer Deck.gl `Tile3DLayer` in de frontend met ondersteuning voor de 3DBAG LoD1.2 tileset (`tileset.json`).
- [ ] **TAAK 1.4:** Voeg de verplichte copyrightattributie toe aan het kaartscherm: *"© 3DBAG by 3DGI and TU Delft (CC BY 4.0)"*.
- [ ] **TAAK 1.5:** Valideer de correcte CRS-projectie (EPSG:4978 naadloos geprojecteerd over MapLibre EPSG:3857/WGS84).

### Fase 2: Feature Metadata, Picking & Client-Side Styling (P1 - Sprint 2)
- [ ] **TAAK 2.1:** Configureer loaders.gl opties (`loadMeshFeatures`, `loadStructuralMetadata`) in `Tile3DLayer`.
- [ ] **TAAK 2.2:** Realiseer de helper-functie `extractBagIdFromTileFeature` en toets of een gebouw-klik betrouwbaar het unieke `BAG-ID` retourneert.
- [ ] **TAAK 2.3:** Koppel de gedetecteerde `BAG-ID` aan het D-OmniTwin gebouwdetailpaneel en Kompas indicatoren.
- [ ] **TAAK 2.4:** Voer een PoC uit voor styling-strategie A (Mesh Feature Uniforms) vs Strategie B (3D Context + 2D Indicator Overlay) en kies het definitieve stylingmechanisme.
- [ ] **TAAK 2.5:** Koppel dynamische kleurschalen (zoals Bouwjaar en Energielabel) client-side aan de geladen 3D-gebouwen.

### Fase 3: LOD Policy & Performance Benchmarking (P1 - Sprint 2)
- [ ] **TAAK 3.1:** Bouw de **LOD Policy Engine** in frontend voor dynamische hot-swapping tussen 2D Vector Tiles, LoD1.2 en LoD1.3 op basis van zoomniveau en camera-pitch.
- [ ] **TAAK 3.2:** Voer een uitgebreide performance-benchmark uit in Sneek Binnenstad (FPS, GPU-geheugen, payload, TTFB).
- [ ] **TAAK 3.3:** Evalueer de visuele en analytische meerwaarde van **LoD1.3** t.o.v. LoD1.2 voor standaard dashboardgebruik.
- [ ] **TAAK 3.4:** Optimaliseer `maximumScreenSpaceError` en `maximumMemoryCacheSize` instellingen voor soepele pan-/zoominteracties.

### Fase 4: Geavanceerde Use Cases, LoD2.2 & Productie-Hardening (P2 - Sprint 3)
- [ ] **TAAK 4.1:** Voeg ondersteuning toe voor de **LoD2.2** tileset uitsluitend bij specifieke zonnepotentie- of dakvlakanalyses.
- [ ] **TAAK 4.2:** Implementeer het automatische fallback-mechanisme naar 2D GeoJSON-footprints bij externe netwerkstoringen naar `data.3dbag.nl`.
- [ ] **TAAK 4.3:** Voeg client-side caching toe voor de `/api/3dbag/styling-data` antwoorden om overtollige netwerk-requests te voorkomen.
- [ ] **TAAK 4.4:** Werk de projectdocumentatie en `docs/STATE.md` bij met de definitieve 3D BAG architectuur en API-specificaties.

---

## 11. Acceptatiecriteria & Empirisch Validatieprotocol

De migratie naar 3D BAG v2.0 geldt pas als afgerond wanneer aan alle onderstaande acceptatiecriteria is voldaan:

1. **Geometrische Rendering & Performance:**
   - 3D Tiles LoD1.2 en LoD1.3 streamen vloeiend zonder merkbare haperingen ($\ge 45\text{ FPS}$ tijdens rotatie).
   - Time to First Building (TTFB) is minder dan 1.5 seconde bij selectie van een nieuwe buurt.
   - De FastAPI backend vertoont 0% CPU-belasting voor geometrie-decodering of GeoJSON-conversie tijdens 3D-streaming.
2. **Semantische Koppeling & Picking:**
   - Klikken op een 3D-gebouw identificeert betrouwbaar de unieke BAG-sleutel (`identificatie`).
   - Het selecteren van een 3D-gebouw opent synchroon het juiste D-OmniTwin indicatorpanel.
   - Dynamisch wisselen van indicator (bijv. Bouwjaar $\rightarrow$ Energielabel) werkt binnen $100\text{ ms}$ zonder dat de 3D-geometrie opnieuw gedownload hoeft te worden.
3. **Resilience & Governance:**
   - Bij een gesimuleerde uitval van `data.3dbag.nl` schakelt de applicatie zonder foutmeldingen over op 2D-extrusie/footprints.
   - De copyrightvermelding *"© 3DBAG by 3DGI and TU Delft (CC BY 4.0)"* is correct en zichtbaar op het kaartscherm aanwezig.
   - Alle 3DBAG release-instellingen worden centraal beheerd via de `/api/3dbag/config` API.

# Concept & Visie: Kompas Taxonomie Studio
**Visueel beheer van de Kompas-taxonomie, themaboom en indicatoren**

**Datum:** 2026-11-20  
**Initiatiefnemer:** Taeke van der Laan (CDO, Súdwest-Fryslân)  
**Status:** Concept / Braindump / RFC  
**Doel-mijlpaal:** 0.8.0 (of vervolgversie na 0.7.0)  
**Locatie:** `docs/4-ux-design/concept-visueel-taxonomie-indicatorenbeheer.md`

---

## 1. Aanleiding & Kernidee

In het huidige beheerpaneel (`admin-panel/`) zijn drie nauw verwante onderdelen historisch als losse pagina's opgezet:
1. **Indicatoren** (`/admin/indicatoren`): een platte tabel met ~267 indicatoren, zoekbalk, paginering en een editor voor metadata, polariteit en ontologie.
2. **Hiërarchie** (`/admin/hierarchie`): een D3 collapsible tree van de Kompas-taxonomie (Configuratie → Titels/Kwadranten → Thema's → Onderdelen → Indicatoren), maar puur als leesweergave zonder bewerkmogelijkheden.
3. **Data Kwaliteit** (`/admin/data-kwaliteit`): deduplicatie van indicatoren (`deduplicatie_service.py`), data lineage checks en aggregatie-audits.

### Het Inzicht
In werkelijkheid is een indicator geen losstaande entiteit in een platte tabel, maar een meetpunt dat zijn betekenis en gewicht ontleent aan de **taxonomie van het Kompas**:
```
[4 Kwadranten] → [12 Thema's] → [Onderdelen] → [Indicatoren]
```

Het idee is om de taxonomie visueel tot leven te wekken in een **bol-, graaf- of radial-hiërarchie (Kompas Taxonomie Studio)**, waarin een beheerder direct op elk niveau kan navigeren, inzoomen en bewerken.

---

## 2. Visueel Model: De Bol / Graaf / Sunburst

In plaats van een statische tekstboom of een platte tabel toont het scherm een interactieve visualisatie die aansluit bij de vormentaal van het D-Omni Kompaswiel:

### Visualisatie-opties
1. **Zoomable Sunburst / Radial Wheel:**
   - Sluit 1-op-1 aan bij het Kompaswiel in de viewer.
   - Binnenring: de 4 hoofdkwadranten (*Kwaliteit van de fysieke leefomgeving*, *Kwaliteit van de sociale leefomgeving*, *Kwaliteit van leven*, *Bestuur & Middelen*).
   - Ring 2: de 12 thematische taartpunten (*Veiligheid*, *Gezondheid*, *Wonen*, *Milieu*, etc.).
   - Ring 3: de functionele onderdelen.
   - Buitenste schil / bolletjes: de individuele indicatoren.
2. **Collapsible Radial Tree / Circle Packing (Bol-hiërarchie):**
   - Knooppunten als bollen die uitwaaieren of inzoomen bij doorklikken.
   - Geeft veel overzicht over de omvang en verdeling van indicatoren per thema.

```
       ┌────────────────────────────────────────────────────────┐
       │                Kompas Taxonomie Studio                 │
       ├──────────────────────────┬─────────────────────────────┤
       │                          │                             │
       │     VISUELE GRAAF / BOL  │    CONTEXTUELE INSPECTOR    │
       │                          │                             │
       │         (Kwadrant)       │  Geselecteerd knooppunt:    │
       │            /    \        │                             │
       │       (Thema)  (Thema)   │  [Indicator / Thema / Kw.]  │
       │        /   \             │                             │
       │     (Ond) (Ond)          │  • Naam & code              │
       │      /                   │  • Status: Actief / Inactief│
       │   [Ind]                  │  • Polariteit & Schema      │
       │                          │  • Bron & Lineage           │
       │   [+] Zoom in / uit      │  • Validatie & Notities     │
       │   [ Weergave: Graaf |    │                             │
       │               Tabel ]    │  [ Opslaan ] [ Deactiveren] │
       └──────────────────────────┴─────────────────────────────┘
```

---

## 3. Directe Interactie op Elk Niveau

Wanneer een beheerder op een knooppunt klikt, toont de rechter inspector direct de relevante beheeropties voor dat specifieke niveau:

1. **Op Indicator-niveau:**
   - Direct bewerken van metadata (naam, omschrijving, eenheid, bron).
   - Polariteit instellen (`hoger_is_beter`, `lager_is_beter`, `neutraal`).
   - Actief / inactief zetten (`is_actief`, conform issue #526).
   - Validatiestatus ontologie en AI-beschrijving.
   - Eventuele verplaatsing naar een ander onderdeel via drag-and-drop of dropdown.
2. **Op Onderdeel- en Thema-niveau:**
   - Thema-omschrijving en toelichting.
   - Volgorde en gewicht in het Kompas.
   - **Koppeling met externe kaartlagen** (haakt naadloos in op issue K3/K4: externe WMS/WFS-lagen koppelen aan het Kompasthema!).
3. **Op Hoofdniveau (Kwadranten):**
   - Kwadranttitel en globale eigenschappen.
   - Samenvattende statistieken: aantal actieve indicatoren, datadekking, openstaande kwaliteitsmeldingen.

---

## 4. Harmonisatie van de Beheer-tabbladen

### A. Samenvoegen: `Indicatoren` + `Hiërarchie` → `Taxonomie & Indicatoren`
De tabbladen `Indicatoren` en `Hiërarchie` worden samengebracht tot één krachtige beheeromgeving:
- **Twee synchrone views:**
  - **Graafweergave (Bol / Sunburst):** voor inzicht in structuur, samenhang, hiaten en het beheren van contextuele relaties.
  - **Tabelweergave (Lijst):** voor bulk-acties, snelle tekstuele filters, sortering op datadekking of ontologie-status.
- Een selectie in de tabel licht op in de graaf, en een klik in de graaf selecteert de rij in de tabel.

### B. Wat doen we met `Data Kwaliteit`? (Twijfel over meenemen)
Taeke gaf terecht aan te twijfelen of *Data Kwaliteit* ook in dit scherm moet worden opgenomen.

**Aanbeveling / Voorstel:**
- **Niet forceren in één overladen editor:** Data Kwaliteit heeft een ander werkdoel (auditing, ontdubbelen van datasets, data lineage scans). Dat vereist specifieke tabellen en reconciliatie-interfaces (zoals twee kolommen vergelijken bij een merge).
- **Wél visueel integreren via kwaliteitsmarkers in de graaf:**
  - Knooppunten in de taxonomie-graaf krijgen visuele indicatoren / badges:
    - ⚠️ **Geel/Oranje:** potentieel duplicaat gedetecteerd (klik opent directe link naar Data Kwaliteit).
    - ⚪ **Grijs:** geen meetdata beschikbaar (`aantal_metingen = 0`).
    - 🔴 **Rood:** inactief of gedeactiveerd (`is_actief = false`).
    - 🔵 **Blauw:** ontologie nog niet beoordeeld (`draft`).
  - Hierdoor dient de taxonomie-graaf als een **visuele gezondheidskaart** van het Kompas, terwijl de daadwerkelijke ontdubbelingsactie op het gespecialiseerde tabblad *Data Kwaliteit* plaatsvindt.

---

## 5. Technische Haalbaarheid & Architectuur

1. **Frontend (React 19 + D3.js):**
   - Het admin-panel gebruikt reeds D3 (`* as d3 from 'd3'`) in `HierarchiePage.tsx` en `KleurschemasPage.tsx`.
   - Een D3 Zoomable Sunburst of Radial Tree kan modulair worden opgezet als React-component met SVG/Canvas.
   - State-beheer via TanStack Query (React Query) voor consistente caching van de hiërarchiestructuur (`/api/admin/kompas/tree`).
2. **Backend API:**
   - Bestaande endpoints:
     - `GET /api/admin/kompas/tree` (haalt de volledige boom op).
     - `PUT /api/admin/indicatoren/{uuid}` (update indicator).
     - `PUT /api/admin/kompas/mapping` (koppelingen en volgorde).
3. **Toegankelijkheid (WCAG 2.1 AA):**
   - De graafweergave is een visuele weergave; de tabelweergave fungeert als het volwaardige, toetsenbord-toegankelijke alternatief met volledige ARIA-ondersteuning.

---

## 6. Aanbevolen Fasering & Plaatsing op de Roadmap

- **0.7.0 (Huidige mijlpaal):**
  - Focus blijft op de viewer, kaartlagen en de directe kleine beheeracties (K1 t/m K7, inclusief #526: indicator actief/inactief schakelen in de huidige `IndicatorsPage`).
- **0.8.0 (Volgende mijlpaal):**
  - **Epic / Feature:** *"Kompas Taxonomie Studio (Visuele Taxonomie-graaf & Geïntegreerd Indicatorenbeheer)"*.
  - Uitwerken van het interactieontwerp en prototyping van de D3 bol/sunburst.
  - Samenvoegen van navigatietabbladen in `admin-panel/src/App.tsx`.

---

## 7. Conceptuele GitHub Issue Template (klaar voor aanmaak)

```markdown
### Vraag
Hoe kunnen we het beheer van indicatoren en de Kompas-taxonomie samenbrengen in een interactieve visuele bol/graaf (Kompas Taxonomie Studio), zodat beheerders op elk niveau (kwadrant, thema, onderdeel, indicator) direct inzicht hebben en wijzigingen kunnen doorvoeren?

### Kader / bron
- `admin-panel/src/pages/IndicatorsPage.tsx` (platte tabel) en `HierarchiePage.tsx` (statische D3 tree) zijn nu gescheiden.
- Indicatoren ontlenen hun context aan de 4 kwadranten en 12 thema's van het Kompas.
- Zie conceptdocument: `docs/4-ux-design/concept-visueel-taxonomie-indicatorenbeheer.md`.

### Gevraagd besluit + wie
Product Owner (Taeke) + Architectuur (Eduard):
1. Goedkeuren van het samensmelten van tabbladen 'Indicatoren' en 'Hiërarchie' tot 'Taxonomie & Indicatoren' met toggle tussen Graaf en Tabel.
2. Bevestigen dat 'Data Kwaliteit' een aparte auditpagina blijft, maar signaalkleuren/markers levert aan de visuele graaf.
3. Inplannen voor mijlpaal 0.8.0.

### Klaar als
1. Een interactieve D3 radial-/bol-graaf toont de 4 kwadranten, 12 thema's, onderdelen en indicatoren in het admin-panel.
2. Selectie van een knooppunt opent de contextuele bewerker (indicator bewerken, thema-eigenschappen, kaartlaagkoppelingen).
3. Naadloze switch mogelijk tussen Graafweergave en Tabelweergave.
4. Kwaliteitsmarkers (duplicaten, geen data, inactief) lichten visueel op in de taxonomie.
```

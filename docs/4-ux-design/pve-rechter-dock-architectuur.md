# Programma van Eisen (PvE) — Rechter Dock-architectuur & Samengevoegd Detailpaneel

**Status:** Concept ter vaststelling  
**Issue:** [#444](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/444) (Fase 2 van het Kritieke Pad, Epic [#309](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/309))  
**Doelversie:** `v0.7.0`  
**Datum:** 18 oktober 2026  
**Auteurs / Betrokkenen:** Taeke van der Laan, Eduard Witteveen  

---

## 1. Aanleiding & Doelstelling

Uit de integrale gebruikerservaring-audit ([`docs/4-ux-design/gebruikerservaring-audit.md`](./gebruikerservaring-audit.md), §2.3, §3 en §7) zijn drie fundamentele knelpunten gebleken in de huidige layout van de kaartviewer:

1. **Visuele obstructie van de kaart:**  
   Het D-Omni Kompas opent momenteel als een zwevend, gecentreerd venster (`#kompas-window`) met vaste CSS-breedte (`1100px !important`, `650px`) dat bovenop de kaart ligt. Hierdoor wordt de zojuist aangeklikte buurt (bijv. Workum, Bolsward of Sneek) direct visueel afgedekt.
2. **Dubbele en gefragmenteerde indicatorinformatie:**  
   Er zijn momenteel twee afzonderlijke plekken waar indicatorgegevens worden getoond:
   - Het **indicatorpaneel** aan de linkerkant (`#panel-indicator`, via `indicatorpaneel.js`).
   - Het **Kompas-detailpaneel** in het zwevende venster (`#kompas-details-panel`, via `kompas.js`).  
   Beide panelen halen deels dezelfde data op, hebben elk een eigen staafdiagram-implementatie, een eigen trend/vergelijking en een eigen knop om een afwijking te melden.
3. **Conflicterende vensters & ontbrekende lifecycle:**  
   Het Kompas, het linker indicatorpaneel en de Assistent (chat) kunnen onafhankelijk van elkaar openstaan en elkaar overlappen, zonder dat de kaart weet hoeveel effectieve schermruimte er overblijft.

### Doelstelling
De interface transformeren naar een rustig, voorspelbaar en intuïtief **drieluik**:
```
┌──────────────────┬─────────────────────────────────────┬───────────────────────────┐
│  LINKS: INVOER   │            MIDDEN: KAART            │       RECHTS: OUTPUT      │
│  - Gebiedskiezer │  - MapLibre GL + Deck.gl            │  - Rechter Dock           │
│  - Thema/Ind.    │  - Automatische viewport padding    │    Tab 1: Kompas & Detail │
│  - Kaartlagen    │    (geselecteerd gebied blijft      │    Tab 2: Assistent (Chat)│
│  - Legenda       │     altijd zichtbaar)               │  - Loskoppelbaar venster  │
└──────────────────┴─────────────────────────────────────┴───────────────────────────┘
```

---

## 2. Kaders & Randvoorwaarden

1. **WCAG 2.1 AA & DigiToegankelijk (ADR 0011):**  
   - Alle interacties moeten volledig bedienbaar zijn met het toetsenbord (`Tab`, `Enter`, `Spatie`, pijltjestoetsen, `Escape`).
   - Het dock moet fungeren als een semantische `tablist` met `tabpanel` en correcte ARIA-attributen (`aria-selected`, `aria-controls`).
   - De indicator-detailweergave moet ook **zonder** de visuele sunburst te raadplegen zijn (volwaardig tekstalternatief voor de kaart en het diagram).
2. **Geen zware frontend-frameworks:**  
   - De hoofdviewer blijft Vanilla JS + MapLibre GL + Deck.gl conform de architectuur-guardrails in [`AGENTS.md`](../../AGENTS.md).
3. **Enkele bron voor data & logica:**  
   - Geen dubbele endpoints. Het samengevoegde detailpaneel gebruikt uitsluitend de centrale backend-routes:
     - `/api/gebiedsmonitor/indicatorpaneel` (inclusief bescherming kleine aantallen #325 en gemeentegemiddelde).
     - `/api/gebiedsmonitor/history` (historische tijdreeks per gebied).
4. **Doelversie `0.7.0` (Minor):**  
   - Dit betreft een substantiële functioneel-visuele upgrade. Wijzigingen worden gedocumenteerd in [`CHANGELOG.md`](../../CHANGELOG.md) onder `## [Unreleased] -> ### Toegevoegd`.

---

## 3. Functionele Eisen (FE)

### FE-1: Rechter Dock Layout & Tabs
- **FE-1.1:** Er is één uniform rechter dock (`#dock-panel` of `<aside id="rechter-dock">`) aan de rechterzijde van het scherm.
- **FE-1.2:** Het dock bevat een tab-balk bovenaan met twee exclusieve tabs:
  - **Tab 1: Kompas** (bevat de Sunburst visualisatie én het samengevoegde Indicator-detailpaneel).
  - **Tab 2: Assistent** (de bestaande chat-functionaliteit met AI/regelgebaseerde dialoog).
- **FE-1.3:** Het dock heeft een responsieve breedte: `clamp(340px, 25vw, 480px)` op desktops (ca. 25% van de schermbreedte). Vaste breedtes (`1100px`, `650px`) vervallen.
- **FE-1.4:** Op schermen kleiner dan `900px` (mobiel/tablet) transformeert het dock naar een inklapbare **bottom sheet** over de onderste 40–50% van het scherm.
- **FE-1.5:** Het dock heeft een duidelijke sluitknop (`✕`) en een minimaliseer-optie.

### FE-2: Samenvoeging Indicatorpaneel in Kompas
- **FE-2.1:** De losse knop "Indicator" (`[data-panel="indicator"]`) in de linker navigatiebalk vervalt. Het linker paneel `#panel-indicator` wordt gesaneerd.
- **FE-2.2:** Het Kompas-detailpaneel wordt de **enige** plek voor indicatorgegevens. Het toont informatie in een vaste, logische verticale volgorde:
  1. **Broodkruimel:** Pad door de thema-hiërarchie (`Thema > Subthema > Indicator`).
  2. **Sunburst (Kompas visualisatie):** Bovenin het paneel; inklapbaar/minimaliseerbaar zodra een specifieke indicator actief is om ruimte te maximaliseren voor details.
  3. **Indicatortitel, actuele waarde & trendindicator:** Duidelijke typografie met actueel peiljaar.
  4. **Trendgrafiek:** Tijdreeks (historische trendlijn) van de indicator voor het geselecteerde gebied.
  5. **Gebiedskiezer bij multiselect:** Indien meerdere gebieden zijn geselecteerd (Shift+klik), verschijnt boven de trendgrafiek een compacte keuzelijst om de trendlijn per specifiek gebied te bekijken.
  6. **Tabs Definitie | Ontologie:** Met automatische terugval op de ontologie indien de definitie leeg is. Met behoud van `white-space: pre-line` (#450).
  7. **Metadata:** Eenheid, officiële bron (met directe lineage link), peildatum en het berekende gemeentegemiddelde.
  8. **Liggend staafdiagram:** Benchmark van het/de geselecteerde gebied(en) ten opzichte van het gemeentegemiddelde (gebaseerd op `/api/gebiedsmonitor/indicatorpaneel`).
  9. **Top-uitschieters:** Rijen met hoogste en laagste buurten, inclusief Z-score en toetsenbord-interactie (Enter/Spatie vliegt naar het gebied, conform #450).
  10. **Acties:**
      - Knop **CSV downloaden** (exporteert de data van het actieve staafdiagram en metadata).
      - Knop **Afwijking melden** (één centrale knop die `#meld-dialoog` opent met de actieve indicator en het actieve gebied vooringevuld).
  11. **Indicatordekking:** Duidelijke aanduiding van de datadekking (% buurten met bekende waarden).

### FE-3: Loskoppelbaar Venster ("Detach / Dock")
- **FE-3.1:** Het dock heeft in de kopbalk een toggle-knop: **"Losmaken"** / **"Vastzetten"** (met icoon `external-link` / `panel-right`).
- **FE-3.2:** Bij klikken op "Losmaken" verhuist *dezelfde* DOM-component vanuit het dock naar een zwevend, versleepbaar en herschaalbaar venster over de kaart.
- **FE-3.3:** In losgekoppelde toestand schakelt het venster via een CSS Container Query (`@container (min-width: 760px)`) over naar een **2-koloms indeling**:
  - Linker kolom: Sunburst visualisatie.
  - Rechter kolom: Samengevoegd indicator-detailpaneel.
  - Beneden 760px vensterbreedte: 1-koloms gestapeld.
- **FE-3.4:** De gekozen stand (gedockt of losgekoppeld) wordt bewaard in `localStorage` (`omnitwin_kompas_docked: "true" | "false"`). Standaardwaarde voor nieuwe gebruikers is altijd **gedockt**.
- **FE-3.5:** Bij herladen of wisselen van weergave worden actieve indicator, drilldown-niveau en tabblad naadloos behouden.

### FE-4: Kaartpadding & Viewport-beheer
- **FE-4.1:** Zodra het rechter dock geopend wordt, berekent de viewer de breedte van het dock en past de kaartviewport dynamisch aan:
  ```javascript
  map.easeTo({
    padding: { right: dockBreedte, left: linkerBalkBreedte, top: 0, bottom: 0 },
    duration: 300
  });
  ```
- **FE-4.2:** Bij het centreren of vliegen naar een geselecteerde buurt (`flyToGebied`) berekent MapLibre de bounding box altijd binnen de effectieve, zichtbare kaartruimte (dus gecentreerd tussen de linkerbalk en het geopende dock).
- **FE-4.3:** Wanneer het dock gesloten wordt (of losgekoppeld), reset de `padding.right` naar `0` en hercentreert de kaart soepel.

### FE-5: Tweerichtingssynchronisatie & Direct Tekstalternatief
- **FE-5.1:** Eén centrale state `state.currentIndicator`.
- **FE-5.2 (Kaart/Lijst ➔ Dock):** Als de gebruiker een indicator activeert via de kaartlagen of zoekbalk:
  - Het dock opent automatisch op de tab *Kompas*.
  - Het paneel scrolt direct naar het detailpaneel.
  - De Sunburst navigeert op de achtergrond synchroon mee naar het betreffende thema.
- **FE-5.3 (Dock ➔ Kaart):** Als de gebruiker in de Sunburst op een indicator klikt:
  - De indicator wordt direct actief op de kaart met automatische fallback op `CBS_BUURT` (conform #450).
  - Het detailpaneel opent en toont de actuele cijfers voor het op de kaart actieve gebied.

---

## 4. Technische Eisen & Architectuur (TE)

### TE-1: DOM-structuur (`templates/index.html`)
Het drieluik wordt verankerd in de hoofdstructuur:
```html
<div class="app-layout">
  <!-- 1. Linker navigatie en configuratiepanelen -->
  <aside id="sidebar-left" class="sidebar-left"> ... </aside>

  <!-- 2. Hoofdinhoud: Volledige kaart -->
  <main id="hoofdinhoud" class="map-container">
    <div id="map" class="map"></div>
    ...
  </main>

  <!-- 3. Rechter Dock (Standaard voor Kompas en Chat) -->
  <aside id="rechter-dock" class="rechter-dock" role="region" aria-label="Zijpaneel met Kompas en Assistent">
    <div class="dock-header">
      <div role="tablist" class="dock-tabs">
        <button id="dock-tab-kompas" role="tab" aria-selected="true" aria-controls="dock-panel-kompas">Kompas</button>
        <button id="dock-tab-chat" role="tab" aria-selected="false" aria-controls="dock-panel-chat">Assistent</button>
      </div>
      <div class="dock-actions">
        <button id="dock-btn-detach" title="Losmaken naar zwevend venster" aria-label="Venster losmaken">...</button>
        <button id="dock-btn-close" title="Sluiten" aria-label="Zijpaneel sluiten">✕</button>
      </div>
    </div>
    
    <div class="dock-body">
      <!-- Tab 1: Kompas + Geïntegreerd Detail -->
      <div id="dock-panel-kompas" role="tabpanel" aria-labelledby="dock-tab-kompas">
        <!-- Sunburst container (inklapbaar) -->
        <div id="kompas-viz-section"> ... </div>
        <!-- Samengevoegd detailgedeelte -->
        <div id="kompas-unified-details"> ... </div>
      </div>

      <!-- Tab 2: Assistent Chat -->
      <div id="dock-panel-chat" role="tabpanel" aria-labelledby="dock-tab-chat" hidden>
        <!-- Bestaande chat content -->
      </div>
    </div>
  </aside>

  <!-- 4. Zwevend venster container (voor losgekoppelde modus) -->
  <div id="kompas-floating-host" class="floating-window" style="display: none;">
    <!-- Hier wordt de inhoud van #dock-panel-kompas ingehangen bij "Losmaken" -->
  </div>
</div>
```

### TE-2: CSS & Styling (`styles.css`)
- **Dock-styling:**
  ```css
  .rechter-dock {
    position: fixed;
    top: var(--header-height, 60px);
    right: 0;
    bottom: 0;
    width: clamp(340px, 25vw, 480px);
    background: var(--panel-bg); /* 76% dekkend conform #450 */
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-left: 1px solid var(--panel-border);
    z-index: 1000;
    display: flex;
    flex-direction: column;
    transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  }
  .rechter-dock.collapsed {
    transform: translateX(100%);
  }
  ```
- **Container queries voor zwevend venster:**
  ```css
  #kompas-floating-host {
    container-type: inline-size;
    container-name: kompas-window;
  }
  @container kompas-window (min-width: 760px) {
    .kompas-content-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
  }
  ```
- **Responsieve bottom sheet:**
  ```css
  @media (max-width: 900px) {
    .rechter-dock {
      top: auto;
      left: 0;
      right: 0;
      bottom: 0;
      width: 100%;
      height: 45vh;
      border-left: none;
      border-top: 1px solid var(--panel-border);
    }
  }
  ```

### TE-3: Lifecycle & State Management
- **Centrale `PanelManager`:**  
  Een eenduidige coördinator (`static/js/core/panel_manager.js` of module in `app.js`):
  - Voorkomt dat links geopende overlay-panelen en het rechter dock elkaar bijten.
  - Bewaakt de actieve tab in het dock (`activeTab = 'kompas' | 'chat'`).
  - Triggert `map.resize()` en `map.setPadding()` synchroon met CSS-transities.
  - Zorgt dat Chart.js grafieken (`resize()`) opnieuw worden ingemeten zodra een tabblad zichtbaar wordt (voorkomt 0x0 bug #422).

---

## 5. Toegankelijkheid (WCAG 2.1 AA) Checklist

| WCAG Criterium | Implementatie-eis |
|---|---|
| **1.3.1 Info & Relaties** | Semantische `tablist`, `tab`, `tabpanel`. Duidelijke koppenhiërarchie (`h2` dock, `h3` indicator, `h4` subsecties). |
| **1.4.3 Contrast (Minimum)** | Alle tekst, iconen en tabs halen minimaal 4,5:1 tegen `--panel-bg` (76% met blur). |
| **2.1.1 Toetsenbord** | Volledige navigatie met pijltoetsen binnen de tablist; `Enter`/`Spatie` op tabs en uitschieters; `Escape` sluit dock of zwevend venster. |
| **2.4.3 Focusvolgorde** | Bij openen van dock blijft de focus op de activerende knop (geen focus theft), of verplaatst logisch naar de eerste tab. |
| **2.4.7 Focus zichtbaar** | Zichtbare focusringen (`:focus-visible`) op alle interactieve knoppen en tabs conform thema tokens. |

---

## 6. Impactanalyse & Uit te faseren code

| Bestand | Wat wijzigt er? |
|---|---|
| `templates/index.html` | - Knop `[data-panel="indicator"]` en `#panel-indicator` verwijderen.<br>- Structuur voor `#rechter-dock` toevoegen met tabs.<br>- `#kompas-window` ombouwen naar `#kompas-floating-host`. |
| `static/js/indicatorpaneel.js` | Logica voor staafdiagram, CSV en metadata overbrengen naar het samengevoegde detailpaneel van het Kompas. Scriptbestand saneren of reduceren tot gedeelde helper. |
| `static/js/kompas.js` | - Verwijderen van vaste `1100px` en `650px` floating-logica.<br>- Inbouwen van detach/dock logica (verplaatsen DOM node tussen dock en host).<br>- Toevoegen van gebiedskiezer voor de trendlijn bij meervoudige selectie.<br>- Inbouwen van het liggende staafdiagram uit het indicatorpaneel. |
| `static/js/app.js` | - Verwijderen van de event-listeners voor het linker indicatorpaneel.<br>- Toevoegen van `updateMapPadding()` bij openen/sluiten van het dock.<br>- EventBus-koppeling `indicator:selected` opent het dock direct op detail. |
| `static/css/styles.css` | - Vaste breedtes en positionering van `#kompas-window` en `#chat-panel` vervangen door `.rechter-dock` stijlen.<br>- Container query toevoegen voor zwevend venster. |
| `tests/e2e/*` | Selectors bijwerken in `test_toegankelijkheid.py`, `test_indicatorpaneel.py` en `test_integratie_e2e.py`. Nieuwe tests voor docking en losmaken. |

---

## 7. Verificatie & Acceptatiecriteria (Definition of Done)

- [ ] **AC-1:** Het Kompas opent standaard in het rechter dock (`clamp(340px, 25vw, 480px)`) en dekt de kaart in het midden niet meer af.
- [ ] **AC-2:** Geselecteerde gebieden (zoals Workum) blijven na openen van het dock volledig zichtbaar doordat de kaart automatisch naar links schuift via viewport padding.
- [ ] **AC-3:** Het indicatorpaneel aan de linkerkant is verwijderd; alle details, trendlijn, liggend staafdiagram, top-uitschieters en CSV-export zitten in het Kompas.
- [ ] **AC-4:** Bij meerdere geselecteerde gebieden kan via een selectielijst gewisseld worden tussen trendlijnen per specifiek gebied.
- [ ] **AC-5:** Met de knop "Losmaken" kan het Kompas worden losgekoppeld naar een zwevend venster (met 2-koloms indeling op schermen/vensters ≥ 760px). De keuze blijft bewaard in `localStorage`.
- [ ] **AC-6:** Wisselen tussen de tabs *Kompas* en *Assistent* werkt soepel zonder herlaad-artefacten of kapotte grafieken (Chart.js resize).
- [ ] **AC-7:** Alle bestaande unit tests (Python) en E2E tests slagen met de nieuwe DOM-structuur.
- [ ] **AC-8:** Documentatie in `CHANGELOG.md` is bijgewerkt als feature voor `v0.7.0`.

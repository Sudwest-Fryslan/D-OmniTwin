# Programma van Eisen (PvE) — Rechter Dock-architectuur & Samengevoegd Detailpaneel

**Status:** Definitief vastgesteld (getoetst via `/grill-me` ontwerpsessie op 19–20 oktober 2026)  
**Issue:** [#444](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/444) (Fase 2 van het Kritieke Pad, Epic [#309](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/309))  
**Doelversie:** `v0.7.0`  
**Datum:** 20 oktober 2026  
**Auteurs / Betrokkenen:** Taeke van der Laan (Product Owner / CDO), Eduard Witteveen (Lead Architect)

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

### Doelstelling: Het Drieluik
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
   - De hoofdviewer blijft Vanilla JS + MapLibre GL + Deck.gl + D3.js conform de architectuur-guardrails in [`AGENTS.md`](../../AGENTS.md).
3. **Enkele bron voor data & logica:**  
   - Geen dubbele endpoints. Het samengevoegde detailpaneel gebruikt uitsluitend de centrale backend-routes:
     - `/api/gebiedsmonitor/indicatorpaneel` (inclusief bescherming kleine aantallen [#325](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/325) en gemeentegemiddelde).
     - `/api/gebiedsmonitor/history` (historische tijdreeks per gebied).
4. **Doelversie `0.7.0` (Minor):**  
   - Dit betreft een substantiële functioneel-visuele upgrade. Wijzigingen worden gedocumenteerd in [`CHANGELOG.md`](../../CHANGELOG.md) onder `## [Unreleased] -> ### Toegevoegd`.

---

## 3. Functionele Eisen (FE)

### FE-1: Rechter Dock Layout & Starttoestand
- **FE-1.1 (Starttoestand):**  
  De applicatie start met een **schone, rustige weergave**. De volledige kaart is zichtbaar; het dock staat standaard ingeklapt/gesloten.
- **FE-1.2 (Automatisch openen bij selectie):**  
  Zodra de gebruiker op een buurt klikt, in de kaart klikt of een indicator activeert, schuift het rechter dock soepel open met de cijfers en analyse van die buurt (conform het vertrouwde gedrag van het chat-venster).
- **FE-1.3 (Layout & Afmetingen):**  
  Er is één uniform rechter dock (`#dock-panel` of `<aside id="rechter-dock">`) aan de rechterzijde van het scherm met responsieve breedte: `clamp(340px, 25vw, 480px)`. Vaste breedtes (`1100px`, `650px`) vervallen.
- **FE-1.4 (Tabs):**  
  Het dock bevat bovenaan een tab-balk met twee exclusieve tabs:
  - **Tab 1: Kompas** (bevat de Sunburst visualisatie én het samengevoegde Indicator-detailpaneel).
  - **Tab 2: Assistent** (de bestaande chat-functionaliteit met AI/regelgebaseerde dialoog).
- **FE-1.5 (Mobiel & Tablets):**  
  Op schermen kleiner dan `900px` transformeert het dock naar een inklapbare **bottom sheet** over de onderste 45% van het scherm.
- **FE-1.6 (Bediening):**  
  Het dock heeft in de kopbalk een duidelijke sluitknop (`✕`) en een minimaliseerknop (`—`).

---

### FE-2: Kompas Tab — Navigatie, Sunburst & Samengevoegd Detailpaneel
- **FE-2.1 (Sanering):**  
  De knop "Indicator" (`[data-panel="indicator"]`) in de linker navigatiebalk vervalt. Het linker paneel `#panel-indicator` en `indicatorpaneel.js` worden definitief gesaneerd en opgenomen in het Kompas.
- **FE-2.2 (Navigatie bovenaan het paneel):**
  1. **Sunburst (Cirkelvisualisatie):** Bovenin het paneel; voorzien van een knop om te minimaliseren/inklappen (`[— Cirkel inklappen]`), zodat alle verticale ruimte direct naar de cijfers en trendlijn gaat.
  2. **Doorklikbaar Kruimelpad:** Duidelijke hiërarchische weergave (`Kwadrant ➔ Thema ➔ Onderdeel ➔ Indicator`) met directe terugklik-optie.
  3. **Directe Zoekfunctie:** Een zoekbalk binnen het dock om snel op trefwoord indicatoren te filteren.
- **FE-2.3 (Geselecteerde Buurten Badge):**  
  Direct boven de indicatorgegevens worden de geselecteerde gebieden getoond:
  - Bij 1 t/m 5 geselecteerde buurten: de namen worden voluit uitgeschreven als interactieve badges.
  - Bij > 5 buurten: de eerste 5 buurtnamen worden getoond, gevolgd door een compacte teller `+ xx overige buurten`.
- **FE-2.4 (Indicator Details & Rijke Inhoud):**  
  Zodra een indicator geselecteerd is (via Sunburst, kaart, kruimelpad of zoekbalk), toont het paneel in vaste volgorde:
  1. **Indicatortitel & actuele peildata:** Naam, peiljaar, gemeten waarde en eenheid.
  2. **Trendindicator:** Pijl met trendstatus (stijgend, dalend, stabiel) en procentuele verandering t.o.v. voorgaand peiljaar.
  3. **Trendgrafiek (Tijdreeks):** Historische lijn grafiek (Chart.js) met:
     - **Play-knop / schuifregelaar:** Om interactief door de beschikbare jaargangen te reizen (animatie van historische kaartkleuren).
     - **Gebiedskiezer bij multiselect:** Indien meerdere gebieden geselecteerd zijn, verschijnt boven de trendgrafiek een compacte keuzelijst om de trendlijn van één specifieke buurt (of het gemiddelde van de selectie) te bekijken.
  4. **Gemeentegemiddelde & Referentie:** Duidelijke weergave van het gemeentegemiddelde en de Z-score t.o.v. de referentiegroep.
  5. **Tabs Definitie | Ontologie:** Met automatische terugval op de ontologie indien de definitie leeg is. Met behoud van `white-space: pre-line` ([#450](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/450)).
  6. **Liggend Benchmark Staafdiagram:** Grafische vergelijking van het/de geselecteerde gebied(en) t.o.v. het gemeentegemiddelde (via `/api/gebiedsmonitor/indicatorpaneel`).
  7. **Top-Uitschieters:** Rijen met hoogste en laagste buurten binnen de gemeente, inclusief Z-score en toetsenbord-interactie (`Enter`/`Spatie` vliegt direct naar de buurt).
  8. **Acties & Knoppen:**
     - Knop **CSV downloaden** (exporteert data van actieve indicator en staafdiagram).
     - Knop **Afwijking melden** (één centrale knop die `#meld-dialoog` opent met de actieve indicator en buurt vooringevuld).
     - Knoppen **Reset** en **Terug naar boven** (scroll to top).
  9. **Indicatordekking:** % buurten met bekende data.

---

### FE-3: Loskoppelbaar Venster (Detach / Dock) & Adaptieve Layout
- **FE-3.1 (Toggle Knop):**  
  In de dock header bevindt zich een prominente toggle-knop: **"Losmaken"** / **"Vastzetten"** (met iconen `external-link` / `pin`).
- **FE-3.2 (Vrij herschaalbaar):**  
  In losgekoppelde (zwevende) toestand is het venster vrij versleepbaar (`DraggableWindow`) en vrij herschaalbaar via de `resize-handle` (minimaal 400px breed, maximaal tot schermgrootte).
- **FE-3.3 (Vloeiende Layout-wissel bij Resizen via Container Queries):**  
  - **Smal (< 750px):** 1-koloms gestapeld (identiek aan de dock-layout).
  - **Breder gesleept (≥ 750px):** De component schakelt automatisch over naar een **2-koloms indeling**:
    - Linker kolom: Sunburst cirkelvisualisatie.
    - Rechter kolom: Geünificeerd indicator-detailpaneel (trendlijn, staafdiagram, definities).
  - **Extra breed (≥ 1100px, bijv. op Ultrawide 3440×1440 of dual monitor):**  
    Optionele **Duo-weergave**: de gebruiker kan zowel het Kompas als de Assistent (Chat) tegelijkertijd naast elkaar geopend houden in het losse venster.
- **FE-3.4 (Persistentie):**  
  De gekozen toestand (`omnitwin_dock_mode: 'docked' | 'floating'`), evenals positie en afmetingen van het zwevende venster, worden opgeslagen in `localStorage`.

---

### FE-4: Kaartpadding & Viewport-beheer
- **FE-4.1 (Dynamische Padding):**  
  Zodra het rechter dock geopend wordt, berekent de viewer de dockbreedte en past MapLibre viewport padding toe:
  ```javascript
  map.easeTo({
    padding: { right: dockBreedte, left: linkerBalkBreedte, top: 0, bottom: 0 },
    duration: 300
  });
  ```
- **FE-4.2 (Zichtbaarheid behouden):**  
  Bij het centreren of vliegen naar een gekozen buurt (`flyToGebied`) berekent MapLibre de bounding box altijd binnen de effectieve, zichtbare kaartruimte (tussen linkerbalk en geopend dock). De geselecteerde buurt blijft altijd 100% zichtbaar.
- **FE-4.3 (Reset):**  
  Wanneer het dock sluit of wordt losgekoppeld naar een zwevend venster, reset `padding.right` naar `0` en hercentreert de kaart soepel over het volledige scherm.

---

### FE-5: Paneelcoördinatie & Chat-interactie (PanelManager)
- **FE-5.1 (Gebruikersregie):**  
  De gebruiker heeft altijd de vrijheid om panelen handmatig open of dicht te zetten via de navigatieknoppen.
- **FE-5.2 (Slimme Responsiviteit op Compacte Schermen < 1400px):**  
  - Op schermen onder 1400px breedte: het openen van een linker overlay-paneel (bijv. Kaartlagen of Gebiedskiezer) klapt het rechter dock zachtjes in (en omgekeerd), om te voorkomen dat de kaart onbedoeld geplet wordt tot een smalle strook.
  - Kiest de gebruiker er daarna voor om beide panelen tegelijk open te zetten, dan wordt die keuze gerespecteerd.
  - Op grote schermen (≥ 1400px en ultrawide) blijven beide zijden standaard probleemloos naast elkaar geopend.
- **FE-5.3 (Assistent ➔ Kompas Interactie):**  
  - Als de Assistent in de chat een indicator voorstelt (bijv. *"Bekijk energiearmoede in Makkum"*), verspringt het tabblad **niet** ongevraagd. De gebruiker blijft rustig in de chat.
  - Het antwoord bevat een interactieve chip of knop: `[📊 Bekijk 'Energiearmoede' in Kompas]`.
  - Pas bij een klik op de chip schakelt het dock soepel naar Tab 1 (Kompas) en zoomt in op de details van die indicator.

---

## 4. Technische Eisen & Architectuur (TE)

### TE-1: DOM-structuur (`templates/index.html`)
Het drieluik wordt verankerd in de HTML-basis:
```html
<div class="app-layout">
  <!-- 1. Linker navigatie en configuratiepanelen -->
  <aside id="sidebar-left" class="sidebar-left"> ... </aside>

  <!-- 2. Hoofdinhoud: Volledige kaart -->
  <main id="hoofdinhoud" class="map-container">
    <div id="map" class="map"></div>
  </main>

  <!-- 3. Rechter Dock (Standaard voor Kompas en Chat) -->
  <aside id="rechter-dock" class="rechter-dock" role="region" aria-label="Zijpaneel met Kompas en Assistent">
    <div class="dock-header">
      <div role="tablist" class="dock-tabs">
        <button id="dock-tab-kompas" role="tab" aria-selected="true" aria-controls="dock-panel-kompas">Kompas</button>
        <button id="dock-tab-chat" role="tab" aria-selected="false" aria-controls="dock-panel-chat">Assistent</button>
      </div>
      <div class="dock-actions">
        <button id="dock-btn-detach" title="Losmaken naar zwevend venster" aria-label="Venster losmaken">↗</button>
        <button id="dock-btn-close" title="Sluiten" aria-label="Zijpaneel sluiten">✕</button>
      </div>
    </div>
    
    <div class="dock-body">
      <!-- Tab 1: Kompas + Geïntegreerd Detail -->
      <div id="dock-panel-kompas" role="tabpanel" aria-labelledby="dock-tab-kompas">
        <!-- Sunburst container (inklapbaar) -->
        <div id="kompas-viz-section" class="kompas-viz-section">
          <div class="viz-header">
            <span class="viz-title">D-Omni Kompas</span>
            <button id="btn-toggle-sunburst" class="btn-toggle-viz" title="Cirkel inklappen/uitklappen">—</button>
          </div>
          <div id="kompas-sunburst-container"></div>
        </div>

        <!-- Doorklikbaar kruimelpad & Zoekbalk -->
        <nav id="kompas-breadcrumb" aria-label="Thema hiërarchie"></nav>
        <div id="kompas-search-box"></div>

        <!-- Geselecteerde gebieden badge container -->
        <div id="kompas-selected-areas" class="selected-areas-chips"></div>

        <!-- Samengevoegd detailgedeelte -->
        <div id="kompas-unified-details"></div>
      </div>

      <!-- Tab 2: Assistent Chat -->
      <div id="dock-panel-chat" role="tabpanel" aria-labelledby="dock-tab-chat" hidden>
        <div id="chat-messages" class="chat-messages"></div>
        <div class="chat-input-row">
          <input id="chat-input" type="text" placeholder="Stel een vraag over een gebied..." />
          <button id="chat-send-btn">Verstuur</button>
        </div>
      </div>
    </div>
  </aside>

  <!-- 4. Zwevend venster container (DraggableWindow host) -->
  <div id="kompas-floating-host" class="floating-window" style="display: none;">
    <div class="floating-window-header">
      <span class="floating-window-title">D-Omni Kompas & Analyse</span>
      <div class="window-controls">
        <button id="float-btn-dock" class="btn-dock" title="Vastzetten in zijbalk">📌</button>
        <button class="btn-minimize" title="Minimaliseren">—</button>
        <button class="btn-close" title="Sluiten">✕</button>
      </div>
    </div>
    <div class="floating-window-content"></div>
    <div class="resize-handle"></div>
  </div>
</div>
```

### TE-2: CSS & Container Queries (`styles.css`)
```css
/* Rechter Dock */
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

/* Container query voor zwevend venster (vloeiende layoutwissel) */
#kompas-floating-host {
  container-type: inline-size;
  container-name: floating-panel;
}

@container floating-panel (min-width: 750px) {
  #dock-panel-kompas {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    align-items: start;
  }
  #kompas-viz-section {
    position: sticky;
    top: 0;
  }
}

@container floating-panel (min-width: 1100px) {
  /* Duo-view optie: Kompas en Chat naast elkaar */
  .floating-window.duo-view .dock-body {
    display: grid;
    grid-template-columns: 1.2fr 0.8fr;
    gap: 16px;
  }
  .floating-window.duo-view #dock-panel-chat {
    display: flex !important;
  }
}

/* Mobiele bottom sheet */
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

### TE-3: Lifecycle & Canvas Re-render Hook
Om canvas-corruptie te voorkomen bij het verplaatsen van de DOM-node tussen `#rechter-dock` en `#kompas-floating-host`:
```javascript
function verplaatsPaneel(naarZwevend) {
  const content = document.querySelector('.dock-body');
  if (naarZwevend) {
    document.querySelector('#kompas-floating-host .floating-window-content').appendChild(content);
  } else {
    document.querySelector('#rechter-dock').appendChild(content);
  }
  
  // Lifecycle Hook: herbereken afmetingen en herteken grafieken
  requestAnimationFrame(() => {
    if (window.trendChartInstance) {
      window.trendChartInstance.resize();
    }
    if (window.sunburstInstance) {
      window.sunburstInstance.updateDimensions();
    }
  });
}
```

---

## 5. Toegankelijkheid (WCAG 2.1 AA) Checklist

| WCAG Criterium | Implementatie-eis |
|---|---|
| **1.3.1 Info & Relaties** | Semantische `tablist`, `tab`, `tabpanel`. Duidelijke koppenhiërarchie (`h2` dock, `h3` indicator, `h4` subsecties). |
| **1.4.3 Contrast (Minimum)** | Alle tekst, iconen en tabs halen minimaal 4,5:1 tegen `--panel-bg` (76% dekkend met blur). |
| **2.1.1 Toetsenbord** | Volledige navigatie met pijltoetsen binnen de tablist; `Enter`/`Spatie` op tabs en uitschieters; `Escape` sluit dock of zwevend venster. |
| **2.4.3 Focusvolgorde** | Bij openen van dock blijft de focus op de activerende knop (geen focus theft), of verplaatst logisch naar de eerste tab. |
| **2.4.7 Focus zichtbaar** | Zichtbare focusringen (`:focus-visible`) op alle interactieve knoppen en tabs conform thema tokens. |

---

## 6. Impactanalyse & Uit te faseren code

| Bestand | Wat wijzigt er? |
|---|---|
| `templates/index.html` | - Knop `[data-panel="indicator"]` en `#panel-indicator` verwijderen.<br>- Structuur voor `#rechter-dock` toevoegen met tabs.<br>- `#kompas-window` ombouwen naar `#kompas-floating-host`. |
| `static/js/indicatorpaneel.js` | Logica voor staafdiagram, CSV en metadata overbrengen naar het samengevoegde detailpaneel van het Kompas. Bestand saneren/verwijderen. |
| `static/js/kompas.js` | - Verwijderen van vaste `1100px` en `650px` floating-logica.<br>- Inbouwen van detach/dock logica via `DraggableWindow`.<br>- Inklapknop voor de Sunburst toevoegen.<br>- Trendlijn met play/schuifregelaar en gebiedskiezer integreren.<br>- Liggend staafdiagram en uitschieters integreren. |
| `static/js/app.js` | - Event-listeners voor linker indicatorpaneel verwijderen.<br>- Toevoegen van `updateMapPadding()` bij openen/sluiten van het dock.<br>- EventBus `indicator:selected` opent direct het rechter dock.<br>- Kaartklik opent automatisch het rechter dock (indien gesloten). |
| `static/js/chat.js` | - Integreren als Tab 2 binnen `#rechter-dock`.<br>- Suggesties van indicatoren voorzien van `[📊 Bekijk in Kompas]` actieknop. |
| `static/css/styles.css` | - Vaste breedtes saneren en vervangen door `.rechter-dock` stijlen.<br>- Container query `@container (min-width: 750px)` toevoegen voor zwevende weergave. |
| `tests/e2e/*` | Selectors bijwerken in `test_toegankelijkheid.py`, `test_indicatorpaneel.py` en `test_integratie_e2e.py`. Nieuwe tests voor docking, losmaken en container queries. |

---

## 7. Verificatie & Acceptatiecriteria (Definition of Done)

- [ ] **AC-1:** De kaartapplicatie start schoon met de volledige kaart; het rechter dock opent soepel zodra een buurt op de kaart wordt aangeklikt of een indicator wordt gekozen.
- [ ] **AC-2:** Het rechter dock (`clamp(340px, 25vw, 480px)`) dekt de geselecteerde buurt niet af doordat de kaart automatisch naar links schuift via viewport padding.
- [ ] **AC-3:** Het losse indicatorpaneel aan de linkerkant is volledig gesaneerd; alle details, trendlijn (met play-slider), liggend staafdiagram, uitschieters en CSV-export zijn geïntegreerd in het Kompas.
- [ ] **AC-4:** Bovenin het Kompas is de Sunburst inklapbaar via een knop (`—`), met een helder kruimelpad (`Kwadrant ➔ Thema ➔ Indicator`) en een directe zoekbalk.
- [ ] **AC-5:** Geselecteerde buurten worden boven de data getoond (maximaal 5 voluit, daarna `+ xx overige buurten`).
- [ ] **AC-6:** Met de knop "Losmaken" kan het dock worden ontkoppeld naar een zwevend, versleepbaar venster. Bij verbreding (≥ 750px) schakelt dit automatisch over naar een 2-koloms indeling zonder renderingfouten in de grafieken.
- [ ] **AC-7:** In de Assistent-tab verspringt de weergave niet ongevraagd bij een suggestie; de gebruiker kan via een klikbare chip bewust overschakelen naar het Kompas.
- [ ] **AC-8:** Alle unit tests en E2E tests slagen met de nieuwe selectors en structuur.
- [ ] **AC-9:** Documentatie in `CHANGELOG.md` is bijgewerkt als feature voor `v0.7.0`.

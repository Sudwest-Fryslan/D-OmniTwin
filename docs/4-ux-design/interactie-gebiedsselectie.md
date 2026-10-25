# Analyse interactie bij gebiedsselectie (#465)

> **Status:** concept, ter bespreking. Metingen nog uit te voeren (sectie 5).
> **Opgesteld door:** Taeke van der Laan, met AI-ondersteuning. Review: Eduard Witteveen.
> **Datum:** 25 oktober 2026
> **Kader:** #465 (onderzoek), #444 en PR #454 (rechter dock), #309 (UX-audit), #305 (werkwijze issues), ADR 0011 (WCAG 2.1 AA)

---

## 1. Doel

Sinds PR #454 (rechter dock) verloopt de cameravlucht naar een aangeklikt gebied schokkerig. Conform #465 leggen we eerst vast:

1. wat het probleem is;
2. hoe de interactie nu werkt, op basis van de code en (nog uit te voeren) metingen;
3. welke gebruikersverwachtingen we toetsen.

Wat er moet veranderen en hoe, valt buiten dit document. Dat volgt in een vervolgissue.

**Legenda:** *feit* = aantoonbaar in de code; *hypothese* = plausibel, niet gemeten of waargenomen.

---

## 2. Het probleem

### 2.1 Wat de gebruiker ervaart

Bij een klik op een gebied op de kaart starten vier dingen tegelijk:

1. de kaart toont de selectie (gouden rand);
2. de camera vliegt in 800 ms naar het gebied;
3. het rechter dock schuift in 250 ms open;
4. het Kompas haalt gegevens op en tekent de sunburst en grafieken zodra het antwoord binnen is.

Stap 1 tot en met 3 starten in dezelfde klikafhandeling (*feit*). Stap 4 rendert pas als het netwerkantwoord binnen is. Of dat tijdens de vlucht (0–850 ms na de klik) of erna valt, is onbekend en moet gemeten worden.

Gemeld effect: de cameravlucht hapert. Hoe vaak, hoe sterk en op welke apparaten is niet vastgelegd.

**Hypothesen over de beleving** (niet waargenomen bij gebruikers):
- *Visuele competitie:* kaart, dock en cijfers trekken tegelijk de aandacht.
- *Verlies van oriëntatie:* door gelijktijdige beweging ziet de gebruiker minder goed waar het gebied ligt.

### 2.2 Mogelijke technische oorzaken (hypothesen)

Een vloeiende animatie vraagt elk frame binnen ±16,7 ms (60 fps). Een frame wordt te laat als de main thread bezet is (JavaScript, stijl, layout) of als de GPU het frame niet op tijd klaar heeft.

| # | Hypothese | Onderbouwing in de code |
|---|---|---|
| H1 | Het renderen van het Kompas (D3-sunburst, Chart.js) valt tijdens de vlucht en blokkeert de main thread. | `renderSunburst` verwijdert en bouwt de hele sunburst opnieuw op ([kompas.js r.686-687](../../static/js/kompas.js)). Tijdstip hangt af van het netwerk. |
| H2 | De detailketen van een actieve indicator loopt twee keer en kost extra main-thread-tijd en requests. | Zie 3.3, bevinding B2. |
| H3 | `backdrop-filter: blur(16px)` op het dock maakt elk frame duurder zolang de kaart eronder beweegt. | [styles.css r.4235](../../static/css/styles.css). Het dock blijft na het openschuiven over de bewegende kaart liggen. |
| H4 | `preserveDrawingBuffer: true` maakt elk WebGL-frame duurder. | Ingesteld voor MapLibre én deck.gl ([app.js r.477 en r.500](../../static/js/app.js)), nodig voor de screenshot-export. |
| H5 | Het opnieuw opbouwen van de kaartlaag kost merkbare tijd bij veel gebieden. | `displayOnMap` maakt een nieuwe laag met dezelfde id en hetzelfde data-object: geen hertessellatie ([app.js r.1851-1854](../../static/js/app.js)). Wel worden lijnkleur en lijnbreedte voor álle features opnieuw berekend (gewijzigde `updateTriggers`). Waarschijnlijk klein, wel meten. |

Geen oorzaak (*feit*): het dock is `position: fixed` en schuift in met een `transform`. De kaart verandert daardoor niet van grootte; er is geen layout-reflow van de kaart. `updateMapPadding` zet de padding altijd op 0 en doet in de praktijk niets.

---

## 3. Hoe het nu werkt

### 3.1 Verschil vóór en na PR #454 (*feit*)

- **Vóór #454:** het Kompasvenster opende bij een klik alleen als het Kompas al actief was (`state.activePanelId === 'kompas'`). Alleen als het venster zichtbaar was, werden Kompas-gegevens geladen. De cameravlucht bestond al (met hetzelfde uitstel van 50 ms).
- **Na #454:** eis FE-1.2 ("dock opent automatisch bij selectie") zorgt dat **elke** klik het dock opent en het Kompas laadt.

Of de vlucht vóór #454 vloeiend was, is niet gemeten.

### 3.2 De keten bij één klik (zonder Shift/Ctrl, dock dicht, ingedockt)

Bron: `onClick` in [app.js r.1965-2031](../../static/js/app.js). Alles tot en met stap 7 draait synchroon in één taak; daarna volgen asynchrone delen.

```
Klik op gebied
 │
 ├─ 1. Selectie: clearGebiedSelection() + selectedGebiedIds.add(id)
 │
 ├─ 2. updateSelectionUI()
 │      - selectiebadge bijwerken (DOM)
 │      - emit SELECTIE_GEWIJZIGD
 │          ├─ kompas.js: badges bijwerken; bij actieve indicator
 │          │   loadIndicatorDetails() (fetch history, top-buurten,
 │          │   benchmark; Chart.js), anders _loadBenchmarkBarChart()
 │          ├─ mijn.js: knop 'Bewaar selectie' bijwerken (licht)
 │          └─ indicatorpaneel.js: niet actief (#panel-indicator bestaat
 │             sinds #444 niet meer; init() registreert niets)
 │
 ├─ 3. loadGebiedDetails(id)          → fetch; vult het linker info-paneel
 │
 ├─ 4. openRechterDock('kompas')
 │      - klasse .collapsed weg → transform-animatie 250 ms start bij volgend frame
 │      - updateMapPadding(true)    → padding 0 (geen effect)
 │      - switchDockTab('kompas')   → in volgend frame resize van grafieken
 │      - loadKompasForSelection()  → fetch Kompas            [aanroep 1]
 │
 ├─ 5. loadKompasForSelection()      → fetch Kompas            [aanroep 2]
 │
 ├─ 6. displayOnMap()                → laag opnieuw, gouden rand
 │
 └─ 7. setTimeout 50 ms → flyToGebied() → cameravlucht 800 ms

Asynchroon, zodra antwoorden binnen zijn (tijdstip onbekend):
 - antwoord aanroep 1: genegeerd (_loadRequestId, #463)
 - antwoord aanroep 2: renderSunburst() + bij actieve indicator
   expandDetails() → loadIndicatorDetails() (tweede keer, zie B2)
 - antwoord loadGebiedDetails: linker info-paneel vullen
```

### 3.3 Bevindingen uit de code (*feit*)

- **B1. Dubbele Kompas-aanroep.** `loadKompasForSelection` wordt twee keer aangeroepen: in `openRechterDock` ([app.js r.3276-3278](../../static/js/app.js)) en direct daarna in `onClick` ([r.1997-1999](../../static/js/app.js)). Gevolg: twee requests. Het eerste antwoord wordt weggegooid, de sunburst rendert één keer.
- **B2. Detailketen twee keer, zonder verzoek-id.** Bij een actieve indicator start `SELECTIE_GEWIJZIGD` de detailketen ([kompas.js r.3134-3141](../../static/js/kompas.js)). Als het Kompas-antwoord binnen is, start `expandDetails` die nog een keer ([r.1854](../../static/js/kompas.js)). `loadIndicatorDetails` heeft geen verzoek-id; de bescherming uit #463 geldt alleen voor `loadGebiedData`. *Hypothese:* bij snel achter elkaar klikken kan een laat antwoord van een vorig gebied het detailpaneel overschrijven.
- **B3. Wat de camera doet.** De camera centreert op het **klikpunt**, niet op het midden van het gebied. De zoom wordt `max(huidig, 12)`: hij zoomt in tot minimaal 12 en nooit uit. Pitch en draaiing blijven gelijk ([app.js r.4418-4475](../../static/js/app.js)). De verschuiving naar de vrije zone (`getFreezone`) wordt 50 ms na de klik berekend, als het dock al als open geldt.
- **B4. Smalle schermen (< 900 px).** Het dock is daar een paneel onderin (100% breed, 48vh hoog). `getFreezone` rekent alleen met de breedte: `rightEdge` wordt de schermbreedte en het doelcentrum komt op ±35 px van links. *Hypothese:* het gebied belandt aan de linkerrand en verticaal deels onder het paneel. Afgeleid uit de code, niet waargenomen.
- **B5. Minder beweging (`prefers-reduced-motion`).** Dit is al geregeld. Een CSS-regel zet alle transities op 0,01 ms ([styles.css r.4075-4084](../../static/css/styles.css)), dus het dock verschijnt direct. De camera springt zonder animatie via `A11y.cameraTransition`.
- **B6. Breedte van het dock.** `clamp(440px, 30vw, 560px)`. Op 1366 px is dat 440 px (32%); op 1920 px met 150% schaling (1280 CSS-px) 34%; met 125% schaling (1536 CSS-px) 30%. Onder 1400 px sluit het linker paneel automatisch (FE-5.2).

### 3.4 Varianten (*feit*, kort)

| Variant | Verschil met 3.2 |
|---|---|
| Shift/Ctrl-klik (meervoudige selectie) | Geen cameravlucht. Wel dock en Kompas: per gebied een fetch, door B1 twee keer (2×N), plus een selectie-fetch bij percentiel- of labelclassificatie. |
| Dock al open | Geen schuifanimatie; wel dezelfde laad- en renderketen. |
| Zwevend venster | Venster opent in plaats van het dock; `getFreezone` houdt rekening met de positie van het venster. |
| Klik tijdens een lopende vlucht | Nieuwe vlucht vanaf de huidige camerapositie; oude Kompas-antwoorden worden genegeerd, oude detailantwoorden niet (B2). |

### 3.5 Nog niet beschreven

- **Klik in het dock** (indicator, kruimelspoor, uitschieter): het effect op kaart en camera. #465 noemt deze situatie; analyse volgt.

---

## 4. Gebruikersverwachting: vragen ter toetsing

Eerste aanzet, af te stemmen met Taeke en Eduard. Per antwoord volgt een meetbaar criterium (sectie 6).

**Vraag 1: wat wil de gebruiker direct na een klik als eerste zien?**
- A. Eerst waar het gebied ligt (kaart), daarna de cijfers.
- B. Zo snel mogelijk de cijfers; de kaartbeweging is bijzaak.

**Vraag 2: moet het dock bij elke selectie automatisch openen?**
- A. Altijd (huidige eis FE-1.2).
- B. Nee, alleen als de gebruiker erom vraagt (badge of knop).
- C. Alleen als er al een indicator of het Kompas actief is.

**Vraag 3: wat moet de gebruiker in het dock zien terwijl de kaart nog beweegt?**
- Direct de cijfers van het nieuwe gebied, of is het acceptabel dat die pas verschijnen als de kaart stilstaat? Hoe lang mag dat duren?

**Vraag 4: wat verwacht de gebruiker op smalle schermen?**
- Laptop (±1280–1536 CSS-px): het dock neemt 30–34% van de breedte in. Is die verhouding goed, of moet het dock daar kleiner of pas op verzoek openen?
- Telefoon en tablet staand (< 900 px): het dock bedekt de onderste helft. Waar moet het geselecteerde gebied dan in beeld komen?

**Vraag 5: wat verwacht de gebruiker bij een tweede klik terwijl de kaart nog beweegt, of bij een meervoudige selectie?**
- Moet de kaart direct naar het nieuwe gebied, en moeten de cijfers altijd bij het laatst gekozen gebied horen?

Bij alle varianten blijft gelden: met `prefers-reduced-motion` geen animatie (B5, WCAG 2.1 AA).

---

## 5. Meetplan (nog uit te voeren)

**Methode:** Chrome DevTools, tabblad Performance, opname van één klik tot alles stilstaat. Elk scenario drie keer, zonder en met CPU-vertraging (4×). Ruwe opnames (`.json`) bewaren bij dit document.

**Per opname vastleggen:**

| Meetpunt | Waarom |
|---|---|
| Tijd van klik tot eerste frame met gouden rand | Directe feedback |
| Aantal frames > 16,7 ms en > 50 ms tijdens de vlucht | Haperen |
| Tijdstip van de Kompas- en detailantwoorden ten opzichte van de vlucht | Toetst H1 en H2 |
| Duur van de langste taken (`renderSunburst`, `loadIndicatorDetails`, `displayOnMap`) | Toetst H1, H2 en H5 |
| Zelfde opname met de blur uitgezet via DevTools | Toetst H3 |

**Scenario's:**

| # | Scherm | Dock vooraf | Indicator actief | Selectie |
|---|---|---|---|---|
| S1 | Desktop 1920 | dicht | nee | 1 gebied |
| S2 | Desktop 1920 | dicht | ja | 1 gebied |
| S3 | Desktop 1920 | open | ja | 1 gebied |
| S4 | Laptop 1366 | dicht | ja | 1 gebied |
| S5 | Desktop 1920 | open | ja | Shift-klik, 3 gebieden |
| S6 | Telefoon < 900 px (emulatie) | dicht | ja | 1 gebied (toetst B4) |
| S7 | Desktop 1920 | dicht | ja | 1 gebied, `prefers-reduced-motion` aan |

H4 (`preserveDrawingBuffer`) is niet via DevTools uit te zetten; die toetsen we alleen als H1 tot en met H3 het haperen niet verklaren.

**Uitkomsten:**
- **S1 (Nulmeting Desktop):** zie [`testresultaten/scenario-1-nulmeting.md`](testresultaten/scenario-1-nulmeting.md) (B1, H1 en H2 bewezen; Long Task van 127 ms + layout thrashing).
- **S2 t/m S7:** nog te meten.

---

## 6. Vervolg

1. Metingen uitvoeren (sectie 5) en de uitkomsten hier vastleggen.
2. De vijf vragen beantwoorden met Taeke en Eduard; per antwoord een meetbaar criterium vastleggen.
3. Klik in het dock analyseren (3.5).
4. Vervolgissue aanmaken voor de uitwerking van het gewenste gedrag; daarna #465 sluiten.

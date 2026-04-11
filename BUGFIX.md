# BUGFIX.md - D-OmniTwin

## Bug #42: 3D BAG Panden Kleuren Enkel bij Multi-Selectie (28-03-2026)

**Gerapporteerd:** 28-03-2026 00:33  
**Status:** ⏳ OPEN  
**Severity:** 🟡 MEDIUM (Visuele feedback ontbreekt bij 1 buurt)

### Probleem
Wanneer een gebruiker 1 buurt selecteert en op de "🏗️ 3D Panden" knop drukt, worden de gebouwen correct geladen, maar krijgen ze niet de kleur van de geselecteerde indicator (bijv. Bouwjaar of de gebieds-gradiënt). Dit gebeurt pas als er 2 buurten geselecteerd zijn.

### Mogelijke Oorzaken
1. De backend logic in `routers/bag3d.py` zoekt expliciet naar bepaalde indicator codes (zoals `BOUWJAAR_INDICATOR_CODES`), die mogelijk niet matchen met de daadwerkelijke UUIDs of codes in de database.
2. De context die vanuit de frontend wordt meegestuurd (via `selectedGebiedIds` en de indicator) mist mogelijk specifieke data voor singuliere selecties, of de fallback structuur wordt getriggerd bij een enkele BBOX, waarbij de kleur-metadata niet doorkomt.

### Geplande Fix
Onderzoeken welke indicator codes/UUIDs er precies in the database hangen voor `bouwjaar` en in de backend query (`bag3d.py`) en zorgen dat single-gebied the indicator mapping correct aanhoudt.

---## Bug #41: Sunburst Zoom Reset bij wisselen tussen indicatoren (24-03-2026)

**Gerapporteerd:** 24-03-2026 20:18  
**Status:** ✅ FIXED (24-03-2026)  
**Severity:** 🟡 MEDIUM (UX - ongewenste navigatie)

### Probleem
Wanneer een gebruiker in het uitgeklapte detailvenster van indicator A naar indicator B klikte (bijv. van "diefstal fiets" naar "inbraak auto"), sprong de sunburst-viz terug naar het root-niveau (default), terwijl de gebruiker op hetzelfde niveau wilde blijven.

### Oorzaak
`syncIndicatorToMap()` verstuurde een `INDICATOR_SELECTED` event. De Kompas-module luisterde zelf ook naar dit event voor Chat-synchronisatie. De listener riep `navigateToIndicator()` aan, die de sunburst altijd vanaf de root opnieuw inzoomde. Er was een guard (`_isSyncing`), maar deze werd niet gezet in de directe klik-handler flow.

### Fix
**File:** `static/js/kompas.js`
In `syncIndicatorToMap()` wordt de `_isSyncing` guard nu expliciet op `true` gezet vóórdat het event wordt verstuurd. Hierdoor negeert de Kompas-module zijn eigen event, terwijl externe triggers (vanuit de chat) nog steeds werken.

---

## Bug #40: Kompas Venster Reset naar Default Grootte bij klik (24-03-2026)

**Gerapporteerd:** 24-03-2026 20:08  
**Status:** ✅ FIXED (24-03-2026)  
**Severity:** 🟡 MEDIUM (UX - irriterend gedrag)

### Probleem
Wanneer de gebruiker het Kompas-venster handmatig groter sleepte (resizable), sprong het venster bij elke klik in de sunburst (zoomen) terug naar de standaardafmetingen (650x800).

### Oorzaak
In `collapseDetails()` (die bij elke zoom-actie wordt aangeroepen) werden de inline `style.width` en `style.height` expliciet leeggemaakt (`''`). Ook `init()` en `expandDetails()` forceerden of wisten inline styles, wat conflicteerde met de afmetingen die `DraggableWindow` via inline styles beheert.

### Fix
**File:** `static/js/kompas.js`
Alle code die inline `width` en `height` forceert of wist is verwijderd. 
- CSS `.expanded` gebruikt nu `!important` om de breedte naar 1100px te dwingen.
- Zodra de `.expanded` class wordt verwijderd, nemen de inline styles van `DraggableWindow` (het resultaat van het slepen/resizen) weer automatisch de controle over zonder dat de JS ze wist.

---

## Bug #39: Kompas Zoom Reset bij wisselen van Buurt (24-03-2026)

**Gerapporteerd:** 24-03-2026 19:10  
**Status:** ✅ FIXED (24-03-2026)  
**Severity:** 🟡 MEDIUM (UX - navigatieverlies)

### Probleem
Bij het wisselen naar een andere buurt op de kaart sprong het Kompas altijd terug naar het hoofdmenu (root), ook als de gebruiker diep ingezoomd was op een specifiek thema (bijv. Veiligheid).

### Oorzaak
`loadGebiedData()` had geen logica om het huidige `zoomPath` en de `isExpanded` status te bewaren en te herstellen na de re-render van de data.

### Fix
**File:** `static/js/kompas.js`
De state-preservation logica uit `loadMultiGebiedData` is geport naar `loadGebiedData`. Vóór het ophalen van nieuwe data wordt het zoom-pad opgeslagen via `_getZoomPath()`. Na het renderen wordt dit pad hersteld via `_navigateToPath()`.

---

## Bug #38: Rechterrand Kompas valt buiten beeld in Expanded View (24-03-2026)

**Gerapporteerd:** 24-03-2026 18:57  
**Status:** ✅ FIXED (24-03-2026)  
**Severity:** 🟡 MEDIUM (Visueel defect)

### Probleem
In de uitgeklapte (expanded) modus was de rechterrand van het Kompas-venster niet zichtbaar (afgesneden door de schermrand), terwijl er aan de linkerkant nog wel ruimte was.

### Oorzaak
In `kompas.js` stond de `expandedWidth` in de functie `checkWindowBounds` hardcoded op `900px`, terwijl de CSS (`styles.css`) het venster naar `1100px` breed maakte. Hierdoor dacht de JavaScript dat het venster nog op het scherm paste, terwijl het in werkelijkheid over de rand viel.

### Fix
**File:** `static/js/kompas.js`
`expandedWidth` aangepast naar `1100` in de `checkWindowBounds` methode om overeen te komen met de CSS-definitie. Het venster schuift nu correct naar links als er rechts te weinig ruimte is.

---

## Bug #37: MAAK_RAPPORT opent altijd lege benchmark — selectie wordt genegeerd (20-03-2026)

**Gerapporteerd:** 20-03-2026 18:20  
**Status:** ✅ FIXED (20-03-2026)  
**Severity:** 🟡 MEDIUM (Functionaliteit werkt niet zoals bedoeld)

### Probleem
De "Rapport genereren" actie-knop in de D-Omni Assistent chat opende altijd de **lege** Benchmark Vergelijker pagina, ongeacht of er buurten geselecteerd waren op de kaart. Het gebiedsdossier (bij 1 selectie) of de voorgevulde benchmark (bij multi-selectie) werd nooit getoond.

### Oorzaak
`chat.js` las `window.state?.selectedGebiedIds` om de huidige kaart-selectie op te halen. Echter: de `state` variabele in `app.js` was een **lokale `const`** die niet op het `window` object was gepubliceerd. Daardoor was `window.state` altijd `undefined`, en viel de logica terug naar het `length === 0` pad (lege benchmark).

### Fix
**File:** `static/js/app.js` (regel 42)

```js
// Publiceer state op window zodat chat.js en andere modules de kaartselectie kunnen lezen
window.state = state;
```

Omdat `state` een object is, is dit een referentie — `chat.js` leest nu dezelfde `Set` die `app.js` bijwerkt bij klik/Shift+Click.

### Verificatie
- ✅ 1 buurt geselecteerd → opent Gebiedsdossier (`/admin/rapport/{buurt_id}`)
- ✅ Multi-selectie (Shift+Click) → opent Benchmark met gebieden voorgevuld
- ✅ Geen selectie → opent lege Benchmark (ongewijzigd gedrag)

---

## Bug #36: Event-Loop Chat↔Kompas INDICATOR_SELECTED (19-03-2026)

**Gerapporteerd:** 19-03-2026 23:11  
**Status:** ✅ FIXED (19-03-2026)  
**Severity:** 🔴 HIGH (Continue loop — kaart laadde dezelfde indicator eindeloos opnieuw)

### Probleem
Na het implementeren van de Chat↔Kompas sync (Sprint 10) ontstond een oneindige event-loop zodra de gebruiker op een indicator klikte vanuit de D-Omni Assistent:

1. Chat klikt indicator → `EventBus.emit('INDICATOR_SELECTED')`
2. `app.js handleIndicatorSelection` → laadt kaartdata ✅
3. `kompas.js` listener → `navigateToIndicator(uuid)`
4. `navigateToIndicator` → `syncIndicatorToMap` → `EventBus.emit('INDICATOR_SELECTED')` 🔄
5. Terug naar stap 2 — **oneindige loop**

### Oorzaak
De `navigateToIndicator()` methode roept intern `syncIndicatorToMap()` aan, die op zijn beurt `INDICATOR_SELECTED` emit. De nieuwe EventBus listener in de Kompas-module had geen guard om zijn eigen downstream events te negeren.

### Fix
**File:** `static/js/kompas.js`

`_isSyncing` flag toegevoegd op de `kompasViz` instantie:
```js
kompasViz._isSyncing = false;
window.EventBus.on('INDICATOR_SELECTED', (data) => {
    if (kompasViz._isSyncing) return; // LOOP GUARD
    kompasViz._isSyncing = true;
    kompasViz.navigateToIndicator(data.uuid);
    setTimeout(() => { kompasViz._isSyncing = false; }, 1200);
});
```
De guard resettet na 1200ms (ruim genoeg voor de 800ms zoom-animatie).

### Verificatie
- ✅ Klik op indicator in chat → kaart laadt éénmalig, Kompas navigeert éénmalig
- ✅ Geen herhaalde API calls in Network tab

---

## Bug #35: Overlappende Buurtgeometrieën Smallingerland (17-03-2026)

**Gerapporteerd:** 17-03-2026 21:26
**Status:** ✅ FIXED (17-03-2026)
**Severity:** 🟡 MEDIUM (Visuele vervuiling)

### Probleem
Na de import van de CBS 2024 buurtindeling waren er in Smallingerland dubbele lagen zichtbaar op de kaart. De oude buurtgeometrieën (uit een eerdere import) lagen onder de nieuwe 2024 indeling, wat leidde tot visuele artifacten en onduidelijkheid bij selectie.

### Oorzaak
De nieuwe 2024 buurten hebben vaak dezelfde of vergelijkbare codes als de oude buurten, maar de geometrieën zijn veranderd. De oude records stonden nog op `actief = true`.

### Fix
**Database SQL:**
Alle buurten in Smallingerland (`id LIKE 'BU0090%'`) die NIET onderdeel uitmaakten van de meest recente 2024 import (`created_at < '2026-03-17'`) zijn op `actief = false` gezet. Dit verbergt de oude geometrieën terwijl historische data behouden blijft.

---

## Bug #34: NULL Geometries in GeoJSON breaking Map Rendering (17-03-2026)

**Gerapporteerd:** 17-03-2026 21:18
**Status:** ✅ FIXED (17-03-2026)
**Severity:** 🔴 HIGH (Kaart laadt niet / Pydantic validatiefout)

### Probleem
De kaart-API (`/api/kaart/v2/data`) retourneerde 500 errors of de frontend gaf Pydantic validatiefouten: `Input should be a valid dictionary` voor het `geometry` veld. Dit gebeurde specifiek wanneer Gemeente (GM) of Wijk (WK) records zonder geometrie werden meegegeven in de buurt-weergave.

### Oorzaak
De query in `get_kaart_data_v2` selecteerde ook records uit de view `vw_gebied_kaart_basis` waarvoor `st_asgeojson(geom)` NULL retourneerde. Pydantic verwacht voor een GeoJSON Feature echter een dictionary of null-object, maar de implementatie in Python voegde deze features toch toe aan de lijst.

### Fix
**File:** `services/gebiedsmonitor_service.py`
In de `features` builder is een expliciete check toegevoegd: `if not row["geometry"]: continue`. Hierdoor worden records zonder geometrie volledig overgeslagen in de GeoJSON response, wat de validatiefout opgelost heeft.

---


**Gerapporteerd:** 15-03-2026 21:22
**Status:** ✅ FIXED (15-03-2026)
**Severity:** 🟢 LOW (UX Verbetering)

### Probleem
Bij het selecteren van een indicator via de AI-zoekfunctie opende het detailpaneel wel, maar het Kompas (Sunburst) zoomde niet in op het betreffende kwadrant of thema. De gebruiker verloor hierdoor de visuele context van de indicator in de hiërarchie.

### Oorzaak
De `navigateToIndicator` functie in `kompas.js` riep de `_zoomFn` direct aan op de indicator (leaf node). Omdat leaf nodes geen kinderen hebben, deed de zoom-transitie niets.

### Fix
**File:** `static/js/kompas.js`
In `navigateToIndicator(uuid)` wordt nu gecheckt of de target node een leaf is. Indien ja, wordt er ingezoomd op de **parent** (het Thema). Hierdoor krijgt de gebruiker de juiste context te zien terwijl de details worden getoond.

### Verificatie
- ✅ Klikken op een zoekresultaat (bijv. "Inbraak") zoomt de Sunburst naar het thema "Veiligheid".

---

## Bug #27: Kompas Tooltips vallen achter het venster (15-03-2026)

**Gerapporteerd:** 15-03-2026 20:31
**Status:** ✅ FIXED (15-03-2026)
**Severity:** 🟡 MEDIUM (Informatie onzichtbaar)

### Probleem
Na het verhogen van de z-index van het Kompas venster (voor zichtbaarheid), vielen de hover-tooltips van de Sunburst achter het venster.

### Oorzaak
Het Kompas venster kreeg een z-index van `10000`, terwijl de `.kompas-tooltip` nog op de standaard `9999` stond.

### Fix
**File:** `static/css/styles.css`
De `z-index` van `.kompas-tooltip` is verhoogd naar `11000`.

### Verificatie
- ✅ Tooltips zijn weer zichtbaar over het gehele Kompas venster.

---

## Bug #26: Kompas Venster Onzichtbaar of Off-screen (15-03-2026)

**Gerapporteerd:** 15-03-2026 13:58
**Status:** ✅ FIXED (15-03-2026)
**Severity:** 🔴 HIGH (Functionaliteit onbereikbaar)

### Probleem
Het Kompas venster was voor sommige gebruikers onzichtbaar of verscheen buiten het scherm na een herlaad-actie. Ook overlapten andere UI elementen (zoals de kaart-legenda) soms het venster.

### Oorzaak
1. **Z-Index Conflict:** Meerdere definities van `.floating-window` met verschillende z-indexen.
2. **Geen Boundary Checks:** De `DraggableWindow` klasse bewaarde coördinaten zonder te controleren of deze nog binnen de huidige viewport pasten bij het herstellen van de sessie.
3. **Instabiele CSS:** `position: absolute` werd onterecht gebruikt in plaats van `fixed`.

### Fix
**Files:** `static/css/styles.css`, `static/js/draggable-window.js`
1. **CSS Consolidatie:** Alle `.floating-window` definities samengevoegd tot één robuuste klasse met `z-index: 10000` en `position: fixed`.
2. **Viewport Safety:** `DraggableWindow.js` uitgebreid met boundary checks in de `open()`, `centerWindow()` en `restorePosition()` functies. Als een venster buiten beeld dreigt te vallen, wordt het automatisch teruggehaald naar het midden of binnen de schermranden 'geclampt'.

### Verificatie
- ✅ Kompas venster opent altijd binnen de zichtbare viewport.
- ✅ Venster blijft bovenop alle andere UI elementen (behalve tooltips).

---

**Gerapporteerd:** 06-03-2026 17:36
**Status:** ✅ FIXED (06-03-2026)
**Severity:** 🟡 MEDIUM (3D visualisatie deels onbruikbaar)

### Probleem
Meerdere bugs traden op bij het in- en uitschakelen van "3D Extrusie" in de kaartweergave:
1. **Camera Reset:** Bij het toggelen van 3D verloor de kaart direct zijn zoomniveau en coördinaten en sprong deze terug naar het midden van de oceaan (lat 0, lon 0, zoom 0).
2. **Kleurverlies (Grijs/Transparant):** 3D blokken werden volledig grijs, transparant of erg flets wit weergegeven en verloren hun originele data-kleur.
3. **Triangulatie WebGL Corruptie:** Bij het terugschakelen van 3D naar 2D veranderden de polygoonvormen in gebroken triangulatie-driehoeken (corrumperende WebGL buffers).

### Oorzaak
1. **Camera:** De toggle-functie las uit `deckgl.viewState` wat `undefined` is in "uncontrolled" opstellingen. Dit werd meegegeven aan de nieuwe map properties.
2. **Kleurverlies:** Zware belichting in materialen (`shininess`, `specularColor`) vervaagde platte objecten naar wit. Ook werd 3D belichting bij een frame drop (<30 fps) structureel uitgeschakeld via `checkPerformance` wat resulteerde in grijze/onbelichte blokken. Polygonen stonden op transparant ingesteld.
3. **Triangulatie:** Het "platdrukken" (`extruded: false`) van 3D geometrie overschrijft buffers die voor vlakke lagen bedoeld zijn.

### Fix
**File:** `static/js/app.js`

1. **Camera:** `onViewStateChange` listener geïntroduceerd om live de camerahoek op te slaan. De toggle functie leest nu netjes deze opgeslagen state uit.
2. **Kleuren & Belichting:** `checkPerformance` schakelt lighting effecten niet meer uit. Lichtbron omgeschakeld van `_SunLight` naar een vastere `DirectionalLight`. Het deck-materiaal is `matte` ingesteld (0 shininess).
3. **Polygon Transparantie:** Ingeschakeld dat de `opacity` van de kaart, highlights, en "Geen Data" automatisch naar 100% (`255`) springt bij 3D weergave, zodat 2D doorschijnendheid geen 3D kleuren verwast.
4. **Triangulatie:** De dynamische Layer ID's opgesplitst (bijv. `gebieden-layer-3d` en `gebieden-layer-2d`). Bij een toggle wordt de deck.gl laag the fresh geïnstantieerd ter bescherming van the buffers.

### Verificatie
- ✅ Togglen van 3D behoudt de huidige kaartpositie exact.
- ✅ In 3D weergave blijven the blokken perfect the respectievelijke gebiedskleuren behouden.
- ✅ WebGL the artifacts in de 2D vlakken zijn structureel the weg.

---

## Bug #24: Benchmark Gemeente Gemiddelde Toont Geen Data (05-03-2026)

**Gerapporteerd:** 05-03-2026 19:53
**Status:** ✅ FIXED (05-03-2026)
**Severity:** 🟡 MEDIUM (Functionaliteit stuk — alleen gemeente modus)

### Probleem
De Benchmark Vergelijker in modus "Gemeente Gemiddelde" toonde geen resultaten. De modus "Fryslân Gemiddelde" en "Specifieke Gebieden" werkten wel correct.

### Oorzaak
**Type mismatch tussen API response en frontend.**

De `/api/gemeenten` endpoint retourneert objecten met property `code` (bijv. `"0081"`), maar de dropdown in `BenchmarkPage.tsx` gebruikte `g.id` als `<option value={g.id}>`. Aangezien de gemeenten-objecten geen `id` property hebben, was deze waarde `undefined`. Het backend ontving een lege `referentie_gemeente` parameter en retourneerde dus geen data.

### Fix
**Files:** `admin-panel/src/pages/BenchmarkPage.tsx`, `admin-panel/src/services/api.ts`

1. **Dropdown value:** `g.id` → `g.code` in de gemeente `<select>` opties.
2. **TypeScript type:** `getGemeenten()` return type gecorrigeerd van `GebiedListItem[]` (`{id, naam}`) naar `{code: string; naam: string}[]`.
3. **State type:** `useState<GebiedListItem[]>` → `useState<{code: string; naam: string}[]>` voor de gemeenten state.

### Verificatie
- ✅ Gemeente Gemiddelde modus toont volledige vergelijkingstabel
- ✅ TypeScript build compileert zonder errors

### Opmerking
Bij het rebuilden van het admin panel: **stop eerst `npm start`** voordat je `npm run build` runt. Beide processen tegelijk draaien in dezelfde directory kan de build laten hangen.

---

## Bug #22: Ngrok Tunneling — Rapport Routing, CORS en Stale Build (05-03-2026)

**Gerapporteerd:** 05-03-2026 19:15
**Status:** ✅ FIXED (05-03-2026)
**Severity:** 🔴 HIGH (Meerdere features stuk via ngrok)

### Probleem
Bij het serveren van de applicatie via ngrok traden drie afwijkingen op t.o.v. localhost:
1. **Benchmark routing faalde:** Multi-selectie van buurten opende de rapport-pagina i.p.v. de benchmark-pagina.
2. **API 404 errors:** Z-score datapunten gaven `Request failed with status code 404`.
3. **Auth bypass:** Het admin dashboard was direct bereikbaar zonder loginscherm.

### Oorzaak
**1. Hardcoded localhost URL-constructie** in `static/js/app.js` (regel 1711-1713):
```js
const isLocalhost = window.location.hostname === 'localhost' || ...;
const baseUrl = isLocalhost ? `http://${window.location.hostname}:3000` : '';
```
Op localhost werd de React dev-server (port 3000) gebruikt. Via ngrok werd een lege baseUrl gebruikt die naar de **gebouwde** admin panel verwees — welke verouderd was.

**2. Verouderde admin panel build** (`static/admin-panel/`): De gebouwde versie kende de benchmark-route niet, waardoor React Router `/rapport/benchmark?...` matchte op `/rapport/:gebied_id?` (met "benchmark" als een gebied-ID).

**3. CORS configuratie** in `main.py`: Alleen `localhost` origins waren toegestaan, de ngrok URL niet. Hierdoor faalden sommige API calls.

**4. Auth "bypass"**: Geen echte kwetsbaarheid — de sessie-cookie (zonder `domain` restrictie) werd door de browser ook naar ngrok meegestuurd. Gecombineerd met de verouderde build leidde dit tot schijnbare auth-bypass.

### Fix
**Files:** `static/js/app.js`, `main.py`, `static/admin-panel/` (rebuild)

1. **Relatieve URLs:** `isLocalhost` check verwijderd, `baseUrl` is nu altijd `''` (relatief). Werkt universeel voor localhost, ngrok en productie.
2. **CORS regex:** `allow_origin_regex=r"https://.*\.ngrok-free\.dev"` toegevoegd aan CORSMiddleware (alleen in DEBUG mode).
3. **Admin panel rebuild:** Verse `npm run build` + deploy naar `static/admin-panel/`.
4. **Workflow aangemaakt:** `.agents/workflows/build-admin-panel.md` zodat de build-stap bij toekomstige wijzigingen niet vergeten wordt.

### Verificatie
- ✅ Multi-selectie via ngrok opent nu correct de benchmark-pagina
- ✅ Geen CORS errors meer in browser devtools
- ✅ Workflow `/build-admin-panel` beschikbaar voor toekomstige builds

---

## Bug #23: Connection Pool Exhaustion bij Multi-Gebied Selectie (05-03-2026)

**Gerapporteerd:** 05-03-2026 19:36
**Status:** ✅ FIXED (05-03-2026)
**Severity:** 🔴 HIGH (Applicatie loopt vast bij 5+ gebieden)

### Probleem
Bij het selecteren van meerdere gebieden (5+) liep de applicatie vast met de foutmelding:
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached,
connection timed out, timeout 30.00
```

### Oorzaak
`create_engine()` in `src/database.py` had geen pool parameters, waardoor SQLAlchemy defaults werden gebruikt (`pool_size=5`, `max_overflow=10`, totaal max 15 connecties). Bij multi-selectie worden er parallel API calls afgevuurd (gebiedsdata, kompas, vergelijking per gebied), die elk een eigen DB-connectie claimen. Bij 5+ gebieden raakt de pool uitgeput.

### Fix
**File:** `src/database.py`

Connection pool parameters vergroot:
| Parameter | Was (default) | Nu |
|-----------|--------------|-----|
| `pool_size` | 5 | 20 |
| `max_overflow` | 10 | 20 |
| `pool_pre_ping` | ❌ | ✅ |
| `pool_recycle` | ❌ | 1800s (30 min) |

### Verificatie
- ✅ Selectie van 5+ gebieden tegelijk levert geen timeout meer op
- ✅ Parallelle API calls worden correct afgehandeld

---

## Bug #21: Kompas SVG Tekst Onleesbaar in Light Mode (03-03-2026)

**Gerapporteerd:** 03-03-2026 17:15
**Status:** ✅ FIXED (03-03-2026)
**Severity:** 🟡 MEDIUM (Slecht contrast)

### Probleem
De hiërarchische labels in het D3.js Sunburst Kompas waren deels of volledig onzichtbaar wanneer de applicatie in Light Mode werd gezet, omdat the labels hardcoded waren op wit (`fill: #fff`), onafhankelijk van de lichte container background. 

### Fix
**File:** `static/js/kompas.js`
In de SVG label declarateur werd het statische `.attr('fill')` veranderd naar een dynamische pseudo-pointer: `.style('fill', 'var(--text-primary)')`. Dit stelt de labels in staat om on-the-fly mee te verkleuren zodra the user in Windows of MacOS the systeem-voorkeur voor light mode toggleert, zonder the chart geforceerd te hoeven herladen!

---

## Bug #20: Logo Onzichtbaar in Light Mode op Gradient-Header (03-03-2026)

**Gerapporteerd:** 03-03-2026 17:00
**Status:** ✅ FIXED (03-03-2026)
**Severity:** 🟡 MEDIUM (Branding)

### Probleem
Het dark-blue π-node PNG logo werd onzichtbaar nadat the CSS Header styles gemoduleerd the werden nar the nieuwe Trust Blue → Nature Green gradiënten, omdat the header zelf in light mode the donker genoeg remained voor dark tekst.

### Fix
**File:** `static/css/styles.css`
Er is een expliciet CSS filter toegekend op the `.header-logo` class base (`filter: brightness(0) invert(1) drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3));`), waardoor the PNG file onafhankelijk van zijn source pixels, the exact de styling pakt van witte the header titels, the dit voorkomt future bugs the het opladen the van dark assets the lichte applicatie balken!

---

## Bug #19: Gemeente Dropdown Onleesbaar in Dark Mode (02-03-2026)

**Gerapporteerd:** 02-03-2026 21:54
**Status:** ✅ FIXED (02-03-2026)
**Severity:** 🟢 LOW (UI Leesbaarheid)

### Probleem
De gemeentenamen in de `<select>` dropdown van de BenchmarkPage "Referentie Gemeente" modus waren nauwelijks leesbaar: lichtgrijze tekst op een bijna identiek grijze achtergrond in dark mode.

### Oorzaak
Native `<select>` `<option>` elementen erven de CSS variabelen (`--color-bg-alt`, `--color-text`) niet consistent. Browsers renderen opties met hun eigen platform-stijl, waardoor de donkere achtergrond uit de `<select>` parent niet doorwerkt op de options list.

### Fix
**File:** `admin-panel/src/pages/BenchmarkPage.tsx`

Expliciete inline `style={{ background: '#1e2535', color: '#e2e8f0' }}` toegevoegd op alle `<option>` elementen in de gemeente `<select>`.

---

## Bug #18: Benchmark Route Vereiste Login (02-03-2026)

**Gerapporteerd:** 02-03-2026 21:44
**Status:** ✅ FIXED (02-03-2026)
**Severity:** 🔴 HIGH (Toegang geblokeerd)

### Probleem
De `BenchmarkPage` (`/admin/rapport/benchmark`) was gewrapped in `<ProtectedRoute>` en stuurde niet-ingelogde gebruikers door naar het loginscherm. De standaard `ReportPage` (`/admin/rapport/:id`) was al publiek toegankelijk — inconsistentie.

### Oorzaak
Bij het toevoegen van de Benchmark route in `App.tsx` was per ongeluk de `<ProtectedRoute>` wrapper toegepast, terwijl de context (rapport genereren vanuit kaart) geen login vereist.

### Fix
**File:** `admin-panel/src/App.tsx` (regel 258-260)

`<ProtectedRoute><BenchmarkPage /></ProtectedRoute>` vervangen door directe `<BenchmarkPage />`, identiek aan de `ReportPage` route.

---

## Bug #17: Typeahead Zoek 422 — Benchmark Dropdown Leeg (02-03-2026)

**Gerapporteerd:** 02-03-2026 21:34
**Status:** ✅ FIXED (02-03-2026)
**Severity:** 🔴 HIGH (Functionaliteit volledig stuk)

### Probleem
De zoekdropdown in de `BenchmarkPage` bleef altijd leeg. Elke zoekterm resulteerde in een lege dropdown zonder suggesties.

### Oorzaak
`gebiedenAPI.getGebieden()` riep `GET /api/gebieden` aan zonder de verplichte `gemeente_code` query parameter. Het backend-endpoint had `gemeente_code: str = Query(...)` (verplicht), waardoor FastAPI een **422 Unprocessable Entity** teruggaf. De frontend ving dit niet af — `allGebieden` bleef leeg.

### Fix
**Files:** `routers/gemeenten.py`, `admin-panel/src/services/api.ts`, `admin-panel/src/pages/BenchmarkPage.tsx`

1. **Nieuw endpoint** `GET /api/gebieden/zoek?q=<term>` toegevoegd in `routers/gemeenten.py` — full-text zoekopdracht op naam/ID zonder gemeente vereiste, min 2 karakters, max 50 resultaten.
2. **API service** vervangen: `getGebieden()` → `zoekGebieden(q)` in `admin-panel/src/services/api.ts`.
3. **BenchmarkPage** omgebouwd van "pre-load alle gebieden" naar **live debounced search** (300ms debounce via `useRef` + `setTimeout`).
4. **URL pre-populatie** toegevoegd: `?gebied_a=BU...&gebieden_b=BU...,BU...` queryparams worden uitgelezen bij mount zodat kaart-selectie de BenchmarkPage kan pre-vullen.

### Verificatie
- ✅ `curl "http://localhost:8000/api/gebieden/zoek?q=Sneek"` → `{"gebieden":[{"id":"BU19000101","naam":"Sneek binnen de grachten","type":"CBS_BUURT"}],"totaal":1}`
- ✅ `curl "http://localhost:8000/api/gebieden/zoek?q=S"` → 422 (min_length=2 gerespecteerd)
- ✅ Dropdown toont suggesties tijdens typen

---

## Bug #15: PDF Export Bestandsnaam en Kleuren (22-02-2026)

**Gerapporteerd:** 22-02-2026 21:00  
**Status:** ✅ FIXED (22-02-2026)  
**Severity:** 🟡 MEDIUM (Print layout)

### Probleem
De "Exporteer PDF" knop resulteerde in in transparante/onleesbare tekst in de afdruk-weergave wegens lichte dark-mode font-kleuren. Het systeem genereerde daarnaast geen logische werkende bestandsnamen bij de opslaan-dialoog (gebroken door o.a speciale karakters `ú`).

### Fix
**Files:** `admin-panel/src/styles/admin.css`, `admin-panel/src/pages/ReportPage.tsx`
1. **CSS `@media print` Override:** Toevoeging van `:root` overrides specifiek voor de print flow. Dit forceert `.text-secondary` en the gridlijnen the dark contrast levels de gebruiken.
2. **Dynamische Opslaan-als API:** Javascript timeout en `window.afterprint` the injectie van `document.title` inclusief clean-regex van accentueerde karakters (Súdwest = Sudwest).

---

## Bug #16: Transparante Ghost Outline op Header Dropdown (24-02-2026)

**Gerapporteerd:** 24-02-2026 12:35  
**Status:** ✅ FIXED (24-02-2026)  
**Severity:** 🟢 LOW (UI Visual Artefact)

### Probleem
Nadat In the React App (`App.tsx`) een profiel-dropdown component (icoon `Gebruiker` & `ChevronDown`) is gebouwd, werd een spook-achtig vierkant transparant overlay-blokje over de knop zichtbaar. Dit gebeurde uitsluitend als we op de `DashboardPage` stonden.

### Fix
**Files:** `admin-panel/src/App.tsx`
1. **Focus/Click Outline Override:** Direct inline in de Account knop alle standard pseudo styling uitgeschakeld (`outline: 'none'`, `box-shadow: 'none'`, `WebkitTapHighlightColor: 'transparent'`).
2. **Z-Index Reparatie:** De root oorzaak bleek the overlappen the long-scrolling layout in het Dashboard. De header wrapper in `App.tsx` heeft strict `position: 'relative', zIndex: 50` gekregen, en the specifieke dropdown de index `51`.

---

## Bug #14: React Public Routing (22-02-2026)

**Gerapporteerd:** 22-02-2026 18:00  
**Status:** ✅ FIXED (22-02-2026)  
**Severity:** 🟡 MEDIUM (Toegang)

### Probleem
De rapport links (zoals the alias route `/publiek-rapport/:id`) fileden on the routeren omdat `/rapport/:id` omwille van default the architecture the afgeschermd werd door de auth `ProtectedRoute` in App.tsx. De gebruiker werd terug gestuurd naar `/admin/login`.

### Fix
In `admin-panel/src/App.tsx` The routing verplaatst naar The de publieke tree (buiten the beschermende React auth loop).

---

## Bug #13B: Z-Score Impact Discrepanties & Indicator Opschoning (22-02-2026)

**Gerapporteerd:** 22-02-2026 13:00  
**Status:** ✅ FIXED (22-02-2026)  
**Severity:** 🟡 MEDIUM

### Probleem
Z-scores met `-` waarden gaven "ongekend-negatief" of "groen positief" out-of-sync statussen aan afhankelijk van hoe een omgekeerde parameter (+/-) gedefinieerd the is in the backend visueel the vergeleken the met the de CSS gradienten. The frontend the had the verkeerde signaalonafhankelijke kleur in the ReportPage labeltjes.

### Fix
1. In `ReportPage.tsx` de Z-score parser `determineImpact` 100% één-op-één the gezet the de database backend string (`scoreType`). 
2. Met SQL the duplicate (incompleet gevulde via CBS) The indicatoren zoals `koopwoningen` vs `% koopwoningen` opgezocht en verwijderd (Database the CASCADE rule the the the redding).

---

## Bug #12: AI (Qwen3) Retourneert Ruwe Tekst i.p.v. JSON (20-02-2026)

**Gerapporteerd:** 20-02-2026 21:30  
**Status:** ✅ FIXED (21-02-2026)  
**Severity:** 🟡 MEDIUM (AI summary output)

### Probleem
Wanneer een gebruiker op "Genereer AI Rapport" klikt in de React frontend, doet de backend een verzoek aan het lokale Ollama model (`qwen3:30b`). De `llm_service.py` verwacht strict JSON output, maar het model retourneert ruwe tekst.
Hierdoor toont de frontend de melding: `Fout: De AI retourneerde geen valide JSON. Ruwe output: [Verhaal van de AI over het geselecteerde gebied]`.

### Oorzaak
Het System Prompt instrueert het model momenteel met: `"Retourneer UITSLUITEND valide JSON: {\"summary\": \"...\"}"`. Qwen3 op de lokale desktop luistert blijkbaar niet volledig gehoorzaam, of stopt de tekst niet in de JSON structuur. 

### Fix
**Files:** `services/llm_service.py`, `routers/admin.py`, `admin-panel/src/pages/LLMConfigPage.tsx`, `static/js/app.js`

1. **Platte Tekst Instructie:** Ipv "Retourneer json" vraagt de prompt nu om een "verhaal in natuurlijke tekst". 
   - Ollama genereert nu gewoon succesvol robuuste tekst, waarna `routers/report.py` deze raw string netjes in een `{"ai_summary": ... }` veld plaatst voor de frontend.
2. **LLMConfig Tabel & Router:** In de PostgreSQL database is `schema_v8_llm_config.sql` aangemaakt. Hierdoor wordt de `api_url` en de `model_name` (bijv. qwen3:30b) beheerd ipv in een env bestand.
3. **Beheerscherm (React UI):** Er is een "/llm" pagina gebouwd in Admin.
    - **Modellen Scraper:** Deze pagina doet live een fetch naar de beheerde Ollama `api_url` + `/api/tags` en geeft in een dropdown de actieve modellen op de server weer als selectie tool! (In dit geval dus DeepSeek, Mistral of Qwen3).
    - **Prompt Manager:** Hier kunnen de Systeemprompts (zoals "executive_summary") per functionaliteit worden aangepast.
4. **Frontend Rapportage Polshing:**
    - Er is een window `messageListener` event hook in `app.js` op de hoofdapplicatie geschreven die op commando (`requestMapSnapshot`) de actieve Deck.GL / Mapbox layer pakt met `canvas.toDataURL()` en als kopie de string (`mapSnapshot`) via postmessage verstuurt.
    - Het Admin Panel (in de Report React Component) kan deze afbeelding vangen en toont de statische image als map referentie tijdens het renderen voor print output.
    - Met de nieuwe stylesheet `@media print` functionaliteit wordt de linker Sidebar op het Rapportage Paneel onzichtbaar gemaakt zodat "Exporteren: PDF" nu een schoon A4 landschap overhoudt met de referentiekaart en de datatabellen.

### Verificatie
- ✅ `/api/report/narrative/{gebied_id}` geeft succesvol response als struct object ipv foutmeldingen.
- ✅ React app toont Map Snapshot van de active gebiedsmonitor en kan lokaal afgedrukt worden zonder navigation clutter.

---

## Bug #13: Ontbrekende Mapbox / Kompas Export & CORS Fouten (21-02-2026)

**Gerapporteerd:** 21-02-2026 14:00  
**Status:** ✅ FIXED (21-02-2026)  
**Severity:** 🔴 HIGH (Rapportage export features faalden)

### Probleem
De AI Rapport module werkte in de React frontend, maar de export van de canvas afbeeldingen voor zowel de 3D-kaart als het D3-kompas faalde tijdens het opslaan als PDF. Specifiek:
1. De Mapbox tile engine werkte met een 'Tainted Canvas' restrictie (CORS issues), waardoor de image export transparant of onzichtbaar bleef.
2. De Kompas D3 The SVG export resulteerde in een "Geen kompas SVG gevonden" error omdat in de DOM de target node niet geladen was wanneer het component niet handmatig open was geklikt.

### Oorzaak
Mapbox in `app.js` had the `preserveDrawingBuffer: true` node specificatie nodig. Omdat the React frontend vastliep op async headless renderers, is er expliciete UI-error handling ingebouwd. Het Kompas paneel genereert de SVG pas zodra het paneel opent, hierdoor faalde de request bij een on-read snapshot operatie. Ook was de id-selector fout geïmplementeerd.

### Fix
**Files:** `static/js/app.js`, `admin-panel/src/pages/ReportPage.tsx`, `admin-panel/src/styles/admin.css`

1. **Mapbox Buffer & Error Forwarding:** De Mapbox instance heeft parameter `preserveDrawingBuffer: true` gekregen en de Javascript hook is verzwaard met `postMessage` error routing. Wanneer een CORS timeout of exception optreedt, wordt deze geforward naar React, zodat er een UI validatie element getoond wordt (de applicatie faalt niet meer catastrofaal stil).
2. **Headless Kompas Render:** `app.js` detecteert of the Gebied-data wel is gegradeerd in `kompasViz.loadGebiedData`. Als er acties ontbreken zal hij de D3 rendering lokaal opstarten, afwachten, de SVG forceren, parsen, en na 250ms onzichtbaar doorsturen naar de UI, the zonder dat de user the pop-over the zien krijgt. 
3. **Selector Fix:** De id target is direct gerepareerd var `document.querySelector('#kompas svg')` naar `#kompas-container svg`.
4. **CSS A3 Scaling:** Map canvas optimalisaties zijn meegenomen the `@page { size: A3 landscape }` voor landschap afdrukken en text scaling rules.

### Verificatie
- ✅ Rapport UI genereert lokaal de kaart afbeelding of gooit robuust een geforceerde exception message out-of-bounds op het dashboard in plaats van stiekem the crashen.
- ✅ Kompas the SVG grafieken worden nu headless rendered the serialiseerd via the app.js brug.
- ✅ PDF exports genereren keurig landschapsbestanden en verwijderen the menu objecten.

---

## Improvement #1: Swagger UI Assets Lokaal Hosten (18-02-2026)

**Type:** 🛡️ Security / Stability  
**Status:** ✅ COMPLEET (18-02-2026)  

### Verbetering
De afhankelijkheid van externe CDN's (`unpkg.com`, `cdn.jsdelivr.net`) voor de API documentatie (`/docs`) is volledig verwijderd.

### Reden
1.  **Security:** We hanteren een aangescherpte **Content-Security-Policy (CSP)**.
2.  **Privacy:** Geen tracking door derden van API documentatie bezoekers.
3.  **Betrouwbaarheid:** API Documentatie werkt ook zonder internetverbinding of bij CDN storingen.

### Implementatie
- Assets gedownload naar `static/swagger-ui/`.
- `main.py` aangepast om lokale assets te gebruiken via custom `/docs` endpoint.
- CSP in `main.py` geoptimaliseerd (lokale docs, externe frontend libs).

### Related Bugs
- **Bug #11 (Opgelost):** Swagger UI styling ontbrak door CSP blokkade. Dit is nu structureel opgelost door de bron oorzaak (externe assets) weg te nemen.

---

## Bug #10: Kleurenpalet Aanmaken Error (17-02-2026)

**Gerapporteerd:** 17-02-2026 15:10  
**Status:** ✅ FIXED (17-02-2026)  
**Severity:** 🔴 HIGH (Functionaliteit gebroken)

### Probleem
Het aanmaken van een nieuw kleurpalet in de beheeromgeving (Admin Panel) resulteerde in een `psycopg2.errors.SyntaxError`. De melding was `syntax error at or near ":"`.

### Oorzaak
SQLAlchemy en de onderliggende database driver raakten in de war door de syntax `:colors::jsonb`. De dubbele dubbele punt (`::`) die in PostgreSQL wordt gebruikt voor type casting, werd door SQLAlchemy onjuist geïnterpreteerd icm de parameter placeholder `:colors`.

### Fix
**Files:** `routers/visualisatie.py` en `routers/admin.py`

1. **SQL Syntax:** De ambigue syntax `:colors::jsonb` vervangen door de expliciete standaard SQL functie `CAST(:colors AS jsonb)`.
2. **JSON Serialisatie:** In `routers/admin.py` de JSON conversie verbeterd van `str().replace()` naar `json.dumps()` voor veiligere data handling.

### Verificatie
- ✅ Nieuw kleurpalet aanmaken werkt nu correct zonder syntax error.
- ✅ Data wordt correct opgeslagen als JSONB in de database.

---

## Bug #9: Legenda Synchronisatie bij Kompas Selectie (16-02-2026)

**Gerapporteerd:** 16-02-2026 21:30  
**Status:** ✅ FIXED (16-02-2026)  
**Severity:** 🟡 MEDIUM (Functioneel - UI sync probleem)

### Probleem
De legenda (kleurenbalk + min/max waarden + coverage) updatte niet wanneer een indicator werd geselecteerd via het Kompas (D3 sunburst). Selectie via "Kaart Configuratie" dropdown werkte wel correct.

### Oorzaak
**Twee duplicate `updateLegenda()` functies** in `app.js`:
- **Functie 1** (lijn 895): SVG-based, targeting `#color-scale-container`
- **Functie 2** (lijn 1378): CSS-based, targeting `.legenda-labels` + `gradientBar.style.background`

In JavaScript overschrijft de tweede definitie de eerste. De tweede functie had:
- Andere DOM targeting dan de HTML structuur verwachtte
- Geen null-safe DOM access (crashes bij ontbrekende elementen)
- Incomplete data handling (geen fallback voor indicator naam uit metadata)

### Fix
**File:** `static/js/app.js`

1. **Consolidatie:** Twee functies samengevoegd tot één robuuste versie op lijn 895
2. **Duplicate verwijderd:** Functie op lijn 1378 vervangen door commentaar
3. **Expliciete sync:** `handleIndicatorSelection` roept nu expliciet `updateLegenda(state.currentData)` aan na `loadKaartData()`
4. **Null-safe:** Alle DOM queries beschermd met `if (element)` guards

### Verificatie
- ✅ Selectie via Kaart Configuratie → legenda update correct
- ✅ Selectie via Kompas → legenda opent en toont gradient + min/max + coverage
- ✅ Console logs: `📊 Legenda updated:` en `✅ Legend explicitly synced`

### Openstaand
- ⏳ Legenda kleurbalk matcht nog niet de daadwerkelijke indicator kleuren (toont hardcoded gradient ipv database-driven palette). Volgende sessie.

---

## Bug #8: Score Type Color Inversion Niet Geïmplementeerd (15-02-2026)

**Gerapporteerd:** 15-02-2026 22:36  
**Status:** ✅ FIXED (15-02-2026)  
**Severity:** 🔴 HIGH (Visuele interpretatie fout)

### Probleem
De nieuwe `ColorScaleService` (Sprint 5D) negeerde `score_type` van indicatoren. Dit resulteerde in verkeerde kleurinterpretatie:
- **Voorbeeld:** "Afstand tot kinderdagverblijf" (score_type `-/+`, laag is goed)
- **Verwacht:** Lage afstand (0.3 km) = BLAUW (goed), Hoge afstand (5 km) = ROOD (slecht)
- **Werkelijk:** Normale kleuren (laag=rood, hoog=blauw) → VERKEERD

### Oorzaak
Bij migratie van oude color logic naar nieuwe `ColorScaleService` werd de score_type inversie logica vergeten:
```python
# OLD (in gebiedsmonitor_service.py)
score_type_str = row["score_type"] or '+/+'
use_inverse = score_type_str in ['+/-', '-/+']  # ✅ WAS ER
color = self.scoring.get_color_for_value(..., inverse=use_inverse)

# NEW (in color_scale_service.py)
color_ramp = self.generate_color_ramp(colors, num_classes)  
# ❌ GEEN INVERSIE!
```

### Score Type Betekenis
- `+/+`: Hoog = Goed → **normal** (blauw=laag, rood=hoog)
- `+/-`: Hoog = Slecht → **REVERSE**
- `-/+`: Laag = Goed → **REVERSE** (blauw=hoog, rood=laag)
- `-/-`: Laag = Slecht → **normal**

### Fix
**File:** `services/color_scale_service.py:216-227`

```python
# Extract score_type from config
score_type = config.get("score_type", "+/+")

# Generate base color ramp
color_ramp = self.generate_color_ramp(colors, num_classes)

# 🔄 SCORE TYPE INVERSION LOGIC
should_reverse = score_type in ['+/-', '-/+']
if should_reverse:
    color_ramp = list(reversed(color_ramp))
```

### Verificatie
```bash
# Test kinderdagverblijf (score_type -/+)
curl "localhost:8000/api/kaart/v1/{gebiedstype}?indicator_uuid={kinderdagverblijf_uuid}"
# Verwacht: Lage afstand = blauw, Hoge afstand = rood ✅
```

### Impact
- **Voor Fix:** Alle afstandsindicatoren (`-/+`) en negatieve indicatoren (`+/-`) hadden verkeerde kleuren
- **Na Fix:** Kleuren worden correct omgekeerd op basis van score_type
- **Betreft:** ~20 indicatoren met non-default score types

### Related
- Sprint 5D: Visualisatie Standaard
- File: `services/color_scale_service.py`
- Commit: Score type inversion implemented

---

## Bug #7: Dashboard Toont 0 Data Coverage (13-02-2026) - FIXED ✅
[Previous bug entries remain...]

---

## Bug #31: FastAPI Route Conflict `/ontologie/status` Caught by `/{uuid}` (16-03-2026) - FIXED ✅

**Sprint:** Sprint 9 Track B  
**Prioriteit:** Medium  
**Status:** ✅ Opgelost via server restart + route ordering

**Symptomen:**
- `GET /api/admin/ontologie/status` gaf `404 Not Found` in de browser logs
- Database en code waren correct; data stond netjes in de DB

**Oorzaak:**
FastAPI matched routes *top-down*. De route `GET /indicatoren/{uuid}` stond geregistreerd vóór `GET /ontologie/status`, waardoor FastAPI de string `"ontologie"` als een UUID-parameter interpreteerde en de verkeerde route aanriep.

**Oplossing:**
Route `GET /ontologie/status` boven `GET /indicatoren/{uuid}` in `routers/admin.py` plaatsen. De huidige versie heeft dit correct staan. Na een volledige server-restart werkt de endpoint correct.

**Les:** Bij FastAPI altijd specifieke routes (met vaste segmenten) *voor* parametrische routes (`{uuid}`) registreren.

---

## Bug #32: Admin Panel Toont Geen Ontologie-velden Na Code Update (16-03-2026) - FIXED ✅

**Sprint:** Sprint 9 Track B  
**Prioriteit:** Low  
**Status:** ✅ Opgelost via server restart

**Symptomen:**
- Admin panel toonde indicatoren zonder `ontologie_status`, `beschrijving_ai`, etc.
- DB had data, curl naar nieuwe endpoint gaf ook de oude response

**Oorzaak:**
Uvicorn's `--reload` detecteerde de bestandswijziging in `routers/admin.py` niet snel genoeg (WSL2 filesystem-notificaties kunnen vertragen bij `/mnt/f/` Windows drives).

**Oplossing:**
Uvicorn stoppen en handmatig herstarten. Na herstart laadt de server de nieuwe routedefinities correct.

**Preventie:** Bij grote backend wijzigingen altijd handmatig herstarten ipv vertrouwen op `--reload` wanneer bestanden op een gemount Windows-rijde staan.

---

## Bug #33: `u.email` Kolom Bestaat Niet in `users` Tabel (16-03-2026) - FIXED ✅

**Sprint:** Sprint 9 Track B  
**Prioriteit:** 🔴 HIGH (blokkeerde admin panel indicator-detail view)  
**Status:** ✅ Opgelost

**Symptomen:**
- Klikken op een indicator in het admin panel toonde geen details (rechter paneel bleef leeg)
- Server gaf `500 Internal Server Error` op `GET /api/admin/indicatoren/{uuid}`
- Foutmelding: `sqlalchemy.exc.ProgrammingError: column u.email does not exist`

**Oorzaak:**
In de SQL-query van `get_indicator()` werd `u.email as gevalideerd_door_email` gebruikt, maar de `users` tabel heeft geen `email` kolom. De werkelijke structuur is: `id (UUID)`, `username`, `hashed_password`, `is_active`, `is_admin`, `created_at`.

**Oplossing:**
Drie bestanden aangepast:
1. **`routers/admin.py`** — `u.email` → `u.username`, responseveld hernoemd naar `gevalideerd_door_naam`
2. **`admin-panel/src/types/index.ts`** — Interface property: `gevalideerd_door_email` → `gevalideerd_door_naam`
3. **`admin-panel/src/pages/IndicatorsPage.tsx`** — Verwijzing bijgewerkt

Admin panel opnieuw gebuild en gedeployed naar `static/admin-panel/`.

**Preventie:** Bij toekomstige JOINs op de `users` tabel altijd `username` gebruiken als identificerende kolom (geen `email` aanwezig).

---

## Bug #34: Intelligent Chat Actions - Pydantic Field Stripping (25-03-2026) - FIXED ✅

**Sprint:** Sprint 11 Track A  
**Prioriteit:** 🔴 HIGH (actie-knoppen in de chat werkten niet)  
**Status:** ✅ Opgelost

**Symptomen:**
- Chat assistent toonde wel de actie-knoppen (bijv. "📍 Leeuwarden"), maar klikken op de knop deed niets.
- In de browser console waren de `data-` attributen (zoals `data-gemeente-code`) leeg: `""`.

**Oorzaak:**
Het Pydantic model `ActieKnop` in `routers/chat.py` bevatte niet de nieuwe velden `gemeente_code`, `gebiedstype_id` en `config_id`. Hierdoor stripte FastAPI deze velden stilzwijgend uit de JSON-response voordat deze de frontend bereikte.

**Oplossing:**
1. **`routers/chat.py`**: Model `ActieKnop` uitgebreid met de ontbrekende velden.
2. **`routers/chat.py`**: De mapping van de LLM-response naar het model bijgewerkt om deze velden door te geven.

**Preventie:** Bij het uitbreiden van API-responses altijd controleren of de Pydantic schema's meegroeien.

---

## Bug #35: Intelligent Chat Actions - Manual Event Triggering (25-03-2026) - FIXED ✅

**Sprint:** Sprint 11 Track A  
**Prioriteit:** Medium  
**Status:** ✅ Opgelost

**Symptomen:**
- Na fix van Bug #34 werden de velden wel gevuld, maar de kaart herlaadde niet. De dropdowns in de zijbalk sprongen niet naar de juiste waarde.
- Klikken op de knop gaf wel visuele feedback (vinkje), maar geen resultaat in de kaart.

**Oorzaak:**
Het programmatisch aanpassen van de `.value` van een `<select>` of `<input>` element (zoals `#gemeente-input` of `#gebiedstype-select`) vuurt in de browser geen 'change' event af. De bestaande listeners in `app.js` werden dus niet getriggerd.

**Oplossing:**
1. **`static/js/app.js`**: In de `EventBus` listeners expliciet `dispatchEvent(new Event('change'))` aangeroepen na het updaten van de values.
2. **`static/js/app.js`**: De gemeente-selector listener robuuster gemaakt door direct de `state` en `localStorage` te updaten bij een `GEMEENTE_SELECTED` event.

**Les:** Programmatische UI-updates vereisen handmatige event-dispatching als er listeners op die elementen vertrouwen.

---

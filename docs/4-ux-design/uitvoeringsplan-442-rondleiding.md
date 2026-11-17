# Uitvoeringsplan #442 — interactieve rondleiding en herhaalbare instaphulp

**Opdrachtgever:** Taeke · **Issue:** [#442](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/442) (mijlpaal `0.7.0 — UX en toegankelijkheid`)
**Status:** Vastgesteld op 2026-11-17 (zie §1) en uitgevoerd op branch `feature/442-rondleiding`.

> Lees eerst [AGENTS.md](../../AGENTS.md). Regels die hier gelden: issue en PR vóór wijzigingen, `CHANGELOG.md` onder `[Unreleased]`, niets organisatie-specifiek hardcoden, geen frameworks in de viewer, wijzig `app.js` gericht, ruim je eigen orphans op.

---

## 1. Vastgestelde besluiten

| # | Besluit | Gevolg |
|---|---|---|
| 1 | **Per stap uitleg in drie regels:** *Wat zie je*, *Wat betekent het*, *Probeer het*. De gebruiker wordt inhoudelijk meegenomen in plaats van alleen "waar klik ik". | Tourteksten in §5. |
| 2 | **Welkomstmodal: twee ingangen**, *Mijn buurt opzoeken* en *Start rondleiding (1 min)*. "Gebiedsanalyse starten" vervalt omdat de startkaart van #443 dat al direct toont. *Handleiding* en *Overslaan* blijven behouden. | §4A. |
| 3 | **Voorbeeldbuurt:** wanneer er bij start van de rondleiding nog geen gebied geselecteerd is, selecteert de tour deterministisch een voorbeeldbuurt met data zodat stap 1, 3 en 4 live te zien zijn. Na afloop wordt die voorbeeldselectie weer opgeruimd. | §5, voorbereiding en herstel. |
| 4 | **Hulpknop (`?`):** vaste knop `#tour-start-btn` (`aria-label="Rondleiding & Uitleg"`) onderaan `.tab-bar` conform het acceptatiecriterium van #442, plus een knop `#info-tour-btn` (*Start interactieve rondleiding*) in `#panel-info` en `#chat-start-tour-btn` (*🧭 Geef me een rondleiding*) onder het welkomstbericht van de D-Omni Assistent. | §4C & §4D. |
| 5 | **Eerlijke rapporttekst (`#panel-rapport`):** de misleidende tekst *"Directe AI analyse van het geselecteerde gebied."* en knoptekst *"Genereer AI Rapport"* (terwijl de Gebiedsfactsheet 100% deterministisch is zonder AI) worden direct gecorrigeerd naar *"Genereer een Gebiedsfactsheet of uitgebreid rapport voor het geselecteerde gebied."* en *"Open Rapportkeuze"*. | §4E. |

---

## 2. Uitgangssituatie (geverifieerd in de code)

- Welkomstmodal: [templates/index.html](../../templates/index.html), logica `initOnboarding`, `dismissWelcomeModal` in [static/js/app.js](../../static/js/app.js). Flag `omnitwin_welcomed` wordt gezet bij sluiting. Het dialoogvenster heet "Welkom bij D-OmniTwin" en heeft `#welcome-skip-btn`; de e2e-test `test_integratie_e2e.py` gebruikt beide.
- `initOnboarding()` draait **vóór** `loadGemeenten()` en `initStartKaart()` ([app.js](../../static/js/app.js)). De modal staat dus op het scherm terwijl de startkaart op de achtergrond laadt.
- Startkaart (#443) opent het Legenda-paneel (`togglePanel('legenda')`) en het rechter dock op Kompas (`openRechterDock('kompas', false, false)`).
- Contextuele tips (Track A2): `initContextualTooltips()` toont eenmalige tips op `INDICATOR_SELECTED`, `GEBIED_SELECTED`, `KOMPAS_OPENED`, `AI_RESPONSE_RECEIVED`.
- Globale Escape-handler in `app.js` wist de actieve indicator alleen als `!e.defaultPrevented`.
- `CHAT_GEBIEDEN_TONEN` selecteert gebieden, wisselt zo nodig de gemeente en zoomt (`zoom: true`).
- Buurt zoeken op postcode/adres of locatie via `POST /api/locatie/buurt` ([routers/locatie.py](../../src/omnitwin/routers/locatie.py), ratelimit 30 per minuut, PDOK Locatieserver).
- Dialoog-helper: `A11y.openDialog(el, { modal, labelledBy, returnFocus, onEscape })` en `A11y.prefersReducedMotion` in [static/js/core/a11y.js](../../static/js/core/a11y.js).
- Dock: onder 900 px wordt het een bottom sheet van `48vh` ([static/css/styles.css](../../static/css/styles.css)).

---

## 3. Samenvatting ontwerpkeuzes

| Onderdeel | Keuze |
|---|---|
| Lichtgewicht Vanilla-JS spotlight, 4 stappen, geen library | **Ja** (`static/js/core/rondleiding.js`). |
| Kaartje met Vorige/Volgende/Overslaan, toetsen ←, →, Escape | **Ja**, met capture-keydown `preventDefault()` zodat Escape nooit de actieve indicator wist (§6). |
| Stap 2 anker | Anker op het al open `#panel-legenda` én op de knop `[data-panel="controls"]` (zonder het paneel geforceerd om te klappen). |
| Stap 4 anker | Omhullende rechthoek van `[data-panel="rapport"]` en `#chat-toggle-btn`, mét actieve voorbeeldbuurt zodat Rapport direct bruikbaar is. |
| Welkomstmodal met 2 primaire ingangen | *Mijn buurt opzoeken* en *Start rondleiding (1 min)*; daarnaast blijven *Handleiding* en *Overslaan* staan. |
| Mijn buurt zoeken | Via gedeelde module `static/js/core/buurtkiezer.js` op postcode/adres en browserlocatie (`POST /api/locatie/buurt`), hergebruikt in zowel de Assistent als de welkomstmodal. |
| Dynamisch indicatoraantal | Geen hardcoded `"235+ indicatoren"` of regioprefix in de onboarding/rondleiding; gebruikt het dynamische aantal uit `loadDataTellers()`. |
| Inhoudelijke begeleiding per stap | Drie vaste blokken per stap: *Wat zie je*, *Wat betekent het*, *Probeer het*. |

---

## 4. Onderdelen

### A. Welkomstmodal & gedeelde Buurtkiezer (`static/js/core/buurtkiezer.js`, `templates/index.html`, `static/js/chat.js`, `static/js/app.js`)
- Behoud: dialoognaam (`#welcome-title`), `#welcome-skip-btn`, de drie uitlegstappen en de link *Handleiding* (`/static/help.html`).
- Vervang de knoppen *Kaart verkennen* en *Kompas begrijpen* door:
  1. **Mijn buurt opzoeken (`#welcome-btn-buurt`)** → klapt in de modal het gedeelde buurtkiezer-formulier open (postcode of adres + *"📍 Gebruik mijn locatie"* + PDOK-privacyverklaring).
  2. **Start rondleiding (1 min) (`#welcome-btn-tour`)** → sluit de modal, wacht zo nodig op `window.startKaartKlaar` en start de rondleiding (`window.startRondleiding()`).
- **Gedeelde module (`static/js/core/buurtkiezer.js`):** bevat `window.BuurtKiezer.maak({ onGevonden, ... })` en wordt gebruikt door zowel `chat.js` (`_buurtKiezer`) als de welkomstmodal.
- Na een gevonden buurt in de welkomstmodal: sluit de modal, wacht zo nodig op `window.startKaartKlaar`, en emit `CHAT_GEBIEDEN_TONEN` met `{ ids: [data.gebied_id], zoom: true }`.

### B. De Spotlight Tour (`static/js/core/rondleiding.js` + CSS in `static/css/styles.css`)
- Overlay (`#spotlight-tour-overlay`) met cutout (`#spotlight-cutout`, `box-shadow`-spotlight) en toegankelijk dialoogkaartje (`#spotlight-popover`), herberekend bij `resize` en na `transitionend` van het dock/paneel.
- Stappen als data (`window.RONDLEIDING_STAPPEN` met `id`, `ankers`, `titel`, `wat`, `betekent`, `probeer`, `voorbereiding`). Ankers uitsluitend in de vormen `#id` of `[data-panel="x"]` (getoetst door unit-test in `tests/test_rondleiding.py`).
- Publieke API: `window.startRondleiding(triggerEl)` en `window.stopRondleiding()`.
- De tour start **nooit** automatisch.

### C. Hulpknop (`?`) in `.tab-bar` en `#panel-info`
- Knop `#tour-start-btn` in `.tab-bar` met `title="Rondleiding & Uitleg"` en `aria-label="Rondleiding & Uitleg"` die `window.startRondleiding(this)` aanroept.
- Knop `#info-tour-btn` (*Start interactieve rondleiding*) in `#panel-info` boven *Volledige Handleiding*.

### D. Actieknop in de D-Omni Assistent
- Knop `#chat-start-tour-btn` (*🧭 Geef me een rondleiding*) onder het welkomstbericht in `#chat-messages` die `window.startRondleiding(this)` aanroept.

### E. Eerlijke tekst in `#panel-rapport`
- Tekst in `#panel-rapport` aangepast van *"Directe AI analyse van het geselecteerde gebied."* naar *"Genereer een Gebiedsfactsheet of uitgebreid rapport voor het geselecteerde gebied."* en knoptekst `#open-rapport-btn` naar *"Open Rapportkeuze"*.

---

## 5. Tourstappen en teksten

**Voorbereiding bij start (`startRondleiding`)**
1. Wacht indien nodig op `window.startKaartKlaar`.
2. Bewaar of er een voorbeeldbuurt moest worden geselecteerd en welk element de tour startte (`triggerEl`).
3. Is er nog geen gebied geselecteerd (`state.selectedGebiedIds.size === 0`): kies deterministisch de eerste buurt op alfabetische naam uit `state.currentData.features` die een geldige waarde heeft (`value !== null && value !== undefined`), en selecteer die via `CHAT_GEBIEDEN_TONEN` (`zoom: true`).
4. Zet `window.tourActief = true` en verberg eventuele actieve contextuele tooltips.

**Herstel bij einde of stoppen (`stopRondleiding`)**
- Als de tour zelf een voorbeeldbuurt had geselecteerd, wis die selectie weer (`clearGebiedSelection()`, `updateSelectionUI()`, `displayOnMap(state.currentData)`).
- Zet `window.tourActief = false` en geef de focus terug aan de startknop.

| Stap | Anker(s) | Wat zie je | Wat betekent het | Probeer het |
|---|---|---|---|---|
| 1. De kaart & gebiedsselectie | `#hoofdinhoud` | Elke vlek op de kaart is een gebied (zoals een buurt); de kleur volgt de gekozen indicator en grijs betekent geen data. | De kleur laat zien hoe een buurt scoort ten opzichte van andere gebieden. *(Bij voorbeeldbuurt: "Voorbeeld: `<buurtnaam>` is voor je geselecteerd.")* | Klik op een buurt op de kaart. Gebruik `Shift+klik` om meerdere buurten te vergelijken. |
| 2. Indicator & legenda | `#panel-legenda`, `[data-panel="controls"]` | De legenda toont de kleurenschaal en gebiedsdekking van de actieve indicator. | Kies zelf: werkelijke waarde, percentielklasse 1–8 of label A–E. Een hoge waarde is niet altijd gunstig — kijk altijd naar de legenda. | Wissel de weergave in de legenda, of kies een andere gemeente of indicator via *Kaartconfiguratie* (tweede icoon links). |
| 3. Het D-Omni Kompas | `#rechter-dock` | Het Kompas bundelt alle thema's in ringen. Eronder zie je direct de tijdreeks, definitie, bron, vergelijking met het gemeentegemiddelde en top-uitschieters. | Gekleurde thema's tonen hoe een buurt presteert; het kwadrant *Samenstelling* is puur beschrijvend (neutraal blauw, zonder goed of slecht). | Klik op een segment in het wiel om in te zoomen op een thema en bekijk het detail van de geselecteerde buurt. |
| 4. Rapport & D-Omni Assistent | `[data-panel="rapport"]`, `#chat-toggle-btn` | De knoppen voor *Rapport* (met bovenaan de *Gebiedsfactsheet*) en de *D-Omni Assistent*. | De Gebiedsfactsheet vat een buurt feitelijk samen per thema (zonder AI). De Assistent haalt antwoorden uit de beheerde data; schrijft een taalmodel de samenvatting, dan staat er een AI-label bij — controleer altijd de bron. | Open *Rapport* voor de geselecteerde buurt, of stel een vraag in gewone taal aan de Assistent. |

---

## 6. Technische eisen & toegankelijkheid

1. **Escape zonder indicator-reset:** de tour vangt `Escape` af in de capture-fase op `document` met `e.preventDefault()` en `e.stopPropagation()`, zodat de globale Escape-handler in `app.js` nooit `resetKaartIndicator()` aanroept.
2. **Contextuele tips onderdrukken:** `showContextualTooltip()` in `app.js` stopt direct zolang `window.tourActief === true`.
3. **Toegankelijkheid (ADR 0011, WCAG 2.1 AA):**
   - Kaartje als `role="dialog"` via `A11y.openDialog` met `modal: false`.
   - Voortgang `"Stap X van 4"` als tekst en `aria-live="polite"` op de inhoud.
   - Pijltoetsen `ArrowRight` (volgende) en `ArrowLeft` (vorige) werken wanneer de focus niet in een tekstveld staat.
   - Respecteert `A11y.prefersReducedMotion()` (geen cutout-transitie).
4. **Mobiel (`< 900px`):** plaatst het tourkaartje automatisch in de vrije helft van het scherm (bovenaan wanneer het dock als bottom sheet van `48vh` onderaan staat).
5. **Opruimen:** verweesde `startOnboarding()`, `ONBOARDING_ACTION` en ongebruikte `.welcome-btn-*` varianten verwijderd.

---

## 7. Tests

- **Unit (`tests/test_rondleiding.py`, marker `unit`):**
  - Elke stapanker (`#id` of `[data-panel="x"]`) uit `static/js/core/rondleiding.js` bestaat in `templates/index.html`.
  - `buurtkiezer.js` en `rondleiding.js` zijn vóór `app.js` ingeladen in `templates/index.html`.
  - `#panel-rapport` bevat geen misleidende `"Directe AI analyse"` of `"Genereer AI Rapport"` meer.
- **E2E (`tests/e2e/test_rondleiding_e2e.py`, marker `e2e`):**
  1. De tour start niet vanzelf; start via `#tour-start-btn` (`?`) en via `#chat-start-tour-btn`, doorloopt de 4 stappen met drie-regelige uitleg, selecteert een voorbeeldbuurt, sluit met `Escape` zonder dat `state.currentIndicator` verloren gaat, ruimt de voorbeeldselectie op en zet de focus terug.
  2. Welkomstmodal: *Mijn buurt opzoeken* met gemockte `POST /api/locatie/buurt` selecteert de buurt; *Overslaan* werkt zoals voorheen.

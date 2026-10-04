# Thema's: eigen huisstijl via NL Design System-tokens

> **Verouderd.** De actuele beschrijving, met de rustigere SWF-kleuren, het thema `legacy` en de WCAG-status per thema ([#284](https://github.com/TLaan/D-OmniTwin/issues/284)), staat in [`docs/9-beheer/thema-s.md`](../9-beheer/thema-s.md). De kleurwaarden hieronder zijn die van vóór #284.

Elke organisatie draait een eigen D-OmniTwin-instantie ([ADR 0007](../2-architectuur/adr/0007-geen-multi-tenancy-mesh-van-instanties.md)). Kleuren, lettertypen, ruimte en hoeken komen uit een **thema**: één CSS-bestand met [NL Design System](https://nldesignsystem.nl)-tokens. Welk thema een instantie laadt, is inrichting (data), geen code. Issue: [#89](https://github.com/TLaan/D-OmniTwin/issues/89).

## Hoe het werkt

```
static/css/themes/<thema>.css      tokens: --basis-*  en  --d-omnitwin-*
        │
        ▼
static/css/styles.css  :root       --primary-color: var(--basis-color-accent-1-color-default, #1e3a8a);
        │                          (fallback = standaardwaarde; zonder thema verandert er niets)
        ▼
componenten (knoppen, panelen, tabs, kopbalk, focusrand)
```

- **Basistokens** volgen de naamgeving van NL Design System ([`nl-design-system/themes`](https://github.com/nl-design-system/themes), pakket `basis-design-tokens`): `basis.color.accent-1.bg-default` wordt `--basis-color-accent-1-bg-default`. Geen build-stap: het thema is gewone CSS.
- **Componenttokens** van D-OmniTwin zelf heten `--d-omnitwin-*` en verwijzen waar het kan naar basistokens. Nu alleen de kopbalk (een verloop, dat NLDS niet kent).
- Het thema zet tokens in drie blokken: licht (`:root`), donker (`[data-theme="dark"]`, de knop in de kopbalk) en donker via de systeeminstelling (`@media (prefers-color-scheme: dark)`, alleen zolang `app.js` nog geen `data-theme` heeft gezet).
- `templates/index.html` laadt `static/css/themes/{thema}.css`; `thema` staat in de organisatiegegevens van de instantie. Standaard `d-omnitwin`. Een ongeldige naam of een naam zonder bestand valt terug op het standaardthema (`omnitwin.thema.kies_thema`).

## Beschikbare thema's

| Thema | Organisatie | Lettertypen | Bestand |
|---|---|---|---|
| `d-omnitwin` | standaard, de huidige uitstraling | Inter | [`static/css/themes/d-omnitwin.css`](../../static/css/themes/d-omnitwin.css) |
| `swf` | Gemeente Súdwest-Fryslân (voorstel, nog af te stemmen met SWF) | Montserrat (koppen), Source Sans 3 (tekst, open vervanger van Calluna Sans) | [`static/css/themes/swf.css`](../../static/css/themes/swf.css) |

De SWF-kleuren komen uit de live CSS van sudwestfryslan.nl; de afwegingen staan in [#89](https://github.com/TLaan/D-OmniTwin/issues/89). Er is (nog) geen officieel NLDS-thema van SWF.

## Tokenmapping

Welke app-variabele welk token leest. De fallback in `styles.css` is gelijk aan `d-omnitwin.css` (de test bewaakt dat).

| App-variabele (`styles.css`) | Token | Standaard licht / donker | SWF licht / donker |
|---|---|---|---|
| `--bg-primary` (pagina) | `--basis-color-default-bg-document` | `#f1f5f9` / `#0f172a` | `#fafafa` / `#141414` |
| `--bg-secondary` (vlakken) | `--basis-color-default-bg-default` | `#ffffff` / `#1e293b` | `#ffffff` / `#1e1e1e` |
| `--text-primary` | `--basis-color-default-color-document` | `#1e293b` / `#f1f5f9` | `#1e1e1e` / `#ffffff` |
| `--text-secondary` | `--basis-color-default-color-subtle` | `#64748b` / `#94a3b8` | `#5e5e5e` / `#b3b3b3` |
| `--border-color` | `--basis-color-default-border-subtle` | `#e2e8f0` / `#334155` | `#eeeeee` / `#3a3a3a` |
| `--primary-color` (links, actieve tab) | `--basis-color-accent-1-color-default` | `#1e3a8a` / `#3b82f6` | `#bf0042` / `#ff5c8a` |
| `--primary-dark` | `--basis-color-accent-1-color-hover` | `#1e40af` / `#2563eb` | `#8c0030` / `#ff8fae` |
| `--primary-fill` (vlak met witte tekst) | `--basis-color-accent-1-bg-default` | `#1e3a8a` / `#2563eb` | `#bf0042` / `#bf0042` |
| `--action-color` | `--basis-color-action-1-color-default` | `#1e3a8a` / `#3b82f6` | `#bf0042` / `#ff5c8a` |
| `--action-dark` | `--basis-color-action-1-color-hover` | `#1e40af` / `#2563eb` | `#8c0030` / `#ff8fae` |
| `--action-fill` (knop) | `--basis-color-action-1-bg-default` | `#1e3a8a` / `#2563eb` | `#bf0042` / `#bf0042` |
| `--action-fill-dark` (knop hover) | `--basis-color-action-1-bg-hover` | `#1e40af` / `#1d4ed8` | `#8c0030` / `#8c0030` |
| `--accent-color`, `--brand-accent` (selectie, highlight) | `--basis-color-accent-2-bg-default` | `#c59d00` / `#eab308` | `#009fd2` / `#4cc3ea` |
| `--accent-text` | `--basis-color-accent-2-color-default` | `#856a00` / `#eab308` | `#00759c` / `#4cc3ea` |
| `--brand-nature` | `--basis-color-accent-3-color-default` | `#15803d` / `#22c55e` | `#4d6b00` / `#91c60f` |
| `--color-danger` | `--basis-color-negative-color-default` | `#b91c1c` / `#ef4444` | `#b91c1c` / `#f87171` |
| `--color-success` | `--basis-color-positive-color-default` | `#15803d` / `#22c55e` | `#15803d` / `#4ade80` |
| `--color-warning` | `--basis-color-warning-color-default` | `#c2410c` / `#f97316` | `#c2410c` / `#fb923c` |
| `--focus-ring` | `--basis-focus-outline-color` | `#1e3a8a` / `#93c5fd` | `#1e1e1e` / `#ffffff` |
| `--header-bg-start` | `--d-omnitwin-header-background-color-start` | `#1e3a8a` / `#3b82f6` | `#bf0042` / `#8c0030` |
| `--header-bg-end` | `--d-omnitwin-header-background-color-end` | `#15803d` / `#22c55e` | `#8c0030` / `#5c0020` |
| `--header-text` | `--d-omnitwin-header-color` | `#ffffff` / `#f1f5f9` | `#ffffff` / `#ffffff` |
| `--border-radius` / `--border-radius-sm` | `--basis-border-radius-lg` / `-md` | `12px` / `8px` | `8px` / `4px` |
| `--spacing-xs` … `--spacing-xl` | `--basis-space-block-xs` … `-xl` | `0.25rem` … `2rem` | gelijk |
| `body` lettertype | `--basis-text-font-family-default` | Inter | Source Sans 3 |
| `h1`–`h6` lettertype | `--basis-heading-font-family` | Inter | Montserrat |

Daarnaast zet `swf.css` tokens die de app nog niet leest maar die bij het palet horen: `--basis-color-accent-3-bg-default` (groen vlak, alleen met donkere tekst) en `--basis-color-highlight-*` (roze). NL Design System kent `accent-1` tot en met `accent-3`; het vierde SWF-accent (roze) is daarom `highlight`.

Niet via het thema (nog): de half-doorzichtige panelen (`--panel-bg`, `--panel-border`, `--shadow-color`), `--secondary-color`, en een handvol vaste kleuren en tinten in `styles.css` (bv. `rgba(59, 130, 246, 0.12)` als lichtblauwe hover). Die volgen bij de componentenstap van #89.

## Wat niet in een thema hoort: datakleuren

De kleuren van de **data** (Z-score-schaal, choropleten op de kaart, Kompas-sunburst) blijven de kleurenblindveilige divergerende paletten uit de tabel `color_schemas` (`services/color_scale_service.py`, beheer via de admin-API, publiek via `/api/visualisatie/paletten`). NL Design System heeft geen choropletpaletten, en een huisstijlkleur is geen goede datakleur: rood en groen naast elkaar zijn voor kleurenblinden niet te onderscheiden, en een merkkleur draagt betekenis ("goed"/"slecht") die de data niet heeft. Een thema bepaalt alleen de UI eromheen. De test `tests/test_thema.py` laat een thema falen dat iets anders zet dan `--basis-*` en `--d-omnitwin-*`.

## Een eigen thema maken

1. **Kopieer** `static/css/themes/swf.css` (met eigen lettertypen) of `d-omnitwin.css` (zonder) naar `static/css/themes/<naam>.css`. De naam bestaat alleen uit kleine letters, cijfers en koppeltekens (`[a-z0-9-]`), bijvoorbeeld `leeuwarden` of `tytsjerksteradiel`.
2. **Pas de tokens aan** in alle drie de blokken (licht, donker, donker via systeeminstelling; de laatste twee zijn gelijk). Kleuren als `#rrggbb`. Houd de opbouw aan: alleen `--basis-*` en `--d-omnitwin-*`, geen selectors voor componenten.
   - Een huisstijlkleur die als tekst of onder witte tekst te weinig contrast heeft, krijgt een donkere (licht thema) of lichte (donker thema) variant voor `color-default`; de originele kleur blijft voor `bg-default` als vlak of rand.
   - Eigen lettertype: alleen open licenties (OFL e.d.), zelf gehost in `static/vendor/<pakket>@<versie>/` met het licentiebestand, en een regel in `NOTICE.md` en `static/vendor/README.md`. Laad het met `@import url("../../vendor/...")` bovenaan het thema. Geen Google Fonts, Typekit of andere CDN ([#117](https://github.com/TLaan/D-OmniTwin/issues/117)); de CSP staat dat ook niet toe.
3. **Toets het contrast** (WCAG 2.1 AA: 4,5:1 voor tekst, 3:1 voor UI-onderdelen en focus):

   ```bash
   python -m pytest tests/test_thema.py      # faalt bij een te laag contrast
   python tests/test_thema.py --rapport      # tabel met alle contrasten per thema en modus
   ```

4. **Zet het thema aan**: veld `thema` in de organisatiegegevens van de instantie (bv. `"thema": "leeuwarden"`). Ververs de pagina; licht en donker wisselen met de knop in de kopbalk.
5. **Bekijk** de hoofdpagina, het Kompas en een rapport in licht en donker.
6. **Teruggeven**: een thema dat de organisatie zelf goedkeurt, kan als pakket naar [`nl-design-system/themes`](https://github.com/nl-design-system/themes) (map `proprietary/<organisatie>-design-tokens`, tokens in JSON volgens de basis-tokens). De tokennamen zijn al dezelfde; alleen de vorm (JSON in plaats van CSS) verschilt. Dat past bij de governance via OpenWebconcept ([#183](https://github.com/TLaan/D-OmniTwin/issues/183)).

## Bekende contrasttekorten in het standaardthema

`d-omnitwin.css` neemt de bestaande kleuren één op één over, zodat er visueel niets verandert. Zeven paren halen WCAG AA daarin niet; ze staan als `BEKENDE_TEKORTEN` in `tests/test_thema.py` en horen bij de toegankelijkheidsronde ([#67](https://github.com/TLaan/D-OmniTwin/issues/67)):

| Modus | Paar | Contrast |
|---|---|---|
| licht | secundaire tekst `#64748b` op pagina `#f1f5f9` | 4,34:1 |
| licht | goud `#c59d00` als selectie op wit | 2,56:1 (eis 3:1) |
| donker | link `#3b82f6` op paneel `#1e293b` (ook actietekst) | 3,98:1 |
| donker | link hover `#2563eb` op paneel `#1e293b` | 2,83:1 |
| donker | fouttekst `#ef4444` op paneel `#1e293b` | 3,89:1 |
| donker | kopbalktekst `#f1f5f9` op `#3b82f6` / `#22c55e` | 3,36:1 / 2,08:1 |

Het SWF-thema heeft geen tekorten.

## Vervolg (#89)

- Componenten: knoppen, formuliervelden, dialogen en meldingen naar NLDS-componenten (CSS van de Utrecht-/Candidate-componenten, zelf gehost), die dezelfde basistokens lezen.
- De admin-UI (React) op dezelfde tokens.
- Logo per organisatie samen met het thema ([#83](https://github.com/TLaan/D-OmniTwin/issues/83)).
- axe/pa11y in de CI per thema ([#62](https://github.com/TLaan/D-OmniTwin/issues/62)).

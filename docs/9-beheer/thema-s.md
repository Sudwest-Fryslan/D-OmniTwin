# Thema's: eigen huisstijl via NL Design System-tokens

Elke organisatie draait een eigen D-OmniTwin-instantie ([ADR 0007](../2-architectuur/adr/0007-geen-multi-tenancy-mesh-van-instanties.md)). Kleuren, lettertypen, ruimte en hoeken komen uit een **thema**: één CSS-bestand met [NL Design System](https://nldesignsystem.nl)-tokens. Welk thema een instantie laadt, is inrichting (data in de tabel `organisatie`), geen code. Issue: [#89](https://github.com/TLaan/D-OmniTwin/issues/89).

## Hoe het werkt

```
static/css/themes/<thema>.css      tokens: --basis-*  en  --d-omnitwin-*
        │
        ▼
static/css/styles.css  :root       --primary-color: var(--basis-color-accent-1-color-default, #1e3a8a);
        │                          (terugval = standaardwaarde; zonder thema verandert er niets)
        ▼
componenten (kopbalk, tabs, knoppen, panelen, chat, Kompas, tooltips, dialogen, focusrand)
```

- **Basistokens** volgen de naamgeving van NL Design System ([`nl-design-system/themes`](https://github.com/nl-design-system/themes), pakket `basis-design-tokens`): `basis.color.accent-1.bg-default` wordt `--basis-color-accent-1-bg-default`. Geen build-stap: het thema is gewone CSS.
- **Componenttokens** van D-OmniTwin zelf heten `--d-omnitwin-*`: plekken waar een organisatie bewust iets anders wil dan de basistokens geven (zie de lijst hieronder).
- Het thema zet tokens in drie blokken: licht (`:root`), donker (`[data-theme="dark"]`, de knop in de kopbalk) en donker via de systeeminstelling (`@media (prefers-color-scheme: dark)`, alleen zolang `app.js` nog geen `data-theme` heeft gezet). De laatste twee zijn gelijk.
- `templates/index.html` laadt `static/css/themes/{thema}.css`; `thema` komt uit de tabel `organisatie` (`GET /api/organisatie`). Standaard `d-omnitwin`. Een ongeldige naam of een naam zonder bestand valt terug op het standaardthema (`omnitwin.thema.kies_thema`). De handleiding (`/static/help.html`, statisch) haalt hetzelfde themabestand op via `/api/organisatie`.
- Tinten (hover, subtiele vlakken, randen) rekent `styles.css` uit met `color-mix()` op de themakleuren, zoals `--tint` (tekstkleur op 8 %) en `color-mix(in srgb, var(--accent-color) 10%, transparent)`. Daarvoor zijn geen extra tokens nodig, en ze werken in licht en donker.

## Beschikbare thema's

| Thema | Organisatie | WCAG 2.1 | Lettertypen | Bestand |
|---|---|---|---|---|
| `d-omnitwin` | standaard in de code (terugval), de huidige uitstraling | **niet AA** (9 paren, [#67](https://github.com/TLaan/D-OmniTwin/issues/67)) | Inter | [`static/css/themes/d-omnitwin.css`](../../static/css/themes/d-omnitwin.css) |
| `legacy` | klassiek groen-blauw: de uitstraling van v0.1.0 ([#284](https://github.com/TLaan/D-OmniTwin/issues/284)) | **niet AA** (13 paren) | Inter | [`static/css/themes/legacy.css`](../../static/css/themes/legacy.css) |
| `swf` | Gemeente Súdwest-Fryslân (voorstel, nog af te stemmen met SWF); standaard in `db/stuurdata/organisatie.sql` | **AA**, tekst AAA (7:1) | Montserrat (koppen), Source Sans 3 (tekst, open vervanger van Calluna Sans) | [`static/css/themes/swf.css`](../../static/css/themes/swf.css) |

De SWF-kleuren komen uit de live CSS van sudwestfryslan.nl; de afwegingen staan in [#89](https://github.com/TLaan/D-OmniTwin/issues/89) en [#284](https://github.com/TLaan/D-OmniTwin/issues/284). Er is (nog) geen officieel NLDS-thema van SWF.

### Wanneer welk thema

- **`swf`** voor Súdwest-Fryslân, en als voorbeeld voor een andere overheidsorganisatie. Sinds [#284](https://github.com/TLaan/D-OmniTwin/issues/284) rustig: kopbalk en vensterkoppen (Kompas) antraciet met een rode accentlijn, SWF-rood alleen voor primaire knoppen, de actieve tab en accenten; links, vinkjes en schuifregelaars in SWF-donkerblauw; tooltips en selectiebadge neutraal. Alle tekst haalt AAA (7:1), behalve de roze highlight die de app nog niet gebruikt (AA).
- **`legacy`** voor wie de groen-blauwe uitstraling van v0.1.0 wil (op verzoek van de projectleider). De kleuren zijn bewust die van v0.1.0 gebleven, ook waar ze WCAG 2.1 AA niet halen. Daarom is voor SWF het `swf`-thema bepaald en niet het oude groen-blauw. `legacy` is kiesbaar in het beheerscherm, met een waarschuwing, maar **nooit de standaard** (niet in de code, niet in `organisatie.sql`, niet als inlogthema van de realm; de test bewaakt dat). Een overheidsorganisatie moet aan WCAG 2.1 AA voldoen (Besluit digitale toegankelijkheid overheid); gebruik `legacy` dus alleen intern of ter vergelijking. Haalt `legacy` ooit AA (aangepaste kleuren, de test dwingt dan `@wcag-aa: ja` af), dan kan het ook bij SWF gekozen worden.
- **`d-omnitwin`** is de terugval van de code (een instantie zonder thema of met een onbekende naam) en het uitgangspunt voor een eigen thema zonder eigen lettertype. Het haalt AA nog niet; dat hoort bij de toegankelijkheidsronde ([#67](https://github.com/TLaan/D-OmniTwin/issues/67)).

### WCAG-status in het thema

De kop van elk themabestand heeft de regel `@wcag-aa: ja` of `@wcag-aa: nee`. `GET /api/organisatie/themas` geeft die terug als `wcag_aa` (`true`, `false`, of `null` als de regel ontbreekt), en het beheerscherm toont bij een thema met `nee` het label *niet WCAG AA* en bij de keuze de waarschuwing "Voldoet niet aan WCAG 2.1 AA; niet geschikt als standaard voor een overheidsorganisatie." `tests/test_thema.py` controleert dat de regel klopt: `ja` alleen als alle contrastparen AA halen, `nee` alleen als er echt tekorten zijn.

## Basistokens

Welke app-variabele welk token leest. De terugval in `styles.css` is gelijk aan `d-omnitwin.css` (de test bewaakt dat). `legacy` heeft dezelfde basistokens als het standaardthema (de kleuren van v0.1.0).

| App-variabele (`styles.css`) | Token | Standaard licht / donker | SWF licht / donker |
|---|---|---|---|
| `--bg-primary` (pagina) | `--basis-color-default-bg-document` | `#f1f5f9` / `#0f172a` | `#fafafa` / `#141414` |
| `--bg-secondary` (vlakken) | `--basis-color-default-bg-default` | `#ffffff` / `#1e293b` | `#ffffff` / `#1e1e1e` |
| `--text-primary` | `--basis-color-default-color-document` | `#1e293b` / `#f1f5f9` | `#1e1e1e` / `#ffffff` |
| `--text-secondary`, `--secondary-color` | `--basis-color-default-color-subtle` | `#64748b` / `#94a3b8` | `#4a4a4a` / `#bdbdbd` |
| `--border-color` | `--basis-color-default-border-subtle` | `#e2e8f0` / `#334155` | `#e6e6e6` / `#3a3a3a` |
| `--primary-color` (links, koppen in panelen, schuifregelaars) | `--basis-color-accent-1-color-default` | `#1e3a8a` / `#3b82f6` | `#005a78` / `#7fd3f0` |
| `--primary-dark` | `--basis-color-accent-1-color-hover` | `#1e40af` / `#2563eb` | `#00445c` / `#b3e5f7` |
| `--primary-fill` (vlak: aangevinkt vakje, secundaire knop hover) | `--basis-color-accent-1-bg-default` | `#1e3a8a` / `#2563eb` | `#005a78` / `#7fd3f0` |
| `--on-primary-fill` (tekst op dat vlak) | `--basis-color-accent-1-inverse-color-default` | `#ffffff` | `#ffffff` / `#141414` |
| `--action-color` | `--basis-color-action-1-color-default` | `#1e3a8a` / `#3b82f6` | `#a8003b` / `#ffa3bc` |
| `--action-dark` | `--basis-color-action-1-color-hover` | `#1e40af` / `#2563eb` | `#8c0030` / `#ffb3c6` |
| `--action-fill` (primaire knop, chatbubbel, actieve chatknop) | `--basis-color-action-1-bg-default` | `#1e3a8a` / `#2563eb` | `#a8003b` / `#a8003b` |
| `--action-fill-dark` (knop hover) | `--basis-color-action-1-bg-hover` | `#1e40af` / `#1d4ed8` | `#8c0030` / `#8c0030` |
| `--on-action-fill` (tekst op knop) | `--basis-color-action-1-inverse-color-default` | `#ffffff` | `#ffffff` |
| `--accent-color`, `--brand-accent` (selectie, highlight in lijsten) | `--basis-color-accent-2-bg-default` | `#c59d00` / `#eab308` | `#007ba3` / `#4cc3ea` |
| `--accent-text` | `--basis-color-accent-2-color-default` | `#856a00` / `#eab308` | `#005a78` / `#7fd3f0` |
| `--brand-nature` | `--basis-color-accent-3-color-default` | `#15803d` / `#22c55e` | `#3d5500` / `#b5e04a` |
| `--color-danger` | `--basis-color-negative-color-default` | `#b91c1c` / `#ef4444` | `#991b1b` / `#fca5a5` |
| `--color-success` | `--basis-color-positive-color-default` | `#15803d` / `#22c55e` | `#166534` / `#86efac` |
| `--color-warning` | `--basis-color-warning-color-default` | `#c2410c` / `#f97316` | `#9a3412` / `#fdba74` |
| `--focus-ring` | `--basis-focus-outline-color` | `#1e3a8a` / `#93c5fd` | `#1e1e1e` / `#ffffff` |
| `--border-radius` / `--border-radius-sm` | `--basis-border-radius-lg` / `-md` | `12px` / `8px` | `8px` / `4px` |
| `--spacing-xs` … `--spacing-xl` | `--basis-space-block-xs` … `-xl` | `0.25rem` … `2rem` | gelijk |
| lettertype `body`, knoppen, invoervelden | `--basis-text-font-family-default` | Inter | Source Sans 3 |
| lettertype `h1`–`h6` | `--basis-heading-font-family` | Inter | Montserrat |

Daarnaast zet `swf.css` tokens die de app nog niet leest maar die bij het palet horen: `--basis-color-accent-3-bg-default` (groen vlak, alleen met donkere tekst) en `--basis-color-highlight-*` (roze). NL Design System kent `accent-1` tot en met `accent-3`; het vierde SWF-accent (roze) is daarom `highlight`.

## Componenttokens

Alle `--d-omnitwin-*`-tokens. Elk thema zet ze allemaal, in licht en donker: `tests/test_thema.py` zoekt elk `var(--d-omnitwin-…)` in de viewer (CSS, JS, templates, SVG) op en faalt als een thema er één mist, of als een thema een token zet dat nergens gelezen wordt.

| Token | Waar | Standaard licht / donker | SWF licht / donker |
|---|---|---|---|
| `--d-omnitwin-header-background-color-start` / `-end` | kopbalk en kop van het Kompas-venster (verloop) | `#1e3a8a`→`#15803d` / `#3b82f6`→`#22c55e` | `#2b2b2b`→`#1e1e1e` / `#262626`→`#1a1a1a` |
| `--d-omnitwin-header-color` | tekst, iconen en focusrand in de kopbalk | `#ffffff` / `#f1f5f9` | `#ffffff` |
| `--d-omnitwin-header-accent-color` / `-width` | accentlijn onder kopbalk en vensterkoppen, en links naast het actieve menu-item in het beheerscherm ([#284](https://github.com/TLaan/D-OmniTwin/issues/284)) | `0px` (geen lijn) | `#bf0042`, `4px` |
| `--d-omnitwin-tab-active-background-color` | actieve knop in de tabbalk links | `#c59d00` / `#eab308` | `#fbeef2` / `#3a1621` |
| `--d-omnitwin-tab-active-color` | icoon op de actieve tab | `#0f172a` | `#a8003b` / `#ffb3c6` |
| `--d-omnitwin-tab-active-border-color` / `-width` | rand van de actieve tab ([#284](https://github.com/TLaan/D-OmniTwin/issues/284)); gewone tabs hebben 2px | gelijk aan het vlak, `2px` | `#a8003b` / `#ff8fae`, `3px` |
| `--d-omnitwin-welcome-button-background-color` | knop "Kaart verkennen" op het welkomstscherm | `#c59d00` / `#eab308` | `#a8003b` |
| `--d-omnitwin-welcome-button-color` | tekst op die knop | `#0f172a` | `#ffffff` |
| `--d-omnitwin-welcome-accent-color` | productnaam, stap-iconen en gloed op het welkomstscherm | `#856a00` / `#eab308` | `#a8003b` / `#ffa3bc` |
| `--d-omnitwin-tooltip-background-color` | tooltips: kaart (deck.gl), Kompas-segment, Kompas-detailpopup, grafieken (Chart.js) | `#0f172a` / `#f1f5f9` | `#1e1e1e` / `#fafafa` |
| `--d-omnitwin-tooltip-color` | tekst in die tooltips | `#ffffff` / `#0f172a` | `#ffffff` / `#1e1e1e` |
| `--d-omnitwin-selection-badge-background-color` | selectiebadge onder in beeld ("Bolsward-Zuidoost · 3D-panden"); het icoon erin is altijd wit, dus een donker vlak | `#047857` | `#2b2b2b` / `#3d3d3d` |
| `--d-omnitwin-selection-badge-color` | tekst op de selectiebadge | `#ffffff` | `#ffffff` |
| `--d-omnitwin-beeldmerk-vlak` / `-lijn` / `-kern` | beeldmerk in kopbalk, beheerscherm en favicon (`/api/organisatie/beeldmerk.svg`), [#249](https://github.com/TLaan/D-OmniTwin/issues/249) | `#0f172a` / `#3b82f6` / `#22c55e` | `#ffffff` / `#bf0042` / `#8c0030` |
| `--d-omnitwin-beheer-kop-background-color-start` / `-end` | kop van de zijbalk in het beheerscherm (altijd donker), [#284](https://github.com/TLaan/D-OmniTwin/issues/284) | `#2563eb`→`#1d4ed8` | `#2b2b2b`→`#1e1e1e` |
| `--d-omnitwin-beheer-kop-color` | tekst in die kop | `#ffffff` | `#ffffff` |
| `--d-omnitwin-beheer-nav-active-background-color` / `-color` | actief menu-item in het beheerscherm | `#2563eb` / `#ffffff` | `#3d3d3d` / `#ffffff` |

`legacy` heeft dezelfde componenttokens als het standaardthema, behalve twee waarden van v0.1.0: wit icoon op de gouden actieve tab (`--d-omnitwin-tab-active-color: #ffffff`) en de groene selectiebadge `#10b981`. Het beheerscherm leest naast de `--d-omnitwin-beheer-*`-tokens ook `--basis-color-action-1-*` (primaire knop) en de beeldmerk- en accentlijntokens; `tests/test_thema.py` zoekt de tokens ook in `admin-panel/src`.

## Wat niet in een thema hoort: datakleuren

De kleuren van de **data** blijven buiten het thema:

- Z-score-schaal en choropleten op de kaart, de legenda-kleurschaal en "geen data"-grijs: de kleurenblindveilige paletten uit de tabel `color_schemas` (`services/color_scale_service.py`, beheer via de admin-API, publiek via `/api/visualisatie/paletten`).
- De segmentkleuren van het Kompas-zonnediagram (afwijking per indicator) en de vaste kleuren per Kompas-thema in `app.js`.
- De reekskleuren in vergelijkingsgrafieken (`areaColors` in `app.js` en `kompas.js`), de trendlijn in de Kompas-popup en de kleuren van externe kaartlagen (`kleur_lijn`/`kleur_fill` uit de laagdefinitie).
- De **selectierand op de kaart** (goud `#eab308`, in `app.js`) en het bijbehorende voorbeeld in de legenda (`--map-selection-color` in `styles.css`). Die rand moet afsteken tegen het datapalet, dat per thema gelijk is; een huisstijlkleur (SWF-blauw) zou wegvallen tegen blauwe klassen.

NL Design System heeft geen choropletpaletten, en een huisstijlkleur is geen goede datakleur: rood en groen naast elkaar zijn voor kleurenblinden niet te onderscheiden, en een merkkleur draagt betekenis ("goed"/"slecht") die de data niet heeft. Een thema bepaalt alleen de UI eromheen. De test laat een thema falen dat iets anders zet dan `--basis-*` en `--d-omnitwin-*`.

In de detailpopup van het Kompas staat de waarde in de tooltipkleur met de datakleur als blokje ernaast: een gele datakleur als tekst was op een licht vlak onleesbaar.

## Een eigen thema maken

1. **Kopieer** `static/css/themes/swf.css` (met eigen lettertypen) of `d-omnitwin.css` (zonder) naar `static/css/themes/<naam>.css`. De naam bestaat alleen uit kleine letters, cijfers en koppeltekens (`[a-z0-9-]`), bijvoorbeeld `leeuwarden` of `tytsjerksteradiel`.
2. **Pas de tokens aan** in alle drie de blokken (licht, donker, donker via systeeminstelling; de laatste twee zijn gelijk). Kleuren als `#rrggbb`. Zet alle componenttokens uit de tabel hierboven. Houd de opbouw aan: alleen `--basis-*` en `--d-omnitwin-*`, geen selectors voor componenten.
   - Een huisstijlkleur die als tekst of onder witte tekst te weinig contrast heeft, krijgt een donkere (licht thema) of lichte (donker thema) variant voor `color-default`; de originele kleur blijft voor `bg-default` als vlak of rand.
   - Eigen lettertype: alleen open licenties (OFL e.d.), zelf gehost in `static/vendor/<pakket>@<versie>/` met het licentiebestand, en een regel in `NOTICE.md` en `static/vendor/README.md`. Laad het met `@import url("../../vendor/...")` bovenaan het thema. Geen Google Fonts, Typekit of andere CDN ([#117](https://github.com/TLaan/D-OmniTwin/issues/117)); de CSP staat dat ook niet toe.
3. **Toets het contrast** (WCAG 2.1 AA: 4,5:1 voor tekst, 3:1 voor UI-onderdelen en focus) en zet in het kopcommentaar `@wcag-aa: ja` (of `nee`, als je bewust tekorten houdt; de test controleert dat het klopt):

   ```bash
   python -m pytest tests/test_thema.py      # faalt bij een te laag contrast of een ontbrekend token
   python tests/test_thema.py --rapport      # tabel met alle contrasten per thema en modus
   ```

4. **Zet het thema aan**: in het beheerscherm onder **Organisatie** (zie [Thema kiezen in het beheerscherm](#thema-kiezen-in-het-beheerscherm)), of met SQL in de tabel `organisatie` (zie [Eigen organisatie](installatie.md#eigen-organisatie)):

   ```sql
   UPDATE organisatie SET thema = 'leeuwarden';
   ```

   Ververs de pagina; licht en donker wisselen met de knop in de kopbalk.
5. **Inlogpagina** (alleen met Keycloak): maak ook `deploy/keycloak/themes/<naam>/` (zie hieronder).
6. **Bekijk** het welkomstscherm, de kaart met een indicator en een selectie, de legenda, het Kompas (met tooltip en detailpaneel), de chat en de rapportkeuze, in licht en donker.
7. **Teruggeven**: een thema dat de organisatie zelf goedkeurt, kan als pakket naar [`nl-design-system/themes`](https://github.com/nl-design-system/themes) (map `proprietary/<organisatie>-design-tokens`, tokens in JSON volgens de basis-tokens). De tokennamen zijn al dezelfde; alleen de vorm (JSON in plaats van CSS) verschilt. Dat past bij de governance via OpenWebconcept ([#183](https://github.com/TLaan/D-OmniTwin/issues/183)).

## Thema kiezen in het beheerscherm

Beheerscherm → **Organisatie** ([#253](https://github.com/TLaan/D-OmniTwin/issues/253), alleen voor de rol `beheerder`):

- **Thema:** alle bestanden in `static/css/themes/`, met een voorbeeld van kopbalk, knop, link, actieve tab en beeldmerk in licht en donker. De kleuren komen uit de tokens van het thema zelf (`GET /api/organisatie/themas`: het lichte `:root`-blok en `[data-theme="dark"]`, `var(--…)` opgelost). Lettertypen ziet het voorbeeld niet. Een thema dat WCAG 2.1 AA niet haalt (`@wcag-aa: nee`, nu `d-omnitwin` en `legacy`) krijgt het label *niet WCAG AA*; kies je het, dan staat er een waarschuwing boven het voorbeeld. Opslaan kan wel.
- **Opslaan** zet de kolom `thema` in de tabel `organisatie` (`PUT /api/organisatie`). Een naam zonder bestand geeft een foutmelding (422); er verandert dan niets. Viewer en beheerscherm tonen het nieuwe thema na een gewone herlaadactie: themabestanden en pagina's hebben `Cache-Control: no-cache` ([#246](https://github.com/TLaan/D-OmniTwin/issues/246)), en de viewer leest het thema bij elke paginalading uit de database. Geen herstart nodig.
- Elke wijziging staat in de log (categorie `ADMIN`): wie (gebruikersnaam en `sub`) en welke velden, met oude en nieuwe waarde (het contactadres alleen als "gewijzigd").
- Een nieuw thema maak je nog steeds als bestand (hierboven); uploaden kan niet.

**De inlogpagina van Keycloak wisselt niet mee.** Het beheerscherm zet alleen het viewerthema; het inlogthema is `loginTheme` van de realm (zie hieronder). Zet dat apart, in de admin-console van Keycloak (*Realm settings* → *Themes* → *Login theme*) of met:

```bash
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080/auth --realm master --user <KEYCLOAK_ADMIN>
docker compose exec keycloak /opt/keycloak/bin/kcadm.sh update realms/omnitwin -s loginTheme=<thema>
```

Bewuste keuze: anders zou de backend blijvend beheerrechten op de realm nodig hebben (admin-API), en kon wie de backend overneemt ook Keycloak aanpassen. Die toegang hebben nu alleen de hulpmiddelen voor demo en test (`keycloak-demo`, testaccounts). Bovendien heeft niet elk viewerthema een inlogthema in `deploy/keycloak/themes/`.

## Inlogpagina (Keycloak)

Met het compose-profiel `keycloak` ([installatie](installatie.md)) heeft de inlogpagina een eigen thema per organisatie in `deploy/keycloak/themes/<thema>/login/`:

- `theme.properties`: `parent=keycloak.v2`, met één extra stylesheet. Geen eigen FreeMarker-templates: pagina's en teksten blijven die van Keycloak, dus een Keycloak-update breekt het thema niet.
- `resources/css/omnitwin.css`: de PatternFly-variabelen van `keycloak.v2` met de waarden van de NLDS-tokens (knop en links `action-1`/`accent-1`, focus, hoeken, lettertypen) en het kopbalkverloop als achtergrond, in licht en donker (`.pf-v5-theme-dark`, volgt de systeeminstelling). De lettertypen komen van `/static/vendor/` van de viewer op dezelfde host; met een externe identity provider valt het terug op het systeemfont.
- `docker-compose.yml` mount `deploy/keycloak/themes` op `/opt/keycloak/themes`.
- Keuze per realm: `"loginTheme"` in `deploy/keycloak/realm-omnitwin.json` (standaard `swf`, zoals de organisatie in `db/stuurdata/organisatie.sql`). De realm wordt alleen bij de eerste start geïmporteerd; bij een bestaande realm: admin-console → *Realm settings* → *Themes* → *Login theme*, of `kcadm.sh update realms/omnitwin -s loginTheme=<thema>`. Een ander thema kiezen in het beheerscherm verandert dit niet (zie [Thema kiezen in het beheerscherm](#thema-kiezen-in-het-beheerscherm)).
- Keycloak bewaart gecomprimeerde kopieën van thema-bestanden in de container. Na een wijziging aan een thema: `docker compose up -d --force-recreate keycloak` (een gewone herstart is niet genoeg).

`tests/test_thema.py` controleert dat elk viewerthema een inlogthema heeft, dat de realm een bestaand thema met `@wcag-aa: ja` kiest (dus nooit `legacy`) en dat de knopkleur gelijk is aan `--basis-color-action-1-bg-default`. Een logo op de inlogpagina zit er nog niet in (alleen de realmnaam); dat kan later met een afbeelding in `resources/img/` en een regel CSS.

## Gecontroleerde contrasten

`python tests/test_thema.py --rapport` geeft de volledige tabel: 198 paren over drie thema's in licht en donker, 176 voldoen, 22 zijn bekende tekorten (alleen in `d-omnitwin` en `legacy`). Een selectie:

| Paar (eis) | Standaard licht / donker | legacy licht / donker | SWF licht / donker |
|---|---|---|---|
| secundaire tekst op pagina (4,5) | 4,34 / 6,96 | 4,34 / 6,96 | 8,49 / 9,81 |
| link op paneel (4,5) | 10,36 / 3,98 | 10,36 / 3,98 | 7,68 / 9,91 |
| tekst op primaire knop (4,5) | 10,36 / 5,17 | 10,36 / 5,17 | 7,70 / 7,70 |
| kopbalktekst, eind verloop (4,5) | 5,02 / 2,08 | 5,02 / 2,08 | 16,67 / 17,40 |
| icoon op actieve tab (3) | 6,97 / 9,31 | 2,56 / 1,92 | 6,82 / 9,51 |
| rand actieve tab op paneel (3) | 2,56 / 7,63 | 2,56 / 7,63 | 7,70 / 7,77 |
| tekst op selectiebadge (4,5) | 5,48 / 5,48 | 2,54 / 2,54 | 14,16 / 10,86 |
| tooltiptekst (4,5) | 17,85 / 16,30 | 17,85 / 16,30 | 16,67 / 15,97 |
| beheerscherm: actief menu-item (4,5) | 5,17 | 5,17 | 10,86 |
| focusrand op paneel (3) | 10,36 / 8,11 | 10,36 / 8,11 | 16,67 / 16,67 |

### SWF: AAA voor tekst

`swf` haalt voor elk tekstpaar 7:1 (WCAG 2.1 AAA, 1.4.6), op één paar na; `tests/test_thema.py` (`test_swf_tekst_aaa`) dwingt dat af. UI-onderdelen en focus halen 3:1 (AA, 1.4.11; er is geen AAA-eis voor UI). Het laagste tekstpaar is 7,13:1 (succestekst `#166534`).

| Paar | Contrast | Waarom AA en geen AAA |
|---|---|---|
| donkere tekst `#1e1e1e` op SWF-roze `#ff00e3` (`--basis-color-highlight-*`) | 5,05:1 | Het roze is te licht voor witte tekst en te donker voor 7:1 (ook zwart haalt maar 6,36:1). De app leest de highlight-tokens nog niet. |

Daarnaast, niet als contrastpaar te toetsen: de actieve tab verschilt van een gewone tab door een **dikkere rand** (3px tegen 2px) en een gekleurd vlak, niet alleen door kleur (WCAG 1.4.1; de test controleert de randdikte). De focusrand is bijna zwart (licht) of wit (donker), in de kopbalk wit. `prefers-reduced-motion` wordt al gerespecteerd in `styles.css`; een aparte `prefers-contrast: more`-variant is er niet (het thema heeft al AAA-contrast).

## Bekende contrasttekorten (d-omnitwin en legacy)

`d-omnitwin.css` neemt de bestaande basiskleuren één op één over, zodat er visueel niets verandert. Negen paren halen WCAG AA daarin niet; ze staan als `BEKENDE_TEKORTEN` in `tests/test_thema.py` en horen bij de toegankelijkheidsronde ([#67](https://github.com/TLaan/D-OmniTwin/issues/67)):

| Modus | Paar | Contrast |
|---|---|---|
| licht | secundaire tekst `#64748b` op pagina `#f1f5f9` | 4,34:1 |
| licht | goud `#c59d00` als selectie op wit, en als rand van de actieve tab | 2,56:1 (eis 3:1) |
| donker | link en actietekst `#3b82f6` op paneel `#1e293b` | 3,98:1 |
| donker | link hover `#2563eb` op paneel `#1e293b` | 2,83:1 |
| donker | fouttekst `#ef4444` op paneel `#1e293b` | 3,89:1 |
| donker | kopbalktekst `#f1f5f9` op `#3b82f6` / `#22c55e` | 3,36:1 / 2,08:1 |

(De rand van de actieve tab is in het standaardthema het gouden vlak zelf; dat paar is sinds [#284](https://github.com/TLaan/D-OmniTwin/issues/284) apart getoetst, het tekort bestond al.)

`legacy` heeft dezelfde negen, plus vier van v0.1.0 die het standaardthema in [#89](https://github.com/TLaan/D-OmniTwin/issues/89) al had opgelost: wit icoon op de gouden actieve tab (2,56:1 licht, 1,92:1 donker; eis 3:1) en wit op de groene selectiebadge `#10b981` (2,54:1, licht en donker). Bewust niet gerepareerd: `legacy` is de oorspronkelijke uitstraling.

Het SWF-thema heeft geen tekorten (`@wcag-aa: ja`; de test staat geen uitzonderingen toe).

## Nog niet via het thema

- **Beheerscherm** (`admin-panel/`, React) en de **rapportpagina's** (`/admin/rapport/...`, onderdeel van het beheerscherm): het beheerscherm laadt het thema (`admin-panel/src/thema.ts`) en neemt kop, actief menu-item, primaire knop, beeldmerk, accentlijn en lettertype over; de rest (`--color-*`, slate/blauw, tabellen, grafieken) en de rapportpagina's hebben nog een eigen palet. Vervolg: de `--color-*`-variabelen naar de `--basis-*`-tokens laten wijzen, zoals in `styles.css`.
- **API-documentatie** (`/docs`): de standaard Swagger UI, zelf gehost; niet in de huisstijl.
- **Foutpagina's** van de backend (bv. 404 op een ontbrekend bestand): platte tekst, zonder opmaak.
- **Statusmelding** "verbinding" (`.verbindingsmelding`): vaste amberkleuren voor een waarschuwing, met voldoende contrast in licht en donker.
- **Schaduwen en scrims** (`rgba(0, 0, 0, …)`) en de witte tinten op de gekleurde kopbalk: neutraal, werken op elk thema.

## Vervolg (#89)

- Het beheerscherm en de rapporten op dezelfde tokens (zie hierboven).
- Componenten: knoppen, formuliervelden, dialogen en meldingen naar NLDS-componenten (CSS van de Utrecht-/Candidate-componenten, zelf gehost), die dezelfde basistokens lezen.
- axe/pa11y in de CI per thema ([#62](https://github.com/TLaan/D-OmniTwin/issues/62)).

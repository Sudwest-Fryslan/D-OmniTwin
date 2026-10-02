# static/vendor — zelf gehoste bibliotheken en lettertypen

De frontend laadt geen code, opmaak of lettertypen van CDN's of Google Fonts (#117).
Zo gaat het IP-adres van de bezoeker niet naar derden en werkt de applicatie ook als een CDN uitvalt.
De test `tests/test_geen_externe_resources.py` bewaakt dat.

Elk pakket staat in een eigen map `<pakket>@<versie>/`, met het licentiebestand erbij.
De bestanden komen ongewijzigd uit de officiële npm-tarball (`registry.npmjs.org`).
De `integrity`-hash van de tarball is bij het downloaden gecontroleerd.

| Map | npm-pakket | Bestanden | Licentie | Gebruikt in |
|---|---|---|---|---|
| `maplibre-gl@3.6.2/` | [`maplibre-gl@3.6.2`](https://registry.npmjs.org/maplibre-gl/-/maplibre-gl-3.6.2.tgz) | `dist/maplibre-gl.js`, `dist/maplibre-gl.css` | BSD-3-Clause (`LICENSE.txt`) | `templates/index.html` |
| `d3@7.9.0/` | [`d3@7.9.0`](https://registry.npmjs.org/d3/-/d3-7.9.0.tgz) | `dist/d3.min.js` | ISC (`LICENSE`) | `templates/index.html` |
| `deck.gl@9.4.0/` | [`deck.gl@9.4.0`](https://registry.npmjs.org/deck.gl/-/deck.gl-9.4.0.tgz) | `dist.min.js` | MIT (`LICENSE`) | `templates/index.html` |
| `chart.js@4.5.1/` | [`chart.js@4.5.1`](https://registry.npmjs.org/chart.js/-/chart.js-4.5.1.tgz) | `dist/chart.umd.min.js` | MIT (`LICENSE.md`) | `templates/index.html` |
| `inter@5.3.0/` | [`@fontsource-variable/inter@5.3.0`](https://registry.npmjs.org/@fontsource-variable/inter/-/inter-5.3.0.tgz) (Google Fonts Inter v20) | `files/inter-latin-wght-normal.woff2`, `files/inter-latin-ext-wght-normal.woff2` | SIL OFL 1.1 (`LICENSE`) | `templates/index.html`, `static/help.html` |
| `montserrat@5.3.0/` | [`@fontsource-variable/montserrat@5.3.0`](https://registry.npmjs.org/@fontsource-variable/montserrat/-/montserrat-5.3.0.tgz) (Google Fonts Montserrat v31) | `files/montserrat-latin-wght-normal.woff2`, `files/montserrat-latin-ext-wght-normal.woff2` | SIL OFL 1.1 (`LICENSE`) | `static/css/themes/swf.css` |
| `source-sans-3@5.3.0/` | [`@fontsource-variable/source-sans-3@5.3.0`](https://registry.npmjs.org/@fontsource-variable/source-sans-3/-/source-sans-3-5.3.0.tgz) (Google Fonts Source Sans 3 v19) | `files/source-sans-3-latin-wght-normal.woff2`, `files/source-sans-3-latin-ext-wght-normal.woff2` | SIL OFL 1.1 (`LICENSE`) | `static/css/themes/swf.css` |

`inter@5.3.0/inter.css` is eigen werk: de `@font-face`-regels uit `wght.css` van het pakket,
alleen de subsets latin en latin-ext, met `font-family: 'Inter'`.
Het is één variabel lettertype voor gewicht 100–900; de oude Google Fonts-link vroeg 400/500/600/700.

`montserrat@5.3.0/montserrat.css` en `source-sans-3@5.3.0/source-sans-3.css` zijn op dezelfde manier gemaakt,
met `font-family: 'Montserrat'` en `'Source Sans 3'`. Source Sans 3 is de open vervanger van Calluna Sans
(Adobe Typekit, licentie) uit de huisstijl van Súdwest-Fryslân. Alleen een thema dat ze nodig heeft, laadt ze (#89);
zie `docs/4-ux-design/thema-s.md`.

Bronkaartbestanden (`*.map`) zijn niet meegenomen. Alleen de browser-devtools vragen erom; die geven dan een 404.

## SRI en regeleinden

De `<script>`- en `<link>`-tags in `templates/index.html` houden hun `integrity`-hash (sha384).
De bestanden zijn byte-gelijk aan die op unpkg/jsdelivr, dus de hashes van #58/#84 kloppen nog.
De hash vangt een per ongeluk gewijzigd of half bijgewerkt bestand.
`.gitattributes` zet `static/vendor/**` op `-text`, zodat Git op Windows geen CRLF invoegt (dat zou de hash breken).

## Bijwerken

1. Kies de nieuwe versie en lees de changelog (MapLibre 4.x vraagt een migratie).
2. Haal de tarball op en controleer de integriteit tegen het register:

   ```bash
   npm view maplibre-gl@<versie> dist.tarball dist.integrity
   curl -sSfLO <tarball-url>
   openssl dgst -sha512 -binary <bestand>.tgz | openssl base64 -A   # moet gelijk zijn aan dist.integrity (na "sha512-")
   tar -xzf <bestand>.tgz            # pakt uit naar ./package/
   ```

3. Maak een nieuwe map `<pakket>@<nieuwe-versie>/`, kopieer de bestanden uit de tabel en het licentiebestand, en verwijder de oude map.
4. Bereken de nieuwe SRI-hash en zet die met het nieuwe pad in de template:

   ```bash
   openssl dgst -sha384 -binary <bestand> | openssl base64 -A
   ```

5. Werk deze tabel en `NOTICE.md` bij en draai `python -m unittest tests.test_geen_externe_resources`.

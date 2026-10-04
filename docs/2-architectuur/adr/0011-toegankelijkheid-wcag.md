# 0011. Toegankelijkheid: zoveel mogelijk WCAG 2.1 AA, met tekstalternatieven voor geo

- Status: voorgesteld
- Datum: 2026-10-04
- Issue: https://github.com/TLaan/D-OmniTwin/issues/67, https://github.com/TLaan/D-OmniTwin/issues/284
- Raakt: thema's per organisatie (https://github.com/TLaan/D-OmniTwin/issues/89), `docs/4-ux-design/toegankelijkheid.md`, `docs/9-beheer/thema-s.md`

## Context

Gemeenten zijn wettelijk verplicht hun websites en apps toegankelijk te maken: het Besluit digitale toegankelijkheid overheid verwijst naar EN 301 549 en daarmee naar WCAG 2.1 niveau AA, met een toegankelijkheidsverklaring (DigiToegankelijk). D-OmniTwin wil aan gemeenten en andere partijen worden aangeboden, dus dit geldt ook hier.

Tot nu toe stond toegankelijkheid wel in issue #67 en in `tests/test_thema.py` (contrast per thema), maar niet als architectuurprincipe. Bij de thema's bleek het verschil: het standaardthema `d-omnitwin` en het oorspronkelijke groen-blauwe thema van v0.1.0 halen het contrast van AA niet overal, het SWF-thema wel.

Een digitale tweeling is sterk visueel: kaarten, een zonnediagram (Kompas), kleurschalen. Die zijn niet volledig toegankelijk te maken voor iedereen.

## Besluit

**1. WCAG 2.1 AA is het uitgangspunt voor alle schermen**: viewer, beheerscherm, rapporten en inlogpagina's. Waar het kan zonder de functie te verliezen, gaan we verder (bijvoorbeeld AAA-contrast voor tekst in het SWF-thema).

**2. Voor geo en grafieken gelden tekstalternatieven.** Wat een kaart of het Kompas laat zien, moet ook zonder het beeld te vinden zijn: de waarde per gebied in het indicatorpaneel en als CSV, de gebiedsnaam en waarde in tooltips en tabellen, het antwoord van de D-Omni Assistent in tekst, en kleurenblindvriendelijke datakleuren. Informatie zit nooit alleen in kleur (zoals een actieve tab met ook een rand).

**3. Thema's worden getoetst.** `tests/test_thema.py` controleert het contrast per thema, in licht en donker. Een thema dat AA niet haalt, wordt gemarkeerd (`@wcag-aa: nee`; de API geeft `wcag_aa: false`), krijgt een waarschuwing in het beheerscherm en mag **niet de standaard** zijn voor een overheidsorganisatie.

**4. De status is openbaar.** `docs/4-ux-design/toegankelijkheid.md` houdt bij wat voldoet en wat (nog) niet, en bevat het concept van de toegankelijkheidsverklaring.

## Gevolgen

- Nieuwe schermen en componenten gebruiken thema-tokens en worden op contrast en toetsenbordbediening gecontroleerd. Pull requests met UI noemen de toegankelijkheid.
- Bekende tekorten staan in #67: vaste kleuren op het beheerdashboard en in rapporten, en een geautomatiseerde toets (axe) in de e2e ontbreekt nog.
- WCAG 2.1 AA en DigiToegankelijk staan bij de leidende standaarden van het project (AGENTS.md).

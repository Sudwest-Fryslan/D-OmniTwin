# Toegankelijkheid: status en conceptverklaring

Overheidswebsites en -apps moeten voldoen aan **WCAG 2.1 niveau AA** (Besluit digitale toegankelijkheid overheid, [DigiToegankelijk](https://www.digitoegankelijk.nl)) en een toegankelijkheidsverklaring publiceren in het [register](https://www.toegankelijkheidsverklaring.nl). Dit document is de stand voor D-OmniTwin en het concept voor die verklaring. Issue: [#67](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/67); productieklaar: [#257](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/257).

**Status (oktober 2026): voldoet gedeeltelijk.** Er is nog geen onderzoek door een onafhankelijke partij en nog geen volledige automatische meting (axe of pa11y). De verklaring is daarom op dit moment **status B of C** ("eerste maatregelen getroffen" / "voldoet gedeeltelijk") en kan pas naar A na een volledig onderzoek.

## Wat de verklaring moet bevatten, en wie wat doet

De verklaring hoort bij een **installatie** (de website op het adres van de organisatie), niet bij de broncode. Elke organisatie die D-OmniTwin publiceert, stelt dus een eigen verklaring op en meldt die aan bij het register. Dit document levert de inhoud over de software; de organisatie vult aan:

- het adres van de installatie en de datum;
- de contactgegevens voor meldingen over toegankelijkheid;
- de eigen inrichting: thema (kleuren, logo), eigen kaartlagen en teksten;
- het onderzoek: wie, wanneer, welke methode (bijvoorbeeld WCAG-EM).

## Gedaan

| Maatregel | Waar |
|---|---|
| Taal van de pagina (`lang="nl"`), landmarks, één `h1`, alt-teksten | hoofdapp en beheeromgeving |
| Skiplink "Direct naar de kaart" | `templates/index.html` |
| Zichtbare focus (`--focus-ring`), geen `outline: none` meer | `static/css/styles.css` |
| Dialogen met `role="dialog"`, focus vasthouden, Escape sluit, focus terug | hoofdapp; getest in `tests/e2e/test_toegankelijkheid.py` |
| `prefers-reduced-motion`: camera en Kompas zonder animatie | getest in `tests/e2e/test_toegankelijkheid.py` |
| Labels en iconknoppen in de beheeromgeving, `lang="nl"` en titel in de build | `admin-panel/` ([#134](https://github.com/Sudwest-Fryslan/D-OmniTwin/pull/134)) |
| Contrast van het thema wordt getest; het SWF-thema heeft geen tekorten | `tests/test_thema.py` ([#89](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/89)) |
| Kleurschema's voor data zijn kleurenblind-veilig (uitgangspunt) | tabel `color_schemas` |

## Bekende tekorten

| Tekort | WCAG | Toelichting |
|---|---|---|
| Contrast in het standaardthema `d-omnitwin`: zeven kleurparen halen AA niet (onder meer secundaire tekst 4,34:1, goud als selectie 2,56:1, links en fouttekst in de donkere modus 2,83-3,98:1, kopbalktekst donker 2,08-3,36:1) | 1.4.3, 1.4.11 | Vastgelegd als `BEKENDE_TEKORTEN` in `tests/test_thema.py`; de test faalt zodra een paar wél voldoet, zodat de lijst actueel blijft. Een organisatie kan een eigen thema zonder tekorten gebruiken (zoals `swf`). |
| De kaart: buurten selecteren gaat met de muis; er is geen volledig toetsenbordalternatief op de kaart zelf | 2.1.1 | Of de andere selectiewegen in de UI een volwaardig alternatief zijn, is nog niet getoetst. |
| Kaartkleuren: informatie deels alleen via kleur (rood-geel-groen-schaal) | 1.4.1 | Bevinding uit #67; een schaal met patroon of label per klasse ontbreekt. |
| Kompas (D3-zonnediagram) en grafieken: geen tekstalternatief met dezelfde informatie in tabelvorm | 1.1.1, 1.3.1 | Een tabelweergave is het voorstel. |
| Klikbare elementen die geen knop zijn (`div`'s zonder toetsenbordbediening) | 2.1.1, 4.1.2 | Uit de statische toets van 30-09 (#67); niet nagelopen of alles is opgelost. |
| Rapporten (HTML/print) en geëxporteerde PDF's niet getoetst | div. | |
| Geen automatische meting in de CI | - | axe/pa11y tegen de draaiende stack staat open ([#62](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/62)). |
| Geen onderzoek met gebruikers van hulpmiddelen (schermlezer, vergroting) | - | |

## Vervolg

1. axe of pa11y in de lokale CI en daarna de GitHub-CI, per thema, met nul fouten op AA als eis ([#67](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/67), [#62](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/62)).
2. Contrast van `d-omnitwin.css` herstellen, of een toegankelijk standaardthema kiezen.
3. Tekstalternatief (tabel) voor Kompas en grafieken; kaartselectie met het toetsenbord.
4. Onderzoek volgens WCAG-EM door een onafhankelijke partij, vóór de eerste publieke productie-installatie; daarna de verklaring per installatie publiceren.

## Conceptverklaring (in te vullen per installatie)

> **Toegankelijkheidsverklaring** — *[organisatie]* streeft ernaar *[adres van de installatie]* toegankelijk te maken volgens WCAG 2.1 niveau AA. De website voldoet gedeeltelijk. Bekende problemen: onvoldoende kleurcontrast in delen van de interface, de kaart is niet volledig met het toetsenbord te bedienen, informatie op de kaart wordt deels alleen met kleur getoond, en het Kompas en de grafieken hebben nog geen tekstalternatief. We werken aan oplossingen (zie de [openbare issues](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/67)). Loopt u tegen een probleem aan? Neem contact op via *[contactgegevens]*. Deze verklaring is opgesteld op *[datum]* op basis van *[onderzoek]*.

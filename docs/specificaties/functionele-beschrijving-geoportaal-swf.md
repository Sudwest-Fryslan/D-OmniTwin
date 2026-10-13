# Functionele beschrijving: geoportaal en open data Súdwest-Fryslân

Status: inventarisatie, 13-10-2026. Technische details (endpoints, attributen, licenties, AVG-risico per laag): [opendata-swf-inventarisatie.md](../3-data-engineering/opendata-swf-inventarisatie.md).

## Kern

Súdwest-Fryslân publiceert geodata op twee plekken:

- het **geoportaal** https://geo.sudwestfryslan.nl/public/ (Neuron Smart Maps van Vicrea): 29 kaartlagen op twee ondergronden;
- **data.overheid.nl**: 6 datasets, waarvan 5 ook in het geoportaal staan.

Achter het portaal staat een GeoServer met 45 openbare WFS-lagen, meer dan het portaal toont.

D-OmniTwin wil deze data als bron opnemen en weer aanbieden, en de functies van het portaal kunnen bieden. Dat laatste is grotendeels nog niet zo. D-OmniTwin heeft al:

- een kaart met lagen en legenda;
- terugmelden op data;
- een DCAT-catalogus;
- OGC API Features (pg_featureserv);
- een WFS-bronadapter.

Wat ontbreekt:

- zoeken binnen een laag;
- klik-info per laag, ingericht als configuratie;
- downloaden in gangbare formaten;
- de SWF-GeoServer als toegestane bron.

## Doel en gebruikers

| Gebruiker | Wil | Voorbeelden |
|---|---|---|
| Inwoner | iets in de buurt vinden of nagaan | hondentoilet, losloopgebied, graf, strooiroute, monument, onderhoud in de straat |
| Ondernemer | regels en contact per locatie | standplaats, accountmanager, ligplaats, welstand, laadpaal |
| Medewerker | planning en beheer op de kaart | onderhoud wegen/riool/groen, bomen en winterkap, groenclusters |
| Hergebruiker (bedrijf, onderzoeker, andere overheid) | data afnemen | download, WMS/WFS, data.overheid.nl |

## Functies

| # | Functie | Waar | Wat doet de gebruiker, wat ziet hij | D-OmniTwin |
|---|---|---|---|---|
| F1 | Ondergrond kiezen | generiek | wisselt tussen luchtfoto (PDOK, WMTS) en BRT-kaart (PDOK, WMTS) | **al** |
| F2 | Lagen aan/uit | generiek | vinkt datasets aan; een laag is pas zichtbaar vanaf een zoomniveau | **al** (externe lagen); zoomgrenzen per laag: **gedeeltelijk** |
| F3 | Legenda | per laag | ziet kleur en symbool per laag of klasse | **al** (indicatoren, lagen) |
| F4 | Metadata | per laag | leest beschrijving en bron van een laag | **gedeeltelijk**: DCAT staat in de catalogus, niet bij de laag in de kaart |
| F5 | Zoeken op adres | generiek | typt een adres (vanaf 4 tekens), kiest een suggestie; de kaart zoomt in en selecteert alles binnen 10 m | **in aanbouw** (#336, PDOK Locatieserver) |
| F6 | Zoeken binnen een laag | 11 lagen | zoekt op plaats, type, status of naam, krijgt een resultatenlijst en zoomt per resultaat in. Voorbeelden: standplaatsen op plaats, sportlocaties op type, onderhoud op status, graven op naam overledene | **nog niet** |
| F7 | Objectgegevens (klik-info) | 23 lagen | klikt op een object en ziet een tabel met gekozen velden, bv. standplaats: branche, stroom, dagen; boom: motivatie, veiligheidsmaatregel | **gedeeltelijk**: klik-info voor gebieden en indicatoren, niet per externe laag met veldkeuze |
| F8 | Tooltip | 15 lagen | ziet bij aanwijzen een korte tekst, bv. welstandsgebied, accountmanager met telefoon | **gedeeltelijk** |
| F9 | Downloaden | per laag (7 lagen aan) | kiest formaat (GML, Shape, CSV, KML, GeoJSON) en gebied (kaartbeeld of hele dataset); de server maakt een bestand | **nog niet** voor lagen (wel export dashboard en inrichting) |
| F10 | Terugmelden op data | generiek | klikt een locatie aan en meldt een fout in de data met titel, bericht, naam en e-mail; de melding verschijnt anoniem op de kaart | **al** (#311 meldingen; melden gaat naar de bron) |
| F11 | Doorverwijzen naar melding openbare ruimte | generiek | link naar het formulier Melding Openbare Ruimte | **nog niet** (eenvoudig: link in inrichting) |
| F12 | Kaartlink delen | generiek | de URL bevat zoom en positie (#6/53.007/5.507) | **gedeeltelijk** (URL-parameters, geen positie) |
| F13 | Startbeeld, zoomen, inzoomen met kader | generiek | knop terug naar gemeente, zoomknoppen, kader trekken | **al** (behalve kader) |
| F14 | Documenten bij een object | ligplaatsen, geurcirkels | link naar een pdf (regels, scheepsgegevens) | **nog niet** |
| F15 | Tijd en planning | onderhoud, winterkap, standplaatsen | jaar van uitvoering, status, dagen per week; alleen als veld, geen tijdfilter | **gedeeltelijk** (jaargangen bij indicatoren) |
| F16 | Open data afnemen | WMS/WFS, data.overheid.nl | koppelt met GIS of downloadt via data.overheid.nl | **gedeeltelijk**: OGC API Features en DCAT bestaan, nog niet voor deze lagen |

Het portaal heeft **geen** meten, printen, filteren op attribuut of tijdreeksen. Locatie bepalen en zoeken op de kaart staan in de configuratie uit.

## Scenario's

1. **Inwoner zoekt een graf.** De inwoner zet *Grafinformatie opzoeken* aan, zoekt op de naam van de overledene en ziet een lijst met begraafplaats, grafnummer en naam. Een klik zoomt in op het graf. Het portaal toont grafnummer, naam, voornamen, geboorte- en overlijdensdatum, monument en oorlogsgraf. Bij dezelfde laag hoort in de WFS een grafoto. Zie AVG hieronder.
2. **Ondernemer zoekt een standplaats.** De ondernemer zoekt standplaatsen op plaats en klikt er een aan: branche, stroomvoorziening, jaarrond of seizoen, beschikbare dagen. Voor contact zet hij *Accountmanagers ondernemen* aan; de tooltip toont naam en telefoonnummer van de accountmanager in dat gebied.
3. **Inwoner wil weten wat er in de straat gebeurt.** Onderhoud wegen, riolering en groen tonen per straat het type maatregel, het jaar en de status. Zoeken kan op status.
4. **Medewerker bekijkt bomen en winterkap.** De bomenkaart toont per boom soort, motivatie, veiligheidsmaatregel en kapvergunning. Zoeken kan op woonplaats en straat.
5. **Schipper zoekt een ligplaats.** De lagen *Ligplaatsen historische schepen* en *Ligplaatsen regels* tonen type ligplaats en een link naar de regels (pdf).
6. **Hergebruiker downloadt sportlocaties** als CSV voor het huidige kaartbeeld, of koppelt de WFS in QGIS.

## Niet-functionele eisen

- **Toegankelijkheid:** WCAG 2.1 AA (ADR 0011). Het huidige portaal (AngularJS 1, Leaflet 0.7, Bootstrap 3) is niet getoetst. Zoeken en klik-info moeten ook zonder kaart werken, als lijst.
- **Privacy (AVG):** niet alles wat nu openbaar is, hoort open. Dit geldt in elk geval voor:
  - graven: naam overledene, data, foto;
  - coördinatoren en accountmanagers: naam, telefoon en e-mail van medewerkers;
  - grootgrondbezit: naam rechthebbende;
  - vergunningen (VIK): zaakomschrijving en toelichting;
  - HR-onderwijs: adressen.

  Eerst een toets per laag (zie de inventarisatie), daarna pas opnemen. Medewerkerscontact gaat via een functie-adres, niet via een persoon.
- **Open licenties:** de vijf geodatasets op data.overheid.nl zijn CC0. Voor de andere lagen staat geen licentie in het portaal of de WFS. Die moet de bronhouder vaststellen; tot die tijd geldt "licentie onbekend" (zoals nu bij de SWF-lagen in D-OmniTwin).
- **Actualiteit:** het portaal toont geen peildatum. D-OmniTwin legt per levering de datum en de bron vast (leveringen/versies) en toont die bij de laag.
- **Vindbaarheid:** elke laag krijgt een DCAT-beschrijving en komt in de catalogus. data.overheid.nl moet worden bijgewerkt: de hondentoiletten verwijzen naar een host die niet meer bestaat (geo.iszf.nl), en de Afvalkalender heeft geen distributie.
- **Bronhouderschap:** D-OmniTwin kopieert niet stil. Elke laag heeft een bronhouder en meldingen gaan naar die bron.

## Hoe D-OmniTwin dit afdekt

| Onderdeel | Stand |
|---|---|
| Data ophalen uit de SWF-GeoServer (WFS) | adapter **al**; domein `geo.sudwestfryslan.nl` nog toe te voegen |
| Beschrijving en catalogus (DCAT) | **al** |
| Kaart met lagen, legenda, ondergrond | **al** |
| Zoeken op adres | **in aanbouw** (#336) |
| Zoeken binnen een laag, resultatenlijst | **nog niet** |
| Klik-info en tooltip per laag via configuratie | **gedeeltelijk** |
| Downloaden per laag (formaat, gebied) | **nog niet**; via OGC API Features (pg_featureserv) is GeoJSON per bbox er al voor eigen tabellen |
| Terugmelden | **al** |
| Documentlinks bij objecten | **nog niet** |
| AVG-toets per laag | **nog niet** |

## Werkpakketten (voorstel voor de mijlpaal)

1. **Bron SWF-GeoServer.** Domein toestaan, één bron `swf-geoportaal` met een dataset per laag (DCAT, licentie, bronhouder), te beginnen met de CC0-lagen en de lagen zonder persoonsgegevens.
2. **Kaartlagen als configuratie.** Per laag instellen:
   - zoomgrenzen;
   - legenda;
   - tooltip;
   - klik-info met veldkeuze en labels;
   - documentlinks;
   - metadata bij de laag.

   Dit vervangt F2–F4, F7, F8 en F14 zonder code per laag.
3. **Zoeken.** Adres (#336) en zoeken binnen een laag op ingestelde velden, met resultatenlijst en inzoomen (F5, F6). Lijstweergave voor toegankelijkheid.
4. **Aanbieden en downloaden.**
   - lagen via OGC API Features;
   - download in CSV, GeoJSON, GML, Shape en KML, voor het kaartbeeld of de hele dataset (F9, F16);
   - registratie op data.overheid.nl bijwerken.
5. **Privacy en governance.**
   - AVG-toets per laag;
   - licentie vaststellen met de bronhouders;
   - actualiteit tonen;
   - link naar Melding Openbare Ruimte (F11).

   Lagen met persoonsgegevens alleen achter login of zonder die velden.

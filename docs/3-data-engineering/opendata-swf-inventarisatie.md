# Inventarisatie open data en geodata Súdwest-Fryslân

Stand 13-10-2026. Alleen metadata opgehaald, geen data geïmporteerd. De functionele beschrijving (gebruikers, functies, scenario's) staat in [functionele-beschrijving-geoportaal-swf.md](../specificaties/functionele-beschrijving-geoportaal-swf.md).

## Bronnen

| Bron | Wat | Hoe opgehaald |
|---|---|---|
| data.overheid.nl, organisatie `sudwest_fryslan` | 6 datasets | CKAN-API `package_search?fq=authority:"http://standaarden.overheid.nl/owms/terms/Sudwest_Fryslan"` |
| Geoportaal https://geo.sudwestfryslan.nl/public/ | 29 lagen + 2 ondergronden | `/public/map.config.json` (laagconfiguratie), `/public/page/` (teksten) |
| GeoServer https://geo.sudwestfryslan.nl/geoserver/ | 45 WFS-lagen: `swf` 41, `swf_kadaster` 3, `swf_vik` 1; WMS 46 lagen; OGC API Features aan (`/geoserver/ogc/features/v1/collections`) | GetCapabilities en DescribeFeatureType |

Het portaal is Neuron Smart Maps (Vicrea): AngularJS 1 en Leaflet, met een eigen backend. De portaal-API:

- `/public/data/:layer/:query` (data);
- `/public/search/:layer/:query/:question` (zoeken in een laag);
- `/public/geocoder/:i/:tekst` (adres zoeken, BAG, RD-coördinaten);
- download via websocket (`prepare download`, formaten GML/Shape/CSV/KML/GeoJSON, voor het kaartbeeld of de hele dataset).

De meeste portaallagen lezen rechtstreeks uit PostgreSQL (`datasource.type = postgres`). Een deel staat niet als WFS open.

Geen licentie of gebruiksvoorwaarden in de GetCapabilities (`Fees` en `AccessConstraints` leeg). Een WFS-GetFeature met `outputFormat=application/json` werkt (HTTP 200).

## data.overheid.nl

| Dataset | Licentie | Gewijzigd | Distributies | Opmerking |
|---|---|---|---|---|
| Bomen Súdwest-Fryslân | CC0 | 2026-04-28 | ZIP (portaal-download `gbi_boom`), WMS, WFS `geo.sudwestfryslan.nl/geoserver/swf` | WFS-laag `swf:gv_bomen` |
| Geurcirkels | CC0 | 2026-04-28 | ZIP, WMS, WFS | `swf:geurcirkels` |
| Hondentoiletten | CC0 | 2026-04-28 | CSV/SHP/KML via `geo.iszf.nl` (**reageert niet meer**), ZIP, WMS, WFS | `swf:swf_gbi_hondentoilet` |
| Ligplaatsen historische schepen | CC0 | 2026-04-23 | ZIP, WMS, WFS | `swf:ligplaatsen_hist_swf` |
| Sportlocaties | CC0 | 2026-04-28 | ZIP, WMS, WFS | `swf:geo_sportlocaties` |
| Afvalkalender | CC0 | 2026-04-28 | **geen** | alleen titel, geen distributie |

Overlap met het geoportaal: 5 van 6.

## Geoportaal: lagen

Legenda:
- **WFS**: typename in workspace `swf`, `–` = alleen via de portaal-API.
- **DON**: staat op data.overheid.nl.
- **Zoek**: zoekveld in het portaal.
- **D-OT**: al in D-OmniTwin.
- **AVG**: L = laag, M = middel (medewerkers- of bedrijfsgegevens, adressen), H = hoog (naam van persoon of rechthebbende).
- **Voorstel**: O = opnemen als bron, T = opnemen na AVG-toets of zonder persoonsvelden, L = alleen doorlinken.

| Laag (portaal) | Tabel | WFS | Geometrie | Klik-info / tooltip-velden | Zoek | DON | D-OT | AVG | Voorstel |
|---|---|---|---|---|---|---|---|---|---|
| Gemeentegrens | swf_gemeentegrens_2018 | swf_gemeentegrens_2018 | vlak | – | – | – | ja (CBS-gebiedsindeling) | L | L |
| Welstandsgebieden | welstandsgebieden | welstandsgebieden | vlak | gebied; WFS: toetsplicht, criteria, welstandsnota | – | – | deels (`swf-gebied-welstand-buurt`) | L | O |
| Welstandsroute | welstandsroute | – | lijn | opmerking | – | – | nee | L | O |
| Standplaatsen | standplaatsen | – | punt | plaats, branche, locatie, stroom, jaarrond, seizoen, ma–zo | plaats | – | nee | L | O |
| Sportlocaties | geo_sportlocaties | geo_sportlocaties | punt | type; naam accommodatie, vereniging, website, adres | type | ja | nee | L | O |
| Parkeervergunningen | parkeerzones | – | vlak | plaats, zone | plaats | – | nee | L | O |
| Onderhoud groen | gv_mrjplanning_groen | ~ gv_planning_groen_moor | vlak | WFS: werkzaamheden, jaar, plaats, straat | – | – | nee | L | O |
| Onderhoud riolering | gv_streng_planning | ~ gv_planning_riolering_moor | lijn | status, startjaar; WFS: maatregel, jaar, planstatus | status | – | nee | L | O |
| Onderhoud wegen | swf_gv_wegvakplanning | ~ gv_planning_verharding_moor | vlak | WFS: maatregel, jaar, planstatus | status | – | nee | L | O |
| Ondergrond, bijzondere omstandigheden | omstandigheden_ondergrond | – (WFS wel `t_bro_bodemkaart_simpel_swf`) | vlak | soort ondergrond | – | – | deels (BRO-bodemkaart PDOK) | L | O |
| Laadpalen (voorstel) | laadpalen | – | punt | nummer laadpaal | – | – | nee | L | O |
| Monumenten Rijks | rijks_monumenten | – | vlak | straat, huisnummer | – | – | ja (RCE via PDOK) | L | L (RCE is bron) |
| Monumenten Gemeentelijk | gemeentelijke_monumenten | – | vlak | adres | – | – | nee | L | O |
| Ligplaatsen regels | ligplaatsen_swf | ligplaatsen_swf | lijn | type ligplaats, pdf | type | – | nee | L | O |
| Ligplaatsen historische schepen | ligplaatsen_hist_swf | ligplaatsen_hist_swf | punt | scheepstype, naam schip, bouwjaar, werf, pdf | plaatsnaam | ja | nee | L (scheepsnaam) | O |
| Hondentoiletten | swf_gbi_hondentoilet | swf_gbi_hondentoilet | punt | id, woonplaats | woonplaats | ja | nee | L | O |
| Honden losloopgebieden | losloopgebieden2408202000 | Losloopgebieden | vlak | – | – | – | nee | L | O |
| Groenclusters | gv_groenclusters | Groenclusters | vlak | – | – | – | nee | L | O |
| Strooiroutes | geo_strooiroutes | geo_strooiroutes | lijn | level | – | – | nee | L | O |
| Grafinformatie | v_graven | graven (+ v_graffoto) | vlak | grafnummer, naam overledene, voornamen, geboren, overleden, monument, oorlogsgraf | naam overledene | – | nee | **H** | T |
| Gemeentelijke begraafplaatsen | begraafplaatsen | begraafplaatsen | punt | plaats, straat, status; WFS: beheer, tarief, contact, verordening | plaats | – | nee | M (contactvelden) | O |
| Geurcirkels | geurcirkels | geurcirkels | vlak | WFS: veld1, veld2, url | – | ja | nee | L | O |
| Coördinatoren | dorps_wijk_coord | dorps_wijk_coord | vlak | plaats/wijk, 1e contact; WFS: naam, functie, telefoon, mobiel, e-mail, foto van 3 personen | woonplaats | – | deels (alleen gebieden) | **H** | T |
| Bomenkaart en winterkap | gv_bomen | gv_bomen | punt | soort, conditie, motivatie, herplant, kapvergunning, veiligheidsmaatregel, inspectie | woonplaats, straat | ja | nee | L | O |
| Beschermde gezichten rijks | townscapes_swf_rijks | – | vlak | naam | – | – | ja (RCE via PDOK) | L | L |
| Beschermde gezichten gemeentelijk | townscapes_swf_gemeentelijk | – | vlak | – | – | – | nee | L | O |
| Bebouwingscontour houtkap | bbknatuurwet | – | vlak | woonplaats | – | – | nee | L | O |
| Beschermde boomstructuren | boomstructuren2026 | – | vlak | – | – | – | nee | L | O |
| Accountmanagers ondernemen | accountteamondernemers | – | vlak | naam accountmanager, telefoon | – | – | nee | **M** | T (functie-adres) |

Ondergronden: luchtfoto (PDOK WMTS `Actueel_ortho25`) en BRT (PDOK WMTS `standaard`). D-OmniTwin heeft beide al.

**Configuratiefout:** de laag Geurcirkels wijst in het portaal naar de BAG-WMS van PDOK (laag `pand`), niet naar `swf:geurcirkels`.

## GeoServer-lagen die niet in het portaal staan

| WFS-laag | Inhoud (velden) | D-OT | AVG | Voorstel |
|---|---|---|---|---|
| kea_afstandtotkoelte_cbsbuurten, kea_koeleplekken_cbsbuurten | klimaateffectatlas per buurt | ja (afstand tot koelte) | L | O (koppelen aan bestaande laag) |
| fka_wateroverlast_gevellijnen, heatmap_wateroverlast_gevellijnen_5m, heatmap_wateroverlast_rijbanen_15m2 | klasse wateroverlast, hexagonen | nee | L | O |
| gv_crow_a_berdi, gv_crow_b_berdi, gv_crow_b_rijbaan_berdi, rayons_onkruidbestrijding | onkruidbestrijding, uitvoerder | nee | L | O |
| gv_kadeinsp_bevindingen, gv_kadeinsp_routes | kade-inspecties, url | nee | L | O |
| gv_planning_integraalwerk_moor | projectnaam, jaar, straat | nee | L | O |
| regiosgroenbeheer, swf_bomen_wensen, swf_bgt_waterdeel, swf_ontmoetingsplaatsen, swf_cbs_buurten | gebieden en objecten | deels (buurten) | L | O |
| t_bro_bodemkaart_simpel_swf | bodemsoort | deels | L | O |
| welstandsgebieden_buitengebied_per_buurt | welstand per buurt | ja | L | – |
| HR_Onderwijs_SWF | handelsnaam, SBI, vestigings- en correspondentieadres | nee | M (eenmanszaken) | T |
| swf_gisvg_vergunning, swf_gisvg_document_nw1 | vergunning, status, tekst, document-url | nee | M | T |
| swf_vik:swf_vik2_vergunningen | zaaktype, zaakomschrijving, toelichting, status, besluit, zaak-url | nee | **H** | T |
| swf_kadaster:gv_grootgrond_swf | naam rechthebbende, aard recht, perceel | ja (`swf-laag-grootgrondbezit`, beperkt) | **H** | T |
| swf_kadaster:brk_percelen | perceelgeometrie | nee | L | L (Kadaster/PDOK is bron) |
| v_graffoto | foto per graf | nee | **H** | niet |

**Aandachtspunt voor de bronhouder:** de lagen met AVG H en M zijn nu zonder login via WFS op te vragen. Controleer of dat zo bedoeld is.

## Vergelijking met D-OmniTwin

- **WFS-adapter:** bestaat (`src/omnitwin/bronadapters/__init__.py`, adapter `wfs`). `geo.sudwestfryslan.nl` staat niet in `TOEGESTANE_DOMEINEN`; tijdelijk kan het via `OMNITWIN_BRON_DOMEINEN`.
- **Al aanwezig:**
  - De SWF-lagen in `usecases/swf-kaartlagen` en `usecases/swf-gebiedsindelingen` komen uit de projectmap van de gebiedsmonitor (licentie onbekend, toegang beperkt), niet uit de GeoServer.
  - Overlap: coördinatorgebieden, welstand per buurt, afstand tot koelte, grootgrondbezit.
  - Externe PDOK-lagen: RCE-monumenten en beschermde gezichten, BRO-bodemkaart.
- **Aanbieden:** pg_featureserv (OGC API Features) en de DCAT-catalogus bestaan.

## Aantallen

- data.overheid.nl: 6 datasets; 5 met geodata, alle 6 CC0.
- Geoportaal: 29 lagen; 11 met zoeken, 7 met download, 23 met klik-info, 15 met tooltip.
- GeoServer: 45 WFS-lagen; 17 portaallagen hebben een WFS-equivalent (3 bij benadering), 28 WFS-lagen staan niet in het portaal.
- Overlap data.overheid.nl en portaal: 5.
- Al (deels) in D-OmniTwin: 9 (gemeentegrens, welstand, ondergrond, rijksmonumenten, rijks beschermde gezichten, coördinatorgebieden, afstand tot koelte, grootgrondbezit, buurten).
- AVG-toets nodig: 8 lagen (graven, grafoto, coördinatoren, accountmanagers, grootgrond, VIK-vergunningen, GIS-vergunningen, HR-onderwijs).

## Thema's (voor de bron-datasets)

1. **Erfgoed en welstand:** monumenten gemeentelijk, beschermde gezichten gemeentelijk, welstandsgebieden, welstandsroute.
2. **Groen en bomen:** bomen en winterkap, groenclusters, beschermde boomstructuren, bebouwingscontour houtkap, regio's groenbeheer, bomenwensen.
3. **Beheer openbare ruimte:** onderhoud wegen/riool/groen/integraal, strooiroutes, onkruidbestrijding, kade-inspecties.
4. **Voorzieningen:** sport, hondentoiletten, losloopgebieden, begraafplaatsen, standplaatsen, ligplaatsen, ontmoetingsplaatsen, laadpalen.
5. **Gebieden en contact:** coördinatoren, accountmanagers, parkeerzones (na AVG-toets).
6. **Klimaat en ondergrond:** wateroverlast, koelte, bodem, bijzondere omstandigheden ondergrond, geurcirkels.

De werkpakketten op functionaliteit staan in de [functionele beschrijving](../specificaties/functionele-beschrijving-geoportaal-swf.md#werkpakketten-voorstel-voor-de-mijlpaal).

## Niet opgehaald

- **De UI zelf:** niet in de browser bekeken. De functies komen uit `index.html`, `js/main.js`, `map.config.json` en de portaal-API.
- **Gegevens van de Afvalkalender:** niet gevonden (geen distributie).
- **Licenties van de lagen die niet op data.overheid.nl staan:** nergens vermeld.
- **Attributen van de portaal-only-lagen** (standplaatsen, monumenten, parkeerzones enz.): niet opgehaald. Er staan alleen de velden die het portaal toont; er is geen WFS.
- **Het aantal objecten per laag:** niet geteld.

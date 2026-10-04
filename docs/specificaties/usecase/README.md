# D-OmniTwin Use Case Specificatie 1.0

- **Versie:** 1.0
- **Status:** voorgesteld ([ADR 0006](../../2-architectuur/adr/0006-usecase-als-declaratieve-app.md)); wordt vastgesteld met die ADR
- **Datum:** 2026-10-02
- **Issue:** https://github.com/TLaan/D-OmniTwin/issues/227
- **Schema's (normatief):** [`1.0/usecase.schema.json`](1.0/usecase.schema.json) (manifest), [`1.0/dataset.schema.json`](1.0/dataset.schema.json) (dataset), [`1.0/bewijs.schema.json`](1.0/bewijs.schema.json) (bewijsverslag)
- **Referentie-implementatie:** de uitvoerder `python -m omnitwin.usecases` ([`src/omnitwin/usecases.py`](../../../src/omnitwin/usecases.py)), met [`src/omnitwin/bronadapters/`](../../../src/omnitwin/bronadapters/__init__.py) en [`src/omnitwin/laden/`](../../../src/omnitwin/laden/registratie.py)

**Kern:** een use case is een **declaratieve app** voor D-OmniTwin. Hij staat in één map `usecases/<naam>/`, heeft een manifest `usecase.json` met een eigen versie, en beschrijft welke data hij nodig heeft, waar die vandaan komt, wie wat mag, hoe je toetst dat hij werkt en hoe het bewijs eruitziet. Hij bevat **geen code**: alle logica zit in de kern (bronadapters, vaste bewerkingen, laad-API). Deze specificatie is het contract tussen wie een use case schrijft en wie hem uitvoert, zoals een OpenAPI-specificatie dat is voor een API.

## Inhoud

1. [Doel en reikwijdte](#1-doel-en-reikwijdte)
2. [Normatieve termen](#2-normatieve-termen)
3. [Begrippen](#3-begrippen)
4. [Structuur van een use case](#4-structuur-van-een-use-case)
5. [Manifest](#5-manifest)
6. [Datasets](#6-datasets)
7. [Bronnen en adapters](#7-bronnen-en-adapters)
8. [Bewerkingen](#8-bewerkingen)
9. [Afhankelijkheden](#9-afhankelijkheden)
10. [Actoren en rechten](#10-actoren-en-rechten)
11. [Controles](#11-controles)
12. [Bewijs](#12-bewijs)
13. [Levenscyclus en status](#13-levenscyclus-en-status)
14. [Uitvoerder](#14-uitvoerder)
15. [Beveiliging](#15-beveiliging)
16. [Versiebeheer](#16-versiebeheer)
17. [Compatibiliteit](#17-compatibiliteit)
18. [Voorbeelden](#18-voorbeelden)
19. [Wijzigingslog](#19-wijzigingslog)

## 1. Doel en reikwijdte

Deze specificatie legt vast:

- hoe een use case is opgebouwd (map, bestanden, manifest, datasets);
- wat elk veld betekent en welke waarden zijn toegestaan;
- hoe een uitvoerder een use case controleert, installeert, test, van bewijs voorziet en opruimt;
- welke regels gelden voor bronnen, afhankelijkheden, actoren, rechten, levenscyclus en beveiliging;
- hoe de use case zelf en deze specificatie worden geversioneerd.

Ze geldt voor alle use cases in `usecases/` van deze repository en voor use cases van buiten (andere gemeenten, andere D-OmniTwin-installaties), zodra die worden ondersteund.

Buiten de reikwijdte: de laad-API zelf (registratie, leveringen, profielen; zie [`docs/api/laden/`](../../api/laden/README.md) en [ADR 0004](../../2-architectuur/adr/0004-een-ingang-voor-vullen.md)), de inhoud van de profielen ([`docs/api/laden/profielen/`](../../api/laden/profielen/README.md)) en de werking van viewer, Kompas en chat.

**Rangorde.** Bij strijd tussen bronnen geldt: (1) deze specificatie, (2) de JSON-schema's in `1.0/`, (3) de uitvoerder. Een verschil tussen specificatie en schema of uitvoerder is een fout in schema of uitvoerder, behalve waar deze specificatie iets als *gereserveerd* markeert.

**Gereserveerd.** Een onderdeel dat als *gereserveerd* is gemarkeerd, is gedefinieerd (een use case MAG het al gebruiken en het schema valideert het), maar de uitvoerder voert het nog niet uit. Het issue erbij zegt wanneer wel.

## 2. Normatieve termen

De woorden **MOET**, **MOET NIET**, **MAG**, **AANBEVOLEN** en **NIET AANBEVOLEN** hebben de betekenis van RFC 2119 (https://www.rfc-editor.org/rfc/rfc2119) en RFC 8174 (https://www.rfc-editor.org/rfc/rfc8174), en alleen als ze in hoofdletters staan:

| Term | RFC 2119 | Betekenis |
|---|---|---|
| **MOET** | MUST, REQUIRED, SHALL | absolute eis; anders voldoet de use case of uitvoerder niet |
| **MOET NIET** | MUST NOT, SHALL NOT | absoluut verbod |
| **AANBEVOLEN** | SHOULD, RECOMMENDED | eis, tenzij er een goede, gedocumenteerde reden is om af te wijken |
| **NIET AANBEVOLEN** | SHOULD NOT, NOT RECOMMENDED | verbod, tenzij er een goede, gedocumenteerde reden is |
| **MAG** | MAY, OPTIONAL | echt optioneel |

## 3. Begrippen

| Begrip | Betekenis |
|---|---|
| **use case** | een vraag van een gebruiker, met de data, inrichting, controles en het bewijs om hem te beantwoorden; als map `usecases/<naam>/` een installeerbare app |
| **manifest** | `usecases/<naam>/usecase.json`: identiteit, versie, afhankelijkheden, actoren, rechten, datasets, controles, bewijs |
| **dataset** | een gegevensverzameling die de use case via de laad-API registreert en levert; beschreven in `datasets/<id>.json` |
| **registratie** | het deel van `datasets/<id>.json` dat naar `POST /api/laden/v1/datasets` gaat: DCAT-beschrijving plus laadprofiel |
| **levering** | één volledige snapshot van een dataset, gemaakt door de uitvoerder uit de bron (GeoPackage, Data Package of `swf-json`) |
| **profiel** | het contract van een levering in de laad-API: `waarnemingen`, `definities`, `gebiedsindeling`, `kaartlaag` (en `kompasprofiel` en `externe-kaartlagen` via beheer) |
| **bron** | waar de data vandaan komt: een openbare internetbron, een interne export of een statisch bestand in de use case |
| **bronadapter** | code in de kern die één soort bron leest (`src/omnitwin/bronadapters/`) |
| **bewerking** | een stap uit een vaste lijst die records omzet (hernoemen, filteren, koppelen, …), zonder expressies |
| **actor** | een gebruiker of machineclient met rollen die de use case nodig heeft |
| **controle** | een toetsbare bewering over de uitkomst (aantal, API-antwoord, afkeuring, …) |
| **bewijs** | screenshots en een verslag (`bewijs.json`) die laten zien dat de use case werkt |
| **uitvoerder** | het programma dat use cases leest en uitvoert: `python -m omnitwin.usecases` |
| **installatie** | een draaiende D-OmniTwin (stack) waartegen de uitvoerder installeert en test |
| **verouderde vorm** | de manifesten van de demopakketten van vóór 0.3.0 (`persona`, `data`, `inrichting`, `ai_zoekvraag`, `verwacht`) |
| **volledige vorm** | een manifest met het veld `datasets` (ook als dat leeg is) |

## 4. Structuur van een use case

```
usecases/<naam>/
├── usecase.json          manifest (MOET)
├── README.md             vraag, gebruiker, stappen, acceptatiecriteria, bewijs, bekende afwijkingen (MOET)
├── datasets/<id>.json    per dataset: registratie + bron + bewerkingen + levering (MOET per dataset)
├── *.json, *.csv         kleine statische bestanden: mapping, sjabloon, Table Schema (MAG)
└── bewijs/               bewijsverslag en compacte screenshots (zie 12)
```

Regels:

1. De mapnaam MOET gelijk zijn aan `naam` in het manifest en MOET voldoen aan `^[a-z0-9]+(-[a-z0-9]+)*$`.
2. **Allowlist van bestandstypen.** Buiten `bewijs/` MOGEN alleen `.json`, `.md` en `.csv` staan; in `data/` ook `.gpkg` (geometrie die niet online te downloaden is, met `herkomst.json` ernaast). In `bewijs/` MOGEN alleen `.json`, `.md`, `.webp`, `.png`, `.jpg` en `.jpeg` staan; nieuwe afbeeldingen MOETEN WebP zijn. Elk ander bestand (ook zonder extensie) is een fout. De uitvoerder (`bestandsfouten`) en de unittest `tests/test_usecases_uitvoerder.py` dwingen dit af.
3. Een use case MOET NIET code of uitvoerbare bestanden bevatten: geen scripts, geen notebooks, geen SQL, geen expressies in JSON. Er zijn geen uitzonderingen (de laatste, `hittestress/maak_data.py`, is sinds https://github.com/TLaan/D-OmniTwin/issues/236 de kernadapter `wcs-zonaal`).
4. Statische bestanden MOETEN klein zijn (richtlijn: samen ≤ 1 MB) en MOETEN NIET openbare brondata bevatten die ook te downloaden is (zie 7).
5. De README van de use case MOET de vraag, de gebruiker, de stappen, de acceptatiecriteria en de bronnen beschrijven, en AANBEVOLEN de screenshots uit `bewijs/` tonen.
6. Na elke nieuwe of gewijzigde use case MOET de index in [`usecases/README.md`](../../../usecases/README.md#index) bijgewerkt zijn (`python -m omnitwin.usecases index`).

## 5. Manifest

Het manifest `usecase.json` is een JSON-object (UTF-8) dat MOET voldoen aan [`1.0/usecase.schema.json`](1.0/usecase.schema.json). Onbekende velden zijn niet toegestaan (`additionalProperties: false`), ook niet in `datasets[]`, `controles[]`, `actoren[]` en `bewijs`. Velden die met `_` beginnen zijn voor de uitvoerder en MOETEN NIET in het bestand staan.

### 5.1 Velden

| Veld | Type | Verplicht | Betekenis |
|---|---|---|---|
| `$schema` | string (URI) | nee | de `$id` van het schema, voor editors; de uitvoerder kijkt naar `specificatie` |
| `specificatie` | string, `"1.0"` | **ja** | versie van deze specificatie waaraan het manifest voldoet (zie 16.2) |
| `naam` | string, `^[a-z0-9]+(-[a-z0-9]+)*$` | **ja** | identiteit; gelijk aan de mapnaam; verandert nooit |
| `id` | string, `^TC-[0-9]{2}-[0-9]{3}$` | nee | testcase-id (`docs/testcases`), uniek over alle use cases |
| `versie` | string, SemVer 2.0.0 | **ja** | versie van de use case, start `0.1.0` (zie 16.1) |
| `titel` | string, ≥ 3 tekens | **ja** | korte titel voor index en galerij |
| `vraag` | string | volledige vorm | de vraag in de woorden van de gebruiker |
| `gebruiker` | string | volledige vorm | functionele rol van de gebruiker, nooit een persoon |
| `status` | `ontwerp` \| `actief` \| `verouderd` | volledige vorm | levenscyclus (zie 13) |
| `veroudering` | object | bij `verouderd` | `sinds`, `verwijderen_na`, `vervangen_door`, `reden` (zie 13) |
| `afhankelijk_van` | array | volledige vorm | andere use cases die eerst geïnstalleerd moeten zijn (zie 9) |
| `actoren` | array van actor | nee | gebruikers en machineclients met rollen (zie 10) |
| `rechten` | array van string | volledige vorm | Keycloak-rollen die de use case nodig heeft (zie 10) |
| `datasets` | array van dataset | volledige vorm | datasets die de use case registreert en levert (zie 6) |
| `controles` | array van controle | volledige vorm | toetsbare controles (zie 11) |
| `bewijs` | object | nee; AANBEVOLEN bij `actief` | `stappen` voor de screenshots (zie 12) |
| `bekende_afwijkingen` | array van string | nee | bekende verschillen met de verwachting of de bron, met reden |
| `persona` | object | verouderde vorm | rol, vraag en besluit van de gebruiker |
| `data` | object | verouderde vorm | gebiedstype, focusgebied, gebieden, indicatoren met richting |
| `inrichting` | object | verouderde vorm | Kompas-configuratie en chatscenario |
| `ai_zoekvraag` | string | verouderde vorm | zoekvraag voor de semantische zoektest |
| `verwacht` | object | verouderde vorm | verwachte uitkomst van de chat |

"Volledige vorm" betekent: verplicht zodra het manifest het veld `datasets` heeft. Dat dwingt de uitvoerder af (`VOLLEDIG` in `usecases.py`). Een nieuwe use case MOET de volledige vorm gebruiken; `datasets` MAG leeg zijn (bijvoorbeeld bij een acceptatie-use case die alleen afhankelijkheden bundelt, zoals `swf-gebiedsmonitor`).

### 5.2 Verouderde vorm

De vijf demopakketten van vóór 0.3.0 gebruiken `persona`, `data`, `inrichting`, `ai_zoekvraag` en `verwacht`, met `data/waarden.csv`, en laden via `init_data/scripts/laad_usecase.py`. Deze vorm is in 1.x toegestaan voor bestaande use cases, MOET NIET gebruikt worden voor nieuwe use cases en vervalt in 2.0. De velden `specificatie`, `naam`, `versie` en `titel` zijn ook in de verouderde vorm verplicht.

## 6. Datasets

Een dataset staat op twee plekken: een verwijzing in het manifest (`datasets[]`) en de beschrijving in `datasets/<id>.json`.

### 6.1 Verwijzing in het manifest

| Veld | Type | Verplicht | Betekenis |
|---|---|---|---|
| `id` | string, `^[a-z0-9]+(-[a-z0-9]+)*$`, 3–63 tekens | **ja** | `datasetId` in de laad-API; gelijk aan `id` in `datasets/<id>.json` |
| `route` | `laden` \| `compat` \| `beheer` | **ja** | `laden`: `POST /api/laden/v1/datasets/{id}/leveringen`; `compat`: de compat-ingang van adapter `swf-monitor-v1`; `beheer`: `/api/beheer/v1` (inrichting, geen dataset in de laad-API) |
| `registratie` | string, `^datasets/[a-z0-9-]+\.json$` | **ja** | pad naar het datasetbestand |
| `profiel` | `waarnemingen` \| `definities` \| `gebiedsindeling` \| `kaartlaag` \| `kompasprofiel` \| `externe-kaartlagen` | nee | profiel van de levering; `kompasprofiel` en `externe-kaartlagen` alleen met route `beheer` (in-process: `omnitwin.laden.beheer`) |
| `beheerpad` | string | bij route `beheer` | pad in `/api/beheer/v1`; de uitvoerder doet `PUT <beheerpad>/<id>` |
| `rol` | string | nee | Keycloak-rol van de leverende client, bijv. `dataset:<id>:laden` |
| `client` | string | nee | functionele naam van de leverende machineclient (AANBEVOLEN: de `naam` van een actor) |
| `prioriteit` | `Must` \| `Should` \| `Could` \| `uitgesteld` | nee | MoSCoW-prioriteit binnen de use case |
| `bron` | string | nee | korte omschrijving van de bron, voor mensen; de uitvoerbare bron staat in het datasetbestand |
| `verwacht` | object | nee | verwachte aantallen en uitkomst, voor mensen; toetsbaar maken met `controles` |

Een dataset die in meer use cases voorkomt, MOET overal dezelfde registratie hebben (unittest `test_zelfde_dataset_zelfde_registratie`).

### 6.2 Het datasetbestand `datasets/<id>.json`

Het bestand MOET voldoen aan [`1.0/dataset.schema.json`](1.0/dataset.schema.json). Het bevat de registratie voor de laad-API en daarnaast vier blokken die alleen voor de uitvoerder zijn en **niet** naar de API gaan (`bron`, `bewerkingen`, `levering`, `varianten`; ook `$schema` niet).

| Veld | Type | Verplicht | Betekenis |
|---|---|---|---|
| `$schema` | string | nee | voor editors; gaat niet naar de API |
| `id` | string, zoals 6.1 | **ja** | `datasetId` |
| `bronId` | string | nee | de bron (dataproduct, ADR 0002) waartoe de dataset hoort |
| `beschrijving` | object (JSON-LD) | bij route `laden`/`compat` | DCAT-AP-NL 3, voor geodata GeoDCAT-AP 3 (zie 6.3) |
| `laadprofiel` | object | bij route `laden`/`compat` | profiel, doel, sleutel, vervangbereik, n-drempel, plausibiliteit; schema `Laadprofiel` in [`openapi.yaml`](../../api/laden/openapi.yaml) |
| `bron` | object | **ja** | welke bronadapter met welke parameters (zie 7) |
| `bewerkingen` | array | nee | declaratieve bewerkingen in volgorde (zie 8) |
| `levering` | object | **ja** | hoe de levering wordt geschreven (zie 6.4) |
| `varianten` | object | nee | varianten van de levering (zie 6.5) |

De registratie (`id`, `bronId`, `beschrijving`, `laadprofiel`) MOET bij route `laden` en `compat` geldig zijn volgens `DatasetRegistratie` in [`docs/api/laden/openapi.yaml`](../../api/laden/openapi.yaml) plus de profielregels (`omnitwin.laden.registratie.valideer_registratie`). Daarmee is de laad-API-specificatie normatief voor dit deel; deze specificatie herhaalt die velden niet.

### 6.3 Beschrijving en herkomst (DCAT)

De `beschrijving` MOET de herkomst vastleggen: `dct:source` (de bron-URL, of voor een interne bron een omschrijving zonder hostnaam), `dct:license` (bij open data), `dct:publisher`, `dct:accessRights` en `dcat:contactPoint` (functioneel, geen persoonsnaam). Voor geodata AANBEVOLEN: `dct:conformsTo` met het CRS.

### 6.4 Levering

| Veld | Type | Verplicht | Betekenis |
|---|---|---|---|
| `formaat` | `datapackage` \| `geopackage` \| `swf-json` | **ja** | Frictionless Data Package (zip), GeoPackage 1.4, of het JSON-formaat van de huidige SWF-push (route `compat`) |
| `bestand` | string | nee | bestandsnaam van de levering |
| `geometrie` | `Point` \| `MultiPoint` \| `LineString` \| `MultiLineString` \| `Polygon` \| `MultiPolygon` | nee | geometrietype in de GeoPackage |
| `schema` | object | nee | `{resource: pad}`: eigen Table Schema per resource (een `.json` in de use case), voor wat geen laad-API-profiel is (bijv. kompasprofiel) |

De uitvoerder valideert elke levering tegen het profiel (Table Schema met frictionless, GeoPackage met fiona) voordat hij hem aanbiedt.

### 6.5 Varianten

`varianten` is een object `{naam: {…}}`. Een variant heeft deze velden (alle optioneel):

| Veld | Type | Betekenis |
|---|---|---|
| `omschrijving` | string | voor mensen |
| `sla_over` | array van stap-id's | de bewerkingen met die `id` niet uitvoeren, bijvoorbeeld `met-fouten` om een afkeuring te toetsen (controle `afkeuring`). Elke id MOET bestaan in de bewerkingen van de variant |
| `bron` | object | een andere bron (een `bron`-blok, zie 7.2), bijvoorbeeld de echte interne bron naast demodata |
| `bewerkingen` | array | de bewerkingen bij die bron (in plaats van die van de dataset) |
| `beschrijving` | object | DCAT-velden die bij deze variant anders zijn (bijv. `dct:type`, `dct:description`, `dct:accessRights`); gaan mee in `dcat.jsonld` van de levering en in de registratie |
| `als_beschikbaar` | boolean | zonder `--variant` gebruikt de uitvoerder eerst deze variant; is zijn bron hier niet beschikbaar (variabele niet gezet, bestand weg), dan de standaardbron |

**Demodata als plaatsvervanger voor een interne bron** (https://github.com/TLaan/D-OmniTwin/issues/236): de standaardbron is de demodata (bijv. `lokaal-bestand` onder `${REPO}`), met in de beschrijving `dct:type` `demodata`, een `dct:description` die zegt dat het een plaatsvervanger is en voor welke interne bron (functionele naam, ook in `prov:wasDerivedFrom`), en per waarde een `bron` die met `DEMODATA` begint (zo ziet de gebruiker het in de API en de viewer). Een variant `intern` met `als_beschikbaar: true` noemt de echte interne bron (bijv. `swf-dump` onder `SWF_DUMP_DIR`); die data komt nooit in de repository.

## 7. Bronnen en adapters

### 7.1 Regels

1. **Openbare internetbronnen** (CBS, PDOK, BAG, RIVM, Klimaateffectatlas) MOETEN NIET in de repository staan. De use case beschrijft de bron; de adapter downloadt hem bij `controleer`, `installeer` en `test`, met een cache in `$DATA_CACHE`.
2. Downloads MOETEN via https gaan, naar een domein uit de allowlist `TOEGESTANE_DOMEINEN` in `omnitwin.bronadapters` (nu `opendata.cbs.nl`, `datasets.cbs.nl`, `www.cbs.nl`, `dataderden.cbs.nl`, `service.pdok.nl`, `api.pdok.nl`, `data.rivm.nl`, `www.klimaateffectatlas.nl`, `klimaateffectatlas.nl`). Een installatie MAG domeinen toevoegen met `OMNITWIN_BRON_DOMEINEN` (kommagescheiden). Een nieuw domein in de standaardlijst gaat via een PR.
3. Bij een download van een vast bestand is `sha256` AANBEVOLEN; klopt de checksum niet, dan faalt de dataset.
4. **Interne bronnen** (exports, dumps van de bronhouder) MOETEN via een omgevingsvariabele uit de allowlist `TOEGESTANE_MAPPEN` lopen: `SWF_DUMP_DIR`, `SWF_DOCS_DIR`, `SWF_GEO_DIR`, `SWF_DB_DUMP`, `SWF_EXPORT_DIR` (export van een andere D-OmniTwin-installatie, bijv. de lokale database voor de eerste vulling), `DATA_CACHE`, en `REPO` (de repository zelf). Een pad MOET de vorm `${VAR}/…` hebben en MOET NIET buiten die map wijzen (`..`, symlinks).
5. Ontbreekt een bron (variabele niet gezet, bestand weg, geen netwerk), dan is de dataset *overgeslagen*, geen fout.
6. De herkomst MOET in de DCAT-beschrijving staan (zie 6.3).
7. **Een nieuwe soort bron is een nieuwe kernadapter**: code in `src/omnitwin/bronadapters/`, via een PR met unittests, en een minor-versie van deze specificatie (nieuwe waarde voor `adapter` in het schema).

### 7.2 Adapters (specificatie 1.0)

Elke `bron` heeft `adapter` en MAG `omschrijving` (voor mensen) en `tabel` (naam van de tabel in het resultaat) hebben. Verder per adapter:

| `adapter` | Wat | Parameters (vet = verplicht) |
|---|---|---|
| `swf-dump` | export van de huidige SWF-gebiedsmonitor onder `SWF_DUMP_DIR` | **`export`** (`definities` \| `waarden`) |
| `cbs-odata` | CBS Kerncijfers wijken en buurten via OData | `gemeenten` (viercijferige codes), `jaren` (array van integer) |
| `wfs` | WFS 2.0 (bijv. PDOK), in EPSG:28992 | **`url`** (https), **`laag`**, `bbox` (array van 4 getallen), `pagina` (paginagrootte) |
| `download` | één bestand via https | **`url`** (https), `sha256` (64 hex), `formaat` (`gpkg` \| `geojson` \| `csv` \| `json`), `laag`, `crs` (EPSG-code als het bestand hem niet noemt; standaard 4326) |
| `lokaal-bestand` | een bestand onder een toegestane map | **`pad`** (`${VAR}/…`), `formaat`, `laag`, `crs` |
| `usecase-bestand` | een statisch `.json`- of `.csv`-bestand in de use case | **`pad`** (relatief, zonder `..`) |
| `cbs-statline` | een StatLine-tabel (CBS, of RIVM en Politie via `dataderden.cbs.nl`), uitgepakt: één record per regio, periode, dimensiewaarden en kolom, met `gebied_code`, `jaar`, `periode`, `kolom`, `waarde` en de gefilterde dimensies | **`url`** (`https://<host>/ODataFeed/odata/<tabel>`), **`kolommen`** (Topic-keys), `regio` (regio-dimensie, standaard `WijkenEnBuurten`), `gemeenten` of `gebieden`, `regio_prefix` (`BU` \| `WK` \| `GM`, standaard `BU`), `filter` ({dimensie: key of [keys]}), `jaren` |
| `wcs-zonaal` | gemiddelde van een WCS-raster (OGC WCS 2.0.1, GeoTIFF in EPSG:28992) per gebied, over de cellen met het middelpunt in het gebied; record `gebied_code`, `waarde`, `cellen` | **`url`** (https), **`coverage`**, **`gebieden`** ({**`bron`**, `bewerkingen`, `sleutel`}: de gebieden als bron-blok, `sleutel` standaard `code`), `celgrootte` (m, standaard 10), `nodata` (standaard -9999), `nodata_als` (nodata telt als deze waarde), `decimalen`, `max_cellen` |

Elke adapter levert tabellen met records; een geometrie staat altijd in EPSG:28992.

## 8. Bewerkingen

`bewerkingen` is een lijst van objecten. Elk object heeft **precies één bewerkingssleutel** uit de vaste lijst hieronder, en MAG daarnaast `id` (naam van de stap, voor `varianten`) en `tabel` (alleen op die tabel) hebben. Er zijn geen expressies, geen `eval` en geen attribuuttoegang: `sjabloon` vervangt alleen `{veld}`-plaatshouders.

| Bewerking | Parameters | Wat |
|---|---|---|
| `hernoem` | `{oud: nieuw}` | velden hernoemen |
| `behoud` | `[veld]` | alleen deze velden (plus `geometry`) |
| `verwijder` | `[veld]` | velden weg |
| `constant` | `{veld: waarde}` | veld met een vaste waarde |
| `kopieer` | `{van, naar}` | waarde kopiëren |
| `tekst`, `getal` | `[veld]` | type omzetten |
| `waarde_map` | `{veld, map, naar?, standaard?}` | waarde vertalen via een tabel |
| `koppel` | `{sleutel, bron, op, velden, tabel?, verplicht?, reden?, normaliseer?, bewerkingen?}` | velden overnemen uit een andere bron; `bewerkingen` eerst op die bron (bijv. `binnen`) |
| `afwijzen` | voorwaarde + `reden` | regels die voldoen eruit, geteld onder de reden |
| `filter` | voorwaarde | alleen regels die voldoen |
| `jaar_uit_datum` | `{veld, jaar?, peildatum?}` | `JJJJ-01-01` → jaar; ongeldig → afgewezen (`jaar-ongeldig`) |
| `jaar_naar_datum` | `{veld, naar}` | jaar → `JJJJ-01-01` |
| `iso_datumtijd` | `[veld]` | `JJJJ-MM-DD HH:MM` → ISO 8601 |
| `prefix` | `{veld, prefix, als?}` | prefix voor codes die niet landelijk uniek zijn |
| `sjabloon` | `{naar, sjabloon}` | veld uit andere velden met `{veld}` |
| `deel` | `{veld, start, eind?, naar}` | deel van een tekst |
| `snake_case` | `true` | veldnamen naar snake_case |
| `nummer` | `{naar, start?}` | volgnummer als sleutel |
| `multipolygon` | `true` | geometrie naar geldige MultiPolygon |
| `geometrietype` | `[type]` | alleen deze geometrietypen |
| `binnen` | `{bron, bewerkingen?}` | alleen features binnen een andere bron |
| `splits_op` | `{bron, bewerkingen?, veld, binnen, buiten}` | feature opdelen in binnen en buiten een andere bron |
| `ontdubbel` | `{veld, sleutel, houd, zet?, achtervoegsel?, normaliseer?, reden?}` | dezelfde `veld` (bijv. naam) met een andere `sleutel` (bijv. uuid): de voorkeur uit `houd` (`{waarde: sleutel of begin daarvan}`) blijft, de andere krijgen `zet` en `achtervoegsel`; geteld onder `reden`, zonder voorkeur onder `<reden>-zonder-voorkeur` (ongewijzigd) |

Een **voorwaarde** is `{"veld": …, <toets>: waarde}` met toets `gelijk`, `niet_gelijk`, `in`, `niet_in`, `leeg`, `begint_met`, `niet_begint_met`, `kleiner_dan` of `groter_dan`. Een geneste `bron` (in `koppel`, `binnen`, `splits_op`) volgt dezelfde regels als in 7. De precieze semantiek staat in de docstring van [`bewerkingen.py`](../../../src/omnitwin/bronadapters/bewerkingen.py). Een nieuwe bewerking gaat via een PR met tests en is een minor-wijziging van deze specificatie.

De uitvoerder telt per reden hoeveel regels een bewerking afwijst of repareert (het bewerkingsrapport); controle `bewerking` toetst die tellingen.

## 9. Afhankelijkheden

`afhankelijk_van` noemt use cases die eerst geïnstalleerd moeten zijn. Elk element is:

- een naam: `"swf-definities"`; of
- een object `{"naam", "versie", "optioneel"}`:
  - `naam` (verplicht): mapnaam van de andere use case, nooit een pad;
  - `versie`: versie-eis, één of meer delen gescheiden door komma's, elk `>=`, `<=`, `>`, `<`, `==` of `=` gevolgd door een versie (zonder operator: `==`). Alle delen moeten kloppen, bijv. `>=0.1.0,<1.0.0`. Alleen de getallen tellen; een pre-release-achtervoegsel wordt genegeerd;
  - `optioneel`: `true` als de use case ook werkt zonder (bijv. via een eigen route); een overgeslagen optionele afhankelijkheid blokkeert niet.

Regels voor de uitvoerder:

1. Hij MOET de afhankelijkheden in **topologische volgorde** installeren (diepte eerst, in de volgorde van `afhankelijk_van`), elke use case één keer.
2. Een onbekende naam, een **cyclus** of een versie die niet aan de eis voldoet, MOET een fout zijn (exitcode 2), voordat er iets wordt geïnstalleerd.
3. Een use case met status `ontwerp`, en alles wat er niet-optioneel van afhangt, wordt bij `installeer` overgeslagen met een melding (zie 13).

**Extern (gereserveerd).** Een afhankelijkheid van buiten deze repository heeft de vorm `{"naam", "bron": "<absolute URL van een git-repository of D-OmniTwin-installatie>", "versie": "<vaste versie>"}`. `bron` MOET een absolute URL zijn en `versie` MOET één vaste versie of tag zijn (geen bereik). De uitvoerder ondersteunt dit nog niet en meldt een fout. Verificatie (checksum of handtekening) wordt onderdeel van een volgende versie.

## 10. Actoren en rechten

### 10.1 Actoren

`actoren` declareert wie de use case gebruikt: mensen en machines, met hun rollen. Een use case MOET NIET wachtwoorden, client secrets, tokens of andere geheimen bevatten.

| Veld | Type | Verplicht | Betekenis |
|---|---|---|---|
| `naam` | string, zoals `naam` van een use case | **ja** | functionele naam binnen de use case (`beheerder`, `etl-swf`, `lezer`) |
| `soort` | `gebruiker` \| `machineclient` | **ja** | een mens die inlogt, of een client met client credentials |
| `rollen` | array van string | **ja** | Keycloak-rollen: realm-rol (`beheerder`, `lezer`) of client-rol op `omnitwin-api` (`dataset:<id>:laden`, `datasets:laden`) |
| `omschrijving` | string | nee | wie of wat de actor is |

Een rol zonder `:` is een realm-rol en MOET in de realm bestaan; een rol met `:` is een client-rol op `omnitwin-api`. De `naam` van een actor MOET uniek zijn binnen de use case. AANBEVOLEN: `client` in `datasets[]` is de naam van de machineclient-actor die de dataset levert, en die actor heeft alleen `dataset:<id>:laden` voor zijn eigen datasets.

Testaccounts (https://github.com/TLaan/D-OmniTwin/issues/223):

- de uitvoerder MAG actoren als testaccount aanmaken, **alleen in test en dev**: met `installeer --testaccounts` of `test --testaccounts`, alleen als `OMNITWIN_TESTACCOUNTS=1` en niet `OMNITWIN_OMGEVING=productie`; anders weigert hij (exitcode 2);
- hij doet dat voor de use case en zijn afhankelijkheden, via de admin-API van Keycloak in de realm van de installatie; bestaande testaccounts van dezelfde use case worden eerst verwijderd;
- naam `uc-<usecase>-<actor>`: een gebruiker met een wachtwoord, of een machineclient (client credentials) met een secret; voor de tokens van de gebruikers één public client `uc-<usecase>--login` met alleen de wachtwoordgrant;
- kenmerk: de clients hebben de attributen `omnitwin.usecase` en `omnitwin.testaccount.tot` (levensduur, standaard 24 uur); de gebruikers heten `Testaccount <usecase>`;
- wachtwoorden en secrets worden willekeurig gegenereerd en staan alleen lokaal (`.usecase-accounts.json`, in `.gitignore`); ze MOETEN NIET gelogd of gecommit worden;
- met testaccounts registreert de uitvoerder als de actor met de realm-rol `beheerder`, levert hij als de `client` van de dataset (of de actor met de rol van de dataset), en voert hij controles met `actor` uit als die actor; ontbreekt een passende actor, dan de machineclient uit de omgeving;
- `opruimen <naam>` verwijdert de testaccounts van de use case en zijn afhankelijkheden: alleen accounts met het prefix `uc-<usecase>-` én het kenmerk van die use case;
- in productie wijst een beheerder de rollen toe in Keycloak; de use case laat alleen zien welke nodig zijn.

### 10.2 Rechten

`rechten` somt de Keycloak-rollen op die de use case nodig heeft. Elk element MOET één van deze vormen hebben, optioneel gevolgd door een toelichting tussen haakjes:

- `dataset:<datasetId>:laden`: client-rol op `omnitwin-api` voor één dataset;
- `datasets:laden`: client-rol voor alle datasets;
- `realm-rol <rol>`: realm-rol, bijv. `realm-rol beheerder (registreren)` of `realm-rol lezer`.

In 1.0 is `rechten` documentatie: de uitvoerder en D-OmniTwin dwingen het niet af op basis van het manifest. Wel geldt: elke `rol` in `datasets[]` en elke rol van een actor AANBEVOLEN ook in `rechten`. De betekenis van de rollen staat in de laad-API ([`openapi.yaml`](../../api/laden/openapi.yaml), `securitySchemes`) en ADR 0004, besluit 8.

## 11. Controles

Een controle is een toetsbare bewering. Elke controle heeft `type` en MAG `omschrijving` (wat hij aantoont) en `actor` hebben. `actor` MOET een `naam` uit `actoren` zijn: met testaccounts voert die actor de controle uit, zonder testaccounts de machineclient uit de omgeving. Een controle met `dataset` MOET verwijzen naar een `id` in `datasets[]`, behalve bij `recht`.

### 11.1 Typen

| `type` | Velden | Lokaal (`controleer`) | Tegen een installatie (`test`) |
|---|---|---|---|
| `aantal` | `dataset`, `resource`?, `gelijk` \| `minimaal` \| `maximaal` | telt regels of features in de gemaakte levering (met `resource`: alleen die resource) | `aantallen.gepubliceerd` van de laatste levering; met `resource` alleen lokaal |
| `bewerking` | `dataset`, `reden`, `gelijk` \| `minimaal` \| `maximaal` | telling onder `reden` in het bewerkingsrapport | niet opnieuw (lokaal getoetst) |
| `api` | `pad`, `anoniem`?, `status`?, `minimaal_aantal`?, `verwacht`?, `uuid`?, `gebied`? | alleen tegen een installatie | `GET <pad>` (zonder token bij `anoniem`); HTTP-status MOET `status` zijn (standaard 200); bij `minimaal_aantal` minstens zoveel elementen (`features`, `datasets`, `indicatoren` of de lijst zelf) |
| `afkeuring` | `dataset`, `variant`, `code` | alleen tegen een installatie | levering met de variant aanbieden (route `laden`: `alleenValideren=true`); geslaagd als HTTP 422 met probleemcode `code` ([probleemtypen](../../api/laden/README.md#probleemtypen)); de vorige versie blijft actief |
| `idempotent` | `dataset` | alleen tegen een installatie | dezelfde levering twee keer: dezelfde datasetversie |
| `chat` | `vraag`, `bevat` | alleen tegen een installatie | de assistent beantwoordt `vraag`; het antwoord bevat elke tekst uit `bevat`; *gereserveerd*: nu overgeslagen, aangetoond via bewijs |
| `viewer` | `stap`, `verwacht`, `bevat`?, `gebied`?, `uuid`? | alleen tegen een installatie | de gebruiker doet `stap` en ziet `verwacht`; *gereserveerd*: nu handmatig, aangetoond via bewijs |
| `recht` | `actor`, `actie`, `dataset` (niet bij `registreren`), `toegestaan` | alleen tegen een installatie | alleen met testaccounts, anders overgeslagen: de actor doet `actie` (`registreren`: `POST /api/laden/v1/datasets`; `leveren`: een levering aan `dataset`, route `laden` of `compat`; `lezen`: `GET /api/laden/v1/datasets/{dataset}`) met een ongeldige parameter of body, zodat er niets verandert; geslaagd als het antwoord 403 is bij `toegestaan: false`, en geen 401 of 403 bij `toegestaan: true`. `dataset` MAG een dataset van een andere use case zijn (de ETL-client krijgt 403 op een andere dataset) |

`pad` MOET een pad op de installatie zijn (begint met `/`), zonder host. `gelijk`, `minimaal` en `maximaal` MOGEN gecombineerd worden; alle opgegeven grenzen moeten kloppen. `uuid` (indicator) en `gebied` (gebiedscode, bijv. `BU19000002`) zijn context voor de lezer en voor bewijs. `verwacht` is een vrije beschrijving of waarde. Bij `afkeuring` en `idempotent` is `variant` de naam uit `varianten` van het datasetbestand.

### 11.2 Resultaten en "geslaagd"

Elke controle heeft één resultaat: `ok`, `fout`, `overgeslagen` (bron of functie ontbreekt), of lokaal `alleen-api` (niet zonder installatie te toetsen).

- Een use case is **geldig** als `controleer` geen fouten vindt: het manifest en de datasetbestanden zijn geldig, geen dataset heeft status `fout` en geen lokale controle is `fout`. Overgeslagen is geen fout.
- Een use case is **geslaagd** als `test` tegen een verse installatie geen controle met resultaat `fout` geeft.
- Een use case is **aangetoond** als hij geslaagd is en het bewijs (12) bij de huidige release hoort.

Een use case met status `actief` MOET geldig zijn (unittest), MOET geslaagd zijn bij elke release, en daarbij MOET elke controle van type `aantal`, `bewerking`, `api`, `afkeuring` en `idempotent` het resultaat `ok` hebben, en met `--testaccounts` ook elke controle van type `recht`. `chat`- en `viewer`-controles MOGEN `overgeslagen` zijn zolang de uitvoerder ze niet uitvoert, mits het bewijs ze laat zien.

## 12. Bewijs

Bewijs laat zien dat de use case werkt en wat je krijgt als je hem installeert. Besluiten: https://github.com/TLaan/D-OmniTwin/issues/225.

### 12.1 Bewijsstappen in het manifest

`bewijs.stappen` is een lijst van **2 tot 4** stappen; elke stap levert één scherm `bewijs/<id>.webp`. Stappen zijn declaratief: een vaste actie met parameters, geen selectors of scripts.

| Veld | Type | Verplicht | Betekenis |
|---|---|---|---|
| `id` | string, zoals `naam` | **ja** | naam van de stap en van de afbeelding; stabiel tussen releases |
| `actie` | `open` \| `kaart` \| `kompas` \| `chat` \| `levering` \| `beheer` | **ja** | wat de uitvoerder doet (zie onder) |
| `omschrijving` | string | nee | bijschrift in README en galerij |
| `actor` | string | nee | actor die ingelogd is; zonder actor anoniem |
| `pad` | string, begint met `/` | bij `open`, `beheer` | pagina op de installatie, zonder host |
| `gebied` | string | nee | gebiedscode die geselecteerd wordt (`kaart`, `kompas`) |
| `indicator` | string | nee | indicator-UUID of -naam op de kaart (`kaart`, `kompas`) |
| `profiel` | string | nee | Kompas-profiel (`kompas`) |
| `vraag` | string | bij `chat` | vraag aan de assistent |
| `dataset` | string | bij `levering` | dataset waarvan de leveringsstatus wordt getoond |
| `bevat` | array van string | nee | teksten die zichtbaar moeten zijn; anders is de stap `fout` |

Acties: `open` (pagina openen), `kaart` (viewer met gebied en indicator), `kompas` (Kompas voor een gebied, eventueel een profiel), `chat` (vraag stellen en antwoord tonen), `levering` (status van de laatste levering in beheer), `beheer` (een beheerpagina openen).

Zo voert de referentie-uitvoerder ([`src/omnitwin/usecase_bewijs.py`](../../../src/omnitwin/usecase_bewijs.py)) ze uit, met Playwright in een eigen browsercontext per stap (viewport 1440 × 860, licht thema, zonder animaties):

- `kaart`: gebiedstype CBS Buurten, het gemeentefilter van `gebied` (BU19000002 → Súdwest-Fryslân), de indicator op de kaart en het gebied geselecteerd, via hetzelfde codepad als 'Toon op kaart' in de chat. In beeld: de wijk van een buurt, of de hele gemeente bij een gemeentecode. Het gemeentefilter houdt de kaart klein genoeg voor software-WebGL.
- `kompas`: als `kaart`, dan het Kompas voor het gebied (met `profiel` de Kompas-configuratie met die naam); het venster staat rechts, de kaart links.
- `chat`: de vraag via het invoerveld; zonder taalmodel antwoordt de assistent met de datavraag-route of een scenario. Het antwoord komt in het verslag.
- `levering`: dataset en laatste levering van de laad-API, als statuspagina; daarvoor is een machineclient met leesrecht nodig (`OMNITWIN_CLIENT_ID`, `OMNITWIN_CLIENT_SECRET`).
- `beheer`: inloggen met `ADMIN_USER`/`ADMIN_PASSWORD` tot de testaccounts er zijn (#223).
- Een stap is `fout` als de pagina niet laadt, gebied, indicator of dataset niet gevonden wordt, of een tekst uit `bevat` niet zichtbaar is; het scherm wordt dan toch bewaard.

### 12.2 Bewijsverslag `bewijs/bewijs.json`

De uitvoerder (`bewijs <naam>`) schrijft een verslag dat MOET voldoen aan [`1.0/bewijs.schema.json`](1.0/bewijs.schema.json):

| Veld | Type | Verplicht | Betekenis |
|---|---|---|---|
| `specificatie` | `"1.0"` | **ja** | versie van deze specificatie |
| `naam` | string | **ja** | naam van de use case |
| `versie` | string | **ja** | versie van de use case |
| `omnitwin_versie` | string | **ja** | versie van D-OmniTwin |
| `datum` | date-time | **ja** | moment van maken, met tijdzone |
| `omgeving` | `lokaal` \| `test` \| `acceptatie` | nee | soort omgeving, nooit een hostnaam |
| `ai_aanbieder` | string | nee | AI-aanbieder, of `geen` |
| `geslaagd` | boolean | **ja** | geen controle en geen stap met resultaat `fout` |
| `controles` | array | **ja** | per controle: `type`, `omschrijving`, `resultaat` (`ok` \| `fout` \| `overgeslagen`), `melding` |
| `stappen` | array | **ja** | per stap: `id`, `resultaat` (`ok` \| `fout`), `afbeelding` (`<id>.webp`), `antwoord`, `antwoordtijd_s`, `console_fouten` |
| `leveringen` | array | nee | per dataset: `dataset`, `status`, `datasetversie`, `aantallen` |

Het verslag MOET NIET hostnamen, tokens, wachtwoorden of persoonsgegevens bevatten.

Controles in het verslag: `api` en `aantal` voert `bewijs` uit tegen de installatie (`aantal` en `api` zonder `anoniem` alleen met een machineclient, anders `overgeslagen`); `idempotent` en `afkeuring` maken een levering uit de bron en horen bij `test` (hier `overgeslagen`); `chat` en `viewer` zijn `overgeslagen` en worden met de schermen aangetoond. Een use case waarvan een dataset nog geen levering heeft (bron hier niet beschikbaar, bijv. zonder `SWF_DUMP_DIR`), slaat `bewijs` over; het bestaande bewijs blijft dan staan.

### 12.3 Afbeeldingen, git en release

- Afbeeldingen MOETEN WebP zijn, met een vaste viewport (1440 × 860), **≤ 150 KB** per afbeelding, **maximaal 4** per use case: alleen de belangrijkste schermen.
- Het **compacte bewijs staat in git**: `bewijs/<id>.webp`, `bewijs/bewijs.json` en `bewijs/README.md`. Het wordt **alleen bij een release** opnieuw gemaakt, niet bij elke run, en overschrijft dezelfde bestandsnamen zodat links stabiel blijven.
- Het **volledige bewijs** (originele resolutie, alle tussenstappen, `controle.json`, leveringsstatussen) MOET NIET in git; het hoort als zip bij de GitHub-release.
- De README van de use case MOET zijn screenshots tonen zodra ze er zijn; de root-`README.md` krijgt een **galerij** (gegenereerd tussen markers) met per use case een afbeelding, titel, vraag en link.
- Een unittest bewaakt de maximale grootte en het maximale aantal afbeeldingen per use case.
- Screenshots van de SWF-use cases MOGEN in de repository en de galerij: de data is openbaar.

Uitvoering: de uitvoerder comprimeert elk scherm tot WebP ≤ 150 KB (eerst lagere kwaliteit, pas daarna kleiner), bewaart het origineel in `bewijs/volledig/` (niet in git) en maakt met `--zip PAD` de zip voor de release. Daarna werkt hij de README's bij: in de README van de use case het blok tussen `<!-- bewijs:start -->` en `<!-- bewijs:end -->` (onder `## Bewijs`), in de root-`README.md` de galerij tussen `<!-- usecase-galerij:start -->` en `<!-- usecase-galerij:end -->`, met per actieve use case met bewijs het eerste scherm, de titel, de vraag en een link. Alleen bijwerken zonder nieuwe schermen: `galerij`. `.gitignore` laat van `bewijs/` alleen `*.webp`, `bewijs.json` en `README.md` toe.

## 13. Levenscyclus en status

```
ontwerp ──► actief ──► verouderd ──► verwijderd (map weg)
```

| Status | Betekenis | Overgang |
|---|---|---|
| `ontwerp` | de use case is de specificatie van iets wat nog gebouwd wordt (bijv. de laad-API) | naar `actief` als hij geslaagd is (11.2) |
| `actief` | werkt en wordt bij elke release getest | naar `verouderd` als hij vervangen wordt of niet meer nodig is |
| `verouderd` | werkt nog, maar verdwijnt; `veroudering` MOET gevuld zijn | verwijderen na `veroudering.verwijderen_na` |
| *verwijderd* | geen status in een manifest: de map is weg | — |

Regels:

1. Bij `verouderd` MOET `veroudering` gevuld zijn: `sinds` (datum), `verwijderen_na` (datum, minstens één minor-release van D-OmniTwin later; AANBEVOLEN minstens drie maanden), `vervangen_door` (naam van de opvolger, als die er is) en `reden`. *Nog niet afgedwongen door de uitvoerder.*
2. Naar `verouderd` gaan is een minor-wijziging van de use case; verwijderen gebeurt in een release, met een regel in `CHANGELOG.md`.
3. Een `naam` wordt na verwijderen nooit hergebruikt.
4. Een use case MOET NIET (niet-optioneel) afhangen van een use case met status `verouderd` zonder zelf een plan in zijn README.

Gedrag van de uitvoerder per status:

| Status | `lijst`, `boom`, `index` | `controleer` | `installeer` | `test` |
|---|---|---|---|---|
| `ontwerp` | getoond | ja | overgeslagen, met alles wat er niet-optioneel van afhangt | ja (ook ontwerp; dat is de acceptatietest) |
| `actief` | getoond | ja | ja | ja |
| `verouderd` | getoond | ja | ja, met een waarschuwing (*gereserveerd*: nu zonder) | ja |
| geen (verouderde vorm) | getoond | ja | ja, via `laad_usecase.py` | ja |

## 14. Uitvoerder

De uitvoerder is `python -m omnitwin.usecases <commando>`. Elke uitvoerder van deze specificatie MOET deze commando's met dit contract bieden; de referentie-implementatie staat in [`src/omnitwin/usecases.py`](../../../src/omnitwin/usecases.py).

| Commando | Wat | Netwerk / installatie | Exitcode |
|---|---|---|---|
| `lijst` | naam, versie, status, titel, afhankelijkheden van alle use cases | nee | 0 |
| `boom <naam>` | afhankelijkheden als boom, met versie, status en `(optioneel)` | nee | 0; 2 bij cyclus of onbekende naam |
| `index [--controleer]` | de index in `usecases/README.md` bijwerken, of alleen vergelijken | nee | 0; 1 als hij niet actueel is (`--controleer`) |
| `controleer <naam> [--uit MAP] [--variant NAAM]` | manifest, bestanden, afhankelijkheden, registraties; leveringen maken uit de bron en valideren tegen het profiel; lokale controles; schrijft `controle.json` in de uitvoermap | bronnen wel, installatie niet | 0 als geldig; 1 als niet geldig; 2 bij een fout in de afhankelijkheden |
| `installeer <naam> … \| --alle [--testaccounts]` | met `--testaccounts` eerst de actoren als testaccounts (10.1); in topologische volgorde: verouderde vorm via `laad_usecase.py`; volledige vorm via de laad-API: registreren (route `laden`/`compat`: `POST`, of `PUT` als hij bestaat), levering maken, aanbieden met `Idempotency-Key` `<dataset>-<sha256[:16]>`; route `beheer`: `PUT <beheerpad>/<id>` | ja | 0, ook als de laad-API er (nog) niet is (met melding); 2 bij een fout in de afhankelijkheden |
| `test <naam> [--testaccounts]` | `installeer` (ook bij status `ontwerp`) en dan de controles tegen de installatie; met `--testaccounts` als de actoren (10.1), met de rechtencontroles | ja | 0 als geen controle `fout` is of de laad-API er nog niet is; 1 anders |
| `bewijs <naam> … \| --alle [--zip PAD] [--zonder-volledig]` | bewijsstappen uitvoeren met Playwright, screenshots en `bewijs.json` schrijven, README's en galerij bijwerken (12); `--alle`: actieve use cases met `bewijs.stappen` | ja (en een browser: Playwright-image) | 0 als elke gemaakte use case geslaagd is; 1 anders |
| `galerij [--controleer]` | de galerij in `README.md` en de screenshots in de README's van de use cases bijwerken, of alleen vergelijken (12.3) | nee | 0; 1 als ze niet actueel zijn (`--controleer`) |
| `opruimen <naam> …` | testaccounts van de use case en zijn afhankelijkheden verwijderen (10.1); mag ook buiten test en dev | ja | 0; 2 bij een fout |

Omgeving:

| Variabele | Gebruik |
|---|---|
| `OMNITWIN_BASE_URL` | basis-URL van de installatie (standaard `http://localhost`) |
| `OMNITWIN_CLIENT_ID`, `OMNITWIN_CLIENT_SECRET` | machineclient (client credentials) voor `installeer` en `test` |
| `OMNITWIN_TOKEN_URL`, `KEYCLOAK_REALM` | tokenendpoint, of discovery van de realm (standaard `omnitwin`) |
| `SWF_DUMP_DIR`, `SWF_DOCS_DIR`, `SWF_GEO_DIR`, `SWF_DB_DUMP`, `SWF_EXPORT_DIR`, `DATA_CACHE` | interne bronnen en de downloadcache (zie 7) |
| `OMNITWIN_BRON_DOMEINEN` | extra downloaddomeinen |
| `OMNITWIN_TESTACCOUNTS`, `OMNITWIN_OMGEVING` | testaccounts alleen met `OMNITWIN_TESTACCOUNTS=1` en niet `OMNITWIN_OMGEVING=productie` (10.1) |
| `KEYCLOAK_ADMIN_CLIENT_ID`, `KEYCLOAK_ADMIN_CLIENT_SECRET` | toegang tot de admin-API voor testaccounts: service account in de realm met de `realm-management`-rollen `manage-users`, `manage-clients`, `view-realm`, `view-clients` en `query-users` |
| `KEYCLOAK_ADMIN`, `KEYCLOAK_ADMIN_PASSWORD` | anders: de (tijdelijke) beheerder van realm `master` (standaard `admin`) |
| `KEYCLOAK_URL`, `OMNITWIN_TESTACCOUNTS_UUR`, `OMNITWIN_TESTACCOUNTS_BESTAND` | adres van Keycloak (standaard `OMNITWIN_BASE_URL` + `/auth`), levensduur (uren, standaard 24) en bestand met de geheimen (standaard `.usecase-accounts.json`) |

Verder MOET een uitvoerder:

- een manifest valideren voordat hij er iets mee doet, en weigeren als `specificatie` een versie is die hij niet kent;
- een use case die niet geldig is niet installeren;
- nooit code uit een use case uitvoeren of laden;
- geheimen niet loggen.

De acceptatietests per use case (`tests/integration/test_usecase_<naam>.py`) doen hetzelfde als `test` en slaan zichzelf over zolang de laad-API, een bron of de machineclient ontbreekt.

## 15. Beveiliging

Een use case is straks ook van buiten te installeren. Daarom is hij **onvertrouwde invoer**: alles wat hij doet, gaat via de kern.

1. **Geen code:** allowlist van bestandstypen (4), vaste adapters (7), vaste bewerkingen zonder expressies (8).
2. **Geen geheimen of interne details:** een use case MOET NIET wachtwoorden, secrets, tokens, interne hostnamen of IP-adressen, persoonsnamen of interne meetwaarden bevatten. Interne data komt alleen via de omgevingsvariabelen uit 7.
3. **Netwerk:** alleen https naar domeinen uit de allowlist; checksum AANBEVOLEN.
4. **Bestandssysteem:** alleen onder de toegestane mappen; geen `..`, geen symlinks naar buiten.
5. **Rechten:** de uitvoerder levert met een machineclient met zo weinig mogelijk rollen (AANBEVOLEN: `dataset:<id>:laden` per dataset, niet `datasets:laden`); registreren vraagt `beheerder`.
6. **Testaccounts** alleen in test en dev, gegenereerd, lokaal bewaard en opgeruimd (10.1).
7. **Privacy:** kleine aantallen worden niet gepubliceerd; dat dwingt de laad-API af met de n-drempel uit het laadprofiel (ADR 0004, besluit 6). Een use case MOET NIET die drempel verlagen onder de norm van de bronhouder.
8. **Externe use cases** (gereserveerd): alleen met een absolute URL en een vaste versie, en met verificatie van herkomst en integriteit voordat er iets wordt uitgevoerd.

## 16. Versiebeheer

### 16.1 Versie van een use case

`versie` volgt SemVer 2.0.0 (https://semver.org/lang/nl/). Elke wijziging aan een use case die in een release komt, MOET de versie verhogen:

| Verhoging | Wanneer | Voorbeelden |
|---|---|---|
| **major** | een use case die ervan afhangt, of een installatie die hem heeft, kan breken | dataset verwijderd of hernoemd; ander profiel of andere sleutel; registratie of rol vervalt; actor vervalt; controle die vroeger slaagde, faalt nu bewust; nieuwe niet-optionele afhankelijkheid |
| **minor** | nieuwe mogelijkheden, achterwaarts compatibel | dataset, controle, actor of bewijsstap erbij; nieuwe jaargang; status naar `verouderd`; nieuwe optionele afhankelijkheid |
| **patch** | geen gedragsverandering voor afhankelijken | tekst, README, `bekende_afwijkingen`, correctie van een omschrijving, nieuwe bron-URL met dezelfde inhoud |

Zolang de versie `0.y.z` is, MAG alles veranderen (SemVer), maar ook dan MOET de versie verhogen. Van `ontwerp` naar `actief` is AANBEVOLEN `1.0.0`. `naam` verandert nooit; een andere naam is een andere use case.

### 16.2 Versie van de specificatie

- `specificatie` in het manifest is `MAJOR.MINOR` van deze specificatie. Elk manifest MOET het hebben.
- **Minor** (1.0 → 1.1): achterwaarts compatibel. Elk geldig 1.0-manifest blijft geldig. Voorbeelden: een nieuw optioneel veld, een nieuwe adapter, bewerking, controletype of bewijsactie, een losser patroon.
- **Major** (1.x → 2.0): niet compatibel. Voorbeelden: een nieuw verplicht veld, een veld of waarde die vervalt (zoals de verouderde vorm), een strenger patroon, een andere betekenis.
- **Redactioneel:** taal, voorbeelden en toelichting zonder gevolg voor de geldigheid; geen nieuwe versie, wel een regel in de wijzigingslog.
- Elke versie heeft een eigen map met schema's: `docs/specificaties/usecase/<MAJOR.MINOR>/`. Zodra een versie is vastgesteld (ADR aanvaard), wijzigen de schema's in die map niet meer, behalve redactioneel. Een nieuwe versie is een nieuwe map; deze README beschrijft de nieuwste versie en de wijzigingslog de verschillen.
- Een wijziging gaat via een issue en een PR die deze README, het schema, de uitvoerder en de tests samen wijzigt. Een major-wijziging vraagt een ADR.

### 16.3 Schema's en `$id`

De schema's zijn de normatieve, machineleesbare bron. Er is maar één exemplaar van elk schema in de repository; de uitvoerder en de tests lezen ze uit `docs/specificaties/usecase/1.0/`. De `$id` is een absolute, stabiele URL op de hoofdtak:

`https://raw.githubusercontent.com/TLaan/D-OmniTwin/main/docs/specificaties/usecase/1.0/<schema>.schema.json`

Die URL levert het schema zelf (JSON), zodat een editor of validator hem kan ophalen. Bij de **overdracht van de repository naar de SWF-organisatie** verhuizen de specificatie en de schema's mee; de `$id`'s worden dan in dezelfde PR naar de nieuwe organisatie gezet (redactionele wijziging). GitHub stuurt de oude URL door.

## 17. Compatibiliteit

- Een uitvoerder die specificatie `X.Y` ondersteunt, MOET elk manifest met `specificatie` `X.0` tot en met `X.Y` accepteren, en MOET een manifest met een onbekende versie weigeren met een duidelijke melding (het schema doet dat via de `enum` van `specificatie`).
- De verouderde vorm (5.2) wordt in 1.x ondersteund en vervalt in 2.0.
- De statuswaarde `vervallen` uit het schema van vóór deze specificatie is vervangen door `verouderd`; geen use case gebruikte hem.
- De laad-API heeft een eigen versie (`API-Version`, ADR 0005). Een major-versie van de laad-API kan een nieuwe versie van deze specificatie vragen; de use cases zijn dan de acceptatietest.
- Velden of waarden die als *gereserveerd* gemarkeerd zijn, MOGEN in een minor-versie hun uitvoering krijgen zonder dat de betekenis verandert.

## 18. Voorbeelden

De voorbeelden zijn geldig volgens de schema's; de unittest `tests/test_usecase_specificatie.py` controleert dat.

### 18.1 Minimale use case

`usecases/gemeenten-in-de-geo-api/usecase.json`: geen eigen data, alleen een controle tegen de installatie.

<!-- voorbeeld: usecase -->
```json
{
  "specificatie": "1.0",
  "naam": "gemeenten-in-de-geo-api",
  "versie": "0.1.0",
  "titel": "Gemeenten zichtbaar in de geo-API",
  "vraag": "Kan ik de Friese gemeenten opvragen via de geo-API?",
  "gebruiker": "ontwikkelaar bij een gemeente",
  "status": "ontwerp",
  "afhankelijk_van": ["cbs-gebiedsindelingen"],
  "rechten": [],
  "datasets": [],
  "controles": [
    {"type": "api", "pad": "/api/geo/v1/collections", "anoniem": true, "omschrijving": "de geo-API antwoordt zonder token"}
  ]
}
```

### 18.2 Volledige use case

`usecases/gemeenten-fryslan/usecase.json`, met actoren, een dataset, controles van elk lokaal en API-type en bewijsstappen.

<!-- voorbeeld: usecase -->
```json
{
  "$schema": "https://raw.githubusercontent.com/TLaan/D-OmniTwin/main/docs/specificaties/usecase/1.0/usecase.schema.json",
  "specificatie": "1.0",
  "naam": "gemeenten-fryslan",
  "id": "TC-07-099",
  "versie": "1.0.0",
  "titel": "Friese gemeenten via de laad-API",
  "vraag": "Ik wil de 18 Friese gemeenten in D-OmniTwin, met de CBS-codes, zodat andere use cases er waarden aan kunnen hangen.",
  "gebruiker": "beheerder D-OmniTwin",
  "status": "actief",
  "afhankelijk_van": [{"naam": "swf-definities", "versie": ">=0.1.0,<1.0.0", "optioneel": true}],
  "actoren": [
    {"naam": "beheerder", "soort": "gebruiker", "rollen": ["beheerder"], "omschrijving": "registreert de dataset"},
    {"naam": "etl-cbs", "soort": "machineclient", "rollen": ["dataset:cbs-gebied-gemeenten:laden"]},
    {"naam": "lezer", "soort": "gebruiker", "rollen": ["lezer"]}
  ],
  "rechten": ["realm-rol beheerder (registreren)", "dataset:cbs-gebied-gemeenten:laden", "realm-rol lezer"],
  "datasets": [
    {
      "id": "cbs-gebied-gemeenten",
      "route": "laden",
      "registratie": "datasets/cbs-gebied-gemeenten.json",
      "profiel": "gebiedsindeling",
      "rol": "dataset:cbs-gebied-gemeenten:laden",
      "client": "etl-cbs",
      "prioriteit": "Must",
      "bron": "PDOK CBS-gebiedsindelingen 2024 (open, CC BY 4.0)",
      "verwacht": {"features": 18}
    }
  ],
  "controles": [
    {"type": "aantal", "dataset": "cbs-gebied-gemeenten", "gelijk": 18, "omschrijving": "18 Friese gemeenten (indeling 2024)"},
    {"type": "bewerking", "dataset": "cbs-gebied-gemeenten", "reden": "geometrie-leeg", "maximaal": 0},
    {"type": "api", "pad": "/api/data/v1/gebieden?id=eq.GM1900&select=id,naam", "anoniem": true, "minimaal_aantal": 1, "gebied": "GM1900"},
    {"type": "api", "pad": "/api/laden/v1/datasets/cbs-gebied-gemeenten", "anoniem": true, "status": 401, "omschrijving": "zonder token geen toegang"},
    {"type": "afkeuring", "dataset": "cbs-gebied-gemeenten", "variant": "zonder-codes", "code": "schema-ongeldig", "actor": "etl-cbs"},
    {"type": "idempotent", "dataset": "cbs-gebied-gemeenten", "actor": "etl-cbs"},
    {"type": "recht", "actor": "etl-cbs", "actie": "leveren", "dataset": "cbs-kerncijfers", "toegestaan": false, "omschrijving": "alleen de eigen dataset (403)"},
    {"type": "recht", "actor": "lezer", "actie": "registreren", "toegestaan": false},
    {"type": "chat", "vraag": "Hoeveel gemeenten heeft Fryslân?", "bevat": ["18"]},
    {"type": "viewer", "stap": "kaart, gebiedstype Gemeente", "verwacht": "18 gemeenten zichtbaar", "gebied": "GM1900"}
  ],
  "bewijs": {
    "stappen": [
      {"id": "kaart", "actie": "kaart", "gebied": "GM1900", "omschrijving": "Súdwest-Fryslân op de kaart", "bevat": ["Súdwest-Fryslân"]},
      {"id": "levering", "actie": "levering", "dataset": "cbs-gebied-gemeenten", "actor": "beheerder", "bevat": ["gepubliceerd"]},
      {"id": "chat", "actie": "chat", "vraag": "Hoeveel gemeenten heeft Fryslân?", "bevat": ["18"]}
    ]
  },
  "bekende_afwijkingen": ["Gemeentelijke herindelingen na 2024 zitten er niet in; jaargang 2025 volgt in een minor-versie."]
}
```

Het datasetbestand `usecases/gemeenten-fryslan/datasets/cbs-gebied-gemeenten.json`:

<!-- voorbeeld: dataset -->
```json
{
  "id": "cbs-gebied-gemeenten",
  "bronId": "cbs",
  "beschrijving": {
    "@context": "https://data.overheid.nl/dcat-ap-nl/context.jsonld",
    "@type": "dcat:Dataset",
    "dct:title": "CBS-gemeenten 2024, Fryslân",
    "dct:description": "Gemeentegrenzen (gegeneraliseerd) van het CBS, jaargang 2024, voor de 18 gemeenten in Fryslân.",
    "dct:publisher": "https://www.cbs.nl/",
    "dct:accessRights": "http://publications.europa.eu/resource/authority/access-right/PUBLIC",
    "dct:license": "http://creativecommons.org/licenses/by/4.0/",
    "dct:source": "https://service.pdok.nl/cbs/gebiedsindelingen/2024/wfs/v1_0",
    "dct:conformsTo": "http://www.opengis.net/def/crs/EPSG/0/28992",
    "dcat:contactPoint": {"@type": "vcard:Organization", "vcard:fn": "Functioneel beheer D-OmniTwin"}
  },
  "laadprofiel": {
    "profiel": "gebiedsindeling",
    "doel": {"gebiedstypeId": "5871bf75-e014-4e75-8cf0-adf7d61dc196", "featureTabel": "gebieden", "sleutelveld": "code", "labelveld": "naam"},
    "plausibiliteit": {"minRegels": 18, "maxDalingProcent": 10}
  },
  "bron": {
    "adapter": "wfs",
    "url": "https://service.pdok.nl/cbs/gebiedsindelingen/2024/wfs/v1_0",
    "laag": "gebiedsindelingen:gemeente_gegeneraliseerd",
    "bbox": [110000, 525000, 240000, 625000],
    "omschrijving": "CBS Wijk- en buurtkaart 2024 via PDOK (CC BY 4.0)"
  },
  "bewerkingen": [
    {"id": "alleen-fryslan", "filter": {"veld": "statcode", "in": ["GM0059", "GM0060", "GM0072", "GM0074", "GM0080", "GM0085", "GM0086", "GM0088", "GM0090", "GM0093", "GM0096", "GM0098", "GM0737", "GM1891", "GM1900", "GM1940", "GM1949", "GM1970"]}},
    {"id": "codes", "hernoem": {"statcode": "code", "statnaam": "naam"}},
    {"behoud": ["code", "naam"]},
    {"multipolygon": true}
  ],
  "levering": {"formaat": "geopackage", "bestand": "cbs-gebied-gemeenten.gpkg", "geometrie": "MultiPolygon"},
  "varianten": {"zonder-codes": {"sla_over": ["codes"]}}
}
```

Een bewijsverslag `bewijs/bewijs.json` (ingekort):

<!-- voorbeeld: bewijs -->
```json
{
  "specificatie": "1.0",
  "naam": "gemeenten-fryslan",
  "versie": "1.0.0",
  "omnitwin_versie": "0.3.0",
  "datum": "2026-10-02T12:00:00+02:00",
  "omgeving": "lokaal",
  "ai_aanbieder": "geen",
  "geslaagd": true,
  "controles": [
    {"type": "aantal", "omschrijving": "18 Friese gemeenten (indeling 2024)", "resultaat": "ok"},
    {"type": "chat", "resultaat": "overgeslagen", "melding": "chat-controles nog niet in de uitvoerder"}
  ],
  "stappen": [
    {"id": "kaart", "resultaat": "ok", "afbeelding": "kaart.webp", "antwoordtijd_s": 2.1, "console_fouten": []},
    {"id": "chat", "resultaat": "ok", "afbeelding": "chat.webp", "antwoord": "Fryslân heeft 18 gemeenten.", "antwoordtijd_s": 4.8, "console_fouten": []}
  ],
  "leveringen": [
    {"dataset": "cbs-gebied-gemeenten", "status": "gepubliceerd", "datasetversie": 1, "aantallen": {"gepubliceerd": 18}}
  ]
}
```

## 19. Wijzigingslog

| Versie | Datum | Wijziging |
|---|---|---|
| 1.0 | 2026-10-04 | Aanvulling (https://github.com/TLaan/D-OmniTwin/issues/222; formeel een minor, 1.0 is nog niet vastgesteld): bewerking `ontdubbel` (dubbele namen met een andere UUID, aanname A4) en map `SWF_EXPORT_DIR` in de allowlist (export van een andere D-OmniTwin-installatie, aanname A1). Alle bestaande manifesten blijven geldig. |
| 1.0 | 2026-10-03 | Aanvulling (https://github.com/TLaan/D-OmniTwin/issues/223; formeel een minor, 1.0 is nog niet vastgesteld): `actoren` en `actor` bij controles niet meer gereserveerd; testaccounts in test en dev (`installeer`/`test --testaccounts`, `opruimen`); controletype `recht` met `actie` en `toegestaan`. Alle bestaande manifesten blijven geldig. |
| 1.0 | 2026-10-03 | Aanvulling (https://github.com/TLaan/D-OmniTwin/issues/225): `bewijs.stappen` en het bewijsverslag zijn niet meer gereserveerd; de uitvoerder voert ze uit (12.1, 12.2), met de galerij in de root-README en het commando `galerij` (12.3, 14). `indicator` mag ook bij `kompas`. Het compacte bewijs staat in git. Alle bestaande manifesten blijven geldig. |
| 1.0 | 2026-10-02 | Aanvulling (voorstel, https://github.com/TLaan/D-OmniTwin/issues/236; formeel een minor, 1.0 is nog niet vastgesteld): adapters `cbs-statline` en `wcs-zonaal`, domein `dataderden.cbs.nl`, varianten met `bron`, `bewerkingen`, `beschrijving` en `als_beschikbaar` (demodata als plaatsvervanger voor een interne bron), geen uitzondering meer voor code in een use case. Alle bestaande manifesten blijven geldig. |
| 1.0 | 2026-10-02 | Eerste versie (https://github.com/TLaan/D-OmniTwin/issues/227). Vastgelegd wat sinds #219 gold (manifest, datasets, bronadapters, bewerkingen, afhankelijkheden, controles, uitvoerder). Nieuw: veld `specificatie` (verplicht), `naam` en `versie` verplicht, `actoren` en `bewijs.stappen` (gereserveerd), `veroudering`, patroon voor `rechten`, status `verouderd` in plaats van `vervallen`, geen onbekende velden meer in manifest, `datasets[]` en `controles[]`, schema `bewijs.schema.json`. Schema's verhuisd van `usecases/` naar `docs/specificaties/usecase/1.0/`. |

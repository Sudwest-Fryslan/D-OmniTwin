# Profiel `kaartlaag`

Features voor de kaart zonder vaste structuur: panden met een kenmerk, klimaatlagen, voorzieningen. Doel: een eigen tabel per dataset in schema `laag` (naam = `datasetId` met `_` in plaats van `-`), gepubliceerd als collectie in OGC API Features (`/api/geo`). Vervangt op termijn de upload voor externe kaartlagen in het beheer (`POST /api/admin/externe-lagen/upload`).

## Registratie

`laadprofiel.doel`:

| Veld | Verplicht | Betekenis |
|---|---|---|
| `featureTabel` | ja | naam van de featuretabel in de GeoPackage |
| `sleutelveld` | ja | attribuut met een unieke sleutel per feature |
| `labelveld` | nee | attribuut voor de pop-up of legenda |

`beschrijving` volgt GeoDCAT-AP (bijv. `dct:spatial`, `dcat:spatialResolutionInMeters`, `dct:conformsTo` met het CRS). Toegang `dct:accessRights` bepaalt of de laag anoniem zichtbaar is (alleen `PUBLIC`); een andere waarde maakt hem intern: alleen met de rol `lezer` of `beheerder`, ook de collectie `laag.<featureTabel>` in pg_featureserv (forwardAuth, [ADR 0010](../../../2-architectuur/adr/0010-toegang-per-laag-en-bron.md)).

## Levering

GeoPackage (`application/geopackage+sqlite3`) of een Data Package-zip met die GeoPackage.

| Eis | Controle |
|---|---|
| CRS | `EPSG:28992` of `EPSG:4326`; opgeslagen in 28992 |
| Geometrie | één geometrietype per tabel (punt, lijn, vlak of multi-variant), geldig |
| Sleutel | `sleutelveld` gevuld en uniek |
| Attributen | namen in `snake_case`, maximaal 63 tekens; types SQLite → PostgreSQL (`TEXT`, `INTEGER`, `REAL`, `DATE`, `DATETIME`, `BOOLEAN`) |
| Omvang | binnen de bodylimiet; `plausibiliteit` in de registratie bewaakt een onverwachte daling |

GeoJSON wordt bewust niet als leveringsformaat aangeboden: RFC 7946-GeoJSON is altijd WGS84, gemeentelijke data staat in RD. GeoJSON blijft wel de uitvoer van de geo-API.

## Publicatie

De tabel wordt in staging opgebouwd en in één transactie omgewisseld (`ALTER TABLE ... RENAME`), met een ruimtelijke index. Bij een fout blijft de vorige tabel staan.

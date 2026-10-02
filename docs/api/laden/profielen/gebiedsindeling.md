# Profiel `gebiedsindeling`

Gebieden met geometrie van één gebiedstype, bijvoorbeeld welstandsgebieden, wijkteamgebieden of een eigen buurtindeling. Doel: tabel `gebieden`. CBS-buurten, -wijken en -gemeenten laadt D-OmniTwin zelf uit open data; dit profiel is voor indelingen die alleen de bronhouder heeft.

## Registratie

`laadprofiel.doel`:

| Veld | Verplicht | Betekenis |
|---|---|---|
| `gebiedstypeId` | ja | UUID van het gebiedstype (moet bestaan, profiel `definities` of stuurdata) |
| `featureTabel` | ja | naam van de featuretabel in de GeoPackage |
| `sleutelveld` | ja | attribuut met de gebiedscode (uniek binnen de levering) |
| `labelveld` | ja | attribuut met de naam van het gebied |
| `codePrefix` | nee | prefix als de codes niet landelijk uniek zijn: welstand-id `728` wordt `WS728` |

## Levering

GeoPackage (`application/geopackage+sqlite3`) of een Data Package-zip met die GeoPackage als resource `gebieden`.

| Eis | Controle |
|---|---|
| CRS | `EPSG:28992` of `EPSG:4326` in `gpkg_spatial_ref_sys`; anders afgekeurd |
| Geometrie | `POLYGON` of `MULTIPOLYGON`, geldig (`ST_IsValid`) en niet leeg; ongeldige geometrie wordt afgekeurd, niet stil gerepareerd |
| Sleutel | `sleutelveld` gevuld en uniek; na prefix uniek over alle gebiedstypen (`gebieden.id` is de primaire sleutel) |
| Label | `labelveld` gevuld |
| Optioneel | `gemeente_code` (4 cijfers), `actief` (boolean); overige attributen gaan naar `gebieden.metadata` |

## Publicatie

`vervangen` vervangt alle gebieden van het gebiedstype. Een gebied dat verdwijnt maar nog waarden heeft in `gebied_data`, wordt niet verwijderd maar op `actief = false` gezet; de status meldt het aantal. De Z-score-referentie en de pg_featureserv-collecties volgen vanzelf, omdat ze op `gebieden` draaien.

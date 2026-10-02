# Profielen van de laad-API

Een profiel is het contract waaraan een levering moet voldoen. Elke dataset heeft precies één profiel (`laadprofiel.profiel` in de registratie); de catalogus noemt het in `dct:conformsTo`. Tabulaire delen staan vast als [Frictionless Table Schema](https://datapackage.org/standard/table-schema/) (v2). De API geeft ze ook terug via `GET /api/laden/v1/profielen/{profielId}`.

| Profiel | Wat | Doel in D-OmniTwin | Formaten | Contract |
|---|---|---|---|---|
| `waarnemingen` | indicatorwaarden per gebied en moment | `gebied_data` | Data Package-zip (CSV), CSV, JSON, GeoPackage-tabel (zonder geometrie) | [waarnemingen.schema.json](waarnemingen.schema.json) |
| `definities` | indicatoren, gebiedstypen en hun relaties (volledige set) | `indicatoren`, `gebiedstypes`, `indicator_gebiedstype_relaties` | Data Package-zip met drie resources, GeoPackage met drie tabellen, JSON (adapter) | [indicatoren](definities-indicatoren.schema.json), [gebiedstypen](definities-gebiedstypen.schema.json), [relaties](definities-relaties.schema.json) |
| `gebiedsindeling` | gebieden met geometrie van één gebiedstype | `gebieden` | GeoPackage, Data Package-zip met GeoPackage | [gebiedsindeling.md](gebiedsindeling.md) |
| `kaartlaag` | features voor de kaart, zonder vaste structuur | eigen tabel per dataset, gepubliceerd via OGC API Features (`/api/geo`) | GeoPackage, Data Package-zip met GeoPackage | [kaartlaag.md](kaartlaag.md) |

Adapter:

| Adapter | Vertaalt | Naar profiel | Beschrijving |
|---|---|---|---|
| `swf-monitor-v1` | het huidige push-formaat van de SWF-gebiedsmonitor (definities-snapshot en waarden-JSON) | `definities`, `waarnemingen` | [swf-monitor-v1.md](swf-monitor-v1.md) |

## Afspraken voor alle profielen

- **Volledige snapshot.** Een levering vervangt de vorige inhoud binnen het vervangbereik van de dataset (`laadprofiel.vervangBereik`; leeg = de hele dataset). Alleen modus `vervangen` in v1.
- **Veldnamen in de data:** `snake_case`, gelijk aan de kolommen in de database. De JSON van de API zelf (registratie, levering) gebruikt `lowerCamelCase`.
- **Extra velden** mogen als het eigen schema van de dataset ze noemt; ze komen in `metadata` (jsonb). Velden uit het profiel weglaten of hernoemen mag niet.
- **Codering:** UTF-8, CSV met komma en kopregel (RFC 4180), decimale punt, datums ISO 8601.
- **Data Package:** zip met `datapackage.json` in de root (Data Package v2). De resources heten zoals in het profiel (`waarnemingen`, `indicatoren`, `gebiedstypen`, `relaties`, `gebieden`, of vrij bij `kaartlaag`). Een `schema` in de resource is optioneel; D-OmniTwin valideert altijd tegen het profiel. Optioneel `dcat.jsonld` naast `datapackage.json`.
- **GeoPackage:** versie 1.2 tot en met 1.4, met `gpkg_contents` en `gpkg_spatial_ref_sys`. CRS `EPSG:28992` (RD New) of `EPSG:4326`; D-OmniTwin slaat op in 28992. Tabellen zonder geometrie (attributes) mogen voor tabulaire profielen.
- **Privacy:** waarden met `n` onder de drempel worden niet gepubliceerd en na publicatie uit de staging verwijderd. Een levering bevat geen persoonsgegevens; alleen aggregaten per gebied.

Voorbeelden: [../voorbeelden/](../voorbeelden/).

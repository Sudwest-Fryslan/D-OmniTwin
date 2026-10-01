# CBS Buurten Fryslân — Bronvermelding

## Over dit bestand: `buurten_fryslan.geojson`

Bevat de CBS gebiedsindeling 2024 voor alle buurten in de provincie Fryslân.

| Kenmerk | Waarde |
|---------|--------|
| **Bron** | Centraal Bureau voor de Statistiek (CBS) via PDOK WFS |
| **Dataset** | CBS Gebiedsindelingen 2024 |
| **Licentie** | [Creative Commons Attribution 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) |
| **Jaar** | 2024 |
| **CRS** | WGS84 (EPSG:4326) |
| **Buurten** | 931 (alle 18 Friese gemeenten) |

**Gemeenten opgenomen:**

| CBS-code | Gemeente |
|----------|---------|
| 0059 | Achtkarspelen |
| 0060 | Ameland |
| 1891 | Dantumadiel |
| 1940 | De Fryske Marren |
| 0072 | Harlingen |
| 0074 | Heerenveen |
| 0080 | Leeuwarden |
| 1970 | Noardeast-Fryslân |
| 0085 | Ooststellingwerf |
| 0086 | Opsterland |
| 0088 | Schiermonnikoog |
| 0090 | Smallingerland |
| 1900 | Súdwest-Fryslân |
| 0093 | Terschelling |
| 0737 | Tytsjerksteradiel |
| 0096 | Vlieland |
| 1949 | Waadhoeke |
| 0098 | Weststellingwerf |

## Over dit bestand: `indicatorwaarden_fryslan.csv`

Bevat RIVM-indicatorwaarden (Gezondheidsmonitor, via CBS dataderden) voor de Friese buurten. De CBS Kerncijfers wijken en buurten staan sinds #159 in [`init_data/cbs/`](../cbs/), met alle jaargangen 2019-2026.

| Kenmerk | Waarde |
|---------|--------|
| **Bron** | RIVM Gezondheidsmonitor via dataderden.cbs.nl |
| **Licentie** | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| **Peiljaar** | 2012, 2016, 2020, 2022, 2024 |
| **Peiljaar** | Kerncijfers: 2021 (tabel 85039NED; in de CSV gelabeld als 2023, zie #119). RIVM: 2012, 2016, 2020, 2022, 2024. Geometrie: 2024. Zie `docs/3-data-engineering/jaargangen.md`. |

**Verplichte bronvermelding bij hergebruik:**

> Centraal Bureau voor de Statistiek (CBS), Den Haag/Heerlen. Geraadpleegd op [datum]. [www.cbs.nl](https://www.cbs.nl)

> Rijksinstituut voor Volksgezondheid en Milieu (RIVM). Gezondheidsmonitor per wijk en buurt 2022. Via CBS dataderden. [www.rivm.nl](https://www.rivm.nl)

# Datakwaliteit sample_indicatoren.csv

Stand bij het opstellen van `datapackage.json` (#60). De data is ongewijzigd; het Table Schema is hierop afgestemd (`bron`, `kwaliteit`, `eenheid` en `categorie` zijn niet verplicht). Totaal: 1.132 regels, 87 indicatoren, 13 buurten.

## Herkomst (`bron`)

| Bevinding | Regels |
|---|---:|
| Lege `bron` | 48 |
| Uploadbestandsnaam als bron (`<uuid>_d_cbs_buurten.json`, 8 bestanden) — onbekend, te herleiden | 96 |
| `DEMO: gemiddelde Bolsward-Noord en Bolsward-Noordoost` (BU19000002) | 88 |
| Vrije tekst zonder tabel-ID (`Kerncijfers wijken en buurten 2023`) | 105 |
| CBS-tabelcode (`CBS_86165NED` 240, `CBS_85618NED` 24, `CBS_85984NED` 15, `CBS_50150NED` 12) | 291 |
| Overige benoemde bron (BAG 168 + 84, RIVM 120, RVO EP-Online 60 + 12 berekend, OpenStreetMap 60) | 504 |

## Overige kolommen

| Bevinding | Regels |
|---|---:|
| `kwaliteit` leeg | 1.132 (alle) |
| `eenheid` leeg | 222 |
| `eenheid` niet genormaliseerd (`aantal`/`Aantal`, `%`/`percentage`) | 15 varianten |
| `categorie` leeg | 729 |

## `interpretatie_logica`

| Waarde | Regels |
|---|---:|
| `pos_is_pos` | 1.080 |
| `N/A` | 39 |
| `-/+` | 13 |

Twee notaties door elkaar (`pos_is_pos` versus `-/+`), plus `N/A`. Normaliseren hoort bij de volgende stap van #60 (metadata één keer per indicator).

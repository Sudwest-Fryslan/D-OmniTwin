# Datakwaliteit sample_indicatoren.csv

Stand bij het opstellen van `datapackage.json` (#60), herkomst bijgewerkt na #159 (CBS Kerncijfers worden sindsdien gedownload en staan niet meer in de sample: nu 728 regels). De overige tellingen gelden voor de stand van #60. De data was toen ongewijzigd; het Table Schema is hierop afgestemd (`bron`, `kwaliteit`, `eenheid` en `categorie` zijn niet verplicht). Totaal: 1.132 regels, 87 indicatoren, 13 buurten.

## Herkomst (`bron`)

| Bevinding | Regels |
|---|---:|
| Lege `bron` | 48 |
| Uploadbestandsnaam als bron (`<uuid>_d_cbs_buurten.json`, 8 bestanden) — onbekend, te herleiden | 96 |
| `DEMO: gemiddelde Bolsward-Noord en Bolsward-Noordoost` (BU19000002; CBS Kerncijfers sinds #159 echt) | 56 |
| Vrije tekst zonder tabel-ID (`Kerncijfers wijken en buurten 2023`, eigenlijk 2021) | 0 (vervangen, #159) |
| `CBS Kerncijfers wijken en buurten <jaar> (<tabel>)`, 2019-2026 | 0 (gedownload bij het laden) |
| CBS-tabelcode (`CBS_85984NED` 12, indicator Huisarts; `CBS_50150NED` 12) | 24 |
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

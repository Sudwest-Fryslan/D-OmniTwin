# TC-06-003 — Gebiedsagenda IJsselmeerkust & Wadden

**Status:** actief · **Versie:** 0.1.0
**Afhankelijk van:** [cbs-gebiedsindelingen](../cbs-gebiedsindelingen/README.md), [cbs-kerncijfers](../cbs-kerncijfers/README.md), [rivm-gezondheidsmonitor](../rivm-gezondheidsmonitor/README.md), [cbs-ses-woa](../cbs-ses-woa/README.md), [politie-misdrijven](../politie-misdrijven/README.md), [hittestress](../hittestress/README.md)
**Manifest:** [`usecase.json`](usecase.json) · **Controleren:** `python -m omnitwin.usecases controleer gebiedsagenda-ijsselmeerkust`

## Vraag

- **Gebruiker:** beleidsadviseur / gebiedsregisseur IJsselmeergebied-Wadden
- **Vraag:** "Hoe staan de kernen langs de IJsselmeerkust en het Waddengebied (o.a. Makkum, Workum, Hindeloopen, Stavoren, Koudum en Witmarsum) ervoor op demografie, gezondheid, sociaal-economische status, veiligheid en klimaatadaptatie ten opzichte van elkaar en het gemeentegemiddelde?"

Deze functionele use case bundelt alle open databronnen die nodig zijn voor het vijf-fasen E2E-scenario in [`TC-06-003_gebiedsagenda_ijsselmeerkust_usecase.md`](../../docs/testcases/gebiedsagenda_ijselmeerkust/TC-06-003_gebiedsagenda_ijsselmeerkust_usecase.md) en de [spiegeling van de Gebiedsagenda IJsselmeerkust](../../docs/testcases/gebiedsagenda_ijselmeerkust/verkenning_gebiedsagenda_ijsselmeerkust_spiegeling.md).

## Kustkernen in focus (GM1900)

| Kern | Buurtcode | Focus in gebiedsanalyse |
|---|---|---|
| Makkum | `BU19001700` | Demografie, SES-WOA, gezondheid, leefstijl |
| Workum | `BU19000200` | Vergrijzing, leefbaarheid, inbraakveiligheid |
| Hindeloopen | `BU19000202` | Vergrijzing, hittestress, voorzieningenniveau |
| Stavoren | `BU19000403` | Gezondheid, regie over eigen leven, steun, SES-WOA |
| Koudum | `BU19000300` | Sociaal-economische status, arbeidsverleden |
| Witmarsum | `BU19001300` | Verzorgingskern noordelijk kustgebied |

## Data

Deze use case registreert zelf geen datasets (`datasets: []`), maar steunt op de bovenliggende open use cases:

- **CBS Gebiedsindelingen & Kerncijfers** (`cbs-gebiedsindelingen`, `cbs-kerncijfers`) — buurten 2024, leeftijd, woningen, energie, inkomen, nabijheid voorzieningen.
- **RIVM Gezondheidsmonitor (`50150NED`)** (`rivm-gezondheidsmonitor`) — uitgebreid met de 4 ontbrekende indicatoren: `Beperking` (`BeperktVanwegeGezondheid_7`), `Matig/veel regie over het eigen leven` (`MatigVeelRegieOverHetEigenLeven_24`), `Krijgt steun van anderen` (`KrijgtSteunVanAnderen_29`) en `Voldoet aan de alcoholrichtlijn` (`VoldoetAanDeAlcoholrichtlijn_38`).
- **CBS SES-WOA (`86092NED`)** (`cbs-ses-woa`) — SES-WOA totaalscore, deelscores (financiële welvaart, opleidingsniveau, arbeidsverleden) en 4-jaars arbeidsdeelname (2014–2023).
- **Politie Misdrijven (`47018NED`)** (`politie-misdrijven`) & **RIVM Hittestress** (`hittestress`).

## Acceptatiecriteria

| # | Type | Wat | Verwacht |
|---|---|---|---|
| 1 | api | Workum (`BU19000200`) — Afstand tot huisarts (CBS Kerncijfers) | HTTP 200, ≥ 3 resultaten |
| 2 | api | Makkum (`BU19001700`) — Beperking (RIVM) | HTTP 200, ≥ 3 resultaten (2020–2024) |
| 3 | api | Makkum (`BU19001700`) — Voldoet aan alcoholrichtlijn (RIVM) | HTTP 200, ≥ 4 resultaten (2016–2024) |
| 4 | api | Stavoren (`BU19000403`) — Matig/veel regie over eigen leven (RIVM) | HTTP 200, ≥ 3 resultaten |
| 5 | api | Stavoren (`BU19000403`) — Krijgt steun van anderen (RIVM) | HTTP 200, ≥ 1 resultaat (2024) |
| 6 | api | Makkum (`BU19001700`) — SES-WOA totaalscore (CBS) | HTTP 200, ≥ 5 resultaten (2014–2023) |
| 7 | api | Koudum (`BU19000300`) — Afgelopen 4 jaar niet werkzaam (CBS) | HTTP 200, ≥ 5 resultaten (2014–2023) |
| 8 | api | Workum (`BU19000200`) — Woninginbraken (Politie) | HTTP 200, ≥ 1 resultaat |
| 9 | api | Hindeloopen (`BU19000202`) — Stedelijk hitte-eiland effect (RIVM) | HTTP 200, ≥ 1 resultaat |

## Bewijs

<!-- bewijs:start -->
*Nog geen bewijs. Maken tegen een draaiende installatie: `python -m omnitwin.usecases bewijs gebiedsagenda-ijsselmeerkust`.*
<!-- bewijs:end -->

## Bekende afwijkingen

- Kleine kustkernen met weinig inwoners/huishoudens (zoals Piaam `BU19001802`, Allingawier `BU19001801`, Gaast `BU19001803`, Scharl `BU19000402`) hebben vanwege privacyonderdrukking niet in alle jaren waarden bij CBS en RIVM.
- Categorie D uit de verkenning (Vektis `D-GZS20`/`GP07`, CBS maatwerk `VSOH52023` en interne SWF `Suite_*`-indicatoren) blijft buiten scope van deze open use case (#497).

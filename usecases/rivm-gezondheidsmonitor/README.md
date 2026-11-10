# TC-07-021 — RIVM Gezondheidsmonitor per buurt via de laad-API

**Status:** actief · **Versie:** 0.3.0 · **Afhankelijk van:** [cbs-gebiedsindelingen](../cbs-gebiedsindelingen/README.md)
**Manifest:** [`usecase.json`](usecase.json) · **Controleren:** `python -m omnitwin.usecases controleer rivm-gezondheidsmonitor`

## Vraag

- **Gebruiker:** beheerder D-OmniTwin
- **Vraag:** "Ik wil de gezondheidscijfers per buurt (ervaren gezondheid, beperking, regie over het eigen leven, eenzaamheid, steun van anderen, mantelzorg, vrijwilligerswerk, moeite met rondkomen, leefstijl) uit de Gezondheidsmonitor in D-OmniTwin, met de trend sinds 2012."
- **Rechten:** `realm-rol beheerder (registreren)`, `dataset:rivm-gezondheid-definities:laden`, `dataset:rivm-gezondheid-buurten:laden`

De RIVM-tabel *Gezondheid per wijk en buurt; 2012/2016/2020/2022/2024 (indeling 2024)* staat op StatLine van derden (`dataderden.cbs.nl`, tabel 50150NED). De kernadapter `cbs-statline` haalt hem op (ODataFeed, gepagineerd) en pakt hem uit per kolom; de dataset koppelt elke kolom aan een indicator van D-OmniTwin. Leeftijd 18 jaar en ouder, de puntschatting (geen marges). Alleen buurten uit de CBS-indeling 2024 (die van [cbs-gebiedsindelingen](../cbs-gebiedsindelingen/README.md)).

Gebruikt door de demo-use cases [hittestress](../hittestress/README.md), [energiearmoede](../energiearmoede/README.md), [brede-welvaart](../brede-welvaart/README.md) en [sociale-cohesie](../sociale-cohesie/README.md). Tot #236 stonden deze waarden in de sample, met demodata voor Bolsward-Zuidoost.

## Data

| Dataset | Route | Profiel | Formaat | Bron | Toegang | Licentie | Rol |
|---|---|---|---|---|---|---|---|
| [`rivm-gezondheid-definities`](datasets/rivm-gezondheid-definities.json) | laden | definities | datapackage | Aanvullende definities 50150NED ([`definities.json`](definities.json)) | open | CC BY 4.0 | `dataset:rivm-gezondheid-definities:laden` |
| [`rivm-gezondheid-buurten`](datasets/rivm-gezondheid-buurten.json) | laden | waarnemingen | datapackage | RIVM StatLine 50150NED via https://dataderden.cbs.nl/ODataFeed/odata/50150NED | open | CC BY 4.0 | `dataset:rivm-gezondheid-buurten:laden` |

| Indicator (D-OmniTwin) | Kolom in 50150NED |
|---|---|
| Ervaren gezondheid | `GoedErvarenGezondheid_4` |
| Beperking (Beperkt vanwege gezondheid) | `BeperktVanwegeGezondheid_7` |
| Hoog risico op angststoornis of depressie | `HoogRisicoAngststoornisOfDepressie_14` |
| Matig/veel regie over het eigen leven | `MatigVeelRegieOverHetEigenLeven_24` |
| Eenzaamheid | `Eenzaam_25` |
| Krijgt steun van anderen | `KrijgtSteunVanAnderen_29` |
| Mantelzorger | `Mantelzorger_30` |
| Vrijwilliger | `Vrijwilligerswerk_31` |
| Moeite met rondkomen | `MoeiteMetRondkomen_32` |
| Overgewicht | `Overgewicht_33` |
| Obesitas | `ErnstigOvergewichtObesitas_34` |
| Roken | `RooktTabak_35` |
| Overmatig drinken | `OvermatigDrinken_37` |
| Voldoet aan de alcoholrichtlijn | `VoldoetAanDeAlcoholrichtlijn_38` |
| Bewegen | `VoldoetAanDeBeweegrichtlijn_40` |

Verwacht: 44.609 regels (15 indicatoren, buurten in Fryslân, peiljaren 2012, 2016, 2020, 2022 en 2024); `kwaliteit` = `geschat` (modelberekening van het RIVM); per waarde `bron` = "RIVM, GGD en CBS: Gezondheidsmonitor <jaar> (StatLine 50150NED)".

Bronvermelding: Gezondheidsmonitor Volwassenen en Ouderen, GGD'en, CBS en RIVM.

### Lokaal gecontroleerd

Bron → levering op 10-11-2026: 44.609 regels (3.431 per buurtindicator over 2012–2024; 2.061 voor Beperking 2020–2024; 2.059 voor Regie 2016/2020/2024; 2.746 voor Alcoholrichtlijn 2016–2024 en Vrijwilliger; 687 voor Steun van anderen 2024), niets afgewezen. Stavoren 2024: beperking 35,4%, regie eigen leven 87,2%, steun van anderen 93,0%, voldoet aan alcoholrichtlijn 37,0%.

## Stappen

1. `python -m omnitwin.usecases controleer rivm-gezondheidsmonitor --uit /tmp/rivm` (zonder API).
2. `python -m omnitwin.usecases installeer rivm-gezondheidsmonitor` (met machineclient, zie [use cases](../README.md#uitvoeren)), of bij een verse installatie automatisch (`db-init`, in-process).
3. Controleren in de API: `GET /api/data/v1/gebied_data?gebied_id=eq.BU19000002&indicator_uuid=eq.4661dcb9-b7c4-42f8-b7c5-a61c12568806&select=jaar,waarde,bron`.

## Acceptatiecriteria

| # | Type | Wat | Verwacht |
|---|---|---|---|
| 1 | aantal | `rivm-gezondheid-definities` (`indicatoren`) | gelijk aan 4 |
| 2 | aantal | `rivm-gezondheid-buurten` | minimaal 43.000 |
| 3 | api | Eenzaamheid in Bolsward-Zuidoost (anoniem) | HTTP 200, ≥ 5 resultaten (2012-2024) |
| 4 | idempotent | `rivm-gezondheid-buurten` twee keer leveren | zelfde versie |

## Bewijs

<!-- bewijs:start -->
*Gemaakt op 13-10-2026 met D-OmniTwin 0.6.0 (use case 0.2.0); geslaagd. Verslag: [`bewijs/bewijs.json`](bewijs/bewijs.json). Opnieuw maken (bij een release): `python -m omnitwin.usecases bewijs rivm-gezondheidsmonitor`.*

![Ervaren gezondheid per buurt in Súdwest-Fryslân (RIVM Gezondheidsmonitor)](bewijs/kaart.webp)
*Ervaren gezondheid per buurt in Súdwest-Fryslân (RIVM Gezondheidsmonitor)*

![Leveringsstatus van de Gezondheidsmonitor per buurt (laad-API)](bewijs/levering.webp)
*Leveringsstatus van de Gezondheidsmonitor per buurt (laad-API)*
<!-- bewijs:end -->

## Bekende afwijkingen

- 2012 en 2016 hebben minder buurten (kleine buurten onderdrukt of niet berekend).
- `Krijgt steun van anderen` (`KrijgtSteunVanAnderen_29`) is door het RIVM alleen in 2024 uitgevraagd; `Matig/veel regie over het eigen leven` ontbreekt in 2012 en 2022; `Beperking` (`BeperktVanwegeGezondheid_7`) ontbreekt in 2012 en 2016.

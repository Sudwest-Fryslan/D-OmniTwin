# TC-07-027 — CBS SES-WOA (welvaart, opleiding en arbeidsverleden) per buurt via de laad-API

**Status:** actief · **Versie:** 0.1.0 · **Afhankelijk van:** [cbs-gebiedsindelingen](../cbs-gebiedsindelingen/README.md)
**Manifest:** [`usecase.json`](usecase.json) · **Controleren:** `python -m omnitwin.usecases controleer cbs-ses-woa`

## Vraag

- **Gebruiker:** beheerder D-OmniTwin
- **Vraag:** "Ik wil de sociaal-economische statusscores (SES-WOA totaalscore en deelscores financiële welvaart, opleidingsniveau en arbeidsverleden) en het 4-jaars arbeidsverleden per buurt in D-OmniTwin, met de meerjarige ontwikkeling sinds 2014."
- **Rechten:** `realm-rol beheerder (registreren)`, `dataset:cbs-ses-woa-definities:laden`, `dataset:cbs-ses-woa-buurten:laden`, `realm-rol lezer`

De CBS-tabel *Sociaal-economische status; scores per wijk en buurt, regio-indeling 2024* (`86092NED`) ontsluit jaarlijkse registerscores (2014–2023) op basis van financiële welvaart, hoogst behaalde opleidingsniveau en het arbeidsverleden in de afgelopen 4 jaar van particuliere huishoudens. De adapter `cbs-statline` haalt de buurten in Fryslân op en koppelt op de CBS-buurtindeling 2024 ([cbs-gebiedsindelingen](../cbs-gebiedsindelingen/README.md)).

Gebruikt door onder andere [gebiedsagenda-ijsselmeerkust](../gebiedsagenda-ijsselmeerkust/README.md) (`TC-06-003`).

## Data

| Dataset | Route | Profiel | Formaat | Bron | Toegang | Licentie | Rol |
|---|---|---|---|---|---|---|---|
| [`cbs-ses-woa-definities`](datasets/cbs-ses-woa-definities.json) | laden | definities | datapackage | Indicatordefinities 86092NED ([`definities.json`](definities.json)) | open | CC BY 4.0 | `dataset:cbs-ses-woa-definities:laden` |
| [`cbs-ses-woa-buurten`](datasets/cbs-ses-woa-buurten.json) | laden | waarnemingen | datapackage | CBS StatLine 86092NED via https://opendata.cbs.nl/ODataFeed/odata/86092NED | open | CC BY 4.0 | `dataset:cbs-ses-woa-buurten:laden` |

| Indicator (D-OmniTwin) | Kolom in 86092NED | Eenheid |
|---|---|---|
| SES-WOA totaalscore | `GemiddeldeScore_29` | score |
| SES-WOA deelscore financiële welvaart | `GemiddeldeScore_31` | score |
| SES-WOA deelscore opleidingsniveau | `GemiddeldeScore_33` | score |
| SES-WOA deelscore arbeidsverleden | `GemiddeldeScore_35` | score |
| Afgelopen 4 jaar voortdurend werkzaam | `Afgelopen4JaarVoortdurendWerkzaam_24` | % |
| Afgelopen 4 jaar niet voortdurend werkzaam | `Afgelopen4JrNietVoortdurendWerkzaam_25` | % |
| Afgelopen 4 jaar niet werkzaam | `Afgelopen4JaarNietWerkzaam_26` | % |

Bronvermelding: CBS, Sociaal-economische status; scores per wijk en buurt, regio-indeling 2024 (StatLine 86092NED).

### Lokaal gecontroleerd

Bron → levering op 10-11-2026: 37.919 regels (5.417 waarnemingen per indicator over 2014–2023), niets afgewezen. Makkum (`BU19001700`) 2023: totaalscore `-0.008`, voortdurend werkzaam `51.4%`, niet werkzaam `3.7%`. Stavoren (`BU19000403`) 2023: totaalscore `-0.057`, voortdurend werkzaam `47.2%`, niet werkzaam `5.7%`.

## Stappen

1. `python -m omnitwin.usecases controleer cbs-ses-woa --uit /tmp/ses-woa` (zonder API).
2. `python -m omnitwin.usecases installeer cbs-ses-woa` (met machineclient), of bij een verse installatie automatisch (`db-init`, in-process).
3. Controleren in de API: `GET /api/data/v1/gebied_data?gebied_id=eq.BU19001700&indicator_uuid=eq.1c12fa21-cabd-5f2a-8cf6-fcc7a651b59e&select=jaar,waarde,bron`.

## Acceptatiecriteria

| # | Type | Wat | Verwacht |
|---|---|---|---|
| 1 | aantal | `cbs-ses-woa-definities` (`indicatoren`) | gelijk aan 7 |
| 2 | aantal | `cbs-ses-woa-buurten` | minimaal 35.000 |
| 3 | api | SES-WOA totaalscore in Makkum (anoniem) | HTTP 200, ≥ 5 resultaten (2014–2023) |
| 4 | recht | `beheerder` registreert dataset, `etl-open-data` laadt eigen dataset, geen andere dataset (403), `lezer` laadt niets (403) | HTTP 200 / 403 |

## Bewijs

<!-- bewijs:start -->
*Nog geen bewijs. Maken tegen een draaiende installatie: `python -m omnitwin.usecases bewijs cbs-ses-woa`.*
<!-- bewijs:end -->

## Bekende afwijkingen

- Buurten met weinig particuliere huishoudens worden door het CBS onderdrukt en ontbreken daarom in de reeks.
- StatLine 86092NED loopt op dit moment van 2014 tot en met 2023.

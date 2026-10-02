# TC-07-010 — D-OmniTwin vervangt de huidige SWF-gebiedsmonitor (acceptatie)

**Status:** ontwerp (de laad-API is nog niet gebouwd; deze use case is de specificatie en straks de acceptatietest)
**Versie:** 0.1.0 · **Afhankelijk van:** [swf-definities](../swf-definities/README.md), [swf-gebiedsindelingen](../swf-gebiedsindelingen/README.md), [swf-kompasprofiel](../swf-kompasprofiel/README.md), [swf-basismonitor-waarden](../swf-basismonitor-waarden/README.md), [swf-klimaatmonitor](../swf-klimaatmonitor/README.md), [swf-kaartlagen](../swf-kaartlagen/README.md), [swf-adapter-fme](../swf-adapter-fme/README.md)
**Manifest:** [`usecase.json`](usecase.json) · **Controleren:** `python -m omnitwin.usecases controleer swf-gebiedsmonitor`

## Vraag

- **Gebruiker:** kernteam gebiedsagenda en functioneel beheerder SWF
- **Vraag:** "Kan Súdwest-Fryslân met D-OmniTwin hetzelfde als met de huidige gebiedsmonitor: dezelfde indicatoren en gebieden, dezelfde sunburst en Klimaatmonitor, dezelfde lagen, gevuld vanuit de DWH?"
- **Rechten:** `realm-rol beheerder`, `realm-rol lezer`, `dataset:swf-monitor-definities:laden`, `dataset:swf-monitor-waarden:laden`

De acceptatietest voor "D-OmniTwin vervangt de huidige gebiedsmonitor" (epic [#195](https://github.com/TLaan/D-OmniTwin/issues/195)). Deze use case heeft zelf geen datasets: via `afhankelijk_van` neemt hij alle `swf-*`-use cases mee, in de volgorde van de huidige stroom, en doet daarna de eindcontroles.

```
swf-definities → (cbs-gebiedsindelingen) → swf-gebiedsindelingen → swf-kompasprofiel
  → swf-basismonitor-waarden → swf-klimaatmonitor → swf-kaartlagen → swf-adapter-fme
```

`python -m omnitwin.usecases boom swf-gebiedsmonitor` toont de boom. Wat de huidige monitor kan en wat 0.3.0 moet doen: [huidige gebiedsmonitor](../../docs/1-visie-concept/huidige-gebiedsmonitor/README.md) en de [gat-analyse](../../docs/1-visie-concept/huidige-gebiedsmonitor/gat-analyse.md).


## Stappen

1. Installeer de afhankelijkheden in volgorde (`python -m omnitwin.usecases boom swf-gebiedsmonitor`); elk met zijn eigen stappen.
2. Voer de controles hieronder uit: API-controles met een token van een machineclient, viewer-controles handmatig met screenshots.

## Acceptatiecriteria

| # | Type | Wat | Verwacht |
|---|---|---|---|
| 1 | api | `GET /api/data/v1/indicatoren?uuid=in.(97f53738-3439-4c28-8cac-046a52c65248,bf4e5b8f-6b0a-4632-b9b4-8e29d025e68c,461d542b-b8be-4510-9dd0-5ba554b818cb)&select=uuid` (anoniem) — dezelfde UUID's als de monitor | HTTP 200, ≥ 3 resultaten |
| 2 | api | `GET /api/data/v1/gebied_data?select=indicator_uuid&gebied_id=like.BU1900*&limit=1` (met token) — waarden op CBS-buurten van Súdwest-Fryslân | HTTP 200, ≥ 1 resultaten |
| 3 | api | `GET /api/beheer/v1/kompasprofielen` (met token) — SWF Basis en SWF Klimaat | HTTP 200, ≥ 2 resultaten |
| 4 | api | `GET /api/geo/v1/collections/laag.swf_laag_projecten_vlak/items?limit=1` (anoniem) — interne laag anoniem niet bereikbaar | HTTP 401 |
| 5 | viewer | inloggen met het SWF-account (OIDC) | naam en rollen zichtbaar; interne lagen beschikbaar |
| 6 | viewer | Basis monitor: Bolsward-Zuidoost aanklikken | sunburst 4/12/33 met dezelfde kleuren (percentielklasse) als de huidige monitor voor ≥ 10 gecontroleerde indicatoren |
| 7 | viewer | Klimaatmonitor: een welstand × buurt in Bolsward | labels per thema en indicator |
| 8 | viewer | indicator op de kaart: Afstand tot koele plek | percentielkaart en gelabelde werkelijke waarde, en uitzetten |
| 9 | api | `GET /api/laden/v1/compat/swf-monitor/monitor_api/indicator_waarde` (met token) — de FME-route werkt: alle waarden terug in het SWF-formaat | HTTP 200, ≥ 43000 resultaten |

`aantal` en `bewerking` controleert `controleer` nu al op de lokaal gemaakte levering; de andere vragen de laad-API en een draaiende installatie.

## Bewijs

In [`bewijs/`](bewijs/README.md), gemaakt door de uitvoerder (niet in git): `controle.json` (uitvoer van `controleer`), per levering de status-JSON van de laad-API (`levering-<dataset>.json`: status, versie, aantallen, fouten), en screenshots van de viewer-controles.

## Bekende afwijkingen

- Deze use case heeft zelf geen datasets: hij neemt alle swf-* use cases mee en doet de eindcontroles.
- Inloggen met rollen, percentielklasse en labels A–E, favorieten en de beveiligde geo-route zijn functies van 0.3.0 die nog gebouwd worden; de viewer-controles zijn handmatig tot de uitvoerder ze kan draaien.
- Open vragen staan in docs/1-visie-concept/huidige-gebiedsmonitor/gat-analyse.md.

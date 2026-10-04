# TC-07-008 — SWF-kaartlagen: klimaat, deelgebieden, projecten en overige lagen

**Status:** actief (lagen waarvan de bron hier ontbreekt, worden overgeslagen)
**Versie:** 0.3.0 · **Afhankelijk van:** [swf-gebiedsindelingen](../swf-gebiedsindelingen/README.md)
**Manifest:** [`usecase.json`](usecase.json) · **Controleren:** `python -m omnitwin.usecases controleer swf-kaartlagen`

## Vraag

- **Gebruiker:** medewerker team of vakgroep (SWF)
- **Vraag:** "Ik wil de kaartlagen van de huidige monitor (klimaatlagen, deelgebieden, coördinatorgebieden, grootgrondbezit, 'Wat speelt er?') in D-OmniTwin, met dezelfde zichtbaarheid: open lagen voor iedereen, interne lagen alleen na inloggen."
- **Rechten:** `realm-rol beheerder (registreren)`, `realm-rol lezer (interne lagen zien)`, `dataset:swf-laag-deelgebieden:laden`, `dataset:swf-laag-coordinatorgebieden:laden`, `dataset:swf-laag-afstand-tot-koelte:laden`, `dataset:swf-laag-risico-paalrot:laden`, `dataset:swf-laag-projecten-vlak:laden`, `dataset:swf-laag-projecten-punt:laden`, `dataset:swf-laag-projecten-lijn:laden`, `dataset:swf-laag-grootgrondbezit:laden`

De lagen van de huidige viewer, als datasets met profiel `kaartlaag` (eigen tabel per dataset, gepubliceerd via de geo-API). De zichtbaarheid volgt `dct:accessRights`: `PUBLIC` is anoniem zichtbaar, `RESTRICTED` alleen na inloggen (rol `lezer` of een SWF-rol), afgedwongen in de geo-route, niet alleen in de viewer.

| Groep in de viewer | Laag | Hier | Bron |
|---|---|---|---|
| Overige lagen | Súdwest-deelgebieden | `swf-laag-deelgebieden` (open) | repo |
| Overige lagen | Dorp-/wijkcoördinatorgebieden | `swf-laag-coordinatorgebieden` | projectmap SWF |
| Overige lagen | SWF-grootgrondbezit | `swf-laag-grootgrondbezit` | GeoServer SWF |
| Klimaatmonitor › Hittestress | Afstand tot koelte | `swf-laag-afstand-tot-koelte` | SWF-bewerking |
| Klimaatmonitor › Droogte | Risico paalrot | `swf-laag-risico-paalrot` | SWF-bewerking |
| Wat speelt er allemaal? | GeoVisia-projectlocaties | `swf-laag-projecten-vlak`, `-punt`, `-lijn` | GeoVisia-export |
| Klimaatmonitor › Hemelwater | Waterdiepte bij intense neerslag | externe laag, geen levering | Klimaateffectatlas (WMS, open) |
| Klimaatmonitor › Hemelwater | Maaiveldhoogte AHN4 | externe laag, geen levering | PDOK (WMS, open) |
| Klimaatmonitor › Droogte | Bodemkaart, GLG | externe laag, geen levering | PDOK/BRO (open) |

**Persoonsgegevens:** de GeoVisia-export bevat projectleider, e-mail, telefoon en aangemaakt/gewijzigd door. De levering neemt alleen een vaste lijst velden over (`behoud`); de rest gaat er in de ETL uit, niet pas in de viewer.

**Met een database-dump van de monitor** (`$SWF_DB_DUMP`, als tweede bron naast de export): de laagdefinities en rechten per rol (welke lagen intern zijn).

## Data

| Dataset | Route | Profiel | Formaat | Bron | Toegang | Licentie | Rol |
|---|---|---|---|---|---|---|---|
| [`swf-laag-extern`](datasets/swf-laag-extern.json) | beheer | externe-kaartlagen | datapackage ([schema](externe-kaartlagen.schema.json)) | repo: [`data/externe_kaartlagen.json`](data/) (lokale D-OmniTwin-database) | open (per laag `toegang`) | volgt de dienst (PDOK) | `realm-rol beheerder` |
| [`swf-laag-deelgebieden`](datasets/swf-laag-deelgebieden.json) | laden | kaartlaag | geopackage | repo (data-upload/) | open | onbekend (navragen) | `dataset:swf-laag-deelgebieden:laden` |
| [`swf-laag-coordinatorgebieden`](datasets/swf-laag-coordinatorgebieden.json) | laden | kaartlaag | geopackage | SWF projectmap ($SWF_DOCS_DIR) | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-laag-coordinatorgebieden:laden` |
| [`swf-laag-afstand-tot-koelte`](datasets/swf-laag-afstand-tot-koelte.json) | laden | kaartlaag | geopackage | SWF-bewerking ($SWF_DOCS_DIR) | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-laag-afstand-tot-koelte:laden` |
| [`swf-laag-risico-paalrot`](datasets/swf-laag-risico-paalrot.json) | laden | kaartlaag | geopackage | SWF-bewerking ($SWF_DOCS_DIR) | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-laag-risico-paalrot:laden` |
| [`swf-laag-projecten-vlak`](datasets/swf-laag-projecten-vlak.json) | laden | kaartlaag | geopackage | GeoVisia-export ($SWF_DOCS_DIR) | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-laag-projecten-vlak:laden` |
| [`swf-laag-projecten-punt`](datasets/swf-laag-projecten-punt.json) | laden | kaartlaag | geopackage | GeoVisia-export ($SWF_DOCS_DIR) | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-laag-projecten-punt:laden` |
| [`swf-laag-projecten-lijn`](datasets/swf-laag-projecten-lijn.json) | laden | kaartlaag | geopackage | GeoVisia-export ($SWF_DOCS_DIR) | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-laag-projecten-lijn:laden` |
| [`swf-laag-grootgrondbezit`](datasets/swf-laag-grootgrondbezit.json) | laden | kaartlaag | geopackage | SWF-intern: export GeoServer ($SWF_GEO_DIR) | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-laag-grootgrondbezit:laden` |

Verwacht:

- `swf-laag-deelgebieden`: features 6; toegang PUBLIC
- `swf-laag-coordinatorgebieden`: features 146; toegang RESTRICTED; weggelaten 1 geometrie zonder vlak (geometrie-geen-vlak)
- `swf-laag-afstand-tot-koelte`: features 41.778 (41.956 in de bron, 178 zonder geometrie); toegang RESTRICTED (open vraag 13)
- `swf-laag-risico-paalrot`: features 289
- `swf-laag-projecten-vlak`: features 148; persoonsvelden 0
- `swf-laag-projecten-punt`: features 15
- `swf-laag-projecten-lijn`: features 1

### Lokaal gecontroleerd

`python -m omnitwin.usecases controleer swf-kaartlagen` op 02-10-2026 (export van februari 2026, open bronnen van die dag). Alleen aantallen, geen meetwaarden.

| Dataset | Bron → levering | Resultaat |
|---|---|---|
| swf-laag-deelgebieden | 6 | geldig |
| swf-laag-coordinatorgebieden | 147 → 146 | geldig |
| swf-laag-afstand-tot-koelte | 41.956 → 41.778 (178 lege geometrieën) | geldig (sleutel: volgnummer) |
| swf-laag-risico-paalrot | 289 | geldig (sleutel: volgnummer) |
| swf-laag-projecten-vlak / -punt / -lijn | 164 → 148 / 15 / 1 | geldig; alleen de vaste lijst velden, geen persoonsvelden |
| swf-laag-grootgrondbezit | – | overgeslagen: SWF_GEO_DIR niet gezet |

**Externe lagen uit de repo** (`swf-laag-extern`, 5 kB): 8 WFS/WMS-lagen (PDOK: BAG woonplaatsen, Natura 2000, RCE, BRT, BRO Bodemkaart, bodemdaling, fiets- en wandelnetwerken) zoals de projectleider ze heeft ingericht (B1: eerste opzet). De data komt van de dienst, met de licentie van die dienst. Per laag `toegang` (B3: GeoVisia en projecten 'in plan' intern; in de lokale database staat geen GeoVisia-laag, die komt uit `swf-laag-projecten-*`). De lokale laag *Omgevingsvisie SWF* gaat niet mee: die komt als `swf-laag-deelgebieden`. Via de beheerroute in-process: aanvullen, een laag met dezelfde naam blijft. Herkomst: de lokale D-OmniTwin-database van de projectleider (dump van 04-10-2026), openbaar volgens besluit van de projectleiding (https://github.com/TLaan/D-OmniTwin/issues/222). Het bestand staat in [`data/`](data/) met `herkomst.json` (aantallen, controlesom); vervangen bij een nieuwere dump met [`scripts/beheer/swf_export.py --repo`](../../scripts/beheer/swf_export.py) en een PR.

## Stappen

1. Levering(en) maken en lokaal controleren tegen het profiel (zonder API):
   ```bash
   python -m omnitwin.usecases controleer swf-kaartlagen --uit /tmp/swf-kaartlagen
   ```
2. Token halen (client credentials; tokenendpoint uit `/.well-known/openid-configuration` van realm `omnitwin`):
   ```bash
   TOKEN=$(curl -s -u "$CLIENT_ID:$CLIENT_SECRET" -d grant_type=client_credentials \
     https://omnitwin.example.nl/auth/realms/omnitwin/protocol/openid-connect/token | jq -r .access_token)
   API=https://omnitwin.example.nl/api/laden/v1
   ```
3. Registreren (eenmalig, realm-rol `beheerder`; de uitvoerder stuurt alleen `id`, `bronId`, `beschrijving` en `laadprofiel`):
   ```bash
   jq '{id, bronId, beschrijving, laadprofiel}' datasets/swf-laag-deelgebieden.json | \
     curl -s -X POST "$API/datasets" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d @-
   ```
   Daarna in Keycloak de client-rol `dataset:swf-laag-deelgebieden:laden` op `omnitwin-api` aanmaken en toekennen aan de machineclient `etl-swf`.
4. Leveren:
   ```bash
   curl -s -X POST "$API/datasets/swf-laag-deelgebieden/leveringen?wacht=true" -H "Authorization: Bearer $TOKEN" \
     -H "Idempotency-Key: swf-laag-deelgebieden-$(date +%Y%m%d)" -H "Content-Type: application/geopackage+sqlite3" \
     --data-binary @/tmp/swf-kaartlagen/swf-laag-deelgebieden/swf-laag-deelgebieden.gpkg
   ```
5. Status volgen: `curl -s "$API/leveringen/<id>" -H "Authorization: Bearer $TOKEN" | jq '{status, versie, aantallen}'`.
6. Controleren in de API en de viewer (zie Acceptatiecriteria). Overige datasets van deze use case op dezelfde manier.

## Acceptatiecriteria

| # | Type | Wat | Verwacht |
|---|---|---|---|
| 1 | aantal | `swf-laag-deelgebieden` | gelijk 6 |
| 2 | aantal | `swf-laag-coordinatorgebieden` — 147 in de bron; 1 geometrie zonder vlak valt af | gelijk 146 |
| 3 | aantal | `swf-laag-risico-paalrot` | gelijk 289 |
| 4 | aantal | `swf-laag-afstand-tot-koelte` | gelijk 41778 |
| 5 | aantal | `swf-laag-projecten-vlak` | gelijk 148 |
| 6 | aantal | `swf-laag-projecten-punt` | gelijk 15 |
| 7 | aantal | `swf-laag-projecten-lijn` | gelijk 1 |
| 8 | api | `GET /api/geo/v1/collections/laag.swf_laag_deelgebieden/items?limit=1` (anoniem) — open laag: anoniem zichtbaar | HTTP 200, ≥ 1 resultaten |
| 9 | api | `GET /api/geo/v1/collections/laag.swf_laag_projecten_vlak/items?limit=1` (anoniem) — interne laag: anoniem 401, ook bij een directe aanroep | HTTP 401 |
| 10 | viewer | inloggen als medewerker, laaggroep 'Wat speelt er allemaal?' aanzetten | projecten zichtbaar, pop-up zonder namen, e-mail of telefoon |
| 11 | viewer | zonder inloggen de lagenlijst openen | alleen open lagen (deelgebieden, PDOK-lagen) |

`aantal` en `bewerking` controleert `controleer` nu al op de lokaal gemaakte levering; de andere vragen de laad-API en een draaiende installatie.

## Bewijs

In [`bewijs/`](bewijs/README.md), gemaakt door de uitvoerder (niet in git): `controle.json` (uitvoer van `controleer`), per levering de status-JSON van de laad-API (`levering-<dataset>.json`: status, versie, aantallen, fouten), en screenshots van de viewer-controles.

## Bekende afwijkingen

- Rasterlagen gaan niet via de laad-API (profiel kaartlaag is vector): waterdiepte bij intense neerslag (Klimaateffectatlas, open WMS), maaiveldhoogte AHN4 (PDOK, open), schaduwkaart en heatmaps wateroverlast blijven externe lagen.
- Profiel kaartlaag heeft één geometrietype per tabel: de GeoVisia-projecten worden drie datasets (vlak, punt, lijn). Overweeg meer tabellen per kaartlaag in profiel v2.
- Toegang: dct:accessRights PUBLIC/RESTRICTED in de registratie; de beveiligde geo-route (forwardAuth) en de rol voor interne lagen bestaan nog niet. Welke lagen intern zijn, is open vraag 13.
- GeoVisia bevat persoonsvelden (projectleider, e-mail, telefoon, aangemaakt/gewijzigd door): de levering neemt alleen een vaste lijst velden over. Vrije tekst (projectomschrijving) kan nog namen bevatten: DPIA-toets.
- Grootgrondbezit (BRK-afgeleid) en de klimaatbewerkingen: herkomst en licentie navragen; grootgrondbezit alleen zonder natuurlijke personen.

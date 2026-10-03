# TC-07-005 — SWF-kompasprofielen Basis (4/12/33) en Klimaat

**Status:** ontwerp (de laad-API is nog niet gebouwd; deze use case is de specificatie en straks de acceptatietest)
**Versie:** 0.2.0 · **Afhankelijk van:** [swf-definities](../swf-definities/README.md)
**Manifest:** [`usecase.json`](usecase.json) · **Controleren:** `python -m omnitwin.usecases controleer swf-kompasprofiel`

## Vraag

- **Gebruiker:** functioneel beheerder SWF
- **Vraag:** "Ik wil de sunburst van de huidige monitor terugzien in D-OmniTwin: dezelfde 4 kwadranten, 12 thema's en 33 onderdelen met dezelfde indicatoren, en de Klimaatmonitor met zijn 3 thema's en 10 indicatoren."
- **Rechten:** `realm-rol beheerder (beheer-API, machineclient of beheer-UI)`

**Keuze: via beheer, niet via een laad-API-profiel.** Het kompasprofiel (kwadrant › thema › onderdeel › indicator, en de classificatie) is inrichting, geen brondata (ADR 0003). Het zit niet in de push van de DWH (eis E17), verandert zelden, is van de functioneel beheerder en wordt ook nu in een beheeromgeving gemaakt. Een vijfde laad-API-profiel zou het onderscheid tussen data en inrichting vervagen. De levering is wel een Data Package met een eigen Table Schema ([kompasprofiel.schema.json](kompasprofiel.schema.json)), zodat hij net zo te controleren is. Voorstel voor de beheer-API: `PUT /api/beheer/v1/kompasprofielen/{profiel}` met dit pakket, realm-rol `beheerder`.

**Bron:** de voortgangslijst per indicator van het data-team van SWF (kwadrant, thema, onderdeel, extra niveau, naam), gekoppeld op naam aan de definities. Met een database-dump van de monitor (`$SWF_DB_DUMP`) komt de echte monitorconfiguratie, inclusief volgorde.

**Met een database-dump van de monitor** (`$SWF_DB_DUMP`, als tweede bron naast de export): de monitorconfiguratie zelf (de 215 indicatoren van de live sunburst, volgorde en de twee monitors), in plaats van de voortgangslijst.

## Data

| Dataset | Route | Profiel | Formaat | Bron | Toegang | Licentie | Rol |
|---|---|---|---|---|---|---|---|
| [`swf-kompas-basis`](datasets/swf-kompas-basis.json) | beheer | kompasprofiel | datapackage | voortgangslijst ($SWF_DUMP_DIR/data) + definities (swf-dump) | beperkt (inloggen) | onbekend (navragen) | `realm-rol beheerder` |
| [`swf-kompas-klimaat`](datasets/swf-kompas-klimaat.json) | beheer | kompasprofiel | datapackage | mapping in de use case (klimaat-indicatoren.json) | beperkt (inloggen) | onbekend (navragen) | `realm-rol beheerder` |

Verwacht:

- `swf-kompas-basis`: regels 219; unieke indicatoren 211; kwadranten 4; themas 12; onderdelen 33; weggelaten 5 oude werktitels, 1 testregel, 4 regels zonder plek
- `swf-kompas-klimaat`: regels 10; themas 3

### Lokaal gecontroleerd

`python -m omnitwin.usecases controleer swf-kompasprofiel` op 02-10-2026 (export van februari 2026, open bronnen van die dag). Alleen aantallen, geen meetwaarden.

| Dataset | Bron → levering | Resultaat |
|---|---|---|
| swf-kompas-basis | 229 regels → 219 (5 oude werktitels, 1 testregel, 4 zonder plek); 4 kwadranten, 12 thema's, 33 onderdelen, 211 unieke UUID's; alle gekoppeld | geldig |
| swf-kompas-klimaat | 10 | geldig |

## Stappen

1. Levering maken en lokaal controleren (zonder API):
   ```bash
   SWF_DUMP_DIR=… python -m omnitwin.usecases controleer swf-kompasprofiel --uit /tmp/swf-kompasprofiel
   ```
2. Token halen voor een machineclient met realm-rol `beheerder` (client credentials):
   ```bash
   TOKEN=$(curl -s -u "$CLIENT_ID:$CLIENT_SECRET" -d grant_type=client_credentials \
     https://omnitwin.example.nl/auth/realms/omnitwin/protocol/openid-connect/token | jq -r .access_token)
   ```
3. Kompasprofiel inlezen via de beheer-API (voorstel, nog niet gespecificeerd):
   ```bash
   curl -s -X PUT "https://omnitwin.example.nl/api/beheer/v1/kompasprofielen/swf-basis" -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/zip" --data-binary @/tmp/swf-kompasprofiel/swf-kompas-basis/swf-kompas-basis.zip
   ```
4. Controleren in de viewer en via `GET /api/beheer/v1/kompasprofielen` (zie Acceptatiecriteria).

## Acceptatiecriteria

| # | Type | Wat | Verwacht |
|---|---|---|---|
| 1 | aantal | `swf-kompas-basis` — 219 plekken (211 unieke indicatoren) in 4 kwadranten, 12 thema's en 33 onderdelen | gelijk 219 |
| 2 | bewerking | `swf-kompas-basis`: regels met reden `indicator-niet-in-definities` — elke indicator in de hiërarchie heeft een definitie (koppeling op naam, spaties en hoofdletters genegeerd) | gelijk 0 |
| 3 | bewerking | `swf-kompas-basis`: regels met reden `oude-werktitel` | gelijk 5 |
| 4 | bewerking | `swf-kompas-basis`: regels met reden `zonder-plek-in-hierarchie` | gelijk 4 |
| 5 | aantal | `swf-kompas-klimaat` | gelijk 10 |
| 6 | api | `GET /api/beheer/v1/kompasprofielen` (met token) — SWF Basis en SWF Klimaat bestaan | HTTP 200, ≥ 2 resultaten |
| 7 | viewer | Kompas 'SWF Basis' openen voor Bolsward-Zuidoost | 4 kwadranten, 12 thema's, 33 onderdelen; indicatoren zonder waarde grijs en benoemd |
| 8 | viewer | Kompas 'SWF Klimaat' openen voor een welstand × buurt in Bolsward | 3 thema's met 10 indicatoren; label A–E zodra de drempels bekend zijn |

`aantal` en `bewerking` controleert `controleer` nu al op de lokaal gemaakte levering; de andere vragen de laad-API en een draaiende installatie.

## Bewijs

In [`bewijs/`](bewijs/README.md), gemaakt door de uitvoerder (niet in git): `controle.json` (uitvoer van `controleer`), per levering de status-JSON van de laad-API (`levering-<dataset>.json`: status, versie, aantallen, fouten), en screenshots van de viewer-controles.

## Bekende afwijkingen

- Route beheer, geen dataset: het kompasprofiel is inrichting (ADR 0003), geen brondata; het staat niet in de push van de DWH (eis E17) en wordt ook nu in een beheeromgeving gemaakt. De beheer-API (/api/beheer/v1) heeft hiervoor nog geen endpoint; voorstel: PUT /api/beheer/v1/kompasprofielen/{profiel} met dit Data Package.
- De voortgangslijst is de beste bron van de hiërarchie zolang er geen database-dump van de monitor is; met $SWF_DB_DUMP komt de monitorconfiguratie zelf (inclusief volgorde en de 215 van de live sunburst).
- Drempels voor de labels A–E zijn onbekend (gat-analyse, vraag 5); classificatie 'label' zonder drempels.

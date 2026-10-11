# TC-07-003 — SWF-definities: indicatoren, gebiedstypen en relaties

**Status:** actief (via de laad-API; zonder bron overgeslagen)
**Versie:** 0.5.0 · **Afhankelijk van:** –
**Manifest:** [`usecase.json`](usecase.json) · **Controleren:** `python -m omnitwin.usecases controleer swf-definities`

## Vraag

- **Gebruiker:** data-engineer DWH (SWF)
- **Vraag:** "Ik wil alle 228 indicatordefinities van de huidige monitor met dezelfde UUID's in D-OmniTwin, met de 11 gebiedstypen en op welk gebiedstype elke indicator waarden heeft."
- **Rechten:** `realm-rol beheerder (registreren)`, `dataset:swf-monitor-definities:laden`

De eerste stap van de huidige stroom (eerst definities, dan waarden): de volledige set indicatoren, gebiedstypen en relaties uit de datamart, met dezelfde UUID's. Geleverd als Data Package-zip (drie CSV-resources) op de gewone ingang; de FME-route met hetzelfde formaat als nu staat in [swf-adapter-fme](../swf-adapter-fme/README.md). Beide leveren op dezelfde dataset `swf-monitor-definities`.

**UUID-conflict `d210c084…`:** in de stuurdata van D-OmniTwin is dit "Custom Gebied Type" (code `CUSTOM`, nergens in de code gebruikt); in de monitor "CBS buurten bebouwde komgrens" met 2.370 waarden. De levering zet naam, code (`CBS_BUURT_BBK`) en niveau via een upsert op `id`; de monitor is de bronhouder van deze UUID. De stuurdata moet mee, zodat een verse installatie niet weer "Custom Gebied Type" zet.

**Statussen (besluit [#341](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/341)).** In de monitor is `A` Actueel, `B` Buiten gebruik, `C` Concept en `O` Onderzoek (A2, [#222](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/222)). D-OmniTwin kent `C` (concept), `O` (operationeel) en `B` (beëindigd). Alleen `A` is openbaar; Concept en Onderzoek zijn alleen intern zichtbaar (ingelogd met de rol lezer of beheerder, ADR 0010).

| Monitor | Bewerking | D-OmniTwin | Toegang |
|---|---|---|---|
| A (Actueel) | `status-a` | O | openbaar |
| O (Onderzoek) | `status-onderzoek` (vóór `status-a`) | C | intern |
| C (Concept) | – | C | intern |
| B (Buiten gebruik) | – | B | openbaar (beëindigd) |

Een indicator met status `C` krijgt toegang `intern` (migratie `V042__concept_indicator_intern.sql`), zijn waarden ook. D-OmniTwin kent geen aparte status Onderzoek: het onderscheid Onderzoek/Concept zit daarna alleen nog in de bron. Een correctie is alleen een andere `map` in de bewerking.

**Dubbele UUID's (A4).** Twee namen hebben in de export twee UUID's. De bewerking `dubbele-naam` (`ontdubbel`) houdt per naam de UUID uit een vaste voorkeurslijst aan; de andere krijgt status `B` en de naam *"&lt;naam&gt; (vervallen)"*, zodat hij in lijsten niet meer met de goede te verwarren is. De lijst is data in [`datasets/swf-monitor-definities.json`](datasets/swf-monitor-definities.json); een dubbele naam die er niet in staat, blijft ongewijzigd en telt onder `dubbele-naam-zonder-voorkeur` (controle: 0).

| Naam | Houd aan | Wordt `B`, "(vervallen)" | Waarom |
|---|---|---|---|
| Waterdiepte op straat | `c4e1b3bb-e4ce-4cd0-bd52-219f4a9f5df3` (monitor C → O, bewerking `waterdiepte-actief`) | `f6eafa70-9383-4de6-bd2a-e47309843437` | beide zonder waarden; `c4e1b3bb…` staat in de geldige Klimaat- en Basismonitor (besluit [#341](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/341), productie-werkelijkheid; was `f6eafa70…`) |
| Werkzamen | `7fd17589-46b6-460a-a1f6-ef421517ccb3` | `ca06d8ad-6430-4f4d-bb32-7b406d26ecc8` | alleen `7fd17589…` heeft waarden (CBS-buurten) |

Een UUID wijzigen kan alleen aan de bronkant (DWH/FME), omdat de push en de profielen ernaar verwijzen; dat is een actie voor SWF-beheer. Daarna vervalt de regel in de voorkeurslijst. Definitieve verificatie van *Waterdiepte op straat* zodra beide in de monitor zitten.

**Mapping gebiedstypen** (`gebiedstypen.json`, statisch): per gebiedstype een unieke code (`gebiedstypes.code` is uniek), het niveau, de dataset die de gebieden levert en een prefix voor codes die niet landelijk uniek zijn (welstand `WS`, woonplaats `WP`, postcode `PC`, bebouwde kom `BK`).

**Met de database-dump van de monitor** (`$SWF_DB_DUMP`, variant `monitor-database`, heeft voorrang; [#316](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/316)): dezelfde drie tabellen uit de database van de monitor, plus `score_type` uit `omkeren` in de actieve monitorconfiguraties (`true` = `-/+`, lager is beter; `false` = `+/+`). Eenheid, bron en code staan ook in de database niet. Exporteren: [`scripts/beheer/swf_monitor_dump.py`](../../scripts/beheer/swf_monitor_dump.py) `exporteer --dump public.monitor.dmp --uit <map>` (geen database nodig; `pg_restore` alleen om het custom format te lezen), daarna `SWF_DB_DUMP=<map>`. De map bevat echte data en komt nooit in git.

Vergelijking dump (09-10-2026) met de export (februari 2026), alleen structuur en aantallen:

| | Export feb. 2026 | Database-dump 09-10-2026 |
|---|---|---|
| indicatoren / gebiedstypen / relaties | 228 / 11 / 263 | 228 / 11 / 263, dezelfde UUID's en namen van de gebiedstypen |
| status A / O / C / B | 10 / 212 / 5 / 1 | 20 / 200 / 5 / 3 |
| andere naam bij dezelfde UUID | – | 9: de leeftijdsgroepen (bijv. *0-3 jaar* → *0-15 jaar*) en opleidingsniveaus (*laag/middelhoog/hoog* → *Basisonderwijs, vmbo, mbo1* enz.) |
| met eindgeldigheid | 9 | 9 (dezelfde, 14-01-2025) |
| dubbele namen (A4) | 2 | 2 (dezelfde) |

Nieuw met status A: de vijf leeftijdsgroepen, drie opleidingsniveaus, *diefstal fiets* en *inbraak auto*; hun voorgangers *diefstal fietsen* en *inbraak auto's* zijn B. In de actieve Klimaatmonitor én de Basis monitor van de dump staat *Waterdiepte op straat* met `c4e1b3bb…` (status C), niet met `f6eafa70…`; daarom houdt D-OmniTwin sinds [#341](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/341) `c4e1b3bb…` aan.

## Data

| Dataset | Route | Profiel | Formaat | Bron | Toegang | Licentie | Rol |
|---|---|---|---|---|---|---|---|
| [`swf-monitor-definities`](datasets/swf-monitor-definities.json) | laden | definities | datapackage | export van de huidige monitor ($SWF_DUMP_DIR) | open | onbekend (navragen) | `dataset:swf-monitor-definities:laden` |

Verwacht:

- `swf-monitor-definities`: indicatoren 228; gebiedstypen 11; relaties 263; status A naar O 10; status O naar C 212 (dump: 200); dubbele naam naar B 2

### Lokaal gecontroleerd

`python -m omnitwin.usecases controleer swf-definities` op 02-10-2026 (export van februari 2026, open bronnen van die dag). Alleen aantallen, geen meetwaarden.

| Dataset | Bron → levering | Resultaat |
|---|---|---|
| swf-monitor-definities | 228 indicatoren, 11 gebiedstypen, 263 relaties; status A → O: 10 | geldig (Table Schema en foreign keys) |
| *database-dump* (`SWF_DB_DUMP`, 10-10-2026, dump van 09-10-2026) | 228 indicatoren, 11 gebiedstypen, 263 relaties; status A → O: 20; dubbele naam: 2; score_type: 53 | geldig |

## Stappen

1. Levering(en) maken en lokaal controleren tegen het profiel (zonder API):
   ```bash
   python -m omnitwin.usecases controleer swf-definities --uit /tmp/swf-definities
   ```
2. Token halen (client credentials; tokenendpoint uit `/.well-known/openid-configuration` van realm `omnitwin`):
   ```bash
   TOKEN=$(curl -s -u "$CLIENT_ID:$CLIENT_SECRET" -d grant_type=client_credentials \
     https://omnitwin.example.nl/auth/realms/omnitwin/protocol/openid-connect/token | jq -r .access_token)
   API=https://omnitwin.example.nl/api/laden/v1
   ```
3. Registreren (eenmalig, realm-rol `beheerder`; de uitvoerder stuurt alleen `id`, `bronId`, `beschrijving` en `laadprofiel`):
   ```bash
   jq '{id, bronId, beschrijving, laadprofiel}' datasets/swf-monitor-definities.json | \
     curl -s -X POST "$API/datasets" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d @-
   ```
   Daarna in Keycloak de client-rol `dataset:swf-monitor-definities:laden` op `omnitwin-api` aanmaken en toekennen aan de machineclient `etl-swf`.
4. Leveren:
   ```bash
   curl -s -X POST "$API/datasets/swf-monitor-definities/leveringen?wacht=true" -H "Authorization: Bearer $TOKEN" \
     -H "Idempotency-Key: swf-monitor-definities-$(date +%Y%m%d)" -H "Content-Type: application/zip" \
     --data-binary @/tmp/swf-definities/swf-monitor-definities/swf-monitor-definities.zip
   ```
5. Status volgen: `curl -s "$API/leveringen/<id>" -H "Authorization: Bearer $TOKEN" | jq '{status, versie, aantallen}'`.
6. Controleren in de API en de viewer (zie Acceptatiecriteria). Overige datasets van deze use case op dezelfde manier.

## Acceptatiecriteria

| # | Type | Wat | Verwacht |
|---|---|---|---|
| 1 | aantal | `swf-monitor-definities`, resource `indicatoren` | gelijk 228 |
| 2 | aantal | `swf-monitor-definities`, resource `gebiedstypen` | gelijk 11 |
| 3 | aantal | `swf-monitor-definities`, resource `relaties` | gelijk 263 |
| 4 | bewerking | `swf-monitor-definities`: regels met reden `status: A → O` — 10 in de export van februari, 20 in de database-dump (A2: A = Actueel → O, openbaar) | minimaal 10 |
| 5 | bewerking | `swf-monitor-definities`: regels met reden `status: O → C` — SWF-status O (Onderzoek) → C, alleen intern (besluit #341); 212 in februari, 200 in de dump | minimaal 200 |
| 6 | bewerking | `swf-monitor-definities`: regels met reden `waterdiepte-actief` — Waterdiepte op straat `c4e1b3bb…` is operationeel (O), ook al geeft de monitor C (besluit #341) | gelijk 1 |
| 7 | bewerking | `swf-monitor-definities`: regels met reden `dubbele-naam` — Waterdiepte op straat (`f6eafa70…`) en Werkzamen (`ca06d8ad…`) → status B, naam '… (vervallen)' | gelijk 2 |
| 8 | bewerking | `swf-monitor-definities`: regels met reden `dubbele-naam-zonder-voorkeur` — elke dubbele naam staat in de voorkeurslijst | gelijk 0 |
| 9 | bewerking | `swf-monitor-definities`: regels met reden `gebiedstype-zonder-mapping` | gelijk 0 |
| 10 | api | `GET /api/data/v1/indicatoren?uuid=eq.97f53738-3439-4c28-8cac-046a52c65248&select=uuid,naam,status` (anoniem) — Oppervlak groen per inwoner (status A), zelfde UUID als in de monitor | HTTP 200, ≥ 1 resultaten |
| 11 | api | `GET /api/data/v1/gebiedstypes?id=eq.d210c084-506b-48b4-87c9-b7d4bf422553&select=naam,code` (anoniem) — UUID-conflict opgelost: d210c084 is 'CBS buurten bebouwde komgrens', niet meer 'Custom Gebied Type' | HTTP 200, ≥ 1 resultaten, code = CBS_BUURT_BBK, naam = CBS buurten bebouwde komgrens |
| 12 | api | `GET /api/data/v1/indicatoren?uuid=eq.c4e1b3bb-e4ce-4cd0-bd52-219f4a9f5df3&select=uuid,naam,status` (anoniem) — de aangehouden Waterdiepte op straat houdt naam en krijgt O, openbaar | HTTP 200, ≥ 1 resultaten, naam = Waterdiepte op straat, status = O |
| 13 | api | `GET /api/data/v1/indicatoren?uuid=eq.f6eafa70-9383-4de6-bd2a-e47309843437&select=uuid,naam,status` (anoniem) — de dubbele is vervallen | HTTP 200, ≥ 1 resultaten, naam = Waterdiepte op straat (vervallen), status = B |
| 14 | api | `GET /api/data/v1/indicatoren?uuid=eq.3773b795-25ea-4039-bd65-9baad76a1009&select=uuid,naam,status` (anoniem) — een indicator met SWF-status O (Onderzoek), hier Sporten, staat niet in de lijst | HTTP 200, ≤ 0 resultaten |
| 15 | api | `GET /api/data/v1/indicatoren?uuid=eq.3773b795-25ea-4039-bd65-9baad76a1009&select=uuid,naam,status,toegang` (beheerder) — dezelfde indicator | HTTP 200, ≥ 1 resultaten, status = C, toegang = intern |
| 16 | afkeuring | `swf-monitor-definities`, variant `status-a` — onbekende status A wordt afgekeurd; vorige versie blijft actief | 422, fout `schema-ongeldig`, niets gepubliceerd |
| 17 | idempotent | `swf-monitor-definities` twee keer leveren | zelfde versie, geen tweede publicatie |

`aantal` en `bewerking` controleert `controleer` nu al op de lokaal gemaakte levering; de andere vragen de laad-API en een draaiende installatie.

## Bewijs

<!-- bewijs:start -->
*Nog geen bewijs. Maken tegen een draaiende installatie: `python -m omnitwin.usecases bewijs swf-definities`.*
<!-- bewijs:end -->

## Bekende afwijkingen

- Status A wordt O (openbaar); O (Onderzoek) wordt C en is, net als C (Concept), alleen intern zichtbaar (besluit https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/341). Het onderscheid Onderzoek/Concept gaat in D-OmniTwin verloren.
- UUID d210c084: in de stuurdata van D-OmniTwin 'Custom Gebied Type' (code CUSTOM, nergens gebruikt); in de monitor 'CBS buurten bebouwde komgrens' met 2.370 waarden. De levering zet naam en code (CBS_BUURT_BBK); de stuurdata moet mee (migratie).
- Eenheid, richting, bron en code per indicator zitten niet in de export; aanvullen via beheer of het gewone profiel definities.
- Eén testdefinitie (status B) gaat mee zoals hij is. De twee dubbele namen: zie *Dubbele UUID's* hierboven (A4, Waterdiepte op straat volgens #341).
- Database-dump: 9 UUID's hebben een andere naam dan in februari (zelfde sleutel, andere betekenis). Dat hoort niet; melden bij DWH-beheer (een nieuwe betekenis = een nieuwe UUID, https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/340). D-OmniTwin volgt de actuele naam; de laadstraat logt per gewijzigde naam een waarschuwing (logger `omnitwin.laden.definities`).
- *Waterdiepte op straat*: D-OmniTwin houdt `c4e1b3bb…` aan (besluit https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/341), zoals de geldige monitors; swf-kompasprofiel en de stuurdata-drempels gebruiken die UUID, een vervallen `f6eafa70…` zet swf-kompasprofiel om.
- Database-dump: `score_type` uit `omkeren` (53 indicatoren) overschrijft de richting uit de stuurdata waar die anders is (besluit https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/342: de monitor is leidend voor de polariteit).

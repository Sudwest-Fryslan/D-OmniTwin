# TC-07-025 — SWF-initialisatie: eerste vulling uit de lokale D-OmniTwin-database

**Status:** ontwerp (de export bestaat nog niet; zie *Open vraag*)
**Versie:** 0.1.0 · **Afhankelijk van:** [swf-definities](../swf-definities/README.md), [cbs-gebiedsindelingen](../cbs-gebiedsindelingen/README.md), [swf-gebiedsindelingen](../swf-gebiedsindelingen/README.md)
**Manifest:** [`usecase.json`](usecase.json) · **Controleren:** `python -m omnitwin.usecases controleer swf-initialisatie`

## Vraag

- **Gebruiker:** projectleider en functioneel beheerder SWF
- **Vraag:** "Ik wil de SWF-installatie de eerste keer vullen met de rijkere data uit mijn lokale D-OmniTwin-database, via de laad-API en herhaalbaar, zonder open data of demodata mee te kopiëren."
- **Rechten:** `realm-rol beheerder (registreren)`, `dataset:swf-init-indicatoren:laden`, `dataset:swf-init-waarnemingen:laden`

Aanname A1 van https://github.com/TLaan/D-OmniTwin/issues/222: de eerste vulling bij SWF komt niet alleen uit de export van de huidige gebiedsmonitor (februari 2026), maar uit de lokale D-OmniTwin-database van de projectleider, die rijker is. De export van de monitor blijft de bron om van te leren (Kompas-hiërarchie, labels, laagrechten) en de route voor de doorlopende levering ([swf-adapter-fme](../swf-adapter-fme/README.md)).

Deze use case beschrijft die eerste vulling als gewone leveringen via de laad-API, zodat hij herhaalbaar en herleidbaar is (versies, herkomst, n-vlag) en niets buiten de laadstraat om in de database komt.

| Wat | Hoe |
|---|---|
| Indicatordefinities die alleen lokaal bestaan | dataset `swf-init-indicatoren` (profiel definities, alleen de resource `indicatoren`) |
| Indicatorwaarden | dataset `swf-init-waarnemingen` (profiel waarnemingen, vervangbereik indicator × gebiedstype) |
| SWF-definities, gebiedstypen, relaties | uit [swf-definities](../swf-definities/README.md) (afhankelijkheid), niet opnieuw |
| Gebiedsindelingen | uit [cbs-gebiedsindelingen](../cbs-gebiedsindelingen/README.md) en [swf-gebiedsindelingen](../swf-gebiedsindelingen/README.md); eigen indelingen uit de lokale database volgen per gebiedstype als dataset met profiel gebiedsindeling (GeoPackage) |
| Open data (CBS-kerncijfers e.d.) | niet uit de export: de adapter van [cbs-kerncijfers](../cbs-kerncijfers/README.md) downloadt zelf (geen afhankelijkheid: de volgorde maakt niet uit, de voorrang bij overlap beslist) |
| Demodata | niet uit de export: blijft in de eigen use cases, gemarkeerd `DEMODATA` (#236) |

**Bron.** De export staat onder `SWF_EXPORT_DIR` (allowlist van de uitvoerder, nooit in git). Zonder die variabele slaat `controleer` de datasets over; dat is geen fout. Verwachte bestanden:

| Bestand | Uit de lokale database | Kolommen |
|---|---|---|
| `gebied_data.csv` | tabel `gebied_data` | `gebied_id`, `indicator_uuid`, `jaar`, `peildatum`, `scenario_id`, `waarde`, `n`, `kwaliteit`, `bron` (precies één van `jaar` en `peildatum`) |
| `indicatoren.csv` | tabel `indicatoren` | `uuid`, `naam`, `code`, `omschrijving`, `eenheid`, `score_type`, `min_waarde`, `max_waarde`, `status`, `begingeldigheid`, `eindgeldigheid`, `bron` |

Voorbeeld van de export (met `psql` op de lokale database; alleen wat niet open is):

```sql
\copy (SELECT gebied_id, indicator_uuid, jaar, CASE WHEN jaar IS NULL THEN datum::date END AS peildatum,
              coalesce(scenario_id, 'current') AS scenario_id, waarde, n, kwaliteit, bron
       FROM gebied_data
       WHERE coalesce(bron, '') NOT LIKE 'DEMODATA%') TO 'gebied_data.csv' CSV HEADER
\copy (SELECT uuid, naam, code, omschrijving, eenheid, score_type, min_waarde, max_waarde, status,
              begingeldigheid, eindgeldigheid, bron
       FROM indicatoren
       WHERE uuid NOT IN (/* UUID's uit swf-definities en de stuurdata */)) TO 'indicatoren.csv' CSV HEADER
```

**Transformaties** (declaratief in `datasets/*.json`):

| Export | Levering | Regel |
|---|---|---|
| `bron` begint met `DEMODATA` | weggelaten (`demodata`) | demodata hoort bij de demo-use cases |
| `bron` begint met `CBS` | weggelaten (`open-data`) | open data downloadt de adapter; voorlopig herkend aan de bronvermelding |
| `gebied_id`, `scenario_id` | `gebied_code`, `scenario` | hernoemen |
| geen `n` | `n` leeg | `bijOntbrekendeN: bron-onderdrukt`; de drempel blijft in de ETL (aanname A7) |
| status `A` | `O` | zoals in swf-definities (aanname A2) |

**Overlap met andere bronnen** (aanname A6). Een waarde uit de initialisatie en een uit `cbs-kerncijfers` of `swf-monitor-waarden` op dezelfde sleutel (gebied × indicator × jaar of peildatum × scenario): de nieuwste bronpeildatum wint, bij een gelijke bronpeildatum de laatst aangeleverde levering. De bronpeildatum is `dct:modified` uit de `dcat.jsonld` van de levering, anders de datum van ontvangst. De andere waarde blijft zichtbaar als `andere_bronnen` (zie [voorrang bij overlap](../../docs/api/laden/README.md#voorrang-bij-overlap)). Zonder `dct:modified` wint de initialisatie dus van wat eerder geleverd is, en verliest hij van elke latere levering; dat is bedoeld.

**Toegang.** Beide datasets zijn `RESTRICTED` (intern): alles wat in de huidige monitor grijs of uit staat, is intern (aanname B3, https://github.com/TLaan/D-OmniTwin/pull/274). Openbaar maken is een wijziging van `dct:accessRights` per dataset.

**Na de initialisatie** de client `etl-initialisatie` intrekken. Doorlopende leveringen gaan via de FME-route ([swf-adapter-fme](../swf-adapter-fme/README.md)) en de open-data-use cases.

## Open vraag aan de projectleider

Welke tabellen en indicatoren lever je uit je lokale database: een CSV-export zoals hierboven, of liever een `pg_dump` van een paar tabellen (`indicatoren`, `gebied_data`, eventueel `gebieden` en `gebiedstypes` met eigen indelingen)? En welke indicatoren zijn alleen lokaal (niet in de monitor, niet open)? Dan maken we bron, bewerkingen en controles passend en zetten we de use case op `actief`.

## Data

| Dataset | Route | Profiel | Formaat | Bron | Toegang | Licentie | Rol |
|---|---|---|---|---|---|---|---|
| [`swf-init-indicatoren`](datasets/swf-init-indicatoren.json) | laden | definities | datapackage | export van de lokale D-OmniTwin-database ($SWF_EXPORT_DIR/indicatoren.csv) | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-init-indicatoren:laden` |
| [`swf-init-waarnemingen`](datasets/swf-init-waarnemingen.json) | laden | waarnemingen | datapackage | export van de lokale D-OmniTwin-database ($SWF_EXPORT_DIR/gebied_data.csv) | beperkt (inloggen) | onbekend (navragen) | `dataset:swf-init-waarnemingen:laden` |

## Stappen

1. Export maken op de lokale database (zie hierboven) en de map als `SWF_EXPORT_DIR` zetten.
2. Leveringen maken en lokaal controleren tegen het profiel (zonder API):
   ```bash
   SWF_EXPORT_DIR=/pad/naar/export python -m omnitwin.usecases controleer swf-initialisatie --uit /tmp/swf-initialisatie
   ```
3. Machineclient voor de eerste vulling (eenmalig): `docker compose exec keycloak bash /opt/keycloak/omnitwin/machineclient.sh etl-initialisatie dataset:swf-init-indicatoren:laden dataset:swf-init-waarnemingen:laden`; registreren doet de beheerder.
4. Installeren met de afhankelijkheden (eerst definities en gebiedsindelingen, dan de initialisatie):
   ```bash
   SWF_EXPORT_DIR=/pad/naar/export python -m omnitwin.usecases installeer swf-initialisatie
   ```
5. Controleren in de API en de viewer (zie Acceptatiecriteria); daarna de client intrekken.

## Acceptatiecriteria

| # | Type | Wat | Verwacht |
|---|---|---|---|
| 1 | aantal | `swf-init-indicatoren`, resource `indicatoren` — de export bevat indicatordefinities | minimaal 1 |
| 2 | aantal | `swf-init-indicatoren`, resource `relaties` — relaties komen uit swf-definities | gelijk 0 |
| 3 | aantal | `swf-init-waarnemingen` — waarden die niet uit een open bron komen | minimaal 1 |
| 4 | bewerking | `swf-init-indicatoren`: reden `status: A → O` — de lokale database kent geen status A | maximaal 0 |
| 5 | api | `GET /api/data/v1/gebied_data?gebied_id=eq.BU19000002&select=indicator_uuid,bron,andere_bronnen&limit=1` — waarden op Bolsward-Zuidoost, met de tweede bron bij overlap | HTTP 200, ≥ 1 resultaten |
| 6 | idempotent | `swf-init-waarnemingen` twee keer leveren | zelfde versie, geen tweede publicatie |
| 7 | recht | `beheerder` registreert | toegestaan |
| 8 | recht | `etl-initialisatie` levert `swf-init-waarnemingen` | toegestaan |
| 9 | recht | `etl-initialisatie` levert `swf-monitor-waarden` | 403 |
| 10 | recht | `lezer` levert `swf-init-waarnemingen` | 403 |

`aantal` en `bewerking` controleert `controleer` op de lokaal gemaakte levering (alleen met `SWF_EXPORT_DIR`; anders overgeslagen); de andere vragen de laad-API en een draaiende installatie.

## Bewijs

<!-- bewijs:start -->
*Nog geen bewijs. Maken tegen een draaiende installatie: `python -m omnitwin.usecases bewijs swf-initialisatie`.*
<!-- bewijs:end -->

## Bekende afwijkingen

- Ontwerp: de export bestaat nog niet. Open vraag aan de projectleider: welke tabellen en indicatoren levert hij (CSV-export volgens deze README, of liever een `pg_dump` van een paar tabellen)? Daarna worden bron, bewerkingen en controles passend gemaakt.
- Open data (CBS) en demodata worden herkend aan de bronvermelding (`bron` begint met `CBS` of `DEMODATA`). Dat is voorlopig; liever levert de export alleen wat niet open is.
- Gebiedsindelingen komen uit cbs-gebiedsindelingen en swf-gebiedsindelingen. Levert de lokale database eigen indelingen, dan komt er per gebiedstype een dataset met profiel gebiedsindeling (GeoPackage onder `SWF_EXPORT_DIR`).
- Zonder `n` in de lokale database: vlag bron-onderdrukt, de drempel blijft in de ETL (aanname A7).
- De bronpeildatum van de export is de datum van ontvangst, tenzij `dcat.jsonld` een `dct:modified` meekrijgt; bij overlap met een nieuwere CBS- of monitorlevering wint die (aanname A6).

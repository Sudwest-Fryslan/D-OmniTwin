# TC-07-026 — SWF-gebruikersvoorkeuren: laatste kaartpositie uit de huidige monitor

**Status:** ontwerp (route via een beheerscript, geen dataset; getest met fictieve data)
**Versie:** 0.1.0 · **Afhankelijk van:** –
**Manifest:** [`usecase.json`](usecase.json) · **Controleren:** `python -m omnitwin.usecases controleer swf-gebruikersvoorkeuren`

## Vraag

- **Gebruiker:** medewerker die de huidige gebiedsmonitor gebruikt; functioneel beheerder SWF (overzetten)
- **Vraag:** "Als ik na de overstap voor het eerst inlog, wil ik de kaart terugzien waar ik in de oude gebiedsmonitor was gebleven, zonder dat mijn oude gebruikersnaam ergens bewaard blijft."
- **Rechten:** `realm-rol beheerder (koppeling maken, script draaien op de server)`, `realm-rol lezer (eigen voorkeuren)`

De huidige monitor bewaart per gebruiker een paar instellingen in de tabel `user_properties` (gebruikersnaam, sleutel, waarde). D-OmniTwin heeft daarvoor `gebruiker_voorkeuren` (V035, [#258](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/258)), met als sleutel alleen de `sub` van Keycloak (of `lokaal:<id>`). Deze use case beschrijft de overzetting. Het gaat om persoonlijke gegevens: niet via de laad-API, niet via de portabiliteitspoort en niet in PostgREST. Daarom is er geen dataset maar een beheerscript, [`scripts/beheer/swf_monitor_dump.py`](../../scripts/beheer/swf_monitor_dump.py), op de server van de installatie.

## Wat er overgaat

| Sleutel in de monitor | Vorm | D-OmniTwin |
|---|---|---|
| `last_map_coordinate` | `{center: [x, y], resolution}`, RD (EPSG:28992), meter per pixel | `gebruiker_voorkeuren.kaartpositie` `{longitude, latitude, zoom}` (RD → WGS84 ±1 m, resolutie → MapLibre-zoom) |
| `selected_node_id` | id van de gekozen monitor (Basis of Klimaat) | geen plek; `niet_overgenomen.monitor` (naam van de monitor) |
| `active_item` | naam van het actieve paneel | geen plek; `niet_overgenomen.actief_paneel` |
| `panel_visible` | paneel open of dicht | geen plek; `niet_overgenomen.paneel_zichtbaar` |
| `visible_base_layer` | gekozen ondergrond | geen plek; `niet_overgenomen.basislaag` |

De monitor heeft geen favorieten in de database. Wat geen plek heeft, staat in `gebruikersvoorkeuren.json` onder `niet_overgenomen`, zodat er niets stil verdwijnt. Of D-OmniTwin daar een plek voor krijgt (bijvoorbeeld het standaard-Kompasprofiel per gebruiker), is een keuze van de beheerder.

## Koppeling oude gebruikersnaam → Keycloak

Een expliciete stap; het script raadt nooit.

1. `exporteer` schrijft `gebruikers-mapping.csv` in de exportmap: de oude gebruikersnamen met een lege kolom `eigenaar`.
2. De beheerder vult per gebruiker de `eigenaar` in: de **Keycloak-gebruikers-ID** (`sub`; Keycloak-beheer → Users → ID, of `kcadm.sh get users -r omnitwin -q email=<adres> --fields id`), of `lokaal:<users.id>` voor een lokaal account. Een e-mailadres of naam wordt geweigerd: D-OmniTwin bewaart alleen de `sub`.
3. Opnieuw `exporteer` met `--gebruikers-mapping`. Alleen gekoppelde gebruikers komen in `gebruikersvoorkeuren.json`; de rest telt als `niet_gekoppeld` in `export.json` (zonder namen).

## Stappen

Op de server, met de dump buiten de repo (bijv. `/tmp/swf-db-dump`); na afloop opruimen.

1. Export maken (pg_restore 16 of nieuwer, alleen om het custom format te lezen):
   ```bash
   python scripts/beheer/swf_monitor_dump.py exporteer --dump public.monitor.dmp --uit /tmp/swf-db-dump --dump-datum 2026-10-09
   ```
2. `/tmp/swf-db-dump/gebruikers-mapping.csv` invullen (zie hierboven) en opnieuw exporteren:
   ```bash
   python scripts/beheer/swf_monitor_dump.py exporteer --dump public.monitor.dmp --uit /tmp/swf-db-dump \
     --gebruikers-mapping /tmp/swf-db-dump/gebruikers-mapping.csv
   ```
3. Laden in de backend-container (aanvullen: wie D-OmniTwin al gebruikt, houdt zijn eigen voorkeuren). Eerst droog:
   ```bash
   docker compose cp /tmp/swf-db-dump/gebruikersvoorkeuren.json backend:/tmp/gebruikersvoorkeuren.json
   docker compose exec backend python scripts/beheer/swf_monitor_dump.py laad-voorkeuren /tmp/gebruikersvoorkeuren.json --droog
   docker compose exec backend python scripts/beheer/swf_monitor_dump.py laad-voorkeuren /tmp/gebruikersvoorkeuren.json
   docker compose exec backend rm /tmp/gebruikersvoorkeuren.json
   ```
4. Opruimen: `rm -r /tmp/swf-db-dump` en de dump.

De rest van de export (definities, waarden, Kompas, drempels) gebruiken de andere swf-use cases via `SWF_DB_DUMP`; zie [swf-definities](../swf-definities/README.md).

## Acceptatiecriteria

| # | Type | Wat | Verwacht |
|---|---|---|---|
| 1 | api | `GET /api/mijn/instellingen` (anoniem) — voorkeuren zijn persoonlijk | HTTP 401 |
| 2 | viewer | inloggen als een gekoppelde gebruiker die D-OmniTwin nog niet gebruikte | de kaart opent op de laatste kaartpositie uit de oude monitor |
| 3 | viewer | inloggen als een gebruiker zonder koppeling, of die D-OmniTwin al gebruikte | de eigen (of standaard) kaartpositie; de overzetting overschrijft niets |

Op 10-10-2026 tegen een verse database (db-init, migraties tot V035) uitgevoerd met de fictieve data: `laad-voorkeuren` voegt 2 rijen toe, een tweede run telt ze als `al_aanwezig` (idempotent, niets overschreven). De omzetting en de koppeling zijn getest met fictieve data in [`tests/test_swf_monitor_dump.py`](../../tests/test_swf_monitor_dump.py) (`tests/data/swf_monitor_dump/`: `voorbeeld.gebruiker1` gekoppeld aan een sub, `voorbeeld.gebruiker2` aan `lokaal:7`, `voorbeeld.gebruiker3` niet gekoppeld).

## Bewijs

<!-- bewijs:start -->
*Nog geen bewijs. Maken tegen een draaiende installatie: `python -m omnitwin.usecases bewijs swf-gebruikersvoorkeuren`.*
<!-- bewijs:end -->

## Bekende afwijkingen

- Geen dataset: persoonlijke gegevens gaan niet via de laad-API of de portabiliteitspoort (V035). Het beheerscript zet ze over.
- Alleen de laatste kaartpositie heeft een plek in D-OmniTwin. Monitorkeuze, actief paneel, paneel open/dicht en basislaag staan in `gebruikersvoorkeuren.json` onder `niet_overgenomen` tot de beheerder beslist ([#316](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/316)).
- Een overgezette rij valt onder dezelfde opruimregel als elke voorkeur: na 365 dagen zonder gebruik verwijderd.
- In git staat alleen fictieve voorbeelddata.

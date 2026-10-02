# db — schema, migraties en stuurdata

```
db/
├── schema/          # schema voor een lege database (db-init)
│   ├── schema_latest.sql              # tabellen, views, functies (baseline)
│   ├── 06_pg_featureserv_views.sql    # views voor pg_featureserv (kaart)
│   ├── 07_postgisftw_functions.sql    # functies onder /api/geo/functions
│   ├── 08_zscore_referentie.sql       # Z-score-referentie en waterbuurt; geladen door V021
│   └── 05_indicator_stats.sql         # get_indicatoren_stats (zit ook in schema_latest.sql)
├── migraties/
│   ├── V018__trigram.sql … V022__auth_hardening.sql   # door de runner, één keer per database
│   ├── R__api_rollen.sql              # rollen en schema api: bij elke start van db-init
│   └── baseline/                      # oude migraties, zitten al in schema_latest.sql; niet uitgevoerd
└── stuurdata/
    ├── stuurdata_seed.sql             # configuratie, scenario's, profielen, kleuren, prompts
    ├── kompas_hierarchie.csv          # Kompas-indeling
    ├── indicatoren_seed.json          # indicatordefinities
    └── config_seed_fixed.sql          # alleen voor init_data/scripts/init_database.sh (zonder Docker)
```

## Migraties (#54)

`db-init` draait `python -m omnitwin.migraties` (`src/omnitwin/migraties.py`):

1. maakt zo nodig de tabel `schema_migraties` (`versie`, `naam`, `checksum`, `toegepast_op`);
2. past elke `V<versie>__<naam>.sql` toe die nog niet in die tabel staat, op volgorde van versie, met `psql` (`ON_ERROR_STOP`, één transactie per migratie inclusief de registratie);
3. waarschuwt als een toegepaste migratie sindsdien gewijzigd is (checksum, inclusief bestanden die met `\ir` worden geladen).

Twee runs tegelijk (bijv. twee keer `db-init` tegen dezelfde database) kan: de runner houdt een advisory lock (`pg_advisory_lock`) vast van het lezen van `schema_migraties` tot de laatste migratie. De tweede run meldt "Een andere migratierun is bezig", wacht en ziet daarna dat er niets meer te doen is. De lock hoort bij een eigen psql-sessie en vervalt ook als de runner crasht.

Bij een lege database gebeurt dit na `schema/schema_latest.sql`, `06` en `07`; bij een bestaande database direct. Een database zonder `schema_migraties` (van vóór 0.2.0) krijgt alle migraties één keer opnieuw: ze zijn idempotent.

```bash
docker compose run --rm db-init python -m omnitwin.migraties --status   # wat is toegepast, wat staat open
```

`--status` leest alleen: geen lock, en de tabel wordt niet aangemaakt. Een migratie die een ander bestand inleest, toont dat erachter, bijv. `V021 zscore_referentie  (+ db/schema/08_zscore_referentie.sql)`.

### Includes en de checksum (V021)

`V021__zscore_referentie.sql` bevat alleen `\ir ../schema/08_zscore_referentie.sql`. De checksum van V021 telt de inhoud van `08_zscore_referentie.sql` mee. Gevolg: wie `08` wijzigt, wijzigt ook de checksum van V021. Op elke database waar V021 al is toegepast, geeft de runner dan bij elke start de waarschuwing "V021 zscore_referentie is gewijzigd ... De checksum telt ook mee: db/schema/08_zscore_referentie.sql". V021 wordt niet opnieuw uitgevoerd, dus de wijziging komt er zo niet in.

Wil je de Z-score-functies wijzigen:

1. wijzig `08_zscore_referentie.sql` niet; zet de nieuwe definitie in een nieuwe migratie (`V0nn__zscore_referentie_<wat>.sql`, met `CREATE OR REPLACE`), of
2. als de functies vaker veranderen: maak van `08` een herhaalbaar bestand (`R__zscore_referentie.sql`, bij elke start, zoals `R__api_rollen.sql`) en bevries V021. Dat vraagt een aanpassing in `docker-entrypoint.sh` en is nog niet gedaan.

Een nieuwe migratie met dezelfde `\ir`-regel als V021 lost het niet op: V021 houdt dan de waarschuwing.

**Nieuwe schemawijziging:** voeg `V<volgend nummer>__<naam>.sql` toe, idempotent (`IF NOT EXISTS`, `CREATE OR REPLACE`). Pas een toegepaste migratie nooit aan; maak een nieuwe. `schema_latest.sql` hoeft niet mee: de runner past de migratie ook op een nieuwe database toe.

## Eerste initialisatie en eigenaar (#201)

- **Init-status:** de tabel `installatie_status` krijgt pas een rij als de eerste initialisatie helemaal gelukt is (schema, migraties, stuurdata, use cases, beheerder, rollen). Staan er tabellen in de database zonder die rij, dan stopt `db-init` met een foutmelding en herstelinstructie, in plaats van een lege stack te starten. Een installatie van vóór 0.2.1 met `gebieden` en een beheerder wordt herkend en krijgt de rij automatisch.
- **Eigenaar:** `schema_latest.sql` zet geen eigenaar en geen rechten voor een vaste rol. Alle objecten zijn van `DATABASE_USER`, de gebruiker die `db-init` draait; een andere naam dan `omnitwin_user` werkt dus ook. De rollen voor PostgREST en pg_featureserv maakt `R__api_rollen.sql`.

## Backup van geüploade kaartlagen

Bestanden die via beheer > externe lagen zijn geüpload staan in het volume `uploads` (in de container `/app/data-upload`), niet in de database. Neem ze mee in de backup:

```bash
docker compose cp backend:/app/data-upload ./backup-data-upload      # backup
docker compose cp ./backup-data-upload/. backend:/app/data-upload    # terugzetten
```

## Laad-API: schema `laden` en het volume `leveringen` (#228)

Migratie V024 maakt het schema `laden` (registraties, leveringen, versies, fouten, staging, de gepubliceerde waarnemingen per dataset) en de rol `laden_schrijver`. De laadstraat (`src/omnitwin/laden/`) schrijft alleen als die rol (`SET LOCAL ROLE`): in `laden` en in `gebied_data`, `gebieden`, `gebiedstypes`, `indicatoren`, `indicator_gebiedstype_relaties` en `externe_kaartlagen`. `gebied_data.levering_id` wijst naar de levering die de waarde publiceerde (leeg: geladen buiten de laad-API).

De ruwe leveringen staan in het volume `leveringen` (in de container `/leveringen`), ongewijzigd en alleen-lezen, met de bewaartermijn uit `LADEN_BEWAAR_*`. Neem het mee in de backup, samen met de database:

```bash
docker compose cp backend:/leveringen ./backup-leveringen      # backup
docker compose cp ./backup-leveringen/. backend:/leveringen    # terugzetten
```

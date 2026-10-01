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

Bij een lege database gebeurt dit na `schema/schema_latest.sql`, `06` en `07`; bij een bestaande database direct. Een database zonder `schema_migraties` (van vóór 0.2.0) krijgt alle migraties één keer opnieuw: ze zijn idempotent.

```bash
docker compose run --rm db-init python -m omnitwin.migraties --status   # wat is toegepast, wat staat open
```

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

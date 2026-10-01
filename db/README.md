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

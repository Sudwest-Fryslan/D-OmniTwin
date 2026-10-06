# Beheerhandleiding

Voor wie een D-OmniTwin-installatie in productie beheert. De [installatiegids](installatie.md) beschrijft installeren, `.env`, Keycloak aanzetten, HTTPS en beveiliging; deze handleiding gaat over het werk daarna: bijwerken, back-up en herstel, gebruikers en machineclients, leveringen, logs, certificaten, incidenten en een acceptatieomgeving. Waar de installatiegids het al uitlegt, staat hier een verwijzing.

Alle commando's draai je in de map van de installatie (naast `.env`), in een POSIX-shell (Linux, macOS, Git Bash op Windows).

Issue: [#257](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/257). Privacy: [privacy-quickscan](../5-secops/privacy-quickscan.md). Toegankelijkheid: [status](../4-ux-design/toegankelijkheid.md).

---

## 1. Dagelijks: status, health en logs

| Wat | Hoe |
|---|---|
| Containers | `docker compose ps -a`. Verwacht: `postgres`, `backend` (en `keycloak`) *healthy*; `db-init` (en `keycloak-db-init`) `Exited (0)`; de rest *Up*. |
| Health van de stack | `curl -fsS http://<host>/health` geeft `{"database":"online","api":"online","version":...}`. Geschikt voor een externe monitor (elke minuut, alarm na 3 keer fout). |
| AI-zoeken en model | `curl http://<host>/api/ai/health` (embeddingmodel, revisie, offline) |
| Kaart- en data-API | `http://<host>/api/geo/collections` en `http://<host>/api/data/gebiedstypes` geven 200 |
| Keycloak | `http://<host>/auth/realms/omnitwin/.well-known/openid-configuration` geeft JSON. De health-endpoints van Keycloak zitten op de interne poort 9000 en gebruikt de healthcheck van de container. |
| Containerlogs | `docker compose logs --tail 200 backend` (of `db-init`, `postgres`, `keycloak`, `traefik`). Docker bewaart die standaard onbeperkt; zet een limiet in de Docker-daemon (`log-opts`, bijvoorbeeld `max-size=50m`, `max-file=5`). |
| Applicatielog | Beheeromgeving > Logs (tabel `app_logs`). Een foutmelding aan een gebruiker bevat een correlatie-id; zoek die op in `docker compose logs backend`. Bewaartermijnen: zie de [privacy-quickscan](../5-secops/privacy-quickscan.md#welke-persoonsgegevens). |
| Schijfruimte | `docker system df`; de volumes `pgdata`, `leveringen` en `uploads` groeien. Oude images en build-cache: `docker image prune` en `docker builder prune`. |

Zie ook [Status en logs](installatie.md#status-en-logs) en [Problemen oplossen](installatie.md#8-problemen-oplossen).

---

## 2. Back-up en herstel

### Wat er bewaard moet worden

| Wat | Waar | In de back-up |
|---|---|---|
| Database (data, inrichting, gebruikers, logs, laadhistorie) | volume `pgdata`, database `DATABASE_NAME` | `database.dump` (`pg_dump -Fc`) |
| Keycloak (realm, gebruikers, clients, secrets) | database `keycloak` in dezelfde PostgreSQL | `keycloak.dump` (alleen met profiel `keycloak`) |
| Databaserollen | PostgreSQL | `rollen.sql`, zonder wachtwoorden |
| Ruwe leveringen van de laad-API | volume `leveringen` | `leveringen.tar.gz` |
| Geüploade kaartlagen | volume `uploads` | `uploads.tar.gz` |
| `.env` (wachtwoorden en sleutels) | de installatiemap | **nee**: bewaar `.env` apart, in een kluis |
| Download-cache van open data | volume `bron-cache` | nee, opnieuw te downloaden |

### Back-up maken

```bash
sh scripts/beheer/backup.sh
```

Het script ([`scripts/beheer/backup.sh`](../../scripts/beheer/backup.sh)) maakt `backups/omnitwin-<project>-<JJJJMMDD-UUMMSS>/` met de bestanden hierboven, een `info.txt` (datum, versie, laatste migratie, aantallen) en `SHA256SUMS`. Het controleert dat de dumps leesbaar zijn. Bij een fout ruimt het de halve back-up op en eindigt met exitcode 1. De stack blijft gewoon draaien.

| Instelling (`.env` of omgeving) | Standaard | Betekenis |
|---|---|---|
| `BACKUP_DIR` | `backups` | Doelmap. Staat in `.gitignore`. |
| `BACKUP_BEWAAR_DAGEN` | `30` | Back-ups van dit project die ouder zijn, worden na een geslaagde back-up verwijderd. `0` = niets verwijderen. |

Aanbevolen:

- **Dagelijks** via cron of een systemd-timer, bijvoorbeeld `15 2 * * * cd /opt/d-omnitwin && sh scripts/beheer/backup.sh >> /var/log/omnitwin-backup.log 2>&1`.
- **Kopie buiten de server** (een andere locatie of de back-upvoorziening van je organisatie). Een back-up op dezelfde schijf beschermt niet tegen verlies van de server.
- **Vóór elke update** een extra back-up (zie [Bijwerken](#3-bijwerken-en-terugrollen)).
- Een back-up bevat persoonsgegevens (accounts, gehashte wachtwoorden, logs met IP-adressen) en de Keycloak-secrets. Bewaar hem net zo zorgvuldig als `.env`: versleuteld en met beperkte toegang. De map krijgt rechten `700`.

### Herstellen

Herstel gaat naar een **lege installatie**: dezelfde of een nieuwere versie van D-OmniTwin, met een eigen `.env`. Een ander `DATABASE_PASSWORD` mag; `DATABASE_USER` moet gelijk zijn aan die in de back-up.

```bash
docker compose down -v          # alleen als hier nog een oude installatie staat: LET OP, wist alles
sh scripts/beheer/restore.sh backups/omnitwin-<project>-<stempel>
docker compose ps -a            # alles healthy?
```

[`restore.sh`](../../scripts/beheer/restore.sh) controleert eerst de controlesommen, start alleen `postgres`, weigert als de database al tabellen heeft (met `--overschrijf` gaat hij toch door en verdwijnt de huidige data), maakt de rollen aan, zet de database(s) en de volumes terug, vergelijkt de aantallen met `info.txt` en start daarna de stack. `db-init` herkent de bestaande database: hij laat de data staan, past openstaande migraties toe (bij een back-up van een oudere versie) en zet de wachtwoorden van de rollen opnieuw uit `.env`. Met `--niet-starten` blijft de stack uit.

### Hersteltest

Een back-up is pas iets waard als herstel werkt. Test dat **elk kwartaal en na elke minor-update**, op een aparte testinstallatie (eigen map, eigen `COMPOSE_PROJECT_NAME` en `OMNITWIN_HTTP_PORT`):

```bash
sh scripts/beheer/hersteltest.sh --wegwerp
```

[`hersteltest.sh`](../../scripts/beheer/hersteltest.sh) legt aantallen en de werking vast (health, geo- en data-API, inloggen als beheerder, de Keycloak-realm), maakt een back-up, gooit de stack met `docker compose down -v` weg, herstelt, en vergelijkt. Het script weigert bij projectnaam `d-omnitwin` of zonder `--wegwerp`. Kopieer voor een test van een productieback-up die back-up naar de testinstallatie en draai `restore.sh` daar.

Uitgevoerd op 03-10-2026 (versie 0.2.1 + #257, Windows 11 met Docker Desktop, sample-data en profiel `keycloak`):

| Meting | Voor | Na herstel |
|---|---|---|
| `gebieden` | 1195 | 1195 |
| `gebied_data` | 252.276 | 252.276 |
| `indicatoren` / `users` / `organisatie` | 93 / 1 / 1 | 93 / 1 / 1 |
| `schema_migraties` | 10 | 10 |
| `laden.leveringen` / `laden.versies` | 10 / 10 | 10 / 10 |
| bestanden in `leveringen` / `uploads` | 10 / 2 | 10 / 2 |
| Keycloak: realms / clients / gebruikers | 2 / 16 / 2 | 2 / 16 / 2 |
| health, geo-API, data-API, inloggen beheerder, realm `omnitwin` | ok | ok |

Back-up 7,9 MB. Uitkomst: `HERSTELTEST GESLAAGD`.

### Handmatig, zonder script

De losse commando's staan in de installatiegids: [Backup](installatie.md#backup), [Restore](installatie.md#restore) en de Keycloak-dump onder [Keycloak](installatie.md#keycloak-optioneel). Het script doet hetzelfde, plus rollen, volumes, controlesommen en bewaartermijn.

---

## 3. Bijwerken en terugrollen

De stappen staan in [Bijwerken](installatie.md#5-bijwerken). Volgorde in productie:

1. **Lees de [CHANGELOG](../../CHANGELOG.md)** van alle versies tussen de jouwe en de nieuwe, vooral "Migreren". Onder 1.0.0 kan elke minor brekende wijzigingen hebben ([releasebeleid](releasebeleid.md)).
2. **Eerst op acceptatie** (zie [hoofdstuk 7](#7-acceptatie-naast-productie)): bijwerken, use cases testen (`python -m omnitwin.usecases test <naam>`), rondkijken.
3. **Back-up van productie:** `sh scripts/beheer/backup.sh`.
4. **Bijwerken:** `git fetch --tags && git checkout v<versie>` (een tag, niet `main`), dan `docker compose up -d --build`.
5. **Controleren:** `docker compose ps -a`, `/health` toont de nieuwe versie, `docker compose logs db-init` toont de toegepaste migraties; `docker compose run --rm db-init python -m omnitwin.migraties --status`.

**Migraties** (`db/migraties/V<nnn>__<naam>.sql`) draaien vanzelf bij elke start van `db-init`, op volgorde, elk in een eigen transactie. Een mislukte migratie stopt `db-init` (exitcode 1); de backend start dan niet en de database staat op de laatste geslaagde migratie. Kijk in `docker compose logs db-init`.

**Terugrollen.** Migraties hebben geen 'down'-stap. Terug naar de vorige versie gaat daarom altijd met de back-up van stap 3:

```bash
git checkout v<vorige versie>
docker compose down -v                                   # wist de bijgewerkte database
sh scripts/beheer/restore.sh backups/omnitwin-<project>-<stempel van stap 3>
```

Data die na de update is geleverd, moet daarna opnieuw geleverd worden (de ETL's leveren volledige snapshots, dus opnieuw leveren is genoeg).

---

## 4. Gebruikers, rollen en machineclients (Keycloak)

Aanzetten, eerste login op de admin-console, rollen in de realm en een identity provider koppelen (Entra ID): zie [Keycloak](installatie.md#keycloak-optioneel). Hier het terugkerende werk.

**Mensen.** Realm `omnitwin` > Users > Add user. Geef de realm-rol `beheerder` alleen aan wie data en inrichting beheert; iedereen krijgt `lezer`. Met een gekoppelde identity provider maak je geen wachtwoorden aan; regel rollen dan via groepen of mappers. Uit dienst: account uitschakelen (*Enabled* uit) of verwijderen, en lopende sessies beëindigen (Users > Sessions).

> De beheeromgeving (`/admin`) gebruikt in deze versie nog een eigen login (tabel `users`, sessiecookie). Beheer die accounts in de beheeromgeving zelf; het eerste account komt uit `ADMIN_USER`. Na de overstap naar Keycloak-login vervalt dit.

**Machineclients** (een ETL of aanleverende partij): één client per bron of partij, nooit gedeeld, met alleen de rollen die hij nodig heeft:

```bash
docker compose exec keycloak bash /opt/keycloak/omnitwin/machineclient.sh etl-<bron> dataset:<id>:laden
```

Het script ([`deploy/keycloak/machineclient.sh`](../../deploy/keycloak/machineclient.sh)) maakt de client aan of vult ontbrekende rollen aan (een nieuwe datasetrol wordt aangemaakt) en toont alleen het secret. Geef het secret via een veilig kanaal door. Is de tijdelijke beheerder `admin` al verwijderd, zet dan `-e KC_BEHEERDER=<naam>` na `exec`.

| Taak | Hoe |
|---|---|
| Secret vernieuwen (periodiek, of bij vermoeden van lekken) | `docker compose exec keycloak bash /opt/keycloak/omnitwin/client-secret.sh <client> --nieuw`; het oude secret werkt meteen niet meer |
| Client tijdelijk blokkeren | Clients > `<client>` > *Enabled* uit |
| Wie heeft welke rol | Clients > `omnitwin-api` > Roles > `<rol>` > Users in role |
| Inlog- en beheergebeurtenissen | Realm settings > Events (staat aan, 30 dagen bewaard) |

Use cases noemen in `actoren` welke accounts en rollen ze nodig hebben ([use cases](../../usecases/README.md#actoren-en-testaccounts)). Testaccounts (`--testaccounts`) zijn alleen voor test en dev; zet op productie `OMNITWIN_OMGEVING=productie`, dan weigert de uitvoerder ze.

---

## 5. Leveringen controleren

Data komt binnen via de [laad-API](../api/laden/README.md). Elke levering doorloopt `ontvangen` → `bezig` → `gepubliceerd`, of eindigt als `afgekeurd` (inhoudelijke fouten) of `mislukt` (technische fout). Bij een fout blijft de vorige versie actief.

| Vraag | Hoe |
|---|---|
| Status van één levering | `GET /api/laden/v1/leveringen/{leveringId}` (met token); de ETL krijgt het adres terug in `Location` |
| Leveringen en versies van een dataset | `GET /api/laden/v1/datasets/{datasetId}/leveringen` en `.../versies` |
| Overzicht in de database | `docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT dataset_id, status, count(*), max(ontvangen_op) FROM laden.leveringen GROUP BY 1,2 ORDER BY 1,2"'` |
| Komt een verwachte levering niet? | Heeft de client de rol (`dataset:<id>:laden`)? Klopt het token (`GET /api/oidc/ik`)? Rate limit (429, `LADEN_RATE_LIMIT`)? Zie `docker compose logs backend` en `traefik`. |

Controleer na elke geplande levering (bijvoorbeeld de maandelijkse ETL) of er een nieuwe versie is. Ruwe leveringen blijven bewaard volgens `LADEN_BEWAAR_VERSIES`, `LADEN_BEWAAR_DAGEN` en `LADEN_BEWAAR_AFGEKEURD_DAGEN` (tabel 2.2 van de [installatiegids](installatie.md#22-env-aanmaken)).

Use cases installeren of opnieuw laden: [Data](installatie.md#4-data).

**Eerste SWF-vulling**: welstand × buurt, het Volledig Kompas en de externe kaartlagen laden vanzelf uit de use cases (bestanden in git); BAG, EP-Online en OpenStreetMap eenmalig via `swf-initialisatie`, zie [Eerste SWF-vulling](installatie.md#eerste-swf-vulling). Controleer daarna `swf-gebied-welstand-buurt` en `swf-init-waarnemingen` *gepubliceerd* (query hierboven), het Kompas en de externe lagen in het beheerscherm. Ruim de tijdelijke database (`docker rm -f swfdump`), de dump en de export daarna op.

---

## 6. Certificaten en HTTPS

Kies manier A (TLS-proxy van je organisatie) of B (Traefik met Let's Encrypt), zie [HTTPS aanzetten](installatie.md#https-aanzetten).

- **Manier A:** het certificaat hoort bij de proxy; vernieuwen is werk van het netwerk- of proxybeheer. Controleer na een wissel dat HSTS en de doorsturing naar HTTPS nog werken.
- **Manier B:** Traefik vraagt het certificaat aan en vernieuwt het zelf (circa 30 dagen voor de vervaldatum), opgeslagen in `acme.json` in het volume van [`tls.example.yml`](../../deploy/traefik/tls.example.yml). Poort 80 moet van buiten bereikbaar blijven voor de HTTP-challenge. Meldingen van Let's Encrypt gaan naar `ACME_EMAIL`: gebruik een functioneel adres.
- **Bewaken:** de vervaldatum, bijvoorbeeld met `echo | openssl s_client -connect <host>:443 -servername <host> 2>/dev/null | openssl x509 -noout -enddate`, of een externe monitor. Alarm bij minder dan 14 dagen.
- Na een wijziging van de hostnaam: ook `KEYCLOAK_HOSTNAME` en `OIDC_ISSUER` aanpassen, en de redirect-URI's van `omnitwin-web`.
- `security.txt` heeft een vervaldatum (`Expires`, hooguit een jaar): verleng die op tijd ([security.txt](installatie.md#securitytxt)).

---

## 7. Acceptatie naast productie

Elke organisatie draait eigen, autonome instanties ([ADR 0007](../2-architectuur/adr/0007-geen-multi-tenancy-mesh-van-instanties.md), [mesh van instanties](../2-architectuur/mesh-van-instanties.md)). Acceptatie en productie zijn **twee losse installaties**, geen twee 'tenants' in één database.

**Opzet**

- Twee mappen (of twee servers), elk met een eigen `.env`: eigen `COMPOSE_PROJECT_NAME` (bijvoorbeeld `omnitwin-acc` en `omnitwin-prod`), eigen `OMNITWIN_HTTP_PORT` of hostnaam, eigen wachtwoorden en sleutels. Traefik routeert alleen naar containers van het eigen project.
- Elk een eigen Keycloak (profiel `keycloak`) met realm `omnitwin`, of één centrale identity provider met per omgeving een eigen realm. Machineclients en secrets zijn per omgeving verschillend.
- Acceptatie draait de nieuwe versie het eerst (zie [Bijwerken](#3-bijwerken-en-terugrollen)).

**Inrichting en data overzetten: als data, niet als database**

Alles wat een instantie inricht is uitwisselbaar als data. Zet dus geen database-dump van acceptatie terug op productie: dan gaan ook accounts, sessies, logs en secrets mee.

| Wat | Van acceptatie naar productie |
|---|---|
| Inrichting en datasets (use cases: definities, Kompas-profiel, kaartlagen, controles) | Dezelfde use-caseversie installeren op productie: `python -m omnitwin.usecases installeer <naam>` tegen productie, of in-process (zie [Data](installatie.md#4-data)). De use case staat in git, met een versie. |
| Data uit eigen bronnen | De ETL levert aan beide omgevingen via de laad-API, elk met een eigen machineclient. Of: levert eerst aan acceptatie en na akkoord hetzelfde bestand aan productie. |
| Eigen organisatie (naam, gemeentecode, logo's, thema) | `db/stuurdata/organisatie.sql` of de SQL uit [Eigen organisatie](installatie.md#eigen-organisatie), per omgeving |
| Keycloak (rollen, clients, mappers) | Realm settings > Action > Partial export (zonder secrets) en Partial import in productie; secrets daarna opnieuw maken met `machineclient.sh` |
| Gebruikers | Niet overzetten: per omgeving aanmaken, of via de gekoppelde identity provider |

Een ondertekend export/import-pakket voor inrichting (de portabiliteitspoort) staat gepland voor 0.4.0 ([mesh van instanties](../2-architectuur/mesh-van-instanties.md#4-de-portabiliteitspoort)).

Een eerste productie-installatie op basis van een volledig ingerichte acceptatie mag wel met `backup.sh` en `restore.sh`; maak daarna in productie nieuwe secrets aan en verwijder testaccounts.

---

## 8. Incidenten

| Situatie | Eerste stappen |
|---|---|
| **Site onbereikbaar** | `docker compose ps -a`; `docker compose logs --tail 200 traefik backend`; `/health`. Een container die herstart: kijk naar geheugen (`docker stats`) en schijf (`df -h`, `docker system df`). |
| **Database stuk of data kwijt** | Stack stoppen (`docker compose stop`), oorzaak vastleggen, herstellen met `restore.sh` naar een lege installatie (of `--overschrijf`). Leveringen van na de back-up opnieuw laten leveren. |
| **Mislukte update** | Zie [Terugrollen](#3-bijwerken-en-terugrollen). |
| **Verkeerde of foute data gepubliceerd** | De bron levert een gecorrigeerde snapshot; dat wordt een nieuwe versie. Meld het aan de gebruikers. |
| **Gelekt secret** (`.env`, client-secret, beheerwachtwoord) | Meteen roteren: client-secret met `client-secret.sh <client> --nieuw`; `ADMIN_API_KEY`, `DATABASE_PASSWORD` (vraagt een `ALTER ROLE` in de database, daarna `docker compose up -d`), `KEYCLOAK_*` en sleutels van LLM-aanbieders in `.env` en bij de aanbieder. Daarna sessies beëindigen en de logs nalopen. |
| **Kwetsbaarheid in D-OmniTwin** | Melden volgens [SECURITY.md](../../SECURITY.md), niet in een openbaar issue. |
| **Datalek (persoonsgegevens)** | Volg de procedure van je organisatie (FG/privacy officer, melding aan de AP binnen 72 uur). Welke persoonsgegevens er zijn: [privacy-quickscan](../5-secops/privacy-quickscan.md). |

Leg elk incident vast (wat, wanneer, oorzaak, herstel) en maak een issue als de software beter kan.

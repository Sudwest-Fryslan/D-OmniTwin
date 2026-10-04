# Changelog

Alle noemenswaardige wijzigingen in D-OmniTwin worden in dit bestand bijgehouden.

De opmaak volgt [Keep a Changelog](https://keepachangelog.com/nl/1.1.0/). Versienummers volgen [Semantic Versioning](https://semver.org/lang/nl/). Hoe versies en releases werken staat in het [releasebeleid](docs/9-beheer/releasebeleid.md).

Eerdere wijzigingen, van vóór dit bestand, zijn terug te vinden in de git-historie, de [Issues](https://github.com/TLaan/D-OmniTwin/issues) en de [pull requests](https://github.com/TLaan/D-OmniTwin/pulls). [`BUILD.md`](./docs/archief/BUILD.md#-sprint-changelog) bevat daarnaast een sprint-changelog.

## [Unreleased]

### Toegevoegd

- Drempels voor de labels A–E van de Klimaatmonitor als data: `db/stuurdata/indicator_labels_klimaatmonitor_swf.json` (9 indicatoren, voorstel uit *Monitoring KA SWF, dialoog 2*, nog door SWF te bevestigen), geladen met `load_sample.py --stap drempels` na de use cases. Zonder drempel blijft een indicator op kwintielen ([#222](https://github.com/TLaan/D-OmniTwin/issues/222) A3).
- Labels A–E per indicator en thema voor de Klimaatmonitor: classificatie `label_ae` naast `zscore` en `percentiel_8` (`kompas_configuraties.classificatie`, migratie `V034__labels_ae.sql`). Elke indicator, elk onderdeel, thema en kwadrant krijgt een label A (gunstigst) t/m E met een kleurenblindvriendelijk palet (A blauw, E rood); het themalabel volgt dezelfde regel als de percentielklasse (gewogen gemiddelde van de indicatorscores, afgerond). Drempels per indicator zijn **data**: tabel `indicator_labels` (label, ondergrens, bovengrens, bron), zodat de drempels van SWF zonder code kunnen worden ingeladen. **Aanname** ([#222](https://github.com/TLaan/D-OmniTwin/issues/222), vraag A3): zonder drempels rekent D-OmniTwin met kwintielen (20%-klassen) binnen dezelfde referentiegroep als de percentielklasse, polariteit toegepast, n < 10 telt niet mee; legenda en Kompas melden dan "Voorlopige drempels (kwintielen)". Kaart: nieuwe modus *Label A–E* (`kaart_data?modus=label`). Het *Klimaat Kompas* is op een verse installatie niet meer leeg: `db/stuurdata/kompasprofiel_klimaat.json` vult het met de klimaatindicatoren uit open data en de use cases (hittestress, hemelwateroverlast, droogte) en zet het op `label_ae`, alleen als het profiel nog leeg is. Methodiek: `docs/3-data-engineering/labels_methodiek.md` ([#256](https://github.com/TLaan/D-OmniTwin/issues/256)).

### Migreren

- Migratie `V034__labels_ae.sql` draait vanzelf bij de start (`db-init`). Het Klimaat Kompas van een bestaande installatie vullen (alleen als het nog leeg is): `docker compose run --rm db-init python /app/init_data/scripts/load_sample.py --stap kompas`. Drempels laden: zie `docs/3-data-engineering/labels_methodiek.md`, *Drempels laden*.

## [0.3.0-rc.1] - 2026-10-03

**Pre-release.** De eerste versie die de huidige SWF-gebiedsmonitor kan opvolgen en aan andere partijen kan worden aangeboden: inloggen via Keycloak (beheer, en optioneel de viewer), een laad-API voor leveringen, use cases als apps met bewijs, open data in plaats van demodata, percentielklassen en kaartmodi, een thema per organisatie en de basis voor productie (back-up en herstel, beheerhandleiding, privacy). Een aantal punten gaat uit van **aannames** tot [#222](https://github.com/TLaan/D-OmniTwin/issues/222) beantwoord is: vulling met de export van februari 2026, de percentielmethodiek, nog geen klimaatlabels A–E en nog geen rechten per laag. Vergelijking met de huidige monitor: [#259](https://github.com/TLaan/D-OmniTwin/issues/259). Lees bij een upgrade de paragraaf **Migreren**.

### Toegevoegd

- Percentielklasse (8 × 12,5%) naast de Z-score, instelbaar per kompasprofiel als data: `kompas_configuraties.classificatie` = `zscore` (standaard, huidige weergave) of `percentiel_8` (migratie `V031__kompas_classificatie.sql`). Bij `percentiel_8` krijgen indicator, onderdeel, thema en kwadrant een klasse 1–8 (8 = gunstigst) met een kleurenblindvriendelijk palet uit `color_schemas`; aggregatie = gewogen gemiddelde van de indicatorklassen (gewicht: aantal gebieden met data in de referentiegroep), afgerond; een multi-selectie volgt dezelfde regel (`GET /api/kompas/{config_id}/selectie`). Kaart: modus *Percentielklasse*, *Werkelijke waarde* (met klassen en bereik in de legenda) of *Uit* (`kaart_data?modus=percentiel|waarde`). **Aanname** tot [#222](https://github.com/TLaan/D-OmniTwin/issues/222) antwoord geeft: percentiel (middenrang) binnen de referentiegroep van de Z-score (gemeente, gebiedstype, zelfde jaar, zonder waterbuurten), polariteit toegepast, waarden met n < 10 tellen niet mee. Methodiek: `docs/3-data-engineering/percentielklasse_methodiek.md` ([#255](https://github.com/TLaan/D-OmniTwin/issues/255)).
- Governance volgens het OpenWebconcept: `GOVERNANCE.md` (eigenaar en beheerder Súdwest-Fryslân, rollen, review bij voorkeur door een andere partij, besluitvorming), `SUPPORT.md` (onderhoudsgarantie één jaar na elke release, einde een jaar vooraf aangekondigd, kanalen) en `PARTICIPANTS.md` (deelnemende organisaties, zonder persoonsnamen); `publiccode.yml` noemt beheerder en termijn ([#183](https://github.com/TLaan/D-OmniTwin/issues/183)).
- Productieklaar bij een gemeente ([#257](https://github.com/TLaan/D-OmniTwin/issues/257)): `scripts/beheer/backup.sh` en `restore.sh` (database, Keycloak-database, rollen en de volumes `leveringen` en `uploads`, met datum, controlesommen en bewaartermijn `BACKUP_BEWAAR_DAGEN`; herstel naar een lege installatie) en `hersteltest.sh` (back-up, `down -v`, herstel, vergelijken; getest met sample-data en Keycloak). Nieuw: [beheerhandleiding](docs/9-beheer/beheerhandleiding.md) (bijwerken en terugrollen, Keycloak-beheer, leveringen, logs en health, certificaten, incidenten, acceptatie naast productie), [privacy-quickscan](docs/5-secops/privacy-quickscan.md) en [toegankelijkheidsstatus](docs/4-ux-design/toegankelijkheid.md). `docs/4-ux-design/thema-s.md` staat nu ook echt in git (stond in `.gitignore`).
- Inloggen in de beheeromgeving via Keycloak (ADR 0008): met `OIDC_ISSUER` gezet toont de inlogpagina **Inloggen met Keycloak** (authorization code + PKCE via `omnitwin-web`; de backend doet de flow en zet het HttpOnly-sessiecookie, ververst het token en logt bij uitloggen ook bij Keycloak uit). Realm-rol `beheerder` geeft beheerrechten, `lezer` niet. Beheer-endpoints accepteren ook een bearer-token van Keycloak met de rol `beheerder`. Gebruikers en rollen beheer je in Keycloak (link in het menu). Lokale accounts werken met Keycloak alleen als noodtoegang (`LOKAAL_INLOGGEN=true`, met waarschuwing); zonder Keycloak blijft het lokale inloggen zoals het was. In de log alleen `sub` en gebruikersnaam. Migratie `V029__oidc_sessies.sql`; nieuwe, optionele variabelen `LOKAAL_INLOGGEN` en `OIDC_CLIENT_ID`; de realmexport neemt `OMNITWIN_BASE_URL/*` op als redirect-URI (bestaande realm: zelf toevoegen in de admin-console) ([#251](https://github.com/TLaan/D-OmniTwin/issues/251)).
- Viewer optioneel achter Keycloak-login (ADR 0009): met `VIEWER_TOEGANG=inloggen` stuurt `/` zonder sessie door naar Keycloak en terug naar de kaart, en zijn ook alle data-API's dicht (API's van de backend via een middleware, `/api/data` en `/api/geo` via Traefik forwardAuth naar `GET /api/viewer/toegang`): zonder sessie `401`, zonder rol `lezer` of `beheerder` `403` (pagina *Geen toegang*). Standaard `open`, zoals het was. In de kop van de viewer *Inloggen* of de gebruikersnaam met *Uitloggen* zodra Keycloak aan staat. Nieuwe, optionele variabele `VIEWER_TOEGANG` ([#266](https://github.com/TLaan/D-OmniTwin/issues/266)).
- Demo-omgeving: `OMNITWIN_OMGEVING=demo` zet standaardaccounts met publieke wachtwoorden: in Keycloak `admin`/`admin` (`beheerder`, `gebruikersbeheerder`) en `gebruiker`/`gebruiker` (`lezer`) met een versoepeld wachtwoordbeleid (nieuwe eenmalige service `keycloak-demo`, profiel `keycloak`, idempotent; buiten demo ruimt hij ze op), en lokaal `admin`/`admin` als `ADMIN_PASSWORD` leeg is. Viewer en beheeromgeving tonen een demobalk. README: snelstart *Demo proberen* ([#245](https://github.com/TLaan/D-OmniTwin/issues/245)).
- Nieuwe realm-rol `gebruikersbeheerder` voor gebruikersbeheer in de Keycloak-console (gebruikers en groepen, geen clients of realm-instellingen), bewust los van `beheerder` ([#251](https://github.com/TLaan/D-OmniTwin/issues/251)).
- Het beheerscherm volgt het organisatiethema voor de inlogpagina, de kop van de zijbalk, de primaire knoppen en het lettertype (`/static/css/themes/<thema>.css` via `GET /api/organisatie`, zoals de viewer); het beeldmerk tekent met de thema-tokens zodra het SVG een `<g id="beeldmerk">` heeft ([#251](https://github.com/TLaan/D-OmniTwin/issues/251)).

- Bewijs per use case en een galerij in de README ([#225](https://github.com/TLaan/D-OmniTwin/issues/225)): `python -m omnitwin.usecases bewijs <naam> | --alle` voert de declaratieve `bewijs.stappen` uit het manifest uit met Playwright (`kaart`, `kompas`, `chat`, `levering`, `open`, `beheer`) en schrijft per stap een WebP-screenshot (1440 × 860, ≤ 150 KB) en `bewijs.json` (controles, antwoordtijden, console-fouten, leveringen). Elke actieve use case heeft 2 tot 4 stappen. Het compacte bewijs staat in git; de originelen gaan met `--zip` als asset bij de release. De README van elke use case toont zijn schermen en de root-README heeft een galerij (`python -m omnitwin.usecases galerij`); unittests bewaken grootte, aantal en actualiteit. Vervangt `scripts/docs/maak_usecase_bewijs.py`.
- Use cases declareren hun **actoren** (gebruikers en machineclients met rollen, nooit wachtwoorden): alle use cases met datasets hebben een `beheerder`, de leverende client(s) met alleen hun eigen `dataset:<id>:laden` en een `lezer`, met rechtencontroles (nieuw controletype `recht`). In test en dev maakt `python -m omnitwin.usecases installeer|test <naam> --testaccounts` ze tijdelijk aan in Keycloak (`uc-<usecase>-<actor>`, via de admin-API, alleen met `OMNITWIN_TESTACCOUNTS=1` en niet bij `OMNITWIN_OMGEVING=productie`), installeert en controleert als die actoren, en `opruimen <naam>` verwijdert ze. Geheimen staan alleen in `.usecase-accounts.json` (in `.gitignore`). Nieuwe, optionele variabelen `OMNITWIN_TESTACCOUNTS`, `OMNITWIN_OMGEVING`, `KEYCLOAK_URL`, `KEYCLOAK_ADMIN`, `KEYCLOAK_ADMIN_CLIENT_ID`, `KEYCLOAK_ADMIN_CLIENT_SECRET`, `OMNITWIN_TESTACCOUNTS_UUR` en `OMNITWIN_TESTACCOUNTS_BESTAND` (alleen voor de uitvoerder, niet in `.env`). De laad-API-client van de uitvoerder haalt bij een 401 eenmaal een nieuw token. Use Case Specificatie 1.0 aangevuld ([#223](https://github.com/TLaan/D-OmniTwin/issues/223)).
- Open data in plaats van demodata ([#236](https://github.com/TLaan/D-OmniTwin/issues/236)): kernadapters `cbs-statline` (elke StatLine-tabel, ook RIVM en Politie via dataderden.cbs.nl) en `wcs-zonaal` (gemiddelde van een WCS-raster per gebied; vervangt `usecases/hittestress/maak_data.py`), use cases `rivm-gezondheidsmonitor`, `politie-misdrijven` en `sample-bronbibliotheek`, varianten met een eigen bron (`als_beschikbaar`, voor de echte interne bron naast demodata) en `installeer --inproces` (de laadstraat zonder HTTP, voor de eerste installatie). Inventaris: `docs/3-data-engineering/demodata-naar-open-data.md`.
- Laad-API: compatibiliteitsingang voor de huidige SWF-gebiedsmonitor (adapter `swf-monitor-v1`, stap 9 van #205). `POST /api/laden/v1/compat/swf-monitor/monitor_api/indicator/setup/inlezen` en `…/indicator_waarde/inlezen` zijn een synchrone levering op `swf-monitor-definities` of `swf-monitor-waarden` (`200`, `422` of `202`, idempotent, `alleenValideren`), de GET-varianten geven definities en waarden terug in het oude formaat. De FME-workspaces wijzigen alleen tokenendpoint, client en URL: [handleiding](docs/api/laden/fme-omzetten.md). Eigen rate-limit op `/compat/` (nieuwe, optionele variabele `LADEN_COMPAT_RATE_LIMIT`, standaard 120 per minuut), omdat een FME-run ±57 aanroepen achter elkaar doet zonder retry. Use case `swf-adapter-fme` op `actief` ([#237](https://github.com/TLaan/D-OmniTwin/issues/237)).
- Thema per organisatie via NL Design System-tokens: `static/css/themes/d-omnitwin.css` (standaard, de huidige uitstraling) en `swf.css` (Súdwest-Fryslân: SWF-rood, -blauw en -groen, Montserrat en Source Sans 3, licht en donker, WCAG AA). De variabelen in `styles.css` lezen de basistokens (`--basis-*`) met de huidige waarde als fallback, dus zonder thema verandert er niets. Montserrat en Source Sans 3 zijn zelf gehost (OFL). Datakleuren blijven buiten het thema. Contrasttest en geldige themanamen in `tests/test_thema.py`; uitleg in `docs/9-beheer/thema-s.md` ([#89](https://github.com/TLaan/D-OmniTwin/issues/89)).
- Architectuurprincipe: geen multi-tenancy, elke organisatie een eigen instantie in een mesh, en alles wat een instantie inricht is uitwisselbaar als data via een portabiliteitspoort (ADR 0007, `docs/2-architectuur/mesh-van-instanties.md`, [#231](https://github.com/TLaan/D-OmniTwin/issues/231)).
- Keycloak als optionele identity provider: compose-profiel `keycloak`, achter Traefik op `/auth`, eigen database `keycloak` in dezelfde PostgreSQL, realm `omnitwin` met een client voor inloggen (code + PKCE), een resource-client met rollen per dataset en een voorbeeld-machineclient (client credentials). Nieuwe, optionele variabelen `COMPOSE_PROFILES`, `KEYCLOAK_ADMIN_PASSWORD`, `KEYCLOAK_DB_PASSWORD` en `KEYCLOAK_HOSTNAME`. De app gebruikt het nog niet ([#214](https://github.com/TLaan/D-OmniTwin/issues/214)).
- Use cases voor de laad-API (status ontwerp): `cbs-gebiedsindelingen`, `cbs-kerncijfers` en acht `swf-*`-use cases die de huidige SWF-gebiedsmonitor via de laad-API naar D-OmniTwin brengen, met `swf-gebiedsmonitor` als acceptatietest. Use cases zijn declaratief (geen code): manifest met versie, afhankelijkheden, rechten, datasets en controles (`usecases/usecase.schema.json`), datasets met DCAT-registratie, bron en bewerkingen (`usecases/dataset.schema.json`). Nieuw in de kern: bronadapters en bewerkingen (`omnitwin.bronadapters`), validatie van registraties en leveringen tegen de laad-API-profielen (`omnitwin.laden`) en de use-case-uitvoerder `python -m omnitwin.usecases` (`lijst`, `boom`, `index`, `controleer`). `laad_usecase.py` volgt `afhankelijk_van` en slaat use cases met status ontwerp over ([#219](https://github.com/TLaan/D-OmniTwin/issues/219)).
- Use-case-uitvoerder `installeer` en `test`: registreren, leveren en de controles uit het manifest tegen de laad-API (client credentials), met één ingang ook voor de demopakketten; acceptatietests `tests/integration/test_usecase_<naam>.py` die zichzelf overslaan zolang de laad-API er niet is ([#219](https://github.com/TLaan/D-OmniTwin/issues/219)).
- Laad-API `/api/laden/v1` ([docs/api/laden](docs/api/laden/README.md)): datasets registreren (DCAT-AP-NL met laadprofiel), leveringen aanbieden als GeoPackage, Data Package-zip, CSV of JSON en volgen; ruw bewaren (volume `leveringen`, sha256, bewaartermijn), valideren tegen het profiel (n-drempel per dataset en indicator), staging en atomisch publiceren per vervangbereik als nieuwe versie; idempotentie, `wacht=true`, Problem Details, `API-Version`, de eigen specificatie op `/api/laden/v1/openapi.json` en een DCAT-catalogusweergave (JSON-LD). Profielen waarnemingen (→ `gebied_data`), definities, gebiedsindeling en kaartlaag (lokale kaartlaag). Traefik-router met bodylimiet en rate-limit; `/api/data/v1` naar PostgREST. Migraties V024–V026: schema `laden`, rol `laden_schrijver`, `gebied_data` met `n`, `n_status` en `levering_id` en de sleutel met scenario. Nieuwe, optionele variabelen `LEVERINGEN_DIR`, `LADEN_*`. Machineclients aanmaken met `deploy/keycloak/machineclient.sh` ([#228](https://github.com/TLaan/D-OmniTwin/issues/228)).
- D-OmniTwin Use Case Specificatie 1.0 (`docs/specificaties/usecase/`): de normatieve definitie van een use case als declaratieve app, met de JSON-schema's als enige bron (verhuisd uit `usecases/`, met absolute `$id`), het nieuwe verplichte veld `specificatie` in elk `usecase.json`, `actoren` en `bewijs.stappen` (gereserveerd), status `verouderd` met `veroudering`, en ADR 0006 ([#227](https://github.com/TLaan/D-OmniTwin/issues/227)).
- Tokens van Keycloak controleren in de backend (`omnitwin.oidc`) voor de nieuwe API's: handtekening via JWKS, `iss`, `aud`, `exp` en rollen per dataset, met `vereis_rol(...)` als FastAPI-dependency en fouten als Problem Details (401/403/503). Testendpoint `GET /api/oidc/ik`. Nieuwe, optionele variabelen `OIDC_ISSUER` (leeg = uit), `OIDC_AUDIENCE`, `OIDC_INTERN_URL` en `OIDC_JWKS_URL`; nieuwe afhankelijkheid `PyJWT[crypto]` ([#224](https://github.com/TLaan/D-OmniTwin/issues/224)).
- De eigen organisatie van een instantie als data (ADR 0007): tabel `organisatie` (migratie `V027__organisatie.sql`) met naam, korte naam, OIN, CBS-gemeentecode(s), benchmarkprovincie, contactadres, footer-logo's en thema (huisstijl: de viewer laadt `static/css/themes/<thema>.css` als dat bestaat), gevuld uit `db/stuurdata/organisatie.sql` (Súdwest-Fryslân; alleen als de tabel leeg is, ook bij een bestaande installatie). Publiek leesendpoint `GET /api/organisatie` en `GET /api/kompas/standaard/hierarchie` (standaard-kompasconfiguratie via `is_standaard`) ([#231](https://github.com/TLaan/D-OmniTwin/issues/231)).
- Beschrijving van de huidige gebiedsmonitor van SWF als vertrekpunt voor 0.3.0: functies, gegevens en gegevensstroom, indicatorenlijst met UUID's, methodiek en gat-analyse met de eisen voor de laad-API ([#195](https://github.com/TLaan/D-OmniTwin/issues/195)).

### Gewijzigd

- **Let op bij bijwerken:** `OMNITWIN_OMGEVING` is standaard `productie`, en dan weigert `db-init` een bekend zwak `ADMIN_PASSWORD` of `KEYCLOAK_ADMIN_PASSWORD` (zoals `admin`, `wachtwoord`, gelijk aan de gebruikersnaam of korter dan 8 tekens); de stack start dan niet. Kies een sterk wachtwoord, of zet `OMNITWIN_OMGEVING=test` ([#245](https://github.com/TLaan/D-OmniTwin/issues/245)).
- `/api/data` en `/api/geo` lopen via een controle in Traefik (forwardAuth naar de backend); bij `VIEWER_TOEGANG=open` laat die alles door, maar zonder draaiende backend werken ze niet meer ([#266](https://github.com/TLaan/D-OmniTwin/issues/266)).
- Het favicon (viewer, beheerscherm, API-documentatie, handleiding) heeft de kleuren van het organisatiethema: `GET /api/organisatie/beeldmerk.svg` levert het beeldmerk met de themakleuren als vaste waarden ([#249](https://github.com/TLaan/D-OmniTwin/issues/249)).
- Organisatiethema overal doorgevoerd in de viewer ([#89](https://github.com/TLaan/D-OmniTwin/issues/89)): welkomstscherm, tabbalk, chat (invoer, bubbels, bron-badges), Kompas (venster, tooltip, detailpopup, grafieken), legenda, indicatorlijst, selectiebadge, kaarttooltip, rapportkeuze en de handleiding lezen hun kleuren nu uit het thema in plaats van vaste (vaak alleen-donkere) waarden. Nieuwe componenttokens `--d-omnitwin-tab-active-*`, `-welcome-button-*`, `-welcome-accent-color`, `-tooltip-*` en `-selection-badge-*` in `d-omnitwin.css` en `swf.css`; tinten via `color-mix()`; knoppen en invoervelden in het lettertype van het thema; hoeken uit `--basis-border-radius-*`. In het SWF-thema zijn welkomstknop en actieve tab nu SWF-rood in plaats van cyaan. Het standaardthema blijft gelijk, op drie contrastverbeteringen na: donker icoon op de gouden actieve tab, selectiebadge `#047857` in plaats van `#10b981` (wit erop 5,48:1) en bron-badges in de chat met tekstkleuren die AA halen. De rapportkeuze was in licht thema donker (niet-bestaande variabelen); de Kompas-tooltip was in donker thema onleesbaar. Datakleuren en de gouden kaartselectie blijven vast. Inlogpagina van Keycloak in de huisstijl: `deploy/keycloak/themes/{d-omnitwin,swf}` (alleen CSS op `keycloak.v2`), gemount in `docker-compose.yml`, `loginTheme` `swf` in de realm. De themadocumentatie staat nu in [`docs/9-beheer/thema-s.md`](docs/9-beheer/thema-s.md) (de oude plek werd door `.gitignore` niet gepubliceerd). `tests/test_thema.py` bewaakt dat elk gebruikt componenttoken in elk thema staat, en de inlogthema's.
- Installatiegids, §4 Data: beschrijft alleen nog de use cases (`python -m omnitwin.usecases`) en de laad-API; de verwijzingen naar `seed_fryslan.py` en het ETL-framework als vulroute zijn weg ([#69](https://github.com/TLaan/D-OmniTwin/issues/69)).
- Statische bestanden krijgen een cachebeleid: bestanden met versie of hash in het pad (vendor, Vite-assets) een jaar `immutable`, de rest `no-cache` (opnieuw valideren met ETag). Na een upgrade toont de browser meteen het nieuwe thema en beeldmerk ([#246](https://github.com/TLaan/D-OmniTwin/issues/246)).
- Het beeldmerk linksboven volgt het organisatiethema via de tokens `--d-omnitwin-beeldmerk-*`; in het SWF-thema wit met SWF-rood ([#249](https://github.com/TLaan/D-OmniTwin/issues/249)). Een eigen SVG-logo zet zijn inhoud in `<g id="beeldmerk">`.
- Een verse installatie (`LOAD_SAMPLE_DATA=true`) laadt alle actieve use cases via de laadstraat (`python -m omnitwin.usecases installeer --alle --inproces`) met open data: alle CBS-buurten, -wijken en -gemeenten van Fryslân, CBS Kerncijfers, RIVM Gezondheidsmonitor, Politie en RIVM-rasters. De demo-use cases hangen daarvan af en zijn `actief` met controles; hun inrichting zet `laad_usecase.py --inrichting`. `init_data/sample/` bevat alleen nog wat niet open is of geen adapter heeft (520 van de 728 waarden), met demodata gemarkeerd (`DEMODATA` in de bron). De indicatordefinities staan in `db/stuurdata/indicatoren.csv` ([#236](https://github.com/TLaan/D-OmniTwin/issues/236)).
- Geen vaste organisatie meer in de code: rapporten (`/api/report/multi-gebied`, `thema-analyse`, `deelgebied`), de viewer en de beheerrapporten vallen zonder gemeentecode terug op die van de organisatie in plaats van `1900`; de footer-logo's komen uit de instelling; de viewer haalt de standaard-Kompasindeling op in plaats van configuratie 1; `postgisftw.buurten_in_deelgebied` filtert op de gemeentecodes van de organisatie (functie verhuisd van `07_postgisftw_functions.sql` naar `V027`). Voor een SWF-installatie verandert er niets zichtbaars. Twee foute codes in de terugvallijst van gemeenten in de viewer gecorrigeerd (De Fryske Marren 1940, Smallingerland 0090) ([#231](https://github.com/TLaan/D-OmniTwin/issues/231)).
- Use cases `cbs-gebiedsindelingen`, `cbs-kerncijfers` en `swf-definities` op status `actief`: ze installeren en slagen via de laad-API (`python -m omnitwin.usecases installeer|test`, machineclient met `beheerder` en `datasets:laden`). Een verse installatie laadt ze niet vanzelf; `laad_usecase.py --alle` laadt nog steeds alleen de demopakketten. `swf-basismonitor-waarden` blijft `ontwerp` tot de gebiedsindeling buurten bebouwde komgrens er is ([#229](https://github.com/TLaan/D-OmniTwin/issues/229)).
- Traefik: de security-headers hangen per router in plaats van op het entrypoint, zodat Keycloak eigen CSP- en frame-regels kan hebben. Een eigen compose-bestand met een extra Traefik-router moet nu zelf `security-headers@file` als middleware zetten ([#214](https://github.com/TLaan/D-OmniTwin/issues/214)).

### Opgelost

- Kaart: bij minder unieke waarden dan kleurklassen (bijv. 3 buurten bij 7 klassen) kregen alle gebieden dezelfde kleur. Nu krijgt elke unieke waarde een eigen klasse, verdeeld over de hele kleurenschaal; gelijke waarden krijgen dezelfde kleur. Bij één unieke waarde: een neutrale middenkleur en een melding in de legenda ([#161](https://github.com/TLaan/D-OmniTwin/issues/161)).
- `vw_gebied_indicator_actueel` (ook `/api/data/vw_gebied_indicator_actueel`) toont alleen gerealiseerde waarden (scenario `current`, NULL telt als `current`) en sorteert op jaar met `NULLS LAST`: een projectie of een rij zonder jaar telt niet meer als actueel. Migratie `V030__actueel_zonder_scenario.sql`. De kaart met een gekozen jaar filtert ook op scenario `current` ([#159](https://github.com/TLaan/D-OmniTwin/issues/159)).
### Beveiliging

- Privacy van de logs ([#264](https://github.com/TLaan/D-OmniTwin/issues/264), uit de privacy-quickscan in [#262](https://github.com/TLaan/D-OmniTwin/pull/262)):
  - **Bewaartermijn:** de dagelijkse opruimtaak verwijdert logregels in `app_logs` van alle niveaus na `LOG_BEWAAR_DAGEN` (standaard 30, DEBUG na 7). Tot nu toe bleven WARNING, ERROR en CRITICAL permanent staan, met IP-adres en gebruikersnaam; bovendien liep de opruimtaak nooit (een `async`-functie in `asyncio.to_thread`) en gaf "Nu uitvoeren" in de beheeromgeving een fout. De taak draait nu ook 5 minuten na de start, niet pas na 24 uur.
  - **IP-adressen** in `app_logs` worden na `LOG_IP_BEWAAR_DAGEN` (standaard 7) ingekort: IPv4 laatste octet `0`, IPv6 `/48`; onleesbare waarden (zoals een oude, ongefilterde `X-Forwarded-For`-lijst) worden leeggemaakt. Een geblokkeerde login zet het IP-adres niet meer in de logtekst.
  - **X-Forwarded-For** wordt alleen overgenomen als het verzoek van een vertrouwde proxy komt (`TRUSTED_PROXIES`, standaard loopback en de privé-reeksen: Traefik op het Docker-netwerk), en dan het meest rechtse niet-vertrouwde adres. De logmiddleware nam de header eerder ongefilterd over; nu gebruiken logging en rate limiting dezelfde functie (`omnitwin.grenzen.client_ip`). Achter een eigen TLS-proxy: `TRAEFIK_TRUSTED_IPS` (Traefik `forwardedHeaders.trustedIPs`).
  - **Containerlogs** begrensd: `json-file`, 3 × 10 MB per container.
  - Nieuwe, optionele variabelen `LOG_BEWAAR_DAGEN`, `LOG_IP_BEWAAR_DAGEN`, `TRUSTED_PROXIES` en `TRAEFIK_TRUSTED_IPS`. Geen migratie.
### Verwijderd

- `ETL/local/` (oud pipeline-pad met `DROP SCHEMA public CASCADE`) en `ETL/Utils/db_init.py` (verwees naar een niet-bestaande `config.ini`). Verwijzingen in de documentatie bijgewerkt ([#69](https://github.com/TLaan/D-OmniTwin/issues/69)).
- Uit de repository (de git-historie blijft): de PDF met de opbouw van het totaalbestand Gezondheidsmonitor 2020 (document van derden, beschikbaar bij het RIVM) en het interne werkdocument `docs/5-secops/logging/plan_email_alerts_smtp.md`, dat al in `.gitignore` stond ([#61](https://github.com/TLaan/D-OmniTwin/issues/61)).

## [0.2.1] - 2026-10-02

Eerste onderhoudsrelease op 0.2: het fundament robuuster, veiliger en beter gedocumenteerd, na een review van 0.2.0 (verse installatie, upgrade, tests, code). Lees bij een upgrade de paragraaf **Migreren**.

### Migreren

- **Geüploade kaartlagen** staan vanaf nu in het volume `uploads` ([#201](https://github.com/TLaan/D-OmniTwin/issues/201)). Bestanden die vóór 0.2.1 zijn geüpload, staan nog in de oude container: kopieer ze vóór de update met `docker compose cp backend:/app/data-upload ./data-upload-backup` en daarna terug naar het volume.
- **`DEBUG` vervalt** ([#203](https://github.com/TLaan/D-OmniTwin/issues/203)). Een bestaande `DEBUG=` in `.env` doet niets meer en mag weg. Het inlogcookie krijgt `Secure` nu via `COOKIE_SECURE` (nieuw, standaard `auto`: alleen als de verbinding HTTPS is). Zonder HTTPS hoef je niets te doen. **Achter een eigen TLS-proxy die over HTTP naar de stack doorstuurt: zet `COOKIE_SECURE=true`** (voorheen `DEBUG=false`); `auto` ziet daar alleen HTTP.
- **CORS:** alleen nog de adressen in `CORS_ORIGINS`. De ngrok-wildcard en de extra localhost-adressen bij `DEBUG=true` zijn weg; zet een ander adres dat de API met cookies aanroept expliciet in `CORS_ORIGINS`. De toegestane header is nu `X-Admin-Key` (wat de backend leest) in plaats van `X-API-Key`.
- **Nieuw, optioneel:** `LLM_RATE_LIMIT` (verzoeken per minuut per IP-adres op chat en AI-teksten, standaard 60, `0` = uit).
- **Foutmeldingen:** een interne fout geeft `500` met `{"detail": "...", "correlatie_id": "..."}` (en header `X-Correlatie-Id`) in plaats van de exceptietekst. Ongeldige UUID's geven `422`, een conflict bij opslaan in beheer `409` (was `400` met de databasemelding).

### Beveiliging

- Geen interne fouten meer naar buiten: centrale foutafhandeling met logging en correlatie-id; de `detail=str(e)`-meldingen (o.a. SQL in `/api/gebiedsmonitor/kaart_data/{id}`) zijn weg; ongeldige UUID's geven 422 ([#203](https://github.com/TLaan/D-OmniTwin/issues/203)).
- Grenzen voor anonieme verzoeken: inloggen na 5 mislukte pogingen per IP + gebruikersnaam (of 20 per IP) in 15 minuten 429, met 1 s vertraging per mislukte poging en bcrypt ook bij een onbekende gebruiker; rate limit op `/api/chat` en de narrative-routes; PostgREST `PGRST_DB_MAX_ROWS=10000`; `statement_timeout` voor `web_anon`/`authenticator` (10 s), `featureserv` (30 s) en de backend (60 s) ([#203](https://github.com/TLaan/D-OmniTwin/issues/203)).
- `COOKIE_SECURE` en `CORS_ORIGINS` los van elkaar in plaats van één `DEBUG`-vlag ([#203](https://github.com/TLaan/D-OmniTwin/issues/203)).

### Gewijzigd

- Documentatie op orde: de installatiegids volgt `.env.example` en de code (één rij per variabele, geen `SECRET_KEY`, backup vóór het bijwerken, geüploade kaartlagen in de backup, upgrade-paragraaf, actuele beveiligingssectie); README en `AGENTS.md` actueel; `docs/STATE.md` gemarkeerd als historisch; dode links gerepareerd, met een linkcheck (`tools/check_links.py`) als unittest; `backups/` en `*.dump` in `.gitignore` ([#204](https://github.com/TLaan/D-OmniTwin/issues/204)).
- Eén `src/omnitwin/config.py` voor alle omgevingsvariabelen van de backend, met dezelfde namen en standaardwaarden ([#130](https://github.com/TLaan/D-OmniTwin/issues/130)).
- Route-handlers zonder `await` zijn `def` (threadpool) in plaats van `async def`: een trage query houdt andere verzoeken niet meer vast; de logqueue is thread-safe ([#68](https://github.com/TLaan/D-OmniTwin/issues/68)).

### Opgelost

- E2E-tests klikken pas als de browser weer vlot tekent en controleren of de klik aankwam, met één nieuwe poging: in CI (software-WebGL) bevroor het compileren van shaders de browser soms seconden lang ([#194](https://github.com/TLaan/D-OmniTwin/issues/194)).
- Installatie robuust: een half mislukte eerste init geeft een foutmelding met herstelinstructie in plaats van een lege stack (tabel `installatie_status`; bestaande installaties worden herkend, geen actie nodig); een mislukte admin-aanmaak stopt de init en er staat geen API-key meer in de log; een andere `DATABASE_USER` werkt (schema zonder vaste eigenaar); de upload van kaartlagen schrijft in stukken, is begrensd op 50 MB en overschrijft niet ([#201](https://github.com/TLaan/D-OmniTwin/issues/201)).
- CI draait ook op `release/**` (push en PR), heeft een job voor het admin-panel (typecheck, lint, test, build en een controle dat `static/admin-panel` bij de broncode hoort) en `concurrency`/`permissions`. Tests die nooit draaiden, draaien weer (`test_escape_html`, `test_jaargangen_sample`, deelgebiedsrapport als integratietest) of zijn weg (debugscript `test_zscore.py`); een test zonder marker laat de collectie falen; verouderde xfail #139 weg. De migratierunner neemt een advisory lock tegen gelijktijdige runs, `--status` is alleen-lezen en toont ingelezen bestanden (V021 → `08_zscore_referentie.sql`, gedocumenteerd in `db/README.md`) ([#202](https://github.com/TLaan/D-OmniTwin/issues/202)).

## [0.2.0] - 2026-10-01

Herstructurering en opschoning, zonder andere werking van de applicatie ([#182](https://github.com/TLaan/D-OmniTwin/issues/182), fases 1–3). Daarmee is de code klaar om open te zetten en te publiceren.

### Migreren vanaf 0.1.x

- **Eerst een backup:** maak vóór `git pull` een backup van de database (zie [Backup](docs/9-beheer/installatie.md#backup)). *(Aangevuld na de release, [#204](https://github.com/TLaan/D-OmniTwin/issues/204).)*
- **Geüploade kaartlagen:** bestanden die via beheer > externe lagen zijn geüpload, staan in deze versie in de backend-container en zijn na `docker compose up -d --build` weg (de rij in `externe_kaartlagen` blijft staan). Kopieer ze vóór de update naar buiten de container met `docker compose cp backend:/app/data-upload ./data-upload-backup` en zet ze na de update terug met `docker compose cp ./data-upload-backup/. backend:/app/data-upload`. *(Aangevuld na de release, [#204](https://github.com/TLaan/D-OmniTwin/issues/204).)*
- **Backend-module:** de app heet nu `omnitwin.main:app` (was `main:app`). Eigen startcommando's, scripts of overrides die `main:app` of `from services…`/`from routers…` gebruiken, moeten naar `omnitwin.…`. Buiten Docker: `pip install -e . --no-deps` of `PYTHONPATH=src`.
- **Paden:** het databaseschema staat in `db/schema/`, de migraties in `db/migraties/` en de stuurdata in `db/stuurdata/`. De mappen `init_data/schema/` en `migrations/` bestaan niet meer.
- **Migraties:** een migratierunner (`python -m omnitwin.migraties`, met `--status`) houdt in de tabel `schema_migraties` bij wat is toegepast. Bij de eerste start na de upgrade maakt hij die tabel aan en past hij V018–V022 (idempotent) opnieuw toe en registreert ze. Daarna draait elke migratie **één keer per database**, niet meer bij elke start. Een wijziging aan een bestaand SQL-bestand vraagt dus een nieuwe migratie; de runner waarschuwt bij een gewijzigde checksum. De rollen en het schema `api` (`R__api_rollen.sql`) worden nog wel bij elke start bijgewerkt.
- **Documenten:** oude root-documenten (`BUILD.md`, `GETTING_STARTED.md`, `ROADMAP.md`, `TODO.md`, `BUGFIX.md`) staan in `docs/archief/`. `PROJECT_GOVERNANCE.md` heet nu `GOVERNANCE.md`.

### Gewijzigd

- Eén Python-pakket `src/omnitwin/` (app, routers, services, schemas, database, versie) met `pyproject.toml` (`[project]`, versie uit `VERSION`) ([#196](https://github.com/TLaan/D-OmniTwin/pull/196)).
- Databaseschema, migraties en stuurdata samen in `db/`, met een migratierunner ([#198](https://github.com/TLaan/D-OmniTwin/pull/198), [#54](https://github.com/TLaan/D-OmniTwin/issues/54)).
- Validatiescripts naar `tools/` ([#193](https://github.com/TLaan/D-OmniTwin/pull/193)).

### Verwijderd

- 43 ongebruikte scripts en ETL-bestanden (eenmalige datafixes, inspectie- en debugscripts, bulk-import Groningen/Drenthe), `obsolete/`, `exports/` en een oud schemabestand. Alles blijft in de git-historie ([#193](https://github.com/TLaan/D-OmniTwin/pull/193), [#153](https://github.com/TLaan/D-OmniTwin/issues/153)).

### Opgelost

- CHANGELOG-links naar het gearchiveerde `BUILD.md`.

## [0.1.0] - 2026-10-01

Eerste release; deze sectie vat de ontwikkeling sinds het begin samen, details staan in de gekoppelde PR's en in [`BUILD.md`](./docs/archief/BUILD.md#-sprint-changelog).

### Toegevoegd

- Basis van de applicatie: D-Omni Kompas (indicatoren in 12 thema's als sunburst), interactieve kaart op buurtniveau (MapLibre GL, deck.gl, PDOK-basiskaart), Z-scores ten opzichte van een referentiegroep, gebiedsrapportages met export, en een AI-chat met een lokaal taalmodel (Ollama).
- Beheeromgeving (React) voor indicatoren, kompas, kaartlagen, prompts en LLM-configuratie.
- Dataspace-architectuur met PostgREST, pg_featureserv en Traefik als gateway ([#13](https://github.com/TLaan/D-OmniTwin/pull/13)).
- Externe kaartlagen beheren, inclusief lokale geodata en uploads; 3D-panden via 3DBAG ([#39](https://github.com/TLaan/D-OmniTwin/issues/39)).
- Configureerbare logging met automatische opschoning.
- Deduplicatie van indicatoren ([#19](https://github.com/TLaan/D-OmniTwin/issues/19)).
- Woonplaats- en deelgebiedsanalyse als rapport ([#45](https://github.com/TLaan/D-OmniTwin/pull/45)).
- Sample dataset met stuurdata en brondata voor 12 buurten in Súdwest-Fryslân, met Bolsward-Zuidoost als testbuurt, voor demo en test ([#53](https://github.com/TLaan/D-OmniTwin/pull/53), [#80](https://github.com/TLaan/D-OmniTwin/pull/80)).
- De sample als Frictionless datapakket met licentie en herkomst ([#86](https://github.com/TLaan/D-OmniTwin/pull/86)).
- Use cases als pakket: alle demodata hoort bij een use case, met laadscript en tests ([#141](https://github.com/TLaan/D-OmniTwin/pull/141)).
- Use case hittestress compleet met echte open data (CBS 2026, RIVM 2022) ([#160](https://github.com/TLaan/D-OmniTwin/pull/160)).
- Volledige Fryslân-data laden in Docker met één commando ([#111](https://github.com/TLaan/D-OmniTwin/pull/111)).
- CBS Kerncijfers 2019–2026 worden bij het laden gedownload (het recept staat in git, de data niet), zodat trends werken ([#176](https://github.com/TLaan/D-OmniTwin/pull/176)).
- Container-entrypoint dat bij de eerste start het databaseschema aanmaakt, de sample dataset laadt (`LOAD_SAMPLE_DATA=true`) en een admin-gebruiker aanmaakt ([#52](https://github.com/TLaan/D-OmniTwin/issues/52)).
- Chat beantwoordt datavragen met cijfers uit de database (grounded), en de kaart beweegt mee ([#175](https://github.com/TLaan/D-OmniTwin/pull/175)).
- Taalmodel: OpenAI-compatibele koppeling naast Ollama, met optionele LiteLLM-gateway ([#107](https://github.com/TLaan/D-OmniTwin/pull/107)); aanbieders (Ollama, Claude, OpenAI, Gemini) wisselen en vergelijken ([#142](https://github.com/TLaan/D-OmniTwin/pull/142)).
- GitHub Actions-pipeline met unittests en Docker-buildcontrole ([#49](https://github.com/TLaan/D-OmniTwin/pull/49)).
- CI op een verse stack met integratie- en e2e-tests en publiccode-validatie ([#114](https://github.com/TLaan/D-OmniTwin/pull/114)).
- Integratietests tegen een verse stack met de sample dataset ([#70](https://github.com/TLaan/D-OmniTwin/pull/70)); browser-e2e-tests per testcase (Playwright) ([#112](https://github.com/TLaan/D-OmniTwin/pull/112)).
- Use cases, e2e-scenario's en nulmetingen als testcases ([#77](https://github.com/TLaan/D-OmniTwin/pull/77)).
- `publiccode.yml`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md` en een concept `PROJECT_GOVERNANCE.md` ([#76](https://github.com/TLaan/D-OmniTwin/pull/76)).
- Issue- en PR-templates, databronlicenties in `NOTICE`, bronvermelding op de kaart ([#132](https://github.com/TLaan/D-OmniTwin/pull/132)).
- `AGENTS.md` en `CONTRIBUTING.md` met de werkwijze van issue tot merge ([#35](https://github.com/TLaan/D-OmniTwin/pull/35), [#37](https://github.com/TLaan/D-OmniTwin/pull/37)).
- Releasebeleid en één bron voor het versienummer (`VERSION`), met een test die de versies gelijk houdt ([#152](https://github.com/TLaan/D-OmniTwin/pull/152), [#27](https://github.com/TLaan/D-OmniTwin/issues/27)).
- Architectuurvisie (doelbeeld dataspace-platform en tooling-richting) in de documentatie ([#6](https://github.com/TLaan/D-OmniTwin/pull/6)).
- Projectinstellingen voor Claude Code ([#3](https://github.com/TLaan/D-OmniTwin/pull/3)).

### Gewijzigd

- Eén installatiegids voor beheerders, getest op een verse clone ([#87](https://github.com/TLaan/D-OmniTwin/pull/87)).
- Docker Compose gesplitst in installatie en ontwikkeling, met healthchecks en een aparte db-init-service ([#78](https://github.com/TLaan/D-OmniTwin/pull/78)).
- Backend-image gehalveerd: multi-stage build, ETL-pakketten apart, download van 1008 naar 533 MB ([#174](https://github.com/TLaan/D-OmniTwin/pull/174)).
- Docker-images, Python-afhankelijkheden en frontend-bibliotheken vastgepind voor reproduceerbare builds; CDN-bibliotheken met SRI ([#74](https://github.com/TLaan/D-OmniTwin/pull/74), [#84](https://github.com/TLaan/D-OmniTwin/pull/84)).
- Embeddingmodel vastgepind en in de image: AI-zoeken werkt offline, zonder telemetrie ([#156](https://github.com/TLaan/D-OmniTwin/pull/156)).
- Beheeromgeving van Create React App naar Vite 8 en TypeScript 5 ([#110](https://github.com/TLaan/D-OmniTwin/pull/110)).
- Z-scores: één centrale referentie voor alle Z-scores, standaard hetzelfde jaar als het doelgebied, waterbuurten altijd uitgesloten (één definitie), minimum-n 5 met zichtbare terugval ([#154](https://github.com/TLaan/D-OmniTwin/pull/154), [#171](https://github.com/TLaan/D-OmniTwin/pull/171)).
- Een Mapbox-token is niet meer nodig ([#72](https://github.com/TLaan/D-OmniTwin/pull/72)).
- `.env.example` terug naar het minimum (alleen `DATABASE_PASSWORD` verplicht), met een test op drift ([#133](https://github.com/TLaan/D-OmniTwin/pull/133)).
- Toegankelijkheid, eerste ronde WCAG 2.1 AA: focus, labels, toetsenbord en contrast ([#75](https://github.com/TLaan/D-OmniTwin/pull/75)); tweede ronde: dialogen met focusbeheer, reduced motion, labels in de beheeromgeving ([#134](https://github.com/TLaan/D-OmniTwin/pull/134)).
- Neutraal tijdelijk beeldmerk in plaats van een persoonlijk logo, per installatie te vervangen ([#150](https://github.com/TLaan/D-OmniTwin/pull/150)).
- Contactadres (team-inbox geo-groep@sudwestfryslan.nl) in `SECURITY.md`, de gedragscode en `publiccode.yml` ([#147](https://github.com/TLaan/D-OmniTwin/pull/147)).
- Screenshots actueel en reproduceerbaar ([#136](https://github.com/TLaan/D-OmniTwin/pull/136)).
- Bug- en backlogtracking samengebracht in GitHub Issues ([#48](https://github.com/TLaan/D-OmniTwin/pull/48)).
- Versienummer overal `0.1.0`; de uiteenlopende nummers (README `v1.0.0-beta`, API `1.5.0`/`1.2.0`, footer `API v0.2.0`) zijn vervangen door de waarde uit `VERSION` ([#152](https://github.com/TLaan/D-OmniTwin/pull/152), [#27](https://github.com/TLaan/D-OmniTwin/issues/27)).
- Dependabot groepeert minor- en patch-updates ([#105](https://github.com/TLaan/D-OmniTwin/pull/105)) en slaat fastapi, starlette en uvicorn over tot een gezamenlijke upgrade ([#173](https://github.com/TLaan/D-OmniTwin/pull/173)).
- Afhankelijkheden bijgewerkt via Dependabot.

### Verwijderd

- Kapotte en dode backend-endpoints ([#73](https://github.com/TLaan/D-OmniTwin/pull/73)).

### Opgelost

- WebGL-buffercorruptie bij het wisselen van gemeente en een 404-lus in de beheeromgeving ([#43](https://github.com/TLaan/D-OmniTwin/pull/43)).
- Buurten in een deelgebied via een pg_featureserv-functie ([#85](https://github.com/TLaan/D-OmniTwin/pull/85)).
- Bevindingen uit de UI-test: tellers uit de data, Kompas opent bij klik, nette melding zonder taalmodel ([#82](https://github.com/TLaan/D-OmniTwin/pull/82)).
- Beheeromgeving: rapporten in het menu, Benchmark via PostgREST, geen hardgecodeerd gebied ([#81](https://github.com/TLaan/D-OmniTwin/pull/81)).
- Kaart: fitBounds werkt, selectiebadge met losse knoppen, Kompas vanuit de chat laadt de selectie ([#113](https://github.com/TLaan/D-OmniTwin/pull/113)).
- Chat: gemeentekeuze van het taalmodel gevalideerd, actief gemeentefilter zichtbaar met wisknop ([#148](https://github.com/TLaan/D-OmniTwin/pull/148)).
- Chat: een datavraag valt bij een fout van het taalmodel terug op de vaste tekst met cijfers ([#181](https://github.com/TLaan/D-OmniTwin/pull/181)).
- Embeddings worden bij de database-initialisatie aangemaakt, zodat chat en AI-zoeken indicatoren vinden ([#143](https://github.com/TLaan/D-OmniTwin/pull/143)).
- Jaargangen zichtbaar en gecontroleerd: 'Kerncijfers 2023' bleek 2021, geometrie 2024 vastgelegd ([#158](https://github.com/TLaan/D-OmniTwin/pull/158)).
- Gemiddeld energielabel telt als 'lager is beter'; kop zonder '3D Visualisatie' ([#186](https://github.com/TLaan/D-OmniTwin/pull/186)).
- Gemeentecodes in de Fryslân-data gecorrigeerd ([#111](https://github.com/TLaan/D-OmniTwin/pull/111)).
- CSV-export ([#112](https://github.com/TLaan/D-OmniTwin/pull/112)).
- Database-image bouwt weer: pgvector uit apt-archive.postgresql.org ([#190](https://github.com/TLaan/D-OmniTwin/pull/190)).
- Backend crasht niet meer in dev-modus op Windows (`logs/` niet schrijfbaar) ([#115](https://github.com/TLaan/D-OmniTwin/pull/115)).
- E2e-test voor reduced motion is niet meer flaky ([#188](https://github.com/TLaan/D-OmniTwin/pull/188)).
- Licentievermelding in `MERKID_D-OMNITWIN.md` in lijn met `LICENSE` (EUPL) en `LICENSE-DOCS` (CC BY 4.0) ([#36](https://github.com/TLaan/D-OmniTwin/pull/36)).

### Beveiliging

- PostgREST en pg_featureserv draaien niet meer als database-eigenaar. Eigen rollen (`authenticator`, `web_anon`, `featureserv`) en een schema `api` met alleen views en functies: anoniem geen toegang meer tot `users`, `sessions`, `api_keys`, `llm_config`, `system_prompts` en de logs, en geen schrijfacties via `/api/data` ([#146](https://github.com/TLaan/D-OmniTwin/pull/146), [#57](https://github.com/TLaan/D-OmniTwin/issues/57)).
- Geen secrets in code of build, admin-autorisatie op alle beheerroutes, gehashte sessies en XSS-escaping in de frontend ([#151](https://github.com/TLaan/D-OmniTwin/pull/151)).
- Security-headers (CSP, `X-Frame-Options`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`) via Traefik op alle routes, ook `/api/data` en `/api/geo`; HSTS op HTTPS; `/.well-known/security.txt`; voorbeeld voor HTTPS met Let's Encrypt in `deploy/traefik/tls.example.yml` ([#145](https://github.com/TLaan/D-OmniTwin/pull/145), [#121](https://github.com/TLaan/D-OmniTwin/issues/121)).
- CDN-domeinen uit de CSP, nu alles zelf gehost wordt ([#177](https://github.com/TLaan/D-OmniTwin/pull/177)).
- Privacy: frontend-bibliotheken en lettertype zelf gehost, geen Google Fonts, unpkg of jsdelivr meer ([#144](https://github.com/TLaan/D-OmniTwin/pull/144)).
- Geen standaard admin/admin-wachtwoord meer bij de container-initialisatie: zonder `ADMIN_PASSWORD` wordt eenmalig een willekeurig wachtwoord gegenereerd ([#52](https://github.com/TLaan/D-OmniTwin/issues/52)).
- Geen hardgecodeerd databasewachtwoord meer in `generate_sample.py` ([#52](https://github.com/TLaan/D-OmniTwin/issues/52)).
- `.dockerignore` toegevoegd, zodat onder meer `.env` niet in het image belandt ([#52](https://github.com/TLaan/D-OmniTwin/issues/52)).
- De backend-container draait als niet-root gebruiker ([#78](https://github.com/TLaan/D-OmniTwin/pull/78)).
- Beheeromgeving gebouwd zonder sourcemaps ([#81](https://github.com/TLaan/D-OmniTwin/pull/81)).

[Unreleased]: https://github.com/TLaan/D-OmniTwin/compare/v0.3.0-rc.1...HEAD
[0.3.0-rc.1]: https://github.com/TLaan/D-OmniTwin/compare/v0.2.1...v0.3.0-rc.1
[0.2.1]: https://github.com/TLaan/D-OmniTwin/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/TLaan/D-OmniTwin/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/TLaan/D-OmniTwin/releases/tag/v0.1.0

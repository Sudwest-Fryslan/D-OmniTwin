# 0010. Toegang per laag en bron: openbaar of intern, afgedwongen in de database en de forwardAuth

- Status: voorgesteld
- Datum: 2026-10-04
- Issue: https://github.com/TLaan/D-OmniTwin/issues/254
- Raakt: ADR 0004 (laad-API), ADR 0007 (geen multi-tenancy), ADR 0008 (inloggen via Keycloak, BFF), ADR 0009 (viewer achter login, forwardAuth), https://github.com/TLaan/D-OmniTwin/issues/222 (vraag B3)

## Context

In de huidige SWF-monitor ziet een ingelogde medewerker meer lagen dan een bezoeker. In D-OmniTwin was alles wat geladen is openbaar; een kaartlaag die niet `PUBLIC` was, stond simpelweg uit. ADR 0009 zet de hele viewer optioneel achter een login, maar niet per laag.

Interne data komt langs vier wegen naar buiten: FastAPI (kaart, Kompas, rapporten, chat; tientallen SQL-query's die `indicatoren` en `gebied_data` lezen), PostgREST (`/api/data`), pg_featureserv (`/api/geo`) en de kaartlaag-proxy (`/api/externe-lagen`). Filteren in de UI is niet genoeg; filteren in elke query is foutgevoelig.

## Besluit

**1. Toegang is data, per dataset.** De bron van de waarheid is `dct:accessRights` in de registratie (DCAT-AP-NL): `PUBLIC` = `openbaar`, al het andere = `intern`. `laden.datasets.toegang` is daarvan afgeleid (gegenereerde kolom), en de laad-API geeft hem terug. Wat de dataset publiceert, krijgt die toegang:

- de kaartlaag (`externe_kaartlagen.toegang`); een interne laag staat aan, maar alleen voor wie mag;
- een indicator (`indicatoren.toegang`) is intern als een interne dataset hem definieert, of als al zijn waarden uit interne datasets komen;
- een waarde (`gebied_data.toegang`) is intern als de levering uit een interne dataset komt of de indicator intern is.

Alles wat niet via de laad-API kwam (stuurdata, uploads, PDOK-lagen), blijft `openbaar`. Een beheerder kan een eigen externe laag `intern` maken (`toegang` in de beheer-API). Een use case toont de keuze met `toegang` per dataset; die moet gelijk zijn aan `dct:accessRights` (Use Case Specificatie 6.1, 6.3). "Later per rol": dan wordt `toegang` een rolnaam in plaats van twee waarden; het mechanisme hieronder blijft.

**2. Wie intern mag zien:** een sessie of bearer-token met realm-rol `lezer` of `beheerder` (of een lokale beheerder, of `X-Admin-Key`): dezelfde regel als ADR 0009. Ingelogd zonder die rol telt als anoniem, met 403 in plaats van 401.

**3. Afdwingen in de database, voor de backend.** Row level security op `indicatoren`, `gebied_data` en `externe_kaartlagen` (migratie V032): de rol `omnitwin_openbaar` ziet alleen `openbaar`, elke andere rol alles. De backend schakelt per anoniem verzoek naar die rol: de middleware bepaalt de stand van het verzoek (contextvar), en een pool-event zet bij elke verbinding `SET ROLE omnitwin_openbaar` of `RESET ROLE` (met commit, zodat een rollback hem niet terugdraait). `omnitwin_openbaar` is lid van de eigenaar (dezelfde rechten op tabellen) maar geen superuser, dus RLS geldt (`FORCE`). Views in `public` die deze tabellen lezen krijgen `security_invoker` (in `R__api_rollen.sql`, bij elke start). Zo filteren alle bestaande query's, joins, views en SQL-functies (Z-scores, Kompas, rapporten, chat) zonder dat ze iets van toegang weten. Zonder verzoek (laadstraat, db-init, achtergrondtaken) is er geen filter.

Een directe aanroep van een interne indicator of laag (kaartdata, visualisatieconfig, Kompas-pad, kaartlaag-features) geeft 401 of 403 (Problem Details) in plaats van 404; daarvoor kijkt de route via een `SECURITY DEFINER`-functie naar de toegang.

**4. PostgREST: views filteren op een header van de forwardAuth.** Het forwardAuth-antwoord (`GET /api/viewer/toegang`, ADR 0009) zet `X-Omnitwin-Toegang: intern` of `openbaar`; Traefik kopieert hem naar het verzoek aan PostgREST en verwijdert eerst een gelijknamige header van de client (`authResponseHeaders`). De views in schema `api` filteren op `toegang = 'openbaar' OR public.verzoek_mag_intern()` (de header uit `request.headers`). Een lijst geeft anoniem gewoon minder rijen, geen fout.

**5. pg_featureserv:** de forwardAuth kijkt naar `X-Forwarded-Uri`; een collectie `laag.<featureTabel>` van een interne dataset geeft anoniem 401 (zonder rol 403). De huidige collecties (gebieden, deelgebieden) bevatten geen interne data.

**6. Viewer:** de lijsten komen uit de gefilterde API's, dus een interne laag of indicator verschijnt pas na inloggen; ingelogd staat er het label *intern* bij.

## Alternatieven

- **In elke query filteren** (`AND i.toegang = 'openbaar'` in services en routers). Werkt, maar het zijn ruim zeventig plekken en elke nieuwe query moet eraan denken; één vergeten join lekt. Afgewezen.
- **RLS op een sessievariabele** (`current_setting('omnitwin.toegang')`) zonder van rol te wisselen. De backend verbindt als superuser (`POSTGRES_USER` in Docker), en een superuser omzeilt RLS altijd. Afgewezen.
- **PostgREST met JWT-rollen** (backend tekent een kort JWT in de forwardAuth). Cryptografisch sterker, maar een gedeeld geheim tussen backend en PostgREST en een tweede rol in PostgREST; pg_featureserv kan het niet. De header is genoeg zolang PostgREST alleen via Traefik bereikbaar is.
- **Interne data in een aparte tabel of database.** Zwaar en dubbel onderhoud; past niet bij "bron blijft bron".

Dit is geen multi-tenancy (ADR 0007): er is één organisatie per instantie; RLS scheidt hier openbaar van intern, niet organisaties.

## Gevolgen

- Bestaande installaties: na V032 is alles openbaar, behalve wat een geregistreerde dataset met `RESTRICTED` (of `NON_PUBLIC`) publiceerde. Een kaartlaag uit de laad-API die daarom uit stond, staat nu aan als `intern`.
- PostgREST en pg_featureserv mogen niet rechtstreeks bereikbaar zijn (alleen via Traefik); anders kan een client de header zelf zetten. In de standaard-compose hebben ze geen gepubliceerde poort.
- Een nieuwe tabel met interne data krijgt een kolom `toegang` en dezelfde policy; een nieuwe view in `api` filtert zelf. Een nieuwe route met een expliciete indicator of laag roept `toegang.vereis_indicator`/`vereis_kaartlaag` aan voor 401/403.
- Elk anoniem verzoek kost één extra statement per verbinding uit de pool (`SET ROLE`); een ingelogde viewer ook een sessie-opzoeking per verzoek.
- Keycloak geeft elke nieuwe gebruiker en elk service account standaard de rol `lezer` (`default-roles-omnitwin`). Een ETL-client ziet daardoor ook interne data, tenzij je die standaardrol bij het service account weghaalt; de testaccounts van de use cases doen dat.
- Nog niet: een gebiedsindeling met `RESTRICTED` krijgt toegang `intern` in de registratie, maar de gebieden zelf blijven zichtbaar. De aantallen in de indicatorenlijst tellen ook interne waarden van een openbare indicator.

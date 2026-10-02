# 0004. D-OmniTwin vullen via één laad-API: dataset-registratie en leveringen

- Status: voorgesteld
- Datum: 2026-10-01, herzien 2026-10-02 (vóór vaststelling: van één waarneming-contract naar registratie + leveringen per dataset)
- Issue: #205 (0.3.0), #195, #182 fase 4; bouwt voort op ADR 0002 (PR #184); API-indeling in ADR 0005

## Context

Data komt op vier manieren in D-OmniTwin:

1. **Push:** een externe ETL bij de bronhouder levert gegevens aan. Bij SWF bouwt FME uit het datawarehouse nu twee soorten pushes naar de huidige gebiedsmonitor: een definities-snapshot (indicatoren, gebiedstypen, relaties) en per indicator × gebiedstype een array met waarden. Zonder `n`, zonder idempotentie, met de hand gestart.
2. **Interne ETL:** een bron als dataproduct (ADR 0002) haalt open data op en laadt die.
3. **Virtualisatie:** een bron wordt bij de bron bevraagd, met een cache.
4. **Federatie:** een vraag gaat door naar een andere databron of D-OmniTwin-installatie (#20, #32).

Nu is er voor geen van deze routes een ingang. Scripts schrijven als database-eigenaar direct in de tabellen, elk met een eigen `INSERT … ON CONFLICT`. Het enige upload-endpoint is voor kaartbestanden in het beheer. Machine-authenticatie is één gedeelde `X-Admin-Key`. Herkomst (`etl_runs`, `data_lineage`, #20) bestaat alleen op papier; `gebied_data` heeft geen kolom voor n.

Wat binnenkomt is niet alleen indicatorwaarden. Ook definities, gebiedsindelingen (welstandsgebieden) en kaartlagen (panden, klimaatlagen) moeten erin, vaak als geodata in RD (EPSG:28992).

Eisen:
- de SWF-monitor in 0.3.0 kunnen vullen, zonder dat FME meer hoeft te wijzigen dan URL en client (#195);
- privacy: kleine aantallen nooit publiceren;
- herkomst per levering herleidbaar (AVG, IAMA, bronvermelding);
- bij een fout blijft de vorige stand staan;
- zo min mogelijk eigen code, passend bij de stack (PostgreSQL, PostgREST, pg_featureserv, Keycloak, Traefik);
- aansluiten op NL-standaarden (API Design Rules, NL GOV OAuth, DCAT-AP-NL) en voorbereid op een dataspace (DSP).

## Besluit

**1. D-OmniTwin accepteert datasets als pakket, niet losse records.** De ETL maakt een snapshot, levert die als één bestand aan, D-OmniTwin valideert en publiceert hem in één keer. Drie verantwoordelijkheden, gescheiden:

| Onderdeel | Vraag | Standaard |
|---|---|---|
| **Registratie** | Wat is de dataset en hoe wordt hij geladen? | beschrijving in DCAT-AP-NL 3, voor geodata GeoDCAT-AP 3 (JSON-LD); daarnaast een **laadprofiel** (profiel, sleutel, vervangbereik, n-drempel). Laadinstructies staan niet in DCAT |
| **Levering** | Wat zit er in deze aanlevering? | GeoPackage 1.4, of een Frictionless Data Package (zip met `datapackage.json`, CSV of GeoPackage, optioneel `dcat.jsonld`); voor kleine tabulaire leveringen CSV of JSON |
| **Loader** | Laad deze levering nu | de laad-API |

**2. Eén laad-API:** `/api/laden/v1` (ADR 0005), specificatie in [`docs/api/laden/openapi.yaml`](../../api/laden/openapi.yaml):
- `POST /datasets` registreert; `GET/PUT/PATCH /datasets/{datasetId}` leest en wijzigt de beschrijving;
- `POST /datasets/{datasetId}/leveringen` biedt een volledige snapshot aan: `202` met `Location`, of met `wacht=true` synchroon tot een time-out; `alleenValideren=true`; header `Idempotency-Key`;
- `GET /leveringen/{leveringId}` geeft status, aantallen, versie, sha256 en fouten per regel (Problem Details);
- `GET /datasets/{datasetId}/leveringen` en `/versies` geven de historie; `…/versies/{versie}/bestand` het geleverde bestand terug.

**3. Profielen in plaats van één contract.** Elke dataset heeft één profiel (`dct:conformsTo`): `waarnemingen` (indicatorwaarden: gebied, indicator-UUID, jaar of peildatum, scenario, waarde, n, kwaliteit, bron), `definities` (indicatoren, gebiedstypen, relaties), `gebiedsindeling` (gebieden met geometrie) en `kaartlaag` (vrije features). Tabulaire delen als Frictionless Table Schema in [`docs/api/laden/profielen/`](../../api/laden/profielen/README.md). Een **adapter** vertaalt een bestaand formaat naar een profiel; de eerste is `swf-monitor-v1` voor de huidige SWF-push, met een compatibiliteitspad dat de huidige paden spiegelt.

**4. Laadstraat:** ruw bewaren (onveranderlijk, met sha256, op een eigen volume) → valideren (pakket, GeoPackage, schema volgens profiel, CRS, codes, dubbele sleutels, plausibel aantal, n-drempel) → staging → **atomisch publiceren** als nieuwe versie. Bij een fout blijft de vorige versie actief. In v1 alleen modus `vervangen`; het vervangbereik (hele dataset, of bijvoorbeeld per indicator × gebiedstype) staat in het laadprofiel. `append`/`upsert` later.

**5. De logica zit in PostgreSQL** (schema `laden`): staging via `COPY` (GeoPackage gelezen met fiona, dat al in de image zit), set-based validatie en publicatie in één transactie. De FastAPI-router is dun: token controleren, bestand streamen naar het volume, status. De laad-API verbindt met een eigen databaserol met alleen `EXECUTE` op `laden.*`.

**6. Privacy bij de ingang.** Waarden met n onder de drempel van de dataset (`minimumN`, SWF: 10) worden niet gepubliceerd en na publicatie uit de staging verwijderd. Levert een bron geen n, dan mag dat alleen als de dataset `bijOntbrekendeN: bron-onderdrukt` heeft: de waarde krijgt die vlag en de bron is verantwoordelijk. Aggregaten over meerdere gebieden gebruiken alleen gepubliceerde waarden en worden zelf ook aan de drempel getoetst.

**7. Versies en herkomst.** Per dataset een versie per geslaagde publicatie en een historie van alle leveringen (ook afgekeurde). `gebied_data` krijgt `levering_id`; `etl_runs` en `data_lineage` (#20) worden de leveringen- en versietabellen van de laad-API, met client (`azp`), sha256 en aantallen. Na een publicatie werkt D-OmniTwin `dct:modified` en de distributie in de catalogus bij.

**8. Autorisatie uit Keycloak (OIDC, realm `omnitwin`, PR #216).** Machines: client credentials met een confidential client per afnemer; nu `client_secret_post`/`client_secret_basic` (FME), later `private_key_jwt`. Client-rol `dataset:{datasetId}:laden` (één dataset) of `datasets:laden` (alle) op resource-client `omnitwin-api`, die via een audience-mapper in `aud` staat; registreren met de realm-rol `beheerder`. FastAPI valideert het token via de JWKS van de realm (`iss`, `aud`, `exp`, rol). `X-Admin-Key` is geen ingang voor data.

**9. Alle routes gebruiken deze laad-API of deze profielen:**
- route 1 (push): de HTTP-ingang;
- route 2 (interne ETL): dezelfde laadstraat, in-process of via HTTP met een eigen client;
- route 3 (virtualisatie): verversen van een virtuele bron is een levering; alleen viewer-lagen buiten berekeningen worden zonder kopie on-demand gecachet;
- route 4 (federatie): de `data`- en `geo`-API geven gepubliceerde datasets terug in hetzelfde profiel; de catalogus in DCAT-AP-NL (later DSP); transport tussen organisaties via FSC (#33).

## Alternatieven

- **Schrijven direct in de database laten (zoals nu).** Een externe partij krijgt het eigenaarswachtwoord, elke loader valideert anders, geen herkomst of n-drempel. Afgewezen.
- **Eén waarneming-contract voor alles** (de eerste versie van dit ADR). Dekt indicatorwaarden, maar geen definities, gebiedsindelingen of kaartlagen. Wordt het profiel `waarnemingen`.
- **Records per stuk leveren** (REST per waarde, of OGC API Features Part 4 per feature). Geen atomische snapshot, veel aanroepen, en Part 4 is nog draft en niet in pg_featureserv. Afgewezen voor laden; Part 4 later mogelijk voor losse geo-objecten.
- **GeoJSON als leveringsformaat voor geodata.** RFC 7946 is altijd WGS84; gemeentelijke data staat in RD. GeoPackage en (later) GeoParquet bewaren het CRS. GeoJSON blijft de uitvoer van de geo-API.
- **PostgREST als schrijf-API.** Geen zip/GeoPackage, geen streaming, geen asynchrone status. Kan later als tweede ingang op dezelfde SQL-functies.
- **Kafka/event-bus, Airbyte/Meltano als ingang, dbt in de kern.** Te zwaar voor periodieke snapshots bij een gemeente, of lost een ander probleem op (connectoren, transformaties aan de bronkant). Een Singer/Meltano-target kan later een dunne wrapper om de laad-API zijn.
- **FME laten aanpassen aan een nieuw formaat vóór 0.3.0.** Zuiverder, maar maakt de overstap afhankelijk van werk bij SWF. De adapter `swf-monitor-v1` is goedkoop en tijdelijk.
- **OData voor laden.** Hoort bij het ontsluiten van bronnen aan de ETL-kant, niet bij het laden in D-OmniTwin.

## Gevolgen

- **Makkelijker:**
  - elke soort dataset (waarden, definities, gebieden, kaartlagen) via één ingang, met dezelfde validatie, versies en herkomst;
  - een externe ETL aansluiten zonder databasetoegang, met rechten per dataset;
  - leveringen proefdraaien, herhalen (idempotent), terugvinden en het geleverde bestand terughalen;
  - de registratie is meteen de catalogus (DCAT-AP-NL) voor afnemers en het API-register (#128).
- **Moeilijker:**
  - een dataset vullen vraagt vooraf een registratie en een Keycloak-rol;
  - Keycloak wordt een vaste afhankelijkheid voor machine-toegang;
  - ruwe leveringen vragen opslag en een bewaartermijn.
- **Migraties:** schema `laden` (datasets, leveringen, versies, staging); `gebied_data` krijgt `n`, `n_status` en `levering_id`; de unieke sleutel zonder scenario verdwijnt; `ON DELETE CASCADE` naar `indicatoren` wordt `RESTRICT`; `gebiedstypes` krijgt `actief` en `metadata`; volume voor ruwe leveringen.
- **Uitvoering:** implementatieplan in de RFC "D-OmniTwin vullen" § 8 en in #205.
- **Besloten (Eduard, 02-10-2026):**
  - **n-drempel per dataset** (`minimumN` in het laadprofiel, standaard 10), met een afwijking per indicator (`minimumNPerIndicator`); controle bij de ingang;
  - **bewaartermijn ruwe leveringen:** altijd de laatste 10 versies per dataset, oudere versies tot 1 jaar, afgekeurde leveringen 30 dagen; instelbaar;
  - **catalogus** eerst als JSON-LD-weergave (`Accept: application/ld+json`) van `laden/datasets`; een eigen API `catalogus/v1` pas als er een tweede bron van metadata is.
- **Open:**
  - de regel voor aggregaten (secundaire onderdrukking);
  - betekenis van indicatorstatus `A` in de SWF-definities;
  - de SWF-IdP (Entra) koppelen aan realm `omnitwin` (de huidige koppeling loopt in december af);
  - rollen per dataset of ook per gemeente (#34).

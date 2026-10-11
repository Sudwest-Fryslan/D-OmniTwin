# Use cases

Een use case is altijd een **bundel van drie dingen**:

1. **Data:** welke bronnen en indicatoren, voor welke gebieden en jaargangen.
2. **Inrichting:** de stuurinformatie: indicatorset, richting (hoger of lager is beter), Kompas-profiel, chatscenario.
3. **Stappen:** wat de gebruiker doet en wat hij dan verwacht te zien, als toetsbare controles.

**Werkafspraak:** elke nieuwe functionaliteit krijgt een use case. De use case werkt out of the box (verse installatie, ook zonder AI-sleutel) en wordt automatisch getest. Eerst de use case definiëren (vraag, data, controles), dan bouwen tot hij slaagt. Zie [CONTRIBUTING.md](../CONTRIBUTING.md#use-case-bij-elke-nieuwe-functionaliteit) en [ADR 0003](../docs/2-architectuur/adr/README.md).

**Leidend is de [D-OmniTwin Use Case Specificatie 1.0](../docs/specificaties/usecase/README.md)** ([ADR 0006](../docs/2-architectuur/adr/0006-usecase-als-declaratieve-app.md)): normatief, met de schema's in [`docs/specificaties/usecase/1.0/`](../docs/specificaties/usecase/1.0/usecase.schema.json). Deze README is het overzicht en de index; bij verschil geldt de specificatie.

## Een use case is een pakket, zonder code

Het manifest (`usecase.json`) is bewust app-achtig: naam, versie, afhankelijkheden, rechten, datasets en controles. **Een use case bevat geen code of uitvoerbare bestanden**, alleen beschrijvingen. Anders wordt een use case (ook een van buiten) een aanvalsvector. Waar data vandaan komt en hoe hij wordt bewerkt, staat declaratief in de use case; de kern voert het uit met een vaste set **bronadapters** en **bewerkingen** (`src/omnitwin/bronadapters/`). Een nieuwe soort bron is een nieuwe kernadapter, via een PR met tests. Het vervolg (use cases als installeerbare apps, uit een catalogus) krijgt een eigen issue.

```
usecases/<naam>/
├── usecase.json          ← manifest: specificatie, naam (= map), versie, titel, vraag, gebruiker, status,
│                           afhankelijk_van, actoren, rechten, datasets[], controles[], bewijs
├── README.md             ← vraag, gebruiker, stappen, acceptatiecriteria, bewijs, bekende afwijkingen
├── datasets/<id>.json    ← per dataset: registratie (DCAT `beschrijving` + `laadprofiel`) en
│                           `bron`, `bewerkingen`, `levering`, `varianten`
├── *.json / *.csv        ← optioneel: kleine statische mapping- of sjabloonbestanden
└── bewijs/               ← gevuld door de uitvoerder; in git alleen <stap>.webp, bewijs.json en README.md
```

- Schema's: [`usecase.schema.json`](../docs/specificaties/usecase/1.0/usecase.schema.json) (manifest), [`dataset.schema.json`](../docs/specificaties/usecase/1.0/dataset.schema.json) (dataset met het `bron`-blok per adapter) en [`bewijs.schema.json`](../docs/specificaties/usecase/1.0/bewijs.schema.json) (bewijsverslag). De registratie zelf volgt `DatasetRegistratie` in de [laad-API](../docs/api/laden/openapi.yaml).
- Toegestaan in de map: `.json`, `.md`, `.csv`; in `bewijs/` ook afbeeldingen. De uitvoerder en `tests/test_usecases_uitvoerder.py` keuren andere bestanden af, zonder uitzonderingen.
- De demo-use cases (TC-06-*) hebben naast de volledige vorm nog de velden van de verouderde vorm (`persona`, `data`, `inrichting`, `ai_zoekvraag`, `verwacht`): daaruit komt hun inrichting (richting van de indicatoren, via `laad_usecase.py --inrichting`) en de verwachting voor de chat. Hun data komt via de laad-API uit de datasets van hun afhankelijkheden (https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/236).

### Bronnen

Open data (CBS, PDOK, BAG, RIVM, Klimaateffectatlas) staat nooit in de repo: de use case beschrijft de bron (URL, laag, jaargang, licentie; in de DCAT-beschrijving `dct:source` en `dct:license`) en de adapter downloadt hem, met cache in `$DATA_CACHE`. Alleen wat echt intern is, komt uit een lokale map via een omgevingsvariabele:

| Variabele | Inhoud | Gebruikt door |
|---|---|---|
| `SWF_DUMP_DIR` | export van de huidige SWF-gebiedsmonitor (`output/*.json`, `data/*.csv`) | swf-definities, swf-basismonitor-waarden, swf-klimaatmonitor, swf-kompasprofiel, swf-adapter-fme |
| `SWF_DOCS_DIR` | projectmap van de gebiedsmonitor (o.a. `Demo/Demo data/`) | swf-gebiedsindelingen, swf-kaartlagen |
| `SWF_GEO_DIR` | GeoPackage-exports uit de GeoServer van SWF (welstand, bebouwde kom, grootgrondbezit) | swf-gebiedsindelingen, swf-kaartlagen |
| `SWF_DB_DUMP` | export van de database-dump van de huidige monitor, gemaakt met [`scripts/beheer/swf_monitor_dump.py`](../scripts/beheer/swf_monitor_dump.py) (`definities.json`, `waarden.json`, `kompasprofiel_monitor.csv`, …); heeft voorrang boven `SWF_DUMP_DIR` (variant `monitor-database`) | swf-definities, swf-basismonitor-waarden, swf-klimaatmonitor, swf-kompasprofiel; swf-gebruikersvoorkeuren (beheerscript) |
| `SWF_EXPORT_DIR` | export van een andere D-OmniTwin-installatie (CSV/GeoPackage), bijv. de lokale database voor de eerste vulling | swf-initialisatie |
| `DATA_CACHE` | cache van downloads (standaard `./data-cache`, in Docker het volume `bron-cache`) | alle |

Adapters: `swf-dump`, `cbs-odata`, `cbs-statline` (elke StatLine-tabel, ook RIVM en Politie via `dataderden.cbs.nl`), `wfs`, `wcs-zonaal` (gemiddelde van een raster per gebied), `download`, `lokaal-bestand` (alleen onder de mappen hierboven of `${REPO}`), `usecase-bestand` (een `.json`/`.csv` in de use case zelf). Downloads alleen via https van een allowlist (o.a. `opendata.cbs.nl`, `dataderden.cbs.nl`, `service.pdok.nl`, `api.pdok.nl`, `data.rivm.nl`, `klimaateffectatlas.nl`; uit te breiden met `OMNITWIN_BRON_DOMEINEN`), met optionele sha256. Bewerkingen: hernoemen, filteren en afwijzen op een voorwaarde, waarde-mapping, koppelen aan een mappingbestand, dubbele namen ontdubbelen met een voorkeurslijst, `JJJJ-01-01` → jaar, prefix voor codes, geometrie naar MultiPolygon, ruimtelijk filteren (zie de docstring van `bronadapters/bewerkingen.py`). Geen expressies, geen `eval`.

### Afhankelijkheden

`afhankelijk_van` noemt andere use cases op naam (de mapnaam), geen paden: `"swf-definities"`, of `{"naam": "cbs-kerncijfers", "versie": ">=0.1.0", "optioneel": true}`. De uitvoerder laadt eerst de afhankelijkheden in topologische volgorde, elke use case één keer, met een duidelijke fout bij een onbekende naam, een cyclus of een versie die niet voldoet. Een use case met `status: "ontwerp"` en alles wat er (niet-optioneel) van afhangt, wordt overgeslagen met een melding.

**Later extern** (nog niet ondersteund; de uitvoerder meldt het): `{"naam": "...", "bron": "<absolute URL van een git-repository of D-OmniTwin-installatie>", "versie": "<vaste tag>"}`. Altijd een absolute URL en een vaste versie, nooit een relatief pad. Elke use case kan dan een `uri` krijgen (zoals een DCAT-dataset) en de catalogus-API (`/api/catalogus/v1/usecases`) toont ze.

### Uitvoeren

```bash
python -m omnitwin.usecases lijst                  # naam, versie, status, titel, afhankelijkheden
python -m omnitwin.usecases boom swf-gebiedsmonitor
python -m omnitwin.usecases index                  # de tabel hieronder bijwerken
python -m omnitwin.usecases controleer swf-definities [--variant status-a] [--uit /tmp/levering]
python -m omnitwin.usecases installeer swf-gebiedsmonitor   # met afhankelijkheden; --alle voor alles
python -m omnitwin.usecases test swf-definities             # installeren + controles tegen de API
python -m omnitwin.usecases bewijs hittestress              # screenshots + bewijs.json (Playwright); --alle bij een release
python -m omnitwin.usecases galerij                         # galerij in README.md en schermen in de README's bijwerken
python -m omnitwin.usecases test swf-definities --testaccounts   # als de actoren, met rechtencontroles (test/dev)
python -m omnitwin.usecases opruimen swf-definities         # testaccounts weer weg
```

`bewijs` voert de `bewijs.stappen` uit het manifest uit in een browser (Playwright, tegen `OMNITWIN_BASE_URL`), en schrijft per stap een WebP-screenshot (≤ 150 KB) en `bewijs/bewijs.json`. Daarna toont de README van de use case de schermen en staat de use case in de galerij van de [root-README](../README.md#use-cases-in-beeld). Alleen bij een release opnieuw maken ([releasebeleid](../docs/9-beheer/releasebeleid.md)); het docker-commando staat in [`src/omnitwin/usecase_bewijs.py`](../src/omnitwin/usecase_bewijs.py), de regels in de [specificatie, sectie 12](../docs/specificaties/usecase/README.md#12-bewijs).

`controleer` werkt nu al, zonder draaiende stack: manifest tegen het schema, bestanden in de map, afhankelijkheden, registraties tegen de laad-API-specificatie, en de levering(en) maken uit de bron en valideren tegen het profiel (Table Schema met frictionless, GeoPackage met fiona). Ontbreekt een bron, dan is die dataset *overgeslagen*.

`installeer` en `test` registreren, leveren en controleren tegen een draaiende installatie: `OMNITWIN_BASE_URL` en een machineclient met client credentials (`OMNITWIN_CLIENT_ID`, `OMNITWIN_CLIENT_SECRET`). Zolang de laad-API er niet is (`/api/laden/v1/openapi.json`), melden ze dat. Demopakketten zonder `datasets` installeert `installeer` via `laad_usecase.py`, zodat er één ingang is. De acceptatietests per use case (`tests/integration/test_usecase_<naam>.py`) doen hetzelfde en slaan zichzelf over zolang de laad-API, een bron of de machineclient ontbreekt.

### Actoren en testaccounts

Een use case noemt in `actoren` wie hem gebruikt, met de Keycloak-rollen, en **nooit wachtwoorden of secrets** (de use cases staan in een publieke repo). Gebruikelijk zijn een `beheerder` (gebruiker, realm-rol `beheerder`: registreert de datasets), één machineclient per leverende partij met alleen `dataset:<id>:laden` voor zijn eigen datasets (de `client` van de dataset, bijv. `etl-swf`, `etl-cbs`), en een `lezer` (gebruiker, realm-rol `lezer`).

```json
"actoren": [
  {"naam": "beheerder", "soort": "gebruiker", "rollen": ["beheerder"]},
  {"naam": "etl-swf", "soort": "machineclient", "rollen": ["dataset:swf-monitor-definities:laden"]},
  {"naam": "lezer", "soort": "gebruiker", "rollen": ["lezer"]}
]
```

In productie maakt een beheerder die accounts aan in Keycloak en wijst hij de rollen toe; de use case laat zien welke nodig zijn. In **test en dev** maakt de uitvoerder ze zelf aan met `--testaccounts` (alleen met `OMNITWIN_TESTACCOUNTS=1`, geweigerd bij `OMNITWIN_OMGEVING=productie`): `uc-<usecase>-<actor>` in realm `omnitwin`, met willekeurige wachtwoorden en secrets in `.usecase-accounts.json` (in `.gitignore`, nooit in de log). De uitvoerder registreert dan als de beheerder, levert als de client van de dataset en voert controles met `actor` uit als die actor. Rechten controleer je declaratief met `type: recht`:

```json
{"type": "recht", "actor": "etl-swf", "actie": "leveren", "dataset": "cbs-kerncijfers", "toegestaan": false}
```

Geslaagd als de laad-API 403 geeft (`toegestaan: false`), of juist geen 401/403 (`toegestaan: true`). Het verzoek heeft een ongeldige parameter of body, dus er verandert niets. Zonder `--testaccounts` zijn rechtencontroles *overgeslagen*. `opruimen <naam>` verwijdert de testaccounts van de use case en zijn afhankelijkheden. Toegang tot de admin-API van Keycloak en de overige variabelen: [installatiegids, Keycloak](../docs/9-beheer/installatie.md#keycloak-optioneel); de regels: [specificatie, 10.1](../docs/specificaties/usecase/README.md#101-actoren).

**Verse installatie** (`LOAD_SAMPLE_DATA=true`): `db-init` draait `python -m omnitwin.usecases installeer --alle --inproces`: alle actieve use cases, met de laadstraat in-process (zelfde validatie, versies en DCAT als de laad-API, zonder HTTP en token; backend en Keycloak draaien dan nog niet). Open data wordt gedownload met cache in `$DATA_CACHE` (volume `bron-cache`); een bron die niet bereikbaar is, wordt overgeslagen met een melding en de installatie gaat door. Wat (nog) niet open is of nog geen adapter heeft, komt uit `sample-bronbibliotheek`, gemarkeerd (demodata: `dct:type` `demodata` en `DEMODATA` in de bron van elke waarde). Zie [demodata naar open data](../docs/3-data-engineering/demodata-naar-open-data.md).

**Actief via de laad-API (0.3.0, #229):** `cbs-gebiedsindelingen`, `cbs-kerncijfers` en `swf-definities` zijn getest tegen een verse stack met Keycloak en staan op `actief`. Sinds https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/236 laadt een verse installatie ze vanzelf (zie hierboven). Installeren op een draaiende installatie gaat met `python -m omnitwin.usecases installeer <naam>` (of `--alle`) en een machineclient met de realm-rol `beheerder` en de client-rol `datasets:laden` (aanmaken: `docker compose exec keycloak bash /opt/keycloak/omnitwin/machineclient.sh <client> beheerder datasets:laden`). `swf-basismonitor-waarden` blijft `ontwerp` tot de gebiedsindeling *buurten bebouwde komgrens* er is (`SWF_GEO_DIR`, use case `swf-gebiedsindelingen`): zonder die gebieden keurt de laad-API de 2.370 waarden op dat gebiedstype terecht af (`gebied-onbekend`).

**Demo-use cases:** een verse installatie laadt het product zonder data (stuurdata, indicatordefinities in `db/stuurdata/indicatoren.csv`, Kompas); de data komt uit de use cases. Een demo-use case hangt af van `cbs-gebiedsindelingen`, `cbs-kerncijfers`, `rivm-gezondheidsmonitor` en/of `sample-bronbibliotheek`, en `hittestress` heeft eigen datasets (RIVM WCS). `tests/test_usecase_pakketten.py` bewaakt dat elke indicator van een demo-use case door een dataset van een afhankelijkheid wordt geleverd, dat de sample alleen nog bevat wat niet open is of geen adapter heeft, en dat demodata gemarkeerd is; `tests/integration/test_usecases.py` toetst ze tegen een draaiende stack.

**Compatibiliteitsingang (#237):** `swf-adapter-fme` staat op `actief`: dezelfde FME-push (1 definities-aanroep, 57 waarde-aanroepen) gaat via `/api/laden/v1/compat/swf-monitor/...` naar D-OmniTwin en is bij herhaling idempotent. Zonder de gebiedsindelingen welstandsgebieden en buurten bebouwde komgrens (`swf-gebiedsindelingen`) geven 9 van de 57 aanroepen terecht `422 gebied-onbekend`; de controles houden daar rekening mee.

## Index

Gegenereerd met `python -m omnitwin.usecases index`; een unittest faalt als hij niet actueel is.

<!-- usecase-index:start -->
| Use case | ID | Titel | Gebruiker | Status | Versie | Afhankelijk van |
|---|---|---|---|---|---|---|
| [ai-compliance](./ai-compliance/README.md) | – | AI volgens de afspraken: vrijgave, herkenbaar, gelogd en uit te zetten | functioneel beheerder, AI Officer of auditor | actief | 0.1.0 | cbs-gebiedsindelingen, cbs-kerncijfers |
| [assistent-kwaliteit](./assistent-kwaliteit/README.md) | TC-06-009 | D-Omni Assistent vindt de juiste indicator en beantwoordt datavragen | beleidsadviseur of inwoner die de assistent gebruikt | ontwerp | 0.1.0 | – |
| [beleidsadviseur-swf](./beleidsadviseur-swf/README.md) | TC-06-001 | Beleidsadviseur verkent kernen in Súdwest-Fryslân (IJsselmeerkust) | Beleidsadviseur leefbaarheid / ruimtelijke ordening | actief | 0.2.0 | cbs-gebiedsindelingen, cbs-kerncijfers, sample-bronbibliotheek |
| [brede-welvaart](./brede-welvaart/README.md) | TC-06-007 | Brede welvaart en functiemenging | Strateeg / economische zaken | actief | 0.2.0 | cbs-gebiedsindelingen, cbs-kerncijfers, rivm-gezondheidsmonitor, sample-bronbibliotheek |
| [cbs-gebiedsindelingen](./cbs-gebiedsindelingen/README.md) | TC-07-001 | CBS-gebiedsindelingen (buurten, wijken, gemeenten) via de laad-API | beheerder D-OmniTwin | actief | 0.2.0 | – |
| [cbs-kerncijfers](./cbs-kerncijfers/README.md) | TC-07-002 | CBS Kerncijfers wijken en buurten via de laad-API | beheerder D-OmniTwin | actief | 0.2.0 | cbs-gebiedsindelingen |
| [energiearmoede](./energiearmoede/README.md) | TC-06-005 | Energietransitie en energiearmoede | Beleidsmaker energietransitie | actief | 0.2.0 | cbs-gebiedsindelingen, cbs-kerncijfers, rivm-gezondheidsmonitor, sample-bronbibliotheek |
| [hittestress](./hittestress/README.md) | TC-06-006 | Klimaatadaptatie: hittestress en kwetsbaarheid | Stedenbouwkundige / GGD | actief | 0.3.0 | cbs-gebiedsindelingen, cbs-kerncijfers, rivm-gezondheidsmonitor, sample-bronbibliotheek |
| [politie-misdrijven](./politie-misdrijven/README.md) | TC-07-022 | Politie: geregistreerde misdrijven per buurt via de laad-API | beheerder D-OmniTwin | actief | 0.2.0 | cbs-gebiedsindelingen |
| [rechten-per-laag](./rechten-per-laag/README.md) | TC-07-024 | Rechten per laag: interne lagen en indicatoren alleen na inloggen | beheerder D-OmniTwin | actief | 0.1.0 | cbs-gebiedsindelingen |
| [rivm-gezondheidsmonitor](./rivm-gezondheidsmonitor/README.md) | TC-07-021 | RIVM Gezondheidsmonitor per buurt via de laad-API | beheerder D-OmniTwin | actief | 0.2.0 | cbs-gebiedsindelingen |
| [sample-bronbibliotheek](./sample-bronbibliotheek/README.md) | TC-07-023 | Sample: wat nog niet open is of nog geen adapter heeft (gemarkeerd) | beheerder D-OmniTwin | actief | 0.2.0 | cbs-gebiedsindelingen |
| [sociale-cohesie](./sociale-cohesie/README.md) | TC-06-008 | Zorgzwaarte en sociale cohesie | Wijkcoördinator / wijkcontactfunctionaris | actief | 0.2.0 | cbs-gebiedsindelingen, cbs-kerncijfers, rivm-gezondheidsmonitor |
| [swf-adapter-fme](./swf-adapter-fme/README.md) | TC-07-009 | SWF-adapter: dezelfde FME-push naar D-OmniTwin | data-engineer DWH (SWF) | actief | 0.4.0 | swf-definities, cbs-gebiedsindelingen |
| [swf-basismonitor-waarden](./swf-basismonitor-waarden/README.md) | TC-07-006 | SWF-basismonitor: waarden per indicator × gebiedstype | data-engineer DWH (SWF) | ontwerp | 0.4.0 | swf-definities, swf-gebiedsindelingen, cbs-gebiedsindelingen |
| [swf-definities](./swf-definities/README.md) | TC-07-003 | SWF-definities: indicatoren, gebiedstypen en relaties | data-engineer DWH (SWF) | actief | 0.5.0 | – |
| [swf-gebiedsindelingen](./swf-gebiedsindelingen/README.md) | TC-07-004 | SWF-gebiedsindelingen als GeoPackage-leveringen | functioneel beheerder SWF / GIS-specialist | actief | 0.3.0 | swf-definities, cbs-gebiedsindelingen |
| [swf-gebiedsmonitor](./swf-gebiedsmonitor/README.md) | TC-07-010 | D-OmniTwin vervangt de huidige SWF-gebiedsmonitor (acceptatie) | kernteam gebiedsagenda en functioneel beheerder SWF | ontwerp | 0.4.0 | swf-definities, swf-gebiedsindelingen, swf-kompasprofiel, swf-basismonitor-waarden, swf-klimaatmonitor, swf-kaartlagen, swf-adapter-fme, swf-initialisatie, swf-gebruikersvoorkeuren (opt.) |
| [swf-gebruikersvoorkeuren](./swf-gebruikersvoorkeuren/README.md) | TC-07-026 | SWF-gebruikersvoorkeuren: laatste kaartpositie uit de huidige monitor | medewerker die de huidige gebiedsmonitor gebruikt; functioneel beheerder SWF (overzetten) | ontwerp | 0.1.0 | – |
| [swf-initialisatie](./swf-initialisatie/README.md) | TC-07-025 | SWF-initialisatie: vulling uit een dump van de lokale D-OmniTwin-database | projectleider en functioneel beheerder SWF | actief | 0.3.0 | swf-definities, cbs-gebiedsindelingen, swf-gebiedsindelingen |
| [swf-kaartlagen](./swf-kaartlagen/README.md) | TC-07-008 | SWF-kaartlagen: klimaat, deelgebieden, projecten en overige lagen | medewerker team of vakgroep (SWF) | actief | 0.3.0 | swf-gebiedsindelingen |
| [swf-klimaatmonitor](./swf-klimaatmonitor/README.md) | TC-07-007 | SWF-klimaatmonitor: welstand × buurt met labels A–E | adviseur klimaatadaptatie | ontwerp | 0.4.0 | swf-definities, swf-gebiedsindelingen, swf-kompasprofiel |
| [swf-kompasprofiel](./swf-kompasprofiel/README.md) | TC-07-005 | SWF-kompasprofielen Basis (4/12/33) en Klimaat | functioneel beheerder SWF | actief | 0.5.0 | swf-definities |
<!-- usecase-index:end -->

De vijf demopakketten komen uit de innovatieaanvraag Digitale Overheid 2026 en zijn nagespeeld op Bolsward, met focus op Bolsward-Zuidoost (status per pakket in zijn README). De `cbs-*`- en `swf-*`-use cases zijn de specificatie en straks de acceptatietests van de laad-API (0.3.0); `swf-gebiedsmonitor` is de acceptatietest voor "D-OmniTwin vervangt de huidige gebiedsmonitor".

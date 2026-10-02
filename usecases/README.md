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
└── bewijs/               ← gevuld door de uitvoerder (screenshots, bewijs.json); niet in git, behalve README.md
```

- Schema's: [`usecase.schema.json`](../docs/specificaties/usecase/1.0/usecase.schema.json) (manifest), [`dataset.schema.json`](../docs/specificaties/usecase/1.0/dataset.schema.json) (dataset met het `bron`-blok per adapter) en [`bewijs.schema.json`](../docs/specificaties/usecase/1.0/bewijs.schema.json) (bewijsverslag). De registratie zelf volgt `DatasetRegistratie` in de [laad-API](../docs/api/laden/openapi.yaml).
- Toegestaan in de map: `.json`, `.md`, `.csv`; in `bewijs/` ook afbeeldingen. De uitvoerder en `tests/test_usecases_uitvoerder.py` keuren andere bestanden af. Uitzondering, uit te faseren naar een kernadapter: `hittestress/maak_data.py`.
- De demopakketten van vóór 0.3.0 (hieronder zonder status) gebruiken nog de kleinere vorm (`id`, `titel`, `persona`, `data`, `inrichting`, `ai_zoekvraag`, `verwacht`) met `data/waarden.csv`, en laden via `init_data/scripts/laad_usecase.py`.

### Bronnen

Open data (CBS, PDOK, BAG, RIVM, Klimaateffectatlas) staat nooit in de repo: de use case beschrijft de bron (URL, laag, jaargang, licentie; in de DCAT-beschrijving `dct:source` en `dct:license`) en de adapter downloadt hem, met cache in `$DATA_CACHE`. Alleen wat echt intern is, komt uit een lokale map via een omgevingsvariabele:

| Variabele | Inhoud | Gebruikt door |
|---|---|---|
| `SWF_DUMP_DIR` | export van de huidige SWF-gebiedsmonitor (`output/*.json`, `data/*.csv`) | swf-definities, swf-basismonitor-waarden, swf-klimaatmonitor, swf-kompasprofiel, swf-adapter-fme |
| `SWF_DOCS_DIR` | projectmap van de gebiedsmonitor (o.a. `Demo/Demo data/`) | swf-gebiedsindelingen, swf-kaartlagen |
| `SWF_GEO_DIR` | GeoPackage-exports uit de GeoServer van SWF (welstand, bebouwde kom, grootgrondbezit) | swf-gebiedsindelingen, swf-kaartlagen |
| `SWF_DB_DUMP` | (later) database-dump van de huidige monitor | de swf-* use cases, als tweede bron |
| `DATA_CACHE` | cache van downloads (standaard `./data-cache`, in Docker het volume `bron-cache`) | alle |

Adapters: `swf-dump`, `cbs-odata`, `wfs`, `download`, `lokaal-bestand` (alleen onder de mappen hierboven of `${REPO}`), `usecase-bestand` (een `.json`/`.csv` in de use case zelf). Downloads alleen via https van een allowlist (o.a. `opendata.cbs.nl`, `service.pdok.nl`, `api.pdok.nl`, `data.rivm.nl`, `klimaateffectatlas.nl`; uit te breiden met `OMNITWIN_BRON_DOMEINEN`), met optionele sha256. Bewerkingen: hernoemen, filteren en afwijzen op een voorwaarde, waarde-mapping, koppelen aan een mappingbestand, `JJJJ-01-01` → jaar, prefix voor codes, geometrie naar MultiPolygon, ruimtelijk filteren (zie de docstring van `bronadapters/bewerkingen.py`). Geen expressies, geen `eval`.

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
```

`controleer` werkt nu al, zonder draaiende stack: manifest tegen het schema, bestanden in de map, afhankelijkheden, registraties tegen de laad-API-specificatie, en de levering(en) maken uit de bron en valideren tegen het profiel (Table Schema met frictionless, GeoPackage met fiona). Ontbreekt een bron, dan is die dataset *overgeslagen*.

`installeer` en `test` registreren, leveren en controleren tegen een draaiende installatie: `OMNITWIN_BASE_URL` en een machineclient met client credentials (`OMNITWIN_CLIENT_ID`, `OMNITWIN_CLIENT_SECRET`). Zolang de laad-API er niet is (`/api/laden/v1/openapi.json`), melden ze dat. Demopakketten zonder `datasets` installeert `installeer` via `laad_usecase.py`, zodat er één ingang is. De acceptatietests per use case (`tests/integration/test_usecase_<naam>.py`) doen hetzelfde en slaan zichzelf over zolang de laad-API, een bron of de machineclient ontbreekt.

De demopakketten laden zoals altijd: `python init_data/scripts/laad_usecase.py <naam> [...]` of `--alle` (ook bij een verse installatie met `LOAD_SAMPLE_DATA=true`). Dat script gebruikt dezelfde volgorde en slaat use cases met `datasets` over.

**Actief via de laad-API (0.3.0, #229):** `cbs-gebiedsindelingen`, `cbs-kerncijfers` en `swf-definities` zijn getest tegen een verse stack met Keycloak en staan op `actief`. Een verse installatie laadt ze niet vanzelf: `db-init` draait alleen `laad_usecase.py --alle`, en dat slaat use cases met `datasets` over (de demodata blijft dus gelijk). Installeren gaat met `python -m omnitwin.usecases installeer <naam>` (of `--alle`) en een machineclient met de realm-rol `beheerder` en de client-rol `datasets:laden` (aanmaken: `docker compose exec keycloak bash /opt/keycloak/omnitwin/machineclient.sh <client> beheerder datasets:laden`). `swf-basismonitor-waarden` blijft `ontwerp` tot de gebiedsindeling *buurten bebouwde komgrens* er is (`SWF_GEO_DIR`, use case `swf-gebiedsindelingen`): zonder die gebieden keurt de laad-API de 2.370 waarden op dat gebiedstype terecht af (`gebied-onbekend`).

**Demopakketten:** een verse installatie laadt het product zonder data (stuurdata, indicatordefinities, Kompas); de data komt uit de use cases. Een pakket laadt zijn gebieden uit de bronbibliotheek `init_data/sample/2_brondata`, zet de richting van de kernindicatoren, berekent afgeleide indicatoren en laadt extra brondata uit `data/waarden.csv`. `tests/test_usecase_pakketten.py` bewaakt dat elk gebied in de bronbibliotheek bij minstens één pakket hoort; `tests/integration/test_usecases.py` toetst ze tegen een draaiende stack.

## Index

Gegenereerd met `python -m omnitwin.usecases index`; een unittest faalt als hij niet actueel is.

<!-- usecase-index:start -->
| Use case | ID | Titel | Gebruiker | Status | Versie | Afhankelijk van |
|---|---|---|---|---|---|---|
| [beleidsadviseur-swf](./beleidsadviseur-swf/README.md) | TC-06-001 | Beleidsadviseur verkent kernen in Súdwest-Fryslân (IJsselmeerkust) | Beleidsadviseur leefbaarheid / ruimtelijke ordening | – | 0.1.0 | cbs-kerncijfers (opt.) |
| [brede-welvaart](./brede-welvaart/README.md) | TC-06-007 | Brede welvaart en functiemenging | Strateeg / economische zaken | – | 0.1.0 | cbs-kerncijfers (opt.) |
| [cbs-gebiedsindelingen](./cbs-gebiedsindelingen/README.md) | TC-07-001 | CBS-gebiedsindelingen (buurten, wijken, gemeenten) via de laad-API | beheerder D-OmniTwin | actief | 0.1.0 | – |
| [cbs-kerncijfers](./cbs-kerncijfers/README.md) | TC-07-002 | CBS Kerncijfers wijken en buurten via de laad-API | beheerder D-OmniTwin | actief | 0.1.0 | cbs-gebiedsindelingen |
| [energiearmoede](./energiearmoede/README.md) | TC-06-005 | Energietransitie en energiearmoede | Beleidsmaker energietransitie | – | 0.1.0 | cbs-kerncijfers (opt.) |
| [hittestress](./hittestress/README.md) | TC-06-006 | Klimaatadaptatie: hittestress en kwetsbaarheid | Stedenbouwkundige / GGD | – | 0.1.0 | cbs-kerncijfers (opt.) |
| [sociale-cohesie](./sociale-cohesie/README.md) | TC-06-008 | Zorgzwaarte en sociale cohesie | Wijkcoördinator / wijkcontactfunctionaris | – | 0.1.0 | cbs-kerncijfers (opt.) |
| [swf-adapter-fme](./swf-adapter-fme/README.md) | TC-07-009 | SWF-adapter: dezelfde FME-push naar D-OmniTwin | data-engineer DWH (SWF) | ontwerp | 0.1.0 | swf-definities |
| [swf-basismonitor-waarden](./swf-basismonitor-waarden/README.md) | TC-07-006 | SWF-basismonitor: waarden per indicator × gebiedstype | data-engineer DWH (SWF) | ontwerp | 0.1.0 | swf-definities, swf-gebiedsindelingen, cbs-gebiedsindelingen |
| [swf-definities](./swf-definities/README.md) | TC-07-003 | SWF-definities: indicatoren, gebiedstypen en relaties | data-engineer DWH (SWF) | actief | 0.1.0 | – |
| [swf-gebiedsindelingen](./swf-gebiedsindelingen/README.md) | TC-07-004 | SWF-gebiedsindelingen als GeoPackage-leveringen | functioneel beheerder SWF / GIS-specialist | ontwerp | 0.1.0 | swf-definities, cbs-gebiedsindelingen |
| [swf-gebiedsmonitor](./swf-gebiedsmonitor/README.md) | TC-07-010 | D-OmniTwin vervangt de huidige SWF-gebiedsmonitor (acceptatie) | kernteam gebiedsagenda en functioneel beheerder SWF | ontwerp | 0.1.0 | swf-definities, swf-gebiedsindelingen, swf-kompasprofiel, swf-basismonitor-waarden, swf-klimaatmonitor, swf-kaartlagen, swf-adapter-fme |
| [swf-kaartlagen](./swf-kaartlagen/README.md) | TC-07-008 | SWF-kaartlagen: klimaat, deelgebieden, projecten en overige lagen | medewerker team of vakgroep (SWF) | ontwerp | 0.1.0 | swf-gebiedsindelingen |
| [swf-klimaatmonitor](./swf-klimaatmonitor/README.md) | TC-07-007 | SWF-klimaatmonitor: welstand × buurt met labels A–E | adviseur klimaatadaptatie | ontwerp | 0.1.0 | swf-definities, swf-gebiedsindelingen, swf-kompasprofiel |
| [swf-kompasprofiel](./swf-kompasprofiel/README.md) | TC-07-005 | SWF-kompasprofielen Basis (4/12/33) en Klimaat | functioneel beheerder SWF | ontwerp | 0.1.0 | swf-definities |
<!-- usecase-index:end -->

De vijf demopakketten komen uit de innovatieaanvraag Digitale Overheid 2026 en zijn nagespeeld op Bolsward, met focus op Bolsward-Zuidoost (status per pakket in zijn README). De `cbs-*`- en `swf-*`-use cases zijn de specificatie en straks de acceptatietests van de laad-API (0.3.0); `swf-gebiedsmonitor` is de acceptatietest voor "D-OmniTwin vervangt de huidige gebiedsmonitor".

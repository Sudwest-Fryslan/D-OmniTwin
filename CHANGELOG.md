# Changelog

Alle noemenswaardige wijzigingen in D-OmniTwin worden in dit bestand bijgehouden.

De opmaak volgt [Keep a Changelog](https://keepachangelog.com/nl/1.1.0/). Versienummers volgen [Semantic Versioning](https://semver.org/lang/nl/). Hoe versies en releases werken staat in het [releasebeleid](docs/9-beheer/releasebeleid.md).

Eerdere wijzigingen, van vóór dit bestand, zijn terug te vinden in de git-historie, de [Issues](https://github.com/TLaan/D-OmniTwin/issues) en de [pull requests](https://github.com/TLaan/D-OmniTwin/pulls). [`BUILD.md`](./BUILD.md#-sprint-changelog) bevat daarnaast een sprint-changelog.

## [Unreleased]

Dit wordt de eerste release, `0.1.0`. Bij het taggen wordt dit kopje `## [0.1.0] - JJJJ-MM-DD` (zie de [checklist](docs/9-beheer/releasebeleid.md#een-release-maken-checklist)). Omdat dit de eerste versie is, vat deze sectie de ontwikkeling sinds het begin samen; details staan in de gekoppelde PR's en in [`BUILD.md`](./BUILD.md#-sprint-changelog).

### Toegevoegd

- Basis van de applicatie: D-Omni Kompas (indicatoren in 12 thema's als sunburst), interactieve kaart op buurtniveau (MapLibre GL, deck.gl, PDOK-basiskaart), Z-scores ten opzichte van een referentiegroep, gebiedsrapportages met export, en een AI-chat met een lokaal taalmodel (Ollama).
- Beheeromgeving (React) voor indicatoren, kompas, kaartlagen, prompts en LLM-configuratie.
- Dataspace-architectuur met PostgREST, pg_featureserv en Traefik als gateway ([#13](https://github.com/TLaan/D-OmniTwin/pull/13)).
- Externe kaartlagen beheren, inclusief lokale geodata en uploads; 3D-panden via 3DBAG ([#39](https://github.com/TLaan/D-OmniTwin/issues/39)).
- Configureerbare logging met automatische opschoning.
- Deduplicatie van indicatoren ([#19](https://github.com/TLaan/D-OmniTwin/issues/19)).
- Woonplaats- en deelgebiedsanalyse als rapport ([#45](https://github.com/TLaan/D-OmniTwin/pull/45)).
- GitHub Actions-pipeline met unittests en Docker-buildcontrole ([#49](https://github.com/TLaan/D-OmniTwin/pull/49)).
- Sample dataset met stuurdata en brondata voor 12 buurten in Súdwest-Fryslân, met Bolsward-Zuidoost als testbuurt, voor demo en test ([#53](https://github.com/TLaan/D-OmniTwin/pull/53), [#80](https://github.com/TLaan/D-OmniTwin/pull/80)).
- De sample als Frictionless datapakket met licentie en herkomst ([#86](https://github.com/TLaan/D-OmniTwin/pull/86)).
- Container-entrypoint dat bij de eerste start het databaseschema aanmaakt, de sample dataset laadt (`LOAD_SAMPLE_DATA=true`) en een admin-gebruiker aanmaakt ([#52](https://github.com/TLaan/D-OmniTwin/issues/52)).
- Integratietests tegen een verse stack met de sample dataset ([#70](https://github.com/TLaan/D-OmniTwin/pull/70)).
- Use cases, e2e-scenario's en nulmetingen als testcases ([#77](https://github.com/TLaan/D-OmniTwin/pull/77)).
- `publiccode.yml`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md` en een concept `PROJECT_GOVERNANCE.md` ([#76](https://github.com/TLaan/D-OmniTwin/pull/76)).
- `AGENTS.md` en `CONTRIBUTING.md` met de werkwijze van issue tot merge ([#35](https://github.com/TLaan/D-OmniTwin/pull/35), [#37](https://github.com/TLaan/D-OmniTwin/pull/37)).
- Releasebeleid en één bron voor het versienummer (`VERSION`), met een test die de versies gelijk houdt ([#27](https://github.com/TLaan/D-OmniTwin/issues/27)).

### Gewijzigd

- Eén installatiegids voor beheerders, getest op een verse clone ([#87](https://github.com/TLaan/D-OmniTwin/pull/87)).
- Docker Compose gesplitst in installatie en ontwikkeling, met healthchecks en een aparte db-init-service ([#78](https://github.com/TLaan/D-OmniTwin/pull/78)).
- Docker-images, Python-afhankelijkheden en frontend-bibliotheken vastgepind voor reproduceerbare builds; CDN-bibliotheken met SRI ([#74](https://github.com/TLaan/D-OmniTwin/pull/74), [#84](https://github.com/TLaan/D-OmniTwin/pull/84)).
- Een Mapbox-token is niet meer nodig ([#72](https://github.com/TLaan/D-OmniTwin/pull/72)).
- Toegankelijkheid, eerste ronde WCAG 2.1 AA: focus, labels, toetsenbord en contrast ([#75](https://github.com/TLaan/D-OmniTwin/pull/75)).
- Bug- en backlogtracking samengebracht in GitHub Issues ([#48](https://github.com/TLaan/D-OmniTwin/pull/48)).
- Versienummer overal `0.1.0`; de uiteenlopende nummers (README `v1.0.0-beta`, API `1.5.0`/`1.2.0`, footer `API v0.2.0`) zijn vervangen door de waarde uit `VERSION` ([#27](https://github.com/TLaan/D-OmniTwin/issues/27)).

### Verwijderd

- Kapotte en dode backend-endpoints ([#73](https://github.com/TLaan/D-OmniTwin/pull/73)).

### Opgelost

- WebGL-buffercorruptie bij het wisselen van gemeente en een 404-lus in de beheeromgeving ([#43](https://github.com/TLaan/D-OmniTwin/pull/43)).
- Buurten in een deelgebied via een pg_featureserv-functie ([#85](https://github.com/TLaan/D-OmniTwin/pull/85)).
- Bevindingen uit de UI-test: tellers uit de data, Kompas opent bij klik, nette melding zonder taalmodel ([#82](https://github.com/TLaan/D-OmniTwin/pull/82)).
- Beheeromgeving: rapporten in het menu, Benchmark via PostgREST, geen hardgecodeerd gebied ([#81](https://github.com/TLaan/D-OmniTwin/pull/81)).

### Beveiliging

- Geen standaard admin/admin-wachtwoord meer bij de container-initialisatie: zonder `ADMIN_PASSWORD` wordt eenmalig een willekeurig wachtwoord gegenereerd ([#52](https://github.com/TLaan/D-OmniTwin/issues/52)).
- Geen hardgecodeerd databasewachtwoord meer in `generate_sample.py` ([#52](https://github.com/TLaan/D-OmniTwin/issues/52)).
- `.dockerignore` toegevoegd, zodat onder meer `.env` niet in het image belandt ([#52](https://github.com/TLaan/D-OmniTwin/issues/52)).
- De backend-container draait als niet-root gebruiker ([#78](https://github.com/TLaan/D-OmniTwin/pull/78)).
- Beheeromgeving gebouwd zonder sourcemaps ([#81](https://github.com/TLaan/D-OmniTwin/pull/81)).

### Gepland voor 0.1.0

Open pull requests die in 0.1.0 horen (stand 2026-10-01, zonder Dependabot). Na de merge verhuist elke regel naar de juiste categorie hierboven; wat niet op tijd gemerged is, schuift door naar 0.2.0.

- Beveiliging: PostgREST en pg_featureserv met eigen rollen en schema `api`, anoniem geen toegang meer tot gebruikers en sessies ([#146](https://github.com/TLaan/D-OmniTwin/pull/146)).
- Beveiliging: security-headers en CSP voor alle routes via Traefik, `security.txt`, TLS-voorbeeld ([#145](https://github.com/TLaan/D-OmniTwin/pull/145)).
- Privacy: frontend-bibliotheken en lettertype zelf hosten, geen Google Fonts, unpkg of jsdelivr meer ([#144](https://github.com/TLaan/D-OmniTwin/pull/144)).
- Contactadres in SECURITY, gedragscode en `publiccode.yml` ([#147](https://github.com/TLaan/D-OmniTwin/pull/147)).
- Issue- en PR-templates, databronlicenties in NOTICE, bronvermelding op de kaart ([#132](https://github.com/TLaan/D-OmniTwin/pull/132)).
- `.env.example` terug naar het minimum, met een test op drift ([#133](https://github.com/TLaan/D-OmniTwin/pull/133)).
- CI: verse stack met integratie- en e2e-tests en publiccode-validatie ([#114](https://github.com/TLaan/D-OmniTwin/pull/114)); browser-e2e-tests per testcase en fix van de CSV-export ([#112](https://github.com/TLaan/D-OmniTwin/pull/112)).
- Dependabot groepeert minor- en patch-updates ([#105](https://github.com/TLaan/D-OmniTwin/pull/105)).
- Beheeromgeving van Create React App naar Vite 8 en TypeScript 5 ([#110](https://github.com/TLaan/D-OmniTwin/pull/110)).
- Volledige Fryslân-data laden in Docker met één commando, gemeentecodes gecorrigeerd ([#111](https://github.com/TLaan/D-OmniTwin/pull/111)).
- Use cases als pakket: alle demodata hoort bij een use case, met laadscript en tests ([#141](https://github.com/TLaan/D-OmniTwin/pull/141)).
- Taalmodel: OpenAI-compatibele koppeling naast Ollama ([#107](https://github.com/TLaan/D-OmniTwin/pull/107)); aanbieders wisselen en vergelijken ([#142](https://github.com/TLaan/D-OmniTwin/pull/142)).
- Embeddings bij de database-initialisatie, zodat chat en AI-zoeken indicatoren vinden ([#143](https://github.com/TLaan/D-OmniTwin/pull/143)).
- Chat: gemeentekeuze van het taalmodel valideren, actief gemeentefilter zichtbaar ([#148](https://github.com/TLaan/D-OmniTwin/pull/148)).
- Kaart: fitBounds, selectiebadge, Kompas vanuit de chat laadt de selectie ([#113](https://github.com/TLaan/D-OmniTwin/pull/113)).
- Toegankelijkheid ronde 2: dialogen met focusbeheer, reduced motion, admin-labels ([#134](https://github.com/TLaan/D-OmniTwin/pull/134)).
- Backend crasht niet meer in dev-modus op Windows ([#115](https://github.com/TLaan/D-OmniTwin/pull/115)).
- Screenshots actueel en reproduceerbaar ([#136](https://github.com/TLaan/D-OmniTwin/pull/136)).

[Unreleased]: https://github.com/TLaan/D-OmniTwin/commits/main

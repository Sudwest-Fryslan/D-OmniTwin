# Releasebeleid

Hoe D-OmniTwin versies nummert, hoe een release ontstaat en welke versies ondersteund worden. Besloten in [#27](https://github.com/TLaan/D-OmniTwin/issues/27).

## Kort

- Versienummers volgen [Semantic Versioning](https://semver.org/lang/nl/): `MAJOR.MINOR.PATCH`.
- De eerste versie is `0.1.0`.
- Ontwikkeling gebeurt op `main` via GitHub Flow ([CONTRIBUTING.md](../../CONTRIBUTING.md)).
- Elke minorversie krijgt een eigen release-branch `release/<MAJOR>.<MINOR>`, en elke release een tag `v<versie>`.
- Alleen de laatste release-branch krijgt nog (beveiligings)fixes.

## Versienummer

| Stap | Wanneer | Voorbeeld |
|---|---|---|
| PATCH | alleen bugfixes, niets breekt | `0.1.0` → `0.1.1` |
| MINOR | nieuwe functionaliteit | `0.1.1` → `0.2.0` |
| MAJOR | brekende wijziging (vanaf 1.0.0) | `1.4.2` → `2.0.0` |

**Onder 1.0.0** mag elke minor brekende wijzigingen bevatten ([semver §4](https://semver.org/lang/nl/#spec-item-4)): API, databaseschema, configuratie (`.env`) of installatiestappen kunnen dan veranderen. Dat staat altijd in de CHANGELOG onder "Gewijzigd" of "Verwijderd", met de stappen voor wie bijwerkt.

**1.0.0** komt als de publieke afspraken stabiel genoeg zijn om ze niet zomaar meer te breken:

- de API (`/api/...`, PostgREST- en pg_featureserv-endpoints) is beschreven en wijzigt niet meer onaangekondigd;
- installeren en bijwerken van een bestaande installatie werkt met de installatiegids, inclusief databasemigraties;
- een andere organisatie dan Súdwest-Fryslân draait het in productie.

Vanaf 1.0.0 betekent een brekende wijziging een nieuwe major.

### Eén bron: `VERSION`

Het versienummer staat op één plek: het bestand [`VERSION`](../../VERSION) in de root. De rest volgt daaruit of wordt erop gecontroleerd:

| Plek | Hoe |
|---|---|
| FastAPI (`/openapi.json`, `/docs`, `/api`, `/health`) | `src/version.py` leest `VERSION` |
| Footer van de gebruikersinterface | Jinja-variabele `app_version`, gezet in `main.py` |
| `publiccode.yml` (`softwareVersion`) | met de hand, gecontroleerd door de test |
| `admin-panel/package.json` (`version`) | met de hand, gecontroleerd door de test |

De test `tests/test_versie.py` faalt als deze uiteenlopen of als `VERSION` geen geldige semver is.

## Branches en tags

```
main ──●──●──●──●──●──●──●──●──●──►        (ontwikkeling, GitHub Flow)
             │           │
             │           └── release/0.2 ──● v0.2.0
             └── release/0.1 ──● v0.1.0 ──● v0.1.1 (cherry-pick van een fix op main)
```

- `main`: altijd de nieuwste stand. Alle wijzigingen komen hier binnen via een PR.
- `release/<MAJOR>.<MINOR>`: gemaakt vanaf `main` op het moment van de release. Hier komen daarna alleen nog fixes op, geen features.
- Tags `v<MAJOR>.<MINOR>.<PATCH>` staan op de release-branch, nooit op `main`.

## Commits en CHANGELOG

- Commitberichten en PR-titels volgen [Conventional Commits](https://www.conventionalcommits.org/nl/v1.0.0/): `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `ci:`, `build:`, `refactor:`, eventueel met scope (`fix(kaart):`). Een brekende wijziging krijgt `!` (`feat(api)!:`) of een regel `BREAKING CHANGE:` in de body.
- [`CHANGELOG.md`](../../CHANGELOG.md) volgt [Keep a Changelog](https://keepachangelog.com/nl/1.1.0/). Een PR met een merkbare wijziging zet een regel onder `## [Unreleased]`. Bij de release wordt dat kopje de nieuwe versie.

## Een release maken (checklist)

Voorbeeld voor `0.2.0`.

1. **Klaar op `main`:** alle PR's voor deze versie zijn gemerged, de CI is groen.
2. **Release-PR naar `main`** (branch `chore/release-0.2.0`):
   - `VERSION`, `publiccode.yml` (`softwareVersion` en `releaseDate`) en `admin-panel/package.json` (plus `package-lock.json`, via `npm version 0.2.0 --no-git-tag-version` in `admin-panel/`) op `0.2.0`;
   - in `CHANGELOG.md`: `## [Unreleased]` wordt `## [0.2.0] - JJJJ-MM-DD`, nieuwe lege `## [Unreleased]` erboven, vergelijkingslinks onderaan bijwerken;
   - `pytest -m unit` lokaal groen (incl. de versietest).
3. **Mergen** na review.
4. **Release-branch en tag** vanaf de merge-commit op `main`:
   ```bash
   git switch -c release/0.2 origin/main
   git tag -a v0.2.0 -m "D-OmniTwin 0.2.0"
   git push origin release/0.2 v0.2.0
   ```
5. **GitHub-release** bij de tag, met de CHANGELOG-sectie als tekst. Grote databestanden die niet in git horen, gaan als release-asset mee (op code.overheid.nl staat LFS uit).
6. **Controle:** een verse installatie volgens de [installatiegids](installatie.md) vanaf de tag werkt, en `/health` toont `0.2.0`.

## Patches

Voorbeeld: een bug in `0.1.0`.

1. Fix via de gewone weg: issue → `feature/<nr>-naam` → PR naar `main`.
2. Na de merge: de fix naar de release-branch, via een cherry-pick of een PR naar `release/0.1`.
   ```bash
   git switch release/0.1
   git cherry-pick -x <commit van de fix op main>
   ```
3. Op `release/0.1`: `VERSION` e.d. naar `0.1.1`, CHANGELOG-sectie `## [0.1.1]` (ook op `main` toevoegen), tag `v0.1.1`, GitHub-release.

Een fix die alleen op de oude versie speelt, gaat direct als PR naar de release-branch.

## Ondersteunde versies

Alleen de **laatste** release-branch krijgt fixes, ook beveiligingsfixes. Komt `release/0.2` uit, dan krijgt `release/0.1` niets meer. Dit staat ook in [SECURITY.md](../../SECURITY.md#ondersteunde-versies).

## Volgende stap: automatiseren

Nu gaat een release met de hand, met de checklist hierboven. Een mogelijke volgende stap is [semantic-release](https://semantic-release.gitbook.io/) in GitHub Actions (patroon: `Sudwest-Fryslan/WebformulierenVerwerker`, `.github/workflows/ci-build.yml`). Die leidt het volgende versienummer af uit de conventional commits, schrijft `VERSION` en de CHANGELOG bij, en maakt tag en GitHub-release. Daarnaast kan de CI het versienummer meegeven aan de Docker-images (tag en OCI-label `org.opencontainers.image.version`, zie [cicd_pipeline_docker_hub.md](cicd_pipeline_docker_hub.md)) en aan de cache-busting van de frontend ([#131](https://github.com/TLaan/D-OmniTwin/issues/131)).

Dat vraagt eerst een keuze over de CI (GitHub Actions of de omgeving van code.overheid.nl) en over hoe semantic-release met release-branches per minor omgaat. Daarom is het nog niet gebouwd.

# Changelog

Alle noemenswaardige wijzigingen in D-OmniTwin worden in dit bestand bijgehouden.

De opmaak volgt [Keep a Changelog](https://keepachangelog.com/nl/1.1.0/). Versienummers volgen straks [Semantic Versioning](https://semver.org/lang/nl/); de afspraken daarover en de eerste release-tag staan nog open in [#27](https://github.com/TLaan/D-OmniTwin/issues/27).

Eerdere wijzigingen, van vóór dit bestand, zijn terug te vinden in de git-historie, de [Issues](https://github.com/TLaan/D-OmniTwin/issues) en de [pull requests](https://github.com/TLaan/D-OmniTwin/pulls). [`BUILD.md`](./BUILD.md#-sprint-changelog) bevat daarnaast een sprint-changelog.

## [Unreleased]

Onderstaande wijzigingen staan (deels) nog in open pull requests.

### Toegevoegd

- Sample dataset met stuurdata en brondata voor 12 buurten in Súdwest-Fryslân, voor demo en test ([#52](https://github.com/TLaan/D-OmniTwin/issues/52), [#53](https://github.com/TLaan/D-OmniTwin/pull/53)).
- Container-entrypoint dat bij de eerste start het databaseschema aanmaakt, de sample dataset laadt (`LOAD_SAMPLE_DATA=true`) en een admin-gebruiker aanmaakt ([#52](https://github.com/TLaan/D-OmniTwin/issues/52)).
- Integratietests tegen een verse stack met de sample dataset ([#62](https://github.com/TLaan/D-OmniTwin/issues/62), [#70](https://github.com/TLaan/D-OmniTwin/pull/70)).
- `publiccode.yml` voor vindbaarheid in codebase-registers ([#56](https://github.com/TLaan/D-OmniTwin/issues/56)).
- `SECURITY.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md` en een concept `PROJECT_GOVERNANCE.md` ([#61](https://github.com/TLaan/D-OmniTwin/issues/61)).

### Gewijzigd

- Een Mapbox-token is niet meer nodig; documentatie en configuratie zijn daarop aangepast ([#55](https://github.com/TLaan/D-OmniTwin/issues/55)).
- Docker-images en afhankelijkheden vastgepind voor reproduceerbare builds ([#58](https://github.com/TLaan/D-OmniTwin/issues/58)).
- README: sectie "Snel starten" met Docker Compose en correcte poorten (alles via Traefik op poort 80).

### Beveiliging

- Geen standaard admin/admin-wachtwoord meer bij de container-initialisatie: zonder `ADMIN_PASSWORD` wordt eenmalig een willekeurig wachtwoord gegenereerd ([#52](https://github.com/TLaan/D-OmniTwin/issues/52)).
- Geen hardgecodeerd databasewachtwoord meer in `generate_sample.py` ([#52](https://github.com/TLaan/D-OmniTwin/issues/52)).
- `.dockerignore` toegevoegd, zodat onder meer `.env` niet in het image belandt ([#52](https://github.com/TLaan/D-OmniTwin/issues/52)).
- Security-headers (CSP, `X-Frame-Options`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`) via Traefik op alle routes, ook `/api/data` en `/api/geo`; HSTS op HTTPS; `/.well-known/security.txt`; voorbeeld voor HTTPS met Let's Encrypt in `deploy/traefik/tls.example.yml` ([#121](https://github.com/TLaan/D-OmniTwin/issues/121)).

[Unreleased]: https://github.com/TLaan/D-OmniTwin/commits/main

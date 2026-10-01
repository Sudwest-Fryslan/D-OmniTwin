# Beveiligingsbeleid

## Een kwetsbaarheid melden

Heb je een kwetsbaarheid gevonden in D-OmniTwin? Meld die dan **niet** via een openbaar issue, discussie of pull request, maar privé per e-mail:

**Taeke van der Laan** (Gemeente Súdwest-Fryslân) — `<e-mailadres Taeke, te bevestigen>`

Vermeld in je melding:

- welk onderdeel het betreft (bijvoorbeeld backend-API, beheeromgeving, database-initialisatie, Docker-configuratie);
- hoe de kwetsbaarheid te reproduceren is (stappen, verzoeken, eventueel een proof of concept);
- de versie of commit waarop je het hebt gevonden;
- wat volgens jou de impact is;
- hoe we je kunnen bereiken voor vragen.

Gebruik geen echte persoonsgegevens of productiedata van anderen om de kwetsbaarheid aan te tonen, en doe niet meer dan nodig is om het probleem vast te stellen.

## Wat je van ons kunt verwachten

- We reageren zo snel mogelijk en streven ernaar een melding binnen 5 werkdagen te bevestigen. Een harde termijn kunnen we niet garanderen.
- We houden je op de hoogte van de beoordeling en de oplossing.
- We maken een kwetsbaarheid pas openbaar als er een oplossing beschikbaar is, in overleg met de melder.
- Als je dat wilt, noemen we je naam bij de oplossing.

We volgen hierbij de uitgangspunten van [Coordinated Vulnerability Disclosure](https://www.ncsc.nl/contact/kwetsbaarheid-melden) van het NCSC.

## Scope

Binnen scope is de code in deze repository:

- de FastAPI-backend en API-routes (`main.py`, `routers/`, `services/`);
- de gebruikersinterface en de beheeromgeving (`static/`, `templates/`, `admin-panel/`);
- database-schema's, migraties en initialisatiescripts (`init_data/`, `migrations/`);
- de Docker-configuratie (`Dockerfile`, `db.Dockerfile`, `docker-compose.yml`, `docker-entrypoint.sh`).

Buiten scope:

- kwetsbaarheden in afhankelijkheden van derden (zoals PostgreSQL, PostgREST, pg_featureserv, Traefik, Ollama) — meld die bij het betreffende project; laat het ons wel weten als D-OmniTwin ze op een onveilige manier gebruikt;
- installaties van D-OmniTwin die door andere organisaties worden beheerd — meld die bij de beheerder van die installatie;
- de lokale ontwikkelconfiguratie (zoals het Traefik-dashboard op poort 8081 en `DEBUG=true`), die niet bedoeld is voor productie.

## Ondersteunde versies

D-OmniTwin volgt [Semantic Versioning](https://semver.org/lang/nl/); de eerste release is `0.1.0`. Elke minorversie heeft een eigen release-branch (`release/0.1`, `release/0.2`, ...). Beveiligingsoplossingen komen op `main` en op de **laatste** release-branch, als patchrelease (bijvoorbeeld `0.1.1`). Oudere release-branches krijgen geen oplossingen meer. Zie het [releasebeleid](docs/9-beheer/releasebeleid.md).

| Versie | Ondersteund |
|--------|-------------|
| `main` | Ja |
| Laatste release-branch (nu: `0.1.x`, zodra uitgebracht) | Ja |
| Oudere release-branches, losse commits en forks | Nee |

---

## English summary

Please **do not** report security vulnerabilities through public GitHub issues. Report them privately by e-mail to Taeke van der Laan (Municipality of Súdwest-Fryslân): `<e-mailadres Taeke, te bevestigen>`. Include the affected component, reproduction steps, the version or commit, and the expected impact. We aim to acknowledge reports within 5 working days (no guaranteed SLA) and follow coordinated vulnerability disclosure. Security fixes go to `main` and to the latest release branch only (see the release policy in `docs/9-beheer/releasebeleid.md`).

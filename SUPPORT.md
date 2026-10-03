# Ondersteuning

Wat je van het onderhoud van D-OmniTwin mag verwachten, en waar je terechtkunt. Volgens de [OWC-afspraak](https://github.com/OpenWebconcept/.github/blob/main/docs/SUPPORT.md): minimaal een jaar onderhoud, en het einde een jaar vooraf aangekondigd. Zie ook [GOVERNANCE.md](./GOVERNANCE.md).

## Onderhoudstermijn

- **Beheerder:** Gemeente Súdwest-Fryslân (zie `maintenance` in [publiccode.yml](./publiccode.yml)).
- **Onderhoudsgarantie:** **één jaar**. De beheerder onderhoudt elke uitgebrachte versie ten minste een jaar na de release (fouten en beveiligingsupdates op de laatste releasetak).
- **Einde van het onderhoud** wordt minimaal **een jaar vooraf** aangekondigd: in deze repository (README en een issue), in de CHANGELOG en in `publiccode.yml` (`maintenance.type: none`).

## Wat je mag verwachten

| Wat | Hoe |
|---|---|
| **Fouten in de code** (tweedelijns ondersteuning) | Meld een issue. De beheerder reageert, beoordeelt en plant een oplossing; een fix komt in de volgende release. |
| **Beveiligingslekken** | Niet via een openbaar issue, maar via [SECURITY.md](./SECURITY.md). Fixes komen ook op de laatste release-branch. |
| **Ondersteunde versies** | Alleen de laatste release-branch krijgt nog fixes (zie het [releasebeleid](./docs/9-beheer/releasebeleid.md#ondersteunde-versies)). |
| **Wijzigingsverzoeken en bijdragen** | Via een issue en een pull request ([CONTRIBUTING.md](./CONTRIBUTING.md)). De beheerder beoordeelt ze, ook van andere partijen en concurrenten. |
| **Nieuwe versies** | Een GitHub-release per versie, met de wijzigingen en migratiestappen in de [CHANGELOG](./CHANGELOG.md). Volg de releases van de repository (*Watch > Custom > Releases*). |
| **Installatie en beheer** | De [installatiegids](./docs/9-beheer/installatie.md) en de documentatie in `docs/9-beheer/`. |

**Niet inbegrepen:** eerstelijns ondersteuning voor gebruikers van een installatie, het beheer van jouw installatie, je data en je koppelingen, en maatwerk. Dat regelt elke organisatie zelf, eventueel met een leverancier. Elke organisatie draait een eigen instantie ([mesh van instanties](./docs/2-architectuur/mesh-van-instanties.md)).

## Kanalen

- **Issues:** [github.com/TLaan/D-OmniTwin/issues](https://github.com/TLaan/D-OmniTwin/issues), voor fouten, vragen en wensen.
- **Beveiliging:** [SECURITY.md](./SECURITY.md).
- **Contact met de beheerder:** het functionele adres in `maintenance.contacts` van [publiccode.yml](./publiccode.yml).

---

## English summary

Maintenance guarantee: **one year**. Súdwest-Fryslân maintains each released version for at least one year after its release. The end of maintenance is announced at least one year in advance (README, an issue, the CHANGELOG and `publiccode.yml`). Bugs and change requests: GitHub issues; security issues: [SECURITY.md](./SECURITY.md). Only the latest release branch receives fixes. Running and supporting your own installation is up to your organisation.

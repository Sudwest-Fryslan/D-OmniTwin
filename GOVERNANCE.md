# Governance

Hoe D-OmniTwin beheerd wordt: wie welke rol heeft, hoe wijzigingen binnenkomen en hoe besluiten vallen. De opbouw volgt de afspraken van het [OpenWebconcept](https://github.com/OpenWebconcept/.github/blob/main/docs/GOVERNANCE.md) (OWC), waarvan Gemeente Súdwest-Fryslân mede-oprichter is. Besloten in [#183](https://github.com/TLaan/D-OmniTwin/issues/183): de OWC-governance is de basis, en we volgen de OWC-standaarden en -afspraken. Of D-OmniTwin formeel een OWC-bouwblok wordt, is nog niet besloten.

Zie ook: [SUPPORT.md](./SUPPORT.md) (onderhoud en ondersteuning), [PARTICIPANTS.md](./PARTICIPANTS.md) (deelnemers), [CONTRIBUTING.md](./CONTRIBUTING.md) (werkwijze), [SECURITY.md](./SECURITY.md) en de [gedragscode](./CODE_OF_CONDUCT.md).

## Uitgangspunten

- **Open source:** licentie EUPL-1.2 voor de code ([LICENSE](./LICENSE)); documentatie onder [LICENSE-DOCS](./LICENSE-DOCS).
- **Open samenwerking:** gemeenten, andere overheden en leveranciers kunnen meedoen, gebruiken en bijdragen. Ook weer stoppen kan, zonder afhankelijkheid: elke organisatie draait een eigen instantie en alles wat die inricht is uitwisselbaar als data ([mesh van instanties](./docs/2-architectuur/mesh-van-instanties.md)).
- **Pragmatisch:** alleen formeel waar het nodig is.
- **Geen afhankelijkheid van closed source**, tenzij in de README vermeld. Externe AI-aanbieders zijn optioneel; standaard draait alles lokaal.

## Rollen

| Rol | Wie | Wat dat inhoudt |
|---|---|---|
| **Eigenaar** | Gemeente Súdwest-Fryslân | Houder van het auteursrecht en de repository (`organisation` en `legal.mainCopyrightOwner` in [publiccode.yml](./publiccode.yml)). Staat garant voor de repository. |
| **Beheerder** | Gemeente Súdwest-Fryslân | Beoordeelt en merget pull requests, beheert releases en beveiligingsmeldingen, houdt de roadmap bij en ondersteunt andere partijen, ook als die elkaars concurrent zijn. Contact: `maintenance.contacts` in [publiccode.yml](./publiccode.yml) (een functioneel adres, geen persoon). |
| **Deelnemer** | Zie [PARTICIPANTS.md](./PARTICIPANTS.md) | Gebruikt of test D-OmniTwin, levert use cases, wensen en feedback, en neemt deel aan de projectgroep. |
| **Bijdrager** | Iedereen: gemeenten, andere overheden, leveranciers, inwoners | Meldt issues en levert pull requests volgens [CONTRIBUTING.md](./CONTRIBUTING.md). Een gemeente kan ook bijdrager (leverancier) zijn. |

De beheerder kan later een andere organisatie worden, bijvoorbeeld na de overdracht naar de organisatie van Súdwest-Fryslân ([#30](https://github.com/TLaan/D-OmniTwin/issues/30)). Dat wordt dan in `publiccode.yml` en hier aangepast.

## Werkwijze

- **Elke wijziging via een pull request** naar `main`, vanuit een issue (GitHub Flow, zie [CONTRIBUTING.md](./CONTRIBUTING.md)). Niemand merget eigen werk.
- **Review door een andere partij:** een pull request wordt goedgekeurd door iemand anders dan de indiener, **bij voorkeur van een andere organisatie** (gemeente of leverancier). Bij wijzigingen aan beveiliging, de API's of het datamodel is dat sterk gewenst.
- **Branch protection** op `main`: pull request verplicht, CI groen, minimaal één goedkeuring. Dit vraagt beheerrechten op de repository en staat nog open ([#29](https://github.com/TLaan/D-OmniTwin/issues/29)).
- **Issues en wijzigingen worden actief opgepakt** door de beheerder; wat niet past, krijgt een reden.
- **Beveiliging:** meldingen lopen privé via [SECURITY.md](./SECURITY.md), niet via openbare issues.
- **Nieuwe functionaliteit** komt met een use case (zie [CONTRIBUTING.md](./CONTRIBUTING.md)).

## Techniek

- Versies volgens [Semantic Versioning](https://semver.org/lang/nl/), één bron `VERSION`; bij elke versie een tag, een GitHub-release en een regel in de [CHANGELOG](./CHANGELOG.md). Zie het [releasebeleid](./docs/9-beheer/releasebeleid.md).
- Een container-image per release staat nog open ([#126](https://github.com/TLaan/D-OmniTwin/issues/126)).
- Tests en controles draaien bij elke pull request ([`.github/workflows/ci.yml`](./.github/workflows/ci.yml)); `publiccode.yml` wordt daarin gevalideerd.
- Elke API heeft een eigen specificatie (NL GOV API Design Rules), zie [API-landschap](./docs/2-architectuur/api-landschap.md).

## Documentatie

- Documentatie staat bij de code, in deze repository.
- Gebruiks- en beheerdocumentatie is Nederlands. Technische documentatie wordt **tweetalig (NL/EN)**, zoals besloten in [#183](https://github.com/TLaan/D-OmniTwin/issues/183); dat wordt stap voor stap aangevuld. Nu hebben de README, SECURITY en dit document een Engelse samenvatting.
- De README zegt waar je terechtkunt met vragen en meldingen (zie ook [SUPPORT.md](./SUPPORT.md)).

## Besluitvorming

- **Code en documentatie:** in issues en pull requests, met review zoals hierboven.
- **Koers en prioriteiten:** de projectgroep van de deelnemers besluit over roadmap, use cases en pilots. Uitkomsten die de code raken, komen als issue in de repository.
- **Governance zelf:** een wijziging van dit document gaat via een pull request met akkoord van de eigenaar.

## Nog open

- Samenstelling van de projectgroep en hoe vaak die besluit.
- Wie naast Súdwest-Fryslân schrijfrechten krijgt (per organisatie een GitHub-team, zoals bij het OWC).
- D-OmniTwin wel of niet aanbieden als OWC-bouwblok, en de plek op [code.overheid.nl](https://code.overheid.nl) of in OpenCatalogi ([#124](https://github.com/TLaan/D-OmniTwin/issues/124)).
- Governance na afloop van het innovatiebudget (na augustus 2027), inclusief overdracht ([#30](https://github.com/TLaan/D-OmniTwin/issues/30)).

---

## English summary

D-OmniTwin follows the governance of the [OpenWebconcept](https://github.com/OpenWebconcept/.github) (OWC), co-founded by the Municipality of Súdwest-Fryslân. Súdwest-Fryslân is the **owner** and the **maintainer**: it reviews and merges pull requests, handles releases and security reports, and supports other parties, including competitors. Participants are listed in [PARTICIPANTS.md](./PARTICIPANTS.md); anyone can contribute via issues and pull requests ([CONTRIBUTING.md](./CONTRIBUTING.md)). Every change goes through a pull request, approved by someone other than the author, preferably from another organisation. Versions follow Semantic Versioning with a GitHub release per version. Technical documentation will be bilingual (Dutch/English). Support terms are in [SUPPORT.md](./SUPPORT.md).

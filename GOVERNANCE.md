# Projectgovernance

> **Concept — vast te stellen door de projectgroep.**
> Dit document beschrijft hoe het project nu feitelijk werkt en is een voorstel. Het is nog niet vastgesteld door de partners.

## Doel

Vastleggen wie welke rol heeft in D-OmniTwin en hoe besluiten over de code en de koers worden genomen, zodat bijdragers en andere overheden weten waar ze aan toe zijn.

## Rollen

| Partij | Rol | Wat dat inhoudt |
|--------|-----|-----------------|
| **Gemeente Súdwest-Fryslân** | Regie en maintainer | Eigenaar van de code en de repository, houdt de roadmap bij, beoordeelt en merget pull requests, beheert releases en beveiligingsmeldingen. |
| **Gemeente Leeuwarden** | Pilotgemeente | Test de toepassing in de eigen praktijk, levert use cases, feedback en wensen aan via issues. |
| **Gemeente Tytsjerksteradiel** | Pilotgemeente | Idem. |
| **Coöperatie DataFryslân** | Dataspace-partner | Inbreng en afstemming over de Fryslân Data Space (FRLDS), datadeling en iSHARE-autorisatie. |
| **Bijdragers** | Iedereen | Meldt issues, doet voorstellen en levert pull requests aan volgens [CONTRIBUTING.md](./CONTRIBUTING.md). |

Contactpersoon namens de maintainer: Taeke van der Laan (Gemeente Súdwest-Fryslân), `<e-mailadres Taeke, te bevestigen>`.

## Besluitvorming

- **Code en documentatie:** via GitHub Issues en pull requests, volgens de GitHub Flow in [CONTRIBUTING.md](./CONTRIBUTING.md): issue, branch, pull request, review, merge. Niemand merget eigen werk zonder akkoord van een ander.
- **Wie mag mergen naar `main`:** de maintainers van Súdwest-Fryslân. De bijbehorende branch protection staat nog open ([#29](https://github.com/TLaan/D-OmniTwin/issues/29)).
- **Koers en prioriteiten:** de projectgroep met de partners hierboven besluit over roadmap, use cases en pilots. Uitkomsten die de code raken worden als issue vastgelegd.
- **Beveiliging:** meldingen lopen privé via [SECURITY.md](./SECURITY.md), niet via openbare issues.
- **Gedrag:** voor alle projectkanalen geldt de [gedragscode](./CODE_OF_CONDUCT.md).

## Nog vast te stellen

- Samenstelling van de projectgroep en hoe vaak die besluit.
- Wie naast Súdwest-Fryslân maintainerrechten krijgt.
- Governance na afloop van het innovatiebudget (na augustus 2027), inclusief overdracht naar de SWF-organisatie ([#30](https://github.com/TLaan/D-OmniTwin/issues/30)).

---

## English summary

*Draft, not yet adopted by the project group.* The Municipality of Súdwest-Fryslân leads the project and maintains the code. The municipalities of Leeuwarden and Tytsjerksteradiel are pilot municipalities; the DataFryslân cooperative is the data space partner. Changes go through GitHub issues and pull requests with review (see CONTRIBUTING.md); the project group decides on roadmap and priorities.

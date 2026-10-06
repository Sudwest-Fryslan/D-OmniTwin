# 0006. Use case als declaratieve app met eigen specificatie

- Status: voorgesteld
- Datum: 2026-10-02
- Issue: https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/227; bouwt voort op ADR 0003 (https://github.com/Sudwest-Fryslan/D-OmniTwin/pull/184), ADR 0004 en ADR 0005; raakt #218, #219, #223, #225

## Context

Sinds 0.3.0 is een use case meer dan een demopakket. Hij registreert datasets via de laad-API, haalt open data op via bronadapters, hangt af van andere use cases met een versie-eis, noemt de rollen die hij nodig heeft en heeft toetsbare controles (#219). Daar komen actoren met testaccounts (#223) en bewijs met screenshots in git en een galerij (#225) bij. Use cases worden de acceptatietests van de laad-API en straks installeerbare apps, ook van andere gemeenten (#218).

De regels stonden verspreid: `usecases/README.md`, `AGENTS.md`, twee JSON-schema's in `usecases/` en de code van de uitvoerder. Het schema had geen eigen versie en liet onbekende velden toe. Wie een use case schrijft, kon niet zien wat vastligt en wat nog verandert; wie de uitvoerder wijzigt, kon ongemerkt het contract breken.

Eduard (02-10-2026): "de definitie van een use case begint bijna zo belangrijk te worden als een API-definitie." ADR 0005 zegt voor API's: specificatie eerst, met een eigen versie. Dat geldt dan ook hier.

## Besluit

1. **Een use case is een declaratieve app.** Eén map `usecases/<naam>/`, `naam` = mapnaam, eigen `versie` (SemVer, met regels voor major, minor en patch). Geen code of uitvoerbare bestanden (allowlist `.json`, `.md`, `.csv`, en afbeeldingen in `bewijs/`); alle logica in de kern: bronadapters, een vaste lijst bewerkingen zonder `eval`, de laad-API. Een nieuwe soort bron is een kernadapter via een PR met tests. `hittestress/maak_data.py` is de enige, uit te faseren uitzondering.
2. **De definitie is een geversioneerde specificatie:** de [D-OmniTwin Use Case Specificatie](../../specificaties/usecase/README.md), versie 1.0, normatief (MOET/MAG/AANBEVOLEN volgens RFC 2119). Ze beschrijft structuur, manifest, datasets, bronnen, bewerkingen, afhankelijkheden, actoren, rechten, controles, bewijs, levenscyclus, uitvoerder, beveiliging, versiebeheer en compatibiliteit.
3. **De JSON-schema's zijn de machineleesbare, normatieve bron** en staan bij de specificatie: `docs/specificaties/usecase/<MAJOR.MINOR>/` (`usecase.schema.json`, `dataset.schema.json`, `bewijs.schema.json`), met een absolute `$id` op de hoofdtak. Er is één exemplaar; de uitvoerder en de tests lezen het daar. Geen onbekende velden.
4. **Elk manifest noemt zijn specificatieversie** (`"specificatie": "1.0"`). Minor-versies zijn achterwaarts compatibel, een major niet. Een uitvoerder weigert een versie die hij niet kent.
5. **Specificatie eerst, ook voor wat nog niet gebouwd is.** Actoren (#223), bewijsstappen en het bewijsverslag (#225), externe afhankelijkheden en het commando `opruimen` zijn gedefinieerd en als *gereserveerd* gemarkeerd. Use cases mogen ze al gebruiken; de uitvoerder volgt.
6. **Levenscyclus:** `ontwerp` → `actief` → `verouderd` (met `veroudering`: datum, termijn, opvolger) → verwijderd. Het gedrag van de uitvoerder per status ligt vast.
7. **Bewijs:** het compacte bewijs (WebP, ≤ 150 KB, 2–4 schermen, alleen bij een release opnieuw) staat in git; het volledige bewijs is een zip bij de release (besluit in #225). Dit vervangt op dit punt ADR 0003 ("niet in git").

## Alternatieven

- **Alleen het schema, zonder specificatie.** Een schema zegt wat geldig is, niet wat het betekent: niet wanneer een controle slaagt, wat `ontwerp` doet bij installeren of wanneer de versie omhoog moet. Te weinig voor een contract met andere gemeenten.
- **Alleen documentatie in `usecases/README.md`.** Zoals tot nu: zonder versie en zonder normatieve status, gemengd met de index en werkinstructies. Die README blijft het overzicht en verwijst naar de specificatie.
- **Een bestaand pakketformaat** (npm `package.json`, Helm-chart, OCI-artefact, Frictionless Data Package als manifest). Die beschrijven code of data, niet de combinatie van datasets, rechten, controles en bewijs, en nodigen uit tot scripts. Voor het publiceren van use cases (#218) kan OCI of een release-asset later de verpakking zijn; het manifest blijft dit formaat.
- **Use cases met eigen code (plug-ins).** Flexibeler, maar een use case van buiten wordt dan een aanvalsvector en kan niet zonder review geïnstalleerd worden. Afgewezen; zie besluit 1.
- **Het schema in `usecases/` laten.** Dan staat het normatieve contract tussen de use cases die eraan moeten voldoen, zonder versie in het pad. Bij de specificatie, per versie, is duidelijker wat vastligt.

## Gevolgen

- **Makkelijker:**
  - wie een use case schrijft (ook buiten SWF), heeft één document met eisen en voorbeelden;
  - de uitvoerder, de catalogus (#218) en straks een UI in beheer werken tegen een vast contract;
  - tests bewaken dat schema, specificatie en use cases gelijk blijven (`tests/test_usecase_specificatie.py`).
- **Moeilijker:**
  - een nieuwe adapter, bewerking of controletype is ook een minor-versie van de specificatie, met een nieuwe schemamap zodra 1.0 is vastgesteld; verzamel zulke wijzigingen per release;
  - een nieuw veld in een manifest kan niet meer zonder de specificatie bij te werken (geen onbekende velden).
- **Werk:**
  - actoren en testaccounts, `opruimen`: #223;
  - `bewijs` in de uitvoerder, `.gitignore` voor het compacte bewijs, galerij in de root-README, unittest op grootte en aantal: #225;
  - waarschuwing bij `verouderd` en controle op `veroudering` in de uitvoerder;
  - `hittestress/maak_data.py` naar een kernadapter;
  - bij overdracht naar de SWF-organisatie de `$id`'s van de schema's meeverhuizen.

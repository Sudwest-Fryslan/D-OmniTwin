# 0003. Use cases als eenheid van functionaliteit, test en demodata

- Status: voorgesteld
- Datum: 2026-10-01
- Issue: #138, #182

## Context

Functionaliteit werd gebouwd en getest los van de vraag die ze moet beantwoorden. De demodata (één gedeelde sample) stond los van de testcases (`docs/testcases/`) en van de tests (`tests/`). Daardoor was niet aantoonbaar dat een gebruikersvraag uit de innovatieaanvraag (energiearmoede, hittestress, brede welvaart, sociale cohesie) écht werkte. Bij het naspelen bleek dat de kaart de richting omdraaide, dat de chat geen datavragen beantwoordde en dat er na een verse installatie geen embeddings waren.

## Besluit

- **Elke nieuwe functionaliteit krijgt een use case** (`usecases/<naam>/`). Een functie is af als de use case aantoonbaar werkt.
- **Een use case is zelfstandig** en bevat:
  - `usecase.json`: gebieden, de gebruikte **bronnen en indicatoren** (zie ADR 0002), de richting, de inrichting (Kompas-profiel, chatscenario) en de verwachte uitkomst;
  - `README.md`: persona, vraag, stappen, databeschrijving en resultaat;
  - `data/`: **alleen** data die niet te downloaden is (demodata `bron=DEMO`, eigen bewerkingen);
  - `tests/`: integratie- en e2e-tests van déze use case;
  - **bewijs**: screenshots en `bewijs.json` (vraag, antwoord, versie, AI-aanbieder), gemaakt met `tools/maak_usecase_bewijs.py`. Per CI-run bewaard als artefact, per release als asset bij de GitHub-release; niet in git.
- **De use cases zijn de demodata.** Een installatie laadt de use cases die je kiest (`USECASES=alle|geen|<lijst>`; `LOAD_SAMPLE_DATA` blijft als alias). Zonder use cases is er alleen het product, zonder data. "Heel Fryslân" is ook een use case (`fryslan-compleet`).
- **Out of the box:** een use case werkt na een verse installatie, ook zonder AI-sleutel. Antwoorden die een taalmodel nodig hebben, vallen dan terug op een vaste tekst uit dezelfde cijfers.
- Bugfixes hebben geen nieuwe use case nodig, maar mogen er geen breken.

## Alternatieven

- **Eén gedeelde sample met losse testcases** (de vroegere situatie). Data, inrichting en test lopen dan uit elkaar, en "werkt het?" blijft een mening.
- **Volledige, losse samples per use case** (eigen kopie van geometrie en stuurdata). Dat geeft duplicatie en drift, en ze zijn niet samen te laden. Daarom selecteren use cases uit gedeelde bronnen (ADR 0002).

## Gevolgen

- Een use case is in één map te begrijpen, te testen en te demonstreren. Ook een andere gemeente kan er een toevoegen zonder het product aan te raken.
- Wie een functie bouwt, levert ook data, tests en bewijs. Dat is meer werk per functie, maar maakt het resultaat aantoonbaar (CONTRIBUTING, AGENTS.md).
- **Uitvoering:**
  - al gedaan: use-casepakketten en de laadroute (#141), echte open data (#160, #176), de datavraag-route (#175);
  - verhuizing van de tests naar de use cases en `USECASES=`: #182, fase 5.

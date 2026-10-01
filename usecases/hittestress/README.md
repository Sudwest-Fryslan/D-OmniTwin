# TC-06-006 — Use case: Klimaatadaptatie: hittestress en kwetsbaarheid

**Bron:** innovatieaanvraag Digitale Overheid 2026, use cases; `docs/8-communicatie/usecases/data-science_use-cases.md`
**Status:** ⚠️ Nagespeeld op 2026-10-01: kaart en Kompas werken met het pakket; AI-assistent nog niet (zie Resultaat)
**Automatische test:** `tests/integration/test_usecases.py` (leest [`usecase.json`](./usecase.json))

Een use case is een **bundel**: data + inrichting + stappen. Alle drie staan hier; `usecase.json` is de machineleesbare versie.

## Persona

- **Rol:** Stedenbouwkundige / GGD
- **Besluit:** Waar eerst vergroenen en koele plekken inrichten?
- **Vraag aan de assistent:** "Ik werk aan hittestress in Bolsward. Welke buurt ligt het verst van een koele plek, en waar wonen relatief de meeste 65-plussers?"

## 1. Data

- **Dataset:** `init_data/sample`, gebiedstype CBS Buurten
- **Gebieden:** Bolsward-Noord (BU19000001), Bolsward-Zuidoost (BU19000002), Bolsward-Noordoost (BU19000004). Focus: Bolsward-Zuidoost (demodata).

| Indicator | Richting |
|---|---|
| Afstand tot koele plek | lager is beter |
| Oppervlak groen per inwoner | hoger is beter |
| 65+ jaar | neutraal |
| Ervaren gezondheid | hoger is beter |
| Verhouding oppervlakte water / verharding | hoger is beter |

**Afgeleid bij het laden** (zie `usecase.json` → `afgeleid`) en **ontbreekt nog** (#138):
- % 65+ en 75+
- Gevoelstemperatuur / hitte-eiland (Klimaateffectatlas)
- Boomkroonbedekking

## 2. Inrichting

| Onderdeel | Waarde |
|---|---|
| Kompas-profiel | Klimaat Kompas |
| Chatscenario | — (nog geen eigen scenario) |
| Polariteit | volgens de kolom *Richting* hierboven |

## 3. Stappen

| # | Actie | Verwacht | Resultaat 01-10 |
|---|---|---|---|
| 0 | Laad het pakket: `python init_data/scripts/laad_usecase.py <naam>` (db-init doet dit automatisch met de sample) | Richting en afgeleide indicatoren staan in de database | ✅ |
| 1 | Open de app, kies **Kaart Configuratie → CBS Buurten** | 13 buurten op de kaart | ✅ |
| 2 | Kies indicator **Afstand tot koele plek**, zoom in op Bolsward | Buurten gekleurd; **rood = slechter**, legenda met eenheid | ✅ Na laden van het pakket (`laad_usecase.py`) klopt de richting; zonder pakket omgekeerd (#120) |
| 3 | Klik op **Bolsward-Zuidoost** | Selectiebalk met de buurtnaam | ✅ |
| 4 | Open het **Kompas** (Klimaat Kompas) | Zonnediagram voor Bolsward-Zuidoost, dekking 100% | ✅ (Volledig Kompas) |
| 5 | Stel de vraag aan de **D-Omni Assistent** | Antwoord noemt de relevante indicatoren en buurten. Verwacht: Bolsward-Noord ligt het verst van een koele plek (246 m), Bolsward-Noordoost het dichtst bij (206 m). Relatief de meeste 65-plussers: Bolsward-Noord (26%). | ❌ Herhaalt de vraag; 'Gemeente: Bolsward' doet zichtbaar niets; geen indicatoren (#139) |
| 6 | **Rapport → Gebiedsdossier** voor Bolsward-Zuidoost | Dossier met AI-samenvatting, label "AI-gegenereerd" | ✅ (eerdere ronde, ~2 min met lokaal model) |

## Resultaat

- **Data:** de indicatoren zijn aanwezig en gevuld voor de drie Bolsward-buurten.
- **Inrichting:** het pakket zet de richting goed en voegt afgeleide percentages toe. Een eigen Kompas-profiel en chatscenario per use case ontbreken nog (#138).
- **Chat zet een verkeerde gemeente:** 'Gemeente: Bolsward' filtert op code 0080 (Leeuwarden). Dat filter blijft bewaard, en daarna blijft de kaart leeg (#140).
- **AI-assistent:** de chat herkent wat je wilt doen en biedt knoppen aan, maar **beantwoordt geen datavraag**. Na een verse installatie stelt hij geen indicatoren voor (#139).

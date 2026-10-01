# TC-06-005 — Use case: Energietransitie en energiearmoede

**Bron:** innovatieaanvraag Digitale Overheid 2026, use cases; `docs/8-communicatie/usecases/data-science_use-cases.md`
**Status:** ⚠️ Nagespeeld op 2026-10-01: kaart en Kompas werken met het pakket; AI-assistent nog niet (zie Resultaat)
**Automatische test:** `tests/integration/test_usecases.py` (leest [`usecase.json`](./usecase.json))

Een use case is een **bundel**: data + inrichting + stappen. Alle drie staan hier; `usecase.json` is de machineleesbare versie.

## Persona

- **Rol:** Beleidsmaker energietransitie
- **Besluit:** Welke buurt krijgt als eerste budget voor isolatie en energiecoaches?
- **Vraag aan de assistent:** "Waar in Bolsward is het risico op energiearmoede het grootst? Ik wil weten waar slechte energielabels samengaan met lage inkomens."

## 1. Data

- **Dataset:** `init_data/sample`, gebiedstype CBS Buurten
- **Gebieden:** Bolsward-Noord (BU19000001), Bolsward-Zuidoost (BU19000002), Bolsward-Noordoost (BU19000004). Focus: Bolsward-Zuidoost (demodata).

| Indicator | Richting |
|---|---|
| Gemiddeld energielabel | hoger is beter |
| Woningen gebouwd vóór 1945 (BAG) | neutraal |
| Huishoudens met laag inkomen | lager is beter |
| Moeite met rondkomen | lager is beter |

**Afgeleid bij het laden** (zie `usecase.json` → `afgeleid`) en **ontbreekt nog** (#138):
- % woningen met label E/F/G
- Gemiddeld gasverbruik
- Energiequote (energiearmoede TNO/CBS)

## 2. Inrichting

| Onderdeel | Waarde |
|---|---|
| Kompas-profiel | — (nog geen eigen profiel) |
| Chatscenario | — (nog geen eigen scenario) |
| Polariteit | volgens de kolom *Richting* hierboven |

## 3. Stappen

| # | Actie | Verwacht | Resultaat 01-10 |
|---|---|---|---|
| 0 | Laad het pakket: `python init_data/scripts/laad_usecase.py <naam>` (db-init doet dit automatisch bij `LOAD_SAMPLE_DATA=true`) | Richting en afgeleide indicatoren staan in de database | ✅ |
| 1 | Open de app, kies **Kaart Configuratie → CBS Buurten** | 13 buurten op de kaart | ✅ |
| 2 | Kies indicator **Gemiddeld energielabel**, zoom in op Bolsward | Buurten gekleurd; **rood = slechter**, legenda met eenheid | ✅ Richting klopt: gecorrigeerd in de definities (#120) |
| 3 | Klik op **Bolsward-Zuidoost** | Selectiebalk met de buurtnaam | ✅ |
| 4 | Open het **Kompas** (— (nog geen eigen profiel)) | Zonnediagram voor Bolsward-Zuidoost, dekking 100% | ✅ (Volledig Kompas) |
| 5 | Stel de vraag aan de **D-Omni Assistent** | Antwoord noemt de relevante indicatoren en buurten. Verwacht: Bolsward-Noord: hoogste moeite met rondkomen (19,1%) en meeste lage inkomens (4,4%) | ❌ Herhaalt de vraag; acties 'Gemeente: Bolsward' (Bolsward is geen gemeente), 'Toon: Buurten', 'Rapport'; geen indicatoren (#139) |
| 6 | **Rapport → Gebiedsdossier** voor Bolsward-Zuidoost | Dossier met AI-samenvatting, label "AI-gegenereerd" | ✅ (eerdere ronde, ~2 min met lokaal model) |

## Resultaat

- **Data:** de indicatoren zijn aanwezig en gevuld voor de drie Bolsward-buurten.
- **Inrichting:** het pakket zet de richting goed en voegt afgeleide percentages toe. Een eigen Kompas-profiel en chatscenario per use case ontbreken nog (#138).
- **Chat zet een verkeerde gemeente:** 'Gemeente: Bolsward' filtert op code 0080 (Leeuwarden). Dat filter blijft bewaard, en daarna blijft de kaart leeg (#140).
- **AI-assistent:** de chat herkent wat je wilt doen en biedt knoppen aan, maar **beantwoordt geen datavraag**. Na een verse installatie stelt hij geen indicatoren voor (#139).

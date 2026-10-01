# TC-06-007 — Use case: Brede welvaart en functiemenging

**Bron:** innovatieaanvraag Digitale Overheid 2026, use cases; `docs/8-communicatie/usecases/data-science_use-cases.md`
**Status:** ⚠️ Nagespeeld op 2026-10-01: kaart en Kompas werken met het pakket; AI-assistent nog niet (zie Resultaat)
**Automatische test:** `tests/integration/test_usecases.py` (leest [`usecase.json`](./usecase.json))

Een use case is een **bundel**: data + inrichting + stappen. Alle drie staan hier; `usecase.json` is de machineleesbare versie.

## Persona

- **Rol:** Strateeg / economische zaken
- **Besluit:** Waar is extra inzet nodig op werk, inkomen en voorzieningen?
- **Vraag aan de assistent:** "Hoe staat het met de brede welvaart in Bolsward-Zuidoost vergeleken met de rest van Bolsward?"

## 1. Data

- **Dataset:** `init_data/sample`, gebiedstype CBS Buurten
- **Gebieden:** Bolsward-Noord (BU19000001), Bolsward-Zuidoost (BU19000002), Bolsward-Noordoost (BU19000004). Focus: Bolsward-Zuidoost (demodata).

| Indicator | Richting |
|---|---|
| Inkomen per inwoner | hoger is beter |
| Netto arbeidsparticipatie | hoger is beter |
| Diversiteit Functies (Simpson Index) | hoger is beter |
| Ervaren gezondheid | hoger is beter |

**Afgeleid bij het laden** (zie `usecase.json` → `afgeleid`) en **ontbreekt nog** (#138):
- Woontevredenheid / Leefbaarometer
- Veiligheidsbeleving
- Trend over meerdere jaargangen
- Opleidingsniveau in %

## 2. Inrichting

| Onderdeel | Waarde |
|---|---|
| Kompas-profiel | Volledig Kompas |
| Chatscenario | beleidsadviseur |
| Polariteit | volgens de kolom *Richting* hierboven |

## 3. Stappen

| # | Actie | Verwacht | Resultaat 01-10 |
|---|---|---|---|
| 0 | Laad het pakket: `python init_data/scripts/laad_usecase.py <naam>` (db-init doet dit automatisch met de sample) | Richting en afgeleide indicatoren staan in de database | ✅ |
| 1 | Open de app, kies **Kaart Configuratie → CBS Buurten** | 13 buurten op de kaart | ✅ |
| 2 | Kies indicator **Inkomen per inwoner**, zoom in op Bolsward | Buurten gekleurd; **rood = slechter**, legenda met eenheid | ✅ Richting klopt (alle indicatoren hoger = beter) |
| 3 | Klik op **Bolsward-Zuidoost** | Selectiebalk met de buurtnaam | ✅ |
| 4 | Open het **Kompas** (Volledig Kompas) | Zonnediagram voor Bolsward-Zuidoost, dekking 100% | ✅ (Volledig Kompas) |
| 5 | Stel de vraag aan de **D-Omni Assistent** | Antwoord noemt de relevante indicatoren en buurten. Verwacht: Bolsward-Zuidoost zit tussen Noord en Noordoost in (demodata = gemiddelde van de buren). | ⚠️ Herhaalt de vraag; stelt 'Toon: Welstandsgebieden' voor (niet relevant); scenario Beleidsadviseur wordt niet herkend zonder het woord 'beleidsadviseur' |
| 6 | **Rapport → Gebiedsdossier** voor Bolsward-Zuidoost | Dossier met AI-samenvatting, label "AI-gegenereerd" | ✅ (eerdere ronde, ~2 min met lokaal model) |

## Resultaat

- **Data:** de indicatoren zijn aanwezig en gevuld voor de drie Bolsward-buurten.
- **Inrichting:** het pakket zet de richting goed en voegt afgeleide percentages toe. Een eigen Kompas-profiel en chatscenario per use case ontbreken nog (#138).
- **Chat zet een verkeerde gemeente:** 'Gemeente: Bolsward' filtert op code 0080 (Leeuwarden). Dat filter blijft bewaard, en daarna blijft de kaart leeg (#140).
- **AI-assistent:** de chat herkent wat je wilt doen en biedt knoppen aan, maar **beantwoordt geen datavraag**. Na een verse installatie stelt hij geen indicatoren voor (#139).

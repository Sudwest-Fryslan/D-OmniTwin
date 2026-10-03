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

- **Data:** via de laad-API uit de datasets van de afhankelijkheden (`cbs-gebiedsindelingen`, `cbs-kerncijfers`, `rivm-gezondheidsmonitor`, `sample-bronbibliotheek`), gebiedstype CBS Buurten. Open data wordt bij de installatie gedownload; wat nog niet open is of nog geen adapter heeft, komt uit `sample-bronbibliotheek` en is gemarkeerd (`DEMODATA` in de bron van de waarde). Zie [demodata naar open data](../../docs/3-data-engineering/demodata-naar-open-data.md).
- **Gebieden:** Bolsward-Noord (BU19000001), Bolsward-Zuidoost (BU19000002), Bolsward-Noordoost (BU19000004). Focus: Bolsward-Zuidoost.

| Indicator | Richting | Bron |
|---|---|---|
| Inkomen per inwoner | hoger is beter | CBS Kerncijfers (`cbs-kerncijfers`) |
| Netto arbeidsparticipatie | hoger is beter | CBS Kerncijfers (`cbs-kerncijfers`) |
| Diversiteit Functies (Simpson Index) | hoger is beter | Kadaster BAG, per buurt berekend (sample; adapter volgt; Bolsward-Zuidoost DEMODATA) |
| Ervaren gezondheid | hoger is beter | RIVM Gezondheidsmonitor (`rivm-gezondheidsmonitor`) |

**Ontbreekt nog** (#138):
- Woontevredenheid / Leefbaarometer
- Veiligheidsbeleving
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
| 0 | Installeer: `python -m omnitwin.usecases installeer brede-welvaart` (db-init doet dit automatisch bij `LOAD_SAMPLE_DATA=true`, met de laadstraat in-process) | De datasets van de afhankelijkheden zijn gepubliceerd; daarna zet `laad_usecase.py --inrichting` de richting | ✅ (verse stack, 02-10) |
| 1 | Open de app, kies **Kaart Configuratie → CBS Buurten** | 13 buurten op de kaart | ✅ |
| 2 | Kies indicator **Inkomen per inwoner**, zoom in op Bolsward | Buurten gekleurd; **rood = slechter**, legenda met eenheid | ✅ Richting klopt (alle indicatoren hoger = beter) |
| 3 | Klik op **Bolsward-Zuidoost** | Selectiebalk met de buurtnaam | ✅ |
| 4 | Open het **Kompas** (Volledig Kompas) | Zonnediagram voor Bolsward-Zuidoost, dekking 100% | ✅ (Volledig Kompas) |
| 5 | Stel de vraag aan de **D-Omni Assistent** | Antwoord noemt de relevante indicatoren en buurten. Verwacht: Inkomen per inwoner: Bolsward-Zuidoost 26,9 duizend euro (CBS 2023), tussen Noord (22,1; 2023) en Noordoost (30,9; 2024). Netto arbeidsparticipatie 2024: Noord 66%, Zuidoost 71%, Noordoost 73%. Goed ervaren gezondheid 2024 (RIVM): Noord 65,9%, Zuidoost 72,7%, Noordoost 77,6%. | ⚠️ Herhaalt de vraag; stelt 'Toon: Welstandsgebieden' voor (niet relevant); scenario Beleidsadviseur wordt niet herkend zonder het woord 'beleidsadviseur' |
| 6 | **Rapport → Gebiedsdossier** voor Bolsward-Zuidoost | Dossier met AI-samenvatting, label "AI-gegenereerd" | ✅ (eerdere ronde, ~2 min met lokaal model) |

## Resultaat

- **Data:** de indicatoren zijn aanwezig en gevuld voor de drie Bolsward-buurten.
- **Inrichting:** het pakket zet de richting goed en voegt afgeleide percentages toe. Een eigen Kompas-profiel en chatscenario per use case ontbreken nog (#138).

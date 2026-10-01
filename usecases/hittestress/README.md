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

| Indicator | Richting | Bron |
|---|---|---|
| Afstand tot koele plek | lager is beter | sample (bronbibliotheek) |
| Oppervlak groen per inwoner | hoger is beter | sample |
| 65+ jaar | neutraal | sample (aantal) |
| Ervaren gezondheid | hoger is beter | sample |
| Verhouding oppervlakte water / verharding | hoger is beter | sample |
| 65+ jaar (%) | neutraal | CBS 2026, `data/waarden.csv` |
| 80 jaar of ouder (%) | neutraal | CBS 2026, `data/waarden.csv` |
| Boomkroonbedekking | hoger is beter | RIVM 2022, `data/waarden.csv` |
| Stedelijk hitte-eiland effect | lager is beter | RIVM 2022, `data/waarden.csv` |

### Extra brondata (`data/waarden.csv`)

Echte open data, opgehaald met [`maak_data.py`](./maak_data.py). Reproduceerbaar: `python usecases/hittestress/maak_data.py` (vereist numpy, Pillow, shapely, pyproj). De CSV staat in git, dus laden werkt offline.

| Indicator | Eenheid | Bron | Jaar | Licentie | Methode |
|---|---|---|---|---|---|
| 65+ jaar (%) | % | CBS Kerncijfers wijken en buurten 2026, tabel [86358NED](https://opendata.cbs.nl/ODataApi/odata/86358NED) | 2026 (1 januari) | CC BY 4.0 | (65-80 jaar + 80+) ÷ inwoners |
| 80 jaar of ouder (%) | % | idem | 2026 | CC BY 4.0 | 80+ ÷ inwoners |
| Boomkroonbedekking | % | RIVM Atlas Natuurlijk Kapitaal, Bomenkaart 2022 (10 m, bomen > 2,5 m); WCS `ank__rivm_20231221_bomenkaart_2022` op `https://data.rivm.nl/geo/ank/wcs` | 2022 | Public Domain Mark 1.0 | gemiddelde over de 10m-cellen in de buurt; cel zonder bomen = 0% |
| Stedelijk hitte-eiland effect | °C | RIVM Atlas Natuurlijk Kapitaal, Stedelijk hitte-eiland effect v2; WCS `ank__Stedelijk_hitte_eiland_effect_01062022_v2` | 2022 | Public Domain Mark 1.0 | gemiddelde over de 10m-cellen in de buurt |

De buurtgrenzen komen uit `init_data/sample/2_brondata/sample_buurten.geojson`, omgezet naar RD New. De uuid per indicator is `uuid5` op de naam (namespace van `laad_usecase.py`). `65+ jaar (%)` was eerder afgeleid uit de sample (65+ 2025 ÷ inwoners 2023, voor Bolsward-Zuidoost uit demodata); nu komt hij rechtstreeks van het CBS.

| Buurt | 65+ (%) | 80+ (%) | Boomkroon (%) | Hitte-eiland (°C) |
|---|---|---|---|---|
| Bolsward-Noord (BU19000001) | 24,1 | 9,5 | 7,6 | 0,47 |
| Bolsward-Zuidoost (BU19000002) | 29,5 | 10,2 | 13,1 | 0,41 |
| Bolsward-Noordoost (BU19000004) | 24,2 | 6,2 | 6,8 | 0,37 |

Deze vier indicatoren zijn ook voor Bolsward-Zuidoost **echt**. De overige indicatoren van Bolsward-Zuidoost in de sample zijn nog demodata.

**Ontbreekt nog** (#138):
- **% 75+:** CBS publiceert per buurt alleen 65-80 en 80+ (Kerncijfers 2026). 80+ is opgenomen; dat is ook de groep die het kwetsbaarst is bij hitte.
- **Gevoelstemperatuur (Klimaateffectatlas):** voor Fryslân niet als open download of WCS beschikbaar (op data.overheid.nl alleen van Zuid-Holland, Overijssel en Zeeland). Vervangen door het stedelijk hitte-eiland effect van het RIVM.

## 2. Inrichting

| Onderdeel | Waarde |
|---|---|
| Kompas-profiel | Klimaat Kompas |
| Chatscenario | — (nog geen eigen scenario) |
| Polariteit | volgens de kolom *Richting* hierboven |

## 3. Stappen

| # | Actie | Verwacht | Resultaat 01-10 |
|---|---|---|---|
| 0 | Laad het pakket: `python init_data/scripts/laad_usecase.py hittestress` (db-init doet dit automatisch bij `LOAD_SAMPLE_DATA=true`) | Richting en de vier indicatoren uit `data/waarden.csv` staan in de database | ✅ (verse stack, 01-10) |
| 1 | Open de app, kies **Kaart Configuratie → CBS Buurten** | 13 buurten op de kaart | ✅ |
| 2 | Kies indicator **Afstand tot koele plek**, zoom in op Bolsward | Buurten gekleurd; **rood = slechter**, legenda met eenheid | ✅ Richting klopt: gecorrigeerd in de definities (#120) |
| 2b | Kies indicator **Stedelijk hitte-eiland effect** | 3 buurten met data; legenda 0,37 – 0,47 °C, groen = laag | ⚠️ Legenda klopt, maar de drie buurten krijgen dezelfde kleur: bij minder waarden dan kleurklassen (3 < 7) maakt `color_scale_service` geen klassen |
| 3 | Klik op **Bolsward-Zuidoost** | Selectiebalk met de buurtnaam | ✅ |
| 4 | Open het **Kompas** (Klimaat Kompas) | Zonnediagram voor Bolsward-Zuidoost, dekking 100% | ✅ (Volledig Kompas) |
| 5 | Stel de vraag aan de **D-Omni Assistent** | Antwoord noemt de relevante indicatoren en buurten. Verwacht: Bolsward-Noord ligt het verst van een koele plek (246 m) en heeft het sterkste hitte-eiland effect (0,47 °C). Bolsward-Noordoost ligt het dichtst bij een koele plek (206 m), maar heeft de minste boomkroon (6,8%). Relatief de meeste 65- en 80-plussers: Bolsward-Zuidoost (29,5% en 10,2%, CBS 2026). | ❌ Herhaalt de vraag; 'Gemeente: Bolsward' doet zichtbaar niets; geen indicatoren (#139) |
| 6 | **Rapport → Gebiedsdossier** voor Bolsward-Zuidoost | Dossier met AI-samenvatting, label "AI-gegenereerd" | ✅ (eerdere ronde, ~2 min met lokaal model) |

## Resultaat

- **Data:** de indicatoren zijn aanwezig en gevuld voor de drie Bolsward-buurten. Vier ervan komen uit echte open data (CBS 2026, RIVM 2022), ook voor Bolsward-Zuidoost.
- **Uitkomst met echte data:** relatief de meeste 65- en 80-plussers wonen in Bolsward-Zuidoost (29,5% en 10,2%). Die buurt heeft ook de meeste boomkroon (13,1%). Bolsward-Noord heeft het sterkste hitte-eiland effect (0,47 °C) en ligt het verst van een koele plek.
- **Kaartkleur:** een indicator met waarden voor maar 3 buurten krijgt één kleur, omdat er minder waarden dan kleurklassen zijn. De legenda klopt wel.
- **Inrichting:** het pakket zet de richting goed en voegt afgeleide percentages toe. Een eigen Kompas-profiel en chatscenario per use case ontbreken nog (#138).
- **Chat zet een verkeerde gemeente:** 'Gemeente: Bolsward' filtert op code 0080 (Leeuwarden). Dat filter blijft bewaard, en daarna blijft de kaart leeg (#140).
- **AI-assistent:** de chat herkent wat je wilt doen en biedt knoppen aan, maar **beantwoordt geen datavraag**. Na een verse installatie stelt hij geen indicatoren voor (#139).

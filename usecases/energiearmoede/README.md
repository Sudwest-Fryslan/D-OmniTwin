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

- **Data:** via de laad-API uit de datasets van de afhankelijkheden (`cbs-gebiedsindelingen`, `cbs-kerncijfers`, `rivm-gezondheidsmonitor`, `sample-bronbibliotheek`), gebiedstype CBS Buurten. Open data wordt bij de installatie gedownload; wat nog niet open is of nog geen adapter heeft, komt uit `sample-bronbibliotheek` en is gemarkeerd (`DEMODATA` in de bron van de waarde). Zie [demodata naar open data](../../docs/3-data-engineering/demodata-naar-open-data.md).
- **Gebieden:** Bolsward-Noord (BU19000001), Bolsward-Zuidoost (BU19000002), Bolsward-Noordoost (BU19000004). Focus: Bolsward-Zuidoost.

| Indicator | Richting | Bron |
|---|---|---|
| Gemiddeld energielabel | lager is beter | RVO EP-Online, per buurt berekend (sample; adapter volgt; Bolsward-Zuidoost DEMODATA) |
| Woningen gebouwd vóór 1945 (BAG) | neutraal | Kadaster BAG, per buurt berekend (sample; adapter volgt; Bolsward-Zuidoost DEMODATA) |
| Huishoudens met laag inkomen | lager is beter | CBS Kerncijfers (`cbs-kerncijfers`, tot 2023) |
| Moeite met rondkomen | lager is beter | RIVM Gezondheidsmonitor 2012-2024 (`rivm-gezondheidsmonitor`) |

**Ontbreekt nog** (#138):
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
| 0 | Installeer: `python -m omnitwin.usecases installeer energiearmoede` (db-init doet dit automatisch bij `LOAD_SAMPLE_DATA=true`, met de laadstraat in-process) | De datasets van de afhankelijkheden zijn gepubliceerd; daarna zet `laad_usecase.py --inrichting` de richting | ✅ (verse stack, 02-10) |
| 1 | Open de app, kies **Kaart Configuratie → CBS Buurten** | 13 buurten op de kaart | ✅ |
| 2 | Kies indicator **Gemiddeld energielabel**, zoom in op Bolsward | Buurten gekleurd; **rood = slechter**, legenda met eenheid | ✅ Richting klopt: gecorrigeerd in de definities (#120) |
| 3 | Klik op **Bolsward-Zuidoost** | Selectiebalk met de buurtnaam | ✅ |
| 4 | Open het **Kompas** (— (nog geen eigen profiel)) | Zonnediagram voor Bolsward-Zuidoost, dekking 100% | ✅ (Volledig Kompas) |
| 5 | Stel de vraag aan de **D-Omni Assistent** | Antwoord noemt de relevante indicatoren en buurten. Verwacht: Bolsward-Noord: hoogste moeite met rondkomen (19,1%, RIVM 2024) en meeste lage inkomens (4,4%, CBS 2023); Bolsward-Zuidoost 12,9% en 3,1% | ❌ Herhaalt de vraag; acties 'Gemeente: Bolsward' (Bolsward is geen gemeente), 'Toon: Buurten', 'Rapport'; geen indicatoren (#139) |
| 6 | **Rapport → Gebiedsdossier** voor Bolsward-Zuidoost | Dossier met AI-samenvatting, label "AI-gegenereerd" | ✅ (eerdere ronde, ~2 min met lokaal model) |

## Resultaat

- **Data:** de indicatoren zijn aanwezig en gevuld voor de drie Bolsward-buurten.
- **Inrichting:** het pakket zet de richting goed en voegt afgeleide percentages toe. Een eigen Kompas-profiel en chatscenario per use case ontbreken nog (#138).

## Bewijs

<!-- bewijs:start -->
*Gemaakt op 11-10-2026 met D-OmniTwin 0.5.0 (use case 0.2.0); geslaagd. Verslag: [`bewijs/bewijs.json`](bewijs/bewijs.json). Opnieuw maken (bij een release): `python -m omnitwin.usecases bewijs energiearmoede`.*

![Huishoudens met een laag inkomen in Bolsward (CBS)](bewijs/kaart.webp)
*Huishoudens met een laag inkomen in Bolsward (CBS)*

![Datavraag: waar is het risico op energiearmoede het grootst?](bewijs/chat.webp)
*Datavraag: waar is het risico op energiearmoede het grootst?*

![Kompas voor Bolsward-Zuidoost](bewijs/kompas.webp)
*Kompas voor Bolsward-Zuidoost*
<!-- bewijs:end -->

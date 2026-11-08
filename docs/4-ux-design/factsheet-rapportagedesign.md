# Factsheet- & Rapportagedesign (WBM / Thematische Buurtbarometer)

> **Gekoppeld issue:** [#441](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/441) · **Afgesplitste vervolg-issues:** [#491](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/491) (eenheden & Kompas-koppelingen), [#492](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/492) (fixes bestaande deelgebiedrapportage)  
> **Kader/Epic:** [Epic #309](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/309) ([Integrale gebruikerservaring-audit](./gebruikerservaring-audit.md), §2.5)  
> **Branch:** `feature/441-factsheet-rapportage-design`  
> **Status:** Vastgesteld ontwerp & implementatieplan (bijgewerkt na kritische code- & data-review)  
> **Auteur / Besluit:** T. van der Laan (Product Owner) & AI Pair Programmer  
> **Referentiebronnen:** Kompas-hiërarchie (`v_kompas_hierarchie` + `indicatoren.polariteit`), [Percentielklasse-methodiek](../3-data-engineering/percentielklasse_methodiek.md) (`src/omnitwin/services/percentielklasse.py`), `db/migraties/V044__kleine_aantallen.sql`, Wijk- en Buurtmonitor (WBM Enschede / Kennispunt Twente), [ADR 0007 Mesh & Portabiliteit](../2-architectuur/adr/0007-geen-multi-tenancy-mesh-van-instanties.md), [ADR 0010 Toegang per laag](../2-architectuur/adr/0010-toegang-per-laag-en-bron.md), [ADR 0011 Toegankelijkheid](../2-architectuur/adr/0011-toegankelijkheid-wcag.md).

---

## 1. Positie, Probleemstelling & Afbakening

### 1.1 Positie naast bestaande rapporten
De **Gebiedsfactsheet** wordt toegevoegd als een **nieuw, zelfstandig rapporttype** op `/rapport/factsheet?gebieden=...` (`FactsheetPage.tsx`), **naast** de bestaande rapportvormen (`Gebiedsdossier` op `/rapport/:gebied_id`, `Deelgebiedsanalyse`, `Multi-Gebiedsdossier`, `Thema-Analyse` en `Benchmark`). Bestaande rapporten blijven ongewijzigd.

Vanuit de kaartviewer (`static/js/app.js`) verschijnt **📋 Gebiedsfactsheet** als **eerste optie bovenaan** in dezelfde rapportkeuze-modal als de overige rapporten — zowel bij een enkel geselecteerd gebied (`openRapportTypeModal`) als bij een meervoudige selectie (`openMultiSelectRapportModal`).

### 1.2 Enkelvoudige buurt én meervoudige buurtselectie (binnen 1 gemeente)
Een factsheet werkt voor zowel **1 buurt** (bijv. Workum) als **meerdere geselecteerde buurten binnen dezelfde gemeente** (bijv. 6 buurten of 42 buurten in het IJsselmeergebied):
- **Afbakening:** Alleen gebiedstype **buurt** (`CBS_BUURT`) binnen **één gemeente** wordt ondersteund. Bij een ander gebiedstype of een selectie over gemeentegrenzen heen geeft de backend een duidelijke `GebruikersFout` (`400`).

| Onderdeel | 1 geselecteerde buurt | Meerdere geselecteerde buurten ($k \ge 2$, zelfde gemeente) |
|---|---|---|
| **Hero-titel & contourkaart** | Buurtnaam, code, gemeente + React `<svg>`-contour van de buurt binnen de beschikbare buurten van de gemeente | Samengestelde naam (optionele `naam` of `{k} buurten`) + React `<svg>`-contour met alle geselecteerde vlakken gemarkeerd (en melding als van enkele buurten geometrie ontbreekt) |
| **Hero kern-KPI's (met peiljaar)** | Waarde + eigen peiljaar van de buurt (inwoners, huishoudens, woningen, BAG-bouwperiodes in %) | **Som** over de geselecteerde buurten (met peiljaar); BAG-percentages berekend uit de gesommeerde bouwjaarklassen |
| **Thema- & Onderdeelscores (Kompas + Percentielklassen)** | Geaggregeerde **percentielklasse 1–8** (en exacte score op schaal `1,0–8,0` t.o.v. midden `4,5`) voor deze buurt t.o.v. referentie (`gemeente` of `fryslan`) | Geaggregeerde **percentielklasse 1–8** over alle `(buurt × indicator)`-paren in de selectie conform `percentielklasse.py` (krimpt niet kunstmatig naar het midden) |
| **Thematische rangpositie** | **Wel getoond** bij normatieve thema's en `referentie = gemeente`: `#14 van {n_met_score}` | **Niet getoond**: een meervoudige selectie vormt een samengesteld gebied zonder individuele plek op de enkelvoudige buurtenranglijst |
| **Waarden in detailtabel** | Waarde van de buurt vs. `⌀ Buurtgemiddelde gemeente` (met peiljaar) | **Inwonersgewogen gemiddelde** voor relatieve indicatoren en **som** (+ gemiddelde per buurt) voor aantal-indicatoren vs. `⌀ Buurtgemiddelde gemeente` |

### 1.3 Wat we bewust NIET doen (Methodische & Scope-afbakening)
- ❌ **Geen vage 'totaalscore' of totaalrangorde per buurt** (zoals *"Rang 5 van 177"*): ongelijksoortige domeinen (bijv. criminaliteit en groen) zijn niet optelbaar tot één rapportcijfer.
- ❌ **Geen vijfde losstaande Z-score-aggregatie:** we bouwen op de bestaande Kompas-boom en `percentielklasse.py` (klasse 1–8), zodat kaart, Kompas en factsheet één methodiek en kleurschaal delen.
- ❌ **Geen gemeentebrede gestapelde buurt-totaalbalken** en **geen 4-kwadranten Trend- & Urgentiematrix (scatterplot)**.
- ❌ **Geen AI/LLM-narratief:** 100% deterministisch, reproduceerbaar en direct beschikbaar zonder taalmodel.

---

## 2. Methodiek: Kompas-boom & Percentielklassen (1–8)

### 2.1 Aansluiting op de 4 ringen van het Kompas (`KompasService` + `percentielklasse.py`)
De factsheet gebruikt het standaard Kompas-profiel (`KompasService.get_standaard_config_id()`, of een expliciet meegegeven `config_id`), filtert inactieve (`is_actief = FALSE`) en vervangen (`vervangen_door_id IS NOT NULL`) indicatoren weg en ontdubbelt per thema op `indicator_uuid`:

1. **Ring 1 — 4 Kwadranten:**
   - Normatief (3 kwadranten): *Kwaliteit fysieke leefomgeving*, *Kwaliteit sociale leefomgeving*, *Kwaliteit van leven* (kleurenpalet `colorblind-safe`: klasse 1 rood → klasse 8 blauw).
   - Beschrijvend / neutraal (1 kwadrant): *Samenstelling* (*Bebouwing* & *Bevolking*, kleurenpalet `sequential-blue`).
2. **Ring 2 — 12 Thema's:** Horizontale benchmarkbalken op schaal `1..8` rond de middenlijn (`4,5` / 50e percentiel).
3. **Ring 3 — 33 Onderdelen (subthema's):** Bron voor de **Top 3 Sterke kanten & Top 3 Aandachtspunten** (alleen de 25 normatieve onderdelen uit Kwadrant 1–3) én groeperingsniveau in de uitklapbare detailtabel.
4. **Ring 4 — Indicatoren:** Individuele meetwaarden met **peiljaar**, eenheid, buurtgemiddelde van de referentiegroep, percentielklasse (1–8), status (`ok`, `onderdrukt`, `geen_data`, `geen_referentie`) en meerjarige tijdreeks (sparkline + trendpijl).

### 2.2 Polariteit-audit (#441) & Kwadrant *Samenstelling* (Neutraal)
- **Polariteit-audit binnen #441 (`V048__polariteit_kompas_audit.sql`):**
  - Bij het inladen van de SWF-monitorexport (`omkeren = false`) zijn diverse klacht-, overlast-, gezondheids- en armoede-indicatoren in de database op `hoger_is_beter` komen te staan (zoals `Roken`, `Obesitas`, `Overgewicht`, `Overmatig drinken`, `Alcohol`, `Beperking`, `Beperkte functionaliteit`, `dronken personen`, `wonen` onder Veiligheid, `Gevoelstemperatuur`, `Gemiddeld energielabel`, `Huishoudens met laag inkomen`, `Participatiewet totaal`). Deze worden in een idempotente migratie en in de stuurdata rechtgezet naar `lager_is_beter`, en beschrijvende indicatoren onder *Samenstelling* naar `neutraal`.
- **Richting in percentielklassen (`percentielklasse.py`):**
  - `hoger_is_beter`: middenrang-percentiel $p \in [0, 1]$; **klasse 8 = hoogste/gunstigste 12,5%**, **klasse 1 = laagste/ongunstigste 12,5%**.
  - `lager_is_beter`: omgekeerd percentiel $1 - p$; **klasse 8 = laagste ruwe waarde = gunstigste 12,5%**.
  - `neutraal` / Kwadrant 4 (*Samenstelling*): ongericht percentiel $p$ met opeenvolgend blauw palet (`sequential-blue`), label *"klasse K (neutraal)"*, **zonder** goed/slecht-duiding, **zonder** gemeentelijke rangpositie en **uitgesloten** van *Top 3 Sterke kanten & Aandachtspunten*.

### 2.3 Uitsluiting van ruwe aantallen (`aantal`) uit normatieve weging
- Ruwe tel-indicatoren (`LOWER(TRIM(i.eenheid)) = 'aantal'` en bekende tel-indicatoren zoals `werkzamen` en `zzp'ers`, zie ook het vervolg-issue voor eenhedennormalisatie) zijn afhankelijk van de omvang van een buurt.
- **Regel:**
  1. Aantal-indicatoren tellen **niet** mee in de geaggregeerde klasse/score van Onderdelen (Ring 3) en Thema's (Ring 2) en komen **niet** in *Top 3 Sterke kanten / Aandachtspunten*.
  2. Ze zijn **wél volledig zichtbaar** in de uitklapbare detailtabel (`ThemaDrilldown`) onder hun eigen onderdeel, gemarkeerd als `context (aantal)` met hun feitelijke waarde, referentiegemiddelde en trendlijn.

### 2.4 Aggregatie, Minimumdekking voor Themarangorde & Top 3 Onderdelen
- **Aggregatie (`percentielklasse.aggregeer`):**
  - Elk normatief onderdeel (Ring 3) en thema (Ring 2) aggregeert de percentielklassen $k_i \in \{1..8\}$ van zijn onderliggende relatieve, niet-onderdrukte indicatoren met gewicht $g_i = n_{\text{ref}, i} \times w_i$:
    $$\bar{k} = \frac{\sum (k_i \times g_i)}{\sum g_i}, \quad K = \text{rond\_klasse}(\bar{k}) = \lfloor \bar{k} + 0{,}5 \rfloor$$
- **Themarangorde bij 1 buurt (`referentie == 'gemeente'` & normatief kwadrant):**
  - Berekend over alle landbuurten in dezelfde gemeente via één bulk-opvraag op `zscore_referentie_waarden` (`V044`).
  - **Minimumdekkingsregel:** Een buurt telt alleen mee in de ranglijst van een thema als zij een geldige (niet-onderdrukte) waarde heeft voor ten minste **50% van de beschikbare thema-indicatoren** in die gemeente (met ondergrens van minimaal 1 indicator). De rang wordt gesorteerd op de onafgeronde themascore $\bar{k}$ (bij gelijke score: standaard competitierang `1, 2, 2, 4`), met dynamische noemer `#14 van {n_buurten_met_voldoende_dekking}`.
- **Top 3 Sterke kanten & Top 3 Aandachtspunten (op Onderdeel-niveau / Ring 3):**
  - Geselecteerd uit de normatieve onderdelen (Ring 3, Kwadrant 1–3) op basis van hun geaggregeerde score $\bar{k}$ en klasse $K$:
    - **Top 3 Sterke kanten:** onderdelen met $K \ge 6$ ($\bar{k} \ge 5{,}5$), aflopend gesorteerd op $\bar{k}$ (max. 3), voorzien van themanaam en de sterkst bijdragende indicator als voorbeeld.
    - **Top 3 Aandachtspunten:** onderdelen met $K \le 3$ ($\bar{k} < 3{,}5$), oplopend gesorteerd vanaf laagste $\bar{k}$ (max. 3), voorzien van themanaam en de meest urgente indicator als voorbeeld.

### 2.5 Vier expliciete statussen, Waterbuurten (#155), RLS (#254) & Veilige Contourkaart
- **Vier indicatorstatussen in de detailtabel:**
  1. `ok`: waarde én referentie beschikbaar (toont klasse 1–8).
  2. `onderdrukt`: doelwaarde heeft `n < kleine_aantallen_drempel()` (bepaald via `percentielklasse.onderdrukte_waarden()`, want `zscore_referentie_waarden` laat onderdrukte rijen weg); toont *"Afgeschermd (kleine aantallen)"*.
  3. `geen_data`: geen meting voor het geselecteerde gebied.
  4. `geen_referentie`: gebied heeft wel een waarde, maar de referentiegroep heeft $< 2$ buurten met data.
- **Waterbuurten (`is_waterbuurt`):** Als een enkele waterbuurt wordt geopend, geeft de factsheet `is_waterbuurt: true` terug met de contourkaart en een heldere melding dat waterbuurten buiten de bewoningsbenchmark vallen. In een meervoudige selectie worden waterbuurten uitgefilterd en vermeld onder `waterbuurten_uitgesloten`.
- **Veilige Contourkaart (geen `dangerouslySetInnerHTML`):**
  - Omdat gemeenten in `gebieden` geen eigen geometrie hebben en 22 van de 179 buurten in SWF `geom IS NULL` hebben, bouwt de backend de kaart op uit de beschikbare buurtgeometrieën van de gemeente (`ST_SimplifyPreserveTopology` in RD `EPSG:28992` vóór projectie naar `viewBox 0 0 400 320`).
  - De backend levert gestructureerde pad-objecten (`achtergrond_paden`, `geselecteerde_paden`, `ontbrekende_geometrie_buurten`); React rendert zelf `<svg>` en `<path fillRule="evenodd">` met CSS-thematokens.

---

## 3. Visuele Layout & Componentenstructuur (Volgorde ontwerp 27 oktober)

De factsheet draait binnen `<ReportLayout>` (`admin-panel/src/App.tsx`, die al de vaste rapportkop met `← Terug naar kaart`, beeldmerk, `Afwijking melden` en `Afdrukken` rendert). De volgorde op de pagina volgt exact het vastgestelde ontwerp:

```
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│ [Bestaande ReportLayout Header: ← Terug naar kaart · Beeldmerk · Afwijking melden · Print] │
├────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. FACTSHEET HERO (FactsheetHero.tsx)                                                      │
│ ┌───────────────────────────────────────────────────────────┬────────────────────────────┐ │
│ │ Gebiedsfactsheet · Referentie: [Gemeente ▾ | Fryslân]     │                            │ │
│ │ Workum (BU19000200)                                       │   [React <svg> Contourkaart│ │
│ │ Gemeente Súdwest-Fryslân · ⌀ Buurtgemiddelde gemeente     │    selectie in gemeente,   │ │
│ │                                                           │    fillRule="evenodd"]     │ │
│ │ ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐ │                            │ │
│ │ │ Inwoners (2024) │ │ Huishoudens (24)│ │ Woningen (26) │ │                            │ │
│ │ │ 4.430           │ │ 1.985           │ │ 2.110         │ │                            │ │
│ │ └─────────────────┘ └─────────────────┘ └───────────────┘ │                            │ │
│ │ Bouwperiodes (BAG 2024): [██ <1915: 22% |██ 15-45: 16% |████ 45-84: 41% |██ ≥1985: 21%]│ │
│ └───────────────────────────────────────────────────────────┴────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. THEMA-OVERZICHT IN 1 OOGOPSLAG (ThemaBenchmarkBalken.tsx — Ring 2 op schaal 1..8)       │
│ Horizontale benchmarkbalken t.o.v. middenlijn (4,5). Klik op thema = open detailtabel.     │
│                                                                                            │
│ Kwadrant: Kwaliteit fysieke leefomgeving                         Klasse / Duiding    Rang* │
│ ▶ Openbare ruimte                 [         |██████     ]        Klasse 6 Bovengem.   #18  │
│ ▶ Verkeer                         [     ████|           ]        Klasse 3 Ondergem.  #112  │
│ ▶ Wonen                           [       ██|           ]        Klasse 4 Gemiddeld   #95  │
│                                                                                            │
│ Kwadrant: Kwaliteit sociale leefomgeving                                                   │
│ ▶ Veiligheid                      [         |█████████  ]        Klasse 7 Gunstig      #6  │
│ ▶ Voorzieningen                   [  ███████|           ]        Klasse 2 Ongunstig  #145  │
│ ▶ Mienskip                        [         |██████     ]        Klasse 6 Bovengem.   #22  │
│                                                                                            │
│ Kwadrant: Kwaliteit van leven                                                              │
│ ▶ Gezondheid · ▶ Meedoen · ▶ Opgroeien · ▶ Rondkomen             (...)                     │
│                                                                                            │
│ Kwadrant: Samenstelling (beschrijvend / neutraal — blauw palet, geen goed/slecht of rang)  │
│ ▶ Bebouwing                       [████████████         ]        Klasse 5 Neutraal     —   │
│ ▶ Bevolking                       [█████████            ]        Klasse 4 Neutraal     —   │
├────────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. TOP 3 STERKE KANTEN & TOP 3 AANDACHTSPUNTEN (Onderdeel-prioritering / Ring 3)           │
│ ┌───────────────────────────────────────────┬────────────────────────────────────────────┐ │
│ │ ▲ Top 3 Sterke kanten (Onderdelen kl. ≥ 6)│ ▼ Top 3 Aandachtspunten (Onderdelen kl. ≤3)│ │
│ │ 1. Overlast & delicten (Klasse 8 · #4)    │ 1. Nabijheid voorzieningen (Klasse 2 ·#162)│ │
│ │    Thema: Veiligheid                      │    Thema: Voorzieningen                    │ │
│ │ 2. Actief betrokken (Klasse 7 · #12)      │ 2. Bereikbaarheid OV (Klasse 2 · #148)     │ │
│ │    Thema: Mienskip                        │    Thema: Verkeer                          │ │
│ │ 3. Klimaat & groen (Klasse 6 · #18)       │ 3. Energierekening & isolatie (Klasse 3)   │ │
│ │    Thema: Openbare ruimte                 │    Thema: Wonen                            │ │
│ └───────────────────────────────────────────┴────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. UITKLAPBARE DETAILTABEL MET TRENDLIJNEN (ThemaDrilldown.tsx — Ring 3 & Ring 4)          │
│ ▼ Thema: Openbare ruimte (Klasse 6 · #18 van 174)                                          │
│   Onderdeel / Indicator    Jaar  Waarde   Buurtgem.  Verschil  Klasse / Status  Trend      │
│   ──────────────────────────────────────────────────────────────────────────────────────── │
│   ▸ Onderdeel: Klimaat (Klasse 6)                                                          │
│   Aandeel bladerdek        2024  28,4 %     21,2 %    +7,2 %   Kl. 7 Gunstig    ▁▃▅▇ ↗     │
│   Afstand koele plek       2024   140 m      210 m     -70 m   Kl. 7 Gunstig    ▇▅▄▂ ↘     │
│   Speelplekken (aantal)    2024      12        8,4      +3,6   context (aantal) ▃▄▅▅ ➔     │
│   Kleine-n indicator       2024  Afgeschermd (< min. n)    —   onderdrukt            —     │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Technische Implementatiestappen & Verificatie

### Fase 1: Polariteit-audit (`V048`) + Backend Service (`factsheet_service.py`) & Router (`report.py`)
1. **Migratie & Stuurdata (`db/migraties/V048__polariteit_kompas_audit.sql`, `db/stuurdata/indicatoren.csv`):**
   - Corrigeert de polariteit van Kompas-indicatoren in de database (`lager_is_beter` voor ziekte/leefstijlrisico/overlast/armoede/hittestress/energielabelscore; `neutraal` voor *Samenstelling*).
   - Breidt `percentielklasse.richting()` en helperlogica uit zodat `indicatoren.polariteit == 'neutraal'` altijd als neutraal wordt behandeld.
2. **Eigen servicemodule `src/omnitwin/services/factsheet_service.py`:**
   - Houdt `report_service.py` slank.
   - Valideert dat alle `gebied_ids` van type `CBS_BUURT` zijn en binnen één gemeente liggen.
   - Berekent Hero-KPI's (met individueel peiljaar), BAG-bouwperiodepercentages en de gestructureerde `contour_kaart` padgegevens (`ST_SimplifyPreserveTopology`).
   - Berekent indicator-, onderdeel- en themaklassen via `percentielklasse.py` (met uitsluiting van aantal-indicatoren uit normatieve scores), inclusief de dynamische gemeentelijke themarangorde (met $\ge 50\%$ dekkingsdrempel) bij 1 buurt en Top 3 Sterke kanten / Aandachtspunten op Onderdeel-niveau (Ring 3).
   - Haalt meerjarige `historie` op (niet-onderdrukt) en bepaalt de trend (`stijgend`, `dalend`, `stabiel` + polariteitsbewuste duiding `gunstig` / `ongunstig` / `neutraal`).
3. **Router (`src/omnitwin/routers/report.py`):**
   - `POST /api/report/factsheet` (`FactsheetRequest`: `gebied_ids` max 200, `referentie`, `gemeente_code`, `deelgebied_naam`, `config_id`) en `GET /api/report/factsheet/{gebied_id}`.
4. **Verificatie Fase 1:**
   - Unit-tests in `tests/unit/test_report_factsheet.py` + `tests/unit/test_polariteit.py`.
   - `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .` en `.venv/bin/pytest tests/unit`.

### Fase 2: Frontend Factsheet-pagina & Componenten (`admin-panel/src/`)
1. **Types & API (`admin-panel/src/types/index.ts`, `admin-panel/src/services/api.ts`):**
   - Interfaces voor `FactsheetPayload` en API-aanroep `reportAPI.getFactsheet` / `postFactsheet`.
2. **Componenten (`admin-panel/src/components/reports/` & `pages/FactsheetPage.tsx`):**
   - `FactsheetHero.tsx` (inclusief React `<svg>` met `<path fillRule="evenodd">`), `ThemaBenchmarkBalken.tsx`, `ThemaDrilldown.tsx` (met toegankelijke SVG-sparklines en polariteitsbewuste trendlabels) en `FactsheetPage.tsx` (leest `?gebieden=...&naam=...&gemeente=...`).
3. **Routing & Layout (`admin-panel/src/App.tsx`):**
   - Regex `isGebiedsdossier` (regel 69) sluit `factsheet` uit.
   - Zijbalk-navigatie uitgebreid met `/rapport/factsheet`.
   - `ReportLayout` `context`-memo herkent `sub === 'factsheet'` (`rapport_type: 'Gebiedsfactsheet'`).
   - Route `/rapport/factsheet` geregistreerd vóór `/rapport/:gebied_id?`.
4. **Verificatie Fase 2:**
   - Vitest componenttests in `admin-panel/src/pages/FactsheetPage.test.tsx`.
   - `npm run typecheck`, `npm run lint`, `npm test`.

### Fase 3: Viewer-koppeling (`app.js`), Statische Build & Documentatie
1. **Viewer (`static/js/app.js`):**
   - Knop **📋 Gebiedsfactsheet** als eerste optie bovenaan in `openRapportTypeModal` en `openMultiSelectRapportModal`, gebouwd via veilige DOM-methodes (`createElement`, `textContent`, `addEventListener`, geen `innerHTML`), navigerend naar `/rapport/factsheet?gebieden=...`.
2. **Build & Changelog:**
   - Productiebuild via Docker `node:24` (`npm run build:static` → `static/admin-panel/`).
   - Vermelding onder `[Unreleased]` in `CHANGELOG.md`.

---

## 5. Verification Plan

### Functioneel & Methodisch
- Unit-tests voor polariteit (`tests/unit/test_polariteit.py`), percentielklasse (`tests/unit/test_percentielklasse.py`) en de nieuwe factsheet-service + routes (`tests/unit/test_report_factsheet.py`).
- Frontend component- en routetests (`admin-panel/src/pages/FactsheetPage.test.tsx`), `tsc --noEmit`, `eslint` en `ruff`.

### Automated Security Check & Security Verification
- **Input Validatie & Parameterisatie:** Pydantic-validatie op `FactsheetRequest` (`min_length=1`, `max_length=200`), strikte controle op gebiedstype `CBS_BUURT` binnen één gemeente (`GebruikersFout` → HTTP 400), en uitsluitend geparameteriseerde SQLAlchemy `text(...)` queries zonder string-interpolatie van gebruikersinvoer.
- **Autorisatie & Row Level Security (RLS, ADR 0009 / ADR 0010):** De routes hangen achter de standaard viewer-toegangsmiddleware (`viewer_toegang.py`) en `get_db()` schakelt voor anonieme verzoeken automatisch naar `SET ROLE omnitwin_openbaar`, zodat `intern`-indicatoren nooit lekken.
- **XSS-preventie & Veilige DOM/SVG-rendering:** Geen `dangerouslySetInnerHTML` in React (`FactsheetHero.tsx` rendert `<svg><path fillRule="evenodd" d={...} />` via JSX auto-escaping) en geen `innerHTML` bij het toevoegen van de factsheetknop in `static/js/app.js`.
- **Geen PII / Secrets / Hardcoded Org:** Geen persoonsgegevens, kleine aantallen onder `n_drempel` worden onderdrukt (`onderdrukt`), en geen hardcoded gemeentecodes of secrets.
- **Security Scanner & Security Audit:** Uitvoeren van de security scanner op alle nieuw aangemaakte bestanden (`factsheet_service.py`, `FactsheetHero.tsx`, `ThemaBenchmarkBalken.tsx`, `ThemaDrilldown.tsx`, `FactsheetPage.tsx`) en vastleggen van het security audit-overzicht na afronding.

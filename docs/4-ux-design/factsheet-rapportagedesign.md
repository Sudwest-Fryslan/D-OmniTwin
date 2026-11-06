# Factsheet- & Rapportagedesign (WBM / Thematische Buurtbarometer)

> **Gekoppeld issue:** [#441](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/441)  
> **Kader/Epic:** [Epic #309](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/309) ([Integrale gebruikerservaring-audit](./gebruikerservaring-audit.md), §2.5)  
> **Branch:** `feature/441-factsheet-rapportage-design`  
> **Status:** Vastgesteld ontwerp & implementatieplan (bijgewerkt na code- en data-audit)  
> **Auteur / Besluit:** T. van der Laan (Product Owner) & AI Pair Programmer  
> **Referentiebronnen:** Kompas-hiërarchie (`v_kompas_hierarchie` + `indicatoren.polariteit`), `db/schema/08_zscore_referentie.sql`, Wijk- en Buurtmonitor (WBM Enschede / Kennispunt Twente), [ADR 0007 Mesh & Portabiliteit](../2-architectuur/adr/0007-geen-multi-tenancy-mesh-van-instanties.md), [ADR 0010 Toegang per laag](../2-architectuur/adr/0010-toegang-per-laag-en-bron.md), [ADR 0011 Toegankelijkheid](../2-architectuur/adr/0011-toegankelijkheid-wcag.md).

---

## 1. Positie, Probleemstelling & Afbakening

### 1.1 Positie naast bestaande rapporten
De **Gebiedsfactsheet** wordt toegevoegd als een **nieuw, zelfstandig rapporttype** op `/rapport/factsheet` (`FactsheetPage.tsx`), **naast** de bestaande rapportvormen (`Gebiedsdossier` op `/rapport/:gebied_id`, `Deelgebiedsanalyse`, `Multi-Gebiedsdossier`, `Thema-Analyse` en `Benchmark`). Bestaande rapporten en hun eventuele AI-narratieven blijven ongewijzigd.

Vanuit de kaartviewer (`static/js/app.js`) verschijnt **📋 Gebiedsfactsheet** als **eerste optie bovenaan** in dezelfde rapportkeuze-modal als de overige rapporten — zowel bij een enkel geselecteerd gebied (`openRapportTypeModal`) als bij een meervoudige selectie (`openMultiSelectRapportModal`).

### 1.2 Enkelvoudige én meervoudige gebiedsselectie
Een factsheet gaat niet uitsluitend over één buurt, maar werkt voor zowel **1 gebied** (bijv. één buurt zoals Workum) als **meerdere geselecteerde gebieden** (bijv. een cluster van 6 buurten of een deelgebied van 42 buurten):

| Onderdeel | 1 geselecteerd gebied | Meerdere geselecteerde gebieden ($k \ge 2$) |
|---|---|---|
| **Hero-titel & contourkaart** | Gebiedsnaam, code, gemeente + SVG-contour van het gebied binnen de gemeente | Samengestelde naam (optionele naam of aantal geselecteerde gebieden) + SVG-contour met alle geselecteerde vlakken gemarkeerd |
| **Hero kern-KPI's (aantallen)** | Waarde van het gebied (inwoners, huishoudens, woningen, BAG-bouwperiodes in %) | **Som** over de geselecteerde gebieden; BAG-percentages berekend uit de gesommeerde bouwjaarklassen |
| **Relatieve indicatoren & themascores** | Waarde en Z-score van het gebied t.o.v. referentie (`gemeente` of `fryslan`) | **Inwonersgewogen gemiddelde** over de selectie (terugval op rekenkundig gemiddelde als inwonertal ontbreekt), afgezet tegen referentie ($\mu_{\text{ref}}, \sigma_{\text{ref}}$) |
| **Thematische rangpositie** | **Wel getoond** bij normatieve thema's: `#14 van {n_met_score}` binnen de gemeente | **Niet getoond**: een vrije meervoudige selectie vormt een samengesteld gebied zonder individuele plek op de enkelvoudige buurtenranglijst |
| **Aantal-indicatoren in detailtabel** | Waarde van het gebied vs. referentiegemiddelde per gebied | **Som** van de selectie + gemiddelde per geselecteerd gebied vs. referentiegemiddelde per gebied |

### 1.3 Wat we bewust NIET doen (Methodische & Scope-afbakening)
- ❌ **Geen 'totaalscore' of totaalrangorde per buurt** (zoals *"Rang 5 van 177"*): ongelijksoortige domeinen (bijv. criminaliteit en groen) zijn inhoudelijk niet optelbaar tot één rapportcijfer.
- ❌ **Geen gemeentebrede gestapelde buurt-totaalbalken:** het opstapelen van themascores over alle buurten heen suggereert een onzuivere totaalsom en valt buiten deze factsheet.
- ❌ **Geen 4-kwadranten Trend- & Urgentiematrix (scatterplot):** bewust buiten scope gehouden om de factsheet overzichtelijk, direct leesbaar en afdrukbaar te houden.
- ❌ **Geen AI/LLM-narratief:** 100% deterministisch, reproduceerbaar en direct beschikbaar zonder afhankelijkheid van een taalmodel.
- ❌ **Geen cijferdump op het hoofdscherm:** op hoofdniveau staan alleen de kern-KPI's, de 12 thema's en de Top 3 sterke kanten/aandachtspunten; alle afzonderlijke indicatoren zitten in de uitklapbare detailtabel per thema.

---

## 2. Methodiek, Kompas-taxonomie & Rekenregels

### 2.1 Aansluiting op de 4 ringen van het Kompas
De factsheet volgt het standaard Kompas-profiel (`kompas_configuraties WHERE is_standaard = TRUE`, of een expliciet meegegeven `config_id` — nooit een hardcoded `config_id = 1`):

1. **Ring 1 — 4 Kwadranten:**
   - Normatief (3 kwadranten): *Kwaliteit fysieke leefomgeving*, *Kwaliteit sociale leefomgeving*, *Kwaliteit van leven*.
   - Beschrijvend / neutraal (1 kwadrant): *Samenstelling* (*Bebouwing* & *Bevolking*).
2. **Ring 2 — 12 Thema's:** Horizontale benchmarkbalken t.o.v. de referentielijn (`0,0 Z`).
3. **Ring 3 — Onderdelen (subthema's):** Groepering in de detailweergave en bron voor thematische duiding.
4. **Ring 4 — Indicatoren:** Individuele meetwaarden, eenheden, referentiegemiddelden, tijdreeksen (sparklines) en bronmetadata in de uitklapbare tabel.

### 2.2 Polariteit & Kwadrant *Samenstelling* (Neutraal)
- **Bron van polariteit (`V046__polariteit.sql`):** De view `v_kompas_hierarchie` bevat enkel `sr.score_type` en `sr.inverse` (vaak `NULL`), maar niet `indicatoren.polariteit`. De backend-query **moet** daarom `indicatoren i` joinen en de effectieve richting bepalen uit `i.polariteit` (`hoger_is_beter` | `lager_is_beter` | `neutraal`) gecombineerd met een eventuele `sr.inverse`-override via `omnitwin.polariteit`.
- **Richtingscorrectie:**
  - `hoger_is_beter`: gerichte Z-score $z^* = +z$ (positief = gunstiger dan referentie).
  - `lager_is_beter` (bijv. overlast, afstand tot voorziening): gerichte Z-score $z^* = -z$ (lagere ruwe waarde wordt positieve score = gunstiger dan referentie).
  - `neutraal`: afwijking $z$ blijft ongericht (beschrijvend hoger/lager dan referentie, zonder goed/slecht-oordeel).
- **Kwadrant 4 (*Samenstelling*) altijd neutraal:** Demografische en fysieke samenstelling (leeftijdsopbouw, huishoudenstypen, bouwjaarklassen, eigendomsverhouding) zijn nooit normatief "goed" of "slecht". Thema's onder *Samenstelling* (en thema's met uitsluitend neutrale indicatoren) worden in een **neutrale blauwtint** getoond met feitelijke afwijkingsrichting (*hoger/lager dan gemiddeld*), **zonder** normatieve kleur (groen/rood), **zonder** goed/slecht-rangnummer en **uitgesloten** van *Top Sterke kanten & Aandachtspunten*.

### 2.3 Uitsluiting van ruwe aantallen (`eenheid == 'aantal'`) uit normatieve weging
- In het Kompas zijn ook ruwe tel-indicatoren gekoppeld (`eenheid = 'aantal'`, zoals `Inwoners`, `Aantal energielabels A..G`, `Aantal bushaltes`). Als deze meetellen in een Z-scoregemiddelde, krijgen grote buurten systematisch afwijkende themascores puur door hun omvang en ontstaat dubbeltelling naast relatieve indicatoren (`%`).
- **Regel:**
  1. Indicatoren met `LOWER(TRIM(i.eenheid)) = 'aantal'` tellen **niet** mee in de normatieve thema- en subthemascores ($S_{\text{thema}}$) en komen **niet** in *Top 3 Sterke kanten / Top 3 Aandachtspunten*.
  2. Ze zijn **wél volledig zichtbaar** in de uitklapbare indicatorentabel (`ThemaDrilldown`) onder hun eigen thema, gemarkeerd als contextuele aantal-indicator (`weging: null`, label `context (aantal)`).

### 2.4 Formules voor Themascore, Rangorde & Top Kansen/Aandachtspunten
- **Normatieve themascore ($S_{\text{thema}}$):** Gewogen gemiddelde van alle niet-onderdrukte, normatieve (`polariteit != 'neutraal'`), relatieve (`eenheid != 'aantal'`) indicatoren onder dat thema:
  $$S_{\text{thema}} = \frac{\sum (z^*_i \times w_i)}{\sum w_i}$$
- **Dynamische themarangorde (alleen bij 1 gebied & normatieve thema's):**
  - Berekend in **één enkele bulk-query** via `public.zscore_gebieden(NULL, gebiedstype_id, gemeente_code, ...)` voor alle landbuurten in de gemeente tegelijk (geen $N$-voudige query-loop).
  - Omdat kleine aantallen (`public.is_kleine_aantallen(gd.n)`, `V044` / #325) per indicator en buurt onderdrukt kunnen zijn, wordt de noemer per thema zuiver bepaald op het werkelijke aantal buurten met een geldige score voor dat thema: `#14 van {n_gebieden_met_score}` (bij gelijke score: standaard competitierang `1, 2, 2, 4`).
- **Top 3 Sterke kanten & Top 3 Aandachtspunten:**
  - Geselecteerd uit de normatieve, relatieve indicatoren (of onderdelen wanneer gewenst op indicatorniveau met vermelding van het bijbehorende thema; we tonen de **sterkste individuele normatieve, niet-aantal indicatoren met themalabel**, gededupliceerd per onderdeel zodat niet drie bijna-identieke indicatoren uit één subthema de hele top 3 vullen):
    - *Sterke kanten (Kansen):* hoogste positieve $z^*_i \ge +0{,}5$, aflopend (max. 3).
    - *Aandachtspunten:* laagste negatieve $z^*_i \le -0{,}5$, oplopend vanaf meest negatief (max. 3).
  - Als er minder dan 3 indicatoren boven/onder de drempel van $\pm 0{,}5\text{ Z}$ liggen, toont het blok alleen de daadwerkelijke uitschieters (geen kunstmatig opgevulde rijen).

### 2.5 Kleine aantallen (#325), Waterbuurten (#155), RLS (#254) & Portabiliteit (ADR 0007)
- **Kleine aantallen (`V044`):** Waarden waarvoor `is_kleine_aantallen(gd.n)` geldt, zijn `NULL` in `zscore_gebieden`. In de detailtabel blijven gekoppelde indicatoren waarvan het gebied wél een afgeschermde meting heeft zichtbaar met `status: "onderdrukt"` en weergave *"Afgeschermd (kleine aantallen)"* in plaats van stilzwijgend te verdwijnen of `0` te tonen.
- **Waterbuurten (`gebieden.metadata->>'water' = 'JA'`):** Maken nooit deel uit van de referentiegroep (`08_zscore_referentie.sql`). Wordt een enkele waterbuurt geopend, dan toont de factsheet de basisidentificatie en contourkaart met een heldere melding dat watergebieden buiten de bewoningsbenchmark vallen. In een meervoudige selectie worden geselecteerde waterbuurten niet meegewogen in normatieve gemiddelden.
- **Toegang per laag (`ADR 0010`):** Alle queries draaien op de reguliere databasesessie van het verzoek (geen eigen `SECURITY DEFINER`), zodat `SET ROLE omnitwin_openbaar` voor anonieme bezoekers automatisch indicatoren met `toegang = 'intern'` uitsluit.
- **Portabiliteit (`ADR 0007`):**
  - Geen hardcoded gemeentecode (`'1900'`), gemeentenaam (`'Súdwest-Fryslân'`) of aantallen (`177`) in code; gemeentecontext komt dynamisch uit `gebieden` en `omnitwin.services.organisatie`.
  - Hero-kerncijfers gebruiken een canonieke lookup op code/naam met graceful fallback: ontbreekt een bron (bijv. energielabels of BAG in een andere gemeente), dan toont die tegel `n.b.` of blijft achterwege zonder dat het endpoint faalt.
  - Voor het woningenaantal wordt gekeken naar gekoppelde of aanwezige woningvoorraad-indicatoren (`Woningvoorraad` / `Woonfunctie` BAG). Voor BAG-bouwperiodes worden de 4 aantal-indicatoren (`Bouwjaar voor 1915`, `Bouwjaar 1915-1945`, `Bouwjaar 1945-1984`, `Bouwjaar vanaf 1985`) gesommeerd en omgerekend naar percentages.

---

## 3. Visuele Layout & Componentenstructuur

De factsheet draait binnen de bestaande `<ReportLayout>` (`admin-panel/src/App.tsx`), die reeds de vaste rapportkop verzorgt (`← Terug naar kaart`, organisatie-beeldmerk, `Afwijking melden`, `Afdrukken`). `FactsheetPage.tsx` rendert dus **geen** dubbele topbalk.

```
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│ [Bestaande ReportLayout Header: ← Terug naar kaart · Beeldmerk · Afwijking melden · Print] │
├────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. FACTSHEET HERO (FactsheetHero.tsx)                                                      │
│ ┌───────────────────────────────────────────────────────────┬────────────────────────────┐ │
│ │ Gebiedsfactsheet · Referentie: [Gemeente ▾ | Fryslân]     │                            │ │
│ │ Workum (BU19000200)                                       │   [Inline SVG Contourkaart │ │
│ │ Gemeente Súdwest-Fryslân · Peiljaar meest recent          │    selectie in gemeente]   │ │
│ │                                                           │                            │ │
│ │ ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐ │                            │ │
│ │ │ Inwoners        │ │ Huishoudens     │ │ Woningen      │ │                            │ │
│ │ │ 4.430           │ │ 1.985           │ │ 2.110         │ │                            │ │
│ │ └─────────────────┘ └─────────────────┘ └───────────────┘ │                            │ │
│ │ Bouwperiodes (BAG): [██ <1915: 22% |██ 15-45: 16% |████ 45-84: 41% |██ ≥1985: 21%]     │ │
│ └───────────────────────────────────────────────────────────┴────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. TOP STERKE KANTEN & AANDACHTSPUNTEN (alleen normatieve, relatieve indicatoren)          │
│ ┌───────────────────────────────────────────┬────────────────────────────────────────────┐ │
│ │ ▲ Top 3 Sterke kanten (gunstiger dan gem.)│ ▼ Top 3 Aandachtspunten (ongunstiger)      │ │
│ │ 1. Lage overlast & vernieling (+1,8 Z)    │ 1. Afstand huisarts/voorziening (-1,9 Z)   │ │
│ │    Thema: Veiligheid · 1,2% vs. gem. 3,4% │    Thema: Voorzieningen · 2,4 vs. 1,1 km   │ │
│ │ 2. Actieve inzet vrijwilligers (+1,2 Z)   │ 2. Aandeel slecht geïsoleerd (-1,3 Z)      │ │
│ │ 3. Aandeel groen & bladerdek (+1,1 Z)     │ 3. Afstand OV-knooppunt (-1,1 Z)           │ │
│ └───────────────────────────────────────────┴────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. THEMA-OVERZICHT IN 1 OOGOPSLAG (ThemaBenchmarkBalken.tsx)                               │
│ Horizontale diverging benchmarkbalken t.o.v. referentielijn (0,0 Z). Klik = open tabel.    │
│                                                                                            │
│ Kwadrant: Kwaliteit fysieke leefomgeving                            Score / Duiding  Rang* │
│ ▶ Openbare ruimte                 [         |███████    ]           +0,8 Z Gunstiger  #18  │
│ ▶ Verkeer                         [     ████|           ]           -0,5 Z Aandacht  #112  │
│ ▶ Wonen                           [       ██|           ]           -0,2 Z Gemiddeld  #95  │
│                                                                                            │
│ Kwadrant: Kwaliteit sociale leefomgeving                                                   │
│ ▶ Veiligheid                      [         |██████████ ]           +1,4 Z Gunstiger   #6  │
│ ▶ Voorzieningen                   [  ███████|           ]           -1,6 Z Aandacht  #145  │
│ ▶ Mienskip                        [         |████████   ]           +0,9 Z Gunstiger  #22  │
│                                                                                            │
│ Kwadrant: Kwaliteit van leven                                                              │
│ ▶ Gezondheid · ▶ Meedoen · ▶ Opgroeien · ▶ Rondkomen                (...)                  │
│                                                                                            │
│ Kwadrant: Samenstelling (beschrijvend / neutraal — geen goed/slecht-oordeel)               │
│ ▶ Bebouwing                       [         |█████      ] (blauw)   +0,6 Z Afwijking   —   │
│ ▶ Bevolking                       [      ███|           ] (blauw)   -0,4 Z Afwijking   —   │
│ (*Rang kolom "#X van Y" verschijnt alleen bij selectie van 1 buurt)                        │
├────────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. UITKLAPBARE DETAILTABEL MET TRENDLIJNEN (ThemaDrilldown.tsx, per thema of "Alles open") │
│ ▼ Openbare ruimte (+0,8 Z · #18 van 174 · 6 indicatoren)                                   │
│   Indicator               Waarde   Ref. gem.  Verschil   Richting / Z    Trend (sparkline) │
│   ──────────────────────────────────────────────────────────────────────────────────────── │
│   Aandeel bladerdek       28,4 %     21,2 %    +7,2 %    +1,2 Z Gunstig  ▁▃▅▇ ↗ (2020–24)  │
│   Afstand koele plek       140 m      210 m     -70 m    +0,9 Z Gunstig  ▇▅▄▂ ↘ (gunstig)  │
│   Speelplekken (aantal)       12        8,4      +3,6    context (aantal) ▃▄▅▅ ➔ (2021–24) │
│   Kleine-n indicator   Afgeschermd (< min. n)     —            —                 —         │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Toegankelijkheid & Vormgeving (WCAG 2.1 AA — ADR 0011)
1. **Geen informatie alleen via kleur:** Elke balk en cel combineert kleur met expliciete voortekens (`+`/`-`), tekstlabels (*Gunstiger*, *Aandachtspunt*, *Gemiddeld*, *Neutraal / afwijking*) en pijlsymbolen (`▲`/`▼`/`↗`/`↘`/`➔`).
2. **Toetsenbord & schermlezers:** Elke themarij heeft een semantische `<button aria-expanded="..." aria-controls="...">` zonder 23-teken afkapping van het label. Sparklines krijgen een beschrijvend `aria-label` met beginjaar/waarde en eindjaar/waarde (bijv. *"2020: 21,0% naar 2024: 28,4%, stijgend"*).
3. **Thema-tokens & Afdrukbaarheid:** Opgebouwd met NL Design System CSS-variabelen (`thema.ts`, werkt in lichte én donkere modus) en `@media print`-regels (optie *"Alle thema's uitklappen"* + automatisch volledig leesbare printopmaak op A4 zonder wegvallende achtergronden).

---

## 4. Technische Implementatiestappen & Verificatie

### Fase 1: Backend Service & Router (`src/omnitwin/`)
- **Bestanden:** `src/omnitwin/services/report_service.py` (of eigen hulpfuncties voor factsheet daarbinnen) en `src/omnitwin/routers/report.py`.
- **Routes:**
  - `POST /api/report/factsheet` met body `{ gebied_ids: list[str], referentie: "gemeente" | "fryslan" = "gemeente", gemeente_code?: str, deelgebied_naam?: str, config_id?: int }`.
  - `GET /api/report/factsheet/{gebied_id}?referentie=gemeente&config_id=...` als directe convenience-route voor 1 gebied (roept dezelfde servicelogica aan).
- **Functionaliteit:**
  1. Validatie van `gebied_ids`, ophalen gebiedsmetadata (`naam`, `code`, `gebiedstype`, `gemeente_code`, waterbuurt-vlag) en generatie van het inline SVG-contourkaartje (`gebieden.geom` van selectie binnen gemeentecontour, naar voorbeeld van `generate_deelgebied_svg_kaart`).
  2. Ophalen van het standaard Kompas-profiel (`is_standaard = TRUE` als `config_id` ontbreekt) en join van `v_kompas_hierarchie` met `indicatoren` (`polariteit`, `eenheid`, `bron`) en `omnitwin.polariteit`.
  3. Berekening van Z-scores via `08_zscore_referentie.sql` (`zscore_gebieden`): bij 1 buurt op gemeentereferentie in één bulk-call (`p_gebied_ids = NULL`) voor zowel de buurtwaarden als de exacte dynamische themarangorde (`#X van Y`); bij meervoudige selectie inwonersgewogen aggregatie voor relatieve indicatoren en sommatie voor aantal-indicatoren.
  4. Ophalen van meerjarige `historie` per gekoppelde indicator (met respect voor `is_kleine_aantallen(n)`) en berekening van trendrichting (`stijgend` | `dalend` | `stabiel` bij $\ge 2$ meetjaren).
  5. Samenstellen van Hero-KPI's + procentuele BAG-bouwperiodeverdeling, Top 3 Sterke kanten & Top 3 Aandachtspunten, 4 Kwadranten / 12 Thema's en de volledige indicator-drilldown inclusief onderdrukte indicatoren (`status: "onderdrukt"`).
- **Verificatie Fase 1:**
  - Nieuwe unit tests in `tests/unit/test_report_factsheet.py` (polariteit `lager_is_beter` omkering, Kwadrant *Samenstelling* & `neutraal` buiten Kansen/Aandachtspunten en zonder rang, uitsluiting `eenheid == 'aantal'` uit normatieve themascore maar behoud in drilldown, 1-buurt rangberekening vs. multi-buurt gewogen aggregatie, onderdrukking kleine aantallen, waterbuurt-afhandeling, 0 hardcoded `'1900'`).
  - Checks: `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .` en `.venv/bin/pytest tests/unit`.

### Fase 2: Frontend Factsheet-pagina & Componenten (`admin-panel/src/`)
- **Bestanden:**
  - `admin-panel/src/types/index.ts` en `admin-panel/src/services/api.ts`: TypeScript-interfaces en client-methodes (`getFactsheet`, `postFactsheet`).
  - `admin-panel/src/components/reports/FactsheetHero.tsx`: Titel, referentie-schakelaar (`Gemeente` / `Fryslân`), KPI-tegels, gestapelde 100%-balk voor BAG-bouwperiodes en inline SVG-contourkaart.
  - `admin-panel/src/components/reports/ThemaBenchmarkBalken.tsx`: Toegankelijke HTML/CSS diverging benchmarkbalken gegroepeerd per kwadrant (normatief vs. neutraal *Samenstelling*), rangkolom bij 1 gebied, accordeon-knoppen en *"Alles uitklappen / inklappen"*.
  - `admin-panel/src/components/reports/ThemaDrilldown.tsx`: Uitklapbare indicatorentabel met waarde, referentie, verschil, gerichte Z-score/status, onderdrukkingsmelding en toegankelijke inline SVG-sparkline + trendpijl (`↗` `↘` `➔`).
  - `admin-panel/src/pages/FactsheetPage.tsx`: Pagina die zowel `?gebied=BU...` / `:gebied_id` (1 gebied) als `?gebieden=BU1,BU2,...&naam=...` (meerdere gebieden) ondersteunt.
  - `admin-panel/src/App.tsx`: Route `/rapport/factsheet` en `/rapport/factsheet/:gebied_id` registreren binnen `<ReportLayout>` en `sub === 'factsheet'` toevoegen aan de rapportcontext (`Gebiedsfactsheet`) voor *Afwijking melden*.
- **Verificatie Fase 2:**
  - Componenttests in `admin-panel/src/pages/FactsheetPage.test.tsx` (enkelvoudig vs. meervoudig gebied, neutrale *Samenstelling*, accordeon `aria-expanded`, sparkline `aria-label`, onderdrukte waarde).
  - Checks: `npm run typecheck`, `npm run lint`, `npm test`.

### Fase 3: Viewer-koppeling, Statische Build & Documentatie
- **Bestanden:**
  - `static/js/app.js`: Knop **📋 Gebiedsfactsheet** als **eerste optie bovenaan** plaatsen in `openRapportTypeModal` (1 gebied → `/rapport/factsheet?gebied=...`) en `openMultiSelectRapportModal` (meerdere gebieden → `/rapport/factsheet?gebieden=...`).
  - `static/admin-panel/`: Productiebuild genereren via de `node:24` container (`npm run build:static`) zodat hashes exact overeenkomen met CI.
  - `CHANGELOG.md`: Vermelding toevoegen onder `[Unreleased]`.
- **Verificatie Fase 3:**
  - Volledige lokale controle van ruff, unit-tests, frontend-checks en git-diff van `static/admin-panel/`.

# Factsheet- & Rapportagedesign (WBM / Thematische Buurtbarometer)

> **Gekoppeld issue:** [#441](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/441)  
> **Kader/Epic:** [Epic #309](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/309) (Integrale gebruikerservaring-audit, §2.5)  
> **Branch:** `feature/441-factsheet-rapportage-design`  
> **Status:** Vastgesteld ontwerp & implementatieplan  
> **Auteur / Besluit:** T. Laan (Product Owner) & AI Pair Programmer  
> **Referentiebronnen:** Kompas-hiërarchie (`v_kompas_hierarchie`), `docs/7-projectmanagement/tmp/issue-441/verkenning_ijsselmeerkust_indicatoren_rapportagedesign_441.md`, Wijk- en Buurtmonitor (WBM Enschede / Kennispunt Twente).

---

## 1. Probleemstelling & Doelstelling

### 1.1 Huidige Situatie
De huidige rapportages (`/rapport/:gebied_id`, `admin-panel/src/pages/ReportPage.tsx`) tonen nu een statische tabel met technische Z-scores (`+10.91`, `+8.16`). Gebruikers ervaren hierbij belangrijke belemmeringen:
1. **Geen overzicht in 1 oogopslag:** Er zijn geen visuele benchmarkbalken; cijfers staan los van een herkenbare gemeentelijke norm;
2. **Gebrek aan thematische prioritering:** Het is onduidelijk welke thema's in een buurt urgent zijn en welke thema's juist als kracht fungeren;
3. **Ontbrekende basiscontext:** Kerncijfers over de bevolking (inwoners, huishoudens) en de fysieke leefomgeving (BAG-bouwperiodes) ontbreken in de kop van het rapport.

### 1.2 Wat we NIET doen (Methodische Afbakening)
- ❌ **Geen vage 'totaalscore' per buurt:** Een eenduidige rangorde van buurten (zoals "Buurt X is nummer 5 van 177") is methodisch onzuiver omdat indicatoren uit verschillende domeinen (bijv. criminaliteit en groen) niet zomaar optelbaar zijn.
- ❌ **Geen AI-narrative overhead (LLM):** Deze rapportvorm wordt 100% data- en visualisatiegedreven: deterministisch, snel, stabiel en zonder afhankelijkheid van een lokaal of extern taalmodel.
- ❌ **Geen onoverzichtelijke cijferdump:** We tonen niet alle 248 indicatoren tegelijk op het hoofdscherm.

### 1.3 Het Doelbeeld: WBM / Buurtbarometer Methodiek
- ✅ **Thematische rangorde en benchmarking op Ring 2 (12 Thema's) en Ring 3 (33 Onderdelen):**  
  De score en onderlinge afwijking van buurten wordt bepaald **per thema en onderdeel** uit het Kompas. Dit beantwoordt direct de centrale beleidsvraag: *"Op Klimaat scoort Workum +1.2 Z (#14 van 177 landbuurten), maar op Voorzieningennabijheid -1.4 Z (#145 van 177)"*.
- ✅ **Volledige transparantie (Drill-down):**  
  Elk thema kan worden opengeklapt om direct in te zien *welke indicatoren* (Ring 4) hebben meegewogen in de themascore, inclusief de reële meetwaarden (% of km).
- ✅ **Gemeentelijke referentielijn:**  
  Vaste visuele referentielijn voor het gemeentegemiddelde van Súdwest-Fryslân (gebaseerd op alle 177 landbuurten, exclusief waterbuurten conform ADR 0007 / z-score methodiek).

---

## 2. Taxonomische Aansluiting: De 4 Ringen van het Kompas

De factsheet sluit 1-op-1 aan op de officiële databasehiërarchie (`v_kompas_hierarchie`):

```
D-Omni Kompas Taxonomie (v_kompas_hierarchie)
├── Ring 1: 4 Kwadranten (Titel)
│   ├── Kwaliteit fysieke leefomgeving
│   ├── Kwaliteit sociale leefomgeving
│   ├── Kwaliteit van leven
│   └── Samenstelling
│
├── Ring 2: 12 Thema's (Thematische Hoofdscores)
│   ├── Openbare ruimte · Verkeer · Wonen
│   ├── Mienskip · Veiligheid · Voorzieningen
│   ├── Gezondheid · Meedoen · Opgroeien · Rondkomen
│   └── Bebouwing · Bevolking
│
├── Ring 3: 33 Onderdelen (Subthema Prioritering & Rangorde)
│   ├── Klimaat · Inrichting · Bereikbaarheid · Betaalbaarheid · Technische kwaliteit
│   ├── Actief betrokken · Overlast · Vermogensdelicten · Maatschappelijke voorzieningen
│   ├── Leefstijl · Functioneren · Armoede · Werk · Bouwperiode · Leeftijd · Huishoudens...
│
└── Ring 4: 248 Indicatoren (Meetwaarden, Weging & Polariteit)
    └── Aandeel bladerdek, Afstand tot huisarts, WOZ-waarde, Bouwjaar <1915, etc.
```

### Berekening & Weegmethodiek:
1. **Indicator Z-score ($z_i$):** Berekend via `db/schema/08_zscore_referentie.sql` t.o.v. alle landbuurten in de gemeente (referentie jaarlogica `zelfde_jaar`).
2. **Polariteitscorrectie ($p_i$):** Correctie via `omnitwin.polariteit`: bij `score_type = '-/+'` (bijv. inbraken) keert de afwijking om zodat een positieve score altijd duidt op een **gunstige** situatie en negatief op een **knelpunt**.
3. **Themascore ($S_{\text{thema}}$):** Gewogen gemiddelde van de gecorrigeerde Z-scores onder dat thema:  
   $$S_{\text{thema}} = \frac{\sum (z_i \times w_i)}{\sum w_i}$$
4. **Thematische Rangorde:** Sortering van alle 177 landbuurten in SWF op $S_{\text{thema}}$ (bijv. *"Rang 14 van 177"*).

---

## 3. Visuele Layout & Componentenstructuur

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. FACTSHEET HERO HEADER                                                               │
│ Buurt: Workum (BU19000200) · Gemeente Súdwest-Fryslân (177 landbuurten)                │
│ ┌──────────────────────────┬──────────────────────────┬──────────────────────────────┐ │
│ │ 👥 Inwoners: 4.430       │ 🏠 Huishoudens: 1.985    │ 🏗️ Woningen: 2.110           │ │
│ │ 📅 Gem. bouwjaar: 1968   │ 🏘️ Vóór 1945: 38% (BAG)  │ ⚡ Gem. energielabel: C       │ │
│ └──────────────────────────┴──────────────────────────┴──────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. THEMA-OVERZICHT IN 1 OOGOPSLAG (12 HOOFDTHEMA'S)                                    │
│ Horizontale benchmarkbalken (diverging bars) t.o.v. gemeentegemiddelde (0.0):          │
│                                                                                        │
│ [Fysieke Leefomgeving]                                                Afwijking Rang   │
│ • Openbare ruimte & Klimaat     [=========|======]                    +0.8 Z    #18    │
│ • Verkeer & Mobiliteit          [======|=========]                    -0.5 Z    #112   │
│ • Wonen & Energie               [=======|========]                    -0.2 Z    #95    │
│                                                                                        │
│ [Sociale Leefomgeving]                                                                 │
│ • Veiligheid                    [===========|====]                    +1.4 Z    #6     │
│ • Voorzieningen                 [====|===========]                    -1.6 Z    #145   │
│ • Mienskip & Betrokkenheid      [=========|======]                    +0.9 Z    #22    │
│                                                                                        │
│ [Kwaliteit van Leven]                                                                  │
│ • Gezondheid & Leefstijl        [=========|======]                    +0.6 Z    #34    │
│ • Rondkomen & Bestaanszekerheid [========|=======]                     0.0 Z    #88    │
│ • Meedoen & Eenzaamheid         [=======|========]                    -0.3 Z    #102   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. TOP KANSEN & TOP KNELPUNTEN (SUBTHEMA-PRIORITERING / RING 3)                        │
│  Top 3 Sterke kanten van de buurt:              Top 3 Aandachtspunten van de buurt:    │
│  1. 🟢 Lage overlast & geweld (+1.8 Z, #4)      1. 🔴 Afstand maatschappelijke voorz.  │
│  2. 🟢 Actieve Mienskip (+1.2 Z, #12)              (-1.9 Z, #162)                      │
│  3. 🟢 Veel groen & bladerdek (+1.1 Z, #15)     2. 🟡 Oudbouw & warmteverlies (-1.3 Z) │
│                                                 3. 🟡 Bereikbaarheid OV (-1.1 Z, #130) │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. TRANSPARANTE DETAIL-INZAGE (DRILL-DOWN NAAR RING 4 INDICATOREN)                     │
│ Klik op een thema vouwt de onderliggende indicatoren uit:                              │
│ ▼ Thema: Openbare ruimte & Klimaat (+0.8 Z)                                           │
│   Indicator                        Waarde    Gem. SWF   Verschil   Z-score  Weging     │
│   ────────────────────────────────────────────────────────────────────────────────     │
│   Aandeel bladerdek                 28.4 %     21.2 %    +7.2 %    +1.2 Z    1.0       │
│   Afstand tot koele plek           140 m      210 m     -70 m     +0.9 Z    1.0       │
│   Oppervlak groen per inwoner       45 m²      38 m²     +7 m²     +0.4 Z    1.0       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Technische Implementatiestappen

### Stap 1: Backend Endpoint (`src/omnitwin/services/report_service.py`)
- Nieuw endpoint toevoegen: `GET /api/report/factsheet/{gebied_id}`:
  1. Ophalen van contextdata:
     - Inwonersaantal (`31f70dff-c116-4267-bef0-d15b0ff4c020`),
     - Huishoudens totaal (`be1a9ac4-6330-47c9-93c6-c9008b5daf89`),
     - Woningen totaal (`Woningvoorraad`),
     - BAG-bouwperiodes (<1915, 1915–1945, 1945–1984, >1985).
  2. Bepalen van themascores voor Ring 2 (Thema's) en Ring 3 (Onderdelen) via `v_kompas_hierarchie` gecombineerd met de referentie-SQL (`08_zscore_referentie.sql`).
  3. Bepalen van de gemeentelijke rangorde per thema t.o.v. alle 177 landbuurten.
  4. Meeverpakken van de onderliggende indicatoren (werkelijke waarde, gemeentegemiddelde, delta, eenheid) voor de transparante drilldown.
- **Verificatie:** Unit tests in `tests/unit/test_report_factsheet.py` draaien groen.

### Stap 2: Frontend UI Componenten (`admin-panel/src/`)
- `FactsheetHero.tsx`: Toont de buurtnaam, kern-KPI's en BAG-bouwperiode grafiekje.
- `ThemaBenchmarkBalken.tsx`: Horizontale diverging bars met vaste referentielijn (0.0 / gemeentegemiddelde) en kleur/icoon codering conform WCAG 2.1 AA.
- `ThemaDrilldown.tsx`: Uitklapbare accordeon met de onderliggende indicatoren en wegingen.
- **Verificatie:** Vitest tests in `admin-panel/` (`npm test`).

### Stap 3: Integratie & Build
- `ReportPage.tsx` refactoren zodat deze componenten de primaire weergave vormen.
- Statische productiebuild voor de web-container: `npm run build:static`.
- **Verificatie:** `npm run typecheck`, `npm run lint` en browsercheck op `http://localhost/rapport/:gebied_id`.

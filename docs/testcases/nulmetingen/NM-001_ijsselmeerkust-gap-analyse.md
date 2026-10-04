# NM-001 — Nulmeting: Gap-analyse IJsselmeerkust & Wadden

**Type:** Nulmeting (IST-situatie)
**Regio:** Súdwest-Fryslân — IJsselmeerkust & Wadden (Makkum, Workum, Koudum)
**Datum:** 2026-04-09
**Status:** Afgerond
**Afgeleid van:** `testcase_d_omni_twin_gebiedsmonitor_ijsselmeerkust_wadden.md` (origineel)

---

## Doel

Deze nulmeting legt de **IST-situatie** vast: wat werkt, wat ontbreekt, en wat blokkeert effectief gebruik van D-OmniTwin als gebiedsmonitor voor de IJsselmeerkust-regio.

Gebruik dit document als:
1. Nulmeting (baseline voor toekomstige metingen)
2. Input voor backlog-prioritering
3. Basis voor dataspace-transitie argumentatie

---

## 1. Testopzet

De toetsing is opgebouwd langs drie lagen:

| Laag | Vraag |
|------|-------|
| **Data** | Is de benodigde data beschikbaar en van voldoende kwaliteit? |
| **Functioneel** | Werkt de functionaliteit in de app? |
| **Architectuur** | Is de opzet toekomstbestendig richting dataspace? |

---

## 2. Functionele toetsing

### 2.1 Navigatie & UX

| Onderdeel | Observatie | Impact |
|----------|-----------|--------|
| Gebiedsselectie | Werkt, maar UX is onduidelijk | Hoog |
| Startpunt (kaart vs. thema) | Geen duidelijke gebruikersflow | Hoog |
| Kompas-scope | Onduidelijk wat de Kompas omvat | Hoog |

➡️ **Conclusie:** UX blokkeert effectief gebruik

### 2.2 Data & Duiding

| Onderdeel | Observatie |
|----------|------------|
| Contextuitleg | Z-scores niet uitgelegd voor eindgebruiker |
| Bronvermelding | Ontbreekt per indicator |
| Peildatum | Ontbreekt |

➡️ **Conclusie:** Lage betrouwbaarheid voor beleidsgebruik

### 2.3 Analysefunctionaliteit

| Functionaliteit | Status |
|----------------|--------|
| Benchmarking | ⚠️ Basis aanwezig |
| Trendanalyse | ❌ Ontbreekt |
| Kaartlagen | ✅ Aanwezig |
| Export | ❌ Ontbreekt |
| Tabelweergave | ❌ Ontbreekt |

---

## 3. Gap-analyse per thema

### 3.1 Verkeer & Bereikbaarheid

| Stap | Actie in D-OmniTwin | Verwacht gedrag | Status |
|------|--------------------|----------------|--------|
| 1 | Selecteer Makkum | Gebied visueel actief | ❓ Onzeker |
| 2 | Zoek indicator "afstand OV" | Indicator vindbaar | ⚠️ Niet expliciet |
| 3 | Bekijk kaartlaag | Choropleth bereikbaarheid | ⚠️ Alleen indirect via CBS |
| 4 | Vergelijk met andere kernen | Benchmark zichtbaar | ⚠️ Beperkt |
| 5 | Bekijk trend (5 jaar) | Tijdreeks zichtbaar | ❌ Ontbreekt |

**Bevinding:** Data deels beschikbaar, niet als expliciete indicator. Geen echte bereikbaarheidsanalyse (network-based).

---

### 3.2 Openbare Ruimte

| Stap | Actie | Verwacht | Status |
|------|-------|----------|--------|
| 1 | Zoek "groen onderhoud" | Indicator zichtbaar | ❌ Ontbreekt |
| 2 | Bekijk kaart | Ruimtelijke spreiding | ❌ Ontbreekt |
| 3 | Context bekijken | Uitleg indicator | ⚠️ Beperkt |

**Bevinding:** Groot datagat. Geen koppeling met gemeentelijke bronnen.

---

### 3.3 Wonen

| Stap | Actie | Verwacht | Status |
|------|-------|----------|--------|
| 1 | Selecteer thema Wonen | Kompas zoomt in | ✅ Werkt |
| 2 | Bekijk betaalbaarheid | Indicator aanwezig | ⚠️ Indirect |
| 3 | Vergelijk gebieden | Benchmark | ⚠️ Beperkt |
| 4 | Bekijk historische trend | Tijdlijn | ❌ Ontbreekt |

**Bevinding:** Sterkste onderdeel. Mist beleidsrelevante KPI's (starters, kwaliteit).

---

### 3.4 Rondkomen / Sociaal Domein

| Stap | Actie | Verwacht | Status |
|------|-------|----------|--------|
| 1 | Zoek participatiewet | Indicator zichtbaar | ✅ (CBS) |
| 2 | Bekijk trend | Tijdreeks | ⚠️ Beperkt |
| 3 | Drill-down | Detailniveau kern | ⚠️ Beperkt |

**Bevinding:** Data aanwezig, maar te grof voor vroegsignalering.

---

### 3.5 Gezondheid & Opgroeien

| Indicator | Status |
|-----------|--------|
| Reistijd scholen | ❌ Ontbreekt |
| Sportvoorzieningen | ❌ Ontbreekt |

**Bevinding:** Volledig afwezig. Bevestigt: app is CBS-gedreven, niet domein-gedreven.

---

## 4. Gap-samenvatting

### Data gaps
- Bereikbaarheid (network-based analyse)
- Sociaal domein detaildata (kerniveau)
- Gezondheid / voorzieningen
- Groen & openbare ruimte (gemeentelijke bronnen)

### Functionele gaps
- Trendanalyse / tijdreeksen
- Volledige benchmarking
- Export (PDF, tabel)
- Tabelweergave

### UX gaps
- Gebruikersflow (startpunt onduidelijk)
- Contextuitleg Z-scores
- Bronvermelding & peildatum

### Architectuur gap
- Geen dataspace-integratie
- Volledig ETL-gedreven (geen federatief)

---

## 5. Architectuurtoets

### Huidige realiteit
- Centrale database (PostgreSQL)
- ETL-gedreven
- CBS/RIVM dominant

### Toets t.o.v. gewenste richting (dataspaces)

| Aspect | Huidig | Gewenst |
|-------|-------|--------|
| Data opslag | Gecentraliseerd | Federatief |
| Data toegang | Kopieën (ETL) | API/contract-based |
| Actualiteit | Batch | Near real-time |
| Privacy | Impliciet | Expliciet (iSHARE) |

**Conclusie:** D-OmniTwin is momenteel een **data dashboard**, nog geen dataspace-interface.

---

## 6. Diagnoseconclusie

D-OmniTwin zit op het kantelpunt van:
- Dashboard → beleidsinstrument
- Data-opslag → data-orkestratie

> **Sterktes:** Visualisatie, structuur (Kompas, thema's)
> **Tekortkomingen:** Beleidsrelevante diepgang, data-integratie, gebruikersflow
> **Kritisch inzicht:** De applicatie ondersteunt **verkennen**, maar nog niet **beslissen**.

---

## 7. Gerelateerde documenten

- [TC-01-001 Gebiedsselectie](../01-kaartmodule/TC-01-001_gebieds-selectie.md)
- [TC-02-001 Wonen indicatoren](../02-kompas-detail/TC-02-001_wonen-indicatoren.md)
- [TC-02-002 Sociaal domein](../02-kompas-detail/TC-02-002_sociaal-domein.md)
- [TC-06-001 E2E Beleidsadviseur](../06-integratie-e2e/TC-06-001_beleidsadviseur-ijsselmeerkust.md)
- [Dataspace-mapping indicatoren](../../2-architectuur/dataspace-mapping/dataspace_mapping_indicatoren_ijsselmeerkust.md)

# Nieuwe Indicatoren Mapping

**Datum:** 10-02-2026  
**Gebaseerd op:** BAG Fryslân, EP-Online, Postcodegebieden  
**Doel:** Identificeren van nieuwe indicatoren en koppeling naar Kompas structuur

---

## Overzicht

| Dataset | Aantal Indicatoren | Prioriteit | Kompas Dimensie |
|---------|-------------------|-----------|-----------------|
| EP-Online | 2 (✅ geïmplementeerd) | ZEER HOOG | Wonen → Technische Kwaliteit → Energie |
| BAG Fryslân | 6 geplanned | MEDIUM-HOOG | Wonen → Technische Kwaliteit, Type |
| Postcodegebieden | PC4 aggregaties | MEDIUM | Alle (nieuwe aggregatieniveau) |

---

## 1. EP-Online Energielabels (✅ Geïmplementeerd)

### Indicator 1.1: Gemiddeld energielabel

| Eigenschap | Waarde |
|------------|--------|
| **Naam** | Gemiddeld energielabel |
| **Code** | `gemiddeld_energielabel` |
| **Bron** | RVO EP-Online |
| **Eenheid** | labelklasse (A++++ - G) |
| **Waarde Type** | Numeric (1.0-9.0), display als label |
| **Aggregatie** | AVG(numeric value) per buurt |
| **Interpretatie** | -=- (lager = beter, A++++ is beste) |
| **Kompas Dimensie** | **Wonen** → **Technische Kwaliteit** → **Energie** |
| **Score Type** | **-=-** (negatief georiënteerd) |
| **Prioriteit** | 🔴🔴 ZEER HOOG |
| **Status** | ✅ Actief sinds 09-02-2026 |

**Rationale negatieve scoring (-=-):**
- Hoog label (G = 9.0) = slecht voor leefbaarheid/duurzaamheid
- Laag label (A++++ = 1.0) = goed voor leefbaarheid/duurzaamheid
- Dus: OMGEKEERDE relatie tussen waarde en score

**Kompas Weging:**
- Relatief hoog (0.8) binnen "Technische Kwaliteit" dimensie
- Energie-transitie is prioriteit beleid

### Indicator 1.2: Aantal energielabels

| Eigenschap | Waarde |
|------------|--------|
| **Naam** | Aantal energielabels |
| **Code** | `aantal_energielabels` |
| **Eenheid** | aantal |
| **Interpretatie** | +=+ (meer = betere data coverage) |
| **Kompas Dimensie** | **Metadata / Coverage** (niet in hoofdkompas) |
| **Prioriteit** | 🟡 MEDIUM (hulpindicator) |
| **Status** | ✅ Actief |

**Gebruik:**
- Denominateur voor percentage berekening
- Coverage monitoring per buurt
- Niet direct in Kompas visualization (metadata indicator)

### Indicator 1.3: Percentage met energielabel (Nieuw - Afgeleid)

| Eigenschap | Waarde |
|------------|--------|
| **Naam** | Percentage huishoudens met energielabel |
| **Code** | `pct_energielabel` |
| **Bron** | RVO EP gepOnline (labels) + BAG (huishoudens) |
| **Eenheid** | % |
| **Berekening** | `aantal_energielabels / huishoudens_bag * 100` |
| **Interpretatie** | +=+ (hoger = betere coverage) |
| **Kompas Dimensie** | Wonen → Technische Kwaliteit → Data Kwaliteit |
| **Score Type** | +=+ |
| **Prioriteit** | 🔴 HOOG |
| **Status** | ⏳ Te implementeren (vereist BAG import) |

---

## 2. BAG Fryslân Gebouwkenmerken

### Indicator 2.1: Gemiddeld bouwjaar woningen

| Eigenschap | Waarde |
|------------|--------|
| **Naam** | Gemiddeld bouwjaar woningen |
| **Code** | `gemiddeld_bouwjaar` |
| **Bron** | Kadaster BAG (panden) |
| **Eenheid** | jaar |
| **Aggregatie** | AVG(bouwjaar) van panden per buurt |
| **Interpretatie** | **-/+** (neutraal, context-afhankelijk) |
| **Kompas Dimensie** | **Wonen** → **Technische Kwaliteit** → **Bouwperiode** |
| **Score Type** | **-/+** (geen automatische positief/negatief oordeel) |
| **Prioriteit** | 🔴 HOOG |
| **Status** | ⏳ Gepland (Sprint 5C) |

**Rationale neutrale scoring (-/+):**
- Oude bouw kan charme hebben MAAR energie-inefficiënt
- Nieuwe bouw energie-efficiënt MAAR mogelijk minder karakteristiek
- Laat gebruiker zelf interpreteren (kleur gradient neutraal)

**Visualisatie Advies:**
- Kleurschaal: Blauw (oud, <1945) → Wit (gemiddeld, 1980) → Groen (nieuw, >2010)
- Gebruiker kan zelf prioriteit aangeven (filter op periode)

### Indicator 2.2: Percentage woningen voor 1945

| Eigenschap | Waarde |
|------------|--------|
| **Naam** | Percentage woningen gebouwd vóór 1945 |
| **Code** | `pct_voor_1945` |
| **Bron** | Kadaster BAG (panden) |
| **Eenheid** | % |
| **Berekening** | `COUNT(bouwjaar < 1945) / COUNT(*) * 100` |
| **Interpretatie** | **-=-** (hoger % = meer aandacht energie-renovatie) |
| **Kompas Dimensie** | Wonen → Technische Kwaliteit → Energie-renovatie Potentie |
| **Score Type** | **-=-** |
| **Prioriteit** | 🔴🔴 ZEER HOOG (energie-transitie) |
| **Status** | ⏳ Gepland |

**Rationale:**
- Vooroorlogse bouw: vaak slecht geïsoleerd, single glas, geen spouwmuren
- Hoog % = Hoge prioriteit voor isolatie-subsidies en renovatie
- Koppeling met energielabel: verwachting slechtere labels in buurten met hoog %

### Indicator 2.3: Gemiddelde woonoppervlakte

| Eigenschap | Waarde |
|------------|--------|
| **Naam** | Gemiddelde oppervlakte woningen |
| **Code** | `gemiddelde_woonoppervlakte` |
| **Bron** | Kadaster BAG (verblijfsobjecten) |
| **Eenheid** | m² |
| **Aggregatie** | AVG(oppervlakte) van VBO's per buurt |
| **Interpretatie** | **+=+** (groter = meer ruimte, positief) |
| **Kompas Dimensie** | Wonen → **Ruimte** → Woonoppervlak |
| **Score Type** | +=+ |
| **Prioriteit** | 🟡 MEDIUM |
| **Status** | ⏳ Gepland |

### Indicator 2.4: Percentage woonfunctie

| Eigenschap | Waarde |
|------------|--------|
| **Naam** | Percentage verblijfsobjecten met woonfunctie |
| **Code** | `pct_woonfunctie` |
| **Bron** | Kadaster BAG (verblijfsobjecten) |
| **Eenheid** | % |
| **Berekening** | `COUNT(woonfunctie=true) / COUNT(*) * 100` |
| **Interpretatie** | **-/+** (neutraal, afhankelijk van gewenst karakter) |
| **Kompas Dimensie** | Wonen → **Type** → Functiemix |
| **Score Type** | -/+ |
| **Prioriteit** | 🟡 MEDIUM |
| **Status** | ⏳ Gepland |

**Context:**
- Hoog % (>90%): Zuivere woonwijk
- Middel % (70-90%): Mix wonen en voorzieningen (ideaal?)
- Laag % (<50%): Bedrijventerrein/centrum (niet per se slecht)

### Indicator 2.5: Diversiteit gebruiksfuncties

| Eigenschap | Waarde |
|------------|--------|
| **Naam** | Diversiteit gebruiksfuncties (Shannon Index) |
| **Code** | `diversiteit_functies` |
| **Bron** | Kadaster BAG (verblijfsobjecten) |
| **Eenheid** | index (0-1) |
| **Berekening** | Shannon diversity: `-SUM(p_i * log(p_i))` waarbij p_i = aandeel functie i |
| **Interpretatie** | **+=+** (meer divers = levendiger, menging functies) |
| **Kompas Dimensie** | **Leefbaarheid** → **Voorzieningen** → Functiemix |
| **Score Type** | +=+ |
| **Prioriteit** | 🔴 MEDIUM-HOOG |
| **Status** | ⏳ Gepland |

**Voorbeeld Berekening:**
```
Buurt X: 80% wonen, 15% winkel, 5% kantoor
Shannon = -(0.8*log(0.8) + 0.15*log(0.15) + 0.05*log(0.05)) = 0.61

Buurt Y: 100% wonen
Shannon = -(1.0*log(1.0)) = 0.00

→ Buurt X is diverser (score 0.61 vs 0.00)
```

### Indicator 2.6: Aantal woonboten en woonwagens (per 1000 huishoudens)

| Eigenschap | Waarde |
|------------|--------|
| **Naam** | Woonboten en woonwagens per 1000 huishoudens |
| **Code** | `woonvormen_alternatief` |
| **Bron** | Kadaster BAG (ligplaatsen + standplaatsen) |
| **Eenheid** | per 1000 |
| **Berekening** | `(COUNT(ligplaats) + COUNT(standplaats)) / huishoudens * 1000` |
| **Interpretatie** | **-/+** (neutraal, culturele diversiteit) |
| **Kompas Dimensie** | Wonen → Type → Alternatieve woonvormen |
| **Score Type** | -/+ |
| **Prioriteit** | 🟢 LAAG (niche indicator) |
| **Status** | ⏳ Gepland (optioneel) |

---

## 3. PC4 Postcode Aggregaties (Nieuw Niveau)

### Concept: PC4 als Aggregatieniveau

**Rationale:**
- CBS buurten soms te klein voor regionale patronen
- PC4 niveau overschrijdt soms gemeentegrenzen (nuttig voor cross-gemeente analyses)
- EP-Online data direct koppelbaar via PC6 → PC4 (zonder buurt tussenlaag)

### Implementatie

**Stap 1:** Voeg PC4 toe als gebiedstype
```sql
INSERT INTO gebiedstypes (id, naam, niveau)
VALUES ('PC4', 'Postcode 4-cijfers', 3);
-- Niveau 3 = tussen buurt (4) en gemeente (2)
```

**Stap 2:** Aggregeer bestaande indicatoren naar PC4
```sql
-- Voorbeeld: Gemiddeld energielabel per PC4
INSERT INTO gebied_data (gebied_id, indicator_uuid, waarde, jaar, bron)
SELECT 
  pc4.id AS gebied_id,
  i.uuid AS indicator_uuid,
  AVG(gd.waarde) AS waarde,
  2025 AS jaar,
  'Aggregatie buurt → PC4' AS bron
FROM gebieden pc4
JOIN gebieden buurt ON ST_Intersects(buurt.centroid, pc4.geometry)
JOIN gebied_data gd ON gd.gebied_id = buurt.id
JOIN indicatoren i ON i.uuid = gd.indicator_uuid
WHERE pc4.gebiedstype_id = 'PC4'
  AND buurt.gebiedstype_id = 'BU'
  AND i.code = 'gemiddeld_energielabel'
GROUP BY pc4.id, i.uuid;
```

**Stap 3:** Frontend dropdown uitbreiden
```javascript
// Gebied selectie dropdown
<select id="gebiedstype">
  <option value="GM">Gemeente</option>
  <option value="WK">Wijk</option>
  <option value="BU" selected>Buurt</option>
  <option value="PC4">Postcode (PC4)</option> <!-- NIEUW -->
</select>
```

---

## Kompas Integratie Overzicht

### Nieuwe Dimensies/Sub-dimensies

**Wonen → Technische Kwaliteit:**
```
Technische Kwaliteit (bestaand)
├── Energie (🆕 nieuw)
│   ├── Gemiddeld energielabel (🆕)
│   ├── % huishoudens met label (🆕)
│   └── Energie-renovatie potentie
│       └── % woningen voor 1945 (🆕)
├── Bouwperiode (🆕 nieuw)
│   └── Gemiddeld bouwjaar (🆕)
└── Data Kwaliteit (nieuw, metadata)
    └── % met energielabel (🆕)
```

**Wonen → Ruimte:**
```
Ruimte (bestaand)
└── Woonoppervlak (🆕 nieuw)
    └── Gemiddelde woonoppervlakte (🆕)
```

**Wonen → Type:**
```
Type (bestaand)
├── Functiemix (🆕 nieuw)
│   └── % woonfunctie (🆕)
└── Alternatieve woonvormen (🆕 nieuw)
    └── Woonboten/woonwagens per 1000 (🆕)
```

**Leefbaarheid → Voorzieningen:**
```
Voorzieningen (bestaand)
└── Functiemix (🆕 nieuw)
    └── Diversiteit gebruiksfuncties (🆕)
```

### Kompas Configuratie (Beheerscherm Acties)

**Sprint 5C - Beheerscherm Invoer:**

1. **Nieuwe dimensies aanmaken:**
   - Energie (onder Technische Kwaliteit)
   - Bouwperiode (onder Technische Kwaliteit)
   - Woonoppervlak (onder Ruimte)
   - etc.

2. **Indicatoren koppelen:**
   - Gebruik Admin Panel "Indicator Beheer"
   - Per indicator: selecteer Kompas dimensie via dropdown
   - Stel score type in (-=-, +=+, -/+)

3. **Weging bepalen:**
   - Binnen "Technische Kwaliteit":
     - Energie: 40% (hoge prioriteit transitie)
     - Bouwperiode: 30%
     - Overig (WOZ, staat): 30%

---

## Prioritering Implementatie

### Sprint 5C (Week 9) - HOOG PRIORITEIT
1. ✅ EP-Online (voltooid)
2. 🔴 **% woningen voor 1945** (energie-transitie urgentie)
3. 🔴 **Gemiddeld bouwjaar**
4. 🔴 **Diversiteit gebruiksfuncties** (leefbaarheid)

### Sprint 6 (Week 10) - MEDIUM PRIORITEIT
5. 🟡 Gemiddelde woonoppervlakte
6. 🟡 % woonfunctie
7. 🟡 PC4 aggregatieniveau implementatie

### Sprint 7+ (Toekomst) - LAAG PRIORITEIT
8. 🟢 Woonboten/woonwagens indicator

---

## Validatie & Testing

### Indicator Validatie Checklist

Voor elke nieuwe indicator:
- [ ] **Data range check:** Waarden binnen verwacht bereik?
- [ ] **Coverage check:** Hoeveel gebieden hebben data? (target: >90%)
- [ ] **Sanity check:** Vergelijk met bekende waardes (bv. energie-inefficiënte buurten hebben inderdaad hoog % voor-1945)
- [ ] **Kompas visual:** Test sunburst chart met nieuwe indicator
- [ ] **Kaart kleuring:** Test color scale op kaart (gradient logisch?)

### Cross-Indicator Correlatie (Verwacht)

**Verwachte correlaties:**
- **Positief:** Gemiddeld bouwjaar ↔ Gemiddeld energielabel (nieuwer = beter label)
- **Negatief:** % voor 1945 ↔ Gemiddeld energielabel (oud = slechter label)
- **Neutraal:** Diversiteit functies ↔ Bouwjaar (geen sterke relatie verwacht)

**Validatie Query:**
```sql
-- Check correlatie bouwjaar vs energielabel
SELECT 
  CORR(bouwjaar.waarde, energielabel.waarde) AS correlatie_coefficient
FROM gebied_data bouwjaar
JOIN gebied_data energielabel ON energielabel.gebied_id = bouwjaar.gebied_id
JOIN indicatoren i1 ON i1.uuid = bouwjaar.indicator_uuid AND i1.code = 'gemiddeld_bouwjaar'
JOIN indicatoren i2 ON i2.uuid = energielabel.indicator_uuid AND i2.code = 'gemiddeld_energielabel';
-- Verwacht: negatieve correlatie (~-0.6, nieuwer = lager label nummer)
```

---

**Document Versie:** 1.0  
**Laatste Update:** 10-02-2026  
**Next Action:** Implementeer Sprint 5C indicatoren via Admin Panel

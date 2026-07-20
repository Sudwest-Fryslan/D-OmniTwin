# 📊 Indicatoren Bronvergelijking: Excel vs. D-OmniTwin Database

**Rapport datum:** 20 juli 2026
**Bron:** `data/sociaaldomein/Indicatoren gemeenteniveau met metadata voor gezonde leefomgeving.xlsx`
**Tabblad:** `Alle indicatoren per regionivea`

---

## 🔢 Totaaloverzicht

| Metric | Aantal |
|--------|--------|
| **Totaal rijen in Excel** | 12.366 |
| **Unieke indicatoren (alle niveaus)** | 812 |
| **Reeds aanwezig in D-OmniTwin mapping** | 11 |
| **Ontbrekend in D-OmniTwin** | **801** |
| **Dekkingsgraad** | **1,4%** |

> [!WARNING]
> We dekken momenteel slechts **11 van de 812 indicatoren** uit deze bron. Dit is het startpunt van de data-verrijkingscampagne.

---

## 📂 Thema's & Verdeling

| Thema | Totaal uniek | Reeds aanwezig | Ontbrekend |
|-------|-------------|----------------|------------|
| Bevolking | 42 | 2 | 40 |
| Gezondheid | 331 | 2 | 329 |
| Meanskip | 2 | 0 | 2 |
| Omgeving | 63 | 0 | 63 |
| Onderwijs | 14 | 3 | 11 |
| Rondkomen | 197 | 2 | 195 |
| Veiligheid | 7 | 0 | 7 |
| Verkeer | 9 | 2 | 7 |
| Voorzieningen | 57 | 3 | 54 |
| Werk | 22 | 3 | 19 |
| Wonen | 43 | 1 | 42 |
| Zorg | 32 | 0 | 32 |

**Aanwezige indicatoren (11):**
- *Bevolking:* 0-15 jaar, 65 jaar of ouder
- *Gezondheid:* Overgewicht, Eenzaam
- *Onderwijs:* Afstand tot school, Bevolkingsdichtheid
- *Rondkomen:* Huishoudens met een laag inkomen, Moeite met rondkomen
- *Verkeer:* Personenauto's per huishouden
- *Voorzieningen:* Afstand tot huisartsenpraktijk, Afstand tot grote supermarkt
- *Wonen:* Koopwoningen

> [!NOTE]
> De mapping-matching is op exacte naam. Sommige indicatoren zitten mogelijk al in de DB onder een iets andere naam. Dit verfijnen we in Stap 2.

---

## 🗺️ Geografische Niveaus in het Excel

| Niveau | Indicatoren | Status in D-OmniTwin |
|--------|------------|---------------------|
| **Buurt** | 441 | ✅ Geometrie aanwezig (CBS buurten) |
| **Wijk** | 584 | ⬇️ Geometrie ophalen via PDOK (FR, GR, DR) |
| **Gemeente** | 811 | ⬇️ Geometrie ophalen via PDOK (FR, GR, DR) |
| **Provincie** | 345 | 🧮 Berekend (aggregatie vanuit buurt/wijk) |
| **Land** | 693 | 🌐 On-demand via CBS OData |

> [!IMPORTANT]
> **Niet alle indicatoren bestaan op alle niveaus.** Gezondheidsdata (RIVM/GGD) is beschikbaar op buurt t/m gemeente, maar CBS Doodsoorzaken-data alleen op gemeente/provincie/land.

---

## 🔌 Databronnen & CBS Dataset IDs

### Bronverdeling (per rij in het Excel)

| Bron | Rijen | % |
|------|-------|---|
| CBS | 11.773 | 95,2% |
| RIVM | 248 | 2,0% |
| GGD | 154 | 1,2% |
| Vektis | 139 | 1,1% |
| Suite | 27 | 0,2% |
| Politie | 16 | 0,1% |
| JM | 9 | 0,1% |

### Indicatoren per bron per niveau

| Bron | Buurt | Wijk | Gemeente |
|------|-------|------|----------|
| CBS | 606 | 655 | 3.663 |
| RIVM | 62 | 62 | 62 |
| GGD | — | 77 | 77 |
| Vektis | 9 | 50 | 50 |
| Suite | 9 | 9 | 9 |
| Politie | 4 | 4 | 4 |

### CBS Dataset IDs (70 uniek)

```
20233NED  47018NED  47024NED  50121NED  50143NED  50150NED
82339NED  82931NED  83173NED  83220NED  83487NED  83502NED
83577NED  83749NED  83759NED  83765NED  83782NED  84286NED
84316NED  84334NED  84417NED  84463NED  84521NED  84583NED
84615NED  84692NED  84718NED  84751NED  84752NED  84753NED
84799NED  84856NED  84897NED  84908NED  84953NED  85039NED
85042NED  85047NED  85075NED  85118NED  85175NED  85217NED
85231NED  85317NED  85318NED  85335NED  85377NED  85485NED
85560NED  85586NED  85618NED  85639NED  85685NED  85814NED
85830NED  85984NED  85990NED  85996NED  86003NED  86089NED
86092NED  86113NED  86131NED  86132NED  86134NED  86157NED
86165NED  86202NED  86204NED  86258NED
```

---

## 🎯 Observaties & Aandachtspunten

1. **Gezondheid is verreweg het grootste thema** (331 indicatoren). Dit bevat CBS Doodsoorzaken data (ICD-hoofdgroepen), RIVM leefstijl-data, en GGD gezondheidsmonitor-data. Dit is een enorme verrijking voor het Kompas.

2. **Rondkomen is het op-een-na-grootste** (197 indicatoren). Veel granulaire CBS inkomens- en vermogensdata op buurt/wijkniveau.

3. **Niet-CBS bronnen (GGD, Vektis, Politie, Suite, JM):** Deze zijn niet via onze huidige `run_etl.py` op te halen. Hier is extra ontwikkelwerk nodig (specifieke connectors of handmatige import).

4. **70 unieke CBS dataset IDs:** Onze huidige mapping gebruikt impliciet 2-3 datasets. De sprong naar 70 is significant maar haalbaar — de CBS OData API is gestandaardiseerd.

5. **Negatief/Positief scoring:** Het Excel bevat een `Negatief_Positief` kolom (0 of 1). Dit correleert direct met onze `score_type` in de `indicatoren` tabel. Zeer waardevol voor de Kompas-scoring.

---

## ⏭️ Vervolgstap

Dit rapport wordt aangevuld in **Stap 2** met:
- Per ontbrekende indicator: gevalideerde CBS/RIVM dataset ID en kolomnaam
- Per indicator: op welke niveaus de data beschikbaar én ophaalbaar is
- De voorgestelde aanpassing aan `cbs_mapping_v3.json`

Na aanvulling wordt dit rapport voorgelegd voor **go/no-go** (de Reviewpoort).

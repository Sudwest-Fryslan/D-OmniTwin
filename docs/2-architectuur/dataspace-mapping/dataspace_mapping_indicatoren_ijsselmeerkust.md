# Dataspace Mapping — Indicatoren IJsselmeerkust & Wadden

**Type:** Architectuurverkenning
**Datum:** 2026-04-09
**Afgeleid van:** NM-001 IJsselmeerkust gap-analyse (§10–14)
**Status:** Concept

---

## Doel

Dit document maakt expliciet:
- Waar data zich bevindt (bron)
- Hoe data ontsloten wordt (huidig vs. gewenst)
- Wat ontbreekt richting beleidsgebruik

---

## 1. Mapping per indicator

### 1.1 Verkeer & Bereikbaarheid

| Indicator | Bron | Toegang (huidig) | Toegang (gewenst) | Gap |
|----------|------|------------------|-------------------|-----|
| Afstand tot treinstation | CBS / NDOV / OpenStreetMap | ETL (geodata) | Federatief (API + routing service) | Geen network-based analyse |
| OV gebruik (groei) | CBS | ETL | Dataspace (FDS / mobiliteit) | Actualiteit ontbreekt |
| Fietspaden (km) | Gemeente | Niet ontsloten | FRLDS (gemeentelijke bron) | Data niet gekoppeld |
| Autoinbraken | Politie (open data) | ETL | Federatief (veiligheids-dataspace) | Detailniveau beperkt |

---

### 1.2 Openbare Ruimte

| Indicator | Bron | Toegang (huidig) | Toegang (gewenst) | Gap |
|----------|------|------------------|-------------------|-----|
| Afstand tot speelplek | Gemeente (BOR) | Niet ontsloten | FRLDS | Geen data-integratie |
| Klachten groen | Gemeente (meldsysteem) | Niet ontsloten | FRLDS | Geen koppeling |

➡️ Volledig afhankelijk van gemeentelijke systemen — alleen via dataspace schaalbaar te ontsluiten.

---

### 1.3 Wonen

| Indicator | Bron | Toegang (huidig) | Toegang (gewenst) | Gap |
|----------|------|------------------|-------------------|-----|
| Betaalbare woningen | CBS / Kadaster | ETL | Hybride | Definitie mismatch |
| Woningkwaliteit | Gemeente / corporaties | Niet ontsloten | FRLDS | Data versnipperd |
| Starterswoningen | Gemeente | Niet ontsloten | FRLDS | KPI ontbreekt |

---

### 1.4 Rondkomen / Sociaal Domein

| Indicator | Bron | Toegang (huidig) | Toegang (gewenst) | Gap |
|----------|------|------------------|-------------------|-----|
| Participatiewet | CBS | ETL | Federatief (CBS API / FDS) | Te grofmazig |
| Circulaire landbouw | Provincie / sector | Niet ontsloten | Dataspace (agrarisch) | Geen standaard |
| Toerisme initiatieven | Gemeente / ondernemers | Niet ontsloten | Publiek-private dataspace | Geen structuur |

---

### 1.5 Gezondheid & Opgroeien

| Indicator | Bron | Toegang (huidig) | Toegang (gewenst) | Gap |
|----------|------|------------------|-------------------|-----|
| Reistijd school | DUO / routing data | Niet ontsloten | Federatief | Ontbreekt volledig |
| Sportvoorzieningen | Gemeente / sportbonden | Niet ontsloten | FRLDS | Geen integratie |

---

## 2. Bronstypologie

| Type bron | Voorbeeld | Dataspace |
|----------|----------|-----------| 
| Nationaal | CBS | FDS |
| Regionaal | Gemeente SWF | FRLDS |
| Domein | Zorg / mobiliteit | Domein dataspace |
| Privaat | Agrariërs / toerisme | Publiek-private dataspace |

---

## 3. Huidig vs. gewenste ontsluiting

| Aspect | Huidig (D-OmniTwin) | Gewenst |
|-------|--------------------|--------|
| Data integratie | ETL | Federatief |
| Opslag | Centraal | Bij bron |
| Updates | Batch | Real-time / near real-time |
| Governance | Impliciet | Contract-based |

---

## 4. Benodigde architectuurcomponenten

Om D-OmniTwin te laten functioneren als dataspace-interface zijn de volgende componenten nodig:

- **Dataspace router** — orkestratie van meerdere dataspaces
- **iSHARE / IDS connector** — authenticatie & contractbeheer
- **Policy engine** — data-gebruiksbeleid afdwingen
- **Federatieve query layer** — query over meerdere bronnen

### Nieuwe rol database

| Huidig | Gewenst |
|--------|---------|
| Primaire databron | Cache / performance layer |

---

## 5. Roadmap-implicaties

### Fase 1 — Korte termijn
- CBS data via API ontsluiten (minder ETL)
- Basis indicatoren expliciet benoemen in UI
- Tabel + export toevoegen

### Fase 2 — Middellange termijn
- Koppeling met gemeentelijke bronnen (FRLDS light)
- Pilot met 1 dataspace (bijv. sociaal domein SWF)

### Fase 3 — Lange termijn
- Volwaardige dataspace-integratie
- Multi-dataspace orchestration
- AI-RAG over meerdere federatieve bronnen

---

## 6. Eindconclusie

> Het probleem is niet alleen dat data ontbreekt — het zit in de **manier waarop data ontsloten wordt**.

Oplossingsrichting:
- ❌ Niet: meer ETL bouwen
- ✅ Maar: dataspace-integratie realiseren

Dit vormt de directe brug tussen de testcase-bevindingen, de FRLDS-visie en de technische roadmap van D-OmniTwin.

---

## 7. Gerelateerde documenten

- [NM-001 Gap-analyse IJsselmeerkust](../../7-projectmanagement/testcases/nulmetingen/NM-001_ijsselmeerkust-gap-analyse.md)
- [Fryslân Data Space Visiedocument](./architecture/fryslan_data_space_d_omni_twin_visiedocument.md)
- [FRLDS Herijkt Visiedocument](./architecture/frlds_in_dataspace_landschap_herijkt_visiedocument.md)

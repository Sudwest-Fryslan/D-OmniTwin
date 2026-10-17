# Integrale Gebruikerservaring-Audit (Epic #309)

**Datum:** 2026-10-16  
**Status:** Uitgevoerd & Vastgesteld  
**Auteur/Reviewer:** AI Pair Programmer & Product Owner (T. Laan)  
**Koppeling:** [Epic #309](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/309) · Sub-issue [#441](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/441) · [ADR 0011 Toegankelijkheid](../2-architectuur/adr/0011-toegankelijkheid-wcag.md)

---

## 1. Doel & Scope

In het kader van **Epic #309** is een integrale cognitive walkthrough en heuristische audit uitgevoerd op de actieve D-OmniTwin applicatie (versie 0.6.0). Hierbij zijn alle kerninterfaces zowel via code-inspectie als live visuele controles (met headless browser-automatisering) getoetst:

1. **Startscherm, onboarding en tutorial**
2. **Kaart- en bedieningsinteracties** (MapLibre GL / Deck.gl)
3. **D-Omni Kompas & indicatorpaneel** (12 thematische kwadranten)
4. **D-Omni Assistent** (Rule-based & AI-chat)
5. **Rapportages en dashboards** (Gebiedsdossiers, benchmark, multi-gebied)
6. **Functioneel beheer** (Admin-panel SPA)

De beoordeling is verricht vanuit vijf sleutelpersona's en getoetst aan de **WCAG 2.1 AA** richtlijnen (DigiToegankelijk).

---

## 2. Visuele & Functionele Bevindingen per Kernonderdeel

### 2.1 Startscherm & Onboarding
- **Wat goed werkt:**
  - De applicatie verwelkomt een nieuwe bezoeker met een strakke, eigentijdse modal (*"Welkom bij D-OmniTwin — Een beslisondersteunend platform voor gebiedsanalyse in Fryslân"*).
  - De driedeling (*1. Kies gemeente*, *2. Kies indicator*, *3. Bekijk het Kompas*) schept direct conceptuele helderheid.
  - Sneltoetsen (*"Kaart verkennen"*, *"Kompas begrijpen"*, *"Handleiding"*, *"Overslaan"*) geven de gebruiker directe controle over de instap.
- **Frictie & Verbeterpunten:**
  - Na het sluiten van de welkomstmodal is de kaart leeg (donkere achtergrondkaart met wegennet en provinciegrenzen) zonder dat er automatisch een startbuurt of themalaag oplicht. De gebruiker moet zelf bedenken welk icoon in de linker zijbalk moet worden aangeklikt.
  - De linker icoonbalk (9 pictogrammen) heeft geen tekstlabels in ruststand; pas bij hover verschijnt een tooltip. Voor minder frequente gebruikers zorgt dit voor een zoekdrempel.
- **Aanbeveling:**
  - Voeg een initiële selectie van de hoofdplaats/hoofdgemeente toe bij de eerste start, zodat de kaart direct "leeft".
  - Bied optioneel uitklapbare tekstlabels aan naast de iconen in de linker navigatiebalk.

---

### 2.2 Kaart- en Bedieningsinteracties
- **Wat goed werkt:**
  - Hoge rendering-snelheid via MapLibre GL en Deck.gl. Vector-tegels en gebiedsgrenzen laden soepel zonder merkbare haperingen.
  - Geselecteerde filters (zoals `📍 Gemeente: Súdwest-Fryslân ✕`) worden als duidelijke chips bovenin de kaart getoond en zijn met één klik te verwijderen.
- **Frictie & Verbeterpunten:**
  - Wanneer er nog geen indicator is gekozen, ontbreekt een kaartlegenda. De gebruiker ziet alleen wegen en donkere vlakken zonder context over wat de vlakken voorstellen.
  - Klikken op de kaart vereist precisie: op mobiele apparaten of laptops zonder muis kan het lastig zijn een kleine binnenstadsbuurt (zoals Sneek binnen de grachten) te selecteren.
- **Aanbeveling:**
  - Toon een subtiele zoomaanwijzing of zwevende zoekwidget ("Zoek buurt of postcode") direct op de kaart om navigatie zonder muisklik te versnellen.

---

### 2.3 D-Omni Kompas & Indicatorpaneel
- **Wat goed werkt:**
  - Het Kompas brengt 235 indicatoren overzichtelijk onder in 12 herkenbare kwadranten (kwaliteit leefomgeving, sociaal domein, voorzieningen, etc.).
  - De configuratieschakelaar (bijv. "Volledig Kompas") biedt flexibiliteit.
  - Detailpaneel toont bij doorklikken een trendgrafiek over meerdere meetjaren en een tijdlijn-slider.
- **Frictie & Visuele Bevindingen (Live Audit):**
  - **Zwevende modal overlapt de kaart:** `#kompas-window` opent gecentreerd over de kaart, waardoor de geselecteerde buurt volledig aan het zicht wordt onttrokken.
  - **Foutmelding bij indicator-activatie vanuit Kompas:** Wanneer een gebruiker op een blad-indicator klikt in het Kompas, roept `kompas.js` `syncIndicatorToMap` aan, maar geeft de kaart direct de foutmelding `⚠️ Selecteer eerst een gebiedstype` als er nog geen gebiedstype (buurten/wijken) actief was geselecteerd.
  - **Eenzijdige synchronisatie bij gesloten Kompas:** Als een indicator op de kaart of in het linkerpaneel wordt geactiveerd terwijl het Kompas gesloten is, negeert het Kompas het event. Bij later handmatig openen staat het Kompas weer in de algemene stand zonder focus op de actieve indicator.
- **Vastgestelde Oplossingen & Besluiten (via `/grill-me`):**
  1. **Docked / Zijpaneel vs. Zwevende Modus:** Toevoegen van een weergave-schakelaar. In gedockte modus schuift het Kompas in als zijpaneel naast de kaart (split-view), zodat kaart en sunburst gelijktijdig zichtbaar zijn en synchroon reageren. De zwevende pop-out blijft beschikbaar voor 'deep dives' op grote schermen.
  2. **Volledige tweerichtingssynchronisatie:**
     - *Kompas ➔ Kaart:* Klik op een indicator in het Kompas selecteert automatisch het schaalniveau `CBS_BUURT` indien nog geen gebiedstype actief was, en laadt direct de choropleet op de kaart.
     - *Kaart/Paneel ➔ Kompas:* Een indicator activeren navigeert en zoomt direct het Kompas naar de betreffende taartpunt/subthema en opent de details. Als het Kompas gesloten is en later geopend wordt, opent het direct gefocust op de actieve indicator.

---

### 2.4 D-Omni Assistent (Chat)
- **Wat goed werkt:**
  - Snelle responsiviteit door regelgebaseerde intentieclassificatie voor standaardvragen.
  - Lokale privacy-vriendelijke AI-narratieven (Ollama/Qwen) vallen netjes terug als het taalmodel offline staat (`ai_uit`).
- **Frictie & Verbeterpunten:**
  - Gebruikers weten vaak niet wat ze de assistent kunnen vragen. Hoewel er suggesties zijn, ontbreekt feedback over welke commando's de kaart daadwerkelijk kunnen aansturen.
- **Aanbeveling:**
  - Maak interactieve "prompt chips" die met één klik direct een actie op de kaart uitvoeren (bijv. *"Toon buurten met laagste energielabels"*).

---

### 2.5 Rapportages en Dashboards (Gebiedsdossiers)
- **Status:** **Hoogste prioriteit voor herontwerp — Sub-issue #441**.
- **Wat goed werkt:**
  - De backend berekent betrouwbare Z-scores en uitschieters via SQL (`08_zscore_referentie.sql`) met correcte uitsluiting van waterbuurten en minimum-n bewaking.
  - De PDF-export knop en afdrukmodus zijn technisch aanwezig.
- **Frictie & Verbeterpunten:**
  - **Droge cijfertabel:** Het huidige rapport (`/rapport/:gebied_id`) toont een technische tabel met z-score getallen (`+10.91`, `+8.16`) zonder visuele benchmark of grafiek.
  - **Geen gemeentelijk overzicht in 1 oogopslag:** Er ontbreekt een gestapelde staafgrafiek waarin zichtbaar is hoe de geselecteerde buurt zich verhoudt tot de andere buurten in de gemeente.
  - **Gebrek aan context:** Kerncijfers (aantal inwoners, huishoudens, woningen) en de fysieke bouwperiode (BAG) ontbreken in de hero-sectie.
  - **Verouderde subheader:** De header toont de ruwe code `BU19000101` in plaats van de begrijpelijke naam *"Sneek binnen de grachten"*.
- **Vastgestelde Oplossingen & Blauwdruk (#441, via `/grill-me`):**
  1. **Directe instap / Transitiemoment:** Directe actieknop ("Open Factsheet") in de actieve buurt-tooltip/kaart én in de topnavigatie zodra een buurt actief is.
  2. **Meervoudige Factsheets conform bestaande sjablonen:** Niet 1 generieke factsheet, maar meervoudige factsheet-types aansluitend op de 5 bestaande D-OmniTwin rapportagesjablonen:
     - *Type 1: Buurtfactsheet (WBM buurtniveau, Sjabloon B / ReportPage):* Hero met rangorde ("Rang 5 van 72"), context-KPI's, thematische benchmarkbalken en BAG-bouwperiodes.
     - *Type 2: Gemeentebrede Top-grafiek & Ranglijst (Sjabloon D / MultiGebiedPage):* Gestapelde balken per buurt opgebouwd uit de thematische deelscores.
     - *Type 3: Benchmark Factsheet (Sjabloon C / BenchmarkPage):* 1-op-1 of 1-op-n vergelijking met deltabalken t.o.v. gemeentegemiddelde.
     - *Type 4: Thema-Factsheet (Sjabloon E / ThemaAnalysePage):* Diepte-analyse voor één specifiek thema/onderdeel over buurten heen.
     - *Type 5: Woonplaats- & Deelgebiedsanalyse (Sjabloon F / DeelgebiedPage):* Gewogen stadsanalyse voor hele dorpen/steden (Sneek, Bolsward).
  3. **Visuele Benchmarkbalken (WBM & WCAG 2.1 AA):**
     - Horizontale benchmarkbalken per indicator gegroepeerd per Kompas-kwadrant met het gemeentelijk of provinciaal gemiddelde als vaste verticale referentielijn.
     - Duidelijke tekstlabels en werkelijke eenheden (geen uitsluitende afhankelijkheid van kleur).
     - Trendline-integratie: tonen van trendlijnen / sparklines of trendindicatie (↗ ↘ ➔) conform het Kompas detailpaneel wanneer er meerdere meetjaren zijn.

---

### 2.6 Functioneel Beheer (Admin Panel)
- **Wat goed werkt:**
  - Het dashboard (`/admin`) geeft in één oogopslag inzicht in datakwaliteit: *Totaal Indicatoren (241)*, *Data Dekking (36.9%)*, *Metadata Voltooid (71.9%)* en *Trending (34)*.
  - Kleurrijke voortgangsbalken per Kompas-kwadrant (fysiek 37.5%, sociaal 20.8%, leven 25.9%, samenstelling 54.5%).
  - Heldere AI-ontologie statusbalk (Draft, AI Beoordeeld, Goedgekeurd, Herstel).
- **Frictie & Verbeterpunten:**
  - Het dashboard is sterk data-georiënteerd, maar biedt beheerders weinig handelingsperspectief over *welke* ontbrekende indicator het eerst moet worden aangevuld.
- **Aanbeveling:**
  - Voeg een actielijst toe ("Aanbevolen acties voor vandaag"): bijv. *"38 indicatoren wachten op beoordeling"* met directe doorkliklink.

---

## 3. Toetsing aan Persona's

| Persona | Behoefte | Huidige Ervaring | Verbetering via Audit / #441 |
|---------|----------|------------------|------------------------------|
| **Bestuurder / Raadslid** | Snelle kernboodschap, rangorde, geen jargon | ⚠️ Ziet losse Z-scores; mist "is dit goed of slecht?" | Hero-factsheet met rangorde ("5 van 72") en samenvattende urgentiescore (#441) |
| **Beleidsadviseur** | Thematische duiding, vergelijking met gemeentegemiddelde | ⚠️ Moet zelf getallen interpreteren | Horizontale benchmarkbalken met gemeentegemiddelde als referentielijn |
| **Inwoner / Burger** | Laagdrempeligheid, duidelijke taal | ❌ Hoge drempel door technische vaktermen | Verhalende duiding, contextuele uitleg en duidelijke legenda |
| **Data-analist** | Diepgang, databronnen, lineage, filters | ✅ Zeer tevreden over Z-score methodiek en metadata | Behoud van gedetailleerde datapunten onder de visualisaties |
| **Functioneel Beheerder** | Grip op compleetheid, use cases en AI-status | ✅ Goed dashboard met dekkingsgraden | Actiegerichte to-do lijst toevoegen op het beheerpaneel |

---

## 4. Toegankelijkheid (WCAG 2.1 AA — ADR 0011)

1. **Kleurcontrast:**
   - De donkere modus met Inter-typografie en bordeauxrode accentkleur haalt ruimschoots het contrastminimum (4.5:1) voor tekst en knoppen.
2. **Kleuronafhankelijkheid:**
   - In rapporten mag status nooit *alleen* via groen/rood worden getoond. Er moeten altijd tekens (`+` / `-`), labels (*bovengemiddeld* / *ondergemiddeld*) en getalwaarden bij staan.
3. **Toetsenbord- en schermlezerbediening:**
   - Alle modale vensters (zoals het welkomstscherm) vangen de focus netjes op en sluiten met `Escape`.
   - Kaartlagen (WebGL canvas) moeten vergezeld blijven van tekstalternatieven (indicatorpaneel en datatabellen).

---

## 5. Visuele Bewijslast (Live Screenshots)

| Scherm / Onderdeel | Context | GitHub Asset |
|--------------------|---------|--------------|
| **Startscherm** | 3-stappen onboarding modal | ![Onboarding](https://github.com/user-attachments/assets/5ad25d84-3d6a-418f-b22c-fe3f5d7f20b6) |
| **Kaart & Zijbalk** | Viewer navigatie en iconen | ![Kaart](https://github.com/user-attachments/assets/ede69f95-f792-486a-9959-b6b8818d5888) |
| **Buurtselectie** | Geselecteerde buurt met filterchips | ![Selectie](https://github.com/user-attachments/assets/13b4a28e-24db-423d-a096-5e877860ee84) |
| **Kompas Sunburst** | 12 kwadranten (293 slices) | ![Kompas](https://github.com/user-attachments/assets/49518b8c-e3d2-44c9-a785-fc0177307637) |
| **Kompas Drilldown** | Subthema's, broodkruimel & details | ![Kompas Detail](https://github.com/user-attachments/assets/5521bf92-2d87-404f-a31b-738974ba3509) |
| **Kaart-Sync Fout** | Foutmelding bij indicator-activatie | ![Foutmelding](https://github.com/user-attachments/assets/f16a3157-27e1-4409-9d8f-1a0ac230ad44) |
| **Huidig Rapport** | Droge Z-score tabel (Sneek) | ![Huidig Rapport](https://github.com/user-attachments/assets/53910c25-5973-491f-b783-4d5317ec4a74) |
| **Beheerpaneel** | Dashboard datakwaliteit & AI-status | ![Beheer](https://github.com/user-attachments/assets/b5d0e57b-5b4e-44f6-a2ba-36ef17b5abb1) |

---

## 6. Conclusie & Sub-issues onder Epic #309

De auditbevindingen zijn conform de #305-vorm uitgesplitst naar zes afzonderlijke, behapbare sub-issues met het label `UX`. Zodra deze zes sub-issues zijn gerealiseerd en gemerged naar `main`, kan Epic #309 formeel worden gesloten:

1. **[#441](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/441) — Factsheet- en rapportageredesign conform WBM/Buurtbarometer** (§5 Rapportages & Dashboards):
   - Redesign van de factsheets naar het WBM/Twentse Buurtbarometer model.
   - Gemeentelijke rangorde ("Rang 5 van 72"), thematische benchmarkbalken met gemeentegemiddelde als verticale referentielijn, trendline-indicatie en BAG-bouwperiodes.
2. **[#442](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/442) — Interactieve rondleiding (tutorial) en herhaalbare instaphulp** (§1 Startscherm & Onboarding):
   - Permanente herstartknop (`?`) in de navigatie om de rondleiding altijd te kunnen herhalen.
   - 4-staps interactieve spotlight tour (Kaart ➔ Indicatoren ➔ Kompas ➔ Factsheet/Assistent).
   - Rol-gestuurde instap (Inwoner: buurt zoeken vs. Adviseur/Raad: gebiedsanalyse).
3. **[#443](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/443) — Startkaart met automatische gebiedsfocus en actieve startindicator** (§1 Onboarding & §2 Kaartinteracties):
   - Automatische startfocus op de organisatie-gemeente (`standaard_gemeente_code`).
   - Directe activering van een representatieve kernindicator met legenda (voorkomt lege donkere startkaart).
   - Uitklapbare tekstlabels voor de linker navigatiebalk.
4. **[#444](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/444) — Tweerichtingssynchronisatie en docked split-view voor Kompas en Kaart** (§2 Kaartinteracties & §3 D-Omni Kompas):
   - Weergave-schakelaar: Docked zijpaneel (split-view) naast de kaart vs. Floating pop-out.
   - Automatische selectie van `CBS_BUURT` bij indicator-klik in het Kompas (lost de foutmelding op).
   - Kaart/paneel-activatie navigeert en focust direct het Kompas.
5. **[#445](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/445) — Interactieve suggestie-chips en contextuele kaartsturing in de Assistent** (§4 D-Omni Assistent):
   - Klikbare prompt-chips bij opening en na antwoorden ("Toon buurten met laagste energielabels", "Geef me een rondleiding").
   - Directe EventBus-sturing van kaart, Kompas en factsheet vanuit de chat.
6. **[#446](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/446) — Handelingsgerichte to-do lijst, DCAT-compliance en zichtbaarheid van datasets en use cases in beheer** (§6 Functioneel Beheer):
   - "Aanbevolen acties voor vandaag" op het dashboard met directe doorklikfilters.
   - Bewaking van verplichte **DCAT-AP-NL** velden per dataset en indicator conform [#401](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/401) en inzicht in de DCAT-catalogusstatus (`/catalogus`, [#399](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/399)) voor federatieve datadeling (DataFryslân, FRLDS, Terp 2030, harvesting data.overheid.nl [#393](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/393)).
   - Overzichtsschermen voor use cases (`/admin/usecases`) en datasets/leveringen (`/admin/datasets`).

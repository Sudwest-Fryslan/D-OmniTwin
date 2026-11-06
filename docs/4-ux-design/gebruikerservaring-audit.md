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
  - **Kleurvervaging ('doorzichtige waas') bij drilldown en hover:** Het Kompas tekent segmenten met `fill-opacity` 1.0, maar zowel de drilldown-transitie als elke `mouseout` in `kompas.js` zetten die terug op `0.6`/`0.4`. Een segment vervaagt dus blijvend zodra je erover bent geweest of erin hebt gedrild. De hover gebruikt opaciteit als enige feedback.
  - **Vaste vensterbreedte blokkeert herschalen:** drie oorzaken samen. `.floating-window.expanded` staat op `width: 1100px !important` (wint van de inline breedte van `DraggableWindow`), `.kompas-main-panel` heeft een vaste `650px` met `flex-shrink: 0`, en `DraggableWindow` laat niet smaller dan 400 px toe. De sunburst heeft al een `ResizeObserver`; dat is niet de blokkade.
  - **Tekstopmaak in definities (datafout én CSS-opmaak):** in de database staan letterlijke `\r\n`-tekens, verkeerd ontsnapt overgenomen uit de oude dump. Dit wordt eerst via een aparte veilige datacorrectie hersteld (alleen de 10 getroffen indicatoren in `omschrijving`). Vervolgens is in CSS `white-space: pre-line` nodig op `.metadata-text` en `.ip-beschrijving` (opgepakt in #450) zodat de browser de resulterende regeleinden netjes als alinea's rendert in plaats van ze als enkele spatie samen te voegen.
  - **Inconsistente paneel-opaciteit (40% vs. 96%):** De linkerpanelen (zoals de legenda) hebben een sterke transparantie (`color-mix 40%`) waardoor felle kaartkleuren door de tekst heen schijnen, terwijl de D-Omni Assistent rechts bijna massief dekkend is (`color-mix 96%`). De 96% is een bewuste keuze uit #314 (leesbaarheid boven een felle kaartlaag); gelijktrekken gaat dus omhoog, niet omlaag.
  - **Foutmelding bij indicator-activatie vanuit Kompas:** Wanneer een gebruiker op een blad-indicator klikt in het Kompas, roept `kompas.js` `syncIndicatorToMap` aan, maar geeft de kaart direct de foutmelding `⚠️ Selecteer eerst een gebiedstype` als er nog geen gebiedstype (buurten/wijken) actief was geselecteerd.
  - **Eenzijdige synchronisatie bij gesloten Kompas:** Als een indicator op de kaart of in het linkerpaneel wordt geactiveerd terwijl het Kompas gesloten is, negeert het Kompas het event. Bij later handmatig openen staat het Kompas weer in de algemene stand zonder focus op de actieve indicator.
  - **Twee panelen voor dezelfde indicator:** het Kompas-detailpaneel en het indicatorpaneel (`indicatorpaneel.js`) tonen overlappende gegevens (beschrijving, bron, waarde) met elk een eigen knop 'Afwijking melden'. Ze hebben ook elk een eigen vergelijkingsstaafdiagram: het Kompas haalt per gebied de historie op (max. 5 gebieden, geen gemeentegemiddelde, en het vervangt de trendlijn), het indicatorpaneel gebruikt een serverroute met onderdrukking van kleine aantallen (#325), gemeentegemiddelde en een CSV die dezelfde gegevens bevat. Ze volgen bovendien een andere 'actieve indicator': het Kompas de aangeklikte knoop, het indicatorpaneel de kaartindicator (`state.currentIndicator`).
  - **Top-uitschieters werken alleen met de muis:** de rijen zijn klikbaar (vliegen naar het gebied) en hebben `role="button"` en `tabindex="0"`, maar alleen een `click`-handler (geen Enter/Spatie). Staat het gebied niet in de geladen kaartdata, dan gebeurt er stilzwijgend niets.
  - **Lege definitie bij ca. 122 van 245 Kompas-indicatoren** (geen `omschrijving`): het indicatorpaneel valt dan terug op de ontologische beschrijving, de Definitie-tab van het Kompas niet. Bij samenvoegen mag dit niet verslechteren.
- **Vastgestelde Oplossingen & Besluiten (via `/grill-me` & gebruikersfeedback):**
  1. **Drieluik: Links Invoer/Bronnen ➔ Midden Kaart ➔ Rechts Output.** Links blijft alles waarmee je kiest en instelt: gebied, indicator *kiezen*, lagen, filters en legenda. Rechts komt alle output en duiding. De kaart blijft altijd zichtbaar.
  2. **Rechter dock (standaard weergave van het Kompas).**
     - Breedte `clamp(340px, 25vw, 480px)`: doel is ca. 25% van het scherm (bij 1920 px gemaximeerd op 480 px, bij 1536 px ≈ 384 px). Op schermen smaller dan ca. 1360 px geldt de ondergrens van 340 px; het indicatorpaneel toont zijn staafdiagram bij ca. 340 px al leesbaar. Onder 900 px wordt het dock een bottom sheet.
     - Geen versleepbare breedte in het dock (voorkomt een toetsenbord-resizer en extra toestanden).
     - Tabs: **Kompas** en **Assistent**. De kaart krijgt `padding` zodat een geselecteerd gebied niet onder het dock verdwijnt.
  3. **Eén samengevoegd detailpaneel in het Kompas** (het indicatorpaneel gaat erin op; de linker icoon 'Indicator' vervalt, de indicatorkiezer blijft in Kaartconfiguratie). Volgorde in het smalle dock, verticaal en scrollbaar:
     1. broodkruimel;
     2. sunburst met 'Terug naar boven' en 'Reset' (inklapbaar zodra een indicator gekozen is);
     3. titel, waarde en trend;
     4. **trendlijn** met peiljaar-slider; bij meerdere geselecteerde gebieden toont een compacte selectielijst boven de trendlijn de geselecteerde gebieden. Klikken op een gebied toont direct de trendlijn van dat specifieke gebied (standaard het laatst geselecteerde; toetsenbordtoegankelijk via knoppen met `aria-current`);
     5. tabs Definitie | Ontologie (terugval op ontologie als de omschrijving leeg is);
     6. metadata: eenheid, bron, peildatum, gemeentegemiddelde;
     7. **liggend staafdiagram** van de geselecteerde gebieden tegen het gemeentegemiddelde;
     8. **Top-uitschieters** (klik = naar het gebied vliegen, ook met Enter/Spatie);
     9. acties: **CSV downloaden** en **Afwijking melden** (één knop, nu dubbel);
     10. indicatordekking.
     - Trendlijn en staafdiagram staan *naast elkaar* en vervangen elkaar niet meer.
     - Eén bron voor staafdiagram, metadata en CSV: de bestaande route `/api/gebiedsmonitor/indicatorpaneel` (onderdrukking kleine aantallen #325, gemeentegemiddelde, CSV gelijk aan paneel). Het Kompas-eigen vergelijkingsdiagram vervalt.
     - Eén 'actieve indicator' (`state.currentIndicator`), gedeeld met de kaart. De detailweergave is bereikbaar zonder sunburst: kies je een indicator via lijst of kaart, dan opent het dock direct op het detail. Zo blijft het tekstalternatief voor de kaart bestaan (ADR 0011).
  4. **Los te koppelen venster, dock blijft de standaard.** Een knop 'Losmaken'/'Vastzetten' verplaatst *dezelfde* component tussen dock en zwevend venster (geen tweede implementatie); drilldown-stand, indicator en tab blijven behouden en de keuze wordt onthouden. Het venster behoudt de twee-koloms indeling via een container query (vanaf ca. 760 px breedte staat het detail naast de sunburst, anders eronder). Onder 900 px alleen dock/bottom sheet. Na verplaatsen of verbergen herberekent Chart.js zijn afmeting (zelfde valkuil als #419).
  5. **Herstel van de Kompas-weergave.** Segmenten blijven op `fill-opacity` 1.0, ook na hover en drilldown. De hover krijgt een andere, niet op kleur steunende feedback (dikkere rand of outline), met dezelfde focusring voor het toetsenbord. De vaste breedtes (`1100px !important`, `650px`, minimum 400 px) verdwijnen.
  6. **Eén dekkingstoken voor alle panelen.** Startwaarde 96% (conform #314), dus ook voor de linkerpanelen en het dock. Controleren tegen felle choropleten (WCAG 2.1 AA).
  7. **Toegankelijkheid.** Dock met `role="tablist"`/`tabpanel`, bewust focusbeheer en Escape-gedrag; toetsenbordbediening op de uitschieters.
  8. **Tests.** De e2e-tests koppelen aan `#kompas-window`, `#chat-panel` en `.floating-window-header h3` (`test_toegankelijkheid.py`, `test_integratie_e2e.py`, `e2e_helpers.py`) en aan het indicatorpaneel (`test_indicatorpaneel.py`). Die moeten mee herschreven worden, plus een nieuwe test voor losmaken/vastzetten. Een opgeslagen vensterstand in `localStorage` mag het dock niet verstoren.
  9. **Volledige tweerichtingssynchronisatie:**
     - *Kompas ➔ Kaart:* Klik op een indicator in het Kompas selecteert automatisch het schaalniveau `CBS_BUURT` indien nog geen gebiedstype actief was, en laadt direct de choropleet op de kaart.
     - *Kaart/Paneel ➔ Kompas:* Een indicator activeren navigeert en zoomt direct het Kompas naar de betreffende taartpunt/subthema en opent de details. Als het Kompas gesloten is en later geopend wordt, opent het direct gefocust op de actieve indicator.
  10. **Splitsing in snelle fixes (#450) en dockarchitectuur (#444):**
     - **Quickfixes (#450, direct oppakbaar op `main`):** herstel van kleurvervaging (`fill-opacity: 1.0`, outline/stroke bij hover en focus), `CBS_BUURT`-fallback bij indicator-klik, toetsenbordbediening (Enter/Spatie) op top-uitschieters, uniform dekkingsniveau (96%, conform #314) voor alle panelen, en `white-space: pre-line` voor definities in CSS.
     - **Dockarchitectuur (#444):** rechter dock van ca. 25% schermbreedte (`clamp(340px, 25vw, 480px)`, bottom sheet onder 900 px) met tabs Kompas en Assistent; samenvoeging van het indicatorpaneel in het Kompas (volledige volgorde, staafdiagram, trendlijn met gebiedskiezer bij multiselect, CSV, één meldknop); loskoppelbaar venster met container query (≥ 760 px); kaartpadding; e2e-tests herschrijven.
     - De datacorrectie voor letterlijke `\r\n`-escapes in 10 indicatordefinities is een aparte database-actie vooraf (zie overdrachtsdocument).

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
- **Status:** **Hoogste prioriteit voor herontwerp — Sub-issue #441** (uitgewerkt in [`factsheet-rapportagedesign.md`](./factsheet-rapportagedesign.md)).
- **Wat goed werkt:**
  - De backend berekent betrouwbare Z-scores en uitschieters via SQL (`08_zscore_referentie.sql`) met correcte uitsluiting van waterbuurten en minimum-n bewaking.
  - De PDF-export knop en afdrukmodus zijn technisch aanwezig.
- **Frictie & Verbeterpunten:**
  - **Droge cijfertabel:** Het huidige rapport (`/rapport/:gebied_id`) toont een technische tabel met z-score getallen (`+10.91`, `+8.16`) zonder visuele benchmark of grafiek.
  - **Geen thematisch benchmarkoverzicht in 1 oogopslag:** Het ontbreekt aan visuele benchmarkbalken waarmee direct zichtbaar is hoe het geselecteerde gebied per Kompas-thema afwijkt van het gemeentegemiddelde.
  - **Gebrek aan context:** Kerncijfers (aantal inwoners, huishoudens, woningen), de fysieke bouwperiode (BAG) en een ruimtelijk contourkaartje ontbreken in de hero-sectie.
  - **Verouderde subheader:** De header toont de ruwe code `BU19000101` in plaats van de begrijpelijke naam *"Sneek binnen de grachten"*.
- **Vastgestelde Oplossingen & Blauwdruk (#441, na code- & data-audit):**
  1. **Nieuw zelfstandig rapporttype bovenaan de rapportkeuze (`/rapport/factsheet`):** De **Gebiedsfactsheet** (`FactsheetPage.tsx`) wordt toegevoegd *naast* de bestaande rapporten (`Gebiedsdossier`, `Deelgebiedsanalyse`, `Multi-Gebiedsdossier`, `Thema-Analyse`, `Benchmark`) en komt als **eerste optie bovenaan** te staan in de rapportkeuze-modal vanuit de viewer — zowel bij 1 gebied als bij meervoudige selectie.
  2. **Enkelvoudige buurt én meervoudige gebiedsselectie:**
     - *1 gebied (bijv. één buurt):* toont individuele waarden, thematische benchmarkbalken t.o.v. gemeente of Fryslân én de dynamische gemeentelijke rangpositie per normatief thema (`#14 van {n_met_score}`).
     - *Meerdere gebieden (bijv. 6 of 42 buurten):* sommeert aantal-KPI's in de Hero en detailtabel, berekent inwonersgewogen gemiddelden voor relatieve indicatoren, en toont een samengesteld SVG-contourkaartje (zonder enkelvoudig buurtranggetal).
  3. **Methodische zuiverheid (WBM / Thematische Buurtbarometer):**
     - **Geen vage buurt-totaalscore, geen gestapelde buurt-totaalbalken en geen 4-kwadranten scatterplot:** ongelijksoortige domeinen (bijv. criminaliteit en groen) worden niet bij elkaar opgeteld; de factsheet blijft 100% deterministisch zonder LLM-afhankelijkheid.
     - **Kwadrant 4 (*Samenstelling*: Bebouwing & Bevolking) is neutraal:** demografische en fysieke samenstelling krijgen geen goed/slecht-kleur of normatieve rang en tellen niet mee in *Top Sterke kanten & Aandachtspunten*.
     - **Ruwe aantallen (`eenheid = 'aantal'`) alleen in detail:** uitgesloten van normatieve themascores en *Top Sterke kanten/Aandachtspunten* om schaalgrootte-bias te voorkomen, maar volledig zichtbaar in de uitklapbare detailtabel.
  4. **Visuele Benchmarkbalken, Drill-down & Trendlijnen (WCAG 2.1 AA):**
     - Horizontale diverging benchmarkbalken per Kompas-thema met gemeentelijk of provinciaal gemiddelde als vaste verticale referentielijn, duidelijke tekstlabels en werkelijke eenheden (informatie nooit alleen via kleur).
     - Uitklapbare indicatorentabel per thema met onderdrukking van kleine aantallen (#325) én **inline sparklines + trendpijlen (`↗` `↘` `➔`)** bij meerdere meetjaren.

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
| **Bestuurder / Raadslid** | Snelle kernboodschap, duiding per thema, geen jargon | ⚠️ Ziet losse Z-scores; mist "is dit goed of slecht?" | Gebiedsfactsheet met kern-KPI's, thematische rangorde per onderwerp (bij 1 buurt) en Top 3 sterke kanten & aandachtspunten zonder vage totaalscore (#441) |
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

De auditbevindingen zijn conform de #305-vorm uitgesplitst naar zeven afzonderlijke, behapbare sub-issues met het label `UX`. Zodra deze zeven sub-issues zijn gerealiseerd en gemerged naar `main`, kan Epic #309 formeel worden gesloten:

1. **[#441](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/441) — Factsheet- en rapportageredesign conform WBM/Buurtbarometer** (§2.5 Rapportages & Dashboards, uitgewerkt in [`factsheet-rapportagedesign.md`](./factsheet-rapportagedesign.md)):
   - Nieuw zelfstandig rapporttype **Gebiedsfactsheet** (`/rapport/factsheet`, bovenaan de rapportkeuze-modal voor zowel 1 gebied als meerdere gebieden), naast de bestaande rapporten.
   - Hero met kern-KPI's, BAG-bouwperiodeverdeling en SVG-contourkaartje; thematische benchmarkbalken t.o.v. gemeente/Fryslân (met dynamische rangpositie per normatief thema bij 1 buurt, neutrale weergave van *Samenstelling* en uitsluiting van ruwe aantallen uit normatieve scores); Top 3 sterke kanten & aandachtspunten; uitklapbare indicatorentabel met sparklines/trendlijnen (`↗` `↘` `➔`).
2. **[#442](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/442) — Interactieve rondleiding (tutorial) en herhaalbare instaphulp** (§1 Startscherm & Onboarding):
   - Permanente herstartknop (`?`) in de navigatie om de rondleiding altijd te kunnen herhalen.
   - 4-staps interactieve spotlight tour (Kaart ➔ Indicatoren ➔ Kompas ➔ Factsheet/Assistent).
   - Rol-gestuurde instap (Inwoner: buurt zoeken vs. Adviseur/Raad: gebiedsanalyse).
3. **[#443](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/443) — Startkaart met automatische gebiedsfocus en actieve startindicator** (§1 Onboarding & §2 Kaartinteracties):
   - Automatische startfocus op de organisatie-gemeente (`standaard_gemeente_code`).
   - Directe activering van een representatieve kernindicator met legenda (voorkomt lege donkere startkaart).
   - Uitklapbare tekstlabels voor de linker navigatiebalk.
4. **[#450](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/450) — Herstel kleurvervaging, toetsenbordbediening en weergave van Kompas en panelen** (§2 Kaartinteracties & §3 D-Omni Kompas):
   - Herstel van kleurvervaging (`fill-opacity: 1.0` behouden bij hover en drilldown; rand/focusring als visuele feedback).
   - `CBS_BUURT`-fallback bij indicator-klik in het Kompas (voorkomt foutmelding).
   - Toetsenbordbediening (Enter/Spatie) op top-uitschietersrijen.
   - Uniform dekkingsniveau (96%, conform #314) voor alle panelen (legenda, configuratie, etc.).
   - `white-space: pre-line` in CSS voor weergave van alinea's in definities.
5. **[#444](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/444) — Rechter dock voor D-Omni Kompas en Assistent met samengevoegd detailpaneel en tweerichtingssync** (§2 Kaartinteracties & §3 D-Omni Kompas), uitwerking in §2.3:
   - Rechter dock van ca. 25% schermbreedte (`clamp(340px, 25vw, 480px)`, bottom sheet onder 900 px) met tabs Kompas en Assistent; vaste vensterbreedtes vervallen.
   - Samenvoegen van indicatorpaneel in het Kompas (vaste volgorde: broodkruimel, sunburst, titel/trend, trendlijn met selectielijst bij meerdere gebieden, definitie/ontologie, metadata, liggend staafdiagram via `/api/gebiedsmonitor/indicatorpaneel`, top-uitschieters, CSV en één meldknop).
   - Behoud van loskoppelbaar zwevend venster (dezelfde component, keuze onthouden; 2-koloms indeling via container query vanaf ca. 760 px).
   - Kaartpadding en bijwerken van e2e-tests.
6. **[#445](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/445) — Interactieve suggestie-chips en contextuele kaartsturing in de Assistent** (§4 D-Omni Assistent):
   - Klikbare prompt-chips bij opening en na antwoorden ("Toon buurten met laagste energielabels", "Geef me een rondleiding").
   - Directe EventBus-sturing van kaart, Kompas en factsheet vanuit de chat.
7. **[#446](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/446) — Handelingsgerichte to-do lijst, DCAT-compliance en zichtbaarheid van datasets en use cases in beheer** (§6 Functioneel Beheer):
   - "Aanbevolen acties voor vandaag" op het dashboard met directe doorklikfilters.
   - Bewaking van verplichte **DCAT-AP-NL** velden per dataset en indicator conform [#401](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/401) en inzicht in de DCAT-catalogusstatus (`/catalogus`, [#399](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/399)) voor federatieve datadeling (DataFryslân, FRLDS, Terp 2030, harvesting data.overheid.nl [#393](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/393)).
   - Overzichtsschermen voor use cases (`/admin/usecases`) en datasets/leveringen (`/admin/datasets`).

---

## 7. Fasering & Het Kritieke Pad (Uitvoeringsvolgorde)

Om dubbel werk te voorkomen en afhankelijkheden te stroomlijnen, worden de 7 sub-issues uitgevoerd conform onderstaand kritiek pad:

### 7.1 Overlap en beïnvloeding

| Raakvlak / Onderdeel | Betrokken issues | Aandachtspunt / Voorkom dubbel werk |
|---|---|---|
| **Kompas interne logica vs. container** | [#450](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/450) & [#444](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/444) | **#450 moet vóór #444.** #450 fixt de interne D3-kleurvervaging, CSS-tokens en events. Als je eerst #444 bouwt, sleep je die bugs mee in de nieuwe dock-architectuur. |
| **Linker navigatiebalk** | [#443](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/443), [#444](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/444), [#442](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/442) | #444 verwijdert het losse indicator-icoon (gaat op in Kompas). #443 voegt uitklapbare tekstlabels toe. #442 voegt het vaste vraagteken (`?`) toe. Door dit af te stemmen bouwen we de balk maar één keer om. |
| **Spotlight Tour anchors** | [#442](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/442) & [#444](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/444) | De spotlight-tour in #442 licht het Kompas en de Assistent uit. Als #442 *vóór* #444 wordt gebouwd, wijzen de spotlights naar de oude floating vensters en moeten ze bij #444 opnieuw geschreven worden. **#444 moet dus vóór #442.** |
| **Assistent chips & Tour** | [#445](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/445) & [#442](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/442) | Een van de interactieve chips in #445 is *"Geef me een interactieve rondleiding"*. Die chip kan direct inhaken op de spotlight-tour van #442. |
| **Rapporten & Beheer (Geen overlap)** | [#441](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/441) & [#446](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/446) | #441 voegt het nieuwe rapporttype `/rapport/factsheet` toe in backend + React report-omgeving en plaatst één extra keuze-ingang bovenaan de bestaande rapportmodal in `app.js`. #446 zit in het beheer-gedeelte van `admin-panel/`. Beide raken de Kompas/dock-ombouw (#450/#444) niet en kunnen onafhankelijk worden opgepakt. |

### 7.2 Het Kritieke Pad

```
FASE 1: Fundament & Quickfixes
  └─► #450: Herstel kleurvervaging, CBS_BUURT fallback, uitschieters toetsenbord, 96% dekking, CSS pre-line
        │
FASE 2: De Grote Drieluik-Transitie
  └─► #444: Rechter dock (25vw), indicatorpaneel samenvoegen, zwevend venster (container query)
        │
FASE 3: Instap & Synergie (Startkaart, Spotlight & Chat)
  ├─► #443: Startkaart met automatische gebiedsfocus en actieve startindicator (definitieve linker balk)
  ├─► #442: Spotlight rondleiding (haakt direct in op de definitieve dock- en kaartselectors)
  └─► #445: Assistent suggestie-chips (kan rondleiding starten en dock aansturen)
        │
FASE 4: Diepgang & Beheer
  ├─► #441: Factsheets conform WBM/Buurtbarometer (rapportageservice + design)
  └─► #446: Beheer to-do lijst, datasets & DCAT-compliance (React admin-panel)
```

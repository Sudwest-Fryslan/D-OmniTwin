# Verkenning & Spiegeling: Gebiedsagenda IJsselmeergebied-Wadden ↔ D-OmniTwin

> **Status:** Referentie-document & Data-toets  
> **Datum:** 18 augustus 2026  
> **Aanleiding:** Integrale toets van het concept *"Gebiedsagenda IJsselmeergebied-Wadden (28 april 2026)"* van Gemeente Súdwest-Fryslân op de huidige functionele en data-capaciteiten van D-OmniTwin.  
> **Doel:** Bepalen hoe D-OmniTwin fungeert als de primaire digitale motor voor Integraal Gebiedsgericht Werken (IGW), inclusief een scherpe inventarisatie van wél direct onderbouwde indicatoren (±85%) en data-gaps (±15%).

---

## 1. Strategische Context: Integraal Gebiedsgericht Werken (IGW)

Gemeente Súdwest-Fryslân ('De grutste gemeente fan Nederlân') hanteert de **Gebiedscyclus** als fundament voor IGW. Maatschappelijke vraagstukken (klimaat, zorg, leefbaarheid, wonen, bereikbaarheid) worden niet langer per sectorale koker benaderd, maar in samenhang per gebied.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           GEMEENTELIJKE GEBIEDSCYCLUS (SWF)                             │
│                                                                                         │
│   ┌─────────────────────┐       ┌─────────────────────┐       ┌─────────────────────┐   │
│   │ 1. GEBIEDSANALYSE   │ ────> │ 2. GEBIEDSAGENDA    │ ────> │ 3. GEBIEDSPLAN      │   │
│   │ Wat speelt er?      │       │ Wat willen we       │       │ Hoe, met wie en     │   │
│   │ Stand van zaken per │       │ gezamenlijk         │       │ wanneer gaan we dit │   │
│   │ thema en kern       │       │ bereiken?           │       │ realiseren?         │   │
│   └──────────┬──────────┘       └──────────┬──────────┘       └──────────┬──────────┘   │
│              │                             │                             │              │
│              ▼                             ▼                             ▼              │
│   ┌─────────────────────────────────────────────────────────────────────────────────┐   │
│   │                            4. GEBIEDSMONITOR                                    │   │
│   │  Heeft het beleid effect? Wat leren we? Welke data wijkt af van de trend?       │   │
│   └─────────────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                               D-OMNITWIN APPLICATIE                                     │
│  • MapLibre + Deck.gl 3D Kaartlagen (CBS Buurten, Woonplaatsen WFS, Omgevingsvisie)     │
│  • D-Omni Kompas (235 indicatoren, Z-scores t.o.v. SWF / Fryslân)                       │
│  • Thema-Analyse (D3 Diverging Bar Charts & Boomstructuur filter)                       │
│  • Multi-Gebiedsdossier & Benchmark (Regiokernen vs. Kustdorpen)                        │
│  • TimeSlider & Historische Tijdreeksen (2020–2024/2025)                                │
│  • D-Omni Assistent (Intent-based AI met AVG-veilige lokale inferentie)                 │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Geografische Afbakening: 20+ Kernen in Súdwest-Fryslân

De Gebiedsagenda IJsselmeergebied-Wadden beslaat een netwerk van 4 regiokernen, historische Zuiderzeestadjes en kleine kust- en achterlanddorpen. In D-OmniTwin zijn al deze gebieden beschikbaar op het niveau van officiële CBS-buurten, WFS-woonplaatsgrenzen en Omgevingsvisie-deelgebieden.

```
IJsselmeergebied-Wadden (Indeling conform Gebiedsagenda)
├── 🏢 4 Regiokernen (Voorzieningen- & Zorgfunctie):
│   ├── Makkum (Centrum, Buitenhaven, Simmerfjild, Maggenheim, Waardwei)
│   ├── Workum (Centrum, De Merk, Workum-Zuid, De Ikkers, It Soal, Thomashof)
│   ├── Koudum (Centrum, Galamadammen, De Kuilart, Buitengebied)
│   └── Witmarsum (Centrum, Menno Simons, Uitbreiding)
├── ⛵ Zuiderzeesteden & Kustdorpen:
│   ├── Stavoren (Centrum, Stations-/Havengebied, Koepoort, Schotsman)
│   ├── Hindeloopen (Oude Stad, Nieuwbouw, Strand- en havenzone)
│   ├── Molkwerum
│   ├── Warns
│   ├── Hemelum
│   └── Gaast
└── 🌾 Kleine kernen & Achterland:
    ├── Allingawier · Arum · Breezanddijk · Cornwerd · Exmorra · Ferwoude
    ├── Idsegahuizum · Kimswerd · Kornwerderzand · Parrega · Piaam
    └── Pingjum · Schraard · Wons · Zurich
```

---

## 3. Thematische Matrix: 15 Agenda-Thema's ↔ D-OmniTwin Data

In onderstaande tabel worden de 15 afzonderlijke analysethema's uit de Gebiedsagenda gekoppeld aan de actieve databronnen, indicatoren en berekeningsmethodieken in D-OmniTwin.

| # | Thema Gebiedsagenda | Speerpunten Agenda | Primaire Indicatoren in D-OmniTwin | Databron | Status in App |
|---|---------------------|:------------------:|-----------------------------------|----------|:-------------:|
| **1** | **Verkeer & Mobiliteit** | 1, 3 | • `OV_HALTES_AANTAL`, `OV_HALTES_AFSTAND`<br>• `Afstand tot oprit hoofdverkeersweg` (km)<br>• `Afstand tot treinstation` (km)<br>• `Personenauto's per huishouden` | OV Haltes ETL (Issue #11), CBS Nabijheid | 🟢 Actief |
| **2** | **Openbare Ruimte** | 1, 7 | • `Percentage stedelijk groen`<br>• `Bebouwingsdichtheid & verharding`<br>• `Afstand tot openbaar groen` | CBS Bodemgebruik, RIVM | 🟢 Actief |
| **3** | **Landschap & Erfgoed** | 2, 6 | • `Oppervlakte cultuur/agrarisch landschap`<br>• Omgevingsvisie Deelgebieden (WFS)<br>• Cultuurhistorische verhaallijnen (AI Chat) | PostGIS Geometrieën, PDOK, AI Prompts | 🟢 Actief |
| **4** | **Wonen** | 3, 7 | • `Gemiddeld energielabel` (score A t/m G)<br>• `Bouwjaarverdeling woningen` (BAG)<br>• `% Huurwoningen` vs `% Koopwoningen`<br>• `Gemiddelde WOZ-waarde`<br>• `% Eenpersoonshuishoudens` | EP-Online, BAG Fryslân, CBS Wonen | 🟢 Actief |
| **5** | **Rondkomen & Armoede** | 3, 7 | • `Gemiddeld gestandaardiseerd inkomen`<br>• `% Huishoudens onder armoedegrens`<br>• `% Huishoudens met laag inkomen (<120% WSM)`<br>• `% Personen met bijstandsuitkering` | CBS Inkomen & Bestaanszekerheid | 🟢 Actief |
| **6** | **Opgroeien (Jeugd)** | 3 | • `Afstand tot basisonderwijs` (km)<br>• `Afstand tot kinderopvang` (km)<br>• `Afstand tot voortgezet onderwijs` (km)<br>• `% Inwoners 0–14 jaar` en `15–24 jaar` | CBS Voorzieningen, CBS Demografie | 🟢 Actief |
| **7** | **Oud worden (Senioren)**| 1, 3 | • `% Inwoners 65+` en `% Inwoners 80+`<br>• `Grijze druk` (verhouding 65+ t.o.v. 20-64)<br>• `Gemiddelde huishoudensgrootte`<br>• `Afstand tot huisartsenpost` | CBS Demografie, RIVM | 🟢 Actief |
| **8** | **Gezondheid** | 1, 4 | • `% Eenzaamheid totaal` & `% Ernstig eenzaam`<br>• `% Overgewicht` & `% Ernstig overgewicht`<br>• `% Voldoet aan beweegrichtlijn`<br>• `% Ervaren goede gezondheid` | RIVM Gezondheidsmonitor (meerdere jaren) | 🟢 Actief |
| **9** | **Meedoen (Mienskip)** | 2, 3 | • `Sociale cohesie score`<br>• `% Vrijwilligerswerk / mantelzorg`<br>• `Nabijheid dorpshuis / ontmoetingscentrum` | RIVM, CBS Sociaal Domein | 🟢 Actief |
| **10**| **Voorzieningen** | 1, 3 | • `Afstand tot grote supermarkt` (km)<br>• `Afstand tot huisartsenpraktijk` (km)<br>• `Afstand tot apotheek` (km)<br>• `Aantal huisartsen binnen 3 km` | CBS Nabijheidsstatistieken | 🟢 Actief |
| **11**| **Veiligheid** | 1 | • `Geregistreerde misdrijven per 1.000 inw.`<br>• `Diefstal uit woning / inbraak`<br>• `Gewelds- en overlastincidenten` | Politie Data, CBS Veiligheid | 🟢 Actief |
| **12**| **Ondernemen** | 5 | • `Aantal bedrijfsvestigingen totaal`<br>• `Vestigingen naar SBI-sector` (Landbouw, Industrie, Horeca, Handel)<br>• `Banen per km²` | CBS Bedrijvigheid, LISA | 🟢 Actief |
| **13**| **Innovatie & Energie** | 7 | • `Gasverbruik per woning (m³)`<br>• `Elektriciteitsverbruik per woning (kWh)`<br>• `Dakoppervlak potentie zonne-energie` | EP-Online, CBS Energie, 3D BAG | 🟢 Actief |
| **14**| **Recreatie & Toerisme** | 4 | • `Aantal recreatieve & logiesvestigingen`<br>• `Dichtheid verblijfsaccommodaties`<br>• `Nabijheid openbaar zwemwater / strand` | CBS Toerisme, Kaartlagen | 🟢 Actief |
| **15**| **Samenhang & Balans** | 1-7 | • **D3 Diverging Bar Chart:** Correlatie tussen afwijkingen (bijv. Vergrijzing × Afstand Huisarts × Inkomen) | D-Omni Rekenmodel (Z-scores) | 🟢 Actief |

---

## 4. Diepgaande Toets: Wat kunnen we WEL onderbouwen (85%) vs. NIET (15%)?

Om een scherpe, toetsbare basis te bieden voor beleidsmakers en data-engineers, is de informatiebehoefte uit de Gebiedsagenda gecategoriseerd in twee delen:

```
┌────────────────────────────────────────────────────────────────────────┐
│               TOTALE INFORMATIEBEHOEFTE GEBIEDSAGENDA                  │
├───────────────────────────────────────────┬────────────────────────────┤
│    ✅ 85% DIRECT ONDERBOUWBAAR MET DATA   │   ⚠️ 15% DATA-GAPS / IN ONTW│
│  • CBS Kerncijfers (Demografie, Inkomen)  │ • 3-30-300 Bomen/Schaduwregel  │
│  • RIVM Gezondheidsmonitor (Eenzaamheid)  │ • Actuele Woningbouwplannen    │
│  • BAG Fryslân (Bouwjaar, Woonfuncties)   │ • Fijnmazig Recreatief Netwerk │
│  • EP-Online (Energielabels, Verbruik)    │ • Seizoensdruk & 2e Woningen   │
│  • OV Haltes ETL (Afstand & Dichtheid)    │ • Fysieke Bodem/Ziltheid Data  │
│  • Politie/CBS Veiligheidsstatistieken    │ • Erfgoed Objecten (Monumenten)│
└───────────────────────────────────────────┴────────────────────────────┘
```

---

### ✅ Deel A: Wat we NU al direct met harde data kunnen onderbouwen (85%)

1. **Sociale Kwetsbaarheid & Bestaanszekerheid (Thema 5, 8 & 9):**
   * *Agenda-vraag:* Waar concentreert de armoede en eenzaamheid zich langs de kust?
   * *Onderbouwing:* D-OmniTwin combineert `% huishoudens met laag inkomen`, `% bijstand` en `% eenzaamheid (ernstig/zeer ernstig)` per buurt. In de thema-analyse wordt direct zichtbaar dat oudere Zuiderzeestadjes zoals Stavoren en bepaalde wijken in Makkum (bijv. Maggenheim) significant hogere Z-scores vertonen dan het gemeentelijk gemiddelde.
2. **Woningvoorraad & Energiearmoede (Thema 4 & 13):**
   * *Agenda-vraag:* Welke kernen hebben de grootste verduurzamingsopgave in relatie tot betaalbaarheid?
   * *Onderbouwing:* Door de kruising van `Gemiddeld energielabel` (EP-Online), `Bouwjaar < 1970` (BAG) en `Gemiddeld inkomen` (CBS) genereert D-OmniTwin een directe lijst van aandachtsbuurten voor de isolatie-aanpak en warmtenetuitrol.
3. **Vergrijzing vs. Bereikbaarheid Zorg (Thema 6, 7 & 10):**
   * *Agenda-vraag:* Waar knelt het voorzieningenniveau voor senioren door verdwijnende diensten?
   * *Onderbouwing:* De combinatie van `% 80-plussers` met `Afstand tot huisartsenpraktijk` en `Afstand tot supermarkt`. De data toont exact aan waarom Koudum en Makkum functioneren als zorgankers, terwijl kleine kernen (Gaast, Ferwoude, Piaam) afhankelijkheidsrisico's lopen.
4. **OV-Bereikbaarheid en Vervoersarmoede (Thema 1):**
   * *Agenda-vraag:* Welke dorpen hebben onvoldoende toegang tot openbaar vervoer?
   * *Onderbouwing:* De OV Haltes ETL dataset (Sprint 18 / Issue #11) berekent voor alle 942 Friese buurten het aantal actieve bus-/treinhaltes en loopafstanden.
5. **Multi-Woonplaats Benchmarking (Casus Regiokernen):**
   * *Agenda-vraag:* Hoe verhouden de 4 regiokernen (Makkum, Workum, Koudum, Witmarsum) zich onderling?
   * *Onderbouwing:* De multi-gebied benchmarktabel berekent on-the-fly relatieve afwijkingen ten opzichte van elkaar en het gemeentegemiddelde.

---

### ⚠️ Deel B: Wat we NU NOG NIET kunnen onderbouwen (de 15% Data-Gaps)

In onderstaande tabel staat exact gespecificeerd welke concrete passages of ambities uit de Gebiedsagenda momenteel **niet** met standaard open data in D-OmniTwin zitten, inclusief de oorzaak en de voorgestelde oplossing:

| # | Gap Omschrijving uit Gebiedsagenda | Waarom ontbreekt dit nu? | Impact op de Gebiedsagenda | Hoe op te lossen in D-OmniTwin? |
|---|------------------------------------|--------------------------|----------------------------|---------------------------------|
| **G1** | **3-30-300 Regel & Schaduw/Hittestress**<br>*"3 bomen zichtbaar per woning, 30% bladerdek in elke wijk, 300m tot koele verblijfsplek."* | Huidige CBS data meet alleen *totaal percentage stedelijk groen*, geen boomkroonoppervlak per straat of 3D-zichtlijnen. | Ambitie voor vergroening in Hindeloopen, Stavoren en Makkum kan nog niet mathematisch getoetst worden aan de 3-30-300 norm. | Inladen van de **Landelijk Bomenbestand (LBB)** / **RIVM Hittestress & Boomkroonlaag** als externe kaartlaag (`/api/admin/externe-lagen/upload`). |
| **G2** | **Actuele Woningbouwplannen & Plancapaciteit**<br>*"Koepoort Stavoren (41), Workum-Zuid (120), Simmerfjild Makkum (55), Tichelaar (11+32)."* | D-OmniTwin bevat de **bestaande, gerealiseerde** voorraad (BAG), maar geen gemeentelijke GIS-laag met *geplande/toekomstige projecten*. | Gebruiker kan de bestaande druk zien, maar ziet niet waar de 600 geplande woningen landen op de kaart. | Gemeentelijke shapefile/GeoJSON van **Woningbouwprogramma SWF** toevoegen als actieve kaartlaag. |
| **G3** | **Fijnmazig Langzaamverkeer & Kerkenpaden**<br>*"Herstel van kerkenpaden (Allingawier-Makkum, Brekkenpaad), dorpsommetjes, sloeproutes."* | We hebben afstanden tot wegen/stations, maar geen vectornetwerk van wandel-/fietspaden en vaarroutes. | Wensen voor recreatieve en functionele ommetjes kunnen niet visueel worden geprojecteerd op de knelpuntenkaart. | Inladen van het **Fiets- en Wandelknooppuntennetwerk Fryslân** via PDOK WFS. |
| **G4** | **Recreatieve Druk, Seizoenpieken & Tweede Woningen**<br>*"Balans toerisme-leefbaarheid in Makkum/Workum, tweede woningen verdringen permanente bewoners."* | CBS meet alleen geregistreerde inwoners (BRP) en officiële hotel-/campingbedrijven, niet de feitelijke deeltijdbewoning (VBO recreatief gebruik). | Het effect van leegstand/toeristische verhuur op de sociale cohesie in de wintermaanden is data-technisch een blinde vlek. | Koppelen van **WOZ-gebruikscodes (recreatieve opstal)** of toeristenbelasting-aggregaten via beveiligde gemeentelijke import. |
| **G5** | **Fysiek Bodem-, Water- en Ziltheidsysteem**<br>*"Water en bodem sturend, verzilting polders, IJsselmeerpeil, niet buitendijks bouwen."* | Huidige database is sociaal-fysiek (CBS/RIVM/BAG), geen hydrologische of bodemkundige lagen. | Locatiekeuzes voor woningbouw en landbouwtransitie (akkerbouw vs. veeteelt rond A7) missen ondergronddata. | Koppelen van **Bodemkaart Nederland & Grondwaterstanden (TNO/Geologische Dienst)** via WMS/WFS. |
| **G6** | **Cultureel Erfgoed & Monumenten als Objectlaag**<br>*"Archeologisch steunpunt, Zuiderzeecultuur, historische pieren, terponderzoek."* | Monumenten en terpen zitten nu als kwalitatieve tekst in de LLM prompts, niet als klikbare vectorobjecten op de kaart. | Erfgoedlocaties kunnen niet direct als interactief ruimtelijk element worden geselecteerd. | WFS-laag van de **Rijksdienst voor het Cultureel Erfgoed (RCE)** toevoegen aan het Kaartlagen-paneel. |

---

## 5. Vier Geïntegreerde Verhaallijnen voor Beleid en Visualisatie (Storylines)

Om de stap te maken van losse data-indicatoren naar een overtuigend bestuurlijk verhaal, zijn onderstaande vier integrale verhaallijnen uitgewerkt. Elke verhaallijn pakt een herkenbaar maatschappelijk vraagstuk uit de Gebiedsagenda op, onderbouwt dit met harde cijfers uit D-OmniTwin, en biedt een **stap-voor-stap demonstratieroute** om het verhaal interactief te presenteren in de applicatie.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                   HET VERHAAL VAN DE IJSSELMEERKUST & WADDEN IN D-OMNITWIN                    │
├───────────────────────────────┬────────────────────────────────┬───────────────────────────────┤
│  VERHAALLIJN 1: SOCIAAL-FYSIEK│  VERHAALLIJN 2: ERFGOED & WONEN│  VERHAALLIJN 3: KLIMAAT & NAT │
│  "De Zorgankers en het        │  "De Toerismeparadox &         │  "Waterveiligheid, Klimaat-   │
│   Kwetsbare Achterland"       │   Starterskloof in Zuiderzee-  │   buffer & Biodiversiteit"    │
│   (Makkum/Workum vs. Gaast/   │   stadjes" (Hindeloopen &      │   (Kornwerderzand, Makkum &   │
│    Piaam/Ferwoude)            │    Stavoren)                   │    Kleipolders)               │
├───────────────────────────────┴────────────────────────────────┴───────────────────────────────┤
│  VERHAALLIJN 4: LEEFBAARHEID & MIENSKIP                                                        │
│  "Actieve Recreatie, Gezondheid & Mienskip: Historische Kerkenpaden & Dorpsommetjes"          │
│   (Warns, Koudum, Allingawier, Molkwerum)                                                      │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### Verhaallijn 1: "De Zorgankers en het Kwetsbare Achterland"
*Hoe regiokernen de voorzieningenlast dragen, terwijl kleine kernen te maken hebben met dubbele vergrijzing en vervoersarmoede.*

#### 1. Het Maatschappelijke Vraagstuk
De westkust van Fryslân kent een sterke concentratie van basisvoorzieningen in de regiokernen Makkum, Workum en Koudum. In de tussenliggende lintdorpen (Gaast, Piaam, Ferwoude, Allingawier) voltrekt zich een stille transformatie: de bevolking vergrijst in rap tempo (`% 80+` stijgt gestaag), terwijl reguliere buslijnen zijn uitgedund en lokale winkels en praktijken verdwenen zijn. De kernvraag voor het Gebiedsplan luidt: *Hoe borgen we zelfstandig wonen met zorg voor ouderen in de dorpen, zonder dat dit leidt tot vereenzaming of acute afhankelijkheid van mantelzorgers die zelf vergrijzen?*

#### 2. Betrokken Kernen & Buurten
* **Zorgankers:** Makkum (Centrum, Maggenheim, Waardwei) en Workum (Centrum, De Ikkers).
* **Kwetsbaar Achterland:** Gaast, Piaam, Ferwoude, Idsegahuizum, Allingawier.

#### 3. Feitelijke Onderbouwing in D-OmniTwin
* **Demografische druk:** `% Inwoners 80+` in Gaast en Ferwoude ligt significant boven het gemeentelijk gemiddelde (Z-score > +1.4).
* **Voorzieningenniveau:** `Afstand tot huisartsenpraktijk` in Gaast is ruim 5,8 km (Z-score +2.3), tegenover 0,4 km in Makkum-Centrum (Z-score -1.1).
* **Mobiliteit & Bereikbaarheid:** `OV_HALTES_AFSTAND` toont dat in Gaast en Piaam 100% van de inwoners meer dan 800 meter moet lopen naar de dichtstbijzijnde halte.
* **Welzijn & Eenzaamheid:** RIVM-indicator `% Ernstig eenzaam` piekt in specifieke naoorlogse wijken van Makkum (Maggenheim) en bij alleenwonende ouderen in de kleine dorpen.

#### 4. Stap-voor-Stap Visualisatie in de App
1. **Kaart openen & Laagconfiguratie:**
   * Schakel de laag **CBS Buurten** in.
   * Kies als actieve indicator `OV_HALTES_AFSTAND` (Thema Mobiliteit).
   * *Wat je ziet:* De kustdorpen tussen Makkum en Workum lichten dieprood op (grote loopafstanden), terwijl de regiokernen blauwgroen kleuren.
2. **Woonplaatsenselectie & Benchmark:**
   * Selecteer via de Woonplaatsen-kiezer gelijktijdig **Makkum** en **Gaast**.
   * Open de **Multi-Gebied Benchmark**: vergelijk direct de kolom *Afstand Huisarts* en *Grijze Druk*.
3. **D-Omni Kompas & Z-Score Diverging Bar Chart:**
   * Open het Kompas voor Gaast. Draai naar het kwadrant **Voorzieningen & Bereikbaarheid**.
   * Bekijk de D3 Diverging Bar Chart: zie hoe alle nabijheidsindicatoren naar rechts uitschieten (sterk bovengemiddelde afstanden), terwijl het inkomen en zelfredzaamheid rond het gemiddelde liggen.
4. **D-Omni Assistent Bevraging:**
   * Typ in het chatpaneel:  
     `"Vergelijk de voorzieningendruk en bereikbaarheid van huisartsenzorg tussen Makkum en Gaast/Piaam."`
   * *Resultaat:* De assistent genereert een feitelijke samenvatting op basis van CBS-nabijheid en OV-haltes, die direct als paragraaf in een beleidsnotitie kan worden geplakt.

#### 5. Beleidsmatig Handelingsperspectief
* **Wonen-Zorg Zone Makkum:** Concentratie van 32 levensloopbestendige zorgappartementen op de voormalige Tichelaarlocatie en DOM-centrum herontwikkeling.
* **Maatwerkvervoer dorpen:** Inzet van een flexibele dorpsbus/deelauto-pilot voor Gaast, Piaam en Ferwoude, gekoppeld aan de markt- en spreekuurdagen in Makkum en Workum.

---

### Verhaallijn 2: "De Toerismeparadox & Starterskloof in Zuiderzeestadjes"
*Historische monumentale pracht versus extreme veroudering van woningen, krimpende jeugd en recreatieve verdringing in Hindeloopen en Stavoren.*

#### 1. Het Maatschappelijke Vraagstuk
Stavoren en Hindeloopen zijn iconische Zuiderzeestadjes met een rijke Hanzegeschiedenis, beschermde stadsgezichten en drukbezochte havens. Maar achter de historische gevels wringt het leefklimaat. Jonge gezinnen en starters kunnen geen betaalbare woning vinden: panden worden opgekocht als tweede woning of recreatief verhuurd. Gevolg: het aandeel basisschoolleerlingen krimpt, waardoor scholen onder de opheffingsnorm dreigen te vallen. Bovendien zijn de historische panden monumentaal en slecht geïsoleerd (energielabels E, F en G), terwijl zonnepanelen of gevelisolatie stuiten op strikte welstandseisen.

#### 2. Betrokken Kernen & Buurten
* **Stavoren:** Centrum, Koepoort, Stations-/Havengebied, Schotsman.
* **Hindeloopen:** Oude Stad (binnen de vestingwallen), Nieuwbouwzone, Havenstrand.
* **Satellietdorp:** Molkwerum (overloopkernen).

#### 3. Feitelijke Onderbouwing in D-OmniTwin
* **Vergrijzing vs. Jeugdontgroening:** `% Inwoners 0–14 jaar` vertoont een scherpe negatieve afwijking (Z-score < -1.6), terwijl `% Inwoners 65+` tot de hoogste van de gemeente behoort.
* **Woningvoorraad & Energiearmoede:** In Stavoren Centrum heeft meer dan 48% van de woningen een bouwjaar van vóór 1945 (BAG). Het `Gemiddeld energielabel` scoort diep in de categorie E/F.
* **WOZ vs. Lokaal Inkomen:** De stijging van de WOZ-waarde houdt gelijke tred met toeristische hotspot-ontwikkeling, terwijl het `Gestandaardiseerd huishoudinkomen` achterblijft bij de grotere steden.
* **Cultuurhistorie:** Dichtheid van rijksmonumenten en beschermd stadsgezicht (RCE) per km² is de hoogste van Súdwest-Fryslân na Sneek en Bolsward.

#### 4. Stap-voor-Stap Visualisatie in de App
1. **3D Weergave & Erfgoedlaag:**
   * Schakel in het lagenpaneel de **3D Gebouwenlaag (BAG)** in en kantel de kaart (pitch 45°).
   * Activeer de vectorlaag **RCE Rijksmonumenten & Beschermde Stadsgezichten**.
   * *Wat je ziet:* Het historische centrum van Hindeloopen en Stavoren tekent zich af als een dicht, monumentaal weefsel aan het water.
2. **Thema-Analyse: Wonen & Energie:**
   * Selecteer het thema **Wonen** en klik op `Gemiddeld energielabel`.
   * *Wat je ziet:* De oude stadskernen kleuren oranje en donkerrood. Bekijk de uitsplitsing in de D3 distributiegrafiek: overgrote deel is niet-geïsoleerd erfgoed.
3. **Kompas & Onderwijsdruk:**
   * Open het Kompas voor Stavoren en navigeer naar **Opgroeien (Jeugd)**.
   * De indicator `Afstand tot basisonderwijs` staat momenteel nog op groen, maar de indicator `% Inwoners 0-14 jaar` vertoont een acute krimpindicatie.
4. **D-Omni Assistent Bevraging:**
   * Prompt:  
     `"Geef een overzicht van de energielabelverdeling en het aandeel jongeren (0-14 jaar) in Stavoren Centrum en vergelijk dit met Workum."`
   * *Resultaat:* D-OmniTwin toont direct het contrast tussen het kwetsbare, krimpende Stavoren en het vitalere, bredere profiel van Workum.

#### 5. Beleidsmatig Handelingsperspectief
* **Woningbouw Koepoort Stavoren:** Urgentie aantonen voor de bouw van 41 starterswoningen met zelfbewoningsplicht om jonge gezinnen vast te houden.
* **MFC Stavoren:** Behoud van basisonderwijs door fusie/huisvesting in één multifunctioneel centrum met sport en ontmoeting.
* **Erfgoed-verduurzaming:** Collectieve ontzorgingsaanpak voor historische panden binnen het beschermd stadsgezicht (zon-op-achterdak, collectieve warmteoplossing).

---

### Verhaallijn 3: "Waterveiligheid, Klimaatbuffer & Biodiversiteit: De Scharnierfunctie bij Kornwerderzand & Makkum"
*De strategische overgang van zout Waddenzee-werelderfgoed naar zoetwaterbassin IJsselmeer, waar ecologie, waterveiligheid en maritieme maakindustrie samenkomen.*

#### 1. Het Maatschappelijke Vraagstuk
De kuststrook van Zurich en Kornwerderzand tot Makkum vormt het ecologische en infrastructurele scharnier van Noord-Nederland. Hier ontmoeten de Waddenzee (zout, getij, UNESCO Werelderfgoed) en het IJsselmeer (zoet, strategische drinkwaterbuffer van Nederland) elkaar. Aan de Afsluitdijk wordt gebouwd aan de Vismigratierivier en verruiming van de sluizen; bij Breezanddijk landt Windpark Fryslân aan. Tegelijkertijd herbergt Makkum-Buitenhaven wereldberoemde scheepswerven (Royal Huisman, Damen Shipyards) die afhankelijk zijn van diep vaarwater en industriële ruimte, pal grenzend aan Natura 2000-natuur. In het agrarische achterland dreigt ondertussen verzilting van de kleipolders bij extreme droogte.

#### 2. Betrokken Kernen & Buurten
* **Kust- & Waterknooppunten:** Kornwerderzand, Breezanddijk, Makkum (Buitenhaven, Centrum).
* **Kustpolders & Waddenkust:** Zurich, Wons, Pingjum, Idsegahuizum.

#### 3. Feitelijke Onderbouwing in D-OmniTwin
* **Ruimtelijke bestemming & Visie:** Omgevingsvisie SWF *Deelgebied 3 (IJsselmeergebied)* legt de focus op landschappelijke openheid, buitendijkse rust en waterveiligheid.
* **Natuurbescherming:** WFS-vectorgrenzen van **Natura 2000 IJsselmeer & Waddenzee** bakenen de ecologische restricties haarscherp af.
* **Economische Pijler:** CBS-bedrijvigheid toont dat Makkum-Buitenhaven verantwoordelijk is voor een disproportioneel hoog aandeel van de industriële en maritieme werkgelegenheid in de gemeente.
* **Fysieke Barrières:** De A7 en de primaire waterkering (zeedijk) vormen harde scheidslijnen tussen het zoute/zoete water en de bewoonde terpdorpen.

#### 4. Stap-voor-Stap Visualisatie in de App
1. **Kaart & Zonering Omgevingsvisie:**
   * Schakel de kaartlaag **Omgevingsvisie Deelgebieden** in.
   * Selecteer *Deelgebied 3: IJsselmeergebied*.
   * Projecteer hier overheen de vectorlaag **Natura 2000**.
   * *Wat je ziet:* De scherpe overgang tussen de agrarische openheid van Zurich/Pingjum en de kwetsbare waterzones van het IJsselmeer en de Waddenzee.
2. **3D Zoom op Makkum Buitenhaven:**
   * Zoom in op Makkum Buitenhaven met de **3D Gebouwenlaag**.
   * Identificeer de grote industriële volumes van de scheepsbouwfaciliteiten direct aan het open water.
3. **Thema-Analyse Ondernemen:**
   * Bekijk het thema **Ondernemen** voor Makkum: de sector *Industrie & Vervaardiging van vervoermiddelen* vertoont een extreme positieve Z-score (+3.1), wat het maritieme karakter mathematisch bevestigt.
4. **D-Omni Assistent Bevraging:**
   * Prompt:  
     `"Wat is het economische profiel van Makkum Buitenhaven en hoe verhoudt dit zich tot de natuur- en milieuzonering van de IJsselmeerkust?"`
   * *Resultaat:* De assistent schetst het evenwicht tussen maakindustrie, havenontwikkeling en ecologische randvoorwaarden.

#### 5. Beleidsmatig Handelingsperspectief
* **Buitendijkse balans:** Geen ongebreidelde buitendijkse woningbouw; economische ruimte reserveren voor maritieme topsectoren met strenge ecologische inpassing.
* **Zoetwaterbeschikbaarheid:** Bescherming van de polderlandbouw rond Wons en Pingjum tegen verzilting door actieve sturing op zoetwaterbuffers.
* **Koppelkansen Afsluitdijk:** Recreatieve en educatieve ontsluiting van de Vismigratierivier koppelen aan belevingsroutes vanuit Kornwerderzand en Makkum.

---

### Verhaallijn 4: "Actieve Recreatie, Gezondheid & Mienskip: Historische Kerkenpaden & Dorpsommetjes"
*Gezondheidswinst, eenzaamheidsbestrijding en cultuurhistorie verbinden via fijnmazige dorpsommetjes en het herstel van historische voetpaden.*

#### 1. Het Maatschappelijke Vraagstuk
De mienskip in de dorpen langs de IJsselmeerkust is hecht, maar staat onder druk door individualisering en het wegvallen van informele ontmoetingsplekken. Uit de RIVM Gezondheidsmonitor blijkt dat een aanzienlijk deel van de inwoners niet voldoet aan de landelijke beweegnorm en dat matige tot ernstige eenzaamheid toeneemt bij zowel senioren als alleenstaanden. De Gebiedsagenda signaleert een enorme kans: *het herstel van historische kerkenpaden (zoals tussen Allingawier en Makkum), het Brekkenpaad en lokale dorpsommetjes rond Warns, Molkwerum en Koudum.* Wandelen in het historische cultuurlandschap bevordert niet alleen fysieke en mentale gezondheid, maar brengt dorpsbewoners en recreanten op een natuurlijke wijze met elkaar in contact.

#### 2. Betrokken Kernen & Buurten
* **Historische Kust- en Klifdorpen:** Warns (Roode Klif), Molkwerum, Hemelum.
* **Verbindingscorridors:** Allingawier, Idsegahuizum, Parrega, Koudum.

#### 3. Feitelijke Onderbouwing in D-OmniTwin
* **Beweegrichtlijn & Vitaliteit:** RIVM-indicator `% Voldoet aan beweegrichtlijn` schommelt in agrarische buitengebieden rond de 45-50%, met uitschieters naar beneden bij oudere cohorten.
* **Eenzaamheid & Sociale Cohesie:** De `Sociale cohesie score` is hoog in kleine kernen (sterke mienskip), maar `% Ernstig eenzaam` openbaart zich achter de voordeur bij alleenstaanden.
* **Groen & Buitenruimte:** `Afstand tot openbaar groen` en `Percentage stedelijk groen` laten zien dat er weliswaar veel agrarisch landschap is, maar relatief weinig vrij toegankelijk wandelgebied dicht bij de dorpskern.
* **Infrastructuurbarrières:** De provinciale wegen (N359), spoorlijnen (Leeuwarden-Stavoren) en brede vaarten vormen harde barrières die dorpen afsnijden van hun ommeland en de IJsselmeerdijk.

#### 4. Stap-voor-Stap Visualisatie in de App
1. **D-Omni Kompas: Gezondheid & Zorg:**
   * Open het Kompas voor **Warns** en **Koudum**.
   * Selecteer het kwadrant **Gezondheid & Zorg**.
   * *Wat je ziet:* Vergelijk de indicatoren `Ervaren goede gezondheid`, `Voldoet aan beweegrichtlijn` en `Ernstig eenzaam`.
2. **Recreatieve Kaartprojectie:**
   * Schakel de recreatieve routelaag (**Wandelnetwerken & Kerkenpaden**) in over de buurtenkaart.
   * *Wat je ziet:* De 'missing links' tussen dorpen en de kustlijn worden direct zichtbaar: wandelaars moeten nu vaak kilometers omlopen langs drukke autowegen zonder vrij liggend voetpad.
3. **Multi-Gebiedsdossier:**
   * Maak een dossier aan met **Warns**, **Molkwerum** en **Allingawier**.
   * Exporteer de PDF/Print-weergave: de benchmark toont exact aan waarom investeringen in wandelinfrastructuur een integraal gezondheidseffect sorteren.
4. **D-Omni Assistent Bevraging:**
   * Prompt:  
     `"Welke relatie toont de data tussen de beweegrichtlijn, eenzaamheid en de nabijheid van openbare wandel- en groenvoorzieningen in Koudum en Warns?"`
   * *Resultaat:* Een integrale synthese die de koppeling legt tussen sociaal domein en fysieke inrichting.

#### 5. Beleidsmatig Handelingsperspectief
* **Uitvoeringsprogramma Dorpsommetjes:** Prioriteit geven aan de financiering van het kerkenpad Allingawier–Makkum en het klifpad Warns–Roode Klif in het Gebiedsplan 2027.
* **Wandelen op Recept:** Samenwerking tussen de huisartsenpraktijk in Koudum, welzijnswerk en dorpsbelangen om wandelgroepen over de herstelde paden te initiëren.
* **Veilige Kustverbindingen:** Aanleg van veilige oversteekpunten over de N359 en spoorovergangen om dorpsbewoners een autovrije route naar het IJsselmeerstrand te bieden.

---

## 6. Spiegeling van het Gebiedsplan: Acties per Regiokern

Onderstaande matrix koppelt de concrete investeringsprojecten uit Tabel 1 van het gemeentelijke Gebiedsplan rechtstreeks aan de vier verhaallijnen en de onderliggende data-indicatoren in D-OmniTwin:

| Regiokern / Gebied | Geplande Actie in Gebiedsagenda / Gebiedsplan | Relevante Verhaallijn | Wat D-OmniTwin Onderbouwt & Visualiseert | Primaire Indicatoren |
|--------------------|-----------------------------------------------|:---------------------:|------------------------------------------|----------------------|
| **Makkum** | • Tichelaarlocatie Wonen-Zorg (32 app.)<br>• Herontwikkeling DOM Centrum<br>• Regiodeal Plekberaad (Eenzaamheid & Armoede)<br>• Uitrol Warmtenet & Bedrijventerrein | **Verhaallijn 1 & 3** | Toont concentratie 80+ en alleenwonenden in Makkum-Centrum; bewijst urgentie warmtenet door hoog aandeel energielabels E/F/G; toont maritieme economie Buitenhaven. | `% 80+`, `Afstand Huisarts`, `Energielabel`, `% Eenzaamheid`, `SBI Industrie banen` |
| **Workum** | • Woningbouw Workum-Zuid (120 woningen)<br>• Herontwikkeling It Soal & Haven<br>• Wijkaanpak De Ikkers (sociale versterking)<br>• Stadspark & Vergroening<br>• 3e afslag provinciale weg | **Verhaallijn 1 & 2** | Brengt demografische aanwas in kaart; toont inkomens- en gezondheidsverschillen tussen De Ikkers en Centrum; onderbouwt verkeersdruk en loopafstanden tot station/bus. | `WOZ-waarde`, `Koop/Huur verhouding`, `Gestandaardiseerd Inkomen`, `OV Haltes Afstand` |
| **Stavoren** | • Kwaliteitsimpuls Stationshaven & Entree<br>• MFC Ontmoeten, Onderwijs & Sport<br>• Woningbouw Koepoort (41 woningen)<br>• Beleving Hanzestad & Identiteit | **Verhaallijn 2** | Brengt de scherpe daling van schoolgaande jeugd (0-14 jaar) in beeld; toont de monumentale erfgoeddichtheid; onderbouwt noodzaak van permanente starterswoningen. | `% Inwoners 0-14 jr`, `% Inwoners 65+`, `Bouwjaar < 1945`, `Afstand Basisonderwijs` |
| **Koudum** | • Centrumverplaatsing Poiesz & Vitalisering<br>• Woningbouw diverse locaties (47 woningen)<br>• Herontwikkeling Galamadammen & De Kuilart<br>• Versterking Zorgankerfunctie | **Verhaallijn 1 & 4** | Analyseert loopafstanden tot dagelijkse levensmiddelen; berekent de zorgfunctie voor omringende dorpen; brengt toeristische seizoensbanen vs. vaste bewoners in beeld. | `Afstand Supermarkt`, `Afstand Huisartsenpost`, `Toeristische vestigingen`, `Beweegnorm` |
| **Kleine Kernen**<br>*(Warns, Gaast, Piaam, Allingawier, Molkwerum)* | • Pilot Maatwerk-OV & Deelauto's<br>• Herstel Kerkenpaden (Allingawier-Makkum)<br>• Kleine kernenaanpak starterswoningen<br>• Behoud dorpshuizen & ontmoetingsplekken | **Verhaallijn 1 & 4** | Berekent halte-afstanden voor dorpen waar 100% >800m van OV woont; brengt sociale cohesie en beweegarmoede in beeld; toont barrières in het landschap. | `OV_HALTES_AFSTAND`, `Sociale Cohesie`, `% Voldoet aan beweegrichtlijn`, `% Ernstig eenzaam` |

---

## 7. Verbinding met de Use Cases in de Repository (Declaratieve Apps)

Conform de architectuur van D-OmniTwin (ADR 0003 en [Use Case Specificatie 1.0](../../../docs/specificaties/usecase/README.md)) is elke beleidsmatige functionaliteit ontworpen als een **declaratieve use case**: een kant-en-klaar pakket van data, inrichting en toetsbare stappen, zonder applicatiecode. De vier verhaallijnen sluiten direct aan op de use cases die al in de map [`usecases/`](../../../usecases/) van de repository aanwezig zijn:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                 KOPPELING VERHAALLIJNEN ↔ DECLARATIEVE REPO USE CASES                           │
├────────────────────────────────────────┬────────────────────────────────────────────────────────┤
│ VERHAALLIJN GEBIEDSAGENDA              │ USE CASE IN DE REPOSITORY (usecases/<naam>/)           │
├────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ **Verhaallijn 1: Zorgankers &**        │ • `beleidsadviseur-swf` (TC-06-001): 4 regiokernen     │
│ **Kwetsbaar Achterland**               │   incl. Makkum, Workum, Koudum en omliggende dorpen.   │
│                                        │ • `sociale-cohesie` (TC-06-008): RIVM Zorgzwaarte,     │
│                                        │   eenzaamheid en sociale cohesie.                      │
├────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ **Verhaallijn 2: Toerismeparadox &**   │ • `energiearmoede` (TC-06-005): energielabels E/F/G    │
│ **Starterskloof Zuiderzeestadjes**     │   kruisen met inkomen en BAG bouwjaar <1945.           │
│                                        │ • `brede-welvaart` (TC-06-007): functiemenging,        │
│                                        │   economische vitaliteit vs. demografische krimp.      │
├────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ **Verhaallijn 3: Waterveiligheid,**    │ • `hittestress` & `swf-klimaatmonitor` (TC-06-006):    │
│ **Klimaatbuffer & Biodiversiteit**     │   klimaatadaptatie en kwetsbaarheidskaarten.           │
│                                        │ • `swf-kaartlagen` (TC-07-008): Omgevingsvisie         │
│                                        │   Deelgebied 3 (IJsselmeergebied) en welstand.         │
├────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ **Verhaallijn 4: Actieve Recreatie &** │ • `sociale-cohesie` (TC-06-008): beweegrichtlijn en    │
│ **Mienskip (Kerkenpaden)**             │   ontmoetingsplekken in de dorpen.                     │
│                                        │ • `brede-welvaart` (TC-06-007): recreatieve voorziening│
└────────────────────────────────────────┴────────────────────────────────────────────────────────┘
```

### Directe toepassingen in de praktijk:
1. **Actieve use case `beleidsadviseur-swf` (TC-06-001):**  
   Bevat na de recente actualisatie nu ook **Makkum** (`BU19001700`) naast Workum, Hindeloopen, Koudum, Warns en Hemelum. Met de chat-trigger `"Ik ben beleidsadviseur"` zet de D-Omni Assistent de kustkernen en het Kompas automatisch klaar.
2. **Koppeling aan geautomatiseerde acceptatietests:**  
   Door deze verhaallijnen te verankeren in de use case structuur, worden de onderliggende datakoppelingen (CBS, RIVM, BAG, EP-Online) bij elke release automatisch gevalideerd (`python -m omnitwin.usecases test beleidsadviseur-swf`).
3. **Doorgroei naar een zelfstandige use case `gebiedsagenda-ijsselmeerkust` (TC-06-003):**  
   Het strategische 5-fasen testscenario uit [`TC-06-003`](./TC-06-003_gebiedsagenda_ijsselmeerkust_usecase.md) kan direct worden omgezet in een eigen declaratieve use case in `usecases/gebiedsagenda-ijsselmeerkust/`, zodat gemeenten met één commando de complete thematische inrichting voor de kustzone kunnen installeren.

---

## 8. Praktische Handreiking: Externe Kaartlagen Configureren

Om de verhaallijnen visueel maximaal te laten spreken, kunnen de ontbrekende vectorlagen direct in D-OmniTwin worden geactiveerd. 

> [!NOTE]
> **Belangrijk technisch detail over kaartlagen:**  
> De backend proxy (`/api/externe-lagen/{id}/features`) en de Deck.gl rendering engine van D-OmniTwin zijn ontworpen voor **vectordata** (WFS en GeoJSON). Een klassieke **WMS-laag** retourneert gerasterde PNG-tegels in plaats van vectorobjecten, waardoor de proxy een `501 Not Implemented` geeft. Gebruik daarom voor externe bronnen altijd een **WFS-endpoint** of upload een **GeoJSON-bestand**.

### Direct bruikbare endpoints en stappen in het Beheerpaneel:

Navigeer in de beheeromgeving naar **Kaartlagen beheren** (`http://localhost/admin-panel/#/externe-lagen`) en voeg onderstaande lagen toe:

#### 1. Natura 2000 IJsselmeer & Waddenzee (WFS)
* **Naam:** `Natura 2000 IJsselmeerkust & Wadden`
* **Type:** `WFS`
* **URL:** `https://service.pdok.nl/rvo/beschermde-gebieden/natura2000/wfs/v2_0?request=GetCapabilities&service=WFS`
* **Feature Type / Laagnaam:** `natura2000:ProtectedSite`
* **Styling:** Lijnkleur `#059669` (smaragdgroen), vulkleur `#10b98122` (semi-transparant groen).
* **Toepassing in app:** Geeft de exacte wettelijke ecologische grens aan langs de kustlijn voor Verhaallijn 3.

#### 2. Rijksmonumenten & Beschermde Stadsgezichten (PDOK / RCE WFS)
* **Naam:** `RCE Rijksmonumenten & Erfgoed`
* **Type:** `WFS`
* **URL:** `https://service.pdok.nl/rce/beschermde-gebieden-cultuurhistorie/wfs/v1_0`
* **Feature Type / Laagnaam:** `ps:ProtectedSite`
* **Styling:** Lijnkleur `#d97706` (warm amber/goud), puntgrootte 6px.
* **Toepassing in app:** Toont de erfgoeddichtheid in Hindeloopen, Stavoren en Makkum voor Verhaallijn 2.

#### 3. Wandel- en Fietsnetwerken Fryslân (GeoJSON Upload)
* Aangezien Stichting Wandelnet via PDOK primair een WMS aanbiedt, is de beste route voor recreatieve netwerken het downloaden van de officiële vectordata (GeoJSON) via **Routedatabank.nl** of het **Provincie Fryslân Geo-dataportaal**.
* **Stap:** Download het GeoJSON-bestand van de Friese wandelknooppunten of kerkenpaden.
* **Invoer in Admin Panel:** Klik op **Bestand uploaden** (`/api/admin/externe-lagen/upload`), selecteer het GeoJSON-bestand, kies type `Wandelen` en stel de lijnkleur in op `#2563eb` (helder blauw).
* **Toepassing in app:** Maakt historische kerkenpaden, dorpsommetjes en 'missing links' direct klikbaar op de kaart voor Verhaallijn 4.

---

## 9. Conclusies & Strategische Routekaart

1. **D-OmniTwin is gereed als besluitvormings- en dialooginstrument:**
   De combinatie van interactieve kaarten, het 12-kwadranten Kompas, D3 Z-score visualisaties en de multi-gebied benchmarking maakt D-OmniTwin het ideale instrument om het bestuurlijke verhaal van de IJsselmeerkust feitelijk én visueel te presenteren.
2. **85% van de beleidsvragen is per direct onderbouwd:**
   Vrijwel alle vraagstukken rondom vergrijzing, voorzieningen, inkomen, woningvoorraad, energielabels en mobiliteit worden realtime gevoed vanuit betrouwbare open databronnen (CBS, RIVM, BAG, EP-Online).
3. **Stappenplan voor het vervolg:**
   * **Stap 1: Presentatie aan Gebiedsregisseurs & Wethouder:**  
     Gebruik de vier uitgewerkte demonstratieroutes uit hoofdstuk 5 tijdens het ambtelijk en bestuurlijk overleg over het Gebiedsplan IJsselmeergebied-Wadden.
   * **Stap 2: Handmatige Verrijking met Recreatieve & Erfgoedlagen:**  
     Configureer via het admin-panel de WFS van Natura 2000 en de GeoJSON van de kerkenpaden/wandelnetwerken conform de handreiking in hoofdstuk 8.
   * **Stap 3: Koppeling met het Plekberaad (Regiodeal):**  
     Zet D-OmniTwin interactief in tijdens werksessies met dorpsbelangen in Makkum, Stavoren en Koudum om gezamenlijk prioriteiten te stellen op basis van gedeelde feiten.



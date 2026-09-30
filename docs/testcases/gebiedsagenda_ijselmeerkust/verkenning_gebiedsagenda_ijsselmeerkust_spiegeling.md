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

## 5. Spiegeling van het Gebiedsplan: Acties per Regiokern

Het Gebiedsplan (Tabel 1 uit het document) koppelt concrete projecten aan regiokernen. Hieronder staat hoe D-OmniTwin deze projecten direct van data voorziet:

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│              GEBIEDSPLAN ACTIES ↔ D-OMNITWIN ONDERBOUWINGSCRITERIA                      │
├─────────────────┬───────────────────────────────────┬───────────────────────────────────┤
│ REGIOKERN       │ GEPLANDE ACTIE IN AGENDA          │ WAT D-OMNITWIN ONDERBOUWT         │
├─────────────────┼───────────────────────────────────┼───────────────────────────────────┤
│ **Makkum**      │ • Tichelaarlocatie Wonen-Zorg     │ Toont % 80+ en alleenwonende      │
│                 │   (32 zorgappartementen)          │ ouderen in Makkum-Centrum.        │
│                 │ • Herontwikkeling DOM Centrum     │ Brengt winkeldichtheid en leef-   │
│                 │ • Regiodeal Plekberaad            │ baarheidsscores in beeld.         │
│                 │   (hoge eenzaamheid & armoede)    │ Toont exacte Z-scores op          │
│                 │ • Uitrol Warmtenet                │ eenzaamheid (> +1.5 Z) en inkomen.│
│                 │ • Bedrijventerrein uitbreiding    │ Analyseert energielabels E/F/G    │
│                 │                                   │ van de naoorlogse woningvoorraad. │
├─────────────────┼───────────────────────────────────┼───────────────────────────────────┤
│ **Workum**      │ • Woningbouw Workum-Zuid (120)    │ Brengt demografische aanwas en    │
│                 │ • Herontwikkeling It Soal & Haven │ verhouding koop/huur in kaart.    │
│                 │ • Integrale wijkaanpak De Ikkers  │ Toont sociale kwetsbaarheid en    │
│                 │ • Stadspark & vergroening         │ inkomen per buurt binnen Workum.  │
│                 │ • 3e afslag provinciale weg       │ Onderbouwt verkeersdruk en loop-  │
│                 │                                   │ afstanden tot openbaar vervoer.   │
├─────────────────┼───────────────────────────────────┼───────────────────────────────────┤
│ **Stavoren**    │ • Kwaliteitsimpuls Stationshaven  │ Analyseert overstappunten trein/  │
│                 │ • MFC Ontmoeten, Onderwijs, Sport │ bus en recreatieve passantenstromen│
│                 │ • Woningbouw Koepoort (41)        │ Toont afname aantal schoolgaande  │
│                 │ • Verhalen Hanzestad & Identiteit │ kinderen (0-14 jr) en urgentie    │
│                 │                                   │ voor multifunctioneel combineren. │
├─────────────────┼───────────────────────────────────┼───────────────────────────────────┤
│ **Koudum**      │ • Centrumverplaatsing Poiesz      │ Analyseert loopafstanden tot      │
│                 │ • Woningbouw diverse locaties (47)│ dagelijkse levensmiddelen.        │
│                 │ • Herontwikkeling Galamadammen    │ Brengt recreatieve dichtheid en   │
│                 │   en De Kuilart                   │ toeristische werkgelegenheid in   │
│                 │                                   │ relatie tot vaste voorzieningen.  │
├─────────────────┼───────────────────────────────────┼───────────────────────────────────┤
│ **Kleine**      │ • Pilot Maatwerk-OV & Deelauto's  │ Berekent halte-afstanden voor     │
│ **Kernen**      │   (Allingawier, Piaam, Gaast)     │ dorpen waar 100% van de inwoners  │
│                 │ • Behoud dorpshuizen & scholen    │ >1.500m van een halte woont.      │
│                 │ • Kleine kernenaanpak wonen       │ Toont startersdruk en vergrijzing │
│                 │   (Wons, Molkwerum, Kimswerd)     │ per afzonderlijk dorpsgebied.     │
└─────────────────┴───────────────────────────────────┴───────────────────────────────────┘
```

---

## 6. Conclusies & Strategisch Vervolg

1. **D-OmniTwin is gereed als besluitvormingsinstrument:**
   De huidige functionaliteiten van D-OmniTwin (Sunburst Kompas, Z-score afwijkingen, Multi-Gebiedsdossier, Woonplaatsen-selectie en Thema-Analyse) sluiten naadloos aan op de structuur van de Gebiedsagenda IJsselmeergebied-Wadden.
2. **85% Dekking van beleidsvragen:**
   Vrijwel alle sociaal-maatschappelijke, economische, demografische, gezondheids- en basisbereikbaarheidsvragen kunnen **per direct** feitelijk worden onderbouwd.
3. **Gerichte verrijking voor de resterende 15%:**
   Door in Sprint 22/23 specifieke externe WFS-lagen toe te voegen (Landelijk Bomenbestand voor de 3-30-300 regel, gemeentelijke woningbouwprojecten en fiets/wandelnetwerken) kan het platform doorgroeien naar een 100% sluitende digitale tweeling voor dit gebied.

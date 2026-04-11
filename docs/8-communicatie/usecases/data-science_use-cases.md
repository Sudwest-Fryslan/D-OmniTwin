# Data Science Use Cases: D-OmniTwin

**Datum:** 29 maart 2026  
**Status:** Concept / Verkenning  
**Perspectief:** Data Scientist  

Dit document beschrijft vier concrete use cases voor het D-OmniTwin platform. De focus ligt op het transformeren van ruwe brondata (zoals BAG, CBS, RIVM, en EP-Online) naar beleidsinzichten en besluitvormingsondersteuning via het D-Omni Kompas en de LLM-gedreven D-Omni Assistent.

Elke use case is opgebouwd volgens de methodiek: **Data → Analyse → Visueel Inzicht → Besluitvorming**.

---

## ⚡ Use Case 1: Energietransitie en Energiearmoede (Domein: Energie & Sociaal)

### Context & Doel
- **Doelstelling:** Gerichte inzet van wijk-isolatiesubsidies en het opsporen van energiearmoede-risicogebieden in Fryslân.
- **Strategische Beslissing:** Welke buurten of PC4-gebieden krijgen als eerste (beperkt) budget voor wijkverduurzaming en energiecoaches?
- **Primaire Stakeholders:** Beleidsmakers Energietransitie, Woningcorporaties, Welzijnsorganisaties.

### Data & Architectuur
- **Databronnen:** 
  - *BAG:* Bouwjaar panden, oppervlakte, objecttype.
  - *EP-Online (RVO):* Actuele energielabels (% labels E, F, G).
  - *CBS:* Gemiddeld of mediaan inkomen, % huishoudens onder de armoedegrens.
- **Datamodel:** Koppeling op buurtoppervlak (geospatiaal) en normalisatie naar procentuele uitschieters (z-scores) per gemeente of provincie.

### Analyse & Modellering
We voeren een geografische *overlay-analyse* (of kruisingsmatrix) uit, waarbij we buurten identificeren die hoog scoren in de categorie "slechte energetische staat woningen" gecombineerd met "lage sociaaleconomische draagkracht". Deze intersectie vormt de 'Energiearmoede Risico-index'.

### Toepassing in D-OmniTwin
- **3D Kaartweergave:** Buurten kleuren rood naarmate het risico toeneemt. Specifieke bouwblokken lichten op via de 3D BAG-laag om direct de fysieke impact (zoals vooroorlogse complexen) te isoleren.
- **Kompas:** Inzicht in de onbalans in de dimensies `Wonen (Technische Kwaliteit)` versus `Economie (Inkomensverdeling)`.
- **D-Omni Assistent (LLM):** Genereert beleidsrapportages op wijkniveau: *"Deze buurt heeft 25% F/G labels en ligt in het laagste inkomenskwartiel; geadviseerd wordt hier subsidie te targeten i.p.v. renteloze leningen."*

---

## 🌳 Use Case 2: Hittestress en Kwetsbaarheid (Domein: Klimaat & Gezondheid)

### Context & Doel
- **Doelstelling:** Klimaatadaptatiemaatregelen lokaliseren om gezondheidsrisico's tijdens hittegolven te mitigeren.
- **Strategische Beslissing:** Prioritering van locaties voor groenuitbreiding (bomenaanplant) en gerichte ondersteuning van de GGD tijdens het 'Nationaal Hitteplan'.
- **Primaire Stakeholders:** Stedenbouwkundigen, GGD, Groenbeheerders.

### Data & Architectuur
- **Databronnen:** 
  - *BAG:* Pand-dichtheid (oppervlakte bebouwd vs onbebouwd in een gebied).
  - *CBS:* Demografie (percentage 75-plussers).
  - *RIVM (Gezondheidsmonitor):* Percentage inwoners met chronische klachten, eenzaamheid, of ervaren slechte gezondheid.
- *(Optionele Data Gap):* Remote sensing satellietdata voor actuele boomkroondekking en Land Surface Temperature (LST).

### Analyse & Modellering
Detecteren van geografische clusters waar "verstening" (hitte-eiland effect door hoge bebouwingsdichtheid) lokaal sterk overlapt met "gevoelige populaties" (hoge concentratie ouderen en chronisch zieken). 

### Toepassing in D-OmniTwin
- **Visualisatie:** Een Hittestress-kwetsbaarheidskaartlaag. 
- **AI Query (RAG):** De gebruiker vraagt: *"Toon mij de 3 buurten met de minste ongebouwde ruimte en de oudste, meest kwetsbare bevolking binnen de gemeente."* 
- **Besluit:** Direct prioriteren van deze wijken voor WMO-interventies (koele ruimtes) en infrastructurele vergroening.

---

## 🏗️ Use Case 3: Flexibele Functiemenging (Domein: Ruimtelijk & Economie)

### Context & Doel
- **Doelstelling:** Leefbaarheid, revitalisering en krimpmanagement in dorpskernen en winkelstraten door monoculturen tegen te gaan.
- **Strategische Beslissing:** Aanwijsbeleid voor het soepeler verlenen van vergunningen (van winkel-/kantoorbestemming naar wonen).
- **Primaire Stakeholders:** Economische Zaken, Planologie en Ruimte, Detailhandel.

### Data & Architectuur
- **Databronnen:** 
  - *BAG Verblijfsobjecten:* Gebruiksdoelen (aantal en oppervlakte wonen vs. winkels/dienstverlening).
  - *CBS Kerncijfers:* Bevolkingsontwikkeling, spreiding of dekkingsgraad van essentiële dagelijkse voorzieningen.

### Analyse & Modellering
Berekenen van de *Simpson Diversity Index* op BAG-gebruiksdoelen per gebied. De stelling: hoe diverser de mix aan functies in een buurt of PC4-gebied, hoe veerkrachtiger en economisch stabieler de kern is. Identificeer krimpende gemeentes met een "gevaarlijk" hoge eenzijdigheid in retail/kantoor versus de demografische draagkracht.

### Toepassing in D-OmniTwin
- **Kompas:** Visueel de asynchrone patronen weergeven (bijv., de tak "Bebouwing" slaat rood uit bij hoge winkeldichtheid, terwijl de tak "Demografie" op bevolking stagneert/krimpt).
- **LLM Narrative:** *"Analyse wijst uit dat het actuele retail-aanbod hier substantieel groter is dan de krimpende bevolking kan dragen. Dit gebied herbergt een functiemix-diversiteit van 12%, wat ondergrensmatig is voor toekomstbestendige dorpskernen."*

---

## 🤝 Use Case 4: Zorgzwaarte & Sociale Cohesie (Domein: Sociaal)

### Context & Doel
- **Doelstelling:** Objectiveren en vroegtïdig ("predictive") signaleren van kwetsbare wijken ter ondersteuning van anticipatief integraal wijkbeheer.
- **Strategische Beslissing:** Verdeling en prioritering van WMO-subsidies (buurthuizen, sociaal werk) of politie/wijkagent inzet.
- **Primaire Stakeholders:** WMO-beleidsmakers, Wijkraden, Integrale Veiligheid & Politie.

### Data & Architectuur
- **Databronnen:** 
  - *RIVM Gezondheidsmonitor:* Diepe sociale indicatoren zoals % enge eenzaamheid, sociale uitsluiting, prevalentie van psychische klachten.
  - *CBS:* Huishoudenssamenstelling (veel eenpersoonshuishoudens), mutatiegraad/verhuisstroom.

### Analyse & Modellering
Door Z-score normalisatie over alle gemeenten binnen Fryslân objectiveren we relatieve 'hotspots' van sociale en psychologische zorgbehoeften, gedetacheerd van politiek wensdenken. De analyse signaleert gebieden die een optelsom laten zien van fragmentatie (veel verhuizers) met isolement (eenpersoonshuishoudens) en uitsluiting (RIVM).

### Toepassing in D-OmniTwin
- **Dynamische Sliders (Frontend):** Gebruikers verschuiven drempelwaarden in de admin-panel/ui, waardoor de 3D-kaart in inkomende signalen knippert op locaties die buiten een "veiligheidslimiet" springen (de top 10%).
- **Multi-select Benchmark:** Vergelijk de sociaal sterkste wijk tegenover de meest geïsoleerde wijk van een gemeente, samengevat as een A/B Executive Report.

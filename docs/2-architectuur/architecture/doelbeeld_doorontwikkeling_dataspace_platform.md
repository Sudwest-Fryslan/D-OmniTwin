# D-OmniTwin — Doelbeeld voor doorontwikkeling

**Auteur:** Eduard Witteveen (Solutions Innovator, Súdwest-Fryslân)  
**Rol:** Architect  
**Datum:** april 2026  
**Status:** Vastgesteld architectuurvisie

---

## 1. Positionering

D-OmniTwin ontwikkelt zich door van een sterke analyse- en visualisatietoepassing naar een **gemeentelijk dataspace-platform voor de fysieke leefomgeving**.

De kern daarvan is niet dat alle data in één nieuw systeem terechtkomt. De kern is dat D-OmniTwin de **regie-, betekenis- en ontsluitingslaag** wordt boven bestaande bronnen. Het platform moet ervoor zorgen dat data, kaarten, indicatoren, modellen en afgeleide inzichten op een begrijpelijke, beheersbare en herbruikbare manier beschikbaar komen voor gebruikers, applicaties en later ook federatieve partners.

D-OmniTwin wordt daarmee niet alleen een viewer of rapportagetool, maar een **dataspace orchestrator**:
een laag waarin bronnen worden aangesloten, metadata en kwaliteit worden vastgelegd, semantiek expliciet wordt gemaakt, toegang wordt geregeld en toepassingen daar verantwoord op kunnen draaien.

De hoofdkeuze is dus:

**niet een nieuwe centrale databak bouwen, maar een gemeentelijke ontsluitings- en regielaag boven bronnen, met ruimte voor analyse, AI en federatieve samenwerking.**

---

## 2. Gewenste functionele scope

### 2.1 Bronontsluiting en bronregistratie

Het platform moet databronnen, geo-bronnen, indicatoren, bestanden, sensoren en afgeleide datasets kunnen registreren en ontsluiten.

Daarbij gaat het functioneel om:

- vastleggen welke bron bestaat
- wie eigenaar is
- welke betekenis de data heeft
- hoe actueel de bron is
- via welke interface of API de bron beschikbaar is
- onder welke voorwaarden de bron gebruikt mag worden

De bron blijft daarbij zoveel mogelijk bron. D-OmniTwin hoeft niet alles fysiek over te nemen als ontsluiting aan de bron kan blijven.

### 2.2 Metadata en catalogus

Het platform moet een eigen cataloguslaag hebben waarin datasets, dataservices, indicatoren, modellen, kaarten en rapportages als herbruikbare objecten beschreven worden.

Die catalogus moet minimaal kunnen vastleggen:

- naam
- functionele beschrijving
- bron
- eigenaar
- actualiteit
- geografische dekking
- thematische indeling
- kwaliteit
- gevoeligheid
- gebruiksbeperkingen
- relatie met andere objecten
- versie
- publicatiestatus

Dit is nodig voor menselijk beheer, maar ook voor AI en federatief gebruik.

### 2.3 Semantische laag en ontologieën

Het platform moet niet alleen weten **welke** data er is, maar ook **wat die betekent**.

Daarom is een semantische laag nodig waarin:

- kernbegrippen worden vastgelegd
- relaties tussen begrippen expliciet zijn
- indicatoren worden gekoppeld aan thema's, objecttypen, bronnen en beleidscontext
- definities niet alleen in tekst, maar ook structureel beschikbaar zijn

Deze laag hoeft in de eerste fase niet academisch zwaar te zijn. Praktisch is beter: begin met een beperkte, beheerbare set kernbegrippen, relaties en definities die direct bruikbaar zijn in kaart, rapportage, beheer en AI.

### 2.4 Kwaliteit, herkomst en betrouwbaarheid

Het platform moet per dataset, indicator en afgeleid product kunnen laten zien:

- waar het vandaan komt
- wanneer het is bijgewerkt
- hoe volledig het is
- of er bewerkingen op zijn uitgevoerd
- welke beperkingen of kanttekeningen gelden
- of het geschikt is voor de beoogde toepassing

Dit is nodig om rapportages, vergelijkingen en AI-antwoorden verantwoord te kunnen gebruiken.

### 2.5 Dataproducten en afgeleide services

Het platform moet niet alleen ruwe data tonen, maar ook **dataproducten** kunnen aanbieden.

Voorbeelden:

- indicatorservices
- gebiedsprofielen
- benchmarkservices
- gebiedsdossiers
- thematische datasets
- API's voor buurten, deelgebieden en aggregaties
- afgeleide kaartlagen
- AI-geschikte kennisobjecten

Een dataproduct is dus meer dan een tabel of export. Het is een beheerbaar, bruikbaar object met bekende betekenis, kwaliteit en interface.

### 2.6 Kaart, 3D en interactieve analyse

De bestaande kracht van D-OmniTwin blijft een kernonderdeel.

Het platform moet gebruikers in staat stellen om:

- gebieden te selecteren
- indicatoren ruimtelijk te verkennen
- verschillen tussen gebieden te zien
- 2D en 3D visualisaties te gebruiken
- analyses door te klikken naar bron, betekenis en context
- kaart, kompas en rapportage in samenhang te gebruiken

De viewerlaag is dus geen losse voorkant, maar een functionele consumer van de onderliggende dataspace.

### 2.7 Rapportage en verklarende laag

Het platform moet gebiedsdossiers, benchmarkrapportages en thematische analyses kunnen genereren op basis van dezelfde onderliggende objecten, metadata en kwaliteitsinformatie.

Rapportage is dan niet een los eindproduct, maar een vorm van hergebruik van dezelfde ontsloten dataproducten.

### 2.8 AI als interactielaag boven betrouwbare ontsluiting

De AI-assistent blijft relevant, maar moet nadrukkelijk boven de dataspace-laag werken, niet er los naast.

Dat betekent:

- AI zoekt in beschreven indicatoren en semantische objecten
- AI gebruikt metadata, definities en kwaliteitsstatus
- AI stuurt kaart, kompas en rapportage aan via nette commando's
- AI blijft uitlegbaar, begrensd en herleidbaar

De AI is dus geen bron van waarheid, maar een **interactielaag op een beheerde informatiebasis**.

### 2.9 Toegang, rollen en publicatie

Het platform moet onderscheid kunnen maken tussen:

- publieke data
- interne data
- partnerdata
- beheerde conceptdata
- alleen-lezen gebruik
- beheer en publicatie

Daarvoor zijn rollen, publicatiestatussen en eenvoudige policy's nodig.

### 2.10 Federatieve aansluiting

Het platform moet later kunnen functioneren als een gemeentelijke dataspace die ook buiten de eigen organisatie kan aansluiten op andere dataspaces of datadiensten.

Dat betekent niet dat dit direct zwaar ingericht moet worden. Maar architectonisch moet wel vanaf het begin ruimte bestaan voor:

- federatief publiceren van metadata
- gecontroleerd delen van dataservices
- deelname van externe partijen
- logging en afspraken over gebruik

---

## 3. Gewenste architectuur

### 3.1 Architectuurprincipe

De architectuur moet simpel en uitlegbaar blijven.

De hoofdstructuur is:

**bronnen → ontsluitingslaag → metadata/semantiek/kwaliteit → dataproducten/services → toepassingen/AI/federatie**

D-OmniTwin moet daarmee functioneren als de laag die bronnen ordent, beschrijft, verrijkt en beschikbaar maakt.

### 3.2 Logische lagen

**Laag 1. Bronnen**
CBS, RIVM, BAG, EP-Online, gemeentelijke geo-bronnen, gebiedsindelingen, toekomstige sensordata, beleids- of domeinspecifieke registraties.

**Laag 2. Inname en verwerking**
Importscripts, datacontroles, mappings, normalisatie, verrijking, gebiedskoppelingen, indicatoropbouw. Bestaat al in belangrijke mate in de repo.

**Laag 3. Operationele datalaag**
PostgreSQL, PostGIS, pgvector waar relevant, beheerde tabellen voor bronnen, indicatoren, metadata, lineage en configuraties.

**Laag 4. Metadata-, kwaliteits- en semantieklaag**
Datasetmetadata, service metadata, definities, ontologieën of vocabularia, kwaliteitskenmerken, herkomst, versies, publicatiestatus, eigenaarschap. Geen losse documentatie, maar onderdeel van het platform.

**Laag 5. Ontsluitings- en orchestratie-laag**
FastAPI, verbreed: nette API's voor datasets, indicatoren, gebieden en rapportages, endpoints voor catalogus en metadata, endpoints voor kwaliteit en lineage, publicatie van dataproducten, later federatieve connectoren.

**Laag 6. Toepassingslaag**
Kaart, kompas, rapportages, admin, AI-assistent, toekomstige dashboards of externe consumers.

**Laag 7. Federatieve laag**
Pas later: publicatie van metadata naar buiten, gecontroleerde uitwisseling, connectoren, afspraken over gebruik en logging.

---

## 4. Wat uit de huidige repo herbruikbaar is

**Direct strategisch herbruikbaar:**
FastAPI backend, PostgreSQL/PostGIS, pgvector, ETL-structuur, indicator- en metadata-aanpak, kaart + kompas + rapportage als samenhangende consumer, admin-panel, AI-gestuurde interactielaag, lineage-fundament met bronnen en indicator_metadata.

**Herbruikbaar, maar door te trekken:**
Huidige metadata-aanpak, prompt- en AI-governance, configuratie van visualisatieprofielen, rapportservices, gebiedsselectie en aggregatielogica, beheer van prompts en modellen.

**Nog uit te bouwen:**
Formele cataloguslaag, expliciete semantische laag, publicatie- en lifecyclebeheer, kwaliteitsmodel per dataproduct, federatieve publicatie, externe identity en partnerrollen, nettere scheiding tussen interne operationele data en publiceerbare dataproducten.

---

## 5. Strategische uitgangspunten

1. **Bron blijft bron** — niet uit reflex centraliseren, alleen overnemen wat functioneel nodig is
2. **Metadata is eerste klas onderdeel** — geen bijlage of wiki-tekst, maar kernfunctionaliteit
3. **Semantiek is praktisch, niet theoretisch** — beheersbaar en direct bruikbaar
4. **Dataproducten boven ruwe tabellen** — beheerbare, bruikbare objecten met bekende betekenis
5. **AI werkt op beheerde informatie** — pas sterk inzetten waar kwaliteit en herkomst op orde zijn
6. **Federatie pas als de binnenkant klopt** — eerst gemeentelijke dataspace op orde
7. **Open waar mogelijk, vervangbaar waar verstandig** — open standaarden om praktische redenen
8. **Begrijpbaarheid boven architectonische luxe** — geen overcomplex platform

---

## 6. Gewenste bouwstenen en positionering

| Bouwsteen | Rol | Positie |
|---|---|---|
| PostgreSQL + PostGIS | Kernopslag | Strategisch |
| FastAPI | Hoofd-API en orchestratie-laag | Strategisch |
| Admin panel | Beheer van indicatoren, metadata, publicatie | Strategisch |
| ETL-scripts | Inname, verrijking, kwaliteitscontrole | Strategisch |
| pgvector | Semantisch zoeken | Tactisch, sterk aanbevolen |
| Lokale Ollama/LLM | AI-interactielaag | Tactisch |
| deck.gl / D3.js | Viewer en analyse | Strategisch voor huidige propositie |
| Mapbox | Basemap, vervangbaar houden | Tactisch |
| GeoNetwork of CKAN | Catalogus/open dataportaal | Strategisch zodra publicatie buiten app nodig |
| Metadata registry in eigen DB | Eerste stap voor dataset/service/kwaliteitsmetadata | Strategisch, direct |
| Ontologie/vocabulaire in eigen model | Semantische basis voor definities en AI | Strategisch, licht uitvoeren |
| Keycloak of vergelijkbaar | Identity en rollen | Tactisch |
| Reverse proxy + TLS | Veilige ontsluiting | Strategisch |
| MinIO | Bestanden, exports, artefacten | Tactisch |
| GeoServer | Alleen bij geo-servicepublicatie buiten de app | Optioneel |
| NGSI-LD | Alleen bij FIWARE-strategie | Strategisch bij FIWARE, anders niet |
| FIWARE componenten | Alleen bij contextdata/sensoren/linked-context | Optioneel tot tactisch |
| Dataspace connector | Bij federatieve uitwisseling | Later, tactisch |
| Volledige event-driven architectuur | Alleen bij schaal of realtime use-cases | Niet nu |

**Kern:** PostGIS + FastAPI + metadata + semantiek + dataproducten + viewer + beheer. Niet meteen te veel erboven zetten.

---

## 7. Groeirichting

**Fase 1 — basis op orde**
Metadata expliciet maken, kwaliteitsvelden en lineage uitbreiden, dataproducten benoemen en publiceren, admin uitbreiden met publicatie- en beheervelden, AI laten werken op beheerde metadata, catalogus intern beschikbaar maken.

**Fase 2 — nette publicatielaag**
Aparte catalogusfunctie, nette API-documentatie, publicatiestatussen, rollen en beheer, eventueel GeoNetwork of CKAN.

**Fase 3 — semantische verdieping**
Kernontologie of vocabulaire, koppeling indicatoren aan begrippen en thema's, semantische zoekingangen, betere AI-context.

**Fase 4 — federatieve aansluiting**
Connector, logging, partnerrollen, publicatie van metadata en services, afspraken over gebruik.

---

## 8. Kernformulering

D-OmniTwin ontwikkelt zich door naar een open, begrijpbaar en beheersbaar gemeentelijk dataspace-platform voor de fysieke leefomgeving. Het platform ontsluit bronnen niet alleen technisch, maar ook inhoudelijk: met metadata, kwaliteit, semantiek en herleidbaarheid. Daardoor kunnen kaart, kompas, rapportage, AI en later ook federatieve partners werken op dezelfde beheerde informatiebasis. De architectuur blijft pragmatisch: bron blijft bron, de regielaag komt erboven, en alleen die bouwstenen worden toegevoegd die functioneel echt nodig zijn.

---

## 9. Standaarden

Federatieve aansluiting werkt alleen als de standaarden kloppen. Dit zijn de leidende standaarden:

- **GGM** (Gemeentelijk Gegevensmodel) — interoperabiliteit met andere gemeenten
- **iSHARE / Gaia-X** — trust framework voor gecontroleerde data-uitwisseling
- **Common Ground** — principes voor ontkoppelde overheidsarchitectuur
- **NORA** — Nederlandse Overheid Referentie Architectuur
- **DCAT** — W3C-standaard voor metadata-catalogi; eigen metadata registry hierop aligneren
- **EUPL** — licentie voor alle code

---

## 10. Kernonderdelen die extra aandacht vragen

**Dynamische Kompas-hiërarchie**
De hiërarchie van het Kompas vormt zich dynamisch op basis van metadata en standaarden van aangesloten bronnen (FRLDS/FDS). Nieuwe thema's of regio's pluggen in zonder handmatige herbouw. Dit is de primaire technische innovatie van het platform.

**Data lineage als expliciete feature**
Gebruikers zien per indicator waar het vandaan komt, wanneer bijgewerkt en welke bewerkingen zijn uitgevoerd. Berekeningen zoals Z-scores zijn volledig navolgbaar. Lineage is geen bijlage maar onderdeel van het datamodel — dit heeft directe implicaties voor het databaseschema.

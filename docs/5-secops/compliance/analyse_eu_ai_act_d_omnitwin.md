# Analyse AI-toetsing D-OmniTwin: Van Definitie naar Risicokwalificatie

De reactie van de AI-Officer legt direct een klassieke denkfout bloot: er wordt een ontologische vraag beantwoord (*"Is het AI?"*), terwijl jullie een risicogebaseerde governance-vraag stellen (*"Moet het tijdelijk uit en is het hoog-risico?"*).

Sterker nog: kijk eens naar de onderste twee regels van de reactie van de AI-Officer (*"Bronvermelding: AI Act NL.pdf / AI en Algoritmern (NL).pdf"*). Dat is de exacte output-structuur van een lokaal RAG-systeem (zoals AnythingLLM of een vergelijkbare document-assistent). De ironie wil dat de AI-Officer jullie vraag hoogstwaarschijnlijk door een AI-tool heeft gehaald die onder de motorkap exact hetzelfde doet als Component B (met een embeddingmodel zoeken naar relevante tekstpassages in een pdf) om vervolgens te concluderen dat een embeddingmodel "AI" is — zonder jullie drie daadwerkelijke toetsingsvragen te beantwoorden.

Als we deze casus tot op het bot ontleden vanuit *First Principles* en de daadwerkelijke wettekst van de EU AI Act, ontstaat een veel scherper beeld.

---

## 1. Deconstructie vanuit First Principles: Wat gebeurt hier echt?

Om tot een zuiver besluit te komen, moeten we twee aannames corrigeren: één bij de AI-Officer en één in de formulering van jullie eigen issue.

### A. De denkfout "Het is AI, dus het valt onder een compliance-stop"
De EU AI Act is geen technologie-wet, maar een risicowet.

* **Artikel 3 lid 1 (De definitie):** De AI-Officer heeft gelijk dat `multilingual-e5-small` juridisch gezien onder de definitie van een AI-systeem valt (het model gebruikt machine learning om uit tekstinput een vector-representatie en relevantie-rangschikking af te leiden, conform de *Commission Guidelines on the definition of an AI system* van februari 2025).
* **De 'Zo-Wat?':** Het simpele feit dat software onder Artikel 3 lid 1 valt, roept onder de EU AI Act nul verboden en nul zware toetsingsplichten in het leven. Verplichtingen ontstaan pas wanneer een specifiek gebruiksdoel (*use-case*) in de categorie **Hoog-Risico** (Artikel 6 + Bijlage III) of **Specifiek Transparantierisico** (Artikel 50) valt. Voor de overige $90\%$ van alle AI-systemen (**Minimaal Risico**, zoals spamfilters en zoekindexen) legt de EU AI Act geen enkele restrictie op, behalve de algemene plicht tot AI-geletterdheid (Artikel 4).

### B. De wiskundige correctie: `multilingual-e5-small` ís deterministisch
In de issue-tekst noemt het projectteam `pg_trgm` het "deterministische alternatief". Daarmee wek je bij een jurist of AI-Officer onbedoeld de indruk dat jullie embeddingmodel niet-deterministisch of onvoorspelbaar zou zijn. Wiskundig klopt dat niet:

* **Generatieve AI (Component A - Qwen/Ollama)** werkt met kansverdelingen en *stochastic sampling* ($\text{temperature} > 0$) om token voor token nieuwe tekst te fabriceren. Dat is niet-deterministisch en kan hallucineren.
* **Semantisch zoeken (Component B - `multilingual-e5-small`)** heeft bevroren gewichten (`float16`), traint niet bij en heeft geen temperature. Tijdens runtime is het model een $100\%$ deterministische algebraïsche functie $f: \text{Tekst} \rightarrow \mathbb{R}^{384}$. Elke keer dat een beleidsmaker het woord *"armoede"* intypt, rolt daar tot op de laatste decimaal exact dezelfde vector $\mathbf{A}$ uit. Vervolgens berekent `pgvector` via de cosinus-afstand ten opzichte van de vaste indicatorvector $\mathbf{B}$:

$$\text{afstand}(\mathbf{A}, \mathbf{B}) = 1 - \frac{\mathbf{A} \cdot \mathbf{B}}{\Vert\mathbf{A}\Vert \Vert\mathbf{B}\Vert}$$

Bij een ongewijzigde indicatorentabel geeft dezelfde zoekopdracht altijd exact dezelfde, $100\%$ reproduceerbare rangschikking. Het verschil tussen `pg_trgm` en `multilingual-e5-small` is dus niet determinisme versus willekeur, maar het meten van afstand op basis van lettergrepen (trigrammen) versus betekenisruimte.

---

## 2. Wet- en Regelgevingstoets: Component A versus Component B

Wanneer we beide componenten naast de EU AI Act, de AVG en de kaders voor het Gemeentelijk Algoritmeregister leggen, ziet de juridische realiteit er als volgt uit:

| Toetsingscriterium | Component A: Generatieve AI (LLM: Chat & Rapporten) | Component B: Semantisch Zoeken (`multilingual-e5-small` + `pgvector`) |
| :--- | :--- | :--- |
| **EU AI Act Art. 3(1)** *(Is het een AI-systeem?)* | **Ja.** Genereert adaptieve tekst en samenvattingen via een groot taalmodel. | **Ja.** Maakt via machine learning inferenties over semantische nabijheid van zoektermen. |
| **EU AI Act Risicoklasse** *(Art. 5, 6, 50)* | **Beperkt Risico (Art. 50).** Geen Hoog-Risico (want geaggregeerde gebiedsdata, geen besluiten over individuen), maar wél directe mens-interactie (chatbot) en synthetische tekstgeneratie. | **Minimaal / Geen Risico.** Uitgezonderd van Hoog-Risico (zelfs expliciet via Art. 6 lid 3: puur voorbereidende zoek-/indexeringstaak zonder materiële sturing van besluiten) en géén Art. 50 (geen dialoog of synthetische content). |
| **AVG / DPIA-plicht** *(Art. 35 AVG)* | **Alleen indien vrije tekst persoonsgegevens bevat.** In de chat zou een gebruiker theoretisch een naam kunnen typen; vereist verwerkers-/logging-afspraken. | **Nee ($0\%$).** Draait $100\%$ lokaal/offline in container en matcht een zoekterm uitsluitend op metadata-titels van statistische gebiedsindicatoren. Geen persoonsgegevens = geen DPIA. |
| **Algoritmeregister** *(BZK / VNG-kaders)* | **Ja (Transparantie).** Zodra dit live gaat voor bestuurlijke duiding, hoort dit als ondersteunend generatief systeem in het register thuis. | **Nee (Niet publicatieplichtig).** Het is een interne zoekindex op metadata, geen impactvol of besluitvormend algoritme dat burgers raakt. |
| **Inhoudelijk & Maatschappelijk Risico** | **Hoog bij ongetoetste inzet:** Hallucinatie in beleidsrapporten of vertekende duiding van scores. Tijdelijk uitschakelen is vakmatig terecht. | **Andersom:** Het uitschakelen veroorzaakt juist schade. Met `pg_trgm` vindt een beleidsadviseur die zoekt op *"eenzaamheid"* de indicator *"sociale cohesie"* niet meer ($0\%$ letter-overlap). |

---

## 3. Concrete beantwoording van jullie 3 Toetsingsvragen

Wat betekent deze analyse voor de drie vragen die jullie hebben voorgelegd en voor de architectuur van D-OmniTwin?

### Vraag 1: Reikwijdte uitschakeling (Semantisch Zoeken)
* **Oordeel:** Beperk de tijdelijke uitschakeling uitsluitend tot **Component A (Generatieve AI)**. Laat **Component B (Semantisch zoeken)** actief.
* **Fundamenteel argument richting de AI-Officer:** Component B valt onder de EU AI Act in de laagste categorie (Minimaal Risico), verwerkt geen persoonsgegevens, verzint geen data en toont uitsluitend reeds gevalideerde indicatortitels uit de database. Als de gemeente ieder systeem dat onder Artikel 3 lid 1 (*"Ja, is AI"*) valt preventief moet uitschakelen, moet de gemeente vandaag ook de zoekbalk van Microsoft 365, SharePoint, Outlook en het zaaksysteem uitzetten — die werken onder de motorkap met exact dezelfde vector-embeddings. Het uitschakelen van B verlaagt het compliance-risico met $0\%$, maar schaadt direct het vakmanschap van beleidsmakers doordat relevante gebiedsindicatoren onvindbaar worden zodra ze niet het exacte trefwoord raden.

### Vraag 2: Kwalificatie Algoritmeregister
* **Oordeel:** Component B is géén hoog-risico algoritme (valt buiten Bijlage III en valt bovendien onder de expliciete uitzondering voor ondersteunende zoektaken in Artikel 6 lid 3 EU AI Act) en hoeft niet in het publieke Algoritmeregister.
* **Best Practice (Governance):** Neem Component B wél als één regel op in het interne gemeentelijke overzicht (of in `docs/5-secops/compliance/`) met de classificatie: *"EU AI Act: AI-systeem (Art. 3.1) -> Risicoklasse: Minimaal risico (interne semantische zoekindex op openbare indicator-metadata, lokaal/offline, deterministische cosinus-ranking, geen persoonsgegevens)"*. Daarmee heb je $100\%$ aantoonbare accountability zonder bureaucratische vertraging.

### Vraag 3: Tekstkeuze Disclaimer
* **Oordeel:** De voorgestelde disclaimer is uitstekend en feitelijk exact juist, juist omdat deze specifiek benoemt dat *"AI-gegenereerde samenvattingen en duidingen"* tijdelijk zijn uitgeschakeld. Dat dekt exact Component A, terwijl de zoekfunctie (Component B) gewoon zijn werk blijft doen om de cijfers en kaarten vindbaar te houden.

---

## 4. Technische & Strategische Next Steps

Om te voorkomen dat je in de code en in de discussie met de AI-Officer alles op één hoop blijft gooien, adviseer ik drie directe stappen:

1. **Splits de configuratie-vlag in `omnitwin.config`:**
   Gebruik niet één generieke parameter `AI_INGESCHAKELD=false`. Daarmee bevestig je in je eigen codebase het misverstand dat alle AI hetzelfde risico draagt. Splits dit in twee expliciete parameters:
   * `GENERATIVE_AI_ENABLED=false` (schakelt Chat-LLM en Rapport-duiding uit en toont de disclaimer).
   * `SEMANTIC_SEARCH_ENABLED=true` (houdt `multilingual-e5-small` + `pgvector` actief).

2. **Scherp `services/deduplicatie_service.py` (onderdeel A3) aan:**
   In het issue staat Deduplicatie (suggesties bij indicatormatching in de beheeromgeving) nu onder Generatieve AI (A). Vraag jezelf vanuit *First Principles* af: waarom zou je een zwaar, hallucinerend LLM (Qwen) gebruiken om te kijken of twee indicatortitels op elkaar lijken, als je al `multilingual-e5-small` + `pgvector` in je stack hebt zitten? Als je deduplicatie in het beheer óók via diezelfde deterministische cosinus-afstand (`<=>`) laat lopen, heb je daar helemaal geen Generatieve AI voor nodig en kan die functie gewoon aan blijven staan.

3. **Stuur een constructieve, kaderstellende reactie terug naar de AI-Officer:**
   Erken het antwoord van de AI-Officer op de definitievraag (*"Klopt, volgens Art. 3 lid 1 is het inderdaad een AI-systeem"*), en zet daar direct de vervolgstap uit de EU AI Act achter (*"En omdat we na de definitietoets de risicoclassificatie van de AI Act toepassen, valt B onder Minimaal Risico en A onder Art. 50..."*). Zo help je de AI-Officer uit de 'alles-wat-AI-heet-moet-op-slot'-reflex, zonder dat het een welles-nietes-discussie wordt.

---

**Waar zullen we nu op doorpakken?** 
Geef even aan of je dit wilt inzetten voor **Communicatie** (de reactie naar de AI-Officer / expertgroep) of voor **Maak/Executie** (het herschrijven van het technische issue en de compliance-notitie voor `docs/5-secops/compliance/`), en wat de belangrijkste zorg van jullie AI-Officer op dit moment is.
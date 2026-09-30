# D-OmniTwin Gebruikersreview

## Doel van deze review

Tijdens het gebruik van de applicatie valt op dat D-OmniTwin veel functionaliteit biedt. Gebruikers kunnen werken met honderden indicatoren, verschillende gebiedsniveaus, het D-Omni Kompas, AI-ondersteunende analyses en rapportages.

Deze review richt zich daarom niet uitsluitend op vormgeving of afzonderlijke functionaliteiten. De nadruk ligt op de vraag:

> Ondersteunt D-OmniTwin gebruikers daadwerkelijk bij het beantwoorden van hun informatievraag, of moeten zij zelf nog veel analyse- en interpretatiewerk verrichten?

Het doel van deze review is niet om vast te stellen hoeveel functionaliteit aanwezig is, maar om te beoordelen of de aanwezige functionaliteit toegankelijk, begrijpelijk en bruikbaar is voor de verschillende doelgroepen waarvoor D-OmniTwin is ontwikkeld.

---

# Gebruikersprofielen

Per profiel wordt een concrete vraag geformuleerd die aansluit bij de beschikbare indicatoren binnen de applicatie. Vervolgens wordt beoordeeld of de gebruiker deze informatie eenvoudig kan vinden en interpreteren.

## Overzicht

| Gebruikersprofiel | Centrale vraag |
|-------------------|----------------|
| Beleidsadviseur Sociaal Domein | In welke buurten zien we de meeste signalen van eenzaamheid en moeite met rondkomen? |
| Wijkregisseur | Welke buurten vertonen signalen van verminderde sociale samenhang? |
| Gezondheidsadviseur | Welke buurten scoren minder goed op gezondheid en leefstijl? |
| Bestuurder | Wat zijn de belangrijkste aandachtspunten van deze buurt? |
| Nieuwe gebruiker | Hoe gezond is mijn buurt en hoe weet ik of dat goed of slecht is? |

---

# 1. Beleidsadviseur Sociaal Domein

## Doel

De beleidsadviseur gebruikt D-OmniTwin om maatschappelijke ontwikkelingen binnen buurten en wijken te analyseren en beleidskeuzes te onderbouwen.

### Informatiebehoefte

- Buurten vergelijken
- Patronen herkennen
- Prioriteiten bepalen
- Ontwikkelingen onderbouwen met data

### Uitgevoerde stappen

1. Gebiedstype ingesteld op CBS-buurten.
2. Gezocht naar de indicator **Eenzaamheid**.
3. Kaart laten kleuren op basis van deze indicator.
4. Detailinformatie van een buurt opgevraagd.
5. D-Omni Kompas geraadpleegd.
6. AI-functionaliteit gebruikt voor vergelijking van buurten.

## Bevindingen

### Positief

- Indicatoren zijn relatief eenvoudig vindbaar.
- Kaartvisualisatie geeft snel een eerste beeld.
- Trends en aanvullende context zijn beschikbaar.

### Verbeterpunten

De applicatie toont veel data, maar geeft beperkt antwoord op de daadwerkelijke beleidsvraag.

Wat ontbreekt:

- Top 5 buurten met hoogste eenzaamheid.
- Grootste stijgers en dalers.
- Afwijkingen ten opzichte van gemiddelden.
- Automatische signalering van aandachtspunten.

Daarnaast vereist het verkrijgen van inzichten meerdere handmatige stappen. Gebruikers moeten zelf buurten identificeren, onthouden en vergelijken.

### UX-observatie

De zoekfunctie binnen het Kompas gaf een foutmelding (*undefined*), waardoor navigatie en interpretatie werden bemoeilijkt.

---

# 2. Wijkregisseur

## Vraag

> Welke buurten vertonen signalen van verminderde sociale samenhang?

### Bevindingen

Indicatoren zoals vrijwilligerswerk, mantelzorg en eenzaamheid zijn afzonderlijk beschikbaar.

Hoewel de gebiedsvergelijking helpt, moet de gebruiker zelf:

- indicatoren combineren;
- patronen herkennen;
- conclusies trekken.

De applicatie ondersteunt onvoldoende bij het automatisch identificeren van buurten die aandacht vragen.

### Aanbevelingen

- Toon een Top 5 van buurten met hoogste en laagste scores.
- Toon buurten die het sterkst afwijken van het gemiddelde.
- Maak trends en afwijkingen direct zichtbaar vanuit de kaartweergave.

---

# 3. Gezondheidsadviseur

## Vraag

> Welke buurten scoren minder goed op gezondheid en leefstijl?

### Bevindingen

De kaart maakt verschillen zichtbaar, maar beantwoordt niet direct welke buurten de grootste gezondheidsuitdagingen hebben.

De gebiedsvergelijking biedt aanvullende context, maar ligt niet direct voor de hand vanuit de primaire gebruikersroute.

### Aanbevelingen

- Toon buurten met de laagste gezondheidsscores.
- Vergelijk direct met gemeentelijke en Friese gemiddelden.
- Vertaal indicatoren naar concrete gezondheidsrisico's en prioriteiten.

---

# 4. Bestuurder

## Vraag

> Wat zijn de belangrijkste aandachtspunten van deze buurt?

### Bevindingen

Bestuurders zoeken doorgaans geen afzonderlijke indicatoren, maar een samenvatting van kansen, risico's en prioriteiten.

Het Kompas helpt hierbij, maar de rapportage vraagt nog veel interpretatie.

### Aanbevelingen

- Automatische samenvatting van belangrijkste aandachtspunten.
- Prioriteitenlijst per buurt.
- Top 5 positieve en negatieve afwijkingen ten opzichte van gemiddelden.

---

# 5. Nieuwe gebruiker zonder data-achtergrond

## Vraag

> Hoe gezond is mijn buurt en hoe weet ik of dat goed of slecht is?

### Bevindingen

Nieuwe gebruikers worden geconfronteerd met:

- veel indicatoren;
- verschillende gebiedsniveaus;
- het Kompas;
- rapportages;
- vaktermen.

Daardoor ontstaat een relatief hoge instapdrempel.

### Aanbevelingen

- Meer toelichting in gewone taal.
- Context bij indicatoren.
- Uitleg waarom een score goed of slecht is.
- Geleide gebruikersroutes ("Start hier").

---

# UX- en Designobservaties

## Wat werkt goed

- Grote hoeveelheid beschikbare data.
- Sterke kaartvisualisaties.
- Integratie van Kompas, rapportages en AI-functionaliteit.
- Mogelijkheid om buurten en gebieden te vergelijken.

## Waar gebruikers vastlopen

1. Data wordt onvoldoende vertaald naar inzichten.
2. Veel functionaliteiten vereisen kennis van het platform.
3. Gebruikers moeten zelf verbanden leggen.
4. Prioriteiten worden niet automatisch zichtbaar gemaakt.
5. Navigatie naar antwoorden vraagt te veel stappen.

---

# Strategische Verbeterkansen

## Van Data naar Inzicht

De grootste kans ligt niet in het toevoegen van meer data, maar in het beter vertalen van bestaande data naar antwoorden.

### Mogelijke functionaliteiten

#### Signalering

- Automatische aandachtspunten.
- Grootste stijgers en dalers.
- Afwijkingen van gemiddelden.

#### Prioritering

- Top 5 buurten per indicator.
- Top 5 risico's per buurt.
- Prioriteiten per thema.

#### AI-ondersteuning

- Automatische beantwoording van gebruikersvragen.
- Samenvattingen in natuurlijke taal.
- Verklaringen van opvallende patronen.

#### Context

- Vergelijking met gemeentelijke gemiddelden.
- Vergelijking met provinciale gemiddelden.
- Benchmarking met vergelijkbare buurten.

---

# Centrale Conclusie

De observaties uit de verschillende gebruikersprofielen laten dezelfde uitdaging zien.

D-OmniTwin biedt veel data, analyses en functionaliteit, maar voelt momenteel vooral als een platform waarin gebruikers zelf inzichten moeten ontdekken.

De grootste verbeterkans ligt daarom niet primair in uitbreiding van de databronnen, maar in het sneller en duidelijker presenteren van inzichten die direct aansluiten op de vraag van de gebruiker.

**Kort samengevat:**

> D-OmniTwin excelleert in het aanbieden van data, maar kan aanzienlijk meer waarde leveren door gebruikers sneller van data naar inzicht, conclusie en handelingsperspectief te begeleiden.
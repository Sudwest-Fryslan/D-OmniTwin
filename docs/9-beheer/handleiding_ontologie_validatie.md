# Beheerdershandleiding: AI Ontologie Validatie & Zichtbaarheid Data

**Versie:** 1.0  
**Laatst bijgewerkt:** Juni 2026  
**Domein:** Beheer & Applicatie Data  

---

## 1. Doel & Achtergrond
Binnen D-OmniTwin tonen we bij indicatoren (zoals 'Vrijwilliger', 'Gezondheid', etc.) extra context in het D-Omni Kompas onder de tab **Ontologie**. Omdat het handmatig schrijven van deze complexe definities en contexten veel tijd kost, maakt het systeem gebruik van een AI (LLM) om deze teksten automatisch op te stellen.

Omdat een AI soms kan hallucineren (feitelijk onjuiste verbanden leggen) of nuances mist die voor Fryslân essentieel zijn, is er gekozen voor een **Human-in-the-Loop** validatie-proces. Dit betekent simpelweg: Een AI schrijft de eerste draft, maar **een mens moet het altijd goedkeuren** voordat het publiek het te zien krijgt.

Deze handleiding legt uit hoe dit in de praktijk werkt en waarom bepaalde informatie in de frontend verborgen kan lijken.

---

## 2. De Lifecycle van een Ontologie Beschrijving

Wanneer je in de frontend (het dashboard) klikt op een indicator en de Ontologie-tab lijkt stuk of toont *"Geen ontologische beschrijving beschikbaar"*, dan bevindt de indicator zich vrijwel zeker in status 1 of 2.

Elke indicator kent één van de volgende ontologie-statussen:

### 1. 🤖 Draft (Geen / Startfase)
- **Status:** Er is nog helemaal geen tekst gegenereerd of beschikbaar.
- **Frontend (Kompas):** De 'Ontologie' tab is óf onzichtbaar, óf toont de standaard fallback tekst.

### 2. 🟠 AI-Voorstel (`beoordeeld_ai`)
- **Status:** De AI heeft succesvol op de achtergrond een concepttekst geschreven en in de database gezet (als `beschrijving_ai`).
- **Beheerpaneel:** Je ziet in de lijst met indicatoren een **oranje "AI" label**.
- **Frontend (Kompas):** 🚫 **Niet zichtbaar!** Het systeem weigert deze data naar de live applicatie te sturen omdat een menselijke beheerder de tekst nog niet heeft gecontroleerd. De frontend toont dus nog steeds *"Geen ontologische beschrijving beschikbaar"*.

### 3. ✅ Gevalideerd (`goedgekeurd_mens`)
- **Status:** Een beheerder heeft de concepttekst gelezen, (eventueel) aangepast en formeel goedgekeurd.
- **Database:** De tekst wordt nu definitief weggeschreven in het veld `ontologische_beschrijving`.
- **Frontend (Kompas):** 🎉 **Direct Zichtbaar!** Zodra de gebruiker de indicator op de kaart aanklikt, toont het paneel direct de goedgekeurde tekst.

---

## 3. Hoe keur ik een beschrijving goed? (Stappenplan)

1. Open de **Beheeromgeving** (Admin Panel, default: `http://localhost:5173/admin`).
2. Ga in het zijmenu naar **Indicatoren**.
3. Selecteer de indicator in de tabel (let op de indicatoren met een oranje 'AI' badge).
4. Navigeer in het rechter detailpaneel naar het tabblad **"Ontologie Validatie"**.
5. Je ziet nu twee velden:
   - **AI-gegenereerde beschrijving:** (Alleen-lezen). Dit is wat de AI heeft bedacht.
   - **Gevalideerde beschrijving:** (Bewerkbaar). Hierin staat in eerste instantie een kopie van de AI-tekst. Hier kun je spelfouten uithalen, nuances toevoegen of zinnen wissen.
6. Ben je tevreden met de inhoud? Klik dan onderaan op de blauwe knop **"✓ Goedkeuren"**.
7. De indicator krijgt direct een groen vinkje in de lijst. Je werk zit er op; de informatie staat nu live!

> **Tip:** Heb je de tekst per ongeluk helemaal gewist en wil je opnieuw beginnen met de AI-versie? Gebruik de **"Reset"** knop naast "Goedkeuren" om de tekst terug te zetten naar de originele AI-draft.

---

## 4. Bonus: Waarom is de Timeslider / Historische grafiek verborgen?
Als je toch bezig bent met databeheer, is het handig om ook dit te weten:

Soms klik je op een indicator in de frontend en zie je de melding *"Geen historische data (nog) beschikbaar"* in de grafiek, terwijl de Timeslider (tijdschuif) ontbreekt.

**Oorzaak:**
Het systeem verbergt de trendlijn (grafiek) en de tijdschuif automatisch als er in de database voor het huidige gebied **slechts 1 meetjaar (1 datapunt)** aanwezig is. Het heeft immers geen zin om een lijn te trekken of animaties af te spelen over tijd, als we maar data van één jaar (bijv. 2024) hebben.
Zodra de dataset in de toekomst wordt verrijkt met een tweede meetmoment (bijv. 2025), zullen de grafieklijn en timeslider vanzelf verschijnen op het kompas.

# 🚀 Inventarisatie & Ontwerp: ETL / Dataspace Beheerpagina

Op basis van de huidige architectuur, de `BRAINDUMP.md`, de `ROADMAP.md` en de aangeleverde UI-inspiratie (Way2GO server) heb ik een eerste verkenning en analyse gemaakt voor de nieuwe ETL / Dataspace beheeromgeving. 

Hieronder vind je de inventarisatie van wat we nu hebben en een conceptueel plan voor hoe we dit slim kunnen integreren.

---

## 1. 📦 Huidige Inventaris (Wat we nu hebben)

Momenteel is onze data-pipeline vrij gefragmenteerd en vooral gericht op backend-scripts:
- **Scripts (`/scripts` en `/ETL`):** We hebben losse Python scripts voor import (`run_bag_import.py`, `import_extra_indicatoren.py`), validatie (`validate_gebiedsmonitor.py`) en metadata (`global_metadata_enrichment.py`). Deze moeten nu via de command-line gedraaid worden. Er is geen centrale UI voor.
- **Externe Kaartlagen (`ExterneKaartlagenPage.tsx`):** We hebben al een werkende beheerpagina voor WFS/WMS en lokale GeoJSON/GPKG bestanden. Dit is echter puur gericht op *visuele overlays* op de kaart en (deels) het verrijken van CBS-buurten.
- **Database Export/Seed:** Momenteel gebeurt dit handmatig (bijv. via `pg_dump` of door init-scripts aan te passen).
- **Dataspace Visie:** In `BRAINDUMP.md` staat de ambitie beschreven om D-OmniTwin in te zetten als "Dataspace Orchestrator". Hierbij halen we data "on the fly" op bij de bron (bijv. FRLDS) zonder alles te kopiëren.

---

## 2. 🎯 Doelstellingen van de nieuwe Beheerpagina

De nieuwe pagina moet het kloppend hart worden van de D-OmniTwin data-engine, met de volgende kernfuncties:
1. **Visuele ETL Pijplijnen:** Weergave van processen (zoals de BAG Extract uit je voorbeeld) als gekoppelde blokken (nodes). In één oogopslag zien waar het proces zich bevindt en waar errors optreden.
2. **Taakbeheer & Executie:** Scripts (zoals `run_bag_import.py`) direct kunnen starten, pauzeren of opnieuw proberen vanuit de UI, met live feedback (percentages en logs).
3. **Data Virtualisatie (Dataspace Orchestrator):** Uitbreiding op de 'Externe Lagen'. Waar de huidige Externe Lagen vooral GIS-overlays zijn, moet dit deel het mogelijk maken om externe API's/OData (bijv. via FRLDS) direct te mappen naar de Kompas-indicatoren zónder fysieke data-opslag (data bij de bron).
4. **Seedfiles & Backups:** Eén druk op de knop om de huidige configuratie (Kompas structuur, Indicatoren, Kleurschema's) te exporteren als `.json` of `.sql` seedfile, zodat we makkelijk nieuwe instanties of demo-omgevingen kunnen optrekken.

---

## 3. 🎨 Functioneel Ontwerp & UI (geïnspireerd op de screenshot)

Om de UI uit het voorbeeld na te bouwen in onze bestaande React (MUI/Tailwind/Custom CSS) structuur, stel ik de volgende layout voor:

### A. Linker Sidebar (Navigatie & Overzicht)
- **Status Categorieën:** "Alle taken", "Geplande taken", "Taken in uitvoering", "Voltooid", "Fouten".
- Met kleine "badges" (bijv. een rood bolletje met een 2 erin voor taken met fouten).

### B. Hoofdvenster: Visuele DAG (Directed Acyclic Graph)
- **Node-based View:** Gebruik van een library zoals `React Flow` (zeer populair en krachtig voor dit soort diagrammen).
- Elke stap in het ETL proces (bijv. `BAG Download` → `Woonplaats` → `OpenbareRuimte`) wordt een blokje.
- **Kleurcodering:** 
  - 🟩 Groen (Voltooid / 100%)
  - 🟦 Blauw (Bezig / 45%)
  - 🟥 Rood (Error / 3%)
  - ⬜ Wit/Grijs (In wachtrij / 0%)

### C. Detailvenster (Onderaan of Rechterpaneel)
Als je op een node (bijv. "OpenbareRuimte") klikt:
- Grote voortgangscirkel (bijv. 100%).
- **Actieknoppen:** Play (starten), Pause (pauzeren), Settings (configuratie), Refresh/Retry (opnieuw draaien).
- **Log output:** Een realtime log-stream met details (bijv. *"355.036 OpenbareRuimte(en) geladen in 00:00:06"*).

---

## 4. ⚙️ Architectuur & Technische Impact

Om dit te realiseren moeten we zowel frontend als backend flink uitbreiden:

**Backend (FastAPI & Task Runner):**
- De huidige losse scripts moeten worden omgevormd tot **Async Taken**. We kunnen hiervoor gebruik maken van `Celery` (met Redis) of, om de stack licht te houden, de ingebouwde `BackgroundTasks` van FastAPI gecombineerd met een `etl_taken` log-tabel in de database.
- We hebben endpoints nodig voor: `GET /api/etl/tasks`, `POST /api/etl/tasks/{id}/start`, en `GET /api/etl/tasks/{id}/logs` (eventueel via WebSockets voor live-updates).
- Een endpoint voor het genereren van de **seedfile**: `GET /api/export/seedfile`.

**Frontend (React Admin Panel):**
- Installatie van `reactflow` (of een vergelijkbare library) voor de visuele procesweergave.
- Nieuwe pagina: `/admin/dataspace` (of `/admin/etl`).

---

> [!IMPORTANT]
> ## ❓ Open Vragen voor de Vervolgstap
> Voordat we code gaan kloppen, wil ik graag het volgende met je afstemmen:
> 
> 1. **Prioriteit binnen de pagina:** Zullen we starten met het **Visuele Taakbeheer (de scripts en nodes)**, of wil je eerst focussen op de **Seedfile generator**, of juist op het **Dataspace/Virtualisatie** concept? 
> 2. **Task Runner Keuze:** Gaan we voor een volledige queueing-oplossing zoals `Celery + Redis` (zwaarder, maar schaalbaar), of bouwen we eerst een lichtere variant in FastAPI (waarbij we processen tracken via de database)?
> 3. **Visuele Graph:** Ben je akkoord dat we de library `React Flow` toevoegen aan de frontend voor het bouwen van die mooie flowcharts uit je voorbeeld?

Lees het rustig door en laat me weten hoe je de eerste echte bouwsteen voor je ziet!

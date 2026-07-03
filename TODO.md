# TODO - D-OmniTwin Roadmap

**Laatste Update:** 30 juni 2026 (Dag 79)
**Status:** Sprint 18 ✅ Afgerond | Sprint 19 📌 Gepland

> **Huidige Sprint:** Sprint 19 — Van Data naar Inzicht
> **Branch:** `feature/sprint-19-data-naar-inzicht` (aan te maken bij start Sprint 19)
> **Spec:** [`docs/7-projectmanagement/archief/sprint-19-plan_data-naar-inzicht.md`](./docs/7-projectmanagement/archief/sprint-19-plan_data-naar-inzicht.md)

---

## ✅ Sprint 18: IJsselmeerkust als Besluitinstrument (Afgerond)

**Doel:** D-OmniTwin transformeren van een verkenningsinstrument naar een besluitondersteunend instrument — getoetst aan de casus IJsselmeerkust & Wadden (Makkum, Workum, Koudum).  
**Aanleiding:** NM-001 gap-analyse + TC-06-001 staan al maanden open en zijn nog nooit volledig doorlopen.  
**Spec:** [`docs/7-projectmanagement/archief/sprint-18-plan_ijsselmeerkust-besluitinstrument.md`](./docs/7-projectmanagement/archief/sprint-18-plan_ijsselmeerkust-besluitinstrument.md)  
**GitHub Issue:** Aan te maken  
**Branch:** `feature/sprint-18-ijsselmeerkust`

### 🔧 Voorbereiding (voor eerste codesessie)
- [x] **GitHub Issue aanmaken** op `github.com/TLaan/D-OmniTwin`
    - Titel: `feat: IJsselmeerkust als Besluitinstrument (Sprint 18)`
    - Labels: `enhancement`, `ux`, `data`, `frontend`, `backend`, `sprint-18`
    - Link naar sprintplan + NM-001 + TC-06-001
- [x] **Feature branch aanmaken en pushen:**
    ```bash
    git checkout -b feature/sprint-18-ijsselmeerkust
    git push -u origin feature/sprint-18-ijsselmeerkust
    ```
- [x] **Worktree aanmaken** (demo-omgeving op `main` intact houden):
    ```bash
    git worktree add ../D-OmniTwin-DEMO main
    ```
- [ ] **Open vragen beantwoorden** (zie sprintplan §Open vragen):
    - BAG woonplaatsen dataset beschikbaar in `data/`?
    - Hoeveel historische CBS-meetmomenten in DB? (`SELECT COUNT(DISTINCT jaar) FROM gebied_data`)
    - Benchmark: alleen kernen-onderling of ook Fries gemiddelde?

### Track A — Duiding & Context (Kompas-paneel) ✅
- [x] **A1 — Bronvermelding & Ontologie**
    - [x] Bron en peildatum zijn reeds zichtbaar.
    - [x] Tooltip of externe link toevoegen aan de bron-weergave.
    - [x] Ontologische beschrijving ophalen via API en weergeven als tabblad naast 'Definitie'.
    - [x] Acceptatie: TC-02-001 stap 3 → ✅
- [x] **A2 — Z-score uitleg (contexttooltip)** *(Obsoluut)*
    - [x] Uit het Kompas gehaald en in Track G (Sessie 4) opgenomen in het rapportpaneel.
    - [x] Acceptatie: Niet meer relevant in Kompas.
- [x] **A3 — Interactieve Trendlijn & Timeslider**
    - [x] Basis trendlijn (Chart.js) toont bij ≥ 2 meetmomenten.
    - [x] Fallback melding tonen wanneer er geen/onvoldoende historische data is.
    - [x] Klikken op een trendlijn-jaar updatet de kaart met historische data.
    - [x] Timeslider (play/pauze) onder de grafiek toevoegen om kaart-historie af te spelen.
    - [x] Acceptatie: TC-02-001 stap 6 → ✅ (was ❌)

### Track B — Selectielaag: BAG Woonplaatsen + Externe Lagen ✅
- [x] **B1 — BAG woonplaatsen (via WFS proxy / PDOK)**
    - [x] `routers/externe_lagen.py` toegevoegd (externe_kaartlagen tabel)
    - [x] Woonplaatsen Fryslân ophalen en cachen
- [x] **B2 — Woonplaatsen toggle in Kaartlagen-paneel**
    - [x] Dynamische toggles via `GET /api/externe-lagen`
    - [x] GeoJsonLayer overlay met tooltip
- [x] **B3 — Kompas aggregeert op externe laag-niveau**
    - [x] Centroid-based selectie (ST_Contains + ST_Centroid)
    - [x] Badge toont aantal buurten, Kompas laadt correct
- [x] **B4 — Lokale geodata als externe kaartlaag (Upload)**
    - [x] `bron_type: 'lokaal'` + GPKG/GeoJSON file uploads
    - [x] `POST /api/admin/externe-lagen/upload` (Data Upload paneel gemigreerd naar admin)
    - [x] Omgevingsvisie SWF succesvol gemigreerd naar lokaal externe-lagen systeem

### Track C — Benchmarking: Kernen naast elkaar ✅
- [x] **C1 — Multi-woonplaats benchmark-tabel**
    - [x] `/api/kompas/{config_id}/benchmark` endpoint toegevoegd, met per-groep en referentie statistieken
    - [x] Frontend: benchmarktabel met kolom per woonplaats + kleur/pijl bij afwijking
    - [x] Acceptatie: TC-02-001 stap 5 → ✅ (was ⚠️)
- [x] **C2 — Gemeentegemiddelde SWF als referentielijn**
    - [x] Contextuitleg en referentiewaarde opgenomen in de benchmark-tabel

### Track D — Gebruikersflow
- [x] **D1 — Dynamische Profielen & Deterministische Scenario's (Showcase IJsselmeerkust)**
    - [x] **D1.1: Database Migratie (`migrations/schema_v14_chat_scenarios.sql`)**: Tabel `chat_scenarios` aanmaken met `rol_code`, `rol_naam`, `beschrijving`, `narrative`, `acties` (JSONB) + Seed-data (beleidsadviseur & wijkcontactfunctionaris).
    - [x] **D1.2: Backend (`routers/chat.py`)**: `ActieKnop` schema uitbreiden met type `SEND_MESSAGE` en `rol_code`.
    - [x] **D1.3: Backend (`routers/chat.py`)**: `get_help_onboarding_response()` async maken + DB-aanroep om actieve profielen dynamisch op te halen.
    - [x] **D1.4: Backend (`routers/chat.py`)**: Deterministische scenario-matching logica implementeren (eerst op `rol_code` uit context, fallback op `trigger_keywords`) vóór LLM-aanroep.
    - [x] **D1.5: Frontend (`static/js/chat.js`)**: Knop-handler uitbreiden voor `SEND_MESSAGE` (stuurt `rol_code` in context en toont `rol_naam` in de UI).
    - [x] **D1.6: Frontend (`static/js/chat.js`)**: Hybride acties (zoals `SELECTEER_GEMEENTE` en `OPEN_KOMPAS`) uit het scenario correct laten uitvoeren door de UI.
    - [x] Acceptatie: TC-06-001 fase 1 → ✅ (was ❓)
- [x] **D2 — Startflow: hint tot eerste selectie**
    - [x] Kaartlading: subtiele hint *"Klik op een buurt of kies een woonplaats om te starten"*
    - [x] Verdwijnt bij eerste selectie (localStorage flag, Sprint 11B patroon)
    - [x] Acceptatie: TC-01-001 stap 1 → ✅ (was ❓)


### Track E — Testcase executie & documentatie
- [ ] **E1 — TC-06-001 volledig doorlopen in browser** (alle 14 stappen)
- [ ] **E2 — TC-01-001, TC-02-001, TC-02-002 statusvelden bijwerken**
- [ ] **E3 — NM-001 actualiseren** (opgeloste gaps ✅, FRLDS-gaps labelen)

### Track F — Gebruikersreview Quickwins
**Aanleiding:** [Gebruikersreview](./docs/7-projectmanagement/testcases/Gebruikersreview.md) — laag hangend fruit direct bruikbaar binnen Sprint 18.
- [x] **F1 — Bug: Zoekfunctie Kompas `undefined` foutmelding**
    - [x] `Array.isArray` guard + `renderSearchResults([])` bij API-fout
    - [ ] Acceptatie: foutmelding nog niet reproduceerbaar in testomgeving — open
- [x] **F2 — Top 3+3 buurten per indicator (grootste afwijkers)**
    - [x] Backend: `GET /api/kompas/indicator/{uuid}/top-buurten?gebied_id=&limit=3`
    - [x] Frontend: sectie in detailpaneel na indicator-selectie met Top 3+ en Top 3-
    - [x] Klik op buurt in lijst → flyToGebied
    - [x] Filtering per gemeente en bugfix voor 'wijk' records
    - [x] Acceptatie: Top 3+3 afwijkers direct zichtbaar en interactief
- [x] **F3 — Visuele weergave/highlight bij klik op Top-buurt**
    - [x] Als men op een buurt klikt in het Kompas Top 3+3 venster, flyToGebied + highlight het gebied visueel
    - [x] Belangrijk: **NIET** als formele selectie toevoegen, want we hebben al een gebiedsselectie actief
    - [x] Acceptatie: Gebruiker kan de uitschieters makkelijk op de kaart vinden door de highlight (Geo Gold dashed line), zonder de huidige selectiestatus kwijt te raken
- [ ] **F4 — Bug: Z-score/Top uitschieters baseert zich op gemeente van aangeklikte buurt, zelfs bij 'Alle gemeenten' filter**
    - [ ] Wanneer 'Alle gemeenten' geselecteerd is als filter, maar je klikt op een specifieke buurt op de kaart, berekent de backend (`get_top_afwijkende_buurten`) de uitschieters momenteel alleen voor de buurten binnen de gemeente van de aangeklikte buurt. 
    - [ ] Gewenst gedrag: de Z-score referentie en top-buurten moeten over de gehele populatie (alle gemeenten) berekend worden als het globale filter op 'Alle gemeenten' staat, ongeacht welke buurt is aangeklikt.
    - [ ] *Voor later, genoteerd als vervolgactie.*

### Track G — Correcties n.a.v. Testbevindingen Sessie 4 (Dag 73)
**Aanleiding:** Handmatige test na merge → twee punten vragen correctie voor volgende sessie.
- [x] **G1 — Eenheden consequent tonen in Kompas venster**
    - [x] Check: waarde `86.00` moet `86.00 %` tonen als eenheid `%` is
    - [x] Controleer `_enrich_tree_with_values` — eenheid zit al in data_map maar wordt niet altijd doorgegeven aan de node
    - [x] Controleer `expandDetails` / `showActionOverlay` — `d.data.eenheid` correct gevuld?
    - [x] Acceptatie: elke indicatorwaarde in het Kompas toont zijn eenheid (%, km, index, etc.)
- [x] **G2 — Z-score uitlegblok verplaatsen: Kompas → Rapport**
    - [x] **Verwijder** het z-score uitlegblok uit het Kompas detailpaneel (`zscore-explanation` div in `index.html` + JS toggle)
    - [x] **Verwijder** z-score tooltip icoontje uit `showActionOverlay` in `kompas.js`
    - [x] **Voeg toe** aan de rapportpagina (`report.js` / rapporttemplate): contextblok boven de z-score tabel
    - [x] Tekst: *"Z-score vergelijkt een indicator met het Friese gemiddelde. 0 = gemiddeld · >+1 = beduidend beter · <-1 = beduidend slechter"*
    - [x] Referentie: Afbeelding 3 (rapportage z-score tabel met WAARDE / JAAR / Z-SCORE / IMPACT kolommen)
    - [x] Acceptatie: Z-score uitleg zichtbaar in rapport ✅ | Niet aanwezig in Kompas ✅
- [x] **G3 — Info hover-over voor Top 3+3 afwijkingsscores**
    - [x] Voeg een info ('i') tooltip toe naast de titel "TOP UITSCHIETERS" in het Kompas detailpaneel.
    - [x] Uitleg toevoegen: Hoe de afwijkingen worden berekend (via de z-score methodiek).
    - [x] Acceptatie: Tooltip zichtbaar bij hoveren over het 'i' icoon.

### Afsluiting & Merge
- [x] Pull Request aanmaken naar `main` met verwijzing naar GitHub Issue
- [x] Squash merge na review
- [x] STATE.md bijwerken: Sprint 18 componenten op 🟢 Actief
- [x] Testcases README bijwerken (statusvelden)

---

## 📌 Sprint 19: Van Data naar Inzicht (Gepland)

**Doel:** D-OmniTwin transformeren van data-exploratie naar inzicht-gedreven besluitvorming — gebruikers actief begeleiden van data naar conclusie en handelingsperspectief.  
**Aanleiding:** [Gebruikersreview juni 2026](./docs/7-projectmanagement/testcases/Gebruikersreview.md) — consistente bevinding over alle 5 gebruikersprofielen.  
**Spec:** [`docs/7-projectmanagement/archief/sprint-19-plan_data-naar-inzicht.md`](./docs/7-projectmanagement/archief/sprint-19-plan_data-naar-inzicht.md)  
**Branch:** `feature/sprint-19-data-naar-inzicht` (aan te maken na Sprint 18)

### Track A — Signalering: Automatische Uitschieters
- [ ] **A1 — Stijgers & Dalers per indicator**
    - [ ] Backend: `GET /api/indicatoren/{uuid}/trends?gemeente_code=&periodes=2`
    - [ ] Frontend: collapsible sectie *"Beweging"* — top 3 stijgers + top 3 dalers
    - [ ] Klik → flyTo buurt op kaart
- [ ] **A2 — Afwijkingssignalering gemeente vs. provincie**
    - [ ] `referentie_type: 'gemeente' | 'provincie'` param op top-buurten endpoint
    - [ ] Frontend: toggle *Referentie: Gemeente | Provincie* op Top 5 sectie

### Track B — Prioritering: Inzicht per Buurt & Thema
- [ ] **B1 — Top 5 risico's per buurt (thema-overstijgend)**
    - [ ] Backend: `GET /api/gebieden/{gebied_id}/prioriteiten`
    - [ ] Frontend: nieuw blok *"⚠️ Aandachtspunten voor [buurt]"* in detailpaneel
    - [ ] Optioneel: ook *"💚 Sterke punten"* (top 3 positief)
- [ ] **B2 — Provinciaal gemiddelde als extra referentielijn**
    - [ ] Backend: provinciaal gemiddelde toevoegen aan Kompas API response
    - [ ] Frontend: extra kolom in benchmarktabel + referentielijn in trendgrafiek

### Track C — Context: Scores in Gewone Taal
- [ ] **C1 — Contextuele score-uitleg per indicator**
    - [ ] Frontend logica: z-score → begrijpelijke label (*Aandacht / Gemiddeld / Goed*)
    - [ ] Zichtbaar per indicatorwaarde in detailpaneel (geen extra backend call)
- [ ] **C2 — Geleide gebruikersroute per doelgroep (rolkeuze)**
    - [ ] Uitbreiding onboarding modal: rolkeuze (Beleidsadviseur / Wijkregisseur / Bestuurder / Verkenner)
    - [ ] Per rol: aanbevolen startpunt getoond
    - [ ] Rol opslaan in localStorage (`omnitwin_rol`)

### Track D — AI-Ondersteuning: Automatische Samenvatting
- [ ] **D1 — AI-samenvatting per buurt (Ollama)**
    - [ ] Backend: `POST /api/gebieden/{gebied_id}/samenvatting` stuurt prompt + data naar lokaal Ollama model
    - [ ] Frontend: nieuw AI-icoon per buurt, toont modal met gegeneerde "Executive Summary"
- [ ] **D2 — Dynamische Gebiedsselectie Assistent**
    - [ ] In plaats van hardcoded scenario's (bijv. "Gemeente Súdwest-Fryslân"), moet de assistent dynamisch een selectielijst/zoekfunctie genereren voor gebiedstypes en gemeenten op basis van de interactie.

### Track E — UI/UX Positionering & Optimalisatie
- [x] **E1 — Verplaatsen actieknoppen voor betere flow**
    - [x] Donker/Licht modus toggle verplaatsen naar rechtsboven, direct rechts naast de 'Beheer' knop.
    - [x] Huidige 'Beheer' knop en 'Verbonden' indicator opschuiven naar links.
- [x] **E2 — Info/Start Paneel Integratie**
    - [x] 'i' knop transformeren naar standaard `.tab-button` en verplaatsen naar absolute top van de navigatiebalk.
    - [x] Oude zwevende overlay `#camera-controls-overlay` vervangen door vast `#panel-info` paneel links.
    - [x] Welkomststappen, Kaartbediening en D-Omni Assistent tips toevoegen aan `#panel-info`.
    - [x] Overbodige CSS en JS opschonen (`setupInfoToggle`).
### Afsluiting & Merge
- [ ] Gebruikersreview opnieuw doorlopen (alle 5 profielen)
- [ ] Pull Request aanmaken naar `main`
- [ ] STATE.md bijwerken: Sprint 19 componenten
- [ ] UX-bevindingen bijwerken na hertest

---

## 📌 Sprint 20: E-mail Alerts & SMTP Flexibiliteit (Gepland)

**Doel:** Het systeem voorzien van betrouwbare e-mail alerts bij kritieke fouten (`ERROR` of `CRITICAL`) via een flexibele SMTP configuratie (ondersteuning voor eigen mailserver, Office365, Gmail, etc).
**Aanleiding:** Issue #10 (voorheen een blocker). Doorgeschoven naar ná Sprint 19.
**Spec:** [`docs/5-secops/logging/plan_email_alerts_smtp.md`](./docs/5-secops/logging/plan_email_alerts_smtp.md)

### Track A — Flexibele SMTP Configuratie & Test-endpoint
- [ ] **A1 — `.env` variabelen toevoegen**
    - [ ] `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `LOG_ALERT_TO`, `LOG_ALERT_ENABLED`
- [ ] **A2 — `log_alert_service.py` bouwen**
    - [ ] Asynchrone mail-verzending
    - [ ] Debouncing logica: max 1 e-mail per categorie per 5 minuten
- [ ] **A3 — Admin Test-functie**
    - [ ] Backend: `POST /api/admin/logs/test-alert`
    - [ ] Frontend: "Test E-mail Instellingen" knop in de Log Config tab.

---

## 📌 Sprint 21: Data Kwaliteit & Betrouwbare Start (Gepland)

**Doel:** Ruis uit de applicatie filteren (lege en dubbele indicatoren) en een toolset bieden voor gebruikersgestuurde deduplicatie.
**Aanleiding:** Ruis vertroebelt het Kompas en AI-antwoorden. Goede data is essentieel voor adoptie.

### Track A — Deduplicatie Assistent (Admin Panel)
- [ ] Backend: Matchmaking algoritme bouwen (Fuzzy + pgvector + Ollama).
- [ ] Backend: Actie "Primaire Indicator Kiezen" (`is_actief = False` voor duplicaten, data re-linken).
- [ ] Frontend: Nieuwe pagina in Beheeromgeving om AI-voorgestelde matches te reviewen.

### Track B — Ruisvrije Frontend & API's
- [ ] Filter-logica inbouwen op `gebied_data` aanwezigheid voor alle relevante endpoints.
- [ ] Verbergen van lege nodes in D3 Sunburst / Kompas.
- [ ] Vector Search & AI uitsluiten van lege indicatoren.

### Track C — Validatie & Opschoning
- [ ] Opschoning "Alcohol" vs "Overmatig drinken" en andere dubbelingen samen met gebruikers.
- [ ] Controle op eenheden (absoluut, %, etc.).

---

## 📌 Sprint 22: Identity & Toegangsbeheer (Fase 2) (Gepland)

**Doel:** Implementatie van volwaardig identiteits- en toegangsbeheer (RBAC) ter vervanging van de statische admin API-keys. Scheiding aanbrengen tussen publieke gebruikers, interne medewerkers (inwoners vs. gemeente) en systeembeheerders.
**Aanleiding:** Architectuurvisie Fase 2 (SSO, OpenID Connect). Noodzaak voor afgeschermde delen van de applicatie.

### Track A — SSO & Keycloak Integratie
- [ ] Implementeren van Keycloak als Identity Provider (IdP).
- [ ] Ondersteuning voor SSO via OpenID Connect (OIDC).
- [ ] Koppelen van Windows Authenticatie (Active Directory / Entra ID) voor naadloze interne login.

### Track B — Role-Based Access Control (RBAC)
- [ ] Authenticatie middleware voor FastAPI uitbreiden naar JWT verificatie via Keycloak.
- [ ] Frontend autorisatie-logica in React Router (`ProtectedRoute` afhankelijk van rol).
- [ ] Rol-definities:
    - **Publiek (Inwoners):** Open dataset, geen login vereist.
    - **Gebruiker (Gemeente):** Ingelogd (via Windows SSO), toegang tot extra datasets of functies.
    - **Beheerder/Admin:** Volledige toegang tot het CMS/Admin Panel en beheerstaken.

---

## ✅ Sprint 17: Configureerbare Logging Infrastructuur (Afgerond 26 mei 2026)

**Doel:** Gedifferentieerde, configureerbare logging op alle facetten van de applicatie — instelbaar per module via de beheeromgeving, persistent in PostgreSQL, zichtbaar via admin panel dashboard, proactief via alerts.
**Spec:** [`docs/5-secops/logging/sprint-17-logging-spec.md`](./docs/5-secops/logging/sprint-17-logging-spec.md)


### 🔧 Voorbereiding (voor eerste codesessie)
- [x] **GitHub Issue #9 aanmaken** op `github.com/TLaan/D-OmniTwin`
    - Titel: `feat: Configureerbare Logging Infrastructuur (Sprint 17)`
    - Labels: `enhancement`, `secops`, `backend`, `admin-panel`, `sprint-17`
    - Link naar `docs/5-secops/logging/sprint-17-logging-spec.md`
    - Sub-tasks als GitHub task list (één per fase 17A/17B/17C)
- [x] **Feature branch aanmaken en pushen:**
    ```bash
    git checkout -b feature/sprint-17-logging
    git push -u origin feature/sprint-17-logging
    ```
- [x] **Worktree aanmaken** (demo-omgeving op `main` intact houden):
    ```bash
    git worktree add ../D-OmniTwin-DEMO main
    ```
- [x] **AVG/GDPR afstemmen** met opdrachtgever over IP-adres opslag (zie spec)
- [x] **SMTP-server** bepalen voor e-mail alerts (Sprint 17C)

### Sprint 17A — Fundament & Server/API Logs
- [x] **Database schema** `migrations/schema_v13_logging.sql` aanmaken:
    - [x] Tabel `app_logs` (id, timestamp, level, category, message, user_id, session_id, ip_address, endpoint, response_time_ms, extra JSONB)
    - [x] Tabel `log_config` (category, level, enabled, updated_at, updated_by)
    - [x] Standaard INSERT voor alle 9 categorieën
    - [x] Indexen op timestamp, level, category, user_id
- [x] **`services/logging_service.py`** aanmaken:
    - [x] `AsyncLogQueue` — in-memory queue met background worker
    - [x] `AppLogger` — wrapper met methoden per categorie (`.info()`, `.warning()`, `.error()`, `.debug()`)
    - [x] Config cache: actieve `log_config` uit DB, elke 60s ververst
    - [x] Fallback: als queue vol → synchroon naar logbestand schrijven
    - [x] Rotating file handler: `logs/server.log` (10MB max, 5 backups)
- [x] **`main.py`** aanpassen:
    - [x] Python `logging` module configureren bovenaan (vóór router imports)
    - [x] `LOG_LEVEL` uit `.env` lezen
    - [x] `RequestLoggingMiddleware` toevoegen (category=API: method, path, status_code, response_time_ms, user/IP)
    - [x] `startup_event`: `print()` → `AppLogger.server()`
- [x] **`run_dev.py`** aanpassen: `log_level` dynamisch vanuit `LOG_LEVEL` env variabele
- [x] **`services/gebiedsmonitor_service.py`**: `print("DEBUG: ...")` → `AppLogger.debug(category="KAART")`
- [x] **`services/llm_service.py`**: `print(LLM REQUEST/RESPONSE)` → `AppLogger.debug(category="LLM_CHAT")`
- [x] **`services/color_scale_service.py`**: `print(f"ERROR: {e}")` → `AppLogger.error(category="KAART")`
- [x] **`routers/dashboard.py`**: `print(f"Error: {e}")` → `AppLogger.error(category="API")`
- [x] **`.env.example`**: `LOG_LEVEL` activeren (was dode variabele), `logs/` toevoegen aan `.gitignore`
- [x] **Verificatie 17A:**
    - [x] Server start → `app_logs` bevat SERVER/startup entries
    - [x] HTTP request → `app_logs` bevat API entry met response_time_ms
    - [x] `LOG_LEVEL=DEBUG` → debug logs in DB én in `logs/server.log`
    - [x] `logs/server.log` bestaat en groeit mee

### Sprint 17B — Module Logs & Admin UI Log Viewer
- [x] **Module instrumentatie:**
    - [x] `routers/kompas.py` — KOMPAS events bij hierarchie/gebied opvraging
    - [x] `routers/gebiedsmonitor.py` — KAART events met gebiedstype, gemeente_code, indicator_uuid
    - [x] `routers/report.py` — RAPPORT events: type, format, duur, succes/fout
    - [x] `routers/auth.py` — AUTH events: login succes/fout, sessie-aanmaak, token gebruik
    - [x] `routers/admin.py` — ADMIN events bij elke configuratiewijziging
    - [x] `routers/chat.py` — upgrade bestaande `logger.*` → `AppLogger(category="LLM_CHAT")`
    - [x] `routers/bag3d.py` — upgrade bestaande `logger.*` → `AppLogger(category="KAART")`
- [x] **`routers/log_viewer.py`** aanmaken:
    - [x] `GET /api/admin/logs` — gefilterd + gepagineerd
    - [x] `GET /api/admin/logs/stats` — statistieken voor dashboard
    - [x] `GET /api/admin/log-config` — configuratie ophalen
    - [x] `PUT /api/admin/log-config/{category}` — configuratie bijwerken
- [x] **Admin Panel React — nieuwe pagina `/admin/logs`:**
    - [x] Statistieken balk (totaal logs vandaag, error rate, actieve gebruikers)
    - [x] Filteropties: periode, categorie (multi-select), niveau, gebruiker, zoekterm
    - [x] Detailtabel: timestamp | niveau | categorie | gebruiker | endpoint | bericht | expandable detail
    - [x] Log configuratie sectie: per categorie toggle (aan/uit) + niveau dropdown
- [x] **Monitor-rol** toevoegen aan auth systeem (read-only log viewer)
- [x] **Verificatie 17B:**
    - [x] Kompas opvragen → KOMPAS entry in `app_logs`
    - [x] Mislukt inloggen → AUTH WARNING in `app_logs`
    - [x] Admin panel log viewer toont entries met correcte filters
    - [x] Configuratiewijziging actief binnen 60 seconden

### Sprint 17C — Statistieken Dashboard & Alerts
- [x] **Admin panel "Gebruik & Gezondheid" tabblad:**
    - [x] Kompas: meest geraadpleegde hiërarchieën en buurten
    - [x] Kaart: populairste gemeente-filters en indicatoren
    - [x] API: hits per endpoint, response times (gemiddeld/p95)
    - [x] Auth: actieve sessies, mislukte inlogpogingen (trendlijn)
    - [x] Errors: fout per categorie over tijd (lijndiagram)
- [x] **Admin panel badge:** `GET /api/admin/logs/unread-errors` → rode badge in navigatie
- [x] **E-mail alerts** bij ERROR/CRITICAL:
    - [x] `LOG_ALERT_EMAIL` in `.env` configureren
    - [x] Debounce: max 1 e-mail per 5 minuten per categorie
    - [x] E-mail template: categorie, bericht, endpoint, gebruiker, timestamp
- [x] **Automatische retentie cleanup** (APScheduler in `main.py`):
    - [x] DELETE DEBUG logs ouder dan 7 dagen
    - [x] DELETE INFO logs ouder dan 30 dagen
    - [x] BEWAAR WARNING/ERROR/CRITICAL permanent
- [x] **Verificatie 17C:**
    - [x] ERROR loggen → admin badge toont +1
    - [x] ERROR loggen → e-mail ontvangen binnen 5 min
    - [x] Cleanup job verwijdert DEBUG logs correct

---


## ✅ Sprint 16: Kaart Viewport Gedrag — Vrije-Zone Centreren (Afgerond)

**Doel:** Bij het klikken op een buurt de kaart centreren in het **grootste vrije, onbedekte kaartgebied** — niet in het midden van het volledige scherm.  
**Aanleiding:** Het Kompas-venster, het linkerpaneel en de chat-zijbalk kunnen de geselecteerde buurt visueel bedekken. Het huidige `flyToGebied()` houdt hier geen rekening mee.  
**Prioriteit:** 🟡 MEDIUM  
**Effort:** ~3–5 uur

### Context & Gewenst Gedrag

Na het klikken op een buurt moet de kaart zo schuiven dat de buurt zichtbaar valt in het **vrije deel van het scherm** (de zone die niet bedekt is door UI-elementen). Als het Kompas-venster rechts staat, centreer dan links; als het links staat, centreer dan rechts.

### UI Dimensies (vastgesteld uit code)

| Element | Positie | Breedte | Zichtbaar wanneer |
|---|---|---|---|
| Tab bar | `left: 0` | `70px` (`--tab-bar-width`) | Altijd |
| Linker panel (Kaart Configuratie) | `left: 70px` | `360px` (`--panel-width`) | Als geopend (`panel-container.open`) |
| Kompas venster (`#kompas-window`) | `position: fixed`, draggable | `650px` (resizable) | Als zichtbaar (`display != none`) |
| Chat panel (`#chat-panel`) | `right: 0` | `380px` | Als `.open` class aanwezig |

### Technische Aanpak: `getFreezone()`

Introduceer een helperfunctie die de **vrije rechthoek** van de kaart berekent — het gedeelte van het scherm dat niet bedekt is door enig UI-panel.
*(Noot: De implementatie hiervan is inmiddels afgerond via de `getFreezone()` functie in `app.js`)*.

Gebruik de viewport-offset om de camera te verplaatsen naar het centroid van de buurt, maar **gepositioneerd in de vrije zone** (zoals uitgerekend door `getFreezone()`).
*(Noot: Ook dit is reeds succesvol verwerkt in de codebase).*

### `fitBounds()` guard (ontkoppelen van re-renders)

Huidige bug: `fitBounds()` wordt bij **elke** `displayOnMap()` aangeroepen, ook bij selectie-re-renders.

```javascript
// In displayOnMap(), vervang:
if (geojson.features.length > 0) { fitBounds(geojson); }

// Door:
if (geojson.features.length > 0 && !state.initialDataLoaded) {
    fitBounds(geojson);
    state.initialDataLoaded = true;  // Alleen bij eerste lading
}
// Reset state.initialDataLoaded = false bij loadKaartData() (nieuwe datasetselectie)
```

### Implementatie Checklist

- [x] `getFreezone()` functie implementeren in `app.js`
- [x] `flyToGebied()` aanpassen: longitude-offset op basis van vrije-zone centrum
- [x] `fitBounds()` ontkoppelen van `displayOnMap()` re-renders via `state.initialDataLoaded` flag
- [x] Reset `state.initialDataLoaded` bij nieuwe dataset-load in `loadKaartData()`
- [x] Handmatig testen: Kompas links, Kompas rechts, Chat open, alle panels open tegelijk

### Bekende Edge Case (acceptabel)

> **Kompas gecentreerd + D-Omni Assistent open:** Als het Kompas-venster in het midden van het scherm staat én de Chat-zijbalk (380px) open is, kan de geselecteerde buurt achter de Chat vallen. Workaround: Kompas naar links verschuiven en opnieuw klikken. Mogelijke toekomstige verbetering: Chat-paneel meenemen in de Kompas-segment berekening.

---


## ✅ Sessie 2026-04-22: Schema Sync & Onboarding Setup (Dag 59)

**Doel:** Zorgen dat een fresh install exact dezelfde database en werking oplevert als de huidige development database (Golden Source) zonder HTTP 500 crashes in de UI.

- [x] **Data-Integriteit Hersteld:** Alias-mismatches in `indicatoren_seed.json` gecorrigeerd en seed-logica aangepast.
- [x] **Setup Wizard:** Interactief script `init_data/scripts/setup_env.py` gemaakt om veilige `.env` keys te genereren zonder copy-paste werk.
- [x] **Documentatie Opschoning:** `GETTING_STARTED.md` up-to-date (geen legacy buurten-extractor meer, fallback voor `pgvector` compilation toegevoegd).
- [x] **Schema Sync:** 13 ontbrekende kolommen in `indicatoren`, 4 in `color_schemas` en volledige `visualisatie_profielen` tabel toegevoegd aan `schema_latest.sql`. Ontbrekende views toegevoegd.
- [x] **Seed Data Aangevuld:** 33 `visualisatie_profielen` en 9 `color_schemas` direct in de seed/schema geïntegreerd om runtime error te voorkomen.
- [x] **Live DB Geüpdatet:** Data ook direct in de lokale testomgeving geïnjecteerd (na het oplossen van wat blokkerende idle-in-transaction locks).
- [x] **Commit `a8166c4`** gepusht naar `main`.

---

## ✅ Sessie 2026-04-20: Indicatoren Consolidatie & Init Data Completering (Dag 58)

**Doel:** Database-indicatoren saneren, seed synchroniseren met ETL-bronnen, initiatie-workflow volledig afsluiten.

- [x] **Inventarisatie:** Alle 275 DB-indicatoren gecategoriseerd (Kompas × data matrix)
- [x] **29 wees-records verwijderd** — geen Kompas-koppeling én geen data
- [x] **6 naam-duplicaten gemerged** — ETL-namen → Kompas-equivalenten (53.000+ datapunten behouden)
  - `Afstand tot huisarts` → `Huisarts` | `Roker` → `Roken` | `Eenzaam` → `Eenzaamheid`
  - `Overmatig alcoholgebruik` → `Overmatig drinken` | `Gemiddelde Woonoppervlakte` → lowercase
  - `Percentage Woonfunctie (BAG)` → lowercase variant
- [x] **5 legacy-records opgeruimd** — BAG-percentages (Winkel/Kantoor/Industrie/Overig) + CBS Onbekend
- [x] **7 indicatoren aan Kompas gekoppeld** — Obesitas, BAG-bouwjaar, woonfunctie, inkomen, energielabel
- [x] **`indicatoren_seed.json` vernieuwd** — 61 → 235 indicatoren, volledig formaat (code, eenheid, score_type, heeft_data)
- [x] **`seed_fryslan.py` bijgewerkt** — gebruikt seed-velden direct, fallback `IND_`-prefix
- [x] **`download_indicatoren_fryslan.py` gesynchroniseerd** — 14 indicator-namen gecorrigeerd
- [x] **Documentatie bijgewerkt** — GETTING_STARTED.md + init_data/README.md (61→235, thematabel uitgebreid)
- [x] **Commit `1dbd700`** gepusht naar `main` — 5 bestanden, 2450 toevoegingen
- [x] **Sessie-samenvatting** opgeslagen in archief (dag 58)
- [x] **STATE.md bijgewerkt**

⏳ **Nog te doen (op jouw laptop):** `python init_data/scripts/download_indicatoren_fryslan.py`

---

## ✅ Sessie 2026-04-13: Initiatie Dataset & Getting Started (Dag 58)

**Doel:** Verlagen van de drempel voor nieuwe gebruikers — starter dataset + volledige documentatie.

- [x] **Analyse:** Gaps geïdentificeerd (data/ volledig gitignored, schema's niet in git)
- [x] **`init_data/` mapstructuur** aangemaakt en uitgesloten van gitignore-restrictie (`!init_data/`)
- [x] **`init_data/schema/schema_latest.sql`** — schema snapshot nu in git
- [x] **`init_data/kompas/kompas_hierarchie.csv`** — 224 rijen opgeschoonde Kompas structuur
- [x] **`init_data/indicatoren/indicatoren_seed.json`** — 61 actuele indicatoren met metadata
- [x] **`init_data/fryslan/buurten_fryslan.geojson`** — 942 CBS buurten 2024 (alle 18 Friese gemeenten, WGS84, 17MB)
- [x] **`init_data/scripts/extract_buurten_fryslan.py`** — extractor vanuit lokale CBS_BUURTEN2024.gpkg
- [x] **`init_data/scripts/download_indicatoren_fryslan.py`** — CBS OData downloader
- [x] **`init_data/scripts/seed_fryslan.py`** — 4-stappen database importer (buurten/indicatoren/kompas/waarden)
- [x] **`init_data/scripts/init_database.sh`** — master init script (alles in 1 commando)
- [x] **`GETTING_STARTED.md`** — volledige stap-voor-stap installatiegids (nieuw in root)
- [x] **`README.md`** — Quick Start sectie herzien en vereenvoudigd
- [x] **`docs/STATE.md`** bijgewerkt (Dag 58, Roadmap, Actieve Componenten)
- [x] **Git commit `547cbf8`** gepusht naar `main` (16 bestanden, 3892 regels)


---


## ⏳ Sprint 11: Chat Afronding & Visuele Overhaul (Verkenning) (Gepland)

**Doel:** De D-Omni Assistent functionaliteit afronden als volwaardige stuurbare 'muis' en 'zoek' functie. Daarnaast het uitwerken en verkennen van een complexe visuele overhaul.
**Geschatte duur:** N.t.b.
**Details:** Kaders/gedachtes worden uitgewerkt in nieuwe documenten.

### Track A: Chat Functionaliteit Afronden
- [ ] Optimalisatie van de intent-herkenning en actie-dispatching
- [ ] Verfijnen van de 'muis'-operaties vanuit chat
- [x] Gemeentelijst uitbreiden: Groningen en Drenthe toevoegen aan de LLM meta-context in `LLMService`. (Voltooid 25-03-2026)
- [x] **HELP_ONBOARDING Intent implementeren** *(Voltooid 09-04-2026)*
    - [x] **Backend (`routers/chat.py`):** Keyword-match vóór LLM-aanroep — detecteer zinnen als "wat kan jij", "hoe gebruik ik", "help", "mogelijkheden". Geen Ollama-call nodig: retourneert een vaste JSON-response met `intent: HELP_ONBOARDING`.
    - [x] **Vaste response definiëren** met 4 actie-knoppen: `🗺️ Kaart verkennen`, `🧭 Kompas begrijpen`, `📄 Rapport genereren`, `📖 Handleiding openen`.
    - [x] **Frontend (`chat.js`):** Afhandeling van `HELP_ONBOARDING` en de nieuwe actietypes `INFO_KAART`, `INFO_KOMPAS`, `INFO_RAPPORT`, `OPEN_WIKI` — inline rich-text info-cards met fade-slide animatie.
    - [x] **Wiki/Help pagina** aangemaakt (`/static/help.html`) met Lucide SVG-iconen, gebruikersgericht, geen technisch jargon.
    - [x] **ⓘ-knop koppelen:** Blauwe ⓘ-knop uitgebreid met `book-open-text.svg` link naar help-pagina (tweede toegangspunt).
- [ ] (Aanvullen obv nieuw document)

### Track B: Visuele Overhaul Verkenning
- [x] Verkennen randvoorwaarden en impact van voorgestelde visuele aanpassingen *(Voltooid 2026-05-14 — zie PLAN_UX_OVERHAUL_SPRINT11B.md)*

### Track C: Indicator Type & Kwaliteit
- [ ] Database schema uitbreiden: kolom `indicatortype` (Objectief/Subjectief) toevoegen aan `indicatoren`.
- [ ] Vergelijken huidige database indicatoren met `data/gebiedsmonitor/indicator.xlsx`.
- [ ] Koppelen van veld 'Type' aan database records.
- [ ] Keuze maken tussen objectief/subjectief voor records met 'objectief/subjectief' (geen dubbele types).

### Track D: Security & Infrastructure
- [ ] API-documentatie (`/docs`) beveiligen: enkel toegankelijk na login (overeenkomstig met beheeromgeving).

### Documentatie & Afsluiting
- [x] Nieuwe documenten analyseren en plannen concretiseren *(Voltooid — zie `docs/4-ux-design/visual/`)*
- [ ] `ROADMAP.md` en `TODO.md` updaten na verkenning

---

## 🚧 Sprint 11B: UX-Overhaul — Learnability, Feedback & Cognitive Load (Gepland)

**Doel:** Transitie van data-interface naar cognitief begeleid besluitvormingsplatform.  
**Basis:** [`docs/4-ux-design/visual/PLAN_UX_OVERHAUL_SPRINT11B.md`](./docs/4-ux-design/visual/PLAN_UX_OVERHAUL_SPRINT11B.md)  
**Branch:** `feat/ux-overhaul-sprint11b` (aan te maken)  
**Geschatte effort:** ~13 uur (2–3 sessies)

### 🔧 Voorbereiding (voor eerste codesessie)
- [x] **GitHub Issue aanmaken** op `github.com/TLaan/D-OmniTwin` *(Voltooid 2026-05-14 — Issue #7)*
    - Titel: `feat: UX-overhaul — Learnability, Feedback & Cognitive Load (Sprint 11B)`
    - Labels: `enhancement`, `ux`, `frontend`, `sprint-11`
    - Koppeling naar `PLAN_UX_OVERHAUL_SPRINT11B.md`
    - Sub-tasks als GitHub task list (één per track)
- [x] **Feature branch aanmaken en pushen** *(Voltooid 2026-05-14)*
    ```bash
    git checkout -b feat/ux-overhaul-sprint11b
    git push -u origin feat/ux-overhaul-sprint11b
    ```
- [x] **Demo-omgeving opzetten** (git worktree op `main`) *(Voltooid 2026-05-14)*
    ```bash
    git worktree add ../D-OmniTwin-DEMO main
    ```

### Track A — Onboarding & Eerste Instap ✅ Voltooid (2026-05-14)
- [x] **A1 — Initiële onboarding** (`templates/index.html`, `app.js`, `styles.css`)
    - [x] Welkomstmodal HTML-structuur toevoegen aan `index.html`
    - [x] `initOnboarding()` functie: localStorage check `omnitwin_welcomed`, toggle modal
    - [x] CTA-knoppen koppelen aan EventBus-acties (`startOnboarding(action)`)
    - [x] Glassmorphism overlay stijl + fade-in/scale animatie in `styles.css`
- [x] **A2 — Contextuele onboarding** (`app.js` — `initContextualTooltips()`)
    - [x] Tooltip bij eerste indicator-selectie (flag: `omnitwin_tt_indicator`)
    - [x] Tooltip bij eerste buurtselectie (flag: `omnitwin_tt_buurt`)
    - [x] Tooltip bij eerste Kompas-open (flag: `omnitwin_tt_kompas`)
    - [x] Tooltip bij eerste AI-response (flag: `omnitwin_tt_ai`)
- [x] **Bonus:** `showError()` geüpgraded van blokkerend `alert()` → glassmorphism toast
- [x] **Bugfix:** `window.EventBus` referentie gecorrigeerd + guard toegevoegd
- [x] **Commit:** `feat(ux): Track A — welkomstmodal + contextuele onboarding layer`

### Track B — Directe Feedback & Micro-interacties ✅ Voltooid (2026-05-15)
- [x] Hover-state cursor feedback op klikbare kaart-elementen (`getCursor` in deck.gl)
- [x] Inline spinner CSS voor gebieddetails-loading — los van fullscreen overlay (`styles.css`)
- [x] Empty state styling info-paneel: *"Klik op een buurt om details te bekijken"* (`index.html`)
- [x] Actieve indicator badge met pulserende dot (`index.html`, `app.js`)
- [x] Inline spinner activeren vóór gebieddetails API-call (`app.js`)
- [x] Empty state herstellen bij `clearGebiedSelection()` (`app.js`)
- [x] **Commit:** `feat(ux): Track B — directe feedback & micro-interacties`

### Track C — Indicatornavigatie & Taxonomie-basis ✅ Voltooid (2026-05-15)
- [x] Accordion HTML-structuur met Kompas thema-groepen (`templates/index.html`)
- [x] Zoekbalk toevoegen boven accordion met debounce 150ms (`templates/index.html`)
- [x] `buildIndicatorAccordion()`: groeperen op thema via Kompas-hiërarchie API (`app.js`)
- [x] Zoekfilter `filterAccordion()` met highlight en auto-open groepen (`app.js`)
- [x] `selectAccordionIndicator()`: klik → kaart laden + legenda + badge (`app.js`)
- [x] Accordion + zoekbalk stijl glassmorphism consistent (`styles.css`)
- [x] Hidden select fallback behouden voor state management (`index.html`)
- [x] **Commit:** `feat(ux): Track C — indicator accordion, zoekfunctie & taxonomie-basis`

### Track D — Visualisatie-consistentie & WCAG ✅ Voltooid (2026-05-15)
- [x] Goud outline via `getLineColor` + `getLineWidth` (deck.gl) bij selectie (`app.js`)
- [x] Fill-kleur behouden bij selectie — gold fill-override verwijderd (`app.js`)
- [x] `updateTriggers` voor `getLineColor`/`getLineWidth` met `selectedGebiedIds` (`app.js`)
- [x] `lineWidthMinPixels: 1` + smooth transitions voor lijn-animatie (`app.js`)
- [x] Legenda hints: "Geselecteerd gebied" (gouden rand) + "Geen data" (grijs) (`app.js`)
- [x] WCAG AA contrast: legenda-labels `font-weight: 600` + `--text-primary` (`styles.css`)
- [x] Dark mode consistentie: coverage bar + help-text kleuren gecorrigeerd (`styles.css`)
- [x] **Commit:** `feat(ux): Track D — outline-selectie, legenda sync & WCAG check`

### Track E — LLM Trust Laag & AI-Governance ✅ Voltooid (2026-05-15)
- [x] Badge/label onderscheid AI-gegenereerd vs. rule-based (`chat.js`)
- [x] Disclaimer bij LLM-response (`chat.js`)
- [x] Bronlabel styling: groen (rule-based) vs. goud (AI) (`styles.css`)
- [x] Disclaimer styling met gele left-border (`styles.css`)
- [x] **Commit:** `feat(ux): Track E — LLM trust laag, governance-notitie & rule-based interpretatie`

### Afsluiting & Merge
- [ ] Performance check alle tracks (zie budget in plan)
- [ ] Handmatige walk-through customer journey (niet-data-vaardig perspectief)
- [ ] Controleren: Kompas, Chat, Rapport, Multi-Gebiedsdossier intact
- [ ] Pull Request aanmaken naar `main` met verwijzing naar GitHub issue
- [ ] Squash merge na review
- [ ] STATE.md bijwerken: Sprint 11B componenten op 🟢 Actief
- [ ] Post-sprint gebruikersvalidatie plannen (3 × 30 min, pilotgemeenten)

---

## ✅ Sessie 2026-04-10: Multi-Gebiedsdossier (Dag 55)

**Doel:** Backend en frontend implementatie van het Multi-Gebiedsdossier, plus bugfixes.

- [x] **ETL:** `ETL/import_omgevingsvisie.py` \u2014 GeoPackage (EPSG:28992) → PostGIS `omgevingsvisie_deelgebieden` (6 polygonen)
- [x] **Database:** Dubbele CRS-opslag (28992 ruimtelijke operaties, 4326 voor GeoJSON)
- [x] **API:** `routers/omgevingsvisie.py` geregistreerd in `main.py`
    - [x] `GET /api/omgevingsvisie/deelgebieden` → 6 features GeoJSON ✅
    - [x] `GET /api/omgevingsvisie/deelgebieden/{id}/buurten` → CBS-buurten via -10m inward buffer ✅
- [x] **Frontend** (`app.js`): `loadOmgevingsvisieLayer()`, `selectBuurtenFromDeelgebied()`, GeoJsonLayer (paars), tooltip, toggle-event
- [x] **UI** (`templates/index.html`): Toggle-checkbox in Kaartlagen-paneel
- [x] **Testcase TC-01-003** bijgewerkt (omgevingsvisie sectie ✅ afgevinkt)
- [x] **Implementatieplan** `PLAN_multi-gebiedsdossier.md` + **Testcase TC-06-002** aangemaakt
- [x] **STATE.md**, **README.md**, **TODO.md**, **ROADMAP.md** bijgewerkt

---

## ✅ Sessie 2026-04-10: Multi-Gebiedsdossier (Dag 55)

**Doel:** Backend en frontend implementatie van het Multi-Gebiedsdossier, plus bugfixes.

- [x] **Stap 1** Backend `report_service.py`: `generate_multi_gebied_payload()` + GeoJSON (z-score, thema's, referentie, water-filter)
- [x] **Stap 2** Backend `routers/report.py`: 2 nieuwe POST-endpoints (`/multi-gebied` + `/geojson`)
- [x] **Stap 3** React `MultiGebiedPage.tsx`: D3-stijl choropleth kaart, ranked uitschietertabel, thema-aggregaat bars.
- [x] **Stap 4** Frontend Integratie: Route `/rapport/multi-gebied`, 3e modal knop in kaart.
- [x] **Bugfixes:** 
    - Flicker-bug in hoverpaneel opgelost met vaste minimumhoogte.
    - Water-buurten gefilterd (`metadata->>'water' != 'JA'`).
    - Colorblind-safe palet geïntegreerd in kaart en tabel.
    - Databereik (min-max), referentiegemiddelde en eenheid gepresenteerd.

---

## ✅ Sessie 2026-04-12: Multi-Gebiedsdossier Uitbreiding (Dag 57)

**Doel:** Verrijking van de analysefunctionaliteit van het Multi-Gebiedsdossier met themafilter, top-3 uitschieters en visuele verbeteringen.

- [x] **Backend `routers/report.py`:** `thema: Optional[str]` toegevoegd aan `MultiGebiedRequest`, doorgestuurd naar beide service-calls.
- [x] **Backend `report_service.py`:** SQL-query omgebouwd van `DISTINCT ON` naar `ROW_NUMBER() OVER (PARTITION BY gebied_id ORDER BY ABS(z_score) DESC) <= 3` voor top-3 uitschieters per buurt.
- [x] **Backend `report_service.py`:** Thema-filter `WHERE thema = :thema_filter` toegevoegd als optionele CTE-laag (`gefilterde_zscores`).
- [x] **Backend `report_service.py`:** Geneste `top_3: []` datastructuur per buurt — hoofdrij bepaalt kleur (rang=1), subitems voor ranks 2 en 3 worden meegestuurd.
- [x] **Backend `report_service.py`:** `generate_multi_gebied_geojson()` uitgebreid met `thema`-param + `top_3` in GeoJSON `properties`.
- [x] **Frontend `api.ts`:** `thema?: string` toegevoegd aan payload-types van beide `reportAPI`-methodes.
- [x] **Frontend `MultiGebiedPage.tsx`:** Thema-dropdown (5 opties), `useState` + herlaad-trigger bij selectieverandering.
- [x] **Frontend `MultiGebiedPage.tsx`:** D3 `geoMercator().fitSize()` vervangt de platte lineaire XY-schaling.
- [x] **Frontend `MultiGebiedPage.tsx`:** Polygonen gesorteerd op `d3.geoArea` (grootste eerst) voor correcte donut-rendering.
- [x] **Frontend `MultiGebiedPage.tsx`:** Hover-paneel toont top-3 afwijkingen per buurt.
- [x] **Frontend `MultiGebiedPage.tsx`:** Nested tabel met uitklapknop `▶` per buurt (subrijen voor rang 2 en 3).
- [x] **Frontend `MultiGebiedPage.tsx`:** Lucide iconen (`Map`, `BarChart2`, `List`, `ChevronRight`, `ChevronDown`).
- [x] **Bugfix:** Hover-paneel flicker loop opgelost met vaste `height: 140px` i.p.v. dynamische `minHeight`.
- [x] **Bugfix #44:** Thema-filter case-mismatch gecorrigeerd — dropdown-waarden matchen nu exact de `titel_naam` in de DB.
- [x] **UI:** `🗺️` emoji in Kaartlagen-paneel vervangen door `map-pinned.svg` icoon.
- [x] **Coverage bugfix (Dag 56/57):** `gebiedsmonitor_service.py` gebruikt nu een onafhankelijke `COUNT(*)` query voor het werkelijke totaal (niet `len(features)`).
- [x] **Semantische fix (Dag 56/57):** "Data Coverage" → "Gebiedsdekking" (legenda), "Coverage" → "Indicatordekking" (Kompas).

---

## 🚧 Sprint 12: 3D BAG Integratie — Realistische Pandmodellen (28-03-2026, Dag 46)

**Doel:** Realistische 3D gebouwmodellen laden via de open [3DBAG](https://3dbag.nl) dataset van TU Delft, als extra kaartlaag.  
**Versie:** 2.3.0 (WIP)

- [x] **Fase 0: API Verkenning & WFS**
    - [x] Ophalen BBOX data via WFS (Zero conversie GeoJSON) in plaats van REST.
- [x] **Fase 1: Backend Router (`routers/bag3d.py`)**
    - [x] `POST /api/3dbag/panden` voor BBOX conversie en HTTP Proxy.
    - [x] Auto-mapping kleuren (Energielabel, Bouwjaar, Buurtgradiënt).
- [x] **Fase 2: Frontend Integratie (`app.js`, `styles.css`)**
    - [x] GeoJsonLayer deck.gl implementatie.
    - [x] Camera fly-to afhandeling (auto-zoom).
    - [x] "🏗️ 3D Panden" toggle knop op de selectie-badge die single en multi-mode aankan.
    - [x] WFS optimalisatie (specifieke property request) en maxZoom > 15 fix voor straatniveau.
    - [x] UI/UX: Semi-transparante loading overlay.
- [ ] **Fase 3: Afronding (Volgende sessie)**
    - [ ] Bug #42: Single-buurt pand-kleur mapping fixen.
    - [ ] Hover tooltips finetunen.

---

---

## 🛡️ Sprint 13: Architectuur Gaps & Security Hardening (Gepland)

**Doel:** Het gericht aanpakken en oplossen van de bekende gaps en risico's die naar voren zijn gekomen uit de recente systeemarchitectuur audit.  
**Basis:** `docs/8-communicatie/D-OmniTwin Systemarchitectuur.html`

### Track A: Security & Infrastructure (High Priority)
- [ ] **G1 - Database SSL/TLS (🔴 High):** Configureren en afdwingen van SSL/TLS encryptie voor alle verbindingen naar de PostgreSQL database.
- [ ] **G2 - HTTPS/TLS Reverse Proxy (🔴 High):** Ontwerp en opzet van een veilige reverse proxy (bijv. Nginx of Caddy) inclusief SSL certificaten (Let's Encrypt) voor veilige verbindingen in productie.

### Track B: Authenticatie & Reliability (Medium Priority)
- [ ] **G3 - JWT Admin Authenticatie (🟡 Medium):** De huidige enkelvoudige, statische API-key auth uitfaseren ten gunste van een robuustere JWT (JSON Web Token) implementatie voor het React Admin Panel.
- [ ] **G4 - AI Fallback Mechanisme (🟡 Medium):** Implementeren van een fallback of redundantie-oplossing voor de lokale Ollama service (bijv. cloud API fallback) om het *Single Point of Failure* risico voor de chat/narrator te mitigeren.

### Track C: Frontend Functionaliteit (Low Priority)
- [ ] **G6 - Executive Summary Frontend (🟢 Low):** Ontwikkelen van de ontbrekende React pagina voor de Executive Summary rapportage, passend bij het reeds gebouwde en actieve backend endpoint.

---

## 🔓 Sprint 14: Open Source Release & EUPL Decoupling (Gepland Q2 2026)

**Doel:** De applicatie en methodiek gereedmaken voor publieke publicatie onder een Dual Licensing model (EUPL 1.2 voor code, CC BY 4.0 voor methodiek).
**Status:** In voorbereiding (Fase 0 voltooid op 29-03-2026).
**Basis:** `docs/1-visie-concept/juridisch/samenvatting_open_source_model_verdienstrategie_overheid.md` en EUPL Audit (29-03-2026).

### Fase 0: Juridisch Fundament (✅ Voltooid)
- [x] Gesprek met werkgever over eigenaarschap en publicatie-intentie.
- [x] Licentie-keuze vastleggen: Dual License (EUPL + CC BY 4.0).
- [x] `LICENSE` en `LICENSE-DOCS` bestanden aanmaken in root.
- [x] `NOTICE.md` aanmaken voor third-party dependencies.
- [x] `README.md` voorzien van formele licentie-sectie.

### Fase 1: Security & Secrets Audit (🔴 BLOCKER voor git publicatie)
- [ ] Volledige git history audit uitvoeren op weggelakte MAPBOX_TOKEN, ADMIN_API_KEY en DB credentials.
- [ ] Bestaande of legacy `config.ini` uit git history halen (indien aanwezig).
- [ ] Een veilige `.env.example` en `config.ini.example` file aanmaken.
- [ ] Codebase scannen (inclusief React build map `admin-panel`) op hardcoded keys.

### Fase 2: Technische Decoupling
- [ ] Beschrijf/verplaats scripts (ETL) weg van Friese codes en maak deze configureerbaar.
- [ ] Lokale LLM (Ollama) optioneel maken in core (feature flag / fallback).
- [ ] `docker-compose.yml` toevoegen ter verduidelijking low-threshold deploy.
- [ ] SPDX headers (`SPDX-License-Identifier: EUPL-1.2`) toevoegen aan core componenten (`main.py`, backend services en main JS).
- [ ] Ensure `exports/` zit expliciet verankerd in `.gitignore`.

### Fase 3: Documentatie Overhaul
- [ ] Opschonen huidige interne `README.md` naar een externe GitHub/GitLab gerichte readme.
- [ ] `METHODOLOGY.md` aanmaken (CC BY 4.0) om methodiek van de backend code te splitsen.
- [ ] `CONTRIBUTING.md` en `CODE_OF_CONDUCT.md` aanmaken.
- [ ] `CHANGELOG.md` aanmaken en logboek historie overzetten.

### Fase 4: Repositories & Launch
- [ ] GitLab public/GitHub repo configureren.
- [ ] `publiccode.yml` aanmaken t.b.v. code.overheid.nl.
- [ ] Setup initial release `v1.0.0-beta` maken/taggen.

---

## 📅 Sprint 15: Kompas UI Uitbreiding - Ontologie & Data Tabs (Nieuw)

**Doel:** Het detailpaneel van het Kompas uitbreiden met tabbladen, zodat naast de standaard trend/data-definitie ook de AI-gevalideerde ontologische beschrijving inzichtelijk is voor de gebruiker.
**Status:** Gepland (Naar aanleiding van feedback).

### Backend (API)
- [ ] Pydantic schema `KompasNode` in `schemas/kompas.py` uitbreiden met `ontologische_beschrijving`.
- [ ] `KompasService` in `kompas_service.py` aanpassen zodat de query `i.ontologische_beschrijving` ophaalt en mapt aan de node-data.

### Frontend (UI/UX)
- [ ] structuur van `#kompas-details-panel` in `templates/index.html` ombouwen naar een tab-layout.
  - Tab 1: 'Data & Definitie' (bestaande chart en omschrijving).
  - Tab 2: 'Ontologie' (nieuwe content area).
- [ ] Styling toevoegen aan `styles.css` voor `.kompas-tabs` en actieve tab-statussen.
- [ ] `kompas.js` (`expandDetails`) updaten:
  - Tab switch-logica implementeren.
  - Vullen van de ontologie-tekst (of fall-back als er geen ontologie beschikbaar is).
  - Standaard de eerste tab selecteren bij het openen van een nieuw detailvenster.

---

## ✅ Sprint 11: Intelligent Assistant & Admin Integration (25-03-2026, Dag 45)

**Doel:** Uitbreiden van de chat-mogelijkheden naar UI-acties, optimaliseren van de developer experience (herstarttijd) en integreren van beheertoegang in de hoofdapp.  
**Versie:** 2.2.0

- [x] **Track A: Intelligent Chat Dispatcher** (`chat.js`, `app.js`, `kompas.js`, `chat.py`)
    - [x] Intent Dispatcher uitgebreid met UI-acties: `SELECTEER_GEMEENTE`, `SELECTEER_GEBIEDSTYPE`, `SELECTEER_KOMPAS`, `OPEN_KOMPAS`.
    - [x] Pydantic model fix voor data-pass-through naar frontend.
    - [x] EventBus integratie met manual event dispatching (`change` events).
    - [x] Naam-gebaseerde fallback lookup voor gebiedstypes in `app.js`.
- [x] **Track D: Performance & DX** (`run_dev.py`, `llm_service.py`)
    - [x] Uvicorn reload optimalisatie (uitsluiten `node_modules`, `admin-panel`).
    - [x] Lazy loading van AI modellen (SentenceTransformer) voor snellere server start.
    - [x] Introductie `run_dev.py` script voor geoptimaliseerde development omgeving.
- [x] **Track E: Admin Integratie** (`index.html`, `styles.css`, `ReportPage.tsx`, `BenchmarkPage.tsx`)
    - [x] Auth-aware "Beheer" knop toegevoegd aan hoofdapp header.
    - [x] Dynamische routing naar `/admin/login` of `/admin/dashboard`.
    - [x] UX verfijning: "Terug naar Dashboard" → "Sluit rapport" (gebruik van `window.close()`).
- [x] **Documentatie:** `BUGFIX.md` (#34, #35), `ROADMAP.md`, `README.md`, Samenvatting Dag 45.

---

## ✅ Sprint 10: D-Omni Assistent — Chat Interface (19-03-2026, Dag 43)

**Doel:** Intent-based AI chat interface voor het aansturen van de kaart, Kompas en rapport-generatie via natuurlijke taal.  
**Versie:** 2.1.0

- [x] **Fase 0: AI Search Enhancement** (`services/ai_search_service.py`)
    - [x] COALESCE beschrijving: mensvali → AI → omschrijving
    - [x] `ontologie_status`, `eenheid`, `score_type` toegevoegd aan zoekresultaten
- [x] **Fase 1: Backend Chat Endpoint** (`routers/chat.py`, `services/llm_service.py`)
    - [x] `POST /api/chat` endpoint met Command Dispatch JSON
    - [x] Intent classifier (VERKEN_INDICATORS, VERGELIJK_GEBIEDEN, MAAK_RAPPORT, ALGEMEEN)
    - [x] `generate_chat_narrative()` in `llm_service.py` — Nederlandstalige LLM toelichting (≤80 woorden)
    - [x] Chat router  geregistreerd in `main.py`
    - [x] Endpoint getest via curl ✅
- [x] **Fase 2: Frontend Chat Zijpaneel** (`static/js/chat.js`, `templates/index.html`, `static/css/styles.css`)
    - [x] `ChatPanel` klasse  met open/close/toggle, loading dots, chat-historiek
    - [x] cpu.svg toggle-knop (inline SVG) in verticale tab-balk
    - [x] Glassmorphism rechts-zijpaneel (380px, identieke stijl als Kaart Configuratie)
    - [x] Actie-knoppen dispatchen via EventBus (`INDICATOR_SELECTED`)
    - [x] Indicator-lijst: klik = kaart + Kompas sync
    - [x] MAAK_RAPPORT: opent gebiedsdossier of benchmark met huidige selectie-context
    - [x] Licht/donker thema sync (inline SVG ipv img-tag)
- [x] **Chat↔Kompas Sync** (`static/js/kompas.js`)
    - [x] `INDICATOR_SELECTED` EventBus listener in Kompas
    - [x] `_isSyncing` guard voorkomt event-loop (Bug #36 gefixt)
- [x] **Documentatie:** dagelijkse samenvatting, BUGFIX.md, README.md, ROADMAP.md

---


## ✅ Sprint 8E: Kleur-Transformatie "Triple Threat" Palet (03-03-2026)

**Basis:** `docs/4-ux-design/visual/kleur_translatie_tabel_deep_data.md` + `docs/4-ux-design/visual/Concept-collor-overhaul.html`  
**Plan:** `SPRINT_KLEUR_TRANSFORMATIE.md`  
**Doel Versie:** 1.9.0

- [x] **Fase 1 — CSS Tokenisatie (🔴 KRITIEK)**
    - [x] Nieuwe CSS-tokens definiëren in `static/css/styles.css`
    - [x] Bestaande kleurvariabelen vervangen conform translatie tabel
    - [x] Tokens doorvoeren in `static/css/admin.css`
- [x] **Fase 2 — Rood Sanering (🔴 HIGH)**
    - [x] Action knoppen → Trust Blue
    - [x] Status "Verbonden" indicator → Nature Green
    - [x] Admin Panel uitsluitend destructieve acties rood
- [x] **Fase 3 — Geo Gold Implementatie**
    - [x] Actieve kaartgebied selectie `[197, 157, 0]` outline op deck.gl
    - [x] Tab buttons en panel-title accenten via `--accent-color`
- [x] **Fase 4 — Kaartkleurschalen / UI Gradients**
    - [x] Coverage-fill en panel-title gradients → Trust Blue & Nature Green
    - [x] Legenda en KleurschemasPage sync
- [x] **Fase 5 — Dark Mode Hue-Consistency & Light Mode Bugs**
    - [x] `[data-theme="dark"]` variabelen bijgewerkt
    - [x] Logo onzichtbaar in Light mode gefixt (filter)
    - [x] Kompas Sunburst labels thema-aware gemaakt
- [x] **Documentatie:** README.md versie → 1.9.0, BUGFIX.md, dagelijkse samenvatting

---

## ✅ Sprint 8D: Benchmark Kaart-integratie & Bugfixes (02-03-2026)

- [x] **Stap 1:** Nieuw `GET /api/gebieden/zoek?q=` endpoint in `routers/gemeenten.py` (Bug #17)
- [x] **Stap 2:** `zoekGebieden(q)` in `admin-panel/src/services/api.ts`
- [x] **Stap 3:** Live debounced search + URL pre-populatie in `BenchmarkPage.tsx`
- [x] **Stap 4:** Rapport-knop keuze-modal in `static/js/app.js` (Bug #11)
- [x] **Stap 5:** Toelichting rapport paneel bijgewerkt in `templates/index.html`
- [x] **Bug #18:** Benchmark route publiek toegankelijk gemaakt (`App.tsx`)
- [x] **Bug #19:** Gemeente dropdown leesbaarheid dark mode gefixed (`BenchmarkPage.tsx`)
- [x] **Documentatie:** BUGFIX.md, README.md, dagelijkse samenvatting, kleur_audit.md

---

## ✅ Fase 1: Fundament & Configuratie (Voltooid)
- [x] Python Virtual Environment opzetten
- [x] `.env` aanmaken voor database credentials (voorheen config.ini)
- [x] PostgreSQL + PostGIS installatie
- [x] Database en user aanmaken
- [x] FastAPI basis project structuur
- [x] SQLAlchemy setup voor database connectie
- [x] Project documentatie (README, BUILD, TODO)

## ✅ Fase 2: Data Engine (D-Omni Scan) - Gebiedsmonitor
- [x] **Gebiedsmonitor Integratie (Dag 2)**
- [x] **Validatie & Visualisatie (Dag 2)**
- [x] **API Endpoints (DAG 3 - VOLTOOID!)**

## ✅ Fase 3A: Frontend MVP (Dag 3 - VOLTOOID 17-01-2026)
- [x] **Frontend Prototype:**
    - [x] HTML template met deck.gl container
    - [x] Static files setup (FastAPI templates + static mounting)
    - [x] Modern CSS styling (glassmorphism, gradients, animations)
    - [x] deck.gl 3D kaart met GeoJsonLayer

## ✅ Fase 3B Sprint 1: Core UX Improvements (VOLTOOID - 18-01-2026)
- [x] **UI Redesign - Fullscreen Kaart**
- [x] **Legenda Systeem**
- [x] **Mapbox Basemap Integration**
- [x] **Export Functionaliteit**

## ✅ Sprint 4: Kompas Visualisatie (Dag 6-10) - **VOLTOOID 24-01-2026** ⚡
- [x] **Database Schema v4** (upgrade van v3)
- [x] **Backend API** (Dag 7 - 22-01-2026) ✅
- [x] **Frontend D3.js** (Dag 8-9 - 23-01-2026) ✅

## ✅ Sprint 4B-D: Visual Polish & Scoring (Dag 11-14)
- [x] **Scoring Logica:** Percentiel methodiek (8-bins)
- [x] **Classic Premium UI:** Dark theme gradient accents
- [x] **Bugfixes:** Kompas zoom, toggle, text scaling

---

## 🔐 Sprint 5: Beheerscherm MVP (Voltooid)

> **Context:** Admin Panel voor Kompas beheer - indicator configuratie, score types, kleurschemas.  
> **Status:** Backend + React Frontend MVP ✅

### ✅ Fase 1: Backend API (01-02-2026 - VOLTOOID)
- [x] **Database Schema v5:**
    - [x] `color_schemas` tabel met 4 default schemas
    - [x] `indicatoren` uitgebreid met `score_type`, `color_schema_id`, `admin_notes`
    - [x] Migration script: `data/schema_v5_beheerscherm.sql`
- [x] **Admin Router (`routers/admin.py`):**
    - [x] API key authenticatie middleware (`X-Admin-Key`)
    - [x] `GET /api/admin/health` - health check
    - [x] `GET /api/admin/score-types` - score type opties
    - [x] `GET /api/admin/color-schemas` - kleurschema's
    - [x] `GET /api/admin/indicatoren` - indicator lijst met search/pagination
    - [x] `GET/PUT /api/admin/indicatoren/{uuid}` - indicator CRUD
    - [x] `GET /api/admin/hierarchie/tree` - kompas tree structuur

### ✅ Fase 2: React Frontend (01-02-2026 - MVP VOLTOOID)
- [x] **Project Setup:**
    - [x] React + TypeScript + React Router
    - [x] Dependencies: React Query, Axios, Zustand, D3, Lucide
    - [x] D-OmniTwin matching CSS (dark theme)
- [x] **Pagina's:**
    - [x] Login (API key verificatie)
    - [x] Dashboard (stats, Kompas overzicht)
    - [x] Indicatoren (zoeken, pagination, inline editor)
- [x] **API Service Layer:**
    - [x] TypeScript types voor alle models
    - [x] Axios interceptor voor auth headers
    - [x] Zustand store voor state management

### 🔜 Fase 3: Advanced Features (25% COMPLEET - 03-02-2026)
- [x] **D3 Collapsible Tree:** ✅ COMPLEET (03-02-2026)
    - [x] Hiërarchie visualisatie component (`HierarchiePage.tsx`)
    - [x] Click-to-expand/collapse animaties
    - [x] Rechtermuisklik voor details panel
    - [x] Breadcrumb navigatie
    - [x] Production build succesvol (127 kB JS, 1.78 kB CSS)
- [ ] **Kompas Preview:**
    - [ ] Live preview van configuratie
    - [ ] Score type effect visualisatie
- [ ] **Kleurschema Beheer:**
    - [ ] CRUD voor custom schemas
    - [ ] Color picker UI
- [ ] **Production Integration:**
    - [ ] `npm run build` → static files
    - [ ] FastAPI serve van `/admin` route
- [ ] **Kompas Hiërarchie Reorganisatie:**
    - [ ] Onderdeel "Klimaat" (Openbare ruimte > Klimaat) opsplitsen in 3 sub-thema's:
        - Hemelwater overlast
        - Droogte
        - Hittestress
    - [ ] Bestaande klimaat-indicatoren herindelen naar juiste sub-thema

**Priority:** 🟡 MEDIUM  
**Effort Restant:** ~4-5 uur  
**Volgende Sessie:** Zie `BEHEERSCHERM_FASE3_PLAN.md` in root


## 🛠️ Sprint 5E: Project Structure & Maintenance (Dag 21 - CURRENT)
- [ ] **ETL Restructuring**
    - [ ] Create `ETL/` root directory
    - [ ] Move CBS scripts to `ETL/CBS/`
    - [ ] Move BAG scripts to `ETL/BAG/`
    - [ ] Move Kompas scripts to `ETL/Kompas/`
    - [ ] Verify imports after move
- [x] **Kompas Export**
    - [x] Script `export_kompas_hierarchie.py` created

- [x] Script `export_kompas_hierarchie.py` created

## 📊 Sprint 5F: Admin Dashboard (Dag 23 - CURRENT)
- [x] **Backend Implementation**
    - [x] Router `dashboard.py` created
    - [x] Endpoints: `/stats`, `/quadrants`, `/indicators`
- [x] **Frontend Implementation**
    - [x] DashboardPage created
    - [x] Components: StatsCard, QuadrantChart, IndicatorsTable, Sparkline
- [x] **Data Verification & Debugging**
    - [x] 🔴 **FIX:** Dashboard shows 0 data coverage (Fixed Ambiguous Column)
    - [x] **Test:** Verify quadrant mapping matching `v_kompas_hierarchie`
    - [x] **Polish:** Fix sparkline rendering (Implemented in IndicatorsTable)
- [x] **Export & Finalization**
    - [x] Implement CSV Export Endpoint
    - [x] Update Documentation (BUGFIX, BUILD, ROADMAP)

---

## 🎨 Sprint 5D: Visualisatie Standaard (Week 10) - **VOLTOOID 15-02-2026** ✅
**Context:** Verbeterslag voor kaartvisualisatie met database-driven color schemas.  
**Basis:** `docs/4-ux-design/visual/kaartkleuring_visualisatie_d_omn_itwin.md`  
**Status:** Backend + Admin UI + Map Integration ✅

### ✅ Fase 1: Database Schema v6 (15-02-2026)
- [x] **Database Schema:**
    - [x] Extend `color_schemas` met `palette_type`, `classificatie`, `klassen`, `nodata_kleur`
    - [x] 8 nieuwe palettes (sequential, diverging,specialized)
    - [x] Create table `visualisatie_profielen` met indicator pattern matching
    - [x] Migration script `data/schema_v6_visualisatie.sql`
- [x] **Backend API:**
    - [x] Router `visualisatie.py` created
    - [x] Public endpoints: `GET /paletten`, `GET /config/{uuid}`
    - [x] Admin CRUD: `/admin/paletten`, `/admin/profielen`

### ✅ Fase 2: Admin Panel UI (15-02-2026)
- [x] **KleurschemasPage.tsx:**
    - [x] Tabbed interface (Palettes / Profiles)
    - [x] Live color gradient previews
    - [x] Color picker modal met real-time interpolatie
    - [x] Profile editor met schema linking
    - [x] Build succesvol (exit 0)

### ✅ Fase 3: Backend Map Integration (15-02-2026)
- [x] **ColorScaleService:**
    - [x] 4 classification methods (quantile, equal_interval, jenks, diverging_midpoint)
    - [x] Color ramp generatie (min → mid → max)
    - [x] Database config lookup met fallback
- [x] **Gebiedsmonitor Service:**
    - [x] Replace hardcoded colors met ColorScaleService
    - [x] Map displays dynamic colors from admin panel ✅

### 🔜 Fase 4: Frontend Client Integration (In Progress)
- [x] `app.js` - Legend sync: `updateLegenda()` geconsolideerd (Bug #9 FIXED - Dag 27)
- [x] `app.js` - Kompas → Legend explicit sync via `handleIndicatorSelection`
- [ ] `app.js` - Legend kleuren dynamisch matchen met indicator kleurschema (palette uit backend)
- [ ] `app.js` - Fetch config from `/api/visualisatie/config/{uuid}`
- [ ] Transitie animaties bij schema wijziging

### 📋 Belangrijke TODO's Volgende Sessie
- [x] ~~**Gemeente Code Verificatie (PRIORITEIT!):**~~ ✅ OPGELOST (Dag 27)
    - [x] Check De Fryske Marren & Smallingerland missing data → Codes correct, import herhaald
- [ ] **Legenda Kleurmatching:** Dynamische kleurbalk die indicator palette toont ipv hardcoded gradient


    - [ ] Models: `VisualisatieProfiel`, `KleurPalet`
    - [ ] Router: `routers/visualisatie.py`

### Fase 2: Frontend Logic (Week 2)
- [ ] **Color Services:**
    - [ ] `services/ColorScaleService.ts` (D3 logica)
    - [ ] Definitie van standaard paletten (Blue, Gold, etc.)
- [ ] **Deck.gl Update:**
    - [ ] `getFillColor` ombouwen naar datadriven config

### Fase 3: UI (Week 3)
- [ ] **Legenda:**
    - [ ] Nieuwe React component met histogram optie
- [ ] **Tooltips:**
    - [ ] Update `app.js` tooltip template met units/percentiles


## 🗄️ Sprint 5A: Database Cleanup & Consolidatie (Voltooid)

**Context:** Opruimen legacy componenten en schema consolidatie  
**Basis:** Database Architectuur Analyse (docs/7-projectmanagement/logs/DATABASE_ARCHITECTUUR_ANALYSE.md)  
**Status:** ✅ 100% COMPLEET

> [!CAUTION]
> **⚠️ LET OP: PRODUCTIE DATABASE BLIJFT INTACT!**
> 
> Deze sprint ruimt ALLEEN legacy componenten op:
> - ✅ DROP van 1 ongebruikte tabel (`configuratie_instanties`)
> - ✅ DROP van 3 ongebruikte views
> - ✅ Archiveren van oude schema FILES (niet de database zelf!)
> 
> **NOOIT uitvoeren op productie:**
> - ❌ `dropdb omnitwin_db` → VERBODEN!
> - ❌ Volledige database recreatie
> 
> **Schema testing gebeurt op APARTE test database:**
> - `omnitwin_test_db` ← ALLEEN voor testen nieuwe scripts
> - Productie database: `omnitwin_db` ← ONAANGETAST (behalve legacy cleanup)

### Fase 1: Legacy Cleanup (2-3 uur) ✅ COMPLEET
- [x] **Verwijder `configuratie_instanties` tabel** (30 min)
    - [x] Verificatie: 0 foreign key dependencies
    - [x] Backup: `data/backups/backup_configuratie_instanties_20260203.sql`
    - [x] Execute: `DROP TABLE IF EXISTS configuratie_instanties CASCADE`
    - [ ] Update ARCHITECTURE.md (verwijder alle referenties)
- [x] **Archive oude schema files** (15 min)
    - [x] `mkdir -p data/backups/archive`
    - [x] Moved: schema.sql, schema_v2, v3, v4_multi_kompas, v4_views
    - [x] v5_beheerscherm.sql behouden voor referentie
- [x] **Verwijder ongebruikte views** (30 min)
    - [x] `DROP VIEW IF EXISTS v_indicatoren_actueel CASCADE`
    - [x] `DROP VIEW IF EXISTS v_gebieden_met_data CASCADE`
    - [x] `DROP VIEW IF EXISTS v_gebied_data_overzicht CASCADE`
    - [x] Verificatie: 7 views remaining (incl. PostGIS systeem views)

### Fase 2: Schema Consolidatie (2-3 uur) ✅ COMPLEET
- [x] **Creëer `data/schema_latest.sql`** (2 uur)
    - [x] Geconsolideerde SQL vanuit DATABASE_INITIALISATIE_HANDLEIDING.md
    - [ ] Test op clean database (optioneel - handmatig uitvoeren)
- [x] **Update BUILD.md** (1 uur)
    - [x] Nieuwe installatie sectie: gebruik `schema_latest.sql`
    - [x] Referentie naar DATABASE_INITIALISATIE_HANDLEIDING.md
    - [x] Migration sectie toegevoegd

### Fase 3: Documentatie (1 uur)
- [x] **README.md updates**
    - [x] Add link: [Database Architectuur](docs/7-projectmanagement/logs/DATABASE_ARCHITECTUUR_ANALYSE.md)
    - [x] Add link: [Database Initialisatie](docs/7-projectmanagement/logs/DATABASE_INITIALISATIE_HANDLEIDING.md)
- [x] **ARCHITECTURE_TECHNICAL_OPERATION.md updates**
    - [x] Embed ER diagram (copy mermaid from DATABASE_ARCHITECTUUR_ANALYSE.md)
    - [x] Update Table Inventory sectie (15 tables, 7 views)
    - [x] Remove configuratie_instanties references (geen gevonden)

**Verificatie Checklist:**
- [x] `configuratie_instanties` tabel bestaat niet meer
- [x] `data/schema_latest.sql` aangemaakt
- [x] Oude schemas in `data/backups/archive/`
- [x] Documentatie bijgewerkt (README, BUILD, ARCHITECTURE)

**Status:** ✅ 100% COMPLEET

---

## 📚 Sprint 5B: Data Verrijking & Documentatie (Voltooid 10-02-2026)

**Context:** Inventarisatie & Documentatie van BAG, Postcodegebieden, en EP-Online.
**Basis:** `docs/7-projectmanagement/logs/DATASET_METADATA_NIEUWE_BRONNEN.md`

- [x] **Documentatie:**
    - [x] Metadata voor 4 cruciale datasets (BAG, PC4, PC6, EP-Online)
    - [x] Verwerkingsplannen en ETL pipelines uitgewerkt
    - [x] 9 Nieuwe indicatoren gedefinieerd en gemapped naar Kompas
- [x] **Bugfix Kompas Service:**
    - [x] Robuuste afhandeling van JSON velden (thresholds)

---

## 🏗️ Sprint 5C: BAG Fryslân Data Integratie (CURRENT - Week 9)

**Context:** Uitbreiding van woningindicatoren met BAG gebouwkenmerken  
**Basis:** DATASET_METADATA_NIEUWE_BRONNEN.md + NIEUWE_INDICATOREN_MAPPING.md  
**Status:** ✅ VOLTOOID (15-02-2026)

### Fase 1: ETL Pipeline Ontwikkeling (6-8 uur)
- [x] **Script: `import_bag_indicators.py`** (Replaced by `run_bag_import.py`)
  - [x] Lees `cleaned_bag_data_verblijfsobject.gpkg` met GeoPandas
  - [x] Lees `bag_data_bag_pand.gpkg` voor bouwjaar data
  - [x] Spatial join met CBS buurten (`gebieden` tabel, gebiedstype='BU')
  - [ ] Spatial join met PC4 gebieden (indien PC4 al geïmporteerd) -> Moved to Sprint 5D
  - [x] Aggregate per gebied:
      - Gemiddeld bouwjaar (AVG)
      - % voor 1945 (COUNT WHERE bouwjaar < 1945)
      - Gemiddelde oppervlakte (AVG)
      - % woonfunctie (COUNT WHERE  woonfunctie=true)
  - [x] **Data Gaten Fix (Bouwjaren):**
      - [x] Specifieke focus op **Smallingerland** en **De Fryske Marren**: data ontbreekt voor bouwjaren.
      - [x] Analyseer oorzaak (ontbrekende VBO-Pand koppeling? PAND status?) (Fixed via VBO filtering)
      - [x] Implementeer fix in `import_bag_indicators.py`
      - Diversiteit functies (Simpson Index)
  - [x] Insert naar `gebied_data` met nieuwe indicator UUIDs
- [x] **Kwaliteitscontroles**
  - [x] Pre-import validatie: bouwjaar range (1600-2026), oppervlakte > 0
  - [x] Post-import verification: coverage check (>90% buurten met data)
  - [x] Sanity checks: gemiddeld bouwjaar Fryslân ~1965, % voor-1945 ~30%
- [x] **Onderzoek Data Gaten (Smallingerland/De Fryske Marren)**
  - [x] Analyzeer `gebieden` tabel: check parent-child relaties voor deze gemeenten (Fixed Missing GM records)
  - [x] Verifieer CBS buurt-code mapping (verschillen gemeentecodes door herindelingen?) (Fixed 0140->0090, 1921->1940)
  - [x] Check BAG import log voor errors in deze regio's (Resolved via manual insert)

### Fase 2: Indicator Configuratie (2-3 uur)
- [x] **Beheerscherm Invoer (Admin Panel)**
  - [x] Nieuwe indicatoren aanmaken
  - [x] Koppelen aan Kompas dimensies
- [x] **Metadata Verrijking**
  - [x] Omschrijvingen: "Gemiddeld bouwjaar van woningen in dit gebied, afgeleid van BAG pand registratie"
  - [x] Bronvermelding: "Kadaster BAG (Basisregistratie Adressen en Gebouwen)"
  - [x] Eenheden correct (jaar, %, m²,  index)

### Fase 3: EP-Online Coverage Indicator (2 uur)
- [x] **Nieuwe indicator: % huishoudens met energielabel**
  - [x] Aanmaken in database (code: `pct_energielabel`, eenheid: %, score: +=+)
  - [x] SQL berekening: `aantal_energielabels / huishoudens_bag * 100`
  - [x] Insert data fopr alle buurten met beide bronnen
  - [x] Validatie: Fryslân gemiddeld ~57.6% coverage

### Fase 4: Verificatie \u0026 Testing (2 uur)
- [x] **Kaart Test**
  - [x] Selecteer indicator "Gemiddeld bouwjaar" in frontend
  - [x] Visuele check: historische kernen (bv. Dokkum, Sneek) hebben lagure waarde
  - [x] Visuele check: nieuwe wijken (bv. Grou-Zuid) hebben hoge waarde
  - [x] Kleurenschaal logisch: Blauw=oud, Groen=nieuw
- [x] **Kompas Test**
  - [x] Open Kompas voor buurt met gemengde bouwjaren
  - [x] Valideer score berekening voor "% voor 1945"
  - [x] Check visuele weergave in sunburst chart
- [x] **Data Coverage Query**
    ```sql
    SELECT COUNT(DISTINCT gebied_id) AS buurten_met_bag
    FROM gebied_data gd
    JOIN indicatoren i ON i.uuid = gd.indicator_uuid
    WHERE i.code IN ('gemiddeld_bouwjaar', 'pct_voor_1945');
    -- Target: >900 van 965 Friese buurten (>93%)
    ```
- [x] **Correlatie Validatie**
  - [x] Check: Negatieve correlatie bouwjaar ↔ energielabel (nieuwer = beter label)
  - [x] Check: Positieve correlatie % voor-1945 ↔ slechtere energielabels

**Deliverables Sprint 5C:**
- ✅ `scripts/import_bag_indicators.py` operational
- ✅ 6 nieuwe BAG-gebaseerde indicatoren in database
- ✅ Kompas integratie getest en functioneel
- ✅ EP-Online coverage indicator met BAG denominateur

---

## 🗄️ Sprint 5G: PC4 Postcode Aggregatieniveau (Backlog - Week 12+)

**Context:** Toevoegen van PC4 als nieuw gebiedstype voor regionale analyses
**Rationale:** Verschoven tgv prioriteit Visualisatie (Sprint 5D)
**Basis:** VERWERKINGSPLAN_NIEUWE_DATASETS.md
**Priority:** 🟡 MEDIUM | **Effort:** 6-8 uur

### Fase 1: Database Schema (2 uur)
- [ ] **Gebiedstype toevoegen**
    ```sql
    INSERT INTO gebiedstypes (id, naam, niveau)
    VALUES ('PC4', 'Postcode 4-cijfers', 3);
    ```
- [ ] **Import PC4 gebieden** (script: `import_postcodegebieden.py`)
  - [ ] Lees `postcodegebieden_fryslan.gpkg`
  - [ ] Insert ~950 PC4 gebieden naar `gebieden` tabel
  - [ ] Geometrie in RD New (EPSG:28992), centroid berekenen
- [ ] **Provincie grens als kaartlaag**
  - [ ] Create table `kaartlagen` (id, naam, geometry, layer_type)
  - [ ] Insert provincie Fryslân boundary

### Fase 2: Data Aggregatie Pipeline (2-3 uur)
- [ ] **Aggregatie Script** (`aggregate_buurt_to_pc4.py`)
  - [ ] Voor alle bestaande indicatoren: aggregate buurt → PC4
  - [ ] Methode: Spatial join (buurt centroid binnen PC4 polygon)
  - [ ] Aggregatie functie: AVG voor meeste indicatoren
  - [ ] Insert naar `gebied_data` met gebied_id = "PC4xxxx"

### Fase 3: Frontend Integratie (2-3 uur)
- [ ] **Frontend Integratie**
  - [ ] 🔴 **FIX:** PC4 optie toevoegen aan `KaartConfiguratie` component (ontbreekt nu)
  - [ ] **Aggregatieniveau Dropdown** (NIET PC4 zoekfunctie!)
  - [ ] Update `/static/js/kaart.js`: aggregatie dropdown toevoegen
    ```javascript
    <select id="aggregatie-niveau">
      <option value="BU">Buurt</option>
      <option value="WK">Wijk</option>
      <option value="PC4">Postcode 4-cijfers</option>
      <option value="GM">Gemeente</option>
    </select>
    ```
  - [ ] Gemeentesearch BEHOUDEN (ongewijzigd)
  - [ ] API call: `/api/gebiedsmonitor/kaart?gemeente_id=GM0081&aggregatie_niveau=PC4`
  - [ ] Backend: Filter PC4 gebieden WHERE parent_id = gemeente_id
- [ ] **Database: PC4 ↔ Gemeente Koppeling**
  - [ ] Voeg `parent_id` (gemeente_code) toe aan PC4 import
  - [ ] Voorbeeld: PC4 "8888" heeft parent_id "GM0081" (Súdwest-Fryslân)
- [ ] **Provincie Boundary Overlay**
  - [ ] Nieuw endpoint: `GET /api/kaartlagen/provincie_fryslan` (GeoJSON)
  - [ ] deck.gl layer: GeoJsonLayer met stroked=true, filled=false
  - [ ] Styling: Zwarte lijn, 2px breed

**Deliverables Sprint 5G:**
- ✅ PC4 gebiedstype actief in database (~950 gebieden)
- ✅ Alle indicatoren geaggregeerd naar PC4 niveau
- ✅ Frontend dropdown met PC4 optie
- ✅ Provincie grens als visuele overlay

---

## 🔜 Sprint 6: Authentication \u0026 Data Management (Week 11-12)

(Bestaande content, zie hieronder...)

---

## 📤 Sprint 7-9: API voor Data Vulling (Week 9-14)

**Context:** Web-based upload API ter vervanging van batch scripts  
**Rationale:** User-friendly, real-time validation, access control, audit logging  
**Basis:** DATABASE_ARCHITECTUUR_ANALYSE.md Sectie 10  
**Priority:** 🟡 MEDIUM-HIGH | **Total Effort:** 6 weken (240 uur)

### Sprint 7: Upload Endpoints + Validation (Week 9-10 - 2 weken)

#### Week 1: Core Endpoints
- [ ] **Setup Upload Infrastructure**
    - [ ] Create `routers/upload.py`
    - [ ] Dependencies: `python-magic` (MIME detection), `aiofiles` (async I/O)
    - [ ] Temp storage directory: `/tmp/omnitwin_uploads/`
- [ ] **CSV Metingen Upload Endpoint**
    - [ ] `POST /api/upload/csv/metingen`
    - [ ] Request: `multipart/form-data` (file, indicator_uuid, jaar)
    - [ ] Validation: MIME type (text/csv), file size (<10MB), UTF-8 encoding
    - [ ] Response: `{"job_id": "...", "status": "queued"}`
- [ ] **GeoJSON Gebieden Upload Endpoint**
    - [ ] `POST /api/upload/geojson/gebieden`
    - [ ] Request: `multipart/form-data` (file, gebiedstype_id)
    - [ ] SRID transformatie: WGS84 (4326) → RD New (28992)
    - [ ] Automatic centroid calculation (ST_Centroid)
    - [ ] Geometry validation: ST_IsValid, type check (MultiPolygon)

#### Week 2: Validation Pipeline + Testing
- [ ] **Multi-Layer Validation Service** (`services/validation_service.py`)
    - [ ] **File Level:**
        - MIME type check (python-magic)
        - File size limit (configurable, default 10MB)
        - Encoding detection (chardet)
    - [ ] **Schema Level:**
        - CSV: columns present (gebied_id, waarde, etc.)
        - GeoJSON: required properties (type, features, geometry)
        - Data types correct (pandas dtype validation)
    - [ ] **Business Logic:**
        - Foreign keys exist (gebied_id in gebieden, indicator_uuid in indicatoren)
        - Value ranges (min_waarde <= waarde <= max_waarde)
        - Jahr validity (>= 2000, <= current_year + 10)
- [ ] **Error Handling & Reporting**
    - [ ] Partial import strategy (succeed rows + error report)
    - [ ] Error format: `{"row": 42, "column": "waarde", "error": "Value out of range (0-100)"}`
    - [ ] Downloadable error report (CSV format)
- [ ] **Unit Tests** (pytest)
    - [ ] `test_upload_valid_csv_happy_path` - Should succeed
    - [ ] `test_upload_invalid_mime_type` - Should reject with 400
    - [ ] `test_upload_foreign_key_violation` - Partial import + error report
    - [ ] `test_upload_malformed_geojson` - Should reject with 400
    - [ ] Target coverage: >80%

**Deliverables Sprint 7:**
- ✅ 2 upload endpoints operational (`/csv/metingen`, `/geojson/gebieden`)
- ✅ Validation pipeline tested (>80% coverage)
- ✅ Error reporting functional

---

### Sprint 8: Async Processing + Admin UI (Week 11-12 - 2 weken)

#### Week 3: Background Processing Infrastructure
- [ ] **Redis Installation & Config**
    - [ ] `sudo apt install redis-server`
    - [ ] Config: `redis.conf` (bind 127.0.0.1, requirepass)
    - [ ] Test: `redis-cli ping` → PONG
- [ ] **Celery Setup**
    - [ ] Install: `pip install celery redis`
    - [ ] Create `celery_app.py` (Celery application)
    - [ ] Create `tasks/upload_tasks.py` (task definitions)
    - [ ] Systemd service: `omnitwin-celery-worker.service`
- [ ] **Background Task Definition**
    - [ ] `@celery_app.task def process_csv_upload(file_path, user_id, indicator_uuid, jaar)`
    - [ ] Batch processing: 1000 rows per batch (performance)
    - [ ] Progress updates: `update_state(state='PROGRESS', meta={'current': 500, 'total': 10000})`
    - [ ] Error collection: append to errors list, continue processing
- [ ] **AI-Beheer Tools Integratie (Kwaliteitscontrole):**
    - [ ] `audit_ontologie` functie integreren in Admin Dashboard (detectie van 'dirty' ontologieën).
    - [ ] `genereer_ontologie` (re-generation) actie per indicator of bulk in de UI.
    - [ ] Visualisatie van 'Hek en Bron' status per item.
- [ ] **Job Management System**
    - [ ] Database table: `upload_jobs` (id, user_id, filename, status, progress, errors, created_at)
    - [ ] `POST /api/upload/csv/async` → save file, create job record, queue task → return job_id
    - [ ] `GET /api/jobs/{job_id}` → `{"status": "processing", "progress": 45, "errors": [...]}`
    - [ ] Job cleanup: cron job to delete jobs >7 days old
- [ ] **Progress Tracking**
    - [ ] Frontend polling: `GET /api/jobs/{id}` elke 2 seconden
    - [ ] Status states: `pending` → `processing` → `completed` | `failed`
    - [ ] Webhook support (future): POST to callback URL on completion

#### Week 4: Admin Panel Upload UI
- [ ] **Upload Page Component** (`admin-panel/src/pages/DataUpload.tsx`)
    - [ ] Install: `npm install react-dropzone`
    - [ ] Drag-drop file zone (visual feedback on hover)
    - [ ] File preview: table met eerste 10 rijen (pandas `.head()` via API)
    - [ ] Column mapping wizard: CSV columns → DB columns (dropdown mapping)
    - [ ] Upload button + cancel button
- [ ] **Progress UI Component**
    - [ ] Progress bar (0-100%)
    - [ ] Status message ("Processing row 5000/10000...")
    - [ ] Cancel button (DELETE /api/jobs/{id})
    - [ ] Success animation (✅ + confetti)
- [ ] **Job History Page** (`admin-panel/src/pages/UploadHistory.tsx`)
    - [ ] Table: Filename | User | Status | Rows | Timestamp | Actions
    - [ ] Filter: My uploads / All uploads (admin only)
    - [ ] Re-run failed jobs button
    - [ ] Download error report button (CSV download)
- [ ] **API Service Integration**
    - [ ] TypeScript types: `UploadJob`, `UploadProgress`, `UploadError`
    - [ ] Zustand store: `useUploadStore` (jobs list, current job)
    - [ ] React Query: `useUploadMutation`, `useJobStatus` (polling)

**Deliverables Sprint 8:**
- ✅ Async processing operational (Celery workers running)
- ✅ Admin panel upload UI functional
- ✅ Job history tracking complete

---

### Sprint 9: Production Hardening + Migration (Week 13-14 - 2 weken)

#### Week 5: Security & Performance
- [ ] **Security Layer**
    - [ ] File size limits: configurable via ENV (default 10MB, max 100MB for admins)
    - [ ] Virus scan integration: ClamAV Docker container (optional but recommended)
        - `docker run -d -p 3310:3310 clamav/clamav`
        - Python client: `clamd` library
    - [ ] Rate limiting: `slowapi` middleware (5 uploads/hour per user)
    - [ ] Input sanitization: prevent path traversal (`os.path.basename(filename)`)
    - [ ] File type whitelist: only `.csv`, `.geojson`, `.json`, `.xlsx`
- [ ] **Performance Optimization**
    - [ ] Batch insert: Use PostgreSQL COPY instead of INSERT for large CSVs
    - [ ] Connection pooling: tune SQLAlchemy pool size (max_overflow=10)
    - [ ] Temp file cleanup: cron job `find /tmp/omnitwin_uploads -mtime +1 -delete`
    - [ ] Progress granularity: update every 100 rows (not every row)
- [ ] **Audit Logging**
    - [ ] Database table: `upload_audit` (user_id, action, table_name, rows_affected, timestamp)
    - [ ] Log all data mutations: INSERT (upload), UPDATE (metadata), DELETE (cleanup)
    - [ ] Retention policy: keep audit logs >6 months

#### Week 6: Migration & Documentation
- [ ] **Script Migration & Deprecation**
    - [ ] Create `scripts/legacy/README.md`:
        ```
        # DEPRECATED: Use Admin Panel Upload Instead
        
        These scripts are maintained for reference only.
        For data uploads, use the Admin Panel: <https://omnitwin.example.com/admin/upload>
        ```
    - [ ] Move scripts:
        - `mv scripts/import_*.py scripts/legacy/`
        - Keep `scripts/validate_*.py` (still useful for testing)
- [ ] **User Training Materials**
    - [ ] Upload UI walkthrough (docs/7-projectmanagement/logs/UPLOAD_GUIDE.md):
        - Screenshot: drag-drop zone
        - Screenshot: column mapping wizard
        - Screenshot: progress tracking
    - [ ] Video tutorial (3-5 min screencast)
    - [ ] Troubleshooting guide:
        - Common error: foreign key violation → check gebied_id exists
        - Common error: large file timeout → split into smaller batches
- [ ] **Integration Tests** (pytest + Playwright)
    - [ ] End-to-end: upload CSV → async processing → data in DB → verify waarden
    - [ ] Error scenario: upload file with invalid data → partial import → error report download
    - [ ] Network failure: upload starts → cancel mid-processing → verify rollback
- [ ] **Production Deployment Checklist**
    - [ ] Environment variables: REDIS_URL, CELERY_BROKER_URL, UPLOAD_MAX_SIZE
    - [ ] Systemd services: celery-worker, celery-beat (for periodic cleanup)
    - [ ] Nginx config: `client_max_body_size 100M;` (allow large uploads)
    - [ ] Monitoring: Celery Flower dashboardfor task monitoring (`pip install flower`)

**Deliverables Sprint 9:**
- ✅ Production-ready upload API (secured, performant, audited)
- ✅ Legacy scripts deprecated with clear migration path
- ✅ Complete user documentation + training materials

**Sprint 7-9 Total:**
- **Priority:** 🟡 MEDIUM-HIGH
- **Effort:** 6 weken (240 uur) - 2 full-stack developers
- **Dependencies:** Redis, Celery, ClamAV (optional)
- **Enables:** Self-service data management, improved data quality, audit compliance

---

### 🚨 Punt 0: Emergency Patch (2-4 uur) ✅ VOLLEDIG COMPLEET
- [x] **Environment Variables Setup:**
    - [x] Installeer `python-dotenv`
    - [x] Maak `.env` file met alle secrets (DATABASE_PASSWORD, SECRET_KEY, etc.)
    - [x] Voeg `.env` toe aan `.gitignore`
    - [x] Verwijder `config.ini` uit git repository (niet getrackt)
    - [x] Update `src/database.py` en `main.py` naar `os.getenv()`
- [x] **CORS Lockdown:**
    - [x] Vervang `allow_origins=["*"]` door specifieke domains in `.env` (`CORS_ORIGINS`)
    - [x] Test CORS restrictie met curl
- [x] **Security Headers Middleware:**
    - [x] Implementeer `SecurityHeadersMiddleware` in `main.py`
    - [x] CSP, X-Frame-Options, X-Content-Type-Options headers
- [x] **Database SSL/TLS:**
    - [x] Add `DATABASE_SSLMODE` to `.env` (default: `prefer`, prod: `require`)
    - [x] Update `src/database.py` connection string met `?sslmode={mode}`
    - [x] Verificatie: Database online met SSL mode
- [x] **Local Swagger UI Assets:**
    - [x] Assets gedownload naar `static/swagger-ui/`
    - [x] CSP aangescherpt (geen externe CDNs meer nodig voor docs)
    - [x] Custom `/docs` endpoint in `main.py`
- [x] **Input Validation (Basis):**
    - [x] Audit SQL queries (✅ geen f-strings - alle queries parameterized!)
    - [x] API endpoints gebruiken Pydantic response models

**Verificatie:**
- [x] App start zonder errors
- [x] `.env` is in `.gitignore`
- [x] `curl -I http://localhost:8000/` toont security headers
- [x] CORS locked naar specifieke origins (vanuit .env)
- [x] Database verbinding werkt met SSL mode (`sslmode=prefer`)

**Priority:** AFGEROND ✅  
**Status:** 🟢 100% Compleet - Risk level: 🟡 MEDIUM (was 🔴 HIGH)  
**Blocker voor:** Alle verdere development (geen features op onveilige basis)

### Fase 1: Transport & Trust (1 week)
- [ ] **TLS/SSL Certificate:**
    - [ ] Let's Encrypt certificate aanvragen (certbot)
    - [ ] Nginx reverse proxy setup (backend draait op 127.0.0.1)
    - [ ] HTTPS redirect middleware (HTTP → HTTPS)
- [ ] **Database SSL (Productie):**
    - [ ] PostgreSQL SSL certificaten genereren (server.crt, server.key)
    - [ ] Enable `ssl = on` in `postgresql.conf`
    - [ ] Zet `DATABASE_SSLMODE=require` in productie `.env`
- [ ] **Network Isolatie:**
    - [ ] Database achter private subnet (geen publiek IP)
    - [ ] Backend alleen bereikbaar via proxy
- [ ] **Monitoring:**
    - [ ] Basic logging naar file (`/logs/app.log`)
    - [ ] Error alerting (email/Slack notificatie bij 500 errors)

**Priority:** 🔴 HIGH  
**Effort:** 8-10 uur (+ wachttijd voor DNS/cert)

---

## ✅ Sprint 6: Authentication & Data Management (Voltooid)

> **Belangrijk:** Beheerscherm-kompas is verschoven naar Sprint 6 (was 5). Eerst moet auth systeem er staan.

### ✅ Fase 2: Identity (Hybrid Auth Model)
- [x] **User Database Schema:**
    - [x] `users` tabel (email, hashed_password, role)
    - [x] `sessions` tabel (voor session-based auth)
    - [x] `api_keys` tabel (voor data upload scripts)
- [x] **Session-Based Auth (Admin UI):**
    - [x] Login/Logout endpoints & Account Wachtwoord API
    - [x] HttpOnly Secure cookies
    - [x] Password hashing (bcrypt)
- [x] **API Key Auth (Data Scripts):**
    - [x] Key generation endpoint (admin-only)
    - [x] Header-based validation (`X-Admin-Key`)
- [x] **Authorization Middleware:**
    - [x] `@require_auth` beveiliging voor endpoints
    - [x] Role-based access (`admin`, `viewer`)
- [x] **Frontend Login UI:**
    - [x] Login form & Redirection (`ProtectedRoute`)
    - [x] Account beheer pagina (`AccountPage`)
    - [x] Session status indicator (Header Dropdown)

**Priority:** ✅ AFGEROND
**Effort:** ~12-16 uur
**Enables:** Beheerscherm-kompas (zonder auth is beheer onveilig!)

### Beheerscherm-Kompas (🔴 HIGH PRIORITY)
> **Context:** Admin panel voor metadata, wegingen, en indicator-relaties.  
> **Vereist:** Fase 2 (Auth) moet compleet zijn.

- [x] **Concept \u0026 Design:**
    - [x] UI wireframes (figma/sketch of markdown beschrijving)
    - [x] Data model voor wegingen tabel
- [x] **Frontend Interface:**
    - [x] CRUD voor indicator metadata (naam, omschrijving, eenheid, scores)
    - [x] Relatie editor (indicators ↔ thema's)
    - [ ] Weging configuratie per kompas-niveau
- [x] **Backend API:**
    - [x] Protected endpoints (`@require_admin` en CRUD indicator logic)
    - [ ] Validation logic (kan X indicator wel in Y thema?)
    - [ ] Audit logging (wie wijzigde wat wanneer?)

**Priority:** 🔴 HIGH (maar NA auth implementatie)  
**Effort:** 16-20 uur  
**Impact:** Oplossen van 200+ missing metadata items

---

## ✅ Sprint 7: Multi-Gebied Analyse (Voltooid 02-03-2026)

**Context:** Vergelijkende analyse voor meerdere gelijktijdig geselecteerde gebieden (Benchmark).
- [x] **Multi-Select UX:** Shift+Click op de kaart selecteert meerdere gebieden (Bug #11).
- [x] **State Management:** Backend en Frontend kunnen arrays van gebied_ids aan.
- [x] **Benchmark Vergelijker (Sjabloon C):**
    - [x] 3 Modi: Gebieden, Gemeente, Fryslân.
    - [x] Berekent delta's en impact per indicator.
    - [x] AI narrative via Ollama (Benchmark-specifiek).
- [x] **Frontend:** `BenchmarkPage.tsx` met live search en PDF export.
- [x] **Rapport Type Picker:** Modal in `app.js` kiest tussen Dossier en Benchmark.

---

## ✅ Sprint 8: AI & RAG "Smart" Kompas (Voltooid 15-03-2026)

**Context:** Intelligent, doorzoekbaar Kompas met wiskundig anker.
- [x] **Vector Database:** `pgvector` en text-embeddings geïmplementeerd.
- [x] **Semantische Zoekbalk:** 100% data coverage (280 indicatoren) in zoekfunctie.
- [x] **Contextuele Navigatie (Dag 39):** Auto-zoom naar Thema bij zoekselectie.
- [x] **AI-Rapportages:** Sjabloon A (Executive Summary) en C (Benchmark) live.
- [x] **Ollama Integratie:** Robuuste LLM-service met JSON output.

---

## 🔜 Sprint 9: Aggregatielagen + AI Ontologie Validatie (16-03-2026)

**Context:** Twee parallelle tracks: *(A)* Data-verbreding via aggregatieniveaus, *(B)* AI-kwaliteitsfundament via menselijke validatie van ontologieën.  
**Versiedoel:** v2.0.0  
**Priority:** 🔴 HIGH

---

### Track A — Aggregatielagen (PC6, PC4, Woonplaats)

**Doel:** Extra geografische resoluties boven en onder de huidige "Buurten"/"Wijken".

#### Fase 1: Database & ETL
- [ ] **Gebiedstypen toevoegen:** PC6, PC4 en Woonplaatsniveaus als `gebiedstypes` opnemen.
- [ ] **Import CBS Gebiedsindeling 2024 (NIEUW):**
    - [ ] Import `provincies.gpkg` naar nieuwe tabel/niveau.
    - [x] Import `CBS_BUURTEN2024.gpkg` (Focus op Friesland, Groningen, Drenthe voltooid op Dag 41).
    - [ ] Bereken een 100 meter buffer rondom de provinciegrenzen en selecteer buurten die hierbinnen vallen.
    - [ ] Voeg `provincie_naam` toe aan de buurten op basis van deze ruimtelijke join.
    - [x] Mappen van oude buurtcodes naar nieuwe 2024 codes voor Smallingerland (Voltooid op Dag 41).
- [ ] **Import scripts:** `import_pc4_gebieden.py` en `import_woonplaatsen.py` schrijven.
- [x] **Data Gaten Fix (ETL Restpunten):**
    - [x] BAG-indicatoren (Bouwjaar, Woonoppervlakte) importeren voor Smallingerland/De Fryske Marren.
    - [x] EP-Online indicatoren (Energielabels) importeren voor Smallingerland/De Fryske Marren.
    - [x] RIVM 50150NED buurt-data Smallingerland her-importeren na 2024 indeling fix (Voltooid op Dag 41).
- [ ] **ETL Roll-up:** `aggregate_buurt_to_pc4.py` — ruimtelijke joins (ST_Intersects/Contains) voor alle bestaande indicatoren.
- [ ] **Hiërarchische koppeling:** `parent_id` (bijv. PC4 → Gemeente) correct vastleggen.

#### Fase 2: Frontend
- [ ] **Aggregatieniveau Dropdown:** Keuze Buurt / Wijk / PC4 / PC6 / Woonplaats in kaartpaneel.
- [ ] **API:** Backend filtert gebieden op `gebiedstype` via query-param `aggregatie_niveau=PC4`.
- [ ] **Kompas Compatibiliteit:** Verificeer dat Kompas-queries werken op PC4 en Woonplaatsniveau.

---

### Track B — AI Ontologie Validatie (Admin Panel Sub-Track) ✅ Dag 40 (16-03-2026)

**Doel:** Fundament leggen voor betrouwbare RAG — zorg dat elke indicator een door de mens gevalideerde ontologische beschrijving heeft voordat die in de AI-pipeline wordt gebruikt.

> **Waarom nu?** De vector-embeddings zijn zo sterk als de beschrijvingen erachter. Een AI-gegenereerde omschrijving die foutief is, geeft foute zoekresultaten én foute RAG-antwoorden.

#### Fase 1: Database Schema ✅
- [x] **Kolommen toegevoegd aan `indicatoren` tabel** via `schema_v11_ontologie_validatie.sql`:
    ```sql
    ALTER TABLE indicatoren ADD COLUMN beschrijving_ai TEXT;
    ALTER TABLE indicatoren ADD COLUMN gevalideerd_door UUID REFERENCES users(id);
    ALTER TABLE indicatoren ADD COLUMN gevalideerd_op TIMESTAMPTZ;
    ALTER TABLE indicatoren ADD COLUMN embedding_versie TEXT;
    ```
- [x] **View `v_ontologie_validatiestatus`** aangemaakt voor Dashboard widget.
- [x] **Datamigatie:** bestaande `ontologische_beschrijving` gekopieerd naar `beschrijving_ai`.

#### Fase 2: Backend API ✅
- [x] **`PATCH /api/admin/indicatoren/{uuid}/valideer`** — ontvangt `{ ontologische_beschrijving, ontologie_status }`, slaat audit-velden op.
- [x] **`GET /api/admin/ontologie/status`** — Dashboard widget endpoint (statussen + percentage gereed).
- [x] **Filter `?ontologie_status=`** toegevoegd aan `GET /api/admin/indicatoren`.
- [x] **Nieuwe response-velden** in GET /indicatoren en GET /indicatoren/{uuid}.
- [ ] **Logica aanpassen:** AI Search prefereert `ontologische_beschrijving` uit `goedgekeurd_mens`-status; fallback op `beschrijving_ai`. **(NEXT SESSION)**

#### Fase 3: Admin Panel UI ✅
- [x] **Indicator Detail View — Validatie Tab:**
    - Zij-aan-zij: AI-beschrijving (read-only) + bewerkbaar tekstveld (rechts).
    - Status badge in lijst: `🤖 Draft` / `⏳ AI` / `✅ Goedgekeurd`.
    - Knoppen: `Goedkeuren`, `Reset naar AI`.
- [x] **Dashboard Widget:** Voortgangsbalk + statusbreakdown per categorie.
- [x] **Build & Deploy:** `npm run build` + deployed naar `static/admin-panel/`.
- [ ] **Bulk Actie:** Meerdere indicatoren tegelijk goedkeuren — Sprint 10+.

#### Fase 4: RAG Kwaliteitsbewaking
- [ ] **Feedback Loop UI in chat-interface (prototype):**
    - Duim omhoog / omlaag per chatresponse.
    - Negatieve feedback linkt terug naar de indicator-ontologie in de beheeromgeving.
- [ ] **Documentatie:** `docs/6-ai-parallel-track/ai-integratie/ontologie_validatie_protocol.md` opstellen (wie valideert wat, wanneer telt iets als 'goedgekeurd').
- [ ] **⚠️ AI Output Kwaliteitscheck (Bevinding Dag 40):**
    - **Probleem 1 — Taal:** Sommige `beschrijving_ai` velden zijn (deels) in het Engels. System prompt wordt niet strikt gevolgd.
    - **Probleem 2 — Denk-artefacten:** Reasoning-modellen (bijv. DeepSeek/Qwen) lekken `<think>` blokken naar de output.
    - **Actie A:** Systeemprompt aanscherpen in `scripts/ai/genereer_ontologie.py`: expliciete instructie `"Schrijf ALTIJD uitsluitend in het Nederlands. Geen denkstappen. Alleen eindtekst."`
    - **Actie B:** Post-processing filter in `genereer_ontologie.py` om `<think>...</think>` en Engelstalige blokken te strippen vóór opslaan.
    - **Zie:** `BRAINDUMP.md` → sectie 'AI Ontologie Kwaliteitscheck'

---

**Sprint 9 Track B Deliverables (Dag 40):**
- ✅ `schema_v11_ontologie_validatie.sql` live in productie DB
- ✅ Admin Panel: Ontologie Validatie Tab live  
- ✅ Dashboard: Voortgangsbalk validatiestatus  
- 🔲 AI Search prefereert gevalideerde beschrijvingen *(volgende sessie)*

**Priority:** 🔴 HIGH

---

## ⏳ Sprint 10: Data Upload & ETL Beheer-UI (Fase 3: Data Integrity)

**Context:** Visuele Data-Management applicatie binnenin het Beheerscherm.
- [ ] **Upload API Endpoints:** Veilige `POST /api/upload/csv` of `/geojson`.
- [ ] **Async Task Queue:** Celery / RQ setup met Redis incl job-status tracking.
- [ ] **Validation Pipeline:** Pydantic file schemas, foreign key checks, file-limits.
- [ ] **Upload Interface (React):** Drag-drop wizard met mapping functionaliteit en live-progressie.

**Priority:** 🟢 LOW (Zware backend data management laag, geparkeerd voor later)

---

## ⏳ Sprint 11: Observability & Compliance (Fase 4)

**Context:** Systeem monitoring en compliance audits voor Data Governance.
- [ ] **Centralized Logging:** Logging infrastructuur (Structured JSON format).
- [ ] **Audit Trail:** Database triggers voor `audit_log` tabel op acties (UPDATE, DELETE).
- [ ] **Performance Monitoring:** Query execution times en slow alerts detectie.

**Priority:** 🟡 MEDIUM

---

## ⏳ Sprint 12: Extra Datasets (Klimaat)

**Context:** Klimaatadaptatiemodellen en themathische verbreding.
- [ ] **Data Scraping/Download:** Hittestress, Overstromingsrisico's, Groen-dekking, etc.
- [ ] **Kompas Taxonomie:** Integratie onder pijler Klimaat/Fysieke Omgeving.

**Priority:** 🟢 LOW

---

## ⏳ Sprint 13: Advanced UX & Map Features (Fase 1/7)

**Context:** Visuele features en QoL updates.
- [ ] **Time Slider:** Historische play/pauze bediening om data af te spelen (2020-2024).
- [ ] **Locatie Filters:** Draw polygon/radius filter tools integreren op in Deck.gl.
- [ ] **Icoon Beheer:** Admin-gedeelte voor dynamische SVG map-/kompasiconen.

**Priority:** � LOW

---

## 🧠 Parallel Track: AI & RAG Kompas (R&D)

**Context:** Direct en intuïtief zoeken via AI/Semantiek op het D-OmniTwin Kompas.
**Status:** Planning / Opstarten (Parallel aan Sprint 9)
**Documentatie:** `docs/7-projectmanagement/logs/plan_aanpak_ai_parallel_track.md`

### Fase 1: Wiskundig Fundament & Data Engineering
- [x] **Python Normalisatie Pipeline (Dag 33):** ✅ COMPLEET
    - [x] Script `normalisation.py` borgt `[0.01, 1.00]` bereik voor hiërarchische stabiliteit.
- [/] **Objectieve Weging (Entropy/CRITIC):**
    - [x] Database-structuur (`weging`-kolom) gereed en in gebruik in views.
    - [x] **Percentile Binning (12.5% bins)** geïmplementeerd als eerste objectieve scoring-maatstaf.
    - [ ] Automatisering van Entropy/CRITIC berekening via Python (R&D).
- [x] **Aggregatie Pipelines:** ✅ COMPLEET (BAG/CBS pipelines stabiel).

### Fase 2: Semantische Zoeklaag (Vector Database)
- [x] **Database & Model Setup:** ✅ COMPLEET
    - [x] Extensie `pgvector` actief.
    - [x] Lokaal SentenceTransformer-model via Ollama/Python.
    - [x] **100% Data Coverage (Dag 39):** Alle 280 indicatoren voorzien van vector-embeddings.
- [x] **Search API & Frontend Integratie:** ✅ COMPLEET
    - [x] FastAPI route `/api/ai/kompas/search` (Intent Vertaler).
    - [x] **Contextuele Navigatie (Dag 39):** Auto-zoom naar Thema-niveau bij zoekselectie.

### Fase 3: De Stem (RAG LLM & Ollama)
- [x] **RAG Data Retrieval (Context Injectie):** ✅ PROTOTYPE
    - [x] Executive Summary (Dag 34) & Benchmark Vergelijker (Dag 35) functioneel.
- [x] **AI-Pipeline (Backend):** ✅ COMPLEET
    - [x] Ollama integratie-class met deterministische JSON output.
- [ ] **Frontend D-Omni Assistant (UI):** 📅 Eerstvolgende stap
    - [ ] Chat / Intent-interface bouwen.
    - [ ] **Stip op de horizon:** Dynamische "Actie Knoppen" o.b.v. chat-vragen (bijv. "Hoe groen is mijn buurt?" → knop stelt relevante indicatoren direct in op de kaart).
- [ ] **Frontend D-Omni Assistant (UI):**
    - [ ] Chat / Intent-interface bouwen.
    - [ ] Beveiligen tegen hallucinaties: De output van de LLM stuurt niet alleen een verhaaltje, maar vooral een Commando-JSON terug die de kaart / het kompas van state verandert.

---

## 📊 Backlog: Advanced Features (Low Priority - Future)

### 🤖 Sprint 8 & 8B: AI Rapportage Module (3-Lagen Architectuur) - **VOLTOOID 21-02-2026** ✅
- [x] **Fase 1: Pre-Processing (Rekenlaag)**
    - [x] Delta-berekeningen implementeren (Z-scores).
    - [x] Filtering logica voor top 10% afwijkingen schrijven.
    - [x] `ReportDataService` API endpoint (`/api/report/data/{gebied_id}`) bouwen.
- [x] **Fase 2: Narrative Engine (LLM)**
    - [x] Ollama lokale node setup (Qwen3:30b configuratie en 600s timeout geimplementeerd).
    - [x] System prompt beheer (CRUD via `system_prompts` DB tabel + Admin API).
    - [x] Connectie leggen tussen FastAPI en Ollama REST API (`/api/report/narrative/{gebied_id}`).
    - [x] 🐛 *BUGFIX #12: Ollama retourneert momenteel ruwe tekst ipv stricte JSON. Fix dit in `llm_service.py` via native JSON-mode of robuuste parsing regex.*
- [x] **Fase 3: React Frontend (Visualisatie)**
    - [x] API integratie & UI Layout opbouwen in nieuw `ReportPage.tsx` component.
    - [x] Route en navigatie toevoegen aan React Admin-paneel.
    - [x] "Genereer Rapport" activatie-knop verbinden in hoofdapplicatie `app.js` met dynamische doorverwijzing.
    - [x] Mapbox Static API of WebGL kopie integratie voor printbare `MapSnapshot`.
    - [x] Z-score kleuring (stoplichtkleuren: rood-oranje-groen) toepassen op datapunten, conform `score_type` regels (+/+, +/-, -/-, -/+).
    - [x] `@media print` CSS perfectioneren voor PDF export (A3 landscape).
    - [x] D3 Sunburst / Kompas SVG export fixen en inbouwen (haarscherp in print via headless SVG rendering in `app.js`).
    - [x] Foutafhandeling voor CORS blockades op canvastype via error forwarding postMessages.

- [x] **Fase 4: Admin Beheer (Nieuwe Functionaliteiten Reportage)**
    - [x] **Systeemprompts beheer:** Uitbreiden Admin Panel UI om systeemprompts (LLM) te beheren en te koppelen aan specifieke thema's of profielen.
    - [ ] **Rapport Templates:** Functionaliteit inbouwen in admin paneel om rapport-templates of profielen aan te maken en te beheren.

### 📊 Sprint 8C: Rapportage Sjablonen — Benchmark & Executive (Dag 34 - 28-02-2026) — **IN PROGRESS**

> **Architectuurdocument:** `docs/6-ai-parallel-track/report&ai/d_omni_twin_rapportagemodule_architectuur.md`

- [x] **Sjabloon C: Benchmark Vergelijker (Backend)**
    - [x] `generate_benchmark_payload()` in `report_service.py` (3 modi: gebieden, gemeente, fryslan)
    - [x] `GET /api/report/benchmark` endpoint met query params (gebied_a, mode, gebieden_b, referentie_gemeente)
    - [x] `generate_benchmark_narrative()` in `llm_service.py` met dedicated system prompt
    - [x] `GET /api/report/benchmark/narrative` endpoint
    - [x] Backend geverifieerd: Fryslân (46 ind.) en Gemeente (46 ind.) modi retourneren correcte delta's

- [x] **Sjabloon C: Benchmark Vergelijker (Frontend)**
    - [x] TypeScript types: `BenchmarkMode`, `BenchmarkIndicator`, `BenchmarkPayload`, `BenchmarkNarrativeResponse`
    - [x] API service uitgebreid: `reportAPI.getBenchmark()`, `reportAPI.getBenchmarkNarrative()`
    - [x] Publieke API client `gebiedenAPI` voor gebieden/gemeenten zoeken
    - [x] Nieuwe pagina `BenchmarkPage.tsx` met typeahead GebiedSelector, 3-modus tabs, delta tabel, AI narrative
    - [x] Route `/rapport/benchmark` + sidebar navigatie item (Scale icoon)

- [x] **Sjabloon A: Executive Summary (Backend)**
    - [x] `generate_executive_payload()` in `report_service.py` (hergebruikt bestaande Z-score logica)
    - [x] `GET /api/report/executive/{gebied_id}` endpoint

- [ ] **Nog te doen (volgende sessie):**
    - [ ] 👤 Handmatige UI test BenchmarkPage in browser
    - [ ] Sjabloon A: Executive Summary frontend (`ExecutivePage.tsx`)
    - [ ] **Sjabloon E: Multi-Gebiedsdossier** — Algemeen dossier van meerdere buurten (naast elkaar, zonder benchmark) 🔴 HIGH PRIORITY
    - [ ] AI narrative testen (vereist actieve Ollama)
    - [ ] n-op-n benchmark (backlog)
    - [ ] Sjabloon D: Participatie Rapport (backlog)

### Vergelijkingsmodus
- [ ] Split-screen layout (2 kompassen naast elkaar)
- [ ] Synchrone map interaction (linked views)

### Time Slider
- [ ] Historische data slider (2020-2024)
- [ ] Animation: "play" through jaren

### Advanced Selection Tools
- [ ] Draw polygon on map → stats
- [ ] Radius selection (within X km)

---

## 📈 Progress Tracking

**Completion Status:**
- ✅ Fase 1-4: Foundation & MVP (100%)
- ✅ Sprint 4A-D: Kompas & Polish (100%)
- ✅ Sprint 5: Security Foundation & Data Expansion (100%)
- ✅ Sprint 6: Auth & Beheerscherm (100%)
- ✅ Sprint 7: Multi-Gebied Analyse (100%)
- ✅ Sprint 8: AI & RAG "Smart" Kompas (100%)
- 🔄 Sprint 9: Aggregatielagen & AI Validatie (50% - Track B voltooid)

**Risk Status:**
- **Current:** 🔴 HIGH RISK (secrets in git, no auth, CORS open)
- **After Punt 0:** 🟡 MEDIUM RISK (secrets safe, CORS locked, headers active)
- **After Fase 1-2:** 🟢 LOW RISK (TLS + Auth active)
- **Production Ready:** After Fase 4 (Audit logging + monitoring)

---

**Next Action:** Start [Security Quick Wins Guide](/docs/7-projectmanagement/logs/SECURITY_QUICK_WINS.md) (Punt 0)  
**Documentation:** Zie [ROADMAP.md](/ROADMAP.md) voor volledige feature planning  
**Architecture:** Zie [ARCHITECTURE_TECHNICAL_OPERATION.md](/ARCHITECTURE_TECHNICAL_OPERATION.md) voor technische diepgang 4 (Kompas) - Backend & Frontend Core Complete ✅

---

## ✅ Fase 1: Fundament & Configuratie (Voltooid)
- [x] Python Virtual Environment opzetten
- [x] `config.ini` aanmaken voor database credentials
- [x] PostgreSQL + PostGIS installatie
- [x] Database en user aanmaken
- [x] FastAPI basis project structuur
- [x] SQLAlchemy setup voor database connectie
- [x] Project documentatie (README, BUILD, TODO)

## ✅ Fase 2: Data Engine (D-Omni Scan) - Gebiedsmonitor
- [x] **Gebiedsmonitor Integratie (Dag 2)**
- [x] **Validatie & Visualisatie (Dag 2)**
- [x] **API Endpoints (DAG 3 - VOLTOOID!)**

## ✅ Fase 3A: Frontend MVP (Dag 3 - VOLTOOID 17-01-2026)
- [x] **Frontend Prototype:**
    - [x] HTML template met deck.gl container
    - [x] Static files setup (FastAPI templates + static mounting)
    - [x] Modern CSS styling (glassmorphism, gradients, animations)
    - [x] deck.gl 3D kaart met GeoJsonLayer

## ✅ Fase 3B Sprint 1: Core UX Improvements (VOLTOOID - 18-01-2026)
- [x] **UI Redesign - Fullscreen Kaart**
- [x] **Legenda Systeem**
- [x] **Mapbox Basemap Integration**
- [x] **Export Functionaliteit**

## ✅ Sprint 4: Kompas Visualisatie (Dag 6-10) - **VOLTOOID 24-01-2026** ⚡
- [x] **Database Schema v4** (upgrade van v3)
- [x] **Backend API** (Dag 7 - 22-01-2026) ✅
- [x] **Frontend D3.js** (Dag 8-9 - 23-01-2026) ✅

## Sprint 4B: Visual Polish & Scoring (Dag 11 & 12)
- [x] **Scoring Logica:**
    - [x] Backend integratie van `KompasScoringService`.
    - [x] Percentiel methodiek (8-bins) implementatie.
    - [x] Consistentie tussen kaart en kompas kleuren.
- [ ] **UI/UX Polish:**
    - [x] "Classic Premium" Look restoration (Gradient header, 40% panel opacity).
    - [x] Status indicator ("Verbonden") hersteld.
    - [x] Legenda en export functionaliteit gefixt.
    - [x] **Iconen:** Vervangen oude icons met Lucide (o.a. Data Export).
    - [x] **Icon Styling:** Kleuring gefixt (o.a. Lucide icons consistent).
    - [x] **Light Mode:** Kaart kleuring CBS buurten naar grijswaarden.
- [x] **Bugfixes:**
    - [x] 3D Toggle color loss (workaround functional).
    - [x] Missing attributes in dropdowns logic.
    - [x] Missing attributes in dropdowns logic.

## ✅ Sprint 4C: Kompas & UI Refinement (Voltooid 31-01-2026)
- [x] **Kompas Window:**
    - [x] Onderzoek/Redesign van grafiek overlay (Center interaction).
    - [x] Tekst in het midden van het kompas (naam) aanpassen/verbeteren.
- [x] **Indicator Informatie:**
    - [x] Toevoegen van beschrijvingen/toelichting per indicator (Backend placeholder + UI).
- [x] **Zoom & Scale:**
    - [x] Inverse text scaling.
    - [x] Geometry auto-scaling.

## 🎨 Sprint 4D: Visual Polish & Bugs (01-02-2026)
- [x] **Layout Optimalisatie:**
    - [x] Hoogte van header en footer verkleinen (meer ruimte voor kaart).
    - [x] Compactere weergave van header tekst en logo.
- [x] **Databron Verrijking:**
    - [x] Database check & update voor indicator metadata (definities).
- [ ] **Bugfixes:**
    - [x] Kompas Zoom/Click Glitch (BUGFIX Log 01-02-2026).

## ✅ Sprint 5C: Data Expansion & Bugfixes (Dag 18 - 08-02-2026)
- [x] **RIVM Data Integratie (Fase 2):**
    - [x] OData endpoint `dataderden.cbs.nl` geïntegreerd.
    - [x] Dataset `50150NED` (Gezondheidsmonitor) geïmporteerd.
    - [x] ETL scripts robuuster gemaakt (pagination/filtering).
- [x] **Bugfixes:**
    - [x] Map Interaction Bug: pointer-events fix in CSS.
- [x] **Metadata Verrijking:**
    - [x] Script `enrich_rivm_metadata.py` gemaakt voor 50150NED definities.

## 🔜 Fase 5 (Dag 12+): Data & Beheer (Sprint 5)
- [ ] **Beheerscherm-kompas (🔴 HIGH PRIORITY):**
    - [ ] Concept uitwerken voor beheer van wegingen en relaties.
    - [ ] Frontend interface.
- [ ] **Data Upload**
    - [ ] GeoJSON/CSV Upload UI.
    - [ ] Backend upload handler.
- [ ] **Deployment Prep**
    - [ ] `requirements.txt` freeze.
    - [ ] Dockerfile opstellen.
    - [ ] Environment variable clean-up.

## 🏗️ Fase 6: Architectuur & Refactor v1.1 (Dag 12 - Lopende)
- [x] **Technische Inventarisatie & Backbone:**
    - [x] Analyse Huidige Architectuur (Frontend/Backend/Data).
    - [x] `ARCHITECTURE_TECHNICAL_OPERATION.md` opgesteld.
    - [x] Risico analyse (Spaghetti Watch).
- [x] **Phase 1: Frontend Decoupling (Parallel Change):**
    - [x] `EventBus` implementatie.
    - [x] Migratie Kompas interacties.
    - [x] Migratie Map interacties.
- [x] **Phase 2: Backend Simplification:**
    - [x] SQL Views aanmaken voor complex data logic.
    - [x] Service layer opschonen (`get_kaart_data_v2`).


---

**Zie ook:**
- `BRAINDUMP.md`
- `feature_roadmap.md`
- `BUILD.md`
- `README.md`
\n- [ ] **Admin functionaliteit toevoegen om losse indicatoren toe te wijzen in the Hiërarchie view (Drag and Drop in component / API endpoint `PUT /api/admin/hierarchie/map`).**

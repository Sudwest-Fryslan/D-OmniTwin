# Sprint 22 Track C: Data Lineage & Bronvermelding — Technische Specificatie

> **Sprint:** 22 (Afronding Track C)  
> **Status:** 📝 Definitief Plan  
> **Datum:** 2026-08-21  
> **Eigenaar:** Data Engineering / Backend  
> **Gerelateerde documenten:**  
> - [`docs/3-data-engineering/etl_dataspace_gap_analyse.md`](./etl_dataspace_gap_analyse.md)  
> - [`docs/STATE.md`](../STATE.md)  
> - [`TODO.md`](../../TODO.md)  

---

## 1. Context & Doelstelling

In D-OmniTwin is data betrouwbaarheid en verifieerbaarheid cruciaal voor beleidsmakers en analisten. Waar indicatoren voorheen enkel een generiek tekstlabel hadden (zoals `"CBS"` of `"RIVM"`), implementeert **Track C** een gestructureerde **Data Lineage & Bronvermeldingsarchitectuur**.

### Kernvragen die beantwoord worden:
1. **Herkomst:** Uit welke specifieke tabel, dataset of API-endpoint is de indicator afkomstig?
2. **Actualiteit:** Wat is de peildatum van de meting en wanneer is deze voor het laatst in D-OmniTwin gesynchroniseerd?
3. **Verificatie:** Is er bij de bronaanbieder (bijv. CBS OData) een nieuwere datasetversie beschikbaar?
4. **Traceerbaarheid:** Is de bronvermelding direct inzichtelijk in het detailpaneel, bij data-exports en in het Multi-Gebiedsdossier?

---

## 2. Architectuur & Datamodel

### 2.1 Metadata Velden in `indicatoren`

De tabel `indicatoren` bevat reeds de vereiste structuur, die in deze track consistent gevuld en gestandaardiseerd wordt:

```sql
-- Reeds aanwezige lineage kolommen in public.indicatoren:
-- bron                    VARCHAR(255)  -- Formele weergavenaam (bijv. "Centraal Bureau voor de Statistiek")
-- bron_systeem_api        VARCHAR(255)  -- Taxonomie: 'CBS_ODATA', 'RIVM_STATLINE', 'BAG_API', 'PDOK_WFS', 'PROVINCIE_GEO', 'LOKAAL'
-- bron_tabel_referentie   VARCHAR(255)  -- Dataset code of tabel (bijv. '83765NED', 'kwb-2024')
-- laatste_update_bron     TIMESTAMP     -- 'Modified' timestamp van de bron zelf
-- laatste_check_datum     TIMESTAMP     -- Tijdstip waarop D-OmniTwin de bron heeft gecontroleerd
-- begingeldigheid         TIMESTAMP     -- Eerste peiljaar/datum
-- eindgeldigheid          TIMESTAMP     -- Laatste peiljaar/datum
```

### 2.2 Bron-Taxonomie & URL Resolutie

Om uniforme weergave en klikbare bronverwijzingen te garanderen, hanteert D-OmniTwin een vaste taxonomie:

| `bron_systeem_api` | Voorbeeld `bron_tabel_referentie` | Resolutie / Externe URL |
|---|---|---|
| `CBS_ODATA` | `83765NED` (Kerncijfers Wijken en Buurten) | `https://opendata.cbs.nl/#/CBS/nl/dataset/{ref}/table` |
| `RIVM_STATLINE` | `vtv_gezondheid` | `https://www.volksgezondheidenzorg.info/` |
| `BAG_API` | `bag_panden_fryslan` | `https://bag.basisregistraties.overheid.nl/` |
| `PDOK_WFS` | `natura2000` / `bodemdaling` | `https://www.pdok.nl/` |
| `OV_API` | `ov_haltes_fryslan` | OpenOV / NDOV Loket |
| `GEMEENTE_UPLOAD`| `gemeente_data_{jaar}` | Lokaal beheerdersbestand |

---

## 3. Uitvoeringsstappen

### Stap 1: Metadata Audit & Verrijkingsscript
- Ontwikkelen van `scripts/enrich_indicator_lineage.py`.
- Het script doorloopt alle 235 actieve indicatoren in `omnitwin_db`:
  - Kwartiert CBS kerncijfers aan tabel `83765NED` / `85769NED`.
  - Koppelt RIVM indicatoren aan de Gezondheidsmonitor definities.
  - Koppelt BAG indicatoren aan `BAG_API`.
  - Koppelt OV indicatoren aan `OV_API`.
- Voert direct een initiële controle uit en zet `laatste_check_datum = CURRENT_TIMESTAMP`.

### Stap 2: Frontend UI Verrijking (Detailpaneel & Kaart)
- **Detailpaneel (`templates/index.html` + `static/js/kompas.js`):**
  - Bronvermelding uitbreiden van een statische string naar een interactieve lineage badge.
  - Klikbaar extern link-icoon naar de officiële dataset catalogus (bijv. CBS OData portaal).
  - Tooltip toont:
    - *Brontabel:* `83765NED`
    - *Peildatum:* `2023 / 2024`
    - *Laatste sync:* `21-08-2026`
    - *Type:* `Officiële Basisregistratie / OData API`
- **Rapportage & Multi-Gebiedsdossier (`routers/report.py`):**
  - Genereren van een automatische bronnenlijst met peildata en metadata onderaan het dossier (colofon).

### Stap 3: DataControle Service & Admin Inzage
- `services/data_controle_service.py` uitbreiden:
  - Implementeren van periodieke update-checks voor CBS OData (`/TableInfos?$select=Modified`).
  - Toevoegen van check voor RIVM endpoints.
- Admin Panel (`admin-panel/src/pages/DataControle.tsx` of Beheeroverzicht):
  - Tonen van indicator actualiteitsstatus:
    - 🟢 **Actueel** (D-OmniTwin is synchroon met bron)
    - 🟡 **Nieuwere data beschikbaar bij bron**
    - ⚪ **Statische / Lokale dataset**

---

## 4. Docker & Runtime Aandachtspunten

- **Docker Integratie:**
  - De applicatie draait in `docker-compose` met live volume mount (`.:/app`).
  - Backend code wijzigingen herladen automatisch via uvicorn hot-reload.
  - Database queries en migraties/scripts verbinden via port `5433` (lokaal) of via `docker compose exec backend python scripts/...`.
- **Admin Panel:**
  - Wijzigingen in `admin-panel/src` worden gecompileerd via `/build-admin-panel` naar `static/admin-panel`.

---

## 5. Verificatie & Acceptatiecriteria

- [ ] **AC 1 (Database):** Minimaal 90% van de actieve indicatoren heeft een geldige `bron_systeem_api` en `bron_tabel_referentie`.
- [ ] **AC 2 (UI):** Selectie van een CBS-indicator op de kaart toont in het detailpaneel een werkende externe link naar de CBS OpenData portal.
- [ ] **AC 3 (Rapportage):** Het gegenereerde Multi-Gebiedsdossier bevat een gestructureerde bron- en peildatabijlage.
- [ ] **AC 4 (Admin):** Endpoint `/api/admin/data-controle/run` voert live checks uit tegen CBS OData en retourneert update status.

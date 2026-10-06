# D-OmniTwin — Overleg Leidraad Externen
> **Datum:** 24 augustus 2026
> **Doel:** Demo & inhoudelijke briefing voor externe stakeholders (developer + subsidieproject-deelnemers)
> **Context:** Innovatieproject D-OmniTwin — gefinancierd via Innovatiebudget Digitale Overheid, Ministerie BZK
> **Opgesteld door:** Project Manager ⟡ Samenwerking & Adoptie Assistent ⟡ Technisch-Communicatie Assistent

---

## 1. 🧭 Wie zit er aan tafel?

| Deelnemer | Rol | Kernvraag |
|-----------|-----|-----------|
| **Ministerie BZK** | Subsidiegever / Innovatiebudget Digitale Overheid | Wat levert dit op? Is het schaalbaar? |
| **Externe Developer(s)** | Technisch partner / innovatieteam | Hoe werkt het? Kan ik ermee werken of op bouwen? |
| **Overige externen** | Projectpartners (pilot / consortium) | Waar staan we? Wat is de volgende stap voor ons? |

---

## 2. ⚡ De 30-seconden kernboodschap

> *"D-OmniTwin is een **open, federatieve interactielaag** waarmee gemeenten en regio's integraal inzicht krijgen in complexe leefomgevingsvraagstukken — van energiearmoede tot hittestress en sociale cohesie. In plaats van data op te sluiten in een nieuw centraal datasilo, **blijft data bij de bron**. We ontsluiten het via open dataspace-standaarden (iSHARE / Federatief Datastelsel). Gefinancierd als open source innovatieproject (EUPL 1.2) voor de publieke sector in Nederland."*

---

## 3. 🤝 Consortium & Partners

| Partner | Rol |
|---------|-----|
| **Gemeente Súdwest-Fryslân** | Regievoerende organisatie — CDO Taeke van der Laan |
| **Gemeente Leeuwarden** | Samenwerkingspartner — praktijkcontext |
| **Gemeente Tytsjerksteradiel** | Samenwerkingspartner — praktijkcontext |
| **DataFryslân** | Dataspace-infrastructuur (FRLDS / iSHARE-registratie) |
| **TU Delft** | Beoogd kennispartner — validatie & onderzoek |
| **NHL-Stenden** | Beoogd kennispartner — toegepast onderzoek |

**Looptijd innovatieproject:** 1 september 2026 – 31 augustus 2027
**Budget:** €300.000 totaal (€180.000 subsidie BZK / €120.000 cofinanciering)

---

## 4. 🖥️ Wat staat er nu LIVE? (Demo-flow — 5 minuten)

### Stap 1 — Het D-Omni Kompas
- **244 gevalideerde indicatoren** verdeeld over 12 thema's en 4 leefwerelddomeinen.
- Interactieve sunburst-visualisatie op buurt-, wijk- en woonplaatsniveau.
- Dekking: **942 Friese buurten** — volledig afgedekt met CBS-kerncijfers en RIVM-data.

### Stap 2 — Data Lineage & Transparante Bronvermelding
- Klik op *iedere* indicator → direct zichtbaar: **peildatum**, **officiële brontabelcode** (bijv. CBS OData `85984NED`) en een klikbare link naar de open data catalogus.
- 100% van de 244 actieve indicatoren is voorzien van transparante herkomst — *aantoonbare datakwaliteit en verantwoording* richting ministerie en partners.

### Stap 3 — Hybride Kaartlagen (OGC Standaarden)
- Externe kaartlagen rechtstreeks via PDOK (Natura 2000, Bodemdaling, Monumenten, BAG Woonplaatsen).
- Lokale geodata-uploads (GeoPackage / GeoJSON) via de Admin interface.
- Rendering via **MapLibre GL JS + Deck.gl** — geen vendor lock-in aan commerciële platforms.

### Stap 4 — Multi-Gebiedsdossier & Benchmarking
- Kernen direct naast elkaar vergelijken (voorbeeld: IJsselmeerkust — Makkum, Workum, Koudum).
- Geautomatiseerde analyse met PDF/HTML-export inclusief automatische **bronverantwoording colofon**.

---

## 5. 🎯 De vier gevalideerde use cases (subsidiedoelstelling)

| # | Use Case | Status | Relevante data |
|---|----------|--------|----------------|
| 1 | **Energietransitie & Energiearmoede** | 🟢 Live | CBS energielabels (A+++++ t/m G), RIVM armoede-indicatoren |
| 2 | **Klimaatadaptatie (hittestress & bodemdaling)** | 🟢 Live | PDOK Bodemdaling WFS, RIVM klimaat-indicatoren |
| 3 | **Brede Welvaart** | 🟢 Live | CBS Brede Welvaart framework, RIVM gezondheidsmonitor |
| 4 | **Sociale Cohesie & Bereikbaarheid** | 🟢 Live | OV-haltes ETL (6.945 nodes → 961 buurten × 5 indicatoren) |

---

## 6. 🛠️ Voor de Developer — Tech Stack & Architectuur

```
  [ Gemeenten / Burgers / Beleidsmakers ]
                     │
                     ▼
       ┌─────────────────────────────┐
       │  Traefik Reverse Proxy      │  (Poort 80/443, SSL, CORS)
       └──────────┬──────────────────┘
                  │
     ┌────────────┴──────────────────────────────┐
     ▼                                           ▼
┌────────────────────────────┐    ┌──────────────────────────────┐
│      FastAPI Backend       │    │  PostgREST & pg_featureserv  │
│  (Python 3.11, Pydantic,   │    │  (OGC API Features + REST    │
│   BFF, Dossiers, AI-chat)  │    │   dataspace-compliant data)  │
└──────────────┬─────────────┘    └──────────────┬───────────────┘
               │                                 │
               └──────────────┬──────────────────┘
                              ▼
               ┌──────────────────────────────┐
               │  PostgreSQL 16 + PostGIS     │
               │  (Spatial Views, RLS-ready,  │
               │   Geoptimaliseerde GIS)      │
               └──────────────────────────────┘
```

**Frontend:**
- Vanilla JS met `window.EventBus` als event-driven communicatielaag tussen map en Kompas.
- **MapLibre GL JS + Deck.gl** voor vector tile rendering en 3D-visualisatie (geen Mapbox).
- **Admin Panel:** Standalone React 18 / TypeScript SPA via Vite, gebuild naar statische assets.

**APIs:**
- `FastAPI`: Domeinlogica, benchmark-statistieken, caching, PDF-generatie, AI-chat BFF.
- `PostgREST`: Directe REST endpoints over PostgreSQL — OData-compatibel, Dataspace-conform.
- `pg_featureserv`: OGC API Features voor geodata-ontsluiting.

**Dataspace-architectuur (richting):**
- Ontworpen als **dataspace-agnostische interactielaag**: connectie met FRLDS, FDS en andere dataspaces via iSHARE-autorisatie.
- Data blijft bij de bron; D-OmniTwin stelt gerichte queries aan de juiste node in het ecosysteem.

**Licentie:** EUPL 1.2 (code) | CC BY 4.0 (methodiek)
**Repository:** [github.com/Sudwest-Fryslan/D-OmniTwin](https://github.com/Sudwest-Fryslan/D-OmniTwin)

---

## 7. 🚀 Roadmap & Sprint Richting

### Nu in uitvoering: Sprint 23 — De Gebruikers Sprint

> **Relevantie voor het ministerie:** Sprint 23 legt het technische fundament voor het kunnen aansluiten van meerdere gemeenten als zelfstandige tenants — dit is de schaalbaarheid die de subsidiedoelstelling van meerdere pilotgemeenten vereist.

| Fase | Omschrijving | Status |
|------|-------------|--------|
| **A — Database Multi-Tenancy** | `organizations` tabel + `organization_id` FK op alle kerntabellen. PostgreSQL Row Level Security (RLS) als vanglaag per gemeente. | 📌 Gepland |
| **B — Keycloak Identity Broker** | Federatieve identiteit via Microsoft Entra ID (Single Sign-On vanuit de eigen gemeente). Realm `omnitwin` met 4-niveaus RBAC. | 📌 Gepland |
| **C — FastAPI BFF & PostgREST beveiliging** | Auth-endpoints (`/api/auth/login`, `/callback`, `/me`, `/logout`). PostgREST afsluiten via Traefik ForwardAuth. | 📌 Gepland |

### Daarna: Dataspace Integratie (Q3/Q4 2026)

- **FRLDS / FDS connector:** Eerste echte federatieve datafeed vanuit de Fryslân Data Space.
- **Open Source Decoupling (EUPL):** Formele publicatie als herbruikbare bouwsteen voor andere regio's.
- **Lokale LLM-integratie:** Privacy-vriendelijke AI-narratieven per gebruikersrol (beleidsadviseur, wijkcontactfunctionaris, inwoner).

---

## 8. 📋 Voor het ministerie — Kernvragen beantwoord

| Vraag | Antwoord |
|-------|----------|
| **Is het schaalbaar naar andere gemeenten?** | Ja. Sprint 23 legt het multi-tenant fundament; elke gemeente kan als afgeschermde tenant worden toegevoegd of een eigen containerinstantie draaien. |
| **Hoe zit het met data-soevereiniteit?** | Data blijft bij de bron (dataspace-architectuur). De applicatie haalt alleen de benodigde data op met actieve iSHARE-autorisatie — geen centrale datastapeling. |
| **Is het open source?** | Volledig. EUPL 1.2 (code) en CC BY 4.0 (methodiek). Publicatie via GitHub, herbruikbaar voor andere regio's en provincies zonder licentiekosten. |
| **Wat is de maatschappelijke waarde?** | Betere vroegsignalering in het sociaal domein, klimaatadaptatie op buurtniveau en effectievere inzet van middelen door integraal inzicht. Bijdraagt aan SDG 3 (gezondheid), SDG 11 (duurzame steden) en SDG 13 (klimaat). |
| **Wie gebruikt het?** | Beleidsmakers & strategen, wijkcontactfunctionarissen, en via de AI-interface ook inwoners zelf. |

---

## 9. ⚠️ Open punten & Eerlijk signalement

| Punt | Status |
|------|--------|
| **PostgREST is momenteel open** (beveiligingsrisico) | Wordt gesloten in Sprint 23 Fase C via Traefik ForwardAuth + RLS. |
| **E-mail alerts (logging)** | On hold — wacht op SMTP-server. Must-have voor gedeelde/productie-omgeving. |
| **iSHARE-registratie FRLDS** | Vroeg contact met DataFryslân vereist. Risico: registratieproces kost tijd. |
| **Data Upload UI (Admin Panel)** | In ontwikkeling — CBS handmatige uploads nog niet via UI afgerond. |

---

*Opgesteld op 2026-08-24 | Bron: `docs/STATE.md`, `ROADMAP.md` (nu `docs/archief/ROADMAP.md`), `docs/8-communicatie/communicatieplan_subsidie_2026.md`, `docs/1-visie-concept/innovatie/aanvraag_innovatiebudget_digitale_overheid_2026_d_omni_twin.md`*

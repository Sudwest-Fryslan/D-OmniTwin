# INDEX.md — D-OmniTwin Documentatie Router
> **Rol:** Navigatielaag voor documentatie | Router voor agents | Overzicht van alle kennisdomeinen
> **Beheer:** Updaten bij nieuwe mappen of structurele wijzigingen
> **Lees eerst:** [`CHANGELOG.md`](../CHANGELOG.md) (wat er per versie veranderd is) en de [issues](https://github.com/TLaan/D-OmniTwin/issues) (wat openstaat). `STATE.md` is een historische momentopname tot 0.1.0.

---

## 🧭 Gebruik (voor agents)
1. Start met `CHANGELOG.md` en de open issues om de actuele situatie te begrijpen
2. Gebruik dit INDEX.md om het relevante domein te selecteren
3. Beperk analyse tot de geïdentificeerde mappen — geen volledige scan

---

## 📂 Domeinen

| Domein | Map | Inhoud | Primaire skills |
|--------|-----|--------|-----------------|
| **Visie & Concept** | `/docs/1-visie-concept/` | Projectfilosofie, doelstellingen, gebruikersscenario's | project-manager, technisch-communicatie |
| **Architectuur** | `/docs/2-architectuur/` | Technische architectuur, API-design, component-diagram, **Dataspace integratie** | backend-db, data-architect-engineer, innovation-lab |
| **Data Engineering** | `/docs/3-data-engineering/` | ETL-pipelines, CBS/RIVM data, scores, indicatoren, Z-score-methodiek ([`zscore_methodiek.md`](./3-data-engineering/zscore_methodiek.md)), percentielklasse ([`percentielklasse_methodiek.md`](./3-data-engineering/percentielklasse_methodiek.md)), labels A–E ([`labels_methodiek.md`](./3-data-engineering/labels_methodiek.md)) | data-architect-engineer, data-gis |
| **UX & Design** | `/docs/4-ux-design/` | UI-patronen, "Classic Premium UI", design-system, thema per organisatie met NL Design System-tokens ([`9-beheer/thema-s.md`](./9-beheer/thema-s.md)), gebruikerservaringen (`gebruikerservaringen/`) | frontend-viz, web-carto-design |
| **SecOps & Compliance** | `/docs/5-secops/` | Security-beleid, privacy-quickscan, AI-compliance ([`analyse_eu_ai_act_d_omnitwin.md`](./5-secops/compliance/analyse_eu_ai_act_d_omnitwin.md)), toegangsbeheer | secops-identity, project-manager, backend-db |
| **AI Parallel Track** | `/docs/6-ai-parallel-track/` | LLM-integratie, ontologie, AI-chat, prompting | innovation-lab, technisch-communicatie |
| **Projectmanagement** | `/docs/7-projectmanagement/` | Sprints, voortgang, besluiten, archief | project-manager |
| **Communicatie** | `/docs/8-communicatie/` | Stakeholdercommunicatie, rapportages, presentaties | technisch-communicatie |
| **Beheer & Applicatie** | `/docs/9-beheer/` | Handleidingen, workflows en applicatiebeheer; eigen huisstijl ([`thema-s.md`](./9-beheer/thema-s.md)) | project-manager, backend-db |
| **Testcases & Scenario's** | [`/docs/testcases/`](./testcases/) | Functionele scenario's, E2E-toetsen (TC-06-*), nulmetingen (NM-001) | project-manager, backend-db |

---

## 🛠️ Installatie

**Canonieke installatiegids:** [`/docs/9-beheer/installatie.md`](./9-beheer/installatie.md) — vereisten, `.env`, `docker compose`, eerste login, data, bijwerken, backup/restore, LLM, problemen oplossen en beveiliging. Andere installatiedocumenten (`BUILD.md`, `GETTING_STARTED.md`, `DATABASE_INITIALISATIE_HANDLEIDING.md`, het stappenplan hieronder) zijn verouderd of aanvullend.

---

## 🔭 Strategische Visiedocumenten

> Documenten die de **toekomstige richting** bepalen — lezen vóór architectuur- of integratiebeslissingen.

| Document | Locatie | Onderwerp | Relevant voor |
|----------|---------|-----------|---------------|
| **Systeemarchitectuur & Implementatiegids (ICT)** | [`/docs/2-architectuur/architecture/systeemarchitectuur_en_implementatiegids_ict.md`](./2-architectuur/architecture/systeemarchitectuur_en_implementatiegids_ict.md) | Componentenoverzicht, interacties, Keycloak/Entra ID SSO & Docker implementatievereisten | project-manager, devops-infra, secops-identity, technisch-communicatie |
| **Docker Installatie & DB Restore (Externe Organisatie)** | [`/docs/9-beheer/stappenplan_docker_installatie_externe_organisatie.md`](./9-beheer/stappenplan_docker_installatie_externe_organisatie.md) | Aanvullend op de installatiegids: complete database via een dump overzetten naar een externe organisatie | devops-infra, project-manager, backend-db |
| **CI/CD Pipeline & Docker Hub** | [`/docs/9-beheer/cicd_pipeline_docker_hub.md`](./9-beheer/cicd_pipeline_docker_hub.md) | GitHub Actions → Docker Hub uitlevering: semantic versioning (#27), build/test/publish pipeline (#28), productie docker-compose, testmethodiek | devops-infra, project-manager |
| **Mesh van instanties (geen multi-tenancy)** | [`/docs/2-architectuur/mesh-van-instanties.md`](./2-architectuur/mesh-van-instanties.md) | Elke organisatie een eigen instantie; samenwerken door uitwisseling; alles wat een instantie inricht is portabel als data, via de portabiliteitspoort; ontwerpregels, repo-toets en fasering (ADR 0007, #231) | data-architect-engineer, secops-identity, backend-db |
| **API-landschap en laad-API** | [`/docs/2-architectuur/api-landschap.md`](./2-architectuur/api-landschap.md), [`/docs/api/laden/`](./api/laden/README.md) | Gescheiden API's per doel (NL GOV API Design Rules, ADR 0005); laad-API voor registratie en leveringen (ADR 0004, #205) | backend-db, data-architect-engineer, devops-infra |
| **Use Case Specificatie 1.0** | [`/docs/specificaties/usecase/`](./specificaties/usecase/README.md) | Normatieve definitie van een use case als declaratieve app: manifest, datasets, bronnen, afhankelijkheden, actoren, rechten, controles, bewijs, levenscyclus, uitvoerder; JSON-schema's per versie (ADR 0006, #227) | alle agents die use cases schrijven of de uitvoerder wijzigen |
| **Releasebeleid** | [`/docs/9-beheer/releasebeleid.md`](./9-beheer/releasebeleid.md) | Semantic Versioning, één bron `VERSION`, release-branches en tags, CHANGELOG, checklist voor een release, patches, ondersteunde versies (#27) | project-manager, devops-infra |
| **Fryslân Data Space & D-OmniTwin** | [`/docs/2-architectuur/architecture/fryslan_data_space_d_omni_twin_visiedocument.md`](./2-architectuur/architecture/fryslan_data_space_d_omni_twin_visiedocument.md) | Federatieve datalaag (FRLDS / iSHARE / FRL1000) als soevereine backend voor D-OmniTwin | data-architect-engineer, innovation-lab, samenwerking-adoptie |
| **D-OmniTwin in het Dataspace Landschap (Herijkt)** | [`/docs/2-architectuur/architecture/frlds_in_dataspace_landschap_herijkt_visiedocument.md`](./2-architectuur/architecture/frlds_in_dataspace_landschap_herijkt_visiedocument.md) | Herijkte visie: D-OmniTwin als dataspace-agnostische interactielaag (FRLDS, FDS en overige dataspaces) | data-architect-engineer, innovation-lab, samenwerking-adoptie |
| **Subsidie- & Adoptieplan 2026** | [`/docs/8-communicatie/communicatieplan_subsidie_2026.md`](./8-communicatie/communicatieplan_subsidie_2026.md) | Publieke positionering, subsidietrajecten (SIA RAAK) en adoptiestrategie voor dataspace-ecosysteem | project-manager, samenwerking-adoptie, technisch-communicatie |
| **Aanvraag Innovatiebudget 2026** | [`/docs/1-visie-concept/innovatie/aanvraag_innovatiebudget_digitale_overheid_2026_d_omni_twin.md`](./1-visie-concept/innovatie/aanvraag_innovatiebudget_digitale_overheid_2026_d_omni_twin.md) | Innovatiebudget aanvraag: D-OmniTwin als federatieve voorziening / dataspace interactielaag | project-manager, innovation-lab |
| **Huidige gebiedsmonitor SWF (vertrekpunt 0.3.0)** | [`/docs/1-visie-concept/huidige-gebiedsmonitor/`](./1-visie-concept/huidige-gebiedsmonitor/README.md) | Beschrijving van de monitor die 0.3.0 vervangt: functies, datamodel en gegevensstroom, indicatoren met UUID, methodiek (percentielklassen, labels A–E, n<10) en gat-analyse met eisen voor de laad-API (#195, #205) | project-manager, data-architect-engineer, backend-db |

---

## 📄 Kernbestanden root (hoge prioriteit)

| Bestand | Doel |
|---------|------|
| `README.md` | Versie, quickstart, overzicht |
| `LICENSE` & `LICENSE-DOCS` | EUPL 1.2 (Code) & CC BY 4.0 (Methodiek) |
| `CHANGELOG.md` | Wijzigingen per versie, met migratie-instructies |
| `docs/archief/` | Archief: `BUILD.md`, `GETTING_STARTED.md`, `ROADMAP.md`, `TODO.md`, `BUGFIX.md` (verouderd; taken en bugs staan in de GitHub-issues) |

---

## 🔑 Navigatieregels

- Bij conflicten tussen documenten geldt de code; voor installatie en beheer de [installatiegids](./9-beheer/installatie.md)
- **INDEX.md bepaalt** waar agents zoeken — geen aannames buiten docs
- **Gaps = expliciet benoemen**, niet invullen met aannames
- Bij **structurele wijzigingen**: dit bestand updaten vóór andere acties

---

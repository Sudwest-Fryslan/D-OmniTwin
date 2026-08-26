# INDEX.md — D-OmniTwin Documentatie Router
> **Rol:** Navigatielaag voor documentatie | Router voor agents | Overzicht van alle kennisdomeinen
> **Beheer:** Updaten bij nieuwe mappen of structurele wijzigingen
> **Lees eerst:** `STATE.md` (huidige systeemstatus) → dan pas dit bestand

---

## 🧭 Gebruik (voor agents)
1. Start met `STATE.md` om de actuele situatie te begrijpen
2. Gebruik dit INDEX.md om het relevante domein te selecteren
3. Beperk analyse tot de geïdentificeerde mappen — geen volledige scan

---

## 📂 Domeinen

| Domein | Map | Inhoud | Primaire skills |
|--------|-----|--------|-----------------|
| **Visie & Concept** | `/docs/1-visie-concept/` | Projectfilosofie, doelstellingen, gebruikersscenario's | project-manager, technisch-communicatie |
| **Architectuur** | `/docs/2-architectuur/` | Technische architectuur, API-design, component-diagram, **Dataspace integratie** | backend-db, data-architect-engineer, innovation-lab |
| **Data Engineering** | `/docs/3-data-engineering/` | ETL-pipelines, CBS/RIVM data, scores, indicatoren | data-architect-engineer, data-gis |
| **UX & Design** | `/docs/4-ux-design/` | UI-patronen, "Classic Premium UI", design-system, gebruikerservaringen (`gebruikerservaringen/`) | frontend-viz, web-carto-design |
| **SecOps** | `/docs/5-secops/` | Security-beleid, deployment, toegangsbeheer | env-setup, backend-db |
| **AI Parallel Track** | `/docs/6-ai-parallel-track/` | LLM-integratie, ontologie, AI-chat, prompting | innovation-lab, technisch-communicatie |
| **Projectmanagement** | `/docs/7-projectmanagement/` | Sprints, voortgang, besluiten, archief | project-manager |
| **Communicatie** | `/docs/8-communicatie/` | Stakeholdercommunicatie, rapportages, presentaties | technisch-communicatie |
| **Beheer & Applicatie** | `/docs/9-beheer/` | Handleidingen, workflows en applicatiebeheer | project-manager, backend-db |

---

## 🔭 Strategische Visiedocumenten

> Documenten die de **toekomstige richting** bepalen — lezen vóór architectuur- of integratiebeslissingen.

| Document | Locatie | Onderwerp | Relevant voor |
|----------|---------|-----------|---------------|
| **Systeemarchitectuur & Implementatiegids (ICT)** | [`/docs/2-architectuur/architecture/systeemarchitectuur_en_implementatiegids_ict.md`](./2-architectuur/architecture/systeemarchitectuur_en_implementatiegids_ict.md) | Componentenoverzicht, interacties, Keycloak/Entra ID SSO & Docker implementatievereisten | project-manager, devops-infra, secops-identity, technisch-communicatie |
| **Docker Installatie & DB Restore (Externe Organisatie)** | [`/docs/9-beheer/stappenplan_docker_installatie_externe_organisatie.md`](./9-beheer/stappenplan_docker_installatie_externe_organisatie.md) | Technisch stappenplan voor container deployment en database dump restore bij externe organisaties | devops-infra, project-manager, backend-db |
| **CI/CD Pipeline & Docker Hub** | [`/docs/9-beheer/cicd_pipeline_docker_hub.md`](./9-beheer/cicd_pipeline_docker_hub.md) | GitHub Actions → Docker Hub uitlevering: semantic versioning (#27), build/test/publish pipeline (#28), productie docker-compose, testmethodiek | devops-infra, project-manager |
| **Fryslân Data Space & D-OmniTwin** | [`/docs/2-architectuur/architecture/fryslan_data_space_d_omni_twin_visiedocument.md`](./2-architectuur/architecture/fryslan_data_space_d_omni_twin_visiedocument.md) | Federatieve datalaag (FRLDS / iSHARE / FRL1000) als soevereine backend voor D-OmniTwin | data-architect-engineer, innovation-lab, samenwerking-adoptie |
| **D-OmniTwin in het Dataspace Landschap (Herijkt)** | [`/docs/2-architectuur/architecture/frlds_in_dataspace_landschap_herijkt_visiedocument.md`](./2-architectuur/architecture/frlds_in_dataspace_landschap_herijkt_visiedocument.md) | Herijkte visie: D-OmniTwin als dataspace-agnostische interactielaag (FRLDS, FDS en overige dataspaces) | data-architect-engineer, innovation-lab, samenwerking-adoptie |
| **Open Source Model & Verdienstrategie** | [`/docs/1-visie-concept/juridisch/samenvatting_open_source_model_verdienstrategie_overheid.md`](./1-visie-concept/juridisch/samenvatting_open_source_model_verdienstrategie_overheid.md) | Herpositionering: Open methodiek + referentie-applicatie (hybride verdienmodel, EUPL licentie) | project-manager, samenwerking-adoptie |
| **Subsidie- & Adoptieplan 2026** | [`/docs/8-communicatie/communicatieplan_subsidie_2026.md`](./8-communicatie/communicatieplan_subsidie_2026.md) | Publieke positionering, subsidietrajecten (SIA RAAK) en adoptiestrategie voor dataspace-ecosysteem | project-manager, samenwerking-adoptie, technisch-communicatie |
| **Aanvraag Innovatiebudget 2026** | [`/docs/1-visie-concept/innovatie/aanvraag_innovatiebudget_digitale_overheid_2026_d_omni_twin.md`](./1-visie-concept/innovatie/aanvraag_innovatiebudget_digitale_overheid_2026_d_omni_twin.md) | Innovatiebudget aanvraag: D-OmniTwin als federatieve voorziening / dataspace interactielaag | project-manager, innovation-lab |

---

## 📄 Kernbestanden root (hoge prioriteit)

| Bestand | Doel |
|---------|------|
| `README.md` | Versie, quickstart, overzicht |
| `LICENSE` & `LICENSE-DOCS` | EUPL 1.2 (Code) & CC BY 4.0 (Methodiek) |
| `ROADMAP.md` | Sprintplanning, toekomstige features |
| `TODO.md` | Actieve takenlijst per domein |
| `BUGFIX.md` | Bekende bugs, fixes en impact |
| `BRAINDUMP.md` | Ideeën, visie, experimentele concepten |
| `BUILD.md` | Instructies voor env-setup en deployment |

---

## 🔑 Navigatieregels

- **STATE.md is leidend** bij conflicten tussen documenten
- **INDEX.md bepaalt** waar agents zoeken — geen aannames buiten docs
- **Gaps = expliciet benoemen**, niet invullen met aannames
- Bij **structurele wijzigingen**: dit bestand updaten vóór andere acties

---

## 📋 Actieve Sprint Plannen

| Sprint | Document | Status |
|--------|----------|--------|
| **Sprint 18** | [`docs/7-projectmanagement/archief/sprint-18-plan_ijsselmeerkust-besluitinstrument.md`](./7-projectmanagement/archief/sprint-18-plan_ijsselmeerkust-besluitinstrument.md) | 🚀 In uitvoering (Track B ✅, Track F toegevoegd) |
| **Sprint 19** | [`docs/7-projectmanagement/archief/sprint-19-plan_data-naar-inzicht.md`](./7-projectmanagement/archief/sprint-19-plan_data-naar-inzicht.md) | 📌 Gepland (na Sprint 18) |
| **Sprint 17** | [`docs/5-secops/logging/sprint-17-logging-spec.md`](./5-secops/logging/sprint-17-logging-spec.md) | ✅ Afgerond |

---

*Laatste update: zie STATE.md → `laatste_update` veld*

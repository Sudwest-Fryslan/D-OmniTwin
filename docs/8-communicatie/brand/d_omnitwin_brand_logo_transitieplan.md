# EPIC: D-OmniTwin Merktransformatie & Logo-Architectuur

**Doel:** Migratie van het persoonlijke monogram (TL-$\pi$) naar een collectieve productidentiteit voor **D-OmniTwin**, met een strakke scheiding tussen de **officiële release-implementatie (v0.3.0)** en de **lange-termijn verkenning naar een speelse mascotte/community-identiteit**.

---

## Inhoudsopgave

1. [Strategische Context & Doelstelling](#1-strategische-context--doelstelling)
2. [Spoor 1 — Release-Kritiek: Implementatie "Geodetisch D-Zegel" (v0.3.0)](#2-spoor-1--release-kritiek-implementatie-geodetisch-d-zegel-v030)
   - [2.1 Technische Specificaties Concept 01](#21-technische-specificaties-concept-01)
   - [2.2 Asset Delivery Matrix](#22-asset-delivery-matrix)
   - [2.3 Codebase Implementatie-Checklist](#23-codebase-implementatie-checklist)
   - [2.4 Definition of Done (DoD) Spoor 1](#24-definition-of-done-dod-spoor-1)
3. [Spoor 2 — R&D / Verkenning: Speelse Mascotte & 80s Retro DNA](#3-spoor-2--rd--verkenning-speelse-mascotte--80s-retro-dna)
   - [3.1 Filosofisch & Metaforisch Kader](#31-filosofisch--metaforisch-kader)
   - [3.2 De Vier Verkenningrichtingen](#32-de-vier-verkenningrichtingen)
   - [3.3 Touchpoints & UX-Toepassingen](#33-touchpoints--ux-toepassingen)
   - [3.4 Onderzoeksvragen & Toetscriteria](#34-onderzoeksvragen--toetscriteria)
4. [Twee-Sporen Model Architectuur (Governance)](#4-twee-sporen-model-architectuur-governance)
5. [Agent Takenlijst & Prompting Instructies](#5-agent-takenlijst--prompting-instructies)

---

## 1. Strategische Context & Doelstelling

### 1.1 Waarom deze transitie?
In de ontstaansfase van D-OmniTwin functioneerde het persoonlijke monogram ($T + L = \pi$) als kwaliteitszegel van de auteur. Met de doorgroei naar een samenwerkingsverband en een federaal platform (geschikt voor gemeenten, waterschappen en provincies) is een persoonsonafhankelijke merkidentiteit noodzakelijk.

### 1.2 Behoud van Kernactiva (Het DNA)
Het loslaten van de letters **T** en **L** betekent nadrukkelijk **niet** dat het visuele fundament verloren gaat. De volgende elementen blijven behouden en worden verrijkt:
* **Het Geodetische Bolrooster:** De cartografische meridianen en breedtegraden die staan voor GIS, wiskunde en ruimtelijke data.
* **De Natuurlijke Horizonlijn:** De gebogen arc die de fysieke aarde en het maaiveld representeert.
* **Het "Triple Threat" Kleurenfundament:** 
  * *Trust Blue* (techniek, interface, betrouwbaarheid)
  * *Nature Green* (leefomgeving, fysieke data, status)
  * *Geo Gold* (de gecoördineerde node, precisie, focus)

---

## 2. Spoor 1 — Release-Kritiek: Implementatie "Geodetisch D-Zegel" (v0.3.0)

> **Status:** READY FOR IMPLEMENTATION  
> **Target:** D-OmniTwin v0.3.0  
> **Prioriteit:** P0 / Blocker  
> **Bron:** `brand_identity_d_omnitwin.html` (Concept 01)

### 2.1 Technische Specificaties Concept 01

Het **Geodetische D-Zegel** vervangt de eerdere dubbele stammen door een monolithische, geometrische letter **D**, waarbij:
1. De **stam (spine)** van de D exact samenvalt met de centrale nulmeridiaan.
2. De **boog (arc)** van de D de geodetische curve van de oostelijke hemisfeer omsluit.
3. De **horizonboog** (groen) dwars door de D snijdt en het snijpunt markeert met een gouden node.

```
       ┌─────────────────────────────┐
       │      Geodetische Koepel     │
       │    ╭───────────┳────────╮   │
       │   │  │   │    █┃█   │   │   │
       │  │   │   │    █┃█────╮   │  │  <-- Boog van de D
       │ ├───┼───┼─────█┃█     │───┤ │
       │  │   │   │    █┃█    ╭╯  │  │
───────┴───═════════════●════════════─┴─────── Horizonboog + Geo Gold Node
       │  │   │   │    █┃█────╯   │  │
       │   │  │   │    █┃█   │   │   │
       │    ╰───────────┻────────╯   │
       │        Meridiaan Grid       │
       └─────────────────────────────┘
```

#### Vector Parameters & SVG Constructie:
* **Canvas Box:** `viewBox="0 0 120 120"`
* **Buitencirkel:** `cx="60" cy="60" r="54"` (Stroke: `#334155`, fill: `#0f172a` in dark / `#ffffff` in light)
* **Cartografisch Raster:** Verticale meridianen op $x = 30, 60, 90$; parallellen op $y = 35, 85$. Stroke-width: `1.0px`.
* **Groene Horizon Arc:** `M 12 76 Q 60 52 108 76` (Stroke: `var(--brand-nature)`, stroke-width: `3.0px`, linecap: `round`)
* **D-Constructie (Monoline / Bepantsering):**
  * *Rechte stam (Spine):* `rect x="36" y="30" width="13" height="60" rx="3"` (Fill: `var(--brand-action)`)
  * *Halfronde boog (Arc):* `M 44 30 L 68 30 C 86 30 96 42 96 60 C 96 78 86 90 68 90 L 44 90 Z` (Stroke: `var(--brand-action-light)` / `var(--brand-action-dark)`, width: `13px`)
* **Geo Gold Node:** `circle cx="60" cy="58" r="4.5"` (Fill: `var(--brand-accent)`, stroke: background-kleur, stroke-width: `2px`)

#### Kleur-Tokens (Master Palette v1.9.0 / Sprint 8E compatibel):
* **Trust Blue:** `#1e3a8a` (Light) / `#3b82f6` (Dark)
* **Nature Green:** `#15803d` (Light) / `#22c55e` (Dark)
* **Geo Gold:** `#c59d00` (Light) / `#eab308` (Dark)

---

### 2.2 Asset Delivery Matrix

Voor v0.3.0 moeten de volgende productieversies gegenereerd en geplaatst worden in `static/images/brand/`:

| Bestandsnaam | Formaat | Resolutie / Doel | Modus |
|--------------|---------|------------------|-------|
| `d-omnitwin-seal-dark.svg` | SVG | Vector / Header, Nav, Splash | Dark Mode (Standaard) |
| `d-omnitwin-seal-light.svg` | SVG | Vector / Export, Reports, Print | Light Mode |
| `d-omnitwin-seal-monochrome.svg`| SVG | 1-kleur wit / zwart voor stempels | Monochroom |
| `favicon.ico` | ICO | Multi-res (16x16, 32x32, 48x48) | Dark/Light adaptive |
| `apple-touch-icon.png` | PNG | 180x180 px | Squircle container |
| `icon-192.png` / `icon-512.png` | PNG | PWA Manifest & App launchers | Web App standaard |

---

### 2.3 Codebase Implementatie-Checklist

Agents en ontwikkelaars dienen de volgende bestanden bij te werken voor v0.3.0:

- [ ] **1. Asset Generatie & Plaatsing:**
  - Plaats de geoptimaliseerde SVG's in `static/images/brand/` en `admin-panel/public/brand/`.
- [ ] **2. Vervanging Oude Logo-referenties:**
  - Zoek naar alle instanties van `TL-logo_v1.png` en vervang door het nieuwe `d-omnitwin-seal-*.svg`.
  - Controleer `templates/index.html` (header navigatie linksboven).
  - Controleer `admin-panel/src/components/Header.tsx` en `Sidebar.tsx`.
- [ ] **3. HTML Meta & Favicon:**
  - Update `<link rel="icon">` in `templates/index.html` en `admin-panel/index.html`.
  - Update OpenGraph meta-tags (`og:image`).
- [ ] **4. CSS Brand Variables Sync:**
  - Zorg dat de hex-waarden van het Master Palette verankerd zijn in `:root` en `[data-theme="dark"]` in `static/css/styles.css` en `admin-panel/src/styles/admin.css`.
- [ ] **5. Regressietest Kaart-Overlay:**
  - Controleer of het logo in compact formaat (28px - 36px hoogte) in de navigatiebalk scherp blijft en de kaartoverlay niet verstoort.

---

### 2.4 Definition of Done (DoD) Spoor 1
* Het logo toont de **D** in plaats van **TL-$\pi$**.
* Het geodetische raster, de horizonboog en de goudkleurige node zijn visueel intact.
* Geen gebroken afbeeldingen of verwijzingen meer naar `TL-logo_v1.png`.
* Favicon en UI-headers tonen het nieuwe zegel in zowel Light- als Dark-mode.
* Release notes van v0.3.0 vermelden de officiële overstap naar het *D-OmniTwin Geodetisch Zegel*.

---

## 3. Spoor 2 — R&D / Verkenning: Speelse Mascotte & 80s Retro DNA

> **Status:** EXPLORATORY / R&D (Niet blokkerend voor v0.3.0)  
> **Prioriteit:** P2 / Strategische Merkontwikkeling  
> **Referentiebestanden:** 
> * `d_omnitwin_80s_mascotte_visuals.html`
> * `d_omnitwin_80s_mascotte_brainstorm.md`
> * `d_omnitwin_speels_en_federatief.md`

### 3.1 Filosofisch & Metaforisch Kader

Spoor 2 onderzoekt hoe we de complexiteit van GIS, digitale tweelingen en federatieve netwerken ontwapenen door een herkenbare mascotte. 

#### De Drie Inspiratiebronnen:
1. **Linux Tux:** 
   Een speels, benaderbaar dier dat niet corporate oogt, maar wereldwijd een cultstatus verwierf binnen open-source engineering.
2. **Robin de Robot (Bassie & Adriaan):** 
   De oervorm van een Digital Twin: een attente robotcompagnon met radar-oortjes die meekijkt, waarschuwt bij obstakels en helpt navigeren (*"Wat zeggie?"*).
3. **Transformers (G1 Optimus Prime) & 80s Synthwave:**
   * *"More Than Meets The Eye":* Een terrein of dijk lijkt fysiek gras, maar herbergt een levend digitaal datamodel.
   * *Combiners (Devastator/Superion):* Autonome mini-robots die samen één krachtige eenheid vormen — exact de metafoor voor een **federatief netwerk** van gemeenten en waterschappen.
   * *Synthwave Grid:* Het paars/blauwe perspectiefraster is historisch gezien identiek aan de eerste computer-gegenereerde **Digital Elevation Models (DEM)** in cartografie.

---

### 3.2 De Vier Verkenningrichtingen

| Concept | Naam | Metafoor | Primaire Toepassing |
|---------|------|----------|---------------------|
| **01** | **Omni-Prime** | De Nobele Terra-Guardian (Optimus DNA, D-helmprofiel, ruiten met hoogtemodel). | Software-ambassadeur, release-posters, keynote-introducties. |
| **02** | **Vector-84** | De Speelse Geodetische Scout (Robin de Robot knipoog, koepelkop, 80s zonsondergang). | Onboarding-assistent, documentatie, status-badges, laptopstickers. |
| **03** | **Twin-Bot Combiner** | De Modulaire Federatie (Groene Phy-Bot + Blauwe Digi-Bot klikken samen tot 'D'). | Uitleg-illustratie voor federatieve samenwerking tussen overheidslagen. |
| **04** | **Omni-Shield** | Het Autobot-Stijl Geodetisch Insigne (Scherpe facetten, geïntegreerd gezicht/windroos). | Alternatief hardware-/keurmerkembleem (*"Powered by OmniTwin"*). |

---

### 3.3 Touchpoints & UX-Toepassingen

In dit onderzoek wordt onderzocht waar een mascotte functionele waarde toevoegt in de software-ervaring:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        D-OmniTwin User Journey                         │
├───────────────────┬───────────────────────────────┬────────────────────┤
│ Touchpoint        │ Conventionele Stijl (Saai)    │ Met Mascotte-DNA   │
├───────────────────┼───────────────────────────────┼────────────────────┤
│ CLI / Sync Status │ "Sync completed: 1721 areas." │ "Vector-84 meldt:  │
│                   │                               │ Alle nodes online!"│
├───────────────────┼───────────────────────────────┼────────────────────┤
│ 2D -> 3D Extrusie │ "Toggle 3D View"              │ Transformatie-icoon│
│                   │                               │ ("Transform!")     │
├───────────────────┼───────────────────────────────┼────────────────────┤
│ Lege Data State   │ "Geen data gevonden."         │ Scout met radartje │
│ (Empty State)     │                               │ zoekt naar signaal │
├───────────────────┼───────────────────────────────┼────────────────────┤
│ Community / Swag  │ Bedrijfsnaam op pen           │ Die-cut sticker van│
│                   │                               │ Omni-Prime / Robin │
└───────────────────┴───────────────────────────────┴────────────────────┘
```

---

### 3.4 Onderzoeksvragen & Toetscriteria

Dit spoor moet de volgende vragen beantwoorden vóór introductie in latere versies (bijv. v0.4.0 of v1.0.0):

1. **Acceptatie bij Overheden & Bestuurders:**
   * Is een speelse mascotte (zoals Vector-84) acceptabel voor traditionele overheidsorganisaties, mits deze beperkt blijft tot onboarding, handleidingen en documentatie?
2. **Humanoïde vs. Abstract:**
   * Geven partners de voorkeur aan een robot-karaktertje (Concept 01/02) of aan een strak hoekig insigne (Concept 04)?
3. **Rol in Documentatie & DevRel:**
   * Kan de mascotte fungeren als mascotte voor developers (SDK, API-documentatie, GitHub repo badges)?

---

## 4. Twee-Sporen Model Architectuur (Governance)

Om te voorkomen dat de speelse verkenning de zakelijke betrouwbaarheid van de software ondermijnt, hanteren we het **GitHub Octocat / Linux Tux model**:

```
                          ┌─────────────────────────────┐
                          │   D-OmniTwin Identiteit     │
                          └──────────────┬──────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
    ┌───────────────────────────┐                 ┌───────────────────────────┐
    │          SPOOR 1          │                 │          SPOOR 2          │
    │   Het Officiële Zegel     │                 │   De Mascotte / Compagnon │
    │   (Geodetische D v0.3.0)  │                 │    (Vector-84 / Omni-Bot) │
    ├───────────────────────────┤                 ├───────────────────────────┤
    │ • App Header & Navigatie  │                 │ • Documentatie & Tutorials│
    │ • Kaartoverlay & Watermark│                 │ • Statusmeldingen & Tips  │
    │ • Officiële Rapportages   │                 │ • Laptopstickers & Swag   │
    │ • Bestuurlijke Presentaties│                │ • Release Notes & Discord │
    └───────────────────────────┘                 └───────────────────────────┘
```

---

## 5. Agent Takenlijst & Prompting Instructies

Wanneer AI-agents (zoals Claude, GPT-Codex of Gemini) worden ingezet om deeltaken uit te voeren, kunnen onderstaande taken direct als input dienen:

### Taak A1 (Design / Vector Agent) — *Spoor 1*
> *"Genereer een schaalbare SVG van Concept 01 (Geodetisch D-Zegel) conform de specificaties in sectie 2.1 van d_omnitwin_brand_issue_plan.md. Zorg voor inline CSS-custom properties (`var(--brand-action)`, `var(--brand-nature)`, `var(--brand-accent)`) zodat het bestand adaptief meekleurt met Light- en Dark-mode."*

### Taak A2 (Frontend Implementatie Agent) — *Spoor 1*
> *"Vervang alle instanties van het oude logo `TL-logo_v1.png` in de frontend templates (`templates/index.html` en admin-panel) door de nieuwe geodetische D-zegel SVG assets conform de checklist in sectie 2.3. Valideer dat de favicon correct functioneert voor v0.3.0."*

### Taak B1 (Community & Concept Agent) — *Spoor 2*
> *"Werk een prototype-document uit voor de integratie van mascotte 'Vector-84' in de onboarding flow van D-OmniTwin. Schrijf 5 voorbeelden van micro-copy voor systeemstatussen (succesvolle sync, offline node, 3D-kaart laden, error state) in de vriendelijke toon van een attente scout."*

---

*Einde Specificatiedocument — Opgesteld ten behoeve van D-OmniTwin v0.3.0 Milestone.*
# Testresultaten Scenario 2: Gebiedsselectie met Actieve Indicator

> **Status:** Uitgevoerd (Zonder blur op dock)  
> **Datum:** 2026-10-25  
> **Omgeving:** Chrome DevTools Performance Trace ([`traces/s2-desktop-actieve-indicator-geen-blur.json.gz`](traces/s2-desktop-actieve-indicator-geen-blur.json.gz))  
> **Viewport:** Desktop 1920×1080  
> **Selectie:** 1 buurt (`BU19001007`)  
> **Initiële staat:** Rechterdock GESLOTEN, **Indicator ACTIEF** (`1bec5763-5216-484d-95fe-474a4296a341`)  
> **Gekoppeld issue:** [#465](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/465)  
> **Moederdocument:** [`docs/4-ux-design/interactie-gebiedsselectie.md`](../interactie-gebiedsselectie.md)

---

## 1. Doel van de meting

Toetsen van Scenario 2 (S2) uit het meetplan: wat gebeurt er als de gebruiker op een buurt klikt terwijl er **al een indicator actief is** op de kaart?
- Treedt de dubbele Kompas-aanroep (B1) weer op?
- Wordt de detailketen van de indicator inderdaad dubbel aangeroepen (Code-bevinding B2)?
- Wat is de totale CPU-, GPU- en layoutbelasting als zowel het Kompas als het indicator-detailpaneel gelijktijdig opbouwen?

---

## 2. Gemeten Tijdlijn (Trace-analyse)

| Relatieve tijd | Duur | Categorie | Exacte gebeurtenis |
|---|---|---|---|
| **t = 24.819 s** | 0.09 ms | Event | **Klik op gebied** (`click` op `BU19001007` met actieve indicator). |
| **t = 25.121 s** | 39.2 ms | Netwerk | `GET /api/gebiedsmonitor/indicatorpaneel?...&gebied_ids=BU19001007` (Detailketen 1) |
| **t = 25.122 s** | 24.5 ms | Netwerk | `GET /api/kompas/1/history/BU19001007/...` (Detailketen 1) |
| **t = 25.122 s** | 61.7 ms | Netwerk | `GET /api/kompas/indicator/.../top-buurten?gebied_id=BU19001007` (Detailketen 1) |
| **t = 25.122 s** | 61.4 ms | Netwerk | `GET /api/gebiedsmonitor/gebieden/BU19001007` |
| **t = 25.122 s** | 400.2 ms | Netwerk | `GET /api/kompas/1/gebied/BU19001007` (Kompas aanroep 1) |
| **t = 25.123 s** | 401.7 ms | Netwerk | `GET /api/kompas/1/gebied/BU19001007` (Kompas aanroep 2 — **B1**) |
| **t = 25.481–26.001 s** | ~500 ms | WebGL / Net | Start MapLibre camera-vlucht (zoom 7 → 12) + ophalen van 35+ PDOK vectortiles. |
| **t = 25.525 s** | — | Netwerk | Beide Kompas HTTP-responses landen na 400 ms. |
| **t = 25.525 s** | **163.89 ms** | **Main CPU** | **Long Task:** Parsing Kompas JSON + opbouw Sunburst + layout van detailpaneel. |
| **t = 25.680 s** | 43.7 ms | Netwerk | `GET /api/gebiedsmonitor/indicatorpaneel?...&gebied_ids=BU19001007` (**Detailketen 2 — B2**) |
| **t = 25.680 s** | 29.8 ms | Netwerk | `GET /api/kompas/1/history/BU19001007/...` (**Detailketen 2 — B2**) |
| **t = 25.680 s** | 70.2 ms | Netwerk | `GET /api/kompas/indicator/.../top-buurten?gebied_id=BU19001007` (**Detailketen 2 — B2**) |
| **t = 26.000–26.400 s** | 400 ms | Layout / Paint | Continue stroom van `Layout` (1.5–2.4 ms) en `Paint` (1.0 ms) per animatieframe. |

---

## 3. Toetsing van de Bevindingen

### [BEWEZEN] Code-bevinding B2 — Dubbele detailketen bij actieve indicator
- **Code-analyse:** In `kompas.js` triggert `SELECTIE_GEWIJZIGD` direct `loadIndicatorDetails` (r.3134). Zodra het Kompas-antwoord later binnenkomt, start `expandDetails` (r.1854) exact dezelfde detailketen nogmaals, zonder verzoek-id bescherming.
- **Feitelijke meting:**
  1. Eerste batch requests vertrekt om **`t = 25.121 s`** (3 requests: indicatorpaneel, history, top-buurten).
  2. Tweede batch met exact dezelfde 3 requests vertrekt om **`t = 25.680 s`** (559 ms later, direct nadat het Kompas klaar is met renderen).
- **Impact:** Bij elke klik met actieve indicator worden er 3 overbodige HTTP-verzoeken naar de backend gestuurd die elkaars data overschrijven.

### [BEWEZEN] Code-bevinding B1 — Dubbele Kompas-aanroep
- Om `t = 25.122 s` en `t = 25.123 s` (1 ms verschil) worden opnieuw twee identieke GET-verzoeken naar `/api/kompas/1/gebied/BU19001007` gestuurd.

### Vergelijking S1 (zonder indicator) vs S2 (met indicator)

| Metric | Scenario 1 (Zonder indicator) | Scenario 2 (Met actieve indicator) | Verschil |
|---|---|---|---|
| **Aantal backend-verzoeken per klik** | 3 (waarvan 1 dubbel) | **8** (waarvan 4 dubbel!) | **+166% netwerkverkeer** |
| **Langste Main-thread Long Task** | 127.71 ms | **163.89 ms** | **+28% langere UI-bevriezing** |
| **Totale Layout / Reflow tijd** | 88.69 ms | **220.41 ms** | **+148% meer layout-herberekening** |
| **Totale Paint tijd** | 16.26 ms | **86.73 ms** | **+433% meer tekenwerk** |

---

## 4. Conclusie

Scenario 2 toont aan dat de huidige interactie met een actieve indicator bijzonder zwaar is voor zowel browser als backend:
1. **Verkeerslawine:** Eén enkele klik veroorzaakt 8 backend API-aanroepen, waarvan er **4 zuiver overbodig zijn** (2x Kompas, 2x detailketen).
2. **Dubbele render-slag:** Het indicatorpaneel wordt bij aankomst van de selectie bijgewerkt (`25.12s`), en 550 ms later nóg eens volledig overtekend (`25.68s`).
3. **Choreografie:** De browser moet gelijktijdig de MapLibre cameravlucht animeren, 35+ PDOK vectortiles laden, twee keer de indicator-details parsen én het Kompas zonnediagram opbouwen.

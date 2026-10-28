# Testresultaten Scenario 1: Nulmeting Gebiedsselectie

> **Status:** Uitgevoerd (Eerste opname — met standaard blur)  
> **Datum:** 2026-10-25  
> **Omgeving:** Chrome DevTools Performance Trace (`traces/s1-desktop-nulmeting.json.gz` — gearchiveerd bij [#465](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/465))  
> **Viewport:** Desktop 1920×1080  
> **Selectie:** 1 buurt (`BU19000115`, Bolsward)  
> **Initiële staat:** Rechterdock GESLOTEN, geen actieve indicator  
> **Gekoppeld issue:** [#465](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/465)  
> **Moederdocument:** [`docs/4-ux-design/interactie-gebiedsselectie.md`](../interactie-gebiedsselectie.md)

---

## 1. Doel van de meting

Toetsen van de baseline interactie (S1) conform het meetplan:
- Wat is de vertraging tussen de klik en het netwerk?
- Wordt `loadKompasForSelection` daadwerkelijk dubbel aangeroepen (Code-bevinding B1)?
- Wanneer landen de data-antwoorden en wat is de impact op de Main CPU thread (Hypothesen H1 en H2)?
- Hoe verloopt de samenloop tussen de Kompas-opbouw en de MapLibre camerabeweging?

---

## 2. Gemeten Tijdlijn (Trace-analyse)

| Relatieve tijd | Duur | Categorie | Exacte gebeurtenis |
|---|---|---|---|
| **t = 16.557 s** | 0.22 ms | Event | **Klik op kaartgebied** (`click` event op canvas voor `BU19000115`). |
| **t = 16.860 s** | 34.8 ms | Netwerk | `GET /api/gebiedsmonitor/gebieden/BU19000115` |
| **t = 16.860 s** | 220.5 ms | Netwerk | `GET /api/kompas/1/gebied/BU19000115` (Aanroep 1) |
| **t = 16.861 s** | 221.7 ms | Netwerk | `GET /api/kompas/1/gebied/BU19000115` (Aanroep 2) |
| **t = 17.082 s** | — | Netwerk | Beide Kompas HTTP-responses landen in de browser. |
| **t = 17.083 s** | **127.71 ms** | **Main CPU** | **Long Task (Rode blokkade):** JSON parsing & D3 Sunburst SVG DOM-opbouw. |
| **t = 17.097–17.100 s** | — | DOM | **Massale DOM-injectie:** In één frame worden 50+ SVG elementen (`path`, `text`) toegevoegd. |
| **t = 17.135–17.150 s** | 15 ms | Layout | **Forced Reflow / Layout Thrashing:** Tientallen opeenvolgende paren van `UpdateLayoutTree` + `Layout`. |
| **t = 17.220–17.990 s** | ~770 ms | WebGL / Net | **Camerabeweging (zoom 7 → 12):** MapLibre `flyTo` camera-animatie gelijktijdig met het ophalen van 40+ PDOK vectortiles. |

---

## 3. Toetsing van de Hypothesen

### [BEWEZEN] Code-bevinding B1 — Dubbele netwerkaanroep
- **Voorspelling:** `loadKompasForSelection` wordt bij één klik tweemaal aangeroepen (in `openRechterDock` én in `onClick`).
- **Meting:** Om `t = 16.860 s` en `t = 16.861 s` vertrekken twee identieke GET-verzoeken naar `/api/kompas/1/gebied/BU19000115`. Beide verzoeken belasten het netwerk en duren ~221 ms.

### [BEWEZEN] Hypothese H1 — Kompas datavertraging
- **Voorspelling:** De data van het Kompas doet er merkbaar lang over en arriveert midden in de interactie.
- **Meting:** Het duurt 525 ms na de klik (`16.557 s` → `17.082 s`) voordat de data beschikbaar is voor rendering.

### [BEWEZEN] Hypothese H2 — Kompas renderpiek & Main-thread blokkade
- **Voorspelling:** Het opbouwen van het Kompas blokkeert de UI thread en veroorzaakt framedrops.
- **Meting:** De browser bevriest de Main thread **127.71 ms lang**. In die taak vindt zware *layout thrashing* plaats (tientallen synchrone layout-recalculations tussen `17.135 s` en `17.150 s`). In de Performance trace leidt dit direct tot gele markeringen in de *Frames* lane (frames > 16.7 ms en > 50 ms).

### [IN ONDERZOEK] Hypothese H3 — Belasting door `backdrop-filter: blur(16px)`
- **Voorspelling:** Het blur-filter op `#rechter-dock` trekt zwaar aan de GPU tijdens gelijktijdige WebGL-camerabewegingen.
- **Status:** Wordt getoetst via een tweede meting waarbij `backdrop-filter: none` is gezet.

---

## 4. Conclusie & Aandachtspunten voor de choreografie
1. **Opeenhoping van werk:** De zware D3 Sunburst rendering landt om `17.083 s`, precies op het moment dat het dock openschuift en de MapLibre cameravlucht start (`17.22 s`). Hierdoor moeten GPU en CPU gelijktijdig DOM-bomen herbouwen, vectortiles laden en WebGL-frames renderen.
2. **Onnodig netwerkverkeer:** De dubbele API-aanroep (B1) is reëel aanwezig in de trace en kan direct geëlimineerd worden.
3. **Layout thrashing:** De code die het Kompas tekent of het dock opent leest en schrijft herhaaldelijk afmetingen naar de DOM binnen dezelfde taak, wat leidt tot geforceerde reflows.

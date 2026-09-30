# Multi-Gebiedsdossier — Implementatieplan

**Sprint:** Volgende sessie  
**Prioriteit:** Hoog  
**Type:** Nieuwe feature (rapportmodule uitbreiding)  
**Auteur:** D-OmniTwin project  
**Datum aangemaakt:** 2026-04-09  
**Status:** 📋 Klaar voor uitvoering

---

## Probleemstelling & Gebruikerswens

Een beleidsmedewerker die de omgevingsvisie-deelgebieden (bijv. IJsselmeergebied, 44 buurten) als selectieframe gebruikt, wil twee dingen weten:

1. **Totaalvraag:** Hoe scoort dit beleidsgebied als geheel op alle thema's?
2. **Spotlightvraag:** Welke buurten binnen de selectie wijken het sterkst af — en op welk onderwerp?

Dit vraagt om een **nieuw rapporttype** naast de bestaande Gebiedsdossier en Benchmark Vergelijker.

---

## Architectuurbeslissingen (vastgesteld)

| Beslissing | Keuze | Motivatie |
|-----------|-------|-----------|
| Aparte pagina | ✅ Ja — `/admin/rapport/multi-gebied` | Ander analytisch product, andere layout-behoeften |
| Referentiekader | Schakelbaar: Gemeente SWF ↔ Provincie Fryslân | Default: gemeente (consistent met Gebiedsdossier) |
| Z-score per buurt | MAX absolute z-score over alle indicatoren | Beleidsrelevant: "op welk onderwerp springt een buurt eruit?" |
| Totaaloverzicht | Gewogen z-score aggregaat per thema | Geeft beleidsmedewerker thema-overzicht |
| Kaartvisualisatie | D3 SVG choropleth (zelfstandig, printbaar) | Geen afhankelijkheid van hoofdvenster |
| API methode | POST met JSON body | URL-lengte te lang bij 44+ buurt-IDs |

---

## Dataflow

```
1. Gebruiker klikt op omgevingsvisie-deelgebied (bijv. IJsselmeergebied)
2. selectBuurtenFromDeelgebied(3, "IJsselmeergebied") → 44 buurt-IDs in state
   + state.selectedDeelgebiedNaam = "IJsselmeergebied"  [NIEUW]
3. Rapport-paneel → "Analyseer Selectie" knop
4. Modal biedt 3 opties: Gebiedsdossier | Benchmark | Multi-Gebiedsdossier
5. window.open('/admin/rapport/multi-gebied?gebieden=BU...&naam=IJsselmeergebied')
6. Backend: z-score berekening voor N buurten × M indicatoren
7. Frontend: choropleth + tabel + thema-aggregaat
```

---

## SQL Kern — Z-score Per Buurt Per Indicator

```sql
WITH alle_zscores AS (
    SELECT
        gd.gebied_id,
        g.naam                         AS buurt_naam,
        i.naam                         AS indicator_naam,
        COALESCE(vkh.titel_naam, i.categorie, 'Overig') AS thema,
        COALESCE(i.score_type, '+/+')  AS score_type,
        gd.waarde,
        rs.avg_waarde,
        rs.std_waarde,
        CASE WHEN rs.std_waarde > 0
            THEN (gd.waarde - rs.avg_waarde) / rs.std_waarde
            ELSE 0
        END AS z_score
    FROM (
        -- Meest recente waarde per buurt per indicator
        SELECT indicator_uuid, gebied_id, waarde, jaar,
               ROW_NUMBER() OVER(PARTITION BY gebied_id, indicator_uuid ORDER BY jaar DESC) AS rn
        FROM gebied_data
        WHERE gebied_id = ANY(:gebied_ids)
    ) gd
    JOIN gebieden g        ON gd.gebied_id = g.id
    JOIN indicatoren i     ON gd.indicator_uuid = i.uuid
    JOIN v_kompas_hierarchie vkh
                           ON i.uuid = vkh.indicator_uuid AND vkh.config_id = 1
    JOIN (
        -- Referentiestatistieken
        SELECT gd2.indicator_uuid,
               AVG(gd2.waarde)         AS avg_waarde,
               STDDEV_SAMP(gd2.waarde) AS std_waarde
        FROM gebied_data gd2
        JOIN gebieden g2 ON gd2.gebied_id = g2.id
        WHERE g2.gebiedstype_id = :gebiedstype_id
          -- Schakelbaar: onderstaande regel aan voor gemeente, weg voor Fryslân
          AND g2.gemeente_code = :gemeente_code
        GROUP BY gd2.indicator_uuid
    ) rs ON gd.indicator_uuid = rs.indicator_uuid
    WHERE gd.rn = 1
),
max_per_buurt AS (
    -- Per buurt: de indicator met de GROOTSTE absolute z-score
    SELECT DISTINCT ON (gebied_id)
        gebied_id, buurt_naam, indicator_naam, thema,
        z_score, ABS(z_score) AS z_score_abs, score_type
    FROM alle_zscores
    ORDER BY gebied_id, ABS(z_score) DESC
)
SELECT * FROM max_per_buurt ORDER BY ABS(z_score) DESC;
```

### Kleurmapping (server-side berekend)

| |z-score| | Kleur (hex) | Klasse |
|---------|------------|--------|
| 0.0 – 0.5 | `#6b7280` | In lijn |
| 0.5 – 1.0 | `#f59e0b` | Licht afwijkend |
| 1.0 – 1.5 | `#f97316` | Matig afwijkend |
| 1.5 – 2.0 | `#ef4444` | Sterk afwijkend |
| > 2.0 | `#991b1b` | Extreem afwijkend |

> Kleurrichting op basis van `score_type`: negatieve uitschieters op "lager is beter" indicatoren kleuren rood (niet groen).

---

## Pagina-indeling Multi-Gebiedsdossier

```
┌─────────────────────────────────────────────────────────┐
│ 🗺️ Multi-Gebiedsdossier: IJsselmeergebied (44 buurten) │
│ [Referentie: ⌀ Gemeente SWF ↔ ⌀ Provincie Fryslân]    │
│                                          [Exporteer PDF] │
├─────────────────────────────────┬───────────────────────┤
│                                 │                       │
│  🗺️ Z-score Afwijkingskaart    │  📊 Thema Aggregaat   │
│  D3 SVG choropleth              │  Gem. z-score/thema   │
│  Kleur per buurt = max |z|      │  Horizontale bars     │
│  Hover → tooltip met indicator  │                       │
│                                 │                       │
├─────────────────────────────────┴───────────────────────┤
│                                                         │
│  📋 Uitschietertabel (ranking)                          │
│  # | Buurt | Thema | Indicator | Z-score | Impact       │
│  1 | Allingawier | Sociaal | Bijstand | -2.4 | 🔴       │
│  2 | Makkum | Veiligheid | Gestolen fietsen | +1.9 | 🟠 │
│  ...                                     [Download CSV] │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Implementatie Stappen

### Stap 1 — Backend: `report_service.py`

**Nieuwe methode:** `generate_multi_gebied_payload()`

```python
def generate_multi_gebied_payload(
    self,
    gebied_ids: List[str],
    referentie: str = 'gemeente',   # 'gemeente' | 'fryslan'
    gemeente_code: str = '1900',
    deelgebied_naam: str = None
) -> Dict[str, Any]
```

**Output-structuur:**
```json
{
  "deelgebied_naam": "IJsselmeergebied",
  "referentie_label": "⌀ Gemeente Súdwest-Fryslân",
  "totaal_buurten": 44,
  "buurten_analyse": [
    {
      "buurt_id": "BU19001700",
      "buurt_naam": "Makkum",
      "max_z_score": -2.4,
      "max_z_score_abs": 2.4,
      "indicator_naam": "Bijstandsuitkering",
      "thema": "Sociaal domein",
      "score_type": "-/-",
      "impact": "bovengemiddeld negatief",
      "kleur_hex": "#ef4444"
    }
  ],
  "thema_aggregaat": {
    "Sociaal domein": { "gem_zscore": -1.2, "n_uitschieters": 8 },
    "Wonen": { "gem_zscore": 0.3, "n_uitschieters": 2 }
  },
  "top_uitschieters": []
}
```

Tweede methode voor GeoJSON (met buurt-geometrie + kleur voor choropleth):
```python
def generate_multi_gebied_geojson(
    self,
    gebied_ids: List[str],
    referentie: str = 'gemeente',
    gemeente_code: str = '1900'
) -> Dict[str, Any]  # GeoJSON FeatureCollection
```

---

### Stap 2 — Backend: `routers/report.py`

Twee nieuwe POST-endpoints toevoegen na de bestaande benchmark-endpoints:

```python
@router.post("/multi-gebied")
def get_multi_gebied_data(payload: MultiGebiedRequest, db: Session = Depends(get_db)):
    ...

@router.post("/multi-gebied/geojson")
def get_multi_gebied_geojson(payload: MultiGebiedRequest, db: Session = Depends(get_db)):
    ...
```

**Pydantic request model:**
```python
class MultiGebiedRequest(BaseModel):
    gebied_ids: List[str]
    referentie: str = 'gemeente'        # 'gemeente' | 'fryslan'
    gemeente_code: str = '1900'
    deelgebied_naam: Optional[str] = None
```

---

### Stap 3 — React Admin Panel: `MultiGebiedPage.tsx`

**Nieuwe pagina** in `admin-panel/src/pages/MultiGebiedPage.tsx`.

Key components:
- URL params: `?gebieden=BU...,BU...&naam=IJsselmeergebied&ref=gemeente`
- State: `referentie` toggle (gemeente | fryslan)
- Choropleth: D3-gebaseerde SVG vanuit GeoJSON response
- Tabel: sorteerbaar, with CSV-export functie
- Thema-bars: simpele horizontal bar chart (D3 of inline SVG)

**Routing in `App.tsx`:**
```tsx
import { MultiGebiedPage } from './pages/MultiGebiedPage';
// ...
<Route path="/rapport/multi-gebied" element={<MultiGebiedPage />} />
```

**Nav-item in sidebar `App.tsx`:**
```tsx
<NavLink to="/rapport/multi-gebied">
  <Layers size={18} /> Multi-Gebiedsdossier
</NavLink>
```

---

### Stap 4 — API service: `admin-panel/src/services/api.ts`

```typescript
multiGebied: {
  getData: (payload: MultiGebiedPayload) =>
    axios.post<MultiGebiedResponse>('/api/report/multi-gebied', payload),
  getGeoJSON: (payload: MultiGebiedPayload) =>
    axios.post('/api/report/multi-gebied/geojson', payload),
},
```

TypeScript types toevoegen aan `types.ts` of inline definieren.

---

### Stap 5 — `static/js/app.js` aanpassingen

**5a: `selectBuurtenFromDeelgebied()` — naam opslaan in state**
```javascript
// Na clearGebiedSelection() en voor updateSelectionUI():
state.selectedDeelgebiedNaam = deelgebiedNaam;  // NIEUW
```

**5b: State uitbreiden**
```javascript
selectedDeelgebiedNaam: null,  // Naam van het actieve deelgebied (voor rapport-link)
```

**5c: Rapport-modal — 3e knop bij multi-select**

In de huidige modal (regel ~1707 in app.js) bij `ids.length > 1`:
```javascript
// Huidig: direct naar benchmark
// Nieuw: ook optie Multi-Gebiedsdossier

const gebiedenParam = ids.join(',');
const deelgebiedNaam = state.selectedDeelgebiedNaam || `${ids.length} buurten`;
const multiUrl = `${baseUrl}/admin/rapport/multi-gebied?gebieden=${gebiedenParam}&naam=${encodeURIComponent(deelgebiedNaam)}`;

// 3 knoppen in modal:
// [Gebiedsdossier (1e buurt)] [Benchmark] [Multi-Gebiedsdossier]
```

---

### Stap 6 — Admin panel bouwen

```bash
# Na wijzigingen in admin-panel/src:
cd admin-panel && npm run build

# Workflow:
/build-admin-panel
```

---

## Verificatiechecklist

**Backend:**
- [ ] `POST /api/report/multi-gebied` geeft correcte JSON terug voor 44 buurt-IDs
- [ ] `POST /api/report/multi-gebied/geojson` geeft GeoJSON FeatureCollection
- [ ] Referentie-schakelaar werkt: gemeente vs Fryslân geeft andere z-scores
- [ ] Lege/niet bestaande buurt-IDs geven graceful error

**Frontend:**
- [ ] Route `/admin/rapport/multi-gebied` laadt pagina
- [ ] Referentie toggle herladen data zonder page refresh
- [ ] Choropleth kleurt buurten correct (grijs → rood)
- [ ] Hover tooltip: "Buurt X: stijgt het sterkst af op [indicator] (z=-2.4)"
- [ ] Uitschietertabel sorteerbaar op z-score, thema, buurt
- [ ] CSV export werkt
- [ ] Print/PDF layout klopt (`@media print` stijlen)

**Integratie:**
- [ ] Na omgevingsvisie klik → Rapport modal biedt "Multi-Gebiedsdossier" aan
- [ ] `state.selectedDeelgebiedNaam` gevuld → naam verschijnt in rapport header
- [ ] Naam correct URL-encoded doorgegeven

---

## Gerelateerde bestanden

| Bestand | Status |
|---------|--------|
| `services/report_service.py` | Toevoegen: `generate_multi_gebied_payload()`, `generate_multi_gebied_geojson()` |
| `routers/report.py` | Toevoegen: 2 POST endpoints |
| `admin-panel/src/pages/MultiGebiedPage.tsx` | Nieuw aanmaken |
| `admin-panel/src/App.tsx` | Route + nav-item toevoegen |
| `admin-panel/src/services/api.ts` | 2 API methods toevoegen |
| `static/js/app.js` | `selectedDeelgebiedNaam` state + rapport-modal 3e knop |
| `docs/testcases/06-integratie-e2e/TC-06-002_multi-gebiedsdossier.md` | Nieuw aanmaken |

---

## Scope-afbakening (v1.0)

**IN scope voor volgende sessie:**
- Z-score per buurt (max |z|) → kaart
- Thema-aggregaat → horizontale bars
- Uitschietertabel → sorteerbaar + CSV
- Referentie toggle gemeente/Fryslân
- Print-layout

**BUITEN scope (later):**
- AI narrative voor multi-gebied (uitbreiding LLM service)
- Totaal-Kompas (sunburst) aggregaat — complex, apart sprint
- Multi-select van omgevingsvisie-zones (is al architectureel voorbereid)

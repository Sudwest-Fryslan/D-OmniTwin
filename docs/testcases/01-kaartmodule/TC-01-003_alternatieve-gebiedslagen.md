# TC-01-003 — Alternatieve Gebiedslagen als Selectieframe

**Module:** Kaartmodule  
**Prioriteit:** Hoog  
**Sprint:** Sessie 2026-04-09  
**Status:** ✅ Omgevingsvisie geïmplementeerd | ❓ BAG / Woonbeleid nog te doen  
**Aangemaakt:** 2026-04-09  
**Bijgewerkt:** 2026-04-09

---

## Doel

Valideren dat de gebruiker kan **switchen tussen verschillende gebiedsindelingen** als selectieframe — naast de standaard CBS buurten/wijken. Elke laag dient als alternatieve geografische eenheid waarbinnen het Kompas en de benchmarks werken.

---

## Achtergrond

De huidige selectiemodus is gekoppeld aan CBS-buurten en -wijken. Voor beleidstoepassingen zijn echter andere indelingen relevanter:

| Gebiedslaag | Beheerder | Gebruik | Beschikbaarheid |
|-------------|-----------|---------|-----------------| 
| **CBS buurten/wijken** | CBS | Standaard statistische eenheid | ✅ Aanwezig |
| **Omgevingsvisie-zones SWF** | Gemeente SWF | Beleidsruimte per visiedocument | ✅ Geïmplementeerd (2026-04-09) |
| **BAG woonplaatsen** | Kadaster (BAG) | Administratieve kern-indeling | ⚠️ Te integreren |
| **Woonbeleid-gebieden** | Gemeente SWF | Woningmarktregio's, prestatieafspraken | 🔜 Dataset aan te leveren |
| **Eigen gebruikerszones** | Eindgebruiker | Ad-hoc beleidsgebied | ❓ Toekomstige feature |

---

## Precondities

- Applicatie draait (lokaal of staging)
- CBS-laag actief als fallback
- Dataset `Deelgebieden_omgevingsvisie.gpkg` geïmporteerd (✅ via `ETL/import_omgevingsvisie.py`)

---

## Teststappen

### A — Omgevingsvisie Súdwest-Fryslân als selectieframe ✅ GEÏMPLEMENTEERD

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 1 | Open **Kaartlagen**-tab → vink **Omgevingsvisie SWF** aan | 6 deelgebiedpolygonen verschijnen als paarse overlay bovenop CBS-buurten | ✅ |
| 2 | Hover over een deelgebied (bijv. Greidhoeke) | Tooltip toont: "🗺️ Greidhoeke · 142.4 km² · Klik om buurten te selecteren" | ✅ |
| 3 | Klik op **IJsselmeergebied** | 44 CBS-buurten worden goud gehighlight; badge toont "44 buurten geselecteerd" | ✅ |
| 4 | Controleer console-output | `📍 44 buurten geselecteerd via deelgebied IJsselmeergebied (buffer: -10m)` | ✅ |
| 5 | Open Kompas-paneel | Kompas laadt geaggregeerde data voor de 44 geselecteerde buurten | ✅ |
| 6 | Klik op **Sneek** (tweede deelgebied) | Vorige selectie gewist; nieuwe set Sneek-buurten geselecteerd | ✅ |
| 7 | Vink **Omgevingsvisie SWF** uit | Paarse overlay verdwijnt; buurt-selectie blijft intact | ✅ |
| 8 | **Grensbuurt-test:** kijk of buurten op de grens van Sneek/Merengebied maar in 1 deelgebied zitten | Dankzij -10m inward buffer geen dubbele selectie | ✅ |

**Geïmplementeerde bestanden:**
- `ETL/import_omgevingsvisie.py` — GeoPackage import naar `omgevingsvisie_deelgebieden` tabel
- `routers/omgevingsvisie.py` — 2 API endpoints
- `static/js/app.js` — `loadOmgevingsvisieLayer()`, `selectBuurtenFromDeelgebied()`, GeoJsonLayer
- `templates/index.html` — Toggle checkbox in Kaartlagen-paneel

**API Verificatie (uitgevoerd 2026-04-09):**
```
GET /api/omgevingsvisie/deelgebieden → 6 features ✅
GET /api/omgevingsvisie/deelgebieden/3/buurten → 44 buurten (IJsselmeergebied) ✅
```

---

### B — BAG Woonplaatsen als selectieframe

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 1 | Schakel naar gebiedslaag **BAG woonplaatsen** | Kaart toont woonplaatspolygonen i.p.v. CBS-buurten | ❓ |
| 2 | Klik op **Makkum** (woonplaats) | Makkum als gehele woonplaats geselecteerd | ❓ |
| 3 | Open Kompas | Kompas toont geaggregeerde data voor woonplaats Makkum | ❓ |
| 4 | Vergelijk met **Workum** (woonplaats) | Benchmark op woonplaatsniveau | ❓ |
| 5 | Schakel terug naar CBS-buurten | Selectie wordt gereset of vertaald naar buurt-equivalenten | ❓ |

### C — Woonbeleid-gebieden als selectieframe

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 1 | Activeer laag **Woonbeleid SWF** | Kaart toont woonmarktregio's | ❓ |
| 2 | Klik op regio | Selectie + Kompas aggregatie | ❓ |
| 3 | Koppel aan woningbouwindicatoren | Relevante Kompas-thema's actief | ❓ |

---

## Acceptatiecriteria

- [x] Omgevingsvisie SWF: deelgebieden laden als overlay
- [x] Omgevingsvisie SWF: klikken selecteert onderliggende CBS-buurten via -10m buffer
- [x] Omgevingsvisie SWF: tooltip met naam, oppervlakte en hint
- [x] Omgevingsvisie SWF: toggle aan/uit zonder verlies van selectie
- [ ] BAG woonplaatsen-laag werkt als volledig selectieframe
- [ ] Woonbeleid-gebieden werken als selectieframe
- [ ] Schakelen tussen lagen reset de selectie of vraagt om bevestiging

---

## Technische Notities

### Aggregatiemodel Omgevingsvisie

```
Omgevingsvisie polygoon (EPSG:28992)
    └── ST_Buffer(geom, -10)           ← inward buffer -10m
        └── ST_Intersects(buurt_geom) ← matching CBS buurten
            └── gemeente_code='1900'   ← filter op SWF
                └── Kompas aggregeert de N geselecteerde buurten
```

### Buffer-rationale
CBS-buurten delen exacte grenspunten. Zonder buffer pikt `ST_Intersects` ook aangrenzende buurten van het naburige deelgebied op. De -10m erosie beperkt de selectie tot buurten die echt binnen het polygoon vallen.

---

## Bevindingen / Opmerkingen

**Sessie 2026-04-09 — Implementatie omgevingsvisieselectie:**
- Dataset `Deelgebieden_omgevingsvisie.gpkg` (EPSG:28992, 6 polygonen) succesvol geïmporteerd
- Alle 6 deelgebieden werken als klikdoel met correcte buurtselectie
- Gemeente-filter in SQL voorkomt false positives bij grensgebieden (IJsselmeergebied is 531 km²)
- Data cached in `state.omgevingsvisieData` na eerste toggle-activatie (geen herhaald laden)

---

## Gerelateerde documenten

- [TC-01-001 Enkelvoudige gebiedsselectie](./TC-01-001_gebieds-selectie.md)
- [TC-01-002 Meervoudige selectie](./TC-01-002_meervoudige-selectie.md)
- [TC-06-001 E2E Beleidsadviseur IJsselmeerkust](../06-integratie-e2e/TC-06-001_beleidsadviseur-ijsselmeerkust.md)
- [TC-06-002 Multi-Gebiedsdossier](../06-integratie-e2e/TC-06-002_multi-gebiedsdossier.md)
- [PLAN Multi-Gebiedsdossier](../04-rapportage/PLAN_multi-gebiedsdossier.md)
- [Dataspace mapping indicatoren](../../../2-architectuur/dataspace-mapping/dataspace_mapping_indicatoren_ijsselmeerkust.md)

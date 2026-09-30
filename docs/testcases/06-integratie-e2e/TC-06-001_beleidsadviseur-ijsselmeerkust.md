# TC-06-001 — E2E: Beleidsadviseur IJsselmeerkust & Wadden

**Module:** Integratie E2E
**Prioriteit:** Hoog
**Sprint:** —
**Status:** ❓ Niet getoetst
**Aangemaakt:** 2026-04-09
**Afgeleid van:** NM-001 IJsselmeerkust gap-analyse (§2 + §3)

---

## Doel

Toetsen of een **beleidsadviseur** van gemeente Súdwest-Fryslân het volledige gebruikerspad kan afleggen: van gebiedsselectie → indicatoren verkennen → kernen vergelijken → tot onderbouwing voor beleid.

---

## Gebruikersprofiel

- **Rol:** Beleidsadviseur Leefbaarheid / Ruimtelijke Ordening
- **Domein:** Gemeente Súdwest-Fryslân
- **Doel:** Inzicht in bereikbaarheid, wonen en sociale situatie van IJsselmeerkust-kernen
- **Verwachting:** Vergelijking tussen kernen + onderbouwing voor beleidsnota

---

## Precondities

- Applicatie draait op staging of productie
- Dataset bevat Súdwest-Fryslân (CBS, RIVM)
- Geen specifieke technische kennis vereist bij testpersoon

---

## Scenario: Leefbaarheid IJsselmeerkust in kaart brengen

### Fase 1 — Oriëntatie

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 1 | Open applicatie | Kaart laadt met heel Nederland of Fryslân | ❓ |
| 2 | Navigeer naar Súdwest-Fryslân | Kaart zoomt in of gebied is filterbaar | ❓ |
| 3 | Selecteer **Makkum** | Gebied highlight, Kompas opent | ❓ |

### Fase 2 — Thema Verkeer & Bereikbaarheid

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 4 | Zoek indicator "afstand OV" of "bereikbaarheid" | Indicator vindbaar via Kompas of zoekfunctie | ⚠️ |
| 5 | Bekijk kaartlaag bereikbaarheid | Choropleth of netwerk-visualisatie | ⚠️ |
| 6 | Vergelijk met Workum | Benchmark zichtbaar | ⚠️ |

### Fase 3 — Thema Wonen

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 7 | Selecteer thema Wonen | Kompas toont wonen-indicatoren | ✅ |
| 8 | Bekijk betaalbaarheid | Waarde + toelichting zichtbaar | ⚠️ |
| 9 | Vergelijk Makkum vs. Workum | Benchmark-weergave | ⚠️ |

### Fase 4 — Thema Sociaal Domein

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 10 | Zoek participatiewet-indicator | Zichtbaar, met bron | ✅ |
| 11 | Controleer detailniveau | Kern-niveau beschikbaar | ⚠️ |
| 12 | Bekijk historische trend | Tijdreeks toonbaar | ⚠️ |

### Fase 5 — Afsluiting & Export

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 13 | Genereer rapport of export | PDF of tabelexport beschikbaar | ❌ |
| 14 | Controleer bronvermelding in output | CBS, RIVM, peildatum vermeld | ❌ |

---

## Acceptatiecriteria

- [ ] Gebruiker kan zonder uitleg een buurt selecteren
- [ ] Kompas toont relevante indicatoren per thema
- [ ] Benchmark werkt bij 2+ geselecteerde gebieden
- [ ] Output (rapport of export) bevat bronvermelding en peildatum
- [ ] Geen technische fouten tijdens het hele pad

---

## Testdata

- **Gemeente:** Súdwest-Fryslân
- **Kernen:** Makkum, Workum, Koudum
- **Thema's:** Verkeer, Wonen, Sociaal domein

---

## Bevindingen / Opmerkingen

> *Samenvatting uit nulmeting NM-001:*
> De applicatie ondersteunt **verkennen**, maar nog niet **beslissen**.
> UX blokkeert effectief gebruik: geen duidelijke startflow, Z-scores niet uitgelegd, bronvermelding ontbreekt.

---

## Gerelateerde documenten

- [TC-01-001 Gebiedsselectie](../01-kaartmodule/TC-01-001_gebieds-selectie.md)
- [TC-02-001 Wonen indicatoren](../02-kompas-detail/TC-02-001_wonen-indicatoren.md)
- [TC-02-002 Sociaal domein](../02-kompas-detail/TC-02-002_sociaal-domein.md)
- [NM-001 Gap-analyse IJsselmeerkust](../nulmetingen/NM-001_ijsselmeerkust-gap-analyse.md)

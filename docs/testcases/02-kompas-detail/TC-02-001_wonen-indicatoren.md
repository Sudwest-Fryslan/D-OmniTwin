# TC-02-001 — Wonen: Indicatoren & Benchmark

**Module:** Kompas Detail
**Prioriteit:** Hoog
**Sprint:** —
**Status:** ⚠️ Gedeeltelijk werkend
**Aangemaakt:** 2026-04-09
**Afgeleid van:** NM-001 IJsselmeerkust gap-analyse (§3.3)

---

## Doel

Valideren dat het Kompas-paneel voor het thema **Wonen** correcte indicatoren toont, en dat de benchmarkfunctie bruikbaar is voor vergelijking tussen gebieden.

---

## Precondities

- Applicatie draait (lokaal of staging)
- Minimaal één buurt geselecteerd in Súdwest-Fryslân
- Kompas-paneel is geopend

---

## Teststappen

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 1 | Selecteer thema **Wonen** in Kompas | Kompas zoomt in op wonen-indicatoren | ✅ |
| 2 | Bekijk indicator **betaalbaarheid** | Indicator zichtbaar met waarde en toelichting | ⚠️ Indirect |
| 3 | Controleer bronvermelding | Bron (CBS / Kadaster) en peildatum zichtbaar | ❌ Ontbreekt |
| 4 | Controleer uitleg Z-score | Uitleg van de score voor eindgebruiker | ❌ Ontbreekt |
| 5 | Voeg tweede gebied toe (Workum) | Benchmark-vergelijking zichtbaar | ⚠️ Beperkt |
| 6 | Controleer historische trend | Tijdreeks van indicator zichtbaar | ❌ Ontbreekt |
| 7 | Controleer **starterswoningen** indicator | Aparte KPI zichtbaar | ❌ Ontbreekt |

---

## Acceptatiecriteria

- [ ] Wonen-indicatoren laden zonder foutmelding
- [ ] Bronvermelding en peildatum zichtbaar per indicator
- [ ] Z-scores voorzien van uitleg
- [ ] Benchmarkvergelijking werkt bij ≥2 geselecteerde gebieden
- [ ] Historische trend aanwezig (minimaal 3 jaar)

---

## Testdata

- Gemeente: **Súdwest-Fryslân**
- Gebieden: Makkum, Workum
- Indicatoren: betaalbaarheid, woningkwaliteit, starterswoningen

---

## Bevindingen / Opmerkingen

> *Uit nulmeting NM-001:* Wonen is het sterkste onderdeel qua bestaande data. Mist echter beleidsrelevante KPI's (starters, kwaliteit). Definitiemismatch bij "betaalbare woningen" (CBS vs. Kadaster definitie).

---

## Gerelateerde documenten

- [NM-001 Gap-analyse IJsselmeerkust](../nulmetingen/NM-001_ijsselmeerkust-gap-analyse.md)
- [TC-06-001 E2E Beleidsadviseur](../06-integratie-e2e/TC-06-001_beleidsadviseur-ijsselmeerkust.md)

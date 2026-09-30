# TC-02-002 — Sociaal Domein: Rondkomen

**Module:** Kompas Detail
**Prioriteit:** Middel
**Sprint:** —
**Status:** ⚠️ Gedeeltelijk werkend
**Aangemaakt:** 2026-04-09
**Afgeleid van:** NM-001 IJsselmeerkust gap-analyse (§3.4)

---

## Doel

Valideren dat het Kompas-paneel voor het thema **Rondkomen / Sociaal domein** bruikbare indicatoren toont, en dat het detailniveau geschikt is voor beleidssignalering.

---

## Precondities

- Applicatie draait (lokaal of staging)
- Minimaal één buurt geselecteerd in Súdwest-Fryslân
- Kompas-paneel is geopend

---

## Teststappen

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 1 | Zoek indicator **participatiewet** | Indicator vindbaar en zichtbaar | ✅ (CBS) |
| 2 | Controleer aggregatieniveau | Data beschikbaar op buurtniveau | ⚠️ Te grofmazig |
| 3 | Bekijk trendlijn | Tijdreeks zichtbaar (≥ 3 jaar) | ⚠️ Beperkt |
| 4 | Drill-down naar kernniveau | Detaildata per kern (Makkum, Workum) | ⚠️ Beperkt |
| 5 | Controleer vroegsignalering | Drempelwaarden of signaleringslogica zichtbaar | ❌ Ontbreekt |
| 6 | Zoek indicator **circulaire landbouw** | Indicator aanwezig | ❌ Ontbreekt |
| 7 | Zoek indicator **toerisme-initiatieven** | Indicator aanwezig | ❌ Ontbreekt |

---

## Acceptatiecriteria

- [ ] Participatiewet-indicator laadt correct
- [ ] Data beschikbaar op minimaal wijkniveau
- [ ] Trendlijn toont minimaal 2 meetmomenten
- [ ] Drempelwaarden of kleurcodering geeft signaal bij afwijkende waarden

---

## Testdata

- Gemeente: **Súdwest-Fryslân**
- Kernen: Makkum, Workum, Koudum
- Indicatoren: participatiewet, bijstandsgerechtigden

---

## Bevindingen / Opmerkingen

> *Uit nulmeting NM-001:* Data aanwezig (CBS), maar te grof voor vroegsignalering op kerniveau. Ontbrekende indicatoren (circulaire landbouw, toerisme) zijn niet via CBS beschikbaar — vereisen gemeentelijke of domein-dataspace-koppeling.

---

## Gerelateerde documenten

- [NM-001 Gap-analyse IJsselmeerkust](../nulmetingen/NM-001_ijsselmeerkust-gap-analyse.md)
- [TC-06-001 E2E Beleidsadviseur](../06-integratie-e2e/TC-06-001_beleidsadviseur-ijsselmeerkust.md)

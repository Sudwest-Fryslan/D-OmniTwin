# TC-01-002 — Meervoudige Gebiedsselectie

**Module:** Kaartmodule
**Prioriteit:** Hoog
**Sprint:** —
**Status:** ❓ Niet getoetst
**Aangemaakt:** 2026-04-09

---

## Doel

Valideren dat een gebruiker **meerdere gebieden gelijktijdig** kan selecteren, via:
1. Opeenvolgende klik-selectie van individuele buurten/wijken
2. Polygoontekening (lasso/vrije hand) over een kaartgebied

Het doel is dat de geselecteerde gebieden samen als **benchmarkset** beschikbaar komen in het Kompas-paneel.

---

## Precondities

- Applicatie draait (lokaal of staging)
- CBS buurt/wijk-laag actief
- Dataset bevat Súdwest-Fryslân

---

## Teststappen

### A — Meervoudige klik-selectie

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 1 | Klik op **Makkum** | Highlight + badge verschijnt | ❓ |
| 2 | Klik (additioneel) op **Workum** | Tweede gebied wordt toegevoegd aan selectie | ❓ |
| 3 | Klik op **Koudum** | Derde gebied wordt toegevoegd | ❓ |
| 4 | Controleer selectiebadge / indicator | Alle drie gebieden zichtbaar in overzicht | ❓ |
| 5 | Open Kompas-paneel | Benchmarkoverzicht van de drie gebieden | ❓ |
| 6 | Deselecteer één gebied | Alleen dat gebied verdwijnt uit selectie | ❓ |
| 7 | Wis gehele selectie | Alle highlights verdwijnen, kaart neutraal | ❓ |

### B — Polygoontekening (lasso-selectie)

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 1 | Activeer tekenmodus (draw/polygon tool) | Cursor verandert, UI geeft instructie | ❓ |
| 2 | Teken polygoon over Makkum, Workum en omgeving | Polygoon wordt getekend op kaart | ❓ |
| 3 | Sluit polygoon af (dubbelklik of enter) | Alle buurten binnen polygoon worden geselecteerd | ❓ |
| 4 | Controleer selectie-inhoud | Gebiedenlijst toont correct de buurten die overlappen | ❓ |
| 5 | Open Kompas | Benchmarkoverzicht van geselecteerde buurten | ❓ |
| 6 | Verwijder getekende polygoon | Selectie wordt gewist | ❓ |

---

## Acceptatiecriteria

- [ ] Minimaal 2 en maximaal N gebieden gelijktijdig selecteerbaar via klik
- [ ] Selectieindicator (badge/lijst) toont alle geselecteerde gebieden
- [ ] Kompas-paneel laadt benchmark voor alle geselecteerde gebieden
- [ ] Polygoontekening selecteert alle overlappende CBS-eenheden
- [ ] Selectie blijft stabiel bij pannen/zoomen van de kaart
- [ ] Wissen van selectie werkt volledig (geen resterende highlights)

---

## Testdata

- **Gemeente:** Súdwest-Fryslân
- **Kernen (klik):** Makkum, Workum, Koudum
- **Polygoon:** Gebied rondom IJsselmeerkust (omvat meerdere kernen)

---

## Bevindingen / Opmerkingen

> *Architectuurnotitie:* Polygoontekening vereist een ruimtelijke intersectie-query (polygon ∩ buurtgeometrie). Dit is realiseerbaar via PostGIS `ST_Intersects` op de kaartlaaggeometrie. Frontend tooling: Mapbox Draw of deck.gl DrawRectangleMode.

---

## Gerelateerde documenten

- [TC-01-001 Enkelvoudige gebiedsselectie](./TC-01-001_gebieds-selectie.md)
- [TC-01-003 Alternatieve gebiedslagen](./TC-01-003_alternatieve-gebiedslagen.md)
- [TC-06-001 E2E Beleidsadviseur](../06-integratie-e2e/TC-06-001_beleidsadviseur-ijsselmeerkust.md)

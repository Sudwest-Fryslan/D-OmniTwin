# TC-01-001 — Gebiedsselectie via Kaart

**Module:** Kaartmodule
**Prioriteit:** Hoog
**Sprint:** —
**Status:** ❓ Niet getoetst
**Aangemaakt:** 2026-04-09
**Afgeleid van:** NM-001 IJsselmeerkust gap-analyse (§3.1–3.5 stap 1)

---

## Doel

Valideren dat een gebruiker een gebied (gemeente, wijk, buurt) correct kan selecteren via de kaartinterface, en dat de UI hierop adequaat reageert.

---

## Precondities

- Applicatie draait (lokaal of staging)
- Dataset bevat minimaal gemeente Súdwest-Fryslân
- Kaart laadt zonder foutmelding

---

## Teststappen

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 1 | Navigeer naar de hoofdkaart | Kaart laadt volledig, geen consolefout | ❓ |
| 2 | Klik op een polygoon van Makkum | Gebied wordt visueel geactiveerd (highlight/border) | ❓ |
| 3 | Controleer selectiebadge | Badge verschijnt met naam van het geselecteerde gebied | ❓ |
| 4 | Klik op een tweede gebied (Workum) | Tweede gebied wordt toegevoegd of eerste wordt vervangen (afhankelijk van modus) | ❓ |
| 5 | Deselecteer via badge of kaart | Selectie verdwijnt, kaart keert terug naar neutrale staat | ❓ |

---

## Acceptatiecriteria

- [ ] Gebied-highlight zichtbaar na klikken
- [ ] Gebiedsnaam correct weergegeven in UI
- [ ] Geen crash of consolefout tijdens selectie
- [ ] Deselecteren werkt intuïtief

---

## Testdata

- Gemeente: **Súdwest-Fryslân**
- Kernen: Makkum, Workum, Koudum

---

## Bevindingen / Opmerkingen

> *Uit nulmeting NM-001:* Gebiedsselectie werkt, maar UX is onduidelijk — startpunt (kaart vs. thema) heeft geen duidelijke flow. Impact: **Hoog**.

---

## Gerelateerde documenten

- [NM-001 Gap-analyse IJsselmeerkust](../nulmetingen/NM-001_ijsselmeerkust-gap-analyse.md)
- [TC-06-001 E2E Beleidsadviseur](../06-integratie-e2e/TC-06-001_beleidsadviseur-ijsselmeerkust.md)

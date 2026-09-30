# TC-06-002 — Multi-Gebiedsdossier (Zones-analyse)

**Module:** Integratie E2E / Rapportmodule  
**Prioriteit:** Hoog  
**Sprint:** Volgende sessie (zie implementatieplan)  
**Status:** ❓ Nog te implementeren  
**Aangemaakt:** 2026-04-09

---

## Doel

Valideren dat de **Multi-Gebiedsdossier**-rapportpagina correct werkt voor een set geselecteerde CBS-buurten (bijv. via een omgevingsvisie-deelgebied). De pagina moet twee beleidsrelevante vragen beantwoorden:

1. Welke buurten in de selectie wijken het **sterkst af** van het referentiegemiddelde, en op welke indicator?
2. Hoe scoort de **totale selectie** per thema t.o.v. de referentiegroep?

---

## Persona

**Thomas de Vries**, beleidsmedewerker gemeente SWF  
— Werkt aan de uitvoeringsparagraaf van de omgevingsvisie voor het IJsselmeergebied  
— Wil weten: "Waar liggen de kwetsbaarheden in dit deel van onze gemeente?"

---

## Precondities

- Applicatie draait
- Omgevingsvisie-deelgebieden zijn geladen (✅ geïmplementeerd)
- Multi-Gebiedsdossier backend endpoints beschikbaar (`POST /api/report/multi-gebied`)
- Admin panel gebouwd met `MultiGebiedPage.tsx`

---

## Teststappen

### A — Rapportpagina openen via omgevingsvisie

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 1 | Activeer **Omgevingsvisie SWF** laag → klik **IJsselmeergebied** | 44 buurten geselecteerd | ❓ |
| 2 | Open **Rapport**-tab → klik **Analyseer Selectie** | Modal toont 3 opties: Gebiedsdossier, Benchmark, Multi-Gebiedsdossier | ❓ |
| 3 | Klik **Multi-Gebiedsdossier** | Nieuwe tab opent: `/admin/rapport/multi-gebied?gebieden=...&naam=IJsselmeergebied` | ❓ |
| 4 | Pagina laadt volledig | Header toont "Multi-Gebiedsdossier: IJsselmeergebied (44 buurten)" | ❓ |

### B — Z-score Afwijkingskaart

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 1 | Choropleth laadt | Buurten ingekleurd van grijs (in lijn) tot rood (sterk afwijkend) | ❓ |
| 2 | Hover over **Allingawier** | Tooltip: "Allingawier · stijgt het sterkst af op [indicator] (z=X.X) · Thema: [...]" | ❓ |
| 3 | Schakel referentie: **Gemeente → Fryslân** | Kaart herlaadt met andere kleurverdeling | ❓ |
| 4 | Schakel terug naar **Gemeente** | Originele kleuren hersteld | ❓ |

### C — Uitschietertabel

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 1 | Tabel zichtbaar met rankings | Kolommen: #, Buurt, Thema, Indicator, Z-score, Impact | ❓ |
| 2 | Klik op **Z-score** kolom header | Tabel sorteert op absolute z-score (sterkste afwijking bovenaan) | ❓ |
| 3 | Klik op **Thema** kolom header | Tabel groepeert/sorteert op thema | ❓ |
| 4 | Klik **Download CSV** | Browser downloadt `multi-gebiedsdossier_IJsselmeergebied.csv` | ❓ |

### D — Thema Aggregaat

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 1 | Thema-sectie zichtbaar | Horizontale bars per kompas-thema met gemiddelde z-score | ❓ |
| 2 | Rood thema zichtbaar | Thema met hoogste gemiddelde afwijking is duidelijk herkenbaar | ❓ |
| 3 | Tooltip/label bij een bar | "8 buurten met significante afwijking (|z|>1)" | ❓ |

### E — Export & Print

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 1 | Klik **Exporteer PDF** | Print-dialoog opent, layout klopt (geen sidebar, correcte marges) | ❓ |
| 2 | Controleer printtitel | Bestandsnaam suggereert deelgebiednaam + datum | ❓ |

---

## Acceptatiecriteria

- [ ] Choropleth laadt correct voor 44+ buurten
- [ ] Kleur per buurt gebaseerd op MAX absolute z-score over alle indicatoren
- [ ] Tooltip toont: buurt, indicator, z-score waarde, thema
- [ ] Referentie toggle gemeente ↔ Fryslân herladen data zonder page refresh
- [ ] Uitschietertabel sorteerbaar op minimaal z-score en thema
- [ ] CSV exporteert alle buurten met indicator + z-score
- [ ] Print-layout is helder en professioneel
- [ ] Pagina werkt ook zonder `window.opener` (zelfstandig te openen via URL)

---

## Gerelateerde documenten

- [PLAN Multi-Gebiedsdossier](../04-rapportage/PLAN_multi-gebiedsdossier.md) ← implementatieplan
- [TC-01-003 Alternatieve gebiedslagen](../01-kaartmodule/TC-01-003_alternatieve-gebiedslagen.md)
- [TC-06-001 E2E Beleidsadviseur IJsselmeerkust](./TC-06-001_beleidsadviseur-ijsselmeerkust.md)
- [NM-001 Gap-analyse IJsselmeerkust](../nulmetingen/NM-001_ijsselmeerkust-gap-analyse.md)

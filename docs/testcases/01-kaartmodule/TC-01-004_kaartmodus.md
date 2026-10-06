# TC-01-004 — Kaartmodus: percentielklasse, label A–E, werkelijke waarde, uit

**Module:** Kaartmodule
**Prioriteit:** Hoog
**Status:** ✅ geautomatiseerd (`tests/e2e/test_kaartmodus.py`)
**Aangemaakt:** 2026-10-03
**Afgeleid van:** [#255](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/255), [#256](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/256) (stap 5), gat-analyse huidige gebiedsmonitor (#4, #5, #6)

---

## Doel

Een indicator op de kaart tonen als percentielklasse (8 × 12,5%), als werkelijke waarde met klassen in de legenda, of zonder kleuring. Methodiek: [percentielklasse_methodiek.md](../../3-data-engineering/percentielklasse_methodiek.md), [labels_methodiek.md](../../3-data-engineering/labels_methodiek.md).

## Precondities

- Verse stack met `LOAD_SAMPLE_DATA=true`; gemeente Súdwest-Fryslân, CBS-buurten
- Indicator *Stedelijk hitte-eiland effect* (use case hittestress), focus Bolsward-Zuidoost (BU19000002)

## Teststappen

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 1 | Laad CBS-buurten met de indicator, open **Legenda** | Modus *Werkelijke waarde* staat aan; de legenda toont per kleur het bereik in °C en het aantal gebieden | ✅ |
| 2 | Kies **Percentielklasse** | Legenda met 8 klassen ("klasse 1: 0–12,5% (ongunstigst)" … "klasse 8: 87,5–100% (gunstigst)"), rood → blauw; tooltip toont "Percentielklasse n van 8" | ✅ |
| 3 | Kies **Uit** | Buurten grijs, legenda meldt "Kaartkleuring staat uit"; de indicator blijft gekozen | ✅ |
| 4 | Kies **Werkelijke waarde** | De kleuring en de legenda met bereik komen terug | ✅ |
| 5 | Kies **Label A–E** | Legenda met 5 labels ("label A (gunstigst), kwintiel 80–100%" … "label E (ongunstigst), kwintiel 0–20%"), blauw → rood, en de melding "Voorlopige drempels (kwintielen)"; elke buurt met data heeft een label; tooltip "Label B (voorlopig, kwintielen)" | ✅ |

## Acceptatiecriteria

- [x] Elke modus is één klik; de keuze blijft bewaard bij een volgende indicator
- [x] Percentielkleuren zijn kleurenblindvriendelijk (geen rood-groen)
- [x] Geen consolefouten

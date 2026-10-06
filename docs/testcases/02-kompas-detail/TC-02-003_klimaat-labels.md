# TC-02-003 — Klimaat Kompas met labels A–E

**Module:** Kompas Detail
**Prioriteit:** Hoog
**Status:** ✅ geautomatiseerd (`tests/e2e/test_kaartmodus.py`, `test_tc_02_003_klimaat_kompas_labels`)
**Aangemaakt:** 2026-10-04
**Afgeleid van:** [#256](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/256), gat-analyse huidige gebiedsmonitor (Must #4)

---

## Doel

Het Klimaat Kompas is op een verse installatie gevuld en toont per indicator en per thema een label A–E, met een legenda en, zolang SWF de drempels niet heeft vastgesteld, de melding "Voorlopige drempels (kwintielen)". Methodiek: [labels_methodiek.md](../../3-data-engineering/labels_methodiek.md).

## Precondities

- Verse stack met `LOAD_SAMPLE_DATA=true` (use cases hittestress en sample-bronbibliotheek); gemeente Súdwest-Fryslân, CBS-buurten
- Focus Bolsward-Zuidoost (BU19000002)

## Teststappen

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 1 | Selecteer Bolsward-Zuidoost, open het Kompas | Het standaardprofiel (Volledig Kompas) verschijnt | ✅ |
| 2 | Kies configuratie **Klimaat Kompas** | Kwadrant Klimaat met de thema's Hittestress, Hemelwateroverlast en Droogte; "Kleur: label A–E" en een legenda A–E | ✅ |
| 3 | Bekijk de segmenten | Elk thema en elke indicator met data heeft een label ("B · Hittestress") en de kleur van dat label; tooltip "Label B (voorlopig, kwintielen)" | ✅ |
| 4 | Lees de melding onder de legenda | "Voorlopige drempels (kwintielen) …" | ✅ |

## Acceptatiecriteria

- [x] Labels kleurenblindvriendelijk (A blauw, E rood) en ook als letter zichtbaar
- [x] Themalabel volgens de gewogen aggregatie van de indicatorscores
- [x] Geen consolefouten

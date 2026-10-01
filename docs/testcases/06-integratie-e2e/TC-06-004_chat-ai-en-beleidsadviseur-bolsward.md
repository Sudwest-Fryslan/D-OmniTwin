# TC-06-004 — E2E: Chat (AI) en beleidsadviseur, Bolsward-Zuidoost

**Module:** Integratie E2E
**Prioriteit:** Middel
**Sprint:** —
**Status:** ✅ Geautomatiseerd (stap 1-4 alleen met LLM)
**Aangemaakt:** 2026-10-01
**Afgeleid van:** #88 (LLM-koppeling, providervergelijking), TC-06-001 (onboarding beleidsadviseur)

---

## Doel

Toetsen of een **beleidsadviseur** vanuit een geselecteerde buurt de D-Omni Assistent kan gebruiken: een vrije vraag krijgt een herkenbaar AI-antwoord met een kaartactie, en het scenario Beleidsadviseur leidt naar het Kompas van dezelfde buurt.

---

## Gebruikersprofiel

- **Rol:** Beleidsadviseur Leefbaarheid / Ruimtelijke Ordening
- **Domein:** Gemeente Súdwest-Fryslân
- **Doel:** Snel een beeld van één buurt (groen) en doorstappen naar de indicatoren
- **Verwachting:** Duidelijk welk antwoord van een taalmodel komt; vaste, voorspelbare onboarding

---

## Precondities

- Stack draait met de sample dataset (bevat Bolsward-Zuidoost, `BU19000002`)
- LLM geconfigureerd (lokaal Ollama of een aanbieder via de LiteLLM-gateway, zie `scripts/llm/kies_provider.py`); alleen nodig voor stap 1-4
- Welkomstmodal al gezien (anders eerst sluiten)

---

## Scenario

### Deel A — Vrije vraag aan de Assistent (LLM-afhankelijk)

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 1 | Kaartconfiguratie: CBS Buurten tonen, klik op **Bolsward-Zuidoost** | Buurt geselecteerd, selectiebadge toont Bolsward-Zuidoost | ✅ |
| 2 | Open de **D-Omni Assistent**, vraag "Hoe groen is Bolsward-Zuidoost?" | Antwoord met label **🤖 AI-gegenereerd** en disclaimer "Dit antwoord is AI-gegenereerd…" | ✅ |
| 3 | Lees het antwoord | Kort Nederlands antwoord over groen in Bolsward-Zuidoost | ✅ |
| 4 | Bekijk de actieknoppen | Knop **Toon: Bolsward-Zuidoost** (type `TOON_OP_KAART`) die de groenindicator op de kaart toont | ⚠️ |

### Deel B — Scenario Beleidsadviseur (deterministisch)

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 5 | Typ "Ik ben beleidsadviseur" | Vaste scenariotekst over de IJsselmeerkust (Súdwest-Fryslân), zonder AI-label | ✅ |
| 6 | Bekijk de actieknoppen | **Toon: Buurten**, **Gemeente: Súdwest-Fryslân**, **Open het D-Omni Kompas** | ✅ |

### Deel C — Kompas (deterministisch)

| # | Actie | Verwacht resultaat | Status |
|---|-------|--------------------|--------|
| 7 | Klik **Open het D-Omni Kompas** | Kompas-venster opent | ✅ |
| 8 | Bekijk de kop van het Kompas | Bolsward-Zuidoost, **Indicatordekking: 100%**, zonnediagram geladen | ✅ |

---

## LLM-afhankelijk versus deterministisch

| Stap | Bron | Toetsing |
|---|---|---|
| 1 | Kaart | strikt |
| 2-4 | LLM (`debug.mode = intelligent_dispatcher`) | alleen de vorm: label, disclaimer, Nederlands, niet leeg, minstens één `TOON_OP_KAART`-actie die naar Bolsward-Zuidoost verwijst (label of id). Tekst en gekozen acties verschillen per model en per run |
| 5-6 | Vast scenario uit `chat_scenarios` (trefwoord "beleidsadviseur", `debug.mode = deterministic_scenario`) | strikt |
| 7-8 | Kompas | strikt |

Zonder werkend LLM valt de chat terug op regels (`debug.mode = legacy_fallback`, of een foutmelding in de tekst). Stap 2-4 worden dan overgeslagen, met de reden in de skip-melding.

---

## Acceptatiecriteria

- [x] Een AI-antwoord is altijd herkenbaar (label + disclaimer); het vaste scenario niet
- [x] Het scenario Beleidsadviseur werkt zonder LLM
- [x] "Open het D-Omni Kompas" vanuit de chat toont het Kompas van de geselecteerde buurt
- [ ] De kaartactie uit het AI-antwoord toont een bestaande indicator (zie bevindingen)
- [x] Geen consolefouten in deel B en C

---

## Testdata

- **Buurt:** Bolsward-Zuidoost (`BU19000002`), gemeente Súdwest-Fryslân
- **Vragen:** "Hoe groen is Bolsward-Zuidoost?", "Ik ben beleidsadviseur"

---

## Bevindingen / Opmerkingen

> *2026-10-01, sample dataset, `qwen3:4b-instruct` via de gateway:*
> - Stap 4: het model geeft `🗺 Toon: Bolsward-Zuidoost` met als `indicator_uuid` de buurtcode `BU19000002` in plaats van een indicator-uuid. De zoekstap vindt in de sample geen indicatoren (`indicatoren: []`), dus het model heeft geen uuid om te kiezen. De knop kan zo geen groenindicator tonen. Daarom ⚠️ en niet in de test geëist.
> - Stap 7-8: de chatknop opende het Kompas-venster zonder de kaartselectie te laden (het venster bleef op "Volledig Kompas"). Opgelost in `static/js/kompas.js`: dezelfde logica als de knop **Open Kompas** in het zijpaneel.

---

## Gerelateerde documenten

- [TC-06-001 Beleidsadviseur IJsselmeerkust](./TC-06-001_beleidsadviseur-ijsselmeerkust.md)
- [LLM-providervergelijking](../llm-vergelijking/)
- [ADR 0001 LLM-koppeling](../../2-architectuur/adr/0001-llm-koppeling-openai-standaard.md)

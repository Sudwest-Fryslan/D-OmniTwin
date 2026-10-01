# Testcases — D-OmniTwin

> **Rol:** Kwaliteitsborging & acceptatietoetsing | Nulmetingen | Functionele validatie  
> **Beheer:** Updaten bij nieuwe features of sprintafsluiting

---

## 🧭 Structuur

```
testcases/
├── README.md                          ← dit bestand
│
├── 01-kaartmodule/                    ← Kaart, selectie, kaartlagen
├── 02-kompas-detail/                  ← Kompas-paneel, indicatoren, benchmark
├── 03-ai-assistent/                   ← Chat, onboarding, RAG
├── 04-rapportage/                     ← Rapportgeneratie, export, implementatieplannen
├── 05-admin-panel/                    ← Ontologie, beheer
├── 06-integratie-e2e/                 ← End-to-end gebruikersscenario's
│
└── nulmetingen/                       ← Baseline-metingen per use case / regio
```

---

## 📋 Documenttypes

| Prefix | Type | Beschrijving |
|--------|------|-------------|
| `TC-XX-XXX` | Testcase | Functionele stap-voor-stap toets |
| `NM-XXX` | Nulmeting | Baseline gap-analyse per domein of regio |
| `PLAN_*` | Implementatieplan | Uitgewerkt plan klaar voor volgende sprint/sessie |

---

## 🏷️ Naamgeving

```
TC-[module-nr]-[volgnr]_[beschrijvende-naam-kebab-case].md
NM-[volgnr]_[beschrijvende-naam-kebab-case].md
PLAN_[beschrijvende-naam-kebab-case].md
```

---

## 📄 Statuslegenda

| Symbool | Betekenis |
|---------|-----------|
| ✅ | Werkt correct / geïmplementeerd |
| ⚠️ | Gedeeltelijk / beperkt |
| ❌ | Ontbreekt / werkt niet |
| ❓ | Onzeker / niet getoetst |
| 📋 | Klaar voor uitvoering (gepland) |

---

## 📁 Index

### Kaartmodule (01)
| ID | Naam | Status |
|----|------|--------|
| [TC-01-001](./01-kaartmodule/TC-01-001_gebieds-selectie.md) | Enkelvoudige gebiedsselectie via kaart | ❓ |
| [TC-01-002](./01-kaartmodule/TC-01-002_meervoudige-selectie.md) | Meervoudige selectie (klik + polygoon) | ❓ |
| [TC-01-003](./01-kaartmodule/TC-01-003_alternatieve-gebiedslagen.md) | Alternatieve gebiedslagen (omgevingsvisie ✅, BAG ❓, woonbeleid ❓) | ✅/❓ |

### Kompas Detail (02)
| ID | Naam | Status |
|----|------|--------|
| [TC-02-001](./02-kompas-detail/TC-02-001_wonen-indicatoren.md) | Wonen — indicatoren & benchmark | ⚠️ |
| [TC-02-002](./02-kompas-detail/TC-02-002_sociaal-domein.md) | Sociaal domein — rondkomen | ⚠️ |

### Rapportage (04)
| Document | Naam | Status |
|----------|------|--------|
| [PLAN_multi-gebiedsdossier](./04-rapportage/PLAN_multi-gebiedsdossier.md) | Implementatieplan Multi-Gebiedsdossier | 📋 Klaar voor uitvoering |

### Integratie E2E (06)
| ID | Naam | Status |
|----|------|--------|
| [TC-06-001](./06-integratie-e2e/TC-06-001_beleidsadviseur-ijsselmeerkust.md) | Beleidsadviseur — IJsselmeerkust & Wadden | ❓ |
| [TC-06-002](./06-integratie-e2e/TC-06-002_multi-gebiedsdossier.md) | Multi-Gebiedsdossier — Zones-analyse | 📋 Nog te implementeren |
| [TC-06-003](./gebiedsagenda_ijselmeerkust/TC-06-003_gebiedsagenda_ijsselmeerkust_usecase.md) | Integraal Gebiedsgericht Werken — IJsselmeergebied-Wadden | 🧪 Toetsbaar |

### Nulmetingen & Reviews
| ID / Document | Naam | Regio / Focus |
|---|---|---|
| [NM-001](./nulmetingen/NM-001_ijsselmeerkust-gap-analyse.md) | Gap-analyse IJsselmeerkust | Súdwest-Fryslân |
| [Gebruikersreview](./Gebruikersreview.md) | Review langs 5 gebruikersprofielen | Gebruikerservaring & begrijpelijkheid |

---

## 🤖 Automatisering

Browser-E2E-tests (Playwright) in [`tests/e2e/`](../../tests/e2e/README.md), draaiend op de sample dataset (`pytest -m e2e tests/e2e`). De sample bevat geen Makkum; de tests gebruiken Workum, Koudum en Hindeloopen.

Status: **geautomatiseerd** = alle stappen · **gedeeltelijk** = een deel van de stappen, rest in de tabel toegelicht · **handmatig** = niet te automatiseren (skip met reden) · **xfail** = test toetst iets dat ontbreekt of een bekende bug; slaagt hij onverwacht, dan faalt de run.

| TC | Test | Status |
|----|------|--------|
| TC-01-001 | `test_tc_01_001_gebiedsselectie` (echte klikken op het kaartcanvas) | geautomatiseerd |
| TC-01-002 A | `test_tc_01_002a_meervoudige_klikselectie` | geautomatiseerd |
| TC-01-002 B | `test_tc_01_002b_polygoonselectie` | handmatig (skip: lassoselectie bestaat nog niet) |
| TC-01-003 A | `test_tc_01_003a_omgevingsvisie` | handmatig (skip: omgevingsvisie niet in sample) |
| TC-01-003 B | `test_tc_01_003b_bag_woonplaatsen` | geautomatiseerd (vereist PDOK, anders skip) |
| TC-01-003 C | `test_tc_01_003c_woonbeleid` | handmatig (skip: dataset nog niet beschikbaar) |
| TC-02-001 stap 1-3 | `test_tc_02_001_wonen_indicatoren` | gedeeltelijk: energielabel i.p.v. betaalbaarheid (niet in sample) |
| TC-02-001 stap 4 | `test_tc_02_001_uitleg_zscore` | handmatig (subjectief) |
| TC-02-001 stap 5 | `test_tc_02_001_benchmark_twee_gebieden` | geautomatiseerd |
| TC-02-001 stap 6 | `test_tc_02_001_historische_trend` | xfail: één meetmoment in sample |
| TC-02-001 stap 7 | `test_tc_02_001_starterswoningen` | xfail: indicator ontbreekt |
| TC-02-002 stap 1-2 | `test_tc_02_002_participatiewet` | gedeeltelijk: via Kompas-navigatie; zoeken met de Kompas-zoekbalk vereist de LLM-stack |
| TC-02-002 stap 3 | `test_tc_02_002_trendlijn` | xfail: één meetmoment in sample |
| TC-02-002 stap 4 | `test_tc_02_002_drilldown_kernen` | geautomatiseerd |
| TC-02-002 stap 5 | `test_tc_02_002_vroegsignalering` | handmatig (skip: bestaat nog niet) |
| TC-02-002 stap 6-7 | `test_tc_02_002_ontbrekende_indicatoren` | xfail: indicatoren ontbreken |
| TC-06-001 fase 1, 3, 4 | `test_tc_06_001_beleidsadviseur_ijsselmeerkust` | gedeeltelijk: onboarding via Assistent (help → Beleidsadviseur → acties), Workum/Koudum i.p.v. Makkum/Workum |
| TC-06-001 fase 2 | `test_tc_06_001_fase2_verkeer_bereikbaarheid` | xfail: Verkeer heeft geen indicatoren in sample |
| TC-06-001 stap 11-12 | `test_tc_06_001_handmatige_review` | handmatig |
| TC-06-001 stap 13 (PDF) | `test_tc_06_001_pdf_rapport` | handmatig (skip: gebiedsdossier gebruikt de LLM) |
| TC-06-001 stap 13-14 (CSV) | geautomatiseerd (bug in export gerepareerd) |
| TC-06-002, TC-06-003 | — | nog niet geautomatiseerd |

---

## 🚀 Volgende Sessie — Prioriteiten

1. **Multi-Gebiedsdossier** bouwen — zie [PLAN_multi-gebiedsdossier.md](./04-rapportage/PLAN_multi-gebiedsdossier.md)
2. TC-06-002 uitvoeren na implementatie
3. TC-01-001 en TC-01-002 daadwerkelijk toetsen in browser

---

*Laatste update: 2026-04-09*

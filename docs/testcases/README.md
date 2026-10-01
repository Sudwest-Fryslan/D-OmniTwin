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
| [TC-06-005](../../usecases/energiearmoede/README.md) | Use case energiearmoede (Bolsward) | ⚠️ |
| [TC-06-006](../../usecases/hittestress/README.md) | Use case hittestress (Bolsward) | ⚠️ |
| [TC-06-007](../../usecases/brede-welvaart/README.md) | Use case brede welvaart (Bolsward) | ⚠️ |
| [TC-06-008](../../usecases/sociale-cohesie/README.md) | Use case sociale cohesie (Bolsward) | ⚠️ |

De use cases zijn **bundels van data, inrichting en stappen** en staan in [`usecases/`](../../usecases/README.md).

### Nulmetingen & Reviews
| ID / Document | Naam | Regio / Focus |
|---|---|---|
| [NM-001](./nulmetingen/NM-001_ijsselmeerkust-gap-analyse.md) | Gap-analyse IJsselmeerkust | Súdwest-Fryslân |
| [Gebruikersreview](./Gebruikersreview.md) | Review langs 5 gebruikersprofielen | Gebruikerservaring & begrijpelijkheid |

---

## 🚀 Volgende Sessie — Prioriteiten

1. **Multi-Gebiedsdossier** bouwen — zie [PLAN_multi-gebiedsdossier.md](./04-rapportage/PLAN_multi-gebiedsdossier.md)
2. TC-06-002 uitvoeren na implementatie
3. TC-01-001 en TC-01-002 daadwerkelijk toetsen in browser

---

*Laatste update: 2026-04-09*

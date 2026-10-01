# Use cases

Een use case is altijd een **bundel van drie dingen**:

1. **Data:** welke bron-indicatoren, voor welke gebieden en jaargangen.
2. **Inrichting:** de stuurinformatie: indicatorset, richting (hoger of lager is beter), Kompas-profiel, chatscenario.
3. **Stappen:** wat de gebruiker doet en wat hij dan verwacht te zien.

Per use case één map:

```
usecases/<naam>/
├── usecase.json       ← data + inrichting + verwachte uitkomst (machineleesbaar)
├── README.md          ← persona, stappen, resultaat (de testcase)
└── data/waarden.csv   ← optioneel: extra brondata, formaat als de sample (echte data, of bron=DEMO)
```

**Laden:** `python init_data/scripts/laad_usecase.py <naam> [...]` of `--alle`. Bij een verse installatie met `LOAD_SAMPLE_DATA=true` laadt `db-init` alle pakketten automatisch.

Een pakket ligt **bovenop de sample** (`init_data/sample`: gebieden, geometrie, algemene stuurdata) en doet drie dingen:
1. de richting van de indicatoren zetten (hoger of lager is beter);
2. afgeleide indicatoren berekenen uit bestaande brondata, bijvoorbeeld `65+ jaar ÷ Inwoners`, voor alle gebieden in de database;
3. extra brondata laden uit `data/waarden.csv`, als die er is.

Laden is idempotent, en pakketten zijn te combineren.

`tests/integration/test_usecases.py` leest de `usecase.json`-bestanden. Een nieuwe use case is dus een nieuwe map, zonder testcode te wijzigen.

| ID | Use case | Persona | Kompas-profiel | Status |
|---|---|---|---|---|
| [TC-06-007](./brede-welvaart/README.md) | Brede welvaart en functiemenging | Strateeg / economische zaken | Volledig Kompas | ⚠️ |
| [TC-06-005](./energiearmoede/README.md) | Energietransitie en energiearmoede | Beleidsmaker energietransitie | — | ⚠️ |
| [TC-06-006](./hittestress/README.md) | Klimaatadaptatie: hittestress en kwetsbaarheid | Stedenbouwkundige / GGD | Klimaat Kompas | ⚠️ |
| [TC-06-008](./sociale-cohesie/README.md) | Zorgzwaarte en sociale cohesie | Wijkcoördinator / wijkcontactfunctionaris | Volledig Kompas | ⚠️ |

De vier use cases komen uit de innovatieaanvraag Digitale Overheid 2026. Ze zijn nagespeeld op Bolsward, met focus op Bolsward-Zuidoost.

**Volgende stap:** ook een Kompas-profiel en een chatscenario per use case laden, als stuurdata (zie #137 voor de scheiding tussen stuur- en brondata, en #138 voor de ontbrekende brondata).

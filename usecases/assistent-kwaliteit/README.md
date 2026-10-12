# TC-06-009 — D-Omni Assistent vindt de juiste indicator en beantwoordt datavragen

**Status:** ontwerp (wordt actief zodra de uitvoerder chat-controles draait, #225; tot dan toetst tests/integration/test_assistent_kwaliteit.py alles) · **Versie:** 0.1.0 · **Afhankelijk van:** geen (stack met sample-data, `LOAD_SAMPLE_DATA=true`)
**Manifest:** [`usecase.json`](usecase.json) · **Controleren:** `python -m omnitwin.usecases controleer assistent-kwaliteit`
**Issue:** https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/233

## Vraag

- **Gebruiker:** beleidsadviseur of inwoner die de assistent gebruikt
- **Vraag:** "Als ik in gewone taal vraag 'hoeveel % is bejaard bij mij in de buurt?', krijg ik dan het cijfer voor mijn buurt met bron en jaar, en bij een zoekvraag alleen indicatoren die er echt bij passen?"

Aanleiding: op die vraag gaf de assistent acht indicatoren met een percentage erachter ("Oppervlak groen per inwoner 56%", "80 jaar of ouder (%) 53%", "Bouwjaar voor 1915 53%", ...). Het percentage was de gelijkenis van het zoekmodel, geen datawaarde, en de helft van de lijst had niets met ouderen te maken.

## Hoe de assistent nu werkt

1. **Datavraag of zoekvraag.** "Hoeveel", "wat is ... in", "hoe staat het met" en dergelijke zijn datavragen (`services/chat_datavraag.py`). "Bij mij in de buurt", "mijn wijk" en "hier" betekenen de buurt die op de kaart geselecteerd is; zonder selectie vraagt de assistent welke buurt.
2. **Indicator zoeken** (`services/zoektaal.py`), drie wegen samen:
   - **begrippen en synoniemen** uit [`db/stuurdata/synoniemen.json`](../../db/stuurdata/synoniemen.json) (SKOS-achtig: `prefLabel`, `altLabel`, indicatoren): "bejaard" → bejaarden → 65+ jaar (%) en 80 jaar of ouder (%);
   - **woorden uit de naam**: "energielabels" → Gemiddeld energielabel;
   - **betekenis**: embeddings met het meertalige model `intfloat/multilingual-e5-small` van naam, kompaspad, eenheid, synoniemen en beschrijving.
3. **Afkappen.** Alleen resultaten dicht bij de beste (liever 2 goede dan 8 matige); niets als niets goed past.
4. **Antwoord.** Bij een datavraag het cijfer voor de buurt, met bron en jaar, en de buren ter vergelijking; de gevonden indicator staat eronder als onderbouwing. Relevantie staat er als woord bij (sterk, matig), niet als percentage.

## Stappen

1. Start een verse stack met sample-data (zie [installatie](../../docs/9-beheer/installatie.md)).
2. Meet de kwaliteit: `python scripts/ai/evalueer_assistent.py --url http://localhost` (alle vragen uit [`tests/data/assistent_evaluatie.json`](../../tests/data/assistent_evaluatie.json), met drempels).
3. Voer de controles uit: `OMNITWIN_BASE_URL=http://localhost pytest -m integration tests/integration/test_assistent_kwaliteit.py`.
4. In de viewer: selecteer Bolsward-Zuidoost, open de assistent en vraag "hoeveel % is bejaard bij mij in de buurt?".

## Acceptatiecriteria

| # | Type | Wat | Verwacht |
|---|---|---|---|
| 1 | evaluatie | 111 vragen (87 afgestemd, 24 holdout; set 1.2) | afgestemd: precision@3 ≥ 0,7, recall@3 ≥ 0,8, MRR ≥ 0,8, routering ≥ 0,9; holdout: precision@3 ≥ 0,4, recall@3 ≥ 0,5, MRR ≥ 0,5, routering ≥ 0,5 |
| 2 | api | `GET /api/ai/kompas/search?q=senioren&limit=3` (anoniem) | 65+ jaar (%) bovenaan, relevantie sterk |
| 3 | api | `GET /api/ai/kompas/search?q=minima&limit=3` (anoniem) | Huishoudens met laag inkomen bovenaan |
| 4 | api | `GET /api/ai/kompas/search?q=wateroverlast&limit=3` (anoniem) | Verwerken hemelwater exc. schade bovenaan |
| 5 | api | `GET /api/ai/kompas/search?q=huizenprijzen&limit=3` (anoniem) | Gemiddelde WOZ-waarde bovenaan |
| 6 | api | `GET /api/ai/kompas/search?q=eenzaam&limit=3` (anoniem) | Eenzaamheid bovenaan |
| 7 | api | `GET /api/ai/kompas/search?q=fietsendiefstal&limit=3` (anoniem) | diefstal fiets bovenaan |
| 8 | chat | "hoeveel % is bejaard in Bolsward-Zuidoost?" | "Bolsward-Zuidoost: 29,5% (2026)", bron CBS Kerncijfers, indicator 65+ jaar (%) |
| 9 | chat | "hoeveel % is bejaard bij mij in de buurt?" zonder selectie | "Welke buurt is jouw buurt?" met de gevonden indicator; in de viewer een veld voor postcode of adres en "Gebruik mijn locatie" (#336) |
| 10 | viewer | Bolsward-Zuidoost geselecteerd, dezelfde vraag | 65+ jaar (%) en 80 jaar of ouder (%) voor Bolsward-Zuidoost met bron en jaar; "Onderbouwing: 2 indicatoren", relevantie "sterk", geen percentage |

## Resultaat (#233, verse stack met sample-data)

| | precision@3 | recall@3 | MRR | routering |
|---|---|---|---|---|
| voor (all-MiniLM-L6-v2, alleen vectoren), alle 82 vragen | 0,228 | 0,341 | 0,421 | 0,667 |
| na (e5-small, begrippen + naam + betekenis), alle 82 vragen | 0,890 | 0,884 | 0,927 | 1,000 |
| voor, alleen de 18 holdout-vragen | 0,185 | 0,278 | 0,314 | – |
| na, alleen de 18 holdout-vragen | 0,602 | 0,722 | 0,722 | – |

Gemiddeld getoonde indicatoren: van 9,0 naar 1,9. De holdout-vragen zijn niet gebruikt om synoniemen en drempels af te stemmen; ze laten zien wat de assistent doet met woorden die niemand vooraf heeft ingevoerd. Ter vergelijking: dezelfde aanpak met het oude Engelstalige model haalt op de holdout-vragen MRR 0,24-0,43.

## Resultaat (#336, verse stack met sample-data, evaluatieset 1.2)

De 20 holdout-vragen van set 1.1 zijn gebruikt om synoniemen aan te vullen (`holdout_1_1` in de testset). Daarvoor in de plaats kwamen 24 nieuwe holdout-vragen, vastgelegd vóór het afstemmen (eigen commit). De drempels gelden voor de afgestemde vragen; de holdout heeft eigen, lagere drempels tegen terugval. Anders dwingt elke nieuwe holdout-vraag die faalt tot afstemmen op die vraag.

| | precision@3 | recall@3 | MRR | routering |
|---|---|---|---|---|
| C dicht, voor (main), alle 111 vragen | 0,733 | 0,715 | 0,770 | 0,889 |
| C dicht, na, alle 111 vragen | 0,830 | 0,865 | 0,887 | 0,889 |
| C dicht, na, afgestemd (87) | 0,931 | 0,943 | 0,971 | 1,000 |
| C dicht, voor → na, holdout (24) | 0,472 → 0,465 | 0,562 → 0,583 | 0,583 → 0,583 | 0,500 → 0,500 |
| C open, na, alle 111 vragen | 0,868 | 0,922 | 0,940 | 0,889 |
| C open, na, holdout (24) | 0,583 | 0,792 | 0,743 | 0,500 |

De synoniemen helpen vooral de vragen waarvoor ze geschreven zijn; op nieuwe vragen verandert het zonder embeddings weinig. Twee holdout-datavragen ('wat kost een huis hier gemiddeld', 'hoe druk bewoond is het hier') vinden geen indicator en gaan daarom niet naar de datavraagroute.

## Bronnen

- CBS Kerncijfers wijken en buurten (via de sample-data), voor de cijfers in de datavragen.
- Synoniemen: [`db/stuurdata/synoniemen.json`](../../db/stuurdata/synoniemen.json), beheerd als data.
- Embeddingmodel: https://huggingface.co/intfloat/multilingual-e5-small (MIT).

## Bekende afwijkingen

Zie `bekende_afwijkingen` in [`usecase.json`](usecase.json).

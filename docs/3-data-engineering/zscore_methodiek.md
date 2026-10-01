# Z-scores: methodiek

> **Status:** vastgesteld in #66 (oktober 2026), aangevuld in #155 (waterdefinitie, minimum-n, waterbuurt als doelgebied). Toezegging uit de aanvraag innovatiebudget: de berekening is navolgbaar.
> **Code:** `init_data/schema/08_zscore_referentie.sql` (SQL-functies, migratie `migrations/schema_v21_zscore_referentie.sql`), `services/zscore_referentie.py` (parameters).
> **Tests:** `tests/integration/test_zscore_referentie.py`, `tests/test_scoring_unit.py`.

D-OmniTwin vergelijkt de waarde van een gebied met een referentiegroep van vergelijkbare gebieden. De Z-score zegt hoeveel standaarddeviaties een gebied van het gemiddelde van die groep afwijkt. Alle rapporten en het Kompas rekenen met dezelfde functies; er is geen tweede berekening.

**Uitgangspunt:** de methodiek volgt hoe de bestaande code (Taeke) werkte, met het Kompas en het executive-rapport als zwaarste paden. Waar die werkwijze afwijkt van hoe het hoort, staat hieronder een waarschuwing. Het principe "waterbuurten uitgesloten van alle statistiek" staat beschreven (`AGENTS.md`, `docs/2-architectuur/architecture/ARCHITECTURE_TECHNICAL_OPERATION.md`, sectie 6B) en is doorgevoerd.

## Keuzes: zo werkte het, zo is het nu

| Keuze | Zo werkte het bij Taeke (vóór #66) | Zo is het nu | ⚠️ Afwijking of risico |
|---|---|---|---|
| Referentiegroep | Gebiedstype + gemeente van het doelgebied: executive, multi-gebied, thema-analyse, deelgebied (referentie `gemeente`), Kompas top-buurten (met `gebied_id`), Kompas-benchmark. Referentie `fryslan`: alleen gebiedstype. | Ongewijzigd, als parameter (`gemeente_code`, `NULL` = alle gemeenten). | `fryslan` betekent: alle gemeenten in de database, niet alleen Fryslân. |
| Jaarlogica | Executive: alleen gebieden met een waarde in **hetzelfde jaar** als de meest recente waarde van het doelgebied (expliciet in commentaar). Kompas top-buurten: het meest recente jaar van de indicator in de groep. Kompas-benchmark: het meest recente jaar over de hele database. Multi-gebied, thema-analyse, deelgebied, benchmark: de meest recente waarde per gebied, ongeacht het jaar. | Standaard `zelfde_jaar` (executive/Kompas), overal. `recentst_per_gebied` blijft beschikbaar als parameter. | Multi-gebied, thema-analyse, deelgebied en benchmark rekenen anders dan voorheen. Zie de waarschuwing onder Jaarlogica. |
| Minimum-n bij `zelfde_jaar` (#155) | Geen minimum: executive en Kompas rekenden ook met 2 à 3 gebieden in hetzelfde jaar. | Minder dan 5 gebieden (`p_min_n`, `MIN_N_STANDAARD`) met een waarde in het jaar van het doelgebied: terugval op `recentst_per_gebied`, met `referentie_terugval = true`. Het gebiedsdossier meldt het. | Bij terugval worden waarden uit verschillende jaren vergeleken. Executive en Kompas rekenen in die gevallen anders dan voorheen. |
| Waterbuurten | Alleen het deelgebied-rapport sloot ze uit de referentie. Executive, multi-gebied, thema-analyse, benchmark en Kompas telden ze mee. De kaartview gebruikte een ruimere definitie (ook op naam). | Eén definitie, `is_waterbuurt(naam, metadata)`: de vlag `metadata->>'water' = 'JA'`, met de naam als vangnet (#155). Altijd uitgesloten uit de referentie en de kaartview. | Uitkomsten veranderen waar waterbuurten waarden hebben. Het naamvangnet kan een gewone buurt raken waarvan de naam op water lijkt. |
| Waterbuurt als doelgebied (#155) | Multi-gebied, thema-analyse en deelgebied lieten een waterbuurt weg. Executive/rapport-data en Kompas gaven wél Z-scores en kleuren. | Overal geen Z-score: `zscore_gebieden` geeft `z_score = NULL` en `is_waterbuurt = true`. Rapport-data en executive geven een lege lijst met een melding, Kompas grijze kleuring met een melding. | Geen. |
| Gebiedstype in top-buurten | Eerste gebiedstype met `LIKE '%buurt%'` in de naam, plus naamfilter `'wijk %'`. | Gebiedstype-id van `gebied_id`; zonder `gebied_id` het type met code `CBS_BUURT`. Geen naamfilter. | Wijken die als CBS-buurt zijn opgeslagen, tellen mee als ze waarden hebben. Open, hangt af van de ETL (#69). |
| Scenario | Niet gefilterd: projecties (`scenario_id` ≠ `current`) konden als "meest recente waarde" meetellen. | Alleen `current` (parameter). | Uitkomsten veranderen als er projecties in `gebied_data` staan. |
| Metingen zonder jaar | `ORDER BY jaar DESC` zette rijen zonder jaar (alleen `datum`) vooraan. | Tellen niet mee. | Klein; geen zulke rijen in de sample. |
| Randgevallen (n < 2, sd = 0) | Executive: Z = 0. Overige rapporten en top-buurten: indicator overgeslagen. | Ongewijzigd in de uitkomst; de formule `zscore()` geeft `NULL`, de rapporten tonen dat zoals voorheen. | Geen. |
| Formule | `(x − μ) / STDDEV_SAMP`, ~6× gekopieerd. | Eén functie `zscore()`, plus `bereken_zscore()` in Python voor het gewogen deelgebiedsgemiddelde (getest op gelijkheid). | Geen. |
| Kompas-kleuring | Percentielen over **alle** waarden in `gebied_data`: alle gebiedstypes, gemeenten, jaren, scenario's, inclusief waterbuurten. | Percentielen over de referentieset van het gebied (gebiedstype + gemeente, peiljaar, zonder waterbuurten). | Kleuren kunnen veranderen in de volledige dataset. |
| `gebieden.actief` | Alleen de Kompas-benchmark filterde op `actief = true`. | Speelt nergens een rol in de referentie. De kaartview filtert er wel op. | Inactieve gebieden tellen mee in de referentie. Open, hangt af van de ETL (#69). |
| Deelgebied, gewogen Z | Referentie van de eerste buurt. | Referentie van het meest recente meetjaar onder de buurten. | Buurten met een ouder meetjaar hebben een andere referentie dan het gewogen gemiddelde. |

> ⚠️ **Waarschuwing:** vóór #66 zaten waterbuurten in de referentiegroep van executive, multi-gebied, thema-analyse, benchmark en het Kompas (top-buurten, benchmark, kleuring). Dat was tegen het beschreven principe. Nu zijn ze overal uitgesloten. Waar waterbuurten waarden hebben, veranderen gemiddelde, standaarddeviatie en dus de Z-scores en de top-lijsten ten opzichte van eerdere rapporten. In de sample dataset zijn er geen waterbuurten; daar verandert niets.

## Formule

```
Z = (x − μ) / s
```

- `x`: de waarde van het gebied voor de indicator;
- `μ`: het gemiddelde van de referentiegroep;
- `s`: de standaarddeviatie van de referentiegroep, als steekproef-standaarddeviatie (`STDDEV_SAMP`, deler n − 1);
- `n`: het aantal gebieden in de referentiegroep met een waarde voor de indicator.

Het gebied zelf telt mee in de referentiegroep als het erin valt (zelfde gebiedstype en gemeente, geen waterbuurt, waarde in het peiljaar).

## Referentiegroep

| Parameter | Standaard | Betekenis |
|---|---|---|
| gebiedstype | gebiedstype van het gebied (`gebieden.gebiedstype_id`) | alleen gebieden van hetzelfde type, bijvoorbeeld CBS-buurten |
| gemeente | gemeente van het gebied | alleen gebieden in dezelfde gemeente. Referentie `fryslan` laat de gemeente weg: dan tellen alle gebieden van het gebiedstype in de database mee |
| waterbuurten | altijd uitgesloten | zie [Waterbuurt](#waterbuurt) |
| scenario | `current` | alleen metingen, geen projecties. Een lege `scenario_id` telt als `current` |

> ⚠️ **Waarschuwing (open, ETL #69):** `ETL/import_geografie_2024.py` slaat wijken (`WK…`, naam `Wijk …`) op met het gebiedstype CBS-buurt. Het oude naamfilter `'wijk %'` in Kompas top-buurten is vervallen, omdat de referentie nu op gebiedstype-id gaat. Hebben wijken waarden, dan tellen ze mee in de referentie van buurten. De oplossing hoort bij de data: een eigen gebiedstype voor wijken.

> ⚠️ **Waarschuwing (open, ETL #69):** `gebieden.actief` speelt geen rol in de referentiegroep. Alleen de oude Kompas-benchmark filterde erop. Inactieve gebieden (bijvoorbeeld vervallen buurtindelingen) met waarden tellen mee. Of ze eruit moeten, hangt af van hoe de ETL vervallen indelingen markeert.

## Waterbuurt

Eén definitie, in SQL: `is_waterbuurt(naam, metadata)` (`init_data/schema/08_zscore_referentie.sql`). Een gebied is een waterbuurt als:

1. **de data het zegt:** `gebieden.metadata->>'water' = 'JA'`. De CBS-wijk- en buurtkaart heeft een kolom `water` (JA/NEE). `ETL/Geometrie/import_geometrie.py` neemt alle kolommen mee in `metadata`; `ETL/import_geografie_2024.py` neemt de kolom `water` mee (#155);
2. **of, als vangnet, de naam op water wijst:** `buitenwater`, `Wadden Sea` of `IJsselmeer` (hoofdletterongevoelig). Dit is de lijst uit de oude kaartview, voor bronnen zonder watervlag, zoals `init_data/fryslan/buurten_fryslan.geojson` (PDOK WFS).

`markeer_waterbuurten()` zet bij het laden de vlag in de data voor gebieden die alleen op naam herkend worden (`metadata.water = 'JA'`, `metadata.water_bron = 'naam'`). De migratie, `load_sample.py`, `seed_fryslan.py` en `import_geografie_2024.py` roepen hem aan. Daarna is de naam alleen nog vangnet.

Gebruikt door: de Z-score-referentie (`zscore_referentie_waarden`), het doelgebied (`zscore_gebieden`), de kaartview `vw_gebied_kaart_basis` en de waterfilters in `services/report_service.py`.

Een waterbuurt als **doelgebied** krijgt geen Z-score: `zscore_gebieden` geeft `z_score = NULL` en `is_waterbuurt = true`. Rapport-data en executive (`/api/report/data/{id}`, `/api/report/executive/{id}`) geven geen indicatoren en een melding; het Kompas (`/api/kompas/{config}/gebied/{id}`) kleurt grijs en geeft `is_waterbuurt` en `melding`. Multi-gebied, thema-analyse en deelgebied laten waterbuurten weg, zoals voorheen (deelgebied noemt ze onder `waterbuurten_uitgesloten`).

> ⚠️ **Waarschuwing:** het naamvangnet is grof. Een gewone buurt met bijvoorbeeld "IJsselmeer" in de naam geldt als waterbuurt, en verdwijnt van de kaart en uit de referentie. Dat gold al voor de kaart; nu ook voor de Z-scores. Controleer na het laden welke gebieden `water_bron = 'naam'` hebben.

## Jaarlogica

| Waarde | Betekenis |
|---|---|
| `zelfde_jaar` (standaard) | de referentie bestaat uit de waarden in het meetjaar van het doelgebied: het jaar van zijn meest recente waarde, per indicator. Zonder doelgebied (Kompas top-buurten, kleuring, Kompas-benchmark): het meest recente jaar van de indicator in de referentiegroep |
| `recentst_per_gebied` | de meest recente waarde van elk gebied, ook als gebieden verschillende jaren hebben |

**Minimum-n (#155).** Hebben bij `zelfde_jaar` minder dan 5 gebieden een waarde in het jaar van het doelgebied, dan valt de referentie terug op `recentst_per_gebied` voor die indicator. De functies geven dan `referentie_terugval = true`. Zonder doelgebied (Kompas top-buurten, kleuring, Kompas-benchmark) geldt hetzelfde voor het peiljaar.

- Instelbaar met `p_min_n` (SQL) en `MIN_N_STANDAARD` (`services/zscore_referentie.py`); `0` betekent nooit terugvallen.
- Waarom 5: met minder gebieden zegt de steekproef-standaarddeviatie weinig en bepaalt één gebied het gemiddelde. Vijf is een pragmatische ondergrens, geen statistische norm.
- Waarom terugval in plaats van geen Z-score: het rapport blijft volledig, en de keuze is navolgbaar (zelfde regel als multi-gebied en thema-analyse vóór #66).
- Het gebiedsdossier (`/api/report/data/{id}`, ook de basis van de executive) geeft per indicator `referentie_terugval` en `n_referentie`, en een melding in `meldingen` met de namen van de indicatoren. De rapportpagina toont die melding boven de Z-scores en een `*` bij het meetjaar.

Het doelgebied gebruikt altijd zijn meest recente waarde. Metingen zonder jaar tellen niet mee. Het rapport toont het meetjaar (`meetjaar`).

Waarom `zelfde_jaar`: zo werkten het executive-rapport (met expliciet commentaar: "ALLEEN voor exact hetzelfde jaar als het actuele datapunt van het target gebied") en Kompas top-buurten. Waarden uit verschillende jaren worden niet door elkaar vergeleken.

> ⚠️ **Waarschuwing:** multi-gebied, thema-analyse, deelgebied en benchmark gebruikten vóór #66 de meest recente waarde per gebied, ongeacht het jaar. Ze rekenen nu met `zelfde_jaar`. Heeft een doelgebied een nieuwer meetjaar dan de meeste andere gebieden, dan is de referentiegroep klein. Voorbeeld in de sample: "Inkomen per inwoner" heeft 2023 voor 10 buurten en 2024 voor 4. Voor Bolsward-Zuidoost (2024) zou de referentie 4 buurten zijn; door de minimum-n valt hij terug op de meest recente waarde van 13 buurten (gemiddelde 29,87), met `referentie_terugval = true`.

> ⚠️ **Waarschuwing:** bij een terugval worden waarden uit verschillende jaren vergeleken. Dat is minder zuiver dan `zelfde_jaar`, maar beter dan een referentie van 2 à 4 gebieden. Het rapport meldt het; de lezer moet het meewegen.

> ⚠️ **Waarschuwing:** bij `zelfde_jaar` kunnen gebieden in één rapport verschillende referenties hebben, als hun meetjaren verschillen. Het deelgebied-rapport berekent de Z-score van het gewogen gemiddelde met de referentie van het meest recente meetjaar onder de buurten; de buurt-Z-scores in de drilldown gebruiken elk hun eigen jaar.

## Randgevallen

| Situatie | Uitkomst |
|---|---|
| n < 2 | geen Z-score (`NULL`) |
| s = 0 (alle gebieden dezelfde waarde) | geen Z-score (`NULL`) |
| gebied heeft geen waarde voor de indicator | indicator ontbreekt voor dat gebied |
| minder dan 5 gebieden met een waarde in het peiljaar (`zelfde_jaar`) | terugval op `recentst_per_gebied`, `referentie_terugval = true` |
| doelgebied is een waterbuurt | geen Z-score (`NULL`), `is_waterbuurt = true` |

Hoe de rapporten "geen Z-score" tonen (ongewijzigd t.o.v. vóór #66):

- rapport-data en executive (`/api/report/data`, `/api/report/executive`): Z = 0, telt niet als uitschieter; voor een waterbuurt geen indicatoren en een melding;
- multi-gebied, thema-analyse, deelgebied, Kompas top-buurten: de indicator wordt overgeslagen.

## Waar het gebruikt wordt

| Onderdeel | Endpoint | Functie |
|---|---|---|
| Rapport-data, executive | `GET /api/report/data/{id}`, `GET /api/report/executive/{id}` | `zscore_gebieden` |
| Multi-gebiedsdossier (top-3 en thema-aggregaat) | `POST /api/report/multi-gebied(/geojson)` | `zscore_gebieden` |
| Thema-analyse | `POST /api/report/thema-analyse(/geojson)` | `zscore_gebieden` |
| Deelgebied (Sjabloon F) | `POST /api/report/deelgebied(/kaart)` | `zscore_gebieden`; Z van het gewogen gemiddelde met `bereken_zscore` |
| Benchmark (gemeente, fryslan) | `GET /api/report/benchmark` | `zscore_gebieden` voor gebied A (gemiddelde en n van de referentie in het meetjaar van A) |
| Kompas-benchmark (gemeentegemiddelde) | `POST /api/kompas/{config}/benchmark` | `zscore_referentie_stats` (CBS-buurten van de gemeente, meest recente jaar) |
| Kompas top-buurten | `GET /api/kompas/indicator/{uuid}/top-buurten` | `zscore_gebieden` over de referentieset; gebiedstype van `gebied_id`, zonder `gebied_id` CBS-buurten van alle gemeenten |
| Kompas-kleuring | `GET /api/kompas/{config}/gebied/{id}` | percentielen (12,5 %-stappen) over `zscore_referentie_waarden` van het gebied; waterbuurt: grijs met `melding` |

De benchmark-modus `gebieden` vergelijkt met een zelfgekozen set gebieden. Dat is geen referentiegroep en gebruikt deze functies niet.

> ⚠️ **Waarschuwing:** de Kompas-kleuring rekende vóór #66 percentielen over alle waarden in de database (alle gebiedstypes, jaren, gemeenten en scenario's, met waterbuurten). Nu over de referentieset van het gebied. In de sample verandert er niets; in de volledige dataset kunnen kleuren verschuiven.

## SQL-functies

```sql
-- Eén definitie van waterbuurt; en de vlag in de data zetten (geeft het aantal)
is_waterbuurt(naam, metadata)
markeer_waterbuurten()

-- Referentieset; jaarlogica 'zelfde_jaar' (zonder doelgebied: meest recente jaar),
-- 'recentst_per_gebied' of de hulpwaarde 'alle_jaren'. Kolom referentie_terugval.
zscore_referentie_waarden(gebiedstype_id, gemeente_code = NULL,
                          jaarlogica = 'zelfde_jaar', scenario_id = 'current',
                          indicator_uuids = NULL, min_n = 5)

-- Gemiddelde, standaarddeviatie, n, min, max, min_jaar, max_jaar, referentie_terugval
-- per indicator (zonder doelgebied)
zscore_referentie_stats(...zelfde parameters...)

-- De formule; NULL bij n < 2 of s = 0
zscore(waarde, gemiddelde, standaarddeviatie, n)

-- Z-scores van gebieden; gebied_ids = NULL geeft de gebieden van de referentieset zelf.
-- Kolommen o.a. z_score, n, referentie_terugval, is_waterbuurt
zscore_gebieden(gebied_ids, gebiedstype_id, gemeente_code = NULL, jaarlogica = 'zelfde_jaar',
                scenario_id = 'current', indicator_uuids = NULL, min_n = 5)
```

Voorbeeld, Bolsward-Zuidoost ten opzichte van de CBS-buurten van Súdwest-Fryslân:

```sql
SELECT i.naam, zs.waarde, zs.jaar, zs.gemiddelde, zs.standaarddeviatie, zs.n, zs.z_score,
       zs.referentie_terugval
FROM zscore_gebieden(ARRAY['BU19000002']::varchar[],
                     (SELECT gebiedstype_id FROM gebieden WHERE id = 'BU19000002'),
                     '1900') zs
JOIN indicatoren i ON i.uuid = zs.indicator_uuid
ORDER BY abs(zs.z_score) DESC NULLS LAST;
```

Een bestaande database bijwerken: `psql -f migrations/schema_v21_zscore_referentie.sql` (idempotent; zet ook ontbrekende watervlaggen en vervangt `vw_gebied_kaart_basis`). Een nieuwe database krijgt de functies via `db-init`.

## Buiten deze methodiek

- **Richting (polariteit).** Of een hoge Z-score gunstig of ongunstig is, volgt uit `score_type` van de indicator. Dat valt buiten de Z-score zelf (zie #120).

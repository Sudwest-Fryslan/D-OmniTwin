# Z-scores: methodiek

> **Status:** vastgesteld in #66 (oktober 2026). Toezegging uit de aanvraag innovatiebudget: de berekening is navolgbaar.
> **Code:** `init_data/schema/08_zscore_referentie.sql` (SQL-functies), `services/zscore_referentie.py` (parameters).
> **Tests:** `tests/integration/test_zscore_referentie.py`, `tests/test_scoring_unit.py`.

D-OmniTwin vergelijkt de waarde van een gebied met een referentiegroep van vergelijkbare gebieden. De Z-score zegt hoeveel standaarddeviaties een gebied van het gemiddelde van die groep afwijkt. Alle rapporten en het Kompas rekenen met dezelfde functies; er is geen tweede berekening.

## Formule

```
Z = (x − μ) / s
```

- `x`: de waarde van het gebied voor de indicator;
- `μ`: het gemiddelde van de referentiegroep;
- `s`: de standaarddeviatie van de referentiegroep, als steekproef-standaarddeviatie (`STDDEV_SAMP`, deler n − 1);
- `n`: het aantal gebieden in de referentiegroep met een waarde voor de indicator.

Het gebied zelf telt mee in de referentiegroep als het erin valt (zelfde gebiedstype en gemeente, geen waterbuurt).

## Referentiegroep

| Parameter | Standaard | Betekenis |
|---|---|---|
| gebiedstype | gebiedstype van het gebied (`gebieden.gebiedstype_id`) | alleen gebieden van hetzelfde type, bijvoorbeeld CBS-buurten |
| gemeente | gemeente van het gebied | alleen gebieden in dezelfde gemeente. Rapporten met referentie `fryslan` laten de gemeente weg: dan tellen alle gebieden van het gebiedstype in de database mee |
| waterbuurten | altijd uitgesloten | een gebied is een waterbuurt als `gebieden.metadata->>'water' = 'JA'` |
| scenario | `current` | alleen metingen, geen projecties. Een lege `scenario_id` telt als `current` |

Een waterbuurt telt nooit mee in gemiddelde, standaarddeviatie of n. Multi-gebied, thema-analyse en deelgebied laten waterbuurten ook als doelgebied weg (het deelgebied-rapport noemt ze onder `waterbuurten_uitgesloten`).

## Jaarlogica

Per gebied en indicator telt één waarde.

| Waarde | Betekenis |
|---|---|
| `recentst_per_gebied` (standaard) | de meest recente waarde van elk gebied, ook als gebieden verschillende jaren hebben |
| `recentst_jaar_indicator` | alleen het meest recente jaar van de indicator in de referentiegroep; gebieden zonder waarde in dat jaar vallen weg |

Het doelgebied krijgt dezelfde jaarlogica. Metingen zonder jaar (alleen een datum) tellen niet mee. Het rapport toont het meetjaar van het gebied (`meetjaar`).

Waarom de standaard: CBS- en RIVM-bronnen publiceren niet elk jaar voor elk gebied. Met "alleen het meest recente jaar" valt een gebied met een oudere waarde uit de vergelijking, en zou het doelgebied zelf geen Z-score kunnen krijgen. Het nadeel: waarden uit verschillende jaren worden vergeleken. Het rapport geeft per indicator het meetjaar, zodat dat zichtbaar is.

## Randgevallen

| Situatie | Uitkomst |
|---|---|
| n < 2 | geen Z-score (`NULL`) |
| s = 0 (alle gebieden dezelfde waarde) | geen Z-score (`NULL`) |
| gebied heeft geen waarde voor de indicator | indicator ontbreekt voor dat gebied |
| geen referentiewaarden voor de indicator | indicator ontbreekt |

Hoe de rapporten "geen Z-score" tonen:

- rapport-data en executive (`/api/report/data`, `/api/report/executive`): Z = 0, telt niet als uitschieter;
- multi-gebied, thema-analyse, deelgebied, Kompas top-buurten: de indicator wordt overgeslagen.

## Waar het gebruikt wordt

| Onderdeel | Endpoint | Functie |
|---|---|---|
| Rapport-data, executive | `GET /api/report/data/{id}`, `GET /api/report/executive/{id}` | `zscore_gebieden` |
| Multi-gebiedsdossier (top-3 en thema-aggregaat) | `POST /api/report/multi-gebied(/geojson)` | `zscore_gebieden` |
| Thema-analyse | `POST /api/report/thema-analyse(/geojson)` | `zscore_gebieden` |
| Deelgebied (Sjabloon F) | `POST /api/report/deelgebied(/kaart)` | `zscore_gebieden`; Z van het gewogen gemiddelde met dezelfde formule (`bereken_zscore`) en dezelfde μ, s, n |
| Benchmark (gemeente, fryslan) | `GET /api/report/benchmark` | `zscore_referentie_stats` (gemiddelde, n) |
| Kompas-benchmark (gemeentegemiddelde) | `POST /api/kompas/{config}/benchmark` | `zscore_referentie_stats` (CBS-buurten van de gemeente) |
| Kompas top-buurten | `GET /api/kompas/indicator/{uuid}/top-buurten` | `zscore_gebieden` over de hele referentiegroep; gebiedstype van `gebied_id`, zonder `gebied_id` CBS-buurten van alle gemeenten |
| Kompas-kleuring | `GET /api/kompas/{config}/gebied/{id}` | percentielen (12,5 %-stappen) over `zscore_referentie_waarden` van het gebied |

De Benchmark-modus `gebieden` vergelijkt met een zelfgekozen set gebieden. Dat is geen referentiegroep en gebruikt deze functies niet.

## SQL-functies

```sql
-- Referentieset: één waarde per gebied en indicator
zscore_referentie_waarden(gebiedstype_id, gemeente_code = NULL,
                          jaarlogica = 'recentst_per_gebied', scenario_id = 'current',
                          indicator_uuids = NULL)

-- Gemiddelde, standaarddeviatie, n, min, max, min_jaar, max_jaar per indicator
zscore_referentie_stats(...zelfde parameters...)

-- De formule; NULL bij n < 2 of s = 0
zscore(waarde, gemiddelde, standaarddeviatie, n)

-- Z-scores van gebieden; gebied_ids = NULL geeft alle gebieden van de referentiegroep
zscore_gebieden(gebied_ids, gebiedstype_id, gemeente_code = NULL, ...)
```

Voorbeeld, Bolsward-Zuidoost ten opzichte van de CBS-buurten van Súdwest-Fryslân:

```sql
SELECT i.naam, zs.waarde, zs.jaar, zs.gemiddelde, zs.standaarddeviatie, zs.n, zs.z_score
FROM zscore_gebieden(ARRAY['BU19000002']::varchar[],
                     (SELECT gebiedstype_id FROM gebieden WHERE id = 'BU19000002'),
                     '1900') zs
JOIN indicatoren i ON i.uuid = zs.indicator_uuid
ORDER BY abs(zs.z_score) DESC NULLS LAST;
```

Een bestaande database bijwerken: `psql -f migrations/schema_v20_zscore_referentie.sql` (idempotent). Een nieuwe database krijgt de functies via `db-init`.

## Buiten deze methodiek

- **Richting (polariteit).** Of een hoge Z-score gunstig of ongunstig is, volgt uit `score_type` van de indicator. Dat valt buiten de Z-score zelf (zie #120).
- **Wijken als buurt.** `ETL/import_geografie_2024.py` slaat wijken (`WK…`) op met het gebiedstype CBS-buurt. Als wijken waarden hebben, vallen ze in de referentiegroep van buurten. Het oude naamfilter `'wijk %'` in top-buurten is vervangen door het gebiedstype; de oplossing hoort bij de data (eigen gebiedstype voor wijken).
- **Inactieve gebieden.** `gebieden.actief` speelt geen rol in de referentiegroep.

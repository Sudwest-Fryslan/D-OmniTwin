# Jaargangen van indicatoren en buurtgeometrie

Issue #119. Stand 1 oktober 2026, op `main`.

## Kern

- De **buurtgeometrie is van 2024** (CBS Wijk- en buurtkaart 2024), in de sample en in de Fryslân-data.
- De **indicatoren komen uit 2021 tot en met 2026**, per bron verschillend. Eén indicator kan per buurt een ander jaar hebben.
- **De waarden met bron "Kerncijfers wijken en buurten 2023" zijn van 2021.** Ze komen uit CBS-tabel `85039NED`, en dat is de Kerncijfers-tabel van 2021 (CBS TableInfos: `Period 2021`). Controle: Bolsward-Noord heeft in de sample 1.770 inwoners. Dat is het getal van 2021; in 2023 (`85618NED`) waren het er 1.920. De sample en `indicatorwaarden_fryslan.csv` noemen in de kolom `jaar` het jaar 2023.
- Gevolg: "Inwoners" in de sample is van 2021, "65+ jaar" van 2025. Een percentage 65+ (PR #141) deelt dus een teller uit 2025 door een noemer uit 2021, terwijl de bron "noemer 2023" vermeldt.

## 1. Jaargangen per bron

### Sample (`init_data/sample/2_brondata/sample_indicatoren.csv`, 1.132 regels)

| Bron (kolom `bron`) | Kolom `jaar` | Regels | Opmerking |
|---|---|---|---|
| `CBS_86165NED` | 2025 | 240 | Kerncijfers wijken en buurten 2025 |
| `CBS_85984NED` | 2024 | 15 | Kerncijfers 2024 (o.a. inkomen per inwoner, deel van de buurten) |
| `CBS_85618NED` | 2023 | 24 | Kerncijfers 2023 |
| `Kerncijfers wijken en buurten 2023` | 2023 | 105 | **werkelijk 2021** (`85039NED`), zie boven |
| `CBS_50150NED` | 2024 | 12 | RIVM-tabel via CBS |
| `Gezondheidsmonitor RIVM 2024` | 2024 | 120 | |
| `BAG` | 2026 | 168 | momentopname |
| `Kadaster BAG Fryslân 2026` | 2025 | 84 | label 2026, jaar 2025 |
| `RVO EP-Online 2026-02` | 2025 | 60 | label 2026-02, jaar 2025 |
| `Berekend: EP-Online / BAG Fryslân` | 2025 | 12 | |
| `OpenStreetMap / Overpass API 2026` | 2026 | 60 | momentopname |
| `<uuid>_d_cbs_buurten.json` (upload) | 2021, 2022, 2025 | 96 | herkomst onbekend (#60); o.a. "Afstand tot koele plek" 2021, GLG en hemelwater 2022 |
| leeg | 2024 | 48 | |
| `DEMO: …` (Bolsward-Zuidoost) | 2021-2026 | 88 | volgt de jaren van de buren |

Op één na heeft elke indicator in de sample één jaargang. Uitzondering: **"Inkomen per inwoner"** heeft voor een deel van de buurten 2024 (`CBS_85984NED`) en voor de rest "2023" (in werkelijkheid 2021). Op de kaart staan die door elkaar.

Per indicator: `python -m pytest tests/test_jaargangen_sample.py -s` drukt de lijst af.

### Fryslân (`init_data/fryslan/indicatorwaarden_fryslan.csv`, ~387.000 regels)

| Bron | Kolom `jaar` | Opmerking |
|---|---|---|
| `Kerncijfers wijken en buurten 2023` | 2023 | **werkelijk 2021** (`85039NED`, `download_indicatoren_fryslan.py`) |
| `Gezondheidsmonitor RIVM 2012` … `2024` | 2012, 2016, 2020, 2022, 2024 | reeks; buurtcodes passen op de indeling van 2024 |

De CSV bevat heel Nederland (ook wijken, gemeenten en `NL00`). Alleen de Friese buurtcodes worden geladen.

## 2. Jaargang van de geometrie

| Bestand | Jaargang | Herkomst |
|---|---|---|
| `init_data/sample/2_brondata/sample_buurten.geojson` | **2024** | `ETL/import_geografie_2024.py` (`CBS_BUURTEN2024.gpkg`); Bolsward-Zuidoost uit PDOK gebiedsindelingen 2024 |
| `init_data/fryslan/buurten_fryslan.geojson` | **2024** | `download_buurten_fryslan.py`, PDOK `gebiedsindelingen/2024`, gegeneraliseerd |
| ~~`ETL/local/etl_02_import_geometrie.py`~~ | 2023 | PDOK `wijkenbuurten2023`. Verwijderd in [#69](https://github.com/TLaan/D-OmniTwin/issues/69) |

Vastgelegd in deze PR:
- `datapackage.json`, resource `sample-buurten`: `"geometrie_jaar": 2024` en `geometrie_bron`.
- `load_sample.py` schrijft dat in `gebieden.metadata` (`{"geometrie_jaar": 2024, "geometrie_bron": "CBS Wijk- en buurtkaart"}`).

## 3. Waar de app een jaar kiest

Overal geldt: **het meest recente jaar, per gebied en per indicator.** Er is geen peiljaar dat voor alle buurten gelijk is.

| Plek | Code | Keuze |
|---|---|---|
| Kaart (kleur, tooltip) | `services/gebiedsmonitor_service.py` → view `vw_gebied_indicator_actueel` | per buurt het laatste jaar (`DISTINCT ON … ORDER BY jaar DESC`). Met de tijdslider een vast `jaar`. Buurten zonder dat jaar krijgen dan geen kleur |
| Kompas, waarde per buurt | `services/kompas_service.py` (`LATERAL … ORDER BY jaar DESC LIMIT 1`) | per buurt het laatste jaar |
| Kompas, referentie (gemiddelde, sd) | `kompas_service.py`, CTE `meest_recent` | het laatste jaar **over alle buurten** van de gemeente |
| Kompas, groepen/benchmark | `kompas_service.py` (`MAX(gd2.jaar)`) | laatste jaar binnen de groep |
| Kompas-detail en tijdslider | `get_indicator_history` | alle jaren van die buurt |
| Gebiedsdossier (rapport) | `services/report_service.py` | laatste jaar van de buurt; referentie in **hetzelfde** jaar. Toont `meetjaar` |
| Deelgebied- en themarapport | `report_service.py` (`ROW_NUMBER … ORDER BY jaar DESC`) | per buurt het laatste jaar; bronverantwoording toont `peildata` uit `indicatoren.begingeldigheid/eindgeldigheid`, in de sample leeg → "Recentste" |
| Dashboard | `routers/dashboard.py` | `MAX(jaar)` |

Issue #66 maakt één centrale Z-score-functie met een vaste referentiegroep. Die functie is de plek om ook het jaar van waarde en referentie gelijk te trekken (zie vervolg).

## 4. Combinaties die fout gaan

1. **Gewijzigde buurtcodes.** De Kerncijfers in `indicatorwaarden_fryslan.csv` zijn van de indeling 2021. Smallingerland (`GM0090`) is daarna opnieuw ingedeeld: **31 buurtcodes** uit de CSV (`BU00900001` …) bestaan niet in de geometrie van 2024, en **61 buurten** in de geometrie (`BU00900101` …) hebben geen Kerncijfers. Die 651 regels worden stil overgeslagen (#111 noemde dit al). In de sample komt het niet voor: alle 13 codes bestaan in de indelingen 2021 tot en met 2024.
2. **Verhoudingen tussen jaren.** Een afgeleide indicator (teller ÷ noemer) uit verschillende jaren klopt niet. In de sample: 65+ (2025) ÷ inwoners (2021). PR #141 zet het jaar van de noemer in de bron, maar dat jaar is het label 2023 en niet het echte jaar 2021.
3. **Waarde en referentie uit verschillende jaren.** In het Kompas komt de waarde van een buurt uit het laatste jaar van die buurt, en de referentie uit het laatste jaar van de gemeente. Bij "Inkomen per inwoner" vergelijkt een buurt met alleen "2023" zich met het gemiddelde van 2024. Het gebiedsdossier doet dit wel goed (referentie in hetzelfde jaar).
4. **Gemengde jaren op één kaart.** De kaart kleurt buurten met waarden uit verschillende jaren in één schaal (inkomen per inwoner: 2021 en 2024).
5. **Scenario's.** `vw_gebied_indicator_actueel` filtert niet op `scenario_id`. Staat er een scenario met een later jaar in `gebied_data`, dan toont de kaart dat als actueel. Dit valt buiten #119; melden als apart issue.

## 5. Wat deze PR doet (MVP)

**Jaargang zichtbaar**
- Kaart-tooltip: toont nu "Jaar … · Bron: …" bij elke waarde. Alle tekst gaat via `escapeHtml`. Bij wisselen van indicator worden jaar en bron van buurten zonder data leeggemaakt.
- Kompas-detail: toonde al het jaar. De bron was die van de indicator (eerste regel bij het laden). Nu de bron van de getoonde waarde, en bij de tijdslider de bron van dat jaar. Was er geen bron, dan stond er "CBS"; nu "Onbekend".
- Kompas bij meerdere buurten: toont de spreiding ("2021–2024 (verschilt per gebied)") in plaats van alleen het eerste jaar.
- Gebiedsdossier (admin-rapport) toont `meetjaar` al. Niet gewijzigd.

**Geometrie-jaargang vastgelegd**: `datapackage.json` en `gebieden.metadata`, zie §2.

**Controle in de ETL**: `init_data/scripts/jaargang_controle.py`. Waarschuwt (geen fout) bij:
- buurtcodes in de waarden die niet in de geometrie staan;
- indicatoren waarvan het **meest recente** jaar meer dan 2 jaar van het geometriejaar afwijkt. Oudere jaren van een reeks (RIVM 2012-2022) zijn bedoeld.

`load_sample.py` roept de controle aan vóór het laden van de waarden. Los te draaien:

```
python init_data/scripts/jaargang_controle.py            # sample: 1 waarschuwing (Afstand tot koele plek, 2021)
python init_data/scripts/jaargang_controle.py --fryslan  # 31 onbekende codes (Smallingerland)
```

`seed_fryslan.py` is niet aangepast, omdat PR #111 dat bestand herschrijft. Na #111 de controle daar ook aanroepen.

**Labels gecorrigeerd**: `download_indicatoren_fryslan.py` noemt `85039NED` nu "Kerncijfers wijken en buurten 2021" met `jaar` 2021. De CSV's zelf zijn niet aangepast; dat gebeurt bij opnieuw downloaden. De bronnen in `datapackage.json` en `init_data/fryslan/README.md` vermelden het werkelijke jaar.

**Test**: `tests/test_jaargangen_sample.py`. Faalt als een `gebied_id` niet in de geometrie staat; drukt per indicator de jaargang af.

## 6. Vervolgvoorstellen (niet in deze PR)

1. **Kerncijfers opnieuw ophalen uit de tabel van 2024** (`85984NED`), passend bij de geometrie van 2024. De kolomnamen (`…_N`) verschillen per tabel; de mapping in `download_indicatoren_fryslan.py` moet mee. Daarna de sample opnieuw genereren. Dit lost Smallingerland en het 2021-label in één keer op.
2. **Eén configuratiebron** voor tabel-ID's en geometriejaar, gebruikt door de downloadscripts en de controle. Voorstel uit #119.
3. **Drempel in de controle**: falen als meer dan x % van de regels geen buurt vindt. Nu alleen een waarschuwing.
4. **Peiljaar in de Z-score** (#66): waarde en referentie altijd uit hetzelfde jaar, zoals het gebiedsdossier al doet. Daarna Kompas en kaart op die functie zetten.
5. **Afgeleide indicatoren alleen uit hetzelfde jaar** (PR #141), of anders expliciet markeren en uitsluiten van de Z-score.
6. **Jaargang per waarde in `gebied_data`**: naast `jaar` ook `bron_tabel` (bijv. `85039NED`) en `indeling_jaar`, zodat de herkomst niet uit vrije tekst hoeft te komen (#60, #54).
7. **Omrekenen tussen buurtindelingen** (bijvoorbeeld 2021 → 2024 via de CBS-wijzigingstabellen of oppervlakteweging) voor historische reeksen. Groot; pas nodig bij trends over herindelingen.
8. **Kaart met één peiljaar**: per indicator standaard het jaar met de meeste buurten, en buurten met een ouder jaar zichtbaar markeren.
9. **`vw_gebied_indicator_actueel` filteren op `scenario_id = 'current'`** (apart issue).

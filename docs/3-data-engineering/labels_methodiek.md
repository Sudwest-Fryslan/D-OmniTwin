# Labels A–E: methodiek

> **Status:** ingevoerd in [#256](https://github.com/TLaan/D-OmniTwin/issues/256) (oktober 2026). Zonder vastgestelde drempels rekent D-OmniTwin met **voorlopige drempels (kwintielen)**: de aanname bij vraag A3 van [#222](https://github.com/TLaan/D-OmniTwin/issues/222). De drempels van SWF laad je als data, zonder code (zie [Drempels laden](#drempels-laden)).
> **Code:** `src/omnitwin/services/labelklasse.py` (label en themalabel), `kompas_service.py` (Kompas), `gebiedsmonitor_service.py` (kaart). Instelling: `kompas_configuraties.classificatie = 'label_ae'`; drempels: tabel `indicator_labels` (migratie `V034__labels_ae.sql`).
> **Tests:** `tests/unit/test_labelklasse.py`, `tests/integration/test_labels_stack.py`, `tests/e2e/test_kaartmodus.py` (TC-01-004 en TC-02-003).

De Klimaatmonitor van SWF geeft elk gebied per indicator en per thema een **label A–E** ([methodiek.md](../1-visie-concept/huidige-gebiedsmonitor/methodiek.md#labels-ae)). D-OmniTwin kent daarvoor de classificatie `label_ae`, naast `zscore` ([zscore_methodiek.md](./zscore_methodiek.md)) en `percentiel_8` ([percentielklasse_methodiek.md](./percentielklasse_methodiek.md)).

## Instellen

Per kompasprofiel, als data:

```sql
UPDATE kompas_configuraties SET classificatie = 'label_ae' WHERE naam = 'Klimaat Kompas';
```

Op een verse installatie gebeurt dit vanzelf: `db/stuurdata/kompasprofiel_klimaat.json` vult het profiel *Klimaat Kompas* met de klimaatindicatoren die D-OmniTwin uit open data en de use cases heeft, en zet het op `label_ae`. Dat gebeurt alleen als het profiel nog leeg is; een eigen inrichting blijft staan. Bij een bestaande installatie: `docker compose run --rm db-init python /app/init_data/scripts/load_sample.py --stap kompas`.

| Thema | Onderdeel | Indicator | Richting | Bron (use case) |
|---|---|---|---|---|
| Hittestress | Hitte | Stedelijk hitte-eiland effect | lager is beter | RIVM ([hittestress](../../usecases/hittestress/README.md)) |
| Hittestress | Koelte en groen | Afstand tot koele plek | lager is beter | DEMODATA (sample-bronbibliotheek) |
| Hittestress | Koelte en groen | Boomkroonbedekking | hoger is beter | RIVM (hittestress) |
| Hittestress | Koelte en groen | Oppervlak groen per inwoner | hoger is beter | DEMODATA (sample-bronbibliotheek) |
| Hemelwateroverlast | Water en verharding | Verhouding oppervlakte water / verharding | hoger is beter | DEMODATA (sample-bronbibliotheek) |
| Droogte | Grondwater | Verandering GLG nu t.o.v. 2050 | hoger is beter | DEMODATA (sample-bronbibliotheek) |

De andere klimaatindicatoren van SWF (gevoelstemperatuur, waterdiepte op straat en tegen de gevel, GLG klei- en veenweide, aandeel bladerdek) komen met de use case [`swf-kompasprofiel`](../../usecases/swf-kompasprofiel/README.md) (profiel *SWF Klimaat*, daar `classificatie: label`, hier `label_ae`).

**Kaart:** los van het profiel heeft de legenda een eigen keuze *Label A–E* (`GET /api/gebiedsmonitor/kaart_data/{gebiedstype_id}?indicator_uuid=…&modus=label`).

## Rekenwijze

| Stap | Regel |
|---|---|
| Met drempels | Staan er voor de indicator rijen in `indicator_labels`, dan geldt het label met `ondergrens <= waarde < bovengrens` (een lege grens is open). De drempels bepalen zelf de richting: polariteit speelt geen rol, en een middenband kan A zijn (bijv. gevoelstemperatuur *comfortabel*). Valt een waarde in een gat tussen de drempels, dan krijgt ze geen label (status `buiten_drempels`). Bij overlap wint het gunstigste label. |
| Zonder drempels (voorlopig) | **Kwintielen** in dezelfde referentiegroep als `percentiel_8`: gebiedstype + gemeente, zonder waterbuurten, scenario `current`, jaarlogica `zelfde_jaar`; middenrang-percentiel (gelijke waarden krijgen hetzelfde label). Polariteit toegepast (bij "lager is beter" 1 − percentiel). 0–20% = **E**, 20–40% = D, 40–60% = C, 60–80% = B, 80–100% = **A**. Een percentiel van precies 20% hoort bij D. |
| Kleine aantallen | Een waarde met een bekende `n` onder **10** telt niet mee: niet in de referentie en niet als waarde van het gebied (status `onderdrukt`, grijs). Zoals bij `percentiel_8`. |
| Themalabel | Dezelfde regel als `percentiel_8`: labelscore A = 5 … E = 1, **gewogen gemiddelde van de indicatorscores** onder het onderdeel, thema of kwadrant (gewicht = aantal gebieden met data in de referentiegroep van die indicator, minimaal 1 bij drempels), afgerond naar de dichtstbijzijnde score (x,5 naar boven), en daarvan het label. Niet het gemiddelde van al afgeronde onderdeellabels. Een indicator zonder label telt niet mee. |
| Multi-selectie | Dezelfde regel over alle paren gebied × indicator (`GET /api/kompas/{config_id}/selectie?gebied_id=…`). |

**Voorbeeld:** thema Hittestress met *Stedelijk hitte-eiland effect* label A (score 5) en *Boomkroonbedekking* label D (score 2), beide op 13 buurten: (5 × 13 + 2 × 13) / 26 = 3,5, afgerond 4 = **B**.

**Waarom niet het slechtste label:** de Klimaatmonitor zegt niet hoe het themalabel ontstaat ([methodiek.md](../1-visie-concept/huidige-gebiedsmonitor/methodiek.md#labels-ae)). Tot SWF dat bevestigt, volgt het dezelfde aggregatie als de percentielklasse; dan is er één regel voor beide.

## In de API

Bij `label_ae` heeft elke node in de kompasboom `label` (`A`–`E`), `klasse` (de labelscore, 5 = A, 1 = E) en `klasse_kleur`; een indicator ook `label_bron`: `drempels` of `kwintiel`. Het antwoord heeft `klassen_legenda` (A–E met kleur en omschrijving) en `label_melding` zolang een indicator met een label op kwintielen rust. De kaart geeft per gebied `label`, `klasse` en `klasse_status`, en in `metadata` `label_bron` en `legenda_melding`.

## Kleuren

Kleurenblindvriendelijk, hetzelfde schema als de percentielklasse (`color_schemas`, `colorblind-safe`: rood → crème → blauw) in 5 stappen: **A = blauw**, E = rood. Geen data, onderdrukt of waterbuurt: grijs. Legenda en Kompas tonen bij kwintielen *"Voorlopige drempels (kwintielen)"*; het label staat ook als letter in het zonnediagram en in de tooltip, zodat de kleur niet de enige drager is.

## Drempels laden

**Klimaatmonitor SWF:** de drempels uit *Monitoring KA SWF, dialoog 2* (16-04-2025, blad *Final shortlist*) staan in [`db/stuurdata/indicator_labels_klimaatmonitor_swf.json`](../../db/stuurdata/indicator_labels_klimaatmonitor_swf.json): 9 van de 10 indicatoren (*Oppervlak groen per inwoner* heeft geen drempel en blijft op kwintielen). Ze worden geladen met `python init_data/scripts/load_sample.py --stap drempels`, bij de installatie na de use cases (de SWF-klimaatindicatoren komen uit `swf-definities`). Het is nog een **voorstel**: bevestiging door SWF staat open in [#222](https://github.com/TLaan/D-OmniTwin/issues/222) (A3). Bijzonderheden: *Waterdiepte tegen gevel* heeft een gat tussen 20 en 25 cm (geen label), bij *Gevoelstemperatuur* is A de middenband 18–23 °C (comfortabel), en bij *Trend GLG* is aangenomen dat een verhoging positief is.

Een eigen bestand `db/stuurdata/indicator_labels_<naam>.json` met dezelfde opbouw wordt ook geladen. Met de hand kan het ook in SQL:

Tabel `indicator_labels` (één rij per indicator × label):

| Kolom | Betekenis |
|---|---|
| `indicator_uuid` | de indicator |
| `label` | `A` (gunstigst) … `E` |
| `ondergrens` | inclusief; leeg = geen ondergrens |
| `bovengrens` | exclusief; leeg = geen bovengrens |
| `bron`, `opmerking` | herkomst, bijv. "Klimaatmonitor SWF, vastgesteld <datum>" |

```sql
-- voorbeeld (geen echte drempels): lager is beter, A onder 5
INSERT INTO indicator_labels (indicator_uuid, label, ondergrens, bovengrens, bron) VALUES
  ('<uuid>', 'A', NULL, 5, 'voorbeeld'), ('<uuid>', 'B', 5, 10, 'voorbeeld'), ('<uuid>', 'C', 10, 15, 'voorbeeld'),
  ('<uuid>', 'D', 15, 20, 'voorbeeld'), ('<uuid>', 'E', 20, NULL, 'voorbeeld')
ON CONFLICT (indicator_uuid, label) DO UPDATE
  SET ondergrens = EXCLUDED.ondergrens, bovengrens = EXCLUDED.bovengrens, bron = EXCLUDED.bron, bijgewerkt = now();
```

Of uit een CSV: `\copy indicator_labels (indicator_uuid, label, ondergrens, bovengrens, bron) FROM 'drempels.csv' CSV HEADER`. Een indicator met drempels toont geen melding "voorlopig" meer. Drempels weghalen (`DELETE FROM indicator_labels WHERE indicator_uuid = …`) zet hem terug op kwintielen.

**Waarom een eigen tabel en niet `kompas_indicator_scoring_regels.thresholds`:** de labels horen bij de indicator, niet bij een kompasprofiel (op de kaart gelden ze ook), en een tabel met een controle per kolom is eenvoudiger te laden en te controleren dan JSON.

## Open (wacht op SWF)

- **Drempels A3:** volgens Taeke ([#222, reactie](https://github.com/TLaan/D-OmniTwin/issues/222)) staan ze in het blad *Final shortlist* van de longlist klimaatindicatoren (16-04-2025): absolute klassen voor 9 van de 10 indicatoren, nog een voorstel uit een dialoogsessie. Na bevestiging door SWF laden in `indicator_labels`; dan vervalt de melding "voorlopig" voor die indicatoren.
- **Themalabel:** gemiddelde (zoals hier) of het slechtste label?
- **Welstand × buurt:** de Klimaatmonitor draait op welstand × buurt; die geometrie wacht op [#222](https://github.com/TLaan/D-OmniTwin/issues/222) (B1). Tot dan op CBS-buurten.

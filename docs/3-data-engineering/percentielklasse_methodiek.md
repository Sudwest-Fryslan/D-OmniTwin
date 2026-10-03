# Percentielklasse (8 × 12,5%): methodiek

> **Status:** ingevoerd in [#255](https://github.com/TLaan/D-OmniTwin/issues/255) (oktober 2026). De rekenwijze is een **aanname** tot [#222](https://github.com/TLaan/D-OmniTwin/issues/222) antwoord geeft over hoe de huidige SWF-monitor precies rekent.
> **Code:** `src/omnitwin/services/percentielklasse.py` (berekening en aggregatie), `kompas_service.py` (Kompas), `gebiedsmonitor_service.py` (kaart). Instelling: kolom `kompas_configuraties.classificatie` (migratie `V031__kompas_classificatie.sql`).
> **Tests:** `tests/unit/test_percentielklasse.py`, `tests/integration/test_percentielklasse_stack.py`, `tests/e2e/test_kaartmodus.py`.

Naast de Z-score ([zscore_methodiek.md](./zscore_methodiek.md)) kan D-OmniTwin een gebied in een **percentielklasse** plaatsen: in welke 12,5% van de vergelijkbare gebieden valt het? Zo werkt de huidige gebiedsmonitor van SWF ([methodiek.md](../1-visie-concept/huidige-gebiedsmonitor/methodiek.md)). Een rangorde is minder gevoelig voor uitschieters dan een Z-score.

## Instellen

De classificatie is data, per kompasprofiel:

| `kompas_configuraties.classificatie` | Kompas |
|---|---|
| `zscore` (standaard) | de huidige weergave, ongewijzigd |
| `percentiel_8` | elke indicator, elk onderdeel, thema en kwadrant krijgt een klasse 1–8 en de kleur van die klasse |

```sql
UPDATE kompas_configuraties SET classificatie = 'percentiel_8' WHERE naam = 'Klimaat Kompas';
```

Er is nog geen beheerscherm voor; de use case [`swf-kompasprofiel`](../../usecases/swf-kompasprofiel/README.md) noemt dezelfde keuze `percentielklasse`.

De **kaart** heeft een eigen keuze in de legenda, los van het profiel: *Percentielklasse*, *Werkelijke waarde* (standaard) of *Uit*. API: `GET /api/gebiedsmonitor/kaart_data/{gebiedstype_id}?indicator_uuid=…&modus=percentiel|waarde`.

## Rekenwijze (aanname tot #222)

| Stap | Regel |
|---|---|
| Referentiegroep | Dezelfde als de Z-score: gebiedstype + gemeente van het gebied, zonder waterbuurten, alleen scenario `current`, jaarlogica `zelfde_jaar` (met de terugval bij minder dan 5 gebieden). Eén SQL-functie: `zscore_referentie_waarden`. Op de kaart met een gekozen jaar: alle gebieden met een waarde in dat jaar. |
| Kleine aantallen | Een waarde met een bekende `n` onder **10** telt niet mee: niet in de referentie en niet als waarde van het gebied (status `onderdrukt`, grijs). De laad-API laat zulke waarden al weg; dit vangt waarden die buiten de laad-API zijn geladen. |
| Percentiel | Middenrang: (aantal waarden lager + ½ × aantal gelijk) / n. De waarde van het gebied zelf hoort bij n. Gelijke waarden krijgen hetzelfde percentiel, dus dezelfde klasse. |
| Polariteit | Bij "lager is beter" (`score_type` `+/-`, `-/-`, `positive_descending` of `inverse` in de scoringsregel) geldt 1 − percentiel. **Klasse 8 is altijd de gunstigste 12,5%, klasse 1 de ongunstigste.** |
| Klasse | `floor(percentiel × 8) + 1`, begrensd op 1..8. Grenzen bij 12,5%, 25%, …, 87,5%: een percentiel van precies 25% hoort bij klasse 3. |
| Aggregatie (onderdeel, thema, kwadrant) | Gewogen gemiddelde van de **indicatorklassen** eronder, gewicht = aantal gebieden met data in de referentiegroep van die indicator. Dus niet het gemiddelde van de al afgeronde onderdeelklassen. Daarna afronden naar de dichtstbijzijnde klasse, x,5 naar boven. Een indicator zonder klasse (geen data, onderdrukt, waterbuurt) telt niet mee. |
| Multi-selectie | Dezelfde regel over alle paren gebied × indicator in de selectie. Een indicator in een selectie van 3 gebieden heeft dus de afgeronde gewogen gemiddelde klasse van die 3. API: `GET /api/kompas/{config_id}/selectie?gebied_id=…&gebied_id=…`. |
| Klassescore | De klasse zelf (1–8). De methodiek van SWF noemt ook scores 1–6 met samengevoegde middenklassen; dat is niet overgenomen. |

**Voorbeeld uit de methodiek van SWF:** klassen 1, 3 en 4 op 88, 100 en 155 buurten geven (88 + 300 + 620) / 343 = 2,9, afgerond klasse 3.

## Kleuren

Kleurenblindvriendelijk, uit `color_schemas` (schema `colorblind-safe`: rood → crème → blauw), in 8 stappen. Klasse 1 = rood, klasse 8 = blauw. Geen data, onderdrukt of waterbuurt: grijs. Het kwadrant **Samenstelling** is neutraal (geen beter of slechter, zoals in de huidige monitor): daar een opeenvolgend blauw palet (schema `sequential-blue`), en het telt niet mee in de klasse van het hele Kompas. De kleuren staan in de database, niet in de code; de code heeft alleen dezelfde kleuren als terugval.

In de modus *werkelijke waarde* toont de legenda per kleur het bereik van de gebieden met die kleur (kleinste – grootste waarde) en het aantal gebieden.

## Open (wacht op #222)

- Rekent de huidige monitor met de klasse of met een continu percentiel, en met welke rangfunctie (middenrang, `percent_rank`, `cume_dist`)? Bij weinig gebieden geeft dat verschillende klassen.
- Hoe aggregeert de monitor over een multi-selectie?
- Welke klassescores (1–8 of 1–6) en welke weging (aantal gebieden of gebruikersweging)?
- Vergelijk na het antwoord 3 buurten × 10 indicatoren met de huidige monitor (advies 8 in [methodiek.md](../1-visie-concept/huidige-gebiedsmonitor/methodiek.md#advies)).

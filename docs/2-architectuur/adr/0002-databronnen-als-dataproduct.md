# 0002. Databronnen als dataproduct: ontsluiten met contract, metadata, semantiek en voorwaarden

- Status: voorgesteld
- Datum: 2026-10-01
- Issue: #182 (uitvoering van #20)

## Context

D-OmniTwin haalt nu zelf alle data op en bewerkt die (`ETL/`, `init_data/`, `scripts/`, samen ±16.000 regels). Het resultaat staat deels als bestand in git (sample-CSV's, geojson, tot #176 een CBS-CSV van 29 MB). Herkomst, licentie en betekenis van de data liggen verspreid vast: in kolommen, in losse JSON-mappings (`cbs_mapping_v3.json`) en in documentatie.

RFC #20 stelt dat D-OmniTwin de **Gold-laag / datamart** is (`indicatoren`, `gebied_data`). De ruwe en gecureerde verwerking (Bronze/Silver) hoort bij de bron of in een dataspace (FRLDS, FDS). D-OmniTwin consumeert "gecertificeerde dataproducten". De gap-analyse (`docs/3-data-engineering/etl_dataspace_gap_analyse.md`) werkt dat uit met een bronnenregister (`etl_bronnen`), job-tracking (`etl_runs`), een semantische laag (`etl_semantic_mapping`) en lineage (`data_lineage`).

Daarnaast:
- Andere gemeenten moeten bronnen kunnen hergebruiken zonder D-OmniTwin over te nemen.
- Herkomst, licentie en gebruiksvoorwaarden moeten machineleesbaar zijn: voor de bronvermelding, de AVG en de IAMA.
- Op termijn moet het geheel als **dataspace** te beschrijven en neer te zetten zijn (DSP-catalogus en -contracten, #32), zonder ombouw.

## Besluit

**1. We kijken naar data vanuit de functie "ontsluiten van brondata".** Een **bron** is een zelfstandig **dataproduct** met een vaste opbouw:

```
bronnen/<naam>/
  bron.json        metadata (DCAT-AP-NL), incl. blok "ontsluiting"
  contract.yaml    datacontract (ODCS): schema, eenheden, sleutels, actualiteit, kwaliteitsregels
  etl/             extract, transform (mapping naar begrippen, afleiding, codecontrole), load
  schema.sql       eigen databaseschema bron_<naam> (#137)
  tests/           kwaliteitstests die het contract toetsen
  README.md
```

**2. Elke bron is op vijf manieren beschreven, in open standaarden:**

| Aspect | Standaard |
|---|---|
| Datacontract | Open Data Contract Standard (ODCS) |
| Metadata en catalogus | DCAT-AP-NL |
| Semantiek (ontologie) | SKOS + NL-SBB voor begrippen, UCUM/QUDT voor eenheden, CBS-gebiedscodes, GGM voor gemeentelijke gegevens (#38) |
| Gebruiksvoorwaarden | ODRL |
| Herkomst | PROV-O (via `data_lineage`) |

Er is **één gedeeld begrippenkader** (SKOS) voor indicatoren, Kompas-thema's en gebiedstypen. Bronnen mappen naar begrippen, niet direct naar tabelkolommen.

**3. Governance voor ontsluiting zit op de bron.** `bron.json` legt vast:
- toegang (open, beperkt of intern);
- bronhouder;
- licentie en gebruiksvoorwaarden;
- doelbinding;
- grondslag, DPIA en IAMA waar nodig;
- autorisatie;
- minimale aantallen.

Afgedwongen wordt dat via de rechten op het schema per bron, de catalogus en, extern, het beleid van de dataspace.

**4. Contract tussen bron en kern.** Een bron levert waarden in de vorm van `gebied_data` en publiceert zich in het bronnenregister `etl_bronnen` (#20). De kern (de Gold-laag) leest alleen views en het register, en weet niets van ETL. `etl_runs`, `etl_semantic_mapping` en `data_lineage` (#20) zijn de vaste registratie van runs, mapping en herkomst.

**5. De definitie staat in git, de runtime-staat in de database.** `bronnen/<naam>/` is de versiebeheerde, geteste definitie. Bij het laden komt de bron in `etl_bronnen`, met de runtime-staat (actief, TTL, laatste run). De beheerpagina (#20) beheert die staat.

**6. Een bron kan in drie vormen draaien, zonder wijziging van de kern of de use cases:**
1. **in-process**, met een cache (nu; #20 virtualisatie niveau 1);
2. **als eigen container of job**, periodiek ververst;
3. **extern of in een dataspace**, via een connector (#20 niveau 2, #32/#33).

**7. Wat te downloaden is, staat niet in git.** In git staan alleen de definitie (recept, contract, metadata, mapping) en data die niet te downloaden is: demodata (`bron=DEMO`), eigen bewerkingen en uploads. Gedownloade data staat in een cache (`$DATA_CACHE`, volume `bron-cache`).

**8. De catalogus is exporteerbaar** als JSON-LD (DCAT + ODRL), bijvoorbeeld via `GET /api/catalogus`. Dat is de basis voor een DSP-catalogus, data.overheid.nl en de bronvermelding in de app.

**9. D-OmniTwin is op termijn ook producent:** de Kompas- en Z-scores worden zelf een bron met contract, metadata en voorwaarden (#20, vraag 4).

## Alternatieven

- **ETL in de applicatie houden, zoals nu.** Snel, maar niet herbruikbaar. Herkomst en voorwaarden zijn niet machineleesbaar, en de stap naar een dataspace vraagt later een ombouw.
- **Alles direct uit een dataspace halen (alleen vorm 3).** Dat is het doel, maar FRLDS/FDS levert nog niet de benodigde dataproducten. Zonder vorm 1 werkt D-OmniTwin dan niet out of the box.
- **Bronnen alleen in de database definiëren** (`etl_bronnen` via de beheerpagina, zonder bestanden). Bronnen zijn dan niet reviewbaar, niet testbaar in de CI en niet als pakket te delen met andere gemeenten. In dit besluit blijft de database de runtime-staat.
- **Zware tooling vanaf het begin** (OpenMetadata, Great Expectations, dbt, een triple store). Dat is te veel infrastructuur voor een installatie bij een gemeente. Het kan later op dezelfde bestanden aansluiten.
- **Eigen formaten in plaats van ODCS, DCAT, SKOS en ODRL.** Minder leerwerk, maar dan geen aansluiting op Forum Standaardisatie (#63), data.overheid.nl en het dataspace-protocol (#32).

## Gevolgen

- **Makkelijker:**
  - een bron hergebruiken (andere gemeente, dataspace);
  - herkomst en licentie tonen;
  - kwaliteit per bron testen;
  - een bron later los of extern draaien;
  - de catalogus publiceren.
- **Moeilijker:** een nieuwe bron toevoegen vraagt meer dan een script: contract, metadata, mapping naar begrippen en tests. Een sjabloon en een voorbeeldbron (`cbs-kerncijfers`) maken dat herhaalbaar.
- **Uitvoering** in 0.2.0/0.3.0 (#182, fase 4: "uitvoering #20"):
  1. sjabloon, register en contract, met `cbs-kerncijfers` en `cbs-geometrie` als eerste bronnen;
  2. de overige bronnen, één per PR;
  3. het begrippenkader en de catalogus-export.

  `ETL/`, `init_data/sample/` en `init_data/fryslan/` verdwijnen.
- **Open:**
  - het dataspace-protocol: iSHARE of DSP + FSC (#32, #33);
  - de keuze van de eerste externe dataspace-bron (FRLDS);
  - het definitieve formaat van het begrippenkader (raakt #120, de ontologie-governance).

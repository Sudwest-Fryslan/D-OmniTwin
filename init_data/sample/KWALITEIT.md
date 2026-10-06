# Datakwaliteit sample_indicatoren.csv

Stand na https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/236: de sample bevat alleen nog wat niet open is of nog geen adapter heeft. 520 regels, 40 indicatoren, 13 buurten. De vorige telling (#60: 1.132 regels, 87 indicatoren; na #159: 728 regels, 56 indicatoren) staat in de git-geschiedenis.

## Herkomst (`bron`)

| Bron | Regels | Status |
|---|---:|---|
| `BAG` | 168 | open (Kadaster BAG), per buurt berekend; adapter volgt |
| `Kadaster BAG Fryslân 2026` | 84 | idem |
| `RVO EP-Online 2026-02` | 60 | open met API-sleutel; adapter volgt |
| `Berekend: EP-Online / BAG Fryslân` | 12 | idem (dekking = labels ÷ woningen) |
| `OpenStreetMap / Overpass API 2026` | 60 | open (ODbL); adapter volgt |
| `DEMODATA: plaatsvervanger voor de interne bron SWF-gebiedsmonitor, …` | 104 | demodata (8 interne indicatoren, alle 13 buurten) |
| `DEMODATA: gemiddelde van Bolsward-Noord en Bolsward-Noordoost, …` | 32 | demodata (BU19000002 bij BAG, EP-Online en OpenStreetMap) |

Opgehelderd in #236: de 48 regels zonder bron waren Politie-cijfers (StatLine 47018NED, nu use case `politie-misdrijven`); de 96 regels met een uploadbestandsnaam als bron (`<uuid>_d_cbs_buurten.json`, de uuid is de indicator) zijn interne indicatoren van de SWF-gebiedsmonitor, nu als demodata gemarkeerd.

## Overige kolommen

- `kwaliteit` is overal leeg.
- `eenheid` en `categorie` zijn niet overal gevuld en niet genormaliseerd; de definities (met eenheid) staan in `db/stuurdata/indicatoren.csv`.
- `interpretatie_logica`: `pos_is_pos`, `-/+` en `N/A` door elkaar (#60).

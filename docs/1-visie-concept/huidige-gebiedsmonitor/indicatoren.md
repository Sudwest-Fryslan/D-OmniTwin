# Indicatoren van de huidige gebiedsmonitor

Stand 02-10-2026. De volledige indicatorenlijst van de Basis monitor en de Klimaatmonitor, met UUID. Terug naar [het overzicht](./README.md).

**Kern:**
- **228 definities** in de monitor (februari 2026), waarvan **49 met waarden**. **30 UUID's** staan al in de D-OmniTwin-repo (vooral in de CBS- en sample-data), dezelfde sleutel.
- De structuur is 4 kwadranten, 12 thema's en 33 onderdelen, soms met een extra niveau (bijv. *groene druk*, *Hitte*).
- De 10 indicatoren van de **Klimaatmonitor** hebben status A. Ze hangen in de Basis monitor ook onder *Openbare ruimte › Klimaat*.
- Een groot deel van de indicatoren is **subjectief** (enquête): ±69 in de inventaris. Daarvoor heeft SWF nog geen bron op buurtniveau.

## Hoe deze lijst is gemaakt

- **Hiërarchie** (kwadrant › thema › onderdeel › extra niveau): uit de voortgangslijst per indicator die het data-team van SWF bijhoudt. Waar een indicator daar niet (meer) onder de huidige naam in staat, is de plek overgenomen uit de live sunburst.
- **UUID en status:** uit de definities in de monitor (export februari 2026), gekoppeld op naam.
- **Waarden in monitor:** of er in februari 2026 waarden waren, en op welk gebiedstype. Alleen ja/nee, geen waarden.
- **UUID in D-OmniTwin:** de UUID komt ergens in deze repository voor (op `main`, 02-10-2026).
- **Status:** O = operationeel, C = concept, A = Klimaatmonitor (betekenis navragen), B = beëindigd.
- Een indicator die onder meer onderdelen hangt (bijv. *Groen* bij Inrichting en bij Onderhoud), staat er meer keer in, met dezelfde UUID. Twee namen hebben twee UUID's (*Werkzamen*, *Waterdiepte op straat*); beide staan erbij.
- Vijf oudere werktitels uit de voortgangslijst zonder eigen definitie zijn weggelaten; het zijn eerdere namen van klimaatindicatoren die hieronder wel staan (o.a. "Verandering GLG nu t.o.v. 2050" → *Trend GLG naar 2050*, "Verhouding oppervlakte water/verharding" → *Aandeel water t.o.v. verhard*). Eén testdefinitie is weggelaten.

## Samenvatting per thema

| Kwadrant | Thema | Regels | Unieke UUID's | Met waarden | UUID in D-OmniTwin |
|---|---|---|---|---|---|
| Kwaliteit fysieke leefomgeving | Openbare ruimte | 34 | 33 | 10 | 6 |
| Kwaliteit fysieke leefomgeving | Verkeer | 12 | 12 | 5 | 2 |
| Kwaliteit fysieke leefomgeving | Wonen | 14 | 13 | 2 | 2 |
| Kwaliteit sociale leefomgeving | Mienskip | 22 | 22 | 2 | 2 |
| Kwaliteit sociale leefomgeving | Veiligheid | 21 | 20 | 1 | 4 |
| Kwaliteit sociale leefomgeving | Voorzieningen | 21 | 20 | 8 | 1 |
| Kwaliteit van leven | Gezondheid | 20 | 20 | 7 | 5 |
| Kwaliteit van leven | Meedoen | 19 | 19 | 1 | 2 |
| Kwaliteit van leven | Opgroeien | 3 | 3 | 1 | 1 |
| Kwaliteit van leven | Rondkomen | 13 | 14 | 2 | 2 |
| Samenstelling | Bebouwing | 17 | 17 | 3 | 0 |
| Samenstelling | Bevolking | 34 | 35 | 8 | 3 |
| **Totaal** | **12** | **230** | **224** | **49** | **30** |

## Basis monitor

### Kwaliteit fysieke leefomgeving

| Thema | Onderdeel | Indicator | UUID | Status | Waarden in monitor (feb. 2026) | UUID in D-OmniTwin |
|---|---|---|---|---|---|---|
| Openbare ruimte | Inrichting | Groen | `18ee5ec3-d8de-4100-9e49-ba60e9a95f80` | O | nee | nee |
| Openbare ruimte | Inrichting | Speelplekken kinderen | `a677997b-8d50-4608-8d8b-97b9ca5d8e23` | O | nee | nee |
| Openbare ruimte | Inrichting | Sport- en spelplekken | `eac0ea06-1a07-4aa2-abfa-41fc9b7bb53d` | O | nee | nee |
| Openbare ruimte | Inrichting | Straatmeubilair | `282cb12e-b46a-4ace-abbf-cf3eb907189f` | O | nee | nee |
| Openbare ruimte | Klimaat | Maatregelen inwoners | `5e457881-a811-4317-9d49-94288e912fb0` | O | nee | nee |
| Openbare ruimte | Klimaat › Droogte | Trend GLG naar 2050 | `2d6bdaba-3832-40cc-acae-950883f1aa76` | A | ja (SWF welstandsgebieden) | ja |
| Openbare ruimte | Klimaat › Droogte | GLG - veenweide | `8a921563-e6e3-45e4-a8e3-5c890c619956` | A | ja (CBS buurten, SWF welstandsgebieden) | nee |
| Openbare ruimte | Klimaat › Droogte | GLG - kleiweide | `b334ce1d-3420-4863-9c10-af8f238dfd6c` | A | ja (CBS buurten, SWF welstandsgebieden) | nee |
| Openbare ruimte | Klimaat › Hemelwateroverlast | Waterdiepte tegen gevel | `89b6274f-9372-4784-8ba3-924b6c7e4d7d` | A | ja (CBS buurten) | ja |
| Openbare ruimte | Klimaat › Hemelwateroverlast | Aandeel water t.o.v. verhard | `0bbd30e5-08f5-4499-b6ca-cdda990720dc` | A | ja (CBS buurten, CBS buurten bebouwde komgrens, SWF welstandsgebieden) | ja |
| Openbare ruimte | Klimaat › Hitte | Aandeel bladerdek per buurt | `66ee35d7-8046-470a-8e99-efce744cb97d` | A | ja (CBS buurten) | nee |
| Openbare ruimte | Klimaat › Hitte | Afstand tot koele plek | `bf4e5b8f-6b0a-4632-b9b4-8e29d025e68c` | A | ja (CBS buurten, SWF welstandsgebieden) | ja |
| Openbare ruimte | Klimaat › Hitte | Gevoelstemperatuur | `fdb4c11b-60ca-4ea1-86b8-6855a83344ee` | A | ja (CBS buurten, SWF welstandsgebieden) | nee |
| Openbare ruimte | Klimaat › Hitte | Vegetatie op daken | `eafba4fe-c2e0-452d-acaf-f6707388feee` | O | nee | nee |
| Openbare ruimte | Klimaat › Hitte | Verkoeling | `edb2e8f2-0081-4b11-a4b7-8bd8e05cf89e` | O | nee | nee |
| Openbare ruimte | Klimaat › Hitte, Wateroverlast | Oppervlakte groen (openbare ruimte) | `dcb66a35-5711-477f-a89f-ea72c5be80a9` | O | nee | nee |
| Openbare ruimte | Klimaat › Hitte, Wateroverlast | Overlast weer | `90c18e2b-c164-4a59-83fe-367e64fceec2` | O | nee | nee |
| Openbare ruimte | Klimaat › Hittestress | Oppervlak groen per inwoner | `97f53738-3439-4c28-8cac-046a52c65248` | A | ja (CBS buurten, SWF welstandsgebieden) | ja |
| Openbare ruimte | Klimaat › Verdroging | Oppervlakte verharding | `104dedf1-87b0-480c-afcd-2cb5eedc8654` | O | nee | nee |
| Openbare ruimte | Klimaat › Verdroging, Hitte | Oppervlakte vegetatie (NDVI) | `0b069c82-c6a6-4918-a87b-f49dca3d93e1` | O | nee | nee |
| Openbare ruimte | Klimaat › Verdroging, Hitte, Wateroverlast | Oppervlakte water | `1d52806b-55fe-4328-a09e-f3a2e38e3f7c` | O | nee | nee |
| Openbare ruimte | Klimaat › Wateroverlast | Afvoer water | `ba212eab-e5a3-4511-80a7-a7709523818c` | O | nee | nee |
| Openbare ruimte | Klimaat › Wateroverlast | Gemiddeld Laagste Grondwaterstand | `a4f84d1c-3263-4229-ad95-615924cb7852` | C | ja (CBS buurten, CBS buurten bebouwde komgrens) | ja |
| Openbare ruimte | Klimaat › Wateroverlast | Waterdiepte op straat | `c4e1b3bb-e4ce-4cd0-bd52-219f4a9f5df3`<br>`f6eafa70-9383-4de6-bd2a-e47309843437` | C<br>A | nee<br>nee | nee<br>nee |
| Openbare ruimte | Onderhoud | Fietspaden | `0261bbb5-65ba-4106-b58c-b3ca6e05c8f0` | O | nee | nee |
| Openbare ruimte | Onderhoud | Groen | `18ee5ec3-d8de-4100-9e49-ba60e9a95f80` | O | nee | nee |
| Openbare ruimte | Onderhoud | Schoonhouden | `365e6c71-e729-44fa-a8b3-13d084815c63` | O | nee | nee |
| Openbare ruimte | Onderhoud | Straatmeubilair | `282cb12e-b46a-4ace-abbf-cf3eb907189f` | O | nee | nee |
| Openbare ruimte | Onderhoud | Trottoirs | `2298a045-ac31-4154-9fe2-08dbe131d83e` | O | nee | nee |
| Openbare ruimte | Onderhoud | Wegen | `694bc048-dffe-4c5d-b362-b037c3de9e98` | O | nee | nee |
| Openbare ruimte | Verloedering | Bekladdingen | `4a4e9cb6-ef0d-4b29-9d26-bc19eda0339e` | O | nee | nee |
| Openbare ruimte | Verloedering | Hondenpoep | `5c75d4a3-3ace-4c95-a051-7040defecefa` | O | nee | nee |
| Openbare ruimte | Verloedering | Rommel | `055d550f-2af8-44cd-87c5-13afdf9aa38f` | O | nee | nee |
| Openbare ruimte | Verloedering | Vernielingen | `13fa6584-2935-4209-bbe3-da04706d4c3e` | O | nee | nee |
| Verkeer | Bereikbaarheid en parkeren | Afstand treinknooppunt | `9d54fe9e-3b54-48e6-ad11-18437cc49dc0` | O | ja (CBS buurten) | nee |
| Verkeer | Bereikbaarheid en parkeren | Afstand treinstation | `c4185251-746b-4a19-b3a4-819ef65081c0` | O | ja (CBS buurten) | nee |
| Verkeer | Bereikbaarheid en parkeren | Bereikbaarheid | `042564f9-3a45-4901-8f14-417622f8b4a0` | O | nee | nee |
| Verkeer | Bereikbaarheid en parkeren | Openbaar vervoer | `1043837d-ce3f-486e-b611-c6940067d6c8` | O | nee | nee |
| Verkeer | Bereikbaarheid en parkeren | Parkeerdruk | `a6e0c52d-c214-4f66-9548-3ee43dd06826` | O | nee | nee |
| Verkeer | Bereikbaarheid en parkeren | Personenauto's per huishouden | `461d542b-b8be-4510-9dd0-5ba554b818cb` | O | ja (CBS buurten) | ja |
| Verkeer | Bereikbaarheid en parkeren | Personenauto's naar oppervlakte | `88192b70-faa9-4108-a473-302aa0f624a9` | O | ja (CBS buurten) | ja |
| Verkeer | Bereikbaarheid en parkeren | Afstand tot oprit hoofdverkeersweg | `1aef4348-35dd-4439-aa1b-0ccd57d92809` | O | ja (CBS buurten) | nee |
| Verkeer | veiligheid en overlast | Overlast autoverkeer | `b0e5ad11-8f42-4733-8e1a-0e5407e6c5fb` | O | nee | nee |
| Verkeer | veiligheid en overlast | Overlast gestalde fietsen | `8ce45dd7-e60d-4356-814e-4e9fe519bf07` | O | nee | nee |
| Verkeer | veiligheid en overlast | Verkeersongevallen | `55ba59c5-19fe-4de3-97f2-97422b4b4f3b` | O | nee | nee |
| Verkeer | veiligheid en overlast | Verkeersveiligheid | `4e5dc6ef-4cec-4879-93df-e6a41fa34af6` | O | nee | nee |
| Wonen | Beschikbaar betaalbaar | prijs-kwaliteit | `5c86f538-76fe-454e-a858-297c5d29e9fd` | O | nee | nee |
| Wonen | Beschikbaar betaalbaar | Verhuiswens | `e5a1cf06-6119-4a75-a78b-793ac63da9c4` | O | nee | nee |
| Wonen | Functionele kwaliteit | Geschikte leefsituatie | `c140f420-0263-4f30-b899-bb96458c569d` | O | nee | nee |
| Wonen | Functionele kwaliteit | Incourante eensgezins | `0365aba9-4555-44c9-86a4-3d532d2e5433` | O | nee | nee |
| Wonen | Functionele kwaliteit | Indeling | `c7378440-b10a-49c5-a1cd-6ed9e6954f51` | O | nee | nee |
| Wonen | Functionele kwaliteit | Omvang | `63c022a2-0832-4de8-8cf2-81942d4ae39b` | O | nee | nee |
| Wonen | Functionele kwaliteit | Sfeer | `499ff5ac-9c79-4d3d-ae47-40b505582e52` | O | nee | nee |
| Wonen | Technische kwaliteit | Definitief energielabel | `81ccf247-0449-40e0-a99c-a67019f272e4` | O | ja (CBS buurten) | ja |
| Wonen | Technische kwaliteit | Geluidsisolatie | `ea01bdeb-14a2-42b7-9234-51a24d72c24c` | O | nee | nee |
| Wonen | Technische kwaliteit | Gemiddeld energielabel | `3c2d0ca0-3a6d-4f53-809f-f82fa9b9fd22` | O | ja (CBS buurten) | ja |
| Wonen | Technische kwaliteit | Onderhoud woningen buurt | `cc1715ea-156f-403c-9841-f06d9dd6ab05` | O | nee | nee |
| Wonen | Technische kwaliteit | Onderhoud woningen buurt | `cc1715ea-156f-403c-9841-f06d9dd6ab05` | O | nee | nee |
| Wonen | Technische kwaliteit | Ventilatie | `2aa4c162-29c3-4313-8a42-0deea6ef0d68` | O | nee | nee |
| Wonen | Technische kwaliteit | Warmte isolatie | `bafc1045-8674-486b-9100-647b397443df` | O | nee | nee |

### Kwaliteit sociale leefomgeving

| Thema | Onderdeel | Indicator | UUID | Status | Waarden in monitor (feb. 2026) | UUID in D-OmniTwin |
|---|---|---|---|---|---|---|
| Mienskip | Actief betrokken | Actief buurt | `5bdffb43-4e09-4fcc-8cf7-ab8fa0b48442` | O | nee | nee |
| Mienskip | Actief betrokken | Buren geholpen | `ffb5832e-d8ec-4f21-be63-4ee591348932` | O | nee | nee |
| Mienskip | Actief betrokken | Mantelzorger | `7b4a6b5f-7d6a-46ef-8a7d-7b3ee28a014c` | O | ja (CBS buurten) | ja |
| Mienskip | Actief betrokken | Medeverantwoordelijk | `b89b9508-6417-429e-b5b6-97671ec882f4` | O | nee | nee |
| Mienskip | Actief betrokken | Oogje in het zeil | `493056d0-9108-4aa5-94fe-35c19ca4dc21` | O | nee | nee |
| Mienskip | Actief betrokken | Vertrouwen in gemeente | `9ff62049-cabe-449b-937b-9bb5993eda6f` | O | nee | nee |
| Mienskip | Actief betrokken | Vrijwilliger | `9b168456-9219-4c3b-af16-636662a74155` | O | ja (CBS buurten) | ja |
| Mienskip | Omgang integratie | Buurtgenoten | `2b83af90-b647-45f9-a80d-9524df4516c5` | O | nee | nee |
| Mienskip | Omgang integratie | Discriminatie | `10c6d4df-44ef-4eb8-b4ab-8987012b7b16` | O | nee | nee |
| Mienskip | Omgang integratie | Etnische groepen | `dd76185d-5e66-4dd9-aeab-82ce845cb14f` | O | nee | nee |
| Mienskip | Omgang integratie | Jong en oud | `52ec4615-dd5c-47d4-a898-44d2aa9edfe8` | O | nee | nee |
| Mienskip | Omgang integratie | Student en ander | `b01d9133-4a0f-41fa-a5f7-cadcea55e8a7` | O | nee | nee |
| Mienskip | Sociale samenhang | 10+ jaar buurt | `57881985-6961-4dc8-8d85-0130e871f842` | O | nee | nee |
| Mienskip | Sociale samenhang | 10+ jaar gemeente | `597e30ae-df0a-43f6-8675-6dfb8db6b774` | O | nee | nee |
| Mienskip | Sociale samenhang | 10+ jaar woning | `4f87a602-7f53-4090-a0b4-bd2608b284aa` | O | nee | nee |
| Mienskip | Sociale samenhang | Elkaar kennen | `5b55a528-6495-4acb-b2e2-4b8cf58d7b9b` | O | nee | nee |
| Mienskip | Sociale samenhang | Gehecht | `8c917dd9-1cdd-436f-a396-7107ac4e39a5` | O | nee | nee |
| Mienskip | Sociale samenhang | Prettige buurt | `f420a15b-7f99-4d19-86d5-5569222c2648` | O | nee | nee |
| Mienskip | Sociale samenhang | Saamhorigheid | `fb9f9529-dc8f-401e-b0e5-e7a5f4ef3ad5` | O | nee | nee |
| Mienskip | Sociale samenhang | Thuis voelen | `3a5eb073-170f-45a2-b07d-65f1c7d77a30` | O | nee | nee |
| Mienskip | Sociale samenhang | Verhuisd | `cd83362b-006f-4381-9663-420c3f729102` | O | nee | nee |
| Mienskip | Sociale samenhang | Verhuisd binnen buurt | `ccf475b4-d2cd-4934-a607-aeb54d982115` | O | nee | nee |
| Veiligheid | Dreiging en geweld | gevoel onveilig | `6d56f7bc-aaf6-441e-a423-f19b3a825a79` | O | nee | nee |
| Veiligheid | Dreiging en geweld | Geweld | `784f5a85-7dcc-43fe-89a1-df4df500e34a` | O | nee | nee |
| Veiligheid | Dreiging en geweld | idee bedreiging | `379cd3a8-409e-499d-beac-02682fd13bcf` | O | nee | nee |
| Veiligheid | Dreiging en geweld | idee geweldsdelicten | `b6c4e4fd-2ec9-4427-92b6-b28b64c125ab` | O | nee | nee |
| Veiligheid | Dreiging en geweld | idee lastigvallen | `6f354ae4-db0a-4645-bec6-8218b4ab572d` | O | nee | nee |
| Veiligheid | Dreiging en geweld | idee wapens | `ec1d551c-9fb1-4649-a9cd-5279a62b77e6` | O | nee | nee |
| Veiligheid | Overlast | dronken personen | `7524a0df-fc76-4755-a855-cbcb368a43be` | O | nee | nee |
| Veiligheid | Overlast | drugs | `48edd30f-ef82-4820-8e80-7eb8daf82963` | O | nee | nee |
| Veiligheid | Overlast | geluid | `b558af0f-fa63-4735-a27c-79d12813ee1e` | O | nee | nee |
| Veiligheid | Overlast | jongeren | `3bbd1382-eaae-4e2c-ae48-caa40c112340` | O | nee | nee |
| Veiligheid | Overlast | omwonenden | `3fa946ce-b007-4748-9fab-c838c7ccb9dc` | O | nee | nee |
| Veiligheid | Overlast | wonen | `ee076c87-95e8-4f5a-a753-e31fc05a0eb8` | O | ja (CBS buurten) | nee |
| Veiligheid | Overlast | woonomgeving | `b8f453e4-522a-4c9d-b4d8-1f0b25594bb9` | O | nee | nee |
| Veiligheid | Vermogensdelicten | beschadiging auto's | `b7090c23-7495-48c2-bfb3-cbfb7140386f` | O | nee | ja |
| Veiligheid | Vermogensdelicten | diefstal fiets | `3ca8572d-cc03-4fd9-9bc9-e1cd0fc0a627` | O | nee | ja |
| Veiligheid | Vermogensdelicten | diefstal fietsen | `35cd7fcf-3ddd-49b8-9703-9b07dbf280db` | O | nee | nee |
| Veiligheid | Vermogensdelicten | inbraak auto | `92137246-e0f1-493d-97a8-e4a5660a99fb` | O | nee | ja |
| Veiligheid | Vermogensdelicten | inbraak auto's | `fab534cc-537b-46e6-ab80-1fbacadbfca7` | O | nee | nee |
| Veiligheid | Vermogensdelicten | inbraak woning | `d90d2b4c-4bce-428c-834a-1cc8113958e4` | O | nee | ja |
| Veiligheid | Vermogensdelicten | inbraak woning | `d90d2b4c-4bce-428c-834a-1cc8113958e4` | O | nee | ja |
| Veiligheid | Vermogensdelicten | slachtoffer inbraak | `9c3224e6-7b1a-4284-a658-52eca918c750` | O | nee | nee |
| Voorzieningen | Maatschappelijke | Apotheek | `162f1888-66d9-428e-bcf5-6af5a3aa4ada` | O | ja (CBS buurten) | nee |
| Voorzieningen | Maatschappelijke | Basisscholen | `6ecbc704-ce1d-49ea-8914-48b3a723d9fc` | O | nee | nee |
| Voorzieningen | Maatschappelijke | Basisschool | `3d913daa-d2e2-4ab2-bf2e-61c5ef2ab0de` | O | nee | nee |
| Voorzieningen | Maatschappelijke | Boodschappen | `a9752cb7-7404-4c46-9f45-49697f8d7d36` | O | nee | nee |
| Voorzieningen | Maatschappelijke | BSO | `fe677e77-6d01-4642-90a4-f9453f9eb462` | O | nee | nee |
| Voorzieningen | Maatschappelijke | Grote supermarkt | `6c90cc6f-29a7-4512-b037-de675112c97b` | O | ja (CBS buurten) | nee |
| Voorzieningen | Maatschappelijke | Huisarts | `0ed37b61-f13d-446b-b108-70bb09af98e0` | O | ja (CBS buurten) | ja |
| Voorzieningen | Maatschappelijke | Kinderdagverblijf | `8cb1b47c-1474-4eba-8a1e-f4e63f374c86` | O | ja (CBS buurten) | nee |
| Voorzieningen | Maatschappelijke | Medische zorg | `dc666cf8-b0ee-4fc7-8cbd-ee5d7666b7d3` | O | nee | nee |
| Voorzieningen | Maatschappelijke | Middelbare school | `6b252d60-caca-4651-91de-5a6e982ea634` | O | nee | nee |
| Voorzieningen | Maatschappelijke | Ondersteuning | `399faf44-3858-4477-8949-99e1e65f734b` | O | nee | nee |
| Voorzieningen | Maatschappelijke | Overige levensmiddelen | `e4eb972b-219d-4ae8-8b7d-b9fa1613cc77` | O | nee | nee |
| Voorzieningen | Sociaal culturele | Bibliotheek | `c70a2b96-510c-434f-ba69-2c575eb9b669` | O | ja (CBS buurten) | nee |
| Voorzieningen | Sociaal culturele | Binnensport | `d3e66467-9425-48be-92bf-e6cf27cc15d6` | O | nee | nee |
| Voorzieningen | Sociaal culturele | Buitensport | `4bfb21eb-0dfe-4e53-97b8-700bb88c9587` | O | nee | nee |
| Voorzieningen | Sociaal culturele | Café | `f2d04e1e-404e-49b6-a5fc-8c600aef782b` | O | ja (CBS buurten) | nee |
| Voorzieningen | Sociaal culturele | Cafetaria | `3d5f1d64-0e67-493c-8213-b20f07fd699f` | O | nee | nee |
| Voorzieningen | Sociaal culturele | Ontmoeting | `2d11e901-25f1-4045-b75f-004cc7e4b4ec` | O | nee | nee |
| Voorzieningen | Sociaal culturele | Restaurant | `1bec5763-5216-484d-95fe-474a4296a341` | O | ja (CBS buurten) | nee |
| Voorzieningen | Sociaal culturele | Zwembad | `cf630c8c-d152-4455-bca5-b3f1fe48dab0` | O | ja (CBS buurten) | nee |
| Voorzieningen | Sociaal culturele | Zwembad | `cf630c8c-d152-4455-bca5-b3f1fe48dab0` | O | ja (CBS buurten) | nee |

### Kwaliteit van leven

| Thema | Onderdeel | Indicator | UUID | Status | Waarden in monitor (feb. 2026) | UUID in D-OmniTwin |
|---|---|---|---|---|---|---|
| Gezondheid | Eigenkracht | Belemmerd | `3c09922b-98ac-448c-8384-d7b8b10f15a7` | O | nee | nee |
| Gezondheid | Eigenkracht | Beperkte functionaliteit | `3dee52f6-edfb-4fe9-9abe-f222315d954f` | O | ja (CBS buurten) | nee |
| Gezondheid | Eigenkracht | Draad oppakken | `2eed6515-267b-4552-85cd-2bf7489c62fd` | O | nee | nee |
| Gezondheid | Eigenkracht | Grip op leven | `54f1c5c9-c7d3-486e-abca-4f4681276def` | O | nee | nee |
| Gezondheid | Eigenkracht | Hulp | `86c91137-c719-4a26-b48c-aab85f6bd0f1` | O | nee | nee |
| Gezondheid | Eigenkracht | Hulp organiseren | `324f1ce6-1684-444a-ab0e-2ee5bab6138c` | O | nee | nee |
| Gezondheid | Eigenkracht | Zelfregie | `68190acc-0018-4c00-8617-b30b5e315c5c` | O | nee | nee |
| Gezondheid | Functioneren | Beperking | `74eac5c2-5828-4bc4-80c9-d09f3dd5cf5e` | O | ja (CBS buurten) | nee |
| Gezondheid | Functioneren | Beperking gehoord | `6784d8c0-5439-4be4-9a83-8a926a4a1484` | O | nee | nee |
| Gezondheid | Functioneren | Beperking zicht | `95cfcccd-8bf1-4b72-8ebe-03a09aaf529b` | O | nee | nee |
| Gezondheid | Functioneren | Chronische aandoening, 2 of meer | `babc4c46-d1c1-444c-af11-2bc1154af66d` | O | nee | nee |
| Gezondheid | Functioneren | Geluk | `aeb8a326-9b6b-4072-a6e4-f194b6250683` | O | nee | nee |
| Gezondheid | Functioneren | Gezondheid | `311a6449-b145-4678-b51e-ac4e342dd1bf` | O | nee | ja |
| Gezondheid | Functioneren | Tevreden leven | `336d70fd-8895-4036-aecb-ef16dbb17b98` | O | nee | nee |
| Gezondheid | Functioneren | Verwachting leven | `acfc43a5-c625-4680-88f5-67d0433fbe43` | O | nee | nee |
| Gezondheid | Leefstijl | Alcohol | `c7534c64-b1ad-4100-ba3e-58d8d8fae9d2` | O | ja (CBS buurten) | nee |
| Gezondheid | Leefstijl | Bewegen | `64470009-7467-4a34-8f3c-b44d896a5364` | O | ja (CBS buurten) | ja |
| Gezondheid | Leefstijl | Overgewicht | `34e36ae1-4132-4555-a4fc-d16b039d467e` | O | ja (CBS buurten) | ja |
| Gezondheid | Leefstijl | Overmatig drinken | `1ed22149-7fed-4466-a3b8-dfd7ff28f5b5` | O | ja (CBS buurten) | ja |
| Gezondheid | Leefstijl | Roken | `a4780646-844e-4221-b07a-b4f4ade25059` | O | ja (CBS buurten) | ja |
| Meedoen | Deelname | Evenement | `04b8badd-50d3-4ce3-b88e-3de9ec3537da` | O | nee | nee |
| Meedoen | Deelname | Hobby's | `71ecc0e5-582e-4ff0-a4ad-0c671f275c04` | O | nee | nee |
| Meedoen | Deelname | Levensbeschouwing | `f3b4cd73-904a-4ac6-b83e-d675d63493ed` | O | nee | nee |
| Meedoen | Deelname | Lid sport | `40bc78fc-9e8a-48ba-9530-38454d6ea2bd` | O | nee | nee |
| Meedoen | Deelname | Sporten | `3773b795-25ea-4039-bd65-9baad76a1009` | O | nee | nee |
| Meedoen | Deelname | Uitgaan | `5825a9b3-7de6-41ad-80e5-d201288fc065` | O | nee | nee |
| Meedoen | Deelname | Voorstelling museum | `a3377f8a-5daf-4bc7-8ae8-626f05001885` | O | nee | nee |
| Meedoen | Deelname | Wijkgebouw | `c2f0cb97-0fbc-4638-ab46-2265c61f4962` | O | nee | nee |
| Meedoen | Netwerk | Buren | `fd7e846f-568a-4bb5-ba98-8f042ce37425` | O | nee | nee |
| Meedoen | Netwerk | Buurtgenoten | `2b83af90-b647-45f9-a80d-9524df4516c5` | O | nee | nee |
| Meedoen | Netwerk | Echt praten | `30dc23ee-aba8-44f8-9a8c-97ac8e21de43` | O | nee | nee |
| Meedoen | Netwerk | Eenzaamheid | `4661dcb9-b7c4-42f8-b7c5-a61c12568806` | O | ja (CBS buurten) | ja |
| Meedoen | Netwerk | Familie | `2a027507-324e-4245-bc89-63a0e764ce84` | O | nee | nee |
| Meedoen | Netwerk | Hulp vragen | `6b5dcba8-079a-4443-a7c1-8978344abd90` | O | nee | nee |
| Meedoen | Netwerk | Internet | `c24bfe4e-a657-4026-9ce1-e301c6fb5ac1` | O | nee | nee |
| Meedoen | Netwerk | Inwoners | `31f70dff-c116-4267-bef0-d15b0ff4c020` | O | nee | ja |
| Meedoen | Netwerk | Meedoen | `22815a97-e5f9-4b16-bfbf-70a0e0298746` | O | nee | nee |
| Meedoen | Netwerk | Voldoende | `802c39dd-3ec1-4b19-b617-9fb8c3f929c4` | O | nee | nee |
| Meedoen | Netwerk | Vrienden | `8a7e7b11-19d5-495d-bbf3-f7d51eef0cec` | O | nee | nee |
| Opgroeien | Onderwijs | Achterstand leerlingen | `a5ed2ff5-f431-48e8-98d4-0c56686de109` | O | ja (CBS buurten) | ja |
| Opgroeien | Onderwijs | Niveau VO | `45ecade6-6417-4bba-8d71-1d576e6a1b08` | O | nee | nee |
| Opgroeien | Onderwijs | Opleiding jonge volwassenen | `5209531d-0766-4576-be94-47cf9d14b481` | O | nee | nee |
| Rondkomen | Armoede | Financiële buffer | `c26a0cc2-c7bf-4860-8cfa-cea5e0b6436f` | O | nee | nee |
| Rondkomen | Armoede | Minima huish met kinderen | `2e6a3139-e3a8-4565-9172-a2e9ff9347c7` | O | nee | nee |
| Rondkomen | Armoede | Minima huishouden | `e6026bbf-0e0d-4c2c-870d-29810b248bcf` | O | nee | nee |
| Rondkomen | Armoede | Minima kinderen | `6dbbd65f-492b-4a80-b6c0-acdef412f0b1` | O | nee | nee |
| Rondkomen | Armoede | Minima personen | `1f5e5ca4-2491-4e64-a587-33181d1635aa` | O | nee | nee |
| Rondkomen | Armoede | Moeite met rondkomen | `58fc72b6-881e-4917-83de-8099df3e3b0d` | O | ja (CBS buurten) | ja |
| Rondkomen | Armoede | Participatiewet 5+ jaar | `1d7c7beb-45b2-406d-ab0a-3580e28e782f` | O | nee | nee |
| Rondkomen | Armoede | Participatiewet totaal | `aa5ce990-a43e-439a-9e98-69899321cf40` | O | nee | ja |
| Rondkomen | Armoede | Verwachting inkomen | `c8a449b6-70d9-4f67-9bf3-834863e31d75` | O | nee | nee |
| Rondkomen | Werk | Werkloos totaal | `d7c79eb2-b8a2-4949-91c5-caf7fefb89ba` | O | nee | nee |
| Rondkomen | Werk | Werkloze jongeren | `05960c54-67c3-4760-8d8e-035d7bc4748e` | O | nee | nee |
| Rondkomen | Werk | Werkzamen | `ca06d8ad-6430-4f4d-bb32-7b406d26ecc8`<br>`7fd17589-46b6-460a-a1f6-ef421517ccb3` | O<br>O | nee<br>ja (CBS buurten) | nee<br>nee |
| Rondkomen | Werk | Werkzamen deeltd 0,3+ | `33f4a3b1-8fc7-4cc1-9628-b6967b6742da` | O | nee | nee |

### Samenstelling

| Thema | Onderdeel | Indicator | UUID | Status | Waarden in monitor (feb. 2026) | UUID in D-OmniTwin |
|---|---|---|---|---|---|---|
| Bebouwing | Bouwperiode › Vooroorlogs | 1915-1945 | `85802491-9c81-4fe1-88be-cc30eb5f4916` | O | nee | nee |
| Bebouwing | Bouwperiode › Vooroorlogs | voor 1915 | `aa8278dd-6f9a-49e8-ada4-62469721f460` | O | nee | nee |
| Bebouwing | Bouwperiode › naoorlogs | 1945-1984 | `f78e804e-7919-4640-89a6-a13f28493955` | O | nee | nee |
| Bebouwing | Bouwperiode › naoorlogs | vanaf 1985 | `2e4981bb-55f8-4799-8bb3-8c03405cdbff` | O | nee | nee |
| Bebouwing | Eigendom › huur | cooperatief | `a5d925dc-13ea-4dc9-8e06-e60947c9b6ec` | O | ja (CBS buurten) | nee |
| Bebouwing | Eigendom › huur | particulier | `ae0f05fd-0587-4de4-a742-d306ca4a0f8a` | O | ja (CBS buurten) | nee |
| Bebouwing | Eigendom › koop | koop | `8c57c048-ccb2-4ea4-b80f-d5ca44c9c183` | O | ja (CBS buurten) | nee |
| Bebouwing | Eigendom › waarde | wozwaard m2 | `846f7c36-5391-4b74-a901-a84622b6cba0` | O | nee | nee |
| Bebouwing | Eigendom › waarde | wozwaarde woning | `26e41525-ef0d-4e00-9f09-834c773b1d1f` | O | nee | nee |
| Bebouwing | Gebruik omgeving › Functie | Bedrijven | `f4b3ed51-31cd-443b-8d25-ef72a328b5f1` | O | nee | nee |
| Bebouwing | Gebruik omgeving › Grond | Woningen | `821b7f1f-cc25-4e24-bd64-abf92fa1d903` | O | nee | nee |
| Bebouwing | Woningtypen › gestapeld | appartementen | `9bcd5fcc-312d-49df-b01e-7bd350e70188` | O | nee | nee |
| Bebouwing | Woningtypen › gestapeld | beneden boven | `c2174b21-1e54-4566-a93a-b39cfe7ceca0` | O | nee | nee |
| Bebouwing | Woningtypen › gestapeld | studio's kamers | `e555fa98-c258-4df0-9c72-0ee5d96649c9` | O | nee | nee |
| Bebouwing | Woningtypen › grondgebonden | 2-onder-1-kap | `755deaa9-74ec-4aac-914d-10be2ea2eeea` | O | nee | nee |
| Bebouwing | Woningtypen › grondgebonden | rijtjes | `d491081f-a96d-4724-9caf-d155196a7941` | O | nee | nee |
| Bebouwing | Woningtypen › grondgebonden | vrijstaand | `2b4a45b8-3756-4e24-851b-5c32a760125e` | O | nee | nee |
| Bevolking | Cultuur › diversiteit  | herkomst | `fd94a542-850c-4377-91d5-395c0c50489a` | O | nee | nee |
| Bevolking | Cultuur › diversiteit  | leefstijl | `e22a0d3f-9171-4f75-9d35-13d652bf58c7` | O | nee | nee |
| Bevolking | Cultuur › diversiteit  | vorige woonwijk | `78430789-a609-4627-86e2-b8de97dc1480` | O | nee | nee |
| Bevolking | Cultuur › leefstijl | Gemakgeoriënteerden | `050b8793-7b5e-458f-b92a-8c954b90caaa` | O | nee | nee |
| Bevolking | Cultuur › leefstijl | Kosmopolieten | `466d90ee-7fc7-440b-8660-b8c2d532978b` | O | nee | nee |
| Bevolking | Cultuur › leefstijl | Moderne burgerij | `4c5d8397-abf9-4b98-a9c3-f7bee795f4c1` | O | nee | nee |
| Bevolking | Cultuur › leefstijl | Nieuw conservatieven | `e55cf4e8-4bc3-4f09-a159-455f6596a091` | O | nee | nee |
| Bevolking | Cultuur › leefstijl | Opwaarts mobielen | `1df7cd09-733e-4c5b-a0e1-f0bd28af7661` | O | nee | nee |
| Bevolking | Cultuur › leefstijl | Post-materialisten | `bcd57865-1f7e-406b-aa19-7f4523f4d29b` | O | nee | nee |
| Bevolking | Cultuur › leefstijl | Postmoderne hedonisten | `f84116fa-448c-4f36-a555-e81539db58a1` | O | nee | nee |
| Bevolking | Cultuur › leefstijl | Traditionele burgerij | `e69d4d1f-68a1-418e-bc68-6c4e80b8fa90` | O | nee | nee |
| Bevolking | Huishoudens › doelgroepen | één ouder gezin | `19a6ed7d-950f-4cd3-84a9-715a872cb68d` | O | nee | nee |
| Bevolking | Huishoudens › doelgroepen | kind gescheid. Ouders | `994ca4cf-b36d-4d75-9d04-15ed593ed74c` | O | nee | nee |
| Bevolking | Huishoudens › doelgroepen | niet-westers | `027ad58c-8344-4a26-8bcd-8fe4d6d18214` | O | ja (CBS buurten) | nee |
| Bevolking | Huishoudens › eenpersoons | 28-64 jaar | `f20c2271-ec50-4eff-b34f-7568bf3917cd` | O | nee | nee |
| Bevolking | Huishoudens › eenpersoons | 65+ jaar | `a4518bae-49e2-463e-bb6d-98e51ef17e10` | O | nee | nee |
| Bevolking | Huishoudens › eenpersoons | tm 27 jaar | `6b5fc16f-5d4f-4058-8d72-536f742d04ce` | O | nee | nee |
| Bevolking | Huishoudens › stellen | jongeren | `3bbd1382-eaae-4e2c-ae48-caa40c112340` | O | nee | nee |
| Bevolking | Huishoudens › stellen | met kind | `4b521d5c-fbd7-458d-8612-cd4e845951f9` | O | ja (CBS buurten) | nee |
| Bevolking | Huishoudens › stellen | zonder kind | `662d5d2f-d682-4007-8c59-bdb1eae11b98` | O | ja (CBS buurten) | nee |
| Bevolking | Leeftijd › grijze druk | 65-79 jaar | `940c6c03-5e2c-4c9a-aef2-91b9e22f7444` | O | nee | nee |
| Bevolking | Leeftijd › grijze druk | 80+ jaar | `eb1764bf-7597-464d-b2f7-1ff80d0dd054` | O | nee | nee |
| Bevolking | Leeftijd › groene druk | 0-3 jaar | `a400ba17-486f-4ae5-ab97-12d25c00c984` | O | nee | nee |
| Bevolking | Leeftijd › groene druk | 13-17 jaar | `fae46924-c3df-4e20-abc6-7f9aa7efae8f` | O | nee | nee |
| Bevolking | Leeftijd › groene druk | 4-12 jaar | `984dedc9-44e9-448b-8cf6-4f2bda50b7df` | O | nee | nee |
| Bevolking | Sociaal economische status › beroepsbevolking | potentiële | `082ebe48-ee30-49f4-9106-e9e1074938d4` | O | nee | nee |
| Bevolking | Sociaal economische status › beroepsbevolking | werkzamen | `ca06d8ad-6430-4f4d-bb32-7b406d26ecc8`<br>`7fd17589-46b6-460a-a1f6-ef421517ccb3` | O<br>O | nee<br>ja (CBS buurten) | nee<br>nee |
| Bevolking | Sociaal economische status › beroepsbevolking | zzp'ers | `bbb97c70-3b6d-4302-b8a2-6a07a2e2c087` | O | ja (CBS buurten) | nee |
| Bevolking | Sociaal economische status › inkomen  | huishouden jaar | `4a24357e-dbe1-4376-8644-53a5f9e1910b` | O | nee | nee |
| Bevolking | Sociaal economische status › inkomen  | koopkracht | `442c39e7-3610-493f-a7ad-ef8e960d30fd` | O | nee | nee |
| Bevolking | Sociaal economische status › inkomen  | persoon | `8bcdb8da-b784-4eae-9646-08db05f8479e` | O | nee | nee |
| Bevolking | Sociaal economische status › opleiding | hoog | `56f32b9a-bc45-4be1-9e1c-c2668c2e2a32` | O | ja (CBS buurten) | ja |
| Bevolking | Sociaal economische status › opleiding | laag | `c9719a07-57a5-48cf-8f93-b6f932aead51` | O | ja (CBS buurten) | ja |
| Bevolking | Sociaal economische status › opleiding | middelhoog | `1fa5df89-13e3-424f-9eba-9372cae42896` | O | ja (CBS buurten) | ja |

### Definities zonder plek in de indicatorenlijst

Deze definities staan in de monitor, maar niet in de voortgangslijst met kwadrant, thema en onderdeel.

| Indicator | UUID | Status | Waarden in monitor (feb. 2026) | UUID in D-OmniTwin |
|---|---|---|---|---|
| Aantal warme nachten | `8d544688-e825-4e6e-a355-e5e674f1d340` | C | nee | nee |
| Frequentie boezempeil onder [waarde] | `13d4676f-3e10-4495-a6e0-bb2b723050c2` | C | nee | nee |
| Verschil max neerslagtekort huidig t.o.v. 2050 | `b4a9111b-5770-4eca-bf10-b0c02dd64c22` | C | nee | nee |

## Klimaatmonitor

De Klimaatmonitor draait op welstandsgebieden × buurt, met labels A–E (zie [methodiek.md](./methodiek.md)). In de definities hebben deze 10 indicatoren status A.

| Thema | Indicator | UUID | Waarden in monitor (feb. 2026) | UUID in D-OmniTwin |
|---|---|---|---|---|
| Hemelwateroverlast | Waterdiepte op straat | `f6eafa70-9383-4de6-bd2a-e47309843437` | nee | nee |
| Hemelwateroverlast | Waterdiepte tegen gevel | `89b6274f-9372-4784-8ba3-924b6c7e4d7d` | ja (CBS buurten) | ja |
| Hemelwateroverlast | Aandeel water t.o.v. verhard | `0bbd30e5-08f5-4499-b6ca-cdda990720dc` | ja (CBS buurten, CBS buurten bebouwde komgrens, SWF welstandsgebieden) | ja |
| Hittestress | Gevoelstemperatuur | `fdb4c11b-60ca-4ea1-86b8-6855a83344ee` | ja (CBS buurten, SWF welstandsgebieden) | nee |
| Hittestress | Afstand tot koele plek | `bf4e5b8f-6b0a-4632-b9b4-8e29d025e68c` | ja (CBS buurten, SWF welstandsgebieden) | ja |
| Hittestress | Aandeel bladerdek per buurt | `66ee35d7-8046-470a-8e99-efce744cb97d` | ja (CBS buurten) | nee |
| Hittestress | Oppervlak groen per inwoner | `97f53738-3439-4c28-8cac-046a52c65248` | ja (CBS buurten, SWF welstandsgebieden) | ja |
| Droogte | Trend GLG naar 2050 | `2d6bdaba-3832-40cc-acae-950883f1aa76` | ja (SWF welstandsgebieden) | ja |
| Droogte | GLG - kleiweide | `b334ce1d-3420-4863-9c10-af8f238dfd6c` | ja (CBS buurten, SWF welstandsgebieden) | nee |
| Droogte | GLG - veenweide | `8a921563-e6e3-45e4-a8e3-5c890c619956` | ja (CBS buurten, SWF welstandsgebieden) | nee |

**Verwante klimaatdefinities** (niet in de live Klimaatmonitor):

| Indicator | UUID | Status | Waarden in monitor (feb. 2026) | UUID in D-OmniTwin |
|---|---|---|---|---|
| Waterdiepte op straat | `c4e1b3bb-e4ce-4cd0-bd52-219f4a9f5df3` | C | nee | nee |
| Gemiddeld Laagste Grondwaterstand | `a4f84d1c-3263-4229-ad95-615924cb7852` | C | ja (CBS buurten, CBS buurten bebouwde komgrens) | ja |
| Aantal warme nachten | `8d544688-e825-4e6e-a355-e5e674f1d340` | C | nee | nee |
| Verschil max neerslagtekort huidig t.o.v. 2050 | `b4a9111b-5770-4eca-bf10-b0c02dd64c22` | C | nee | nee |
| Frequentie boezempeil onder [waarde] | `13d4676f-3e10-4495-a6e0-bb2b723050c2` | C | nee | nee |

- **De klimaatset is herzien.** De indicatorenlijst in het DWH van november 2024 had op welstandsgebieden een andere set: overlast weer, vegetatie op daken, verkoeling, afvoer water, maatregelen inwoners, % groen, NDVI, % verharding en % water. Die staan nu onder *Openbare ruimte › Klimaat* in de Basis monitor. De actuele klimaatdefinities zijn die in de tabel hierboven.
- **Normen in de documentatie** (Deltares-sjabloon en kaartlegenda's): hittestress vanaf 23 °C PET, extreem vanaf 41 °C PET; een koele plek binnen 300 m (minimaal 200 m²); afstand tot koelte in klassen 0–200, 200–300, 300–400, 400–500, 500+ m; waterdiepte bij intense neerslag in klassen 5–10, 10–15, 15–20, 20–30, >30 cm. Of de labels A–E hierop gebaseerd zijn, is niet bekend.
- **Bronnen:** Klimaateffectatlas (gevoelstemperatuur, afstand tot koelte, paalrot), Wetterskip Fryslân (GLG en trend), BGT en BRK (aandelen groen, grijs en water), de stresstest wateroverlast van SWF (waterdiepte), AHN4 (maaiveld).

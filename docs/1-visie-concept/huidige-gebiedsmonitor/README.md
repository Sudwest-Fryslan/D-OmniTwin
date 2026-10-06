# De huidige gebiedsmonitor van Súdwest-Fryslân

Stand 02-10-2026. Vertrekpunt voor D-OmniTwin 0.3.0 (epic [#195](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/195)): de eerste versie die de huidige gebiedsmonitor van Súdwest-Fryslân (SWF) moet kunnen vervangen.

**Kern:** de huidige monitor is een werkend prototype met twee monitors (Basis op CBS-buurten, Klimaat op welstandsgebieden × buurt), een sunburst van 4 kwadranten → 12 thema's → 33 onderdelen → ±215 indicatoren, gekleurd naar percentiel of label A–E. Hij wordt handmatig gevuld vanuit het DWH van SWF via FME. Van de 228 indicatordefinities hebben er 49 waarden. D-OmniTwin 0.3.0 moet **hetzelfde kunnen, en meer**: inloggen met rollen en laagrechten, dezelfde indicatoren (zelfde UUID's), dezelfde kleurmethodiek als keuze, en een laad-API die de huidige FME-stroom kan vervangen.

## Wat de monitor is

| Aspect | Huidige situatie |
|---|---|
| Naam in de documenten | Gebiedsmonitor, Basismonitor SWF, Gebiedskompas, Instrumentarium IGW |
| Doel | data-instrument onder het **Integraal Gebiedsgericht Werken (IGW)**: vraagstukken in gebieden in samenhang benaderen, met partners ("van buiten naar binnen") |
| Plek in de gebiedscyclus | gebiedsanalyse (1× per 4 jaar), gebiedsagenda (1× per 4 jaar, jaarlijks bijsturen), gebiedsplan (jaarlijks), **gebiedsmonitor (2× per jaar)** |
| Drie vragen per gebied | *Hoe staat het ervoor?* (Kompas), *Wat speelt er allemaal?* (projecten), *Waar moeten we rekening mee houden?* (ruimtelijke kaders, klimaat). Elke vraag is een laaggroep in de viewer |
| Herkomst structuur | de Kompas-structuur komt van de Basismonitor Groningen; SWF hernoemde "Samen leven" naar *Mienskip* en koos een eigen methodiek (percentielklassen, labels A–E) |
| Status | werkend prototype ("bèta") sinds 2025, intern gebruik |
| Eigendom | de broncode is van de leverancier, de data van SWF. D-OmniTwin bouwt de functies dus na en neemt de data over |

## Gebruikers

| Groep | Gebruik | Frequentie |
|---|---|---|
| Medewerker in team of vakgroep | wat speelt er in mijn werkgebied | ad hoc |
| Beleidsadviseur, projectleider | data en trends analyseren, vergelijken, exporteren | ad hoc |
| Kernteam gebiedsagenda (gebiedsregisseur, strategisch adviseur, domeinadviseur) | integraal overzicht, aggregeren | maandelijks |
| Kernteam+ (coördinatoren, accountmanagers, projectleiders) | operationeel signaleren | tweemaandelijks |
| Afstemmingsoverleg (keten- en programmamanagers) | projecten en middelen | per kwartaal |
| Sturingsdriehoek (wethouder, directeur, gebiedsregisseur) | strategische regie | maandelijks |

Het gebruik is intern; een publiek deel is als wens genoemd. Een gebruikersgroep met medewerkers uit elk domein test de monitor in workshops (casus "De Vitale Wijk").

## Wat 0.3.0 moet kunnen

"Hetzelfde én meer" betekent concreet:

1. **Inloggen** via OIDC tegen Keycloak SWF, met rollen die bepalen welke lagen en functies zichtbaar zijn.
2. **Twee monitors:** Basis (CBS-buurten) en Klimaat (welstandsgebieden × buurt), met dezelfde indicator-UUID's.
3. **Percentielklasse en label A–E** als kleurmethodiek, naast de Z-score van D-OmniTwin.
4. **Vulling vanuit het DWH van SWF** via een laad-API, met een adapter voor het huidige pushformaat en onderdrukking bij n<10.
5. **De drie laaggroepen** als bronnen met ontsluitingsregels.
6. **Favorieten en instellingen** per gebruiker.

D-OmniTwin heeft al méér: trends over jaargangen, rapporten, AI-chat, 3D en open API's. De gaten zitten in identiteit, vulling, methodiek en gebiedsindelingen, niet in de basisfunctionaliteit.

## Leeswijzer

| Document | Inhoud |
|---|---|
| [functies.md](./functies.md) | de viewer: monitorkeuze, kaartselectie, sunburst, kaartweergaven, klimaatmonitor, lagen, favorieten, instellingen, rollen |
| [gegevens.md](./gegevens.md) | datamodel, gebiedstypes, volumes en dekking, de gegevensstroom DWH → FME → monitor |
| [indicatoren.md](./indicatoren.md) | de volledige indicatorenlijst met UUID's, en de klimaatindicatoren |
| [methodiek.md](./methodiek.md) | percentielklassen, aggregatie, labels A–E, n<10; vergelijking met de Z-score-methodiek en advies |
| [gat-analyse.md](./gat-analyse.md) | huidige functie → D-OmniTwin nu → actie 0.3.0 (MoSCoW), eisen voor de laad-API, use cases, open vragen |

## Bronnen en afbakening

- Een analyse van de draaiende viewer (alleen kijkend, ingelogd), de projectdocumentatie van SWF, de FME-workspaces van de push en een export van de definities en waarden (februari 2026).
- In deze map staan alleen afgeleide beschrijvingen: structuur, aantallen, indicatornamen, UUID's en methodiek. Geen meetwaarden, schermafdrukken met buurtwaarden, interne adressen of persoonsgegevens. Systemen hebben functionele namen, personen staan er als rol in.
- Verwant: RFC voor het vullen van D-OmniTwin ([#205](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/205)), bronnen als dataproduct ([#182](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/182)), Z-score-methodiek ([#66](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/66), [zscore_methodiek.md](../../3-data-engineering/zscore_methodiek.md)).

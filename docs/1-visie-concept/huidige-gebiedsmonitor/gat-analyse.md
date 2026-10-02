# Gat-analyse: van de huidige monitor naar D-OmniTwin 0.3.0

Stand 02-10-2026. Wat D-OmniTwin 0.3.0 moet doen om de huidige gebiedsmonitor te vervangen ("hetzelfde én meer", epic [#195](https://github.com/TLaan/D-OmniTwin/issues/195)). Terug naar [het overzicht](./README.md).

**Kern:** de grootste gaten zijn **identiteit** (OIDC, rollen, laagrechten), **vulling** (een laad-API die de FME-stroom van SWF vervangt, met dezelfde UUID's en n-onderdrukking), **methodiek** (percentielklasse en labels naast de Z-score) en **gebiedsindelingen** (welstand × buurt). De basisfunctionaliteit (kaart, Kompas, multi-selectie, trends, rapporten) heeft D-OmniTwin al.

## Functies: huidig → D-OmniTwin → actie

MoSCoW voor 0.3.0: *Must* = nodig om te vervangen; *Should* = hoort erbij, mag later in 0.3.x; *Could* = wens.

| # | Functie | Huidige monitor | D-OmniTwin nu | Actie 0.3.0 | MoSCoW |
|---|---|---|---|---|---|
| 1 | Inloggen met het SWF-account | Keycloak SWF | lokale sessie en beheerder | OIDC (authorization code + PKCE) tegen een configureerbare Keycloak-realm, via de backend | **Must** |
| 2 | Rollen → laag- en functierechten; publiek en intern deel | lagen per rol in de viewer | beheerder tegenover anoniem | rollen uit Keycloak; per bron/laag `openbaar` of `intern`, afgedwongen in de API en de proxy naar de kaartdiensten | **Must** |
| 3 | Basis monitor op CBS-buurten: 4/12/33/±215 met dezelfde UUID's | ja | Kompas met dezelfde structuur; ±92 indicatoren in de sample, 30 UUID's gedeeld | kompasprofiel "SWF Basis" met alle UUID's uit de definities; ontbrekende waarden grijs en benoemd | **Must** |
| 4 | Klimaatmonitor op welstand × buurt met labels A–E | ja (10 indicatoren) | klimaat-Kompas in de use case hittestress; welstand alleen als gebiedstype zonder geometrie | gebiedsindeling welstand × buurt laden; profiel "SWF Klimaat" met label-classificatie | **Must** |
| 5 | Percentielklasse 12,5% en klasse-aggregatie | ja | Z-score | classificatie en aggregatie per profiel (zie [methodiek.md](./methodiek.md#advies)) | **Must** |
| 6 | Indicator op de kaart: percentiel / gelabelde werkelijke waarde / uit | ja | kaartkleuring per indicator (Z) | twee kaartmodi plus uitzetten | **Must** |
| 7 | Vulling vanuit het DWH van SWF | push vanuit FME, handmatig | recepten voor CBS en RIVM; geen laad-API | laad-API met adapterprofiel voor het huidige formaat (zie hieronder) | **Must** |
| 8 | Onderdrukking bij n<10 | in de ETL | nee (alleen minimaal 5 gebieden in de referentie) | kolom `n`, drempel per bron of indicator, onderdrukken in de API | **Must** |
| 9 | Multi-selectie met tabel, sunburst over de selectie | ja | multi-selectie en vergelijking | aggregatieregel over de selectie gelijktrekken; bewijs via use case | **Must** |
| 10 | Klimaatlagen (paalrot, koelte, waterdiepte, GLG, AHN4, schaduw) | ±15 lagen | deels (RIVM, PDOK) | lagen als bronnen via GeoServer SWF | **Must** |
| 11 | Kleurenblindvriendelijk palet | nee | ja | ook voor de percentielkleuring | **Must** |
| 12 | Productieklaar bij SWF: acceptatieomgeving, back-up, beheerhandleiding, werkinstructies | deels | Docker, CI, installatiegids | acceptatieomgeving, back-uprecept, beheerhandleiding | **Must** |
| 13 | Privacycheck: accounts, logging, interne lagen | – | – | korte DPIA-toets; projectlaag zonder persoonsvelden | **Must** |
| 14 | Indicatorpaneel: beschrijving, bron, eenheid, staafdiagram van de selectie | beschrijving en staafdiagram | indicatorinfo, trends, rapport | eenheid, gemeentegemiddelde en staafdiagram van de selectie | **Should** |
| 15 | "Wat speelt er allemaal?": projecten met paspoort | laag, rol-afhankelijk | externe kaartlagen | bron "projecten" (intern), popup met paspoort zonder persoonsvelden | **Should** |
| 16 | Overige lagen (gemeentegrens, deelgebieden, coördinatorgebieden, grootgrondbezit) | ja | deelgebieden | als bronnen inrichten | **Should** |
| 17 | Overige gebiedsindelingen | 11 gebiedstypes, 2 actief | buurt, wijk, gemeente, deelgebieden | woonplaats en coördinatorgebieden als gebiedstype; postcode en bebouwde kom later | **Should** (woonplaats, coördinator), **Could** (rest) |
| 18 | Favorieten | ja | nee | per gebruiker, na inloggen | **Should** |
| 19 | Export (data, PDF) | nee | rapporten (PDF), open API's | CSV-export van het indicatorpaneel | **Should** |
| 20 | Beheer: definities, kompasprofiel, koppeling indicator × gebiedsindeling | beheeromgeving bij de leverancier | beheer: indicatoren, Kompas, externe lagen | koppeling indicator × gebiedsindeling in beheer | **Should** |
| 21 | Metadata per bron tonen (bron, jaargang, licentie) | beschrijving | ontologie en definities | in het indicatorpaneel | **Should** |
| 22 | Huisstijl SWF | eigen | eigen thema | SWF-thema via ontwerpvariabelen ([#89](https://github.com/TLaan/D-OmniTwin/issues/89)) | **Should** |
| 23 | Instellingen per gebruiker (laatste kaartpositie) | ja | nee | per gebruiker | **Could** |
| 24 | Identify BAG-pand, markeringen | ja | 3D BAG, info | BAG-pandinfo bij een klik | **Could** |
| 25 | Kerncijfers, top-5, stijgers en dalers, signalering | nee | deels (uitschieters in rapport) | buiten "gelijkwaardig" | **Could** |
| 26 | Thema kiezen → kaart gekleurd op de themascore | nee | controleren | – | **Could** |
| 27 | Trendlijn per indicator | gedocumenteerd, niet live | ja | – (al aanwezig) | – |

## Eisen voor de laad-API

Uitgewerkt in RFC [#205](https://github.com/TLaan/D-OmniTwin/issues/205) (model "Dataset Registry + Bulk Loader"). Wat volgt uit de huidige stroom ([gegevens.md](./gegevens.md#gegevensstroom)):

| # | Eis | Waarom (huidige stroom) |
|---|---|---|
| E1 | **Drie profielen:** `definities` (indicator, gebiedstype, relatie), `waarneming` (waarden) en `gebiedsindeling` (geometrie, GeoPackage). Definities vóór waarnemingen; een waarde met een onbekende UUID wordt geweigerd, met rapport | nu: eerst definities, dan waarden; geometrie komt live uit een WFS |
| E2 | **Snapshot/replace als standaard.** Definities altijd als volledige set; waarnemingen per dataset (of per indicator × gebiedstype × jaar) | de definitie-SQL levert altijd alles; de waardebestanden zijn per indicator × gebiedstype |
| E3 | **Idempotent:** `Idempotency-Key` plus een sha256 van het pakket; dezelfde levering twee keer = één versie | nu is het gedrag bij herhaling onbekend |
| E4 | **Contract waarneming:** indicator-UUID, gebiedstype, gebiedscode, peildatum óf jaar, waarde, **`n`** (optioneel maar aanbevolen), bron, kwaliteit | de push heeft geen `n`, geen bron |
| E5 | **Adapterprofiel `swf-monitor-v1`:** accepteert het huidige formaat (`indicator_id`, `gebiedstype_id`, `gebieds_id`, `waarde`, `begingeldigheid` `JJJJ-01-01`, `eindgeldigheid`) en de huidige definitie-JSON (drie arrays). SWF hoeft dan in FME alleen het adres en de authenticatie te wijzigen | overstap zonder de ETL om te bouwen |
| E6 | **Definitiegeldigheid** (begin/eind) apart van de peildatum van een waarde | de monitor kent beide |
| E7 | **n-drempel bij publicatie** (SWF: 10), instelbaar per bron of indicator; ontbrekende `n` toegestaan met de vlag "onderdrukt in de bron" | nu weggelaten in de ETL, niet controleerbaar |
| E8 | **Gebiedscodes per gebiedstype valideren**, met een namespace voor niet-unieke codes (welstand-volgnummers); jaar 0 en onbekende buurtcodes afwijzen | gevonden in de export |
| E9 | **Eén pakket per bron:** alle waarden van één bron in één levering (CSV in zip, GeoPackage-tabel of JSON) in plaats van één run per indicator | nu ±57 handmatige runs; wordt 1–2 |
| E10 | **Volumes:** ±45 duizend waarnemingen nu, ±200–250 duizend bij volledige vulling; bodylimiet ≥ 50 MB, zip/gzip toegestaan | export februari 2026 |
| E11 | **Synchrone optie:** naast `202` + status-URL ook een wachtende variant (tot ±60 s) voor kleine leveringen; status-JSON met een vast veld `status` (`geaccepteerd`, `bezig`, `gepubliceerd`, `afgewezen`) | pollen is in FME omslachtig |
| E12 | **Proef zonder publiceren** (`proef=true`) en een **rapport per regel** (aantallen geaccepteerd en afgewezen, redenen; Problem Details); duidelijke HTTP-codes (400/422 contract, 401/403 toegang, 409 dubbel) | nu alleen het FME-log |
| E13 | **Atomische publicatie:** bij een fout blijft de vorige versie actief | nu kan een levering half geladen zijn |
| E14 | **Teruglezen** in hetzelfde contract (per dataset of indicator), voor de voortgangscontrole | de huidige scripts lezen alles terug |
| E15 | **Machine-authenticatie:** OAuth2 client credentials via Keycloak, één client per bron met rol `bron:{bron}:leveren`. Ondersteun clientauthenticatie met **`client_secret_post` en `client_secret_basic`** (wat FME standaard kan); `private_key_jwt` optioneel | FME haalt de toegang nu met een form-POST op |
| E16 | **Audit per levering:** welke client, wanneer, welk pakket (sha256), welke versie | ontbreekt nu |
| E17 | **Kompas-hiërarchie** niet verplicht in de waardestroom; als eigen profiel of via beheer | de monitor scheidt dit ook |

**Wat FME makkelijk kan:** JSON (zoals nu), CSV en GeoPackage schrijven; een bestand als body uploaden; vrije headers (`Idempotency-Key`); retry met backoff (veilig door idempotentie); planning via FME Flow-schedules aan de kant van SWF.

## Voorgestelde use cases

Volgens de werkwijze van `usecases/<naam>/` (data, inrichting, stappen, bewijs, out of the box getest; focus Bolsward-Zuidoost, BU19000002). Waar de data intern is, twee varianten: een open demoset in de repo en een SWF-installatie buiten git.

| Use case | Vraag (kort) | Gebruiker | Dekt |
|---|---|---|---|
| `swf-inloggen-rollen` | met het SWF-account inloggen en interne lagen zien; anoniem alleen open lagen | beleidsadviseur, anonieme bezoeker | #1, #2 |
| `swf-basismonitor` | hoe staat Bolsward-Zuidoost ervoor ten opzichte van de andere SWF-buurten, in de kleuren van de huidige monitor | gebiedsregisseur | #3, #5, #9 |
| `swf-klimaatmonitor` | welk label (A–E) heeft het gebied voor hittestress, en welke indicator trekt het omlaag | adviseur klimaatadaptatie | #4, #10 |
| `indicator-op-kaart` | waar is de afstand tot een koele plek het grootst, in meters en ten opzichte van SWF | beleidsadviseur | #6, #14, #19 |
| `swf-datalevering` | een nieuwe jaargang aanleveren; hij staat direct in het Kompas en n<10 is onderdrukt | functioneel beheerder SWF | #7, #8, E1–E16 |
| `wat-speelt-er` | welke gemeentelijke projecten lopen er in het gebied, en in welke fase | kernteam+ | #15 |
| `favorieten-en-instellingen` | dezelfde vijf buurten in één klik terug, op de laatste kaartpositie | ingelogde medewerker | #18, #23 |
| `gebiedsanalyse-deelgebied` | knelpunten van een deelgebied tegenover heel SWF, als input voor de gebiedsagenda | kernteam gebiedsagenda | #17 |
| `vitale-wijk` | de workshopcasus van de gebruikersgroep als acceptatietest | gebiedsteam | combinatie |

**Acceptatie in het kort:** zonder rol geeft een intern laag-endpoint 401/403 (ook bij een directe aanroep); de klasse per indicator is gelijk aan de huidige monitor voor ≥ 10 gecontroleerde indicatoren; een levering is idempotent, een onbekende UUID wordt geweigerd en de n-drempel wordt in de API afgedwongen; een favoriet is alleen zichtbaar voor de eigen gebruiker.

## Open vragen

**Data en methodiek** (aan de leverancier en de data-engineer DWH)
1. Wanneer komt een volledige database-export van de monitor (definities, kompasconfiguratie, waarden, rollen, laagrechten)?
2. Hoe gedraagt het laadendpoint zich bij een herhaalde levering: upsert, vervangen of dubbel?
3. Wat betekent status A?
4. Hoe rekent de monitor het percentiel precies (klasse of continu, referentiegroep, aggregatie over meerdere geselecteerde gebieden)?
5. Wat zijn de drempels van de labels A–E per indicator, en hoe ontstaat het themalabel?
6. Wordt de n<10-onderdrukking overal in de ETL toegepast, en is `n` per waarde beschikbaar?
7. Welke workspaces of scripts maken de waardebestanden per indicator, en waar staat de ETL-documentatie?
8. Welke bron is bedoeld voor de ±69 subjectieve indicatoren (veiligheidsmonitor op clusterniveau, burgerpeiling, GGD), op welk gebiedsniveau, en mag die buiten de gemeente?
9. Onder welke licentie valt de commerciële leefstijlsegmentatie (8 segmenten onder Bevolking › Cultuur)?
10. Bron en jaar van gevoelstemperatuur, GLG-trend, waterdiepte en groen per inwoner; mag de bewerking als open data?

**Inrichting en gebieden** (aan de functioneel beheerder SWF en de projectleider IGW)

11. Is de geometrie van welstand × buurt als export of WFS beschikbaar, en is die openbaar?
12. Is de keuze voor de IGW-gebiedsindeling (6 deelgebieden, stad-platteland of oost-west) gemaakt?
13. Welke van de ±30 lagen zijn intern en welke openbaar? Levert GeoServer SWF ook in EPSG:3857?

**Identiteit en beheer** (aan de functioneel beheerder SWF)

14. Welke Keycloak-realm gebruikt D-OmniTwin, nu de huidige koppeling met de SWF-accounts in december afloopt? Krijgt D-OmniTwin een eigen client?
15. Welke rollen wil SWF (publiek, medewerker, beheerder, partnergemeente)?
16. Waar draait 0.3.0 in productie, en wie is functioneel beheerder en achtervang?

**Gebruikers** (aan de projectleider IGW)

17. Wie test de acceptatie van 0.3.0? Zijn de resultaten van de workshops en de enquête onder het gebruikerspanel beschikbaar?
18. Valt "projecten en middelen per gebied" binnen 0.3.0, of is dat een volgende stap?

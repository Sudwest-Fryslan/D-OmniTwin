# 0007. Geen multi-tenancy: autonome D-OmniTwin-instanties in een mesh

- Status: voorgesteld
- Datum: 2026-10-02
- Issue: #231
- Uitwerking: [Mesh van instanties](../mesh-van-instanties.md)
- Raakt: ADR 0002 (bronnen als dataproduct, PR #184), ADR 0003 (use cases), ADR 0004 (vullen), ADR 0005 (API's per doel), #20, #32, #33, #34, #218

## Context

D-OmniTwin moet breder bruikbaar worden dan Súdwest-Fryslân: Leeuwarden en Tytsjerksteradiel zijn partner in de innovatieaanvraag, DataFryslân is erkend data-intermediair onder de Data Governance Act en beheert de Friese dataspace (FRLDS). Er lagen twee richtingen op tafel:

- **Multi-tenant:** één installatie voor meerdere organisaties, gescheiden met een `organization_id` en Row Level Security. Gepland in Sprint 23 (`docs/STATE.md`, #34, `docs/8-communicatie/overleg_leidraad_externen_2026-08-24.md`).
- **Meerdere instanties:** elke organisatie een eigen D-OmniTwin; samenwerken door uitwisseling.

Multi-tenancy maakt één partij (de hoster) verantwoordelijk voor de data, de rechten en de beschikbaarheid van alle anderen. Dat past niet bij overheden die elk zelf verwerkingsverantwoordelijke zijn (AVG), zelf hun IAMA en DPIA doen en zelf over hun informatiebeheer beslissen. Het past ook niet bij hoe dataspaces werken (IDSA, Eclipse Dataspace Protocol, FSC, iSHARE, Federatief Datastelsel): autonome deelnemers met een eigen connector, die per afspraak delen. En het past niet bij data mesh: domeinen zijn eigenaar van hun data en bieden die als product aan, onder gezamenlijke, geautomatiseerde regels.

Samenwerken vraagt dan wel dat alles wat een instantie inricht (use cases, datasets, Kompas-profielen, rollen, contacten, afspraken) van de ene instantie naar de andere kan, als data. Anders wordt "eigen instantie" "eigen eiland".

## Besluit

**1. Geen multi-tenancy.** Eén D-OmniTwin-instantie hoort bij één organisatie (een gemeente, DataFryslân, een samenwerkingsverband dat als één verantwoordelijke optreedt). Dus **niet**:
- geen `tenant_id`, `organization_id` of `organisatie_id` als scheiding in het datamodel;
- geen Row Level Security per organisatie;
- geen gedeelde database tussen organisaties;
- geen "gemeente-filter" als toegangsscheiding: `gemeente` is een gebiedskenmerk (CBS-code, referentiegroep voor de Z-score), geen grens tussen klanten;
- geen rollen per gemeente binnen één instantie (zie #34);
- geen centrale hoster die namens anderen beheert, tenzij als verwerker van één organisatie in een eigen instantie.

**2. Elke deelnemer heeft een eigen instantie**, met:
- eigen database, eigen volumes en eigen back-ups;
- eigen Keycloak (realm `omnitwin`), eigen gebruikers en machineclients; koppeling met de eigen IdP (Entra, eHerkenning) per instantie;
- eigen beheer, eigen release-keuze (binnen de ondersteunde versies) en eigen verantwoordelijkheid (AVG, IAMA, DPIA, archivering);
- een eigen identiteit in de mesh: de organisatie met haar OIN, later een PKIoverheid- of iSHARE-certificaat per instantie.

**3. Samenwerken gaat via uitwisseling tussen instanties: een mesh.** Een instantie biedt datasets, diensten (API's) en use cases aan in een catalogus (DCAT-AP-NL), onder een afspraak (ODRL-policy, later een FSC- of DSP-contract). Een andere instantie neemt af via de vier vulroutes van ADR 0004 (route 1 push, route 4 federatie). Wie aanbiedt, is en blijft verantwoordelijk voor zijn aanbod; wie afneemt, voor zijn gebruik.

**4. Alles wat een instantie inricht, is uitwisselbaar als data (portabiliteit).** Niet alleen meetwaarden, ook use cases, datasetregistraties en laadprofielen, bronnen, Kompas-profielen, kaartlagen, rollen en rechten, contacten, contracten en afspraken, catalogusbeschrijvingen en herkomst. Elk item heeft een open formaat (DCAT, ODRL, SKOS, vCard, PROV, JSON-schema's van D-OmniTwin) en is te exporteren en te importeren zonder code. Geheimen gaan nooit mee; persoonsgegevens alleen met grondslag en afspraak. Overzicht per item: [mesh-van-instanties § 3](../mesh-van-instanties.md#3-alles-is-data).

**5. Elke uitwisseling gaat door de portabiliteitspoort.** Export en import zijn geen kopieeractie maar een besluit, met vaste stappen:
1. **beleid:** wat mag mee (geen geheimen; persoonsgegevens alleen met grondslag; classificatie bepaalt wat mag);
2. **verificatie:** handtekening, uitgever, versie, herkomst en integriteit (sha256) kloppen;
3. **toets tegen eigen beleid:** voorwaarden (ODRL) en gevraagde rechten passen bij het beleid van de ontvanger;
4. **goedkeuring** door een rol (`beheerder` of data-steward) van de ontvangende partij, en bij export van de verstrekkende partij;
5. **auditspoor:** wie, wat, wanneer, welke versie, welk besluit.

Elk portabel pakket heeft minimaal: uitgever (organisatie + OIN), identificatie (URI) en versie (semver), ondertekening, licentie en voorwaarden, herkomst (PROV) en classificatie (open, beperkt, intern).

**6. Ontwerpregels voor wat we nu bouwen:**
- geen hardcoded organisatie (naam, gemeentecode, logo, contact, hostnaam) in code; dat is inrichting;
- identificatie met UUID of URI, zonder aanname over de instantie; nooit een serieel databasenummer als externe sleutel;
- elke inrichting heeft een export (en op termijn een import) in een open formaat;
- use cases bevatten geen organisatie-specifieke code (ADR 0003, #218);
- elke instantie heeft haar eigen Keycloak-realm; vertrouwen tussen instanties via federatie (identity brokering, later OpenID Federation of iSHARE), niet via gedeelde accounts.

## Alternatieven

- **Multi-tenant SaaS** (één installatie, `organization_id` + RLS). Goedkoper per extra gemeente en één update voor allen. Maar: één partij verantwoordelijk voor de data van alle anderen; één lek of fout in een RLS-regel raakt iedereen; geen eigen release-keuze; geen eigen IdP-regie; AVG-rollen worden onduidelijk (wie is verwerker?). En het staat haaks op "methodiek + referentie-implementatie" en op de dataspace-gedachte. Afgewezen.
- **Gedeeld regionaal platform** (bijvoorbeeld één D-OmniTwin bij DataFryslân voor alle Friese gemeenten). Ogenschijnlijk efficiënt, maar het is multi-tenancy met een andere eigenaar; gemeenten verliezen de regie over inrichting en rechten. DataFryslân krijgt in dit besluit een eigen instantie en de rol van intermediair en catalogus, niet die van hoster. Afgewezen als model; een organisatie mag wel een verwerker inhuren die haar eigen instantie beheert.
- **Centrale datahub** (alle data naar één regionale database, D-OmniTwin's lezen daaruit). Strijdig met "bron blijft bron" (doelbeeld), met de soevereiniteit van dataspaces en met doelbinding per afnemer. Afgewezen.
- **Eigen instanties zonder uitwisselbare inrichting** (ieder installeert en richt zelf in). Wel autonomie, maar geen hergebruik: elke gemeente bouwt dezelfde use cases en profielen opnieuw. Afgewezen; daarom besluitpunt 4.

## Gevolgen

- **Makkelijker:**
  - verantwoordelijkheden zijn helder: één instantie, één verantwoordelijke;
  - een fout of lek blijft binnen één instantie;
  - een gemeente kan instappen zonder anderen te raken, en uitstappen met al haar inrichting;
  - past op DGA, FDS, FSC, iSHARE en DSP zonder ombouw;
  - geen RLS-complexiteit in de kern.
- **Moeilijker:**
  - meer installaties om te beheren; daarom moet installeren en bijwerken eenvoudig blijven (`docs/9-beheer/installatie.md`, releasebeleid);
  - vergelijken over gemeentegrenzen vraagt uitwisseling (route 1 of 4), geen query op één database;
  - export, import, ondertekening en de portabiliteitspoort moeten gebouwd worden;
  - identiteit tussen instanties (organisatie en medewerker) vraagt federatie.
- **Vervalt:** het multi-tenancy-datamodel uit Sprint 23 (`organizations`, `organization_id`, RLS per organisatie; #34, `docs/STATE.md`). De Keycloak-stack, BFF-auth en PostgREST-beveiliging uit #34 blijven nodig, per instantie.
- **Fasering:**
  - **0.3.0:** de principes en ontwerpregels; use cases en datasetregistraties zijn al exporteerbare bestanden; geen nieuwe organisatie-aannames in code;
  - **0.4.0:** semantiek en catalogus (DCAT-AP-NL), export/import van inrichting als ondertekend pakket, met de portabiliteitspoort;
  - **0.5.0:** verbinden: connector (FSC/DSP), contracten tussen instanties, federatieve identiteit;
  - **1.0:** minstens twee organisaties met een eigen instantie die aantoonbaar inrichting en data uitwisselen.
- **Open:** het protocol tussen instanties (DSP en/of FSC, iSHARE; #32, #33), het pakketformaat (zip met manifest of OCI-artefact), en de ondertekening (PKIoverheid, Sigstore/cosign of JWS).

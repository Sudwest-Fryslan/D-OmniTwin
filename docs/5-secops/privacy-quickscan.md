# Privacy-quickscan (DPIA-voortoets)

Korte toets welke persoonsgegevens een D-OmniTwin-installatie verwerkt, waarom, hoe lang, en wat nog open staat. Bedoeld als startpunt voor de privacytoets van de organisatie die D-OmniTwin in productie neemt; geen volledige DPIA. Stand: versie 0.2.1 plus de wijzigingen op `main` (oktober 2026). Issue: [#257](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/257).

## Conclusie

- D-OmniTwin verwerkt **geen persoonsgegevens van inwoners** als inhoud: de data zijn indicatoren op buurtniveau en hoger (CBS, RIVM, Politie, eigen bronnen), geaggregeerd. Wel persoonsgegevens van **gebruikers en beheerders** (accounts, logs met IP-adres) en, als de organisatie dat inschakelt, **vrije tekst naar een AI-aanbieder**.
- Het risico is laag zolang (1) de bronnen geaggregeerd blijven (geen gegevens tot op een persoon of adres herleidbaar), (2) de AI-assistent lokaal draait of een verwerkersovereenkomst heeft, en (3) de open punten hieronder (bewaartermijn van waarschuwingslogs, IP-adressen) zijn opgelost of geaccepteerd.
- Een volledige DPIA lijkt niet nodig voor de standaardinstallatie. Wel bij koppeling van interne bronnen met kleine aantallen (kans op herleidbaarheid) of bij een externe AI-aanbieder. Dat oordeel ligt bij de FG van de organisatie.

## Rollen

| Rol | Wie |
|---|---|
| Verwerkingsverantwoordelijke | De organisatie die de instantie draait (elke organisatie een eigen instantie, [ADR 0007](../2-architectuur/adr/0007-geen-multi-tenancy-mesh-van-instanties.md)) |
| Verwerker | Een hostingpartij of leverancier die de installatie voor de organisatie beheert, als die er is (verwerkersovereenkomst nodig). Een externe AI-aanbieder, als die is ingeschakeld. |
| Ontwikkelaars van D-OmniTwin | Geen rol in de verwerking: de software draait bij de organisatie zelf en stuurt niets terug (geen telemetrie; het embeddingmodel draait offline met `HF_HUB_DISABLE_TELEMETRY=1`). |

## Welke persoonsgegevens

| Gegeven | Waar | Van wie | Doel | Grondslag (voorstel) | Bewaartermijn nu |
|---|---|---|---|---|---|
| Gebruikersnaam en wachtwoord-hash (bcrypt), beheerrechten | tabel `users` (eigen login van de beheeromgeving) | beheerders | toegang | publieke taak / gerechtvaardigd belang (beveiliging) | tot het account wordt verwijderd |
| Sessietoken (sha256-hash), gebruikers-id, vervaltijd | tabel `sessions` | beheerders | ingelogd blijven | idem | 12 uur; verlopen sessies worden bij een volgende login opgeruimd |
| Account in Keycloak: gebruikersnaam, en zo ingevuld naam en e-mail; rollen | database `keycloak` | gebruikers, beheerders | inloggen (OIDC), rollen | idem | tot het account wordt verwijderd |
| Inlog- en beheergebeurtenissen met IP-adres | database `keycloak` (events) | gebruikers, beheerders | beveiliging | gerechtvaardigd belang (beveiliging) | 30 dagen (`eventsExpiration` in [`realm-omnitwin.json`](../../deploy/keycloak/realm-omnitwin.json)) |
| Applicatielog per verzoek: pad, status, duur, **IP-adres** (ook uit `X-Forwarded-For`), gebruikers-id | tabel `app_logs` | **alle bezoekers**, ook anoniem | beheer, foutopsporing, misbruik | gerechtvaardigd belang | `INFO` 30 dagen, `DEBUG` 7 dagen, **`WARNING` en hoger permanent** (`log_cleanup_service.py`); een verzoek met status 4xx is een `WARNING` |
| Mislukte inlogpoging met de **ingetypte gebruikersnaam** en IP-adres | `app_logs` (`WARNING`) | wie probeert in te loggen | beveiliging | gerechtvaardigd belang | **permanent** |
| Eerste 80 tekens van een chatvraag | `app_logs` (`INFO`) | alle bezoekers | foutopsporing | gerechtvaardigd belang | 30 dagen |
| Prompt naar het taalmodel (eerste 200 tekens) | `app_logs` (`DEBUG`, alleen als debuglogging aan staat) | alle bezoekers | foutopsporing | idem | 7 dagen |
| Verzoeken met IP-adres in de containerlog (uvicorn, Traefik-fouten) | Docker-logs van de host | alle bezoekers | beheer | idem | onbeperkt, tenzij de Docker-daemon een limiet heeft ([beheerhandleiding](../9-beheer/beheerhandleiding.md#1-dagelijks-status-health-en-logs)) |
| Wie een indicator goedkeurde (`gevalideerd_door`: gebruikers-id; `ontologie_beoordeeld_door`) | tabel `indicatoren` | beheerders | herkomst, verantwoording | publieke taak | zolang de indicator bestaat |
| Favorieten (gebiedenselecties met een zelfgekozen naam) en laatste kaartpositie, met als sleutel alleen de `sub` uit Keycloak (of `lokaal:<id>` voor een lokaal account); geen naam of e-mail ([#258](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/258)) | tabellen `gebruiker_voorkeuren` en `gebruiker_favorieten` (V035); niet via PostgREST | ingelogde gebruikers | gemak: dezelfde selectie en kaartpositie terug | publieke taak / gerechtvaardigd belang (functioneel, door de gebruiker zelf opgeslagen) | tot de gebruiker ze verwijdert; alles van een gebruiker wordt opgeruimd na **365 dagen** zonder gebruik (dagelijkse opruimtaak, `gebruikersvoorkeuren.BEWAAR_DAGEN`). Een verwijderd Keycloak-account ruimt niet direct op: dat gebeurt via dezelfde termijn, of handmatig met `DELETE FROM gebruiker_voorkeuren WHERE eigenaar = '<sub>'` |
| Vraag of taak bij een AI-actie (eerste 500 tekens; vrije tekst, kan persoonsgegevens bevatten als de gebruiker die intypt), zonder gebruikers-id, sessie of IP-adres ([#313](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/313)) | tabel `ai_logboek` (V039), alleen-toevoegen | alle bezoekers die AI gebruiken | verantwoording van AI-gebruik | publieke taak | bewaartermijn per instantie, standaard **365 dagen** (besluit over de standaard staat open) |
| Login van wie een AI-verklaring uploadde of een noodstop zette ([#307](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/307)) | tabellen `ai_verklaringen`, `ai_usecases`, `ai_vrijgave_log` | beheerders | navolgbaarheid van de vrijgave | publieke taak | zolang de instantie bestaat |
| Client-id van de leverende machineclient | `laden.leveringen.client_id` | systemen (geen persoon; bij testaccounts `uc-<usecase>-<actor>`) | herkomst van data | publieke taak | zolang de levering bestaat |
| Functioneel contactadres van de organisatie | tabel `organisatie` | organisatie | contact | n.v.t. (geen persoon, mits functioneel) | - |
| Al het bovenstaande in back-ups | `backups/` | | herstel | | `BACKUP_BEWAAR_DAGEN` (standaard 30), plus de termijn van de externe kopie |

Geen cookies voor tracking of analytics; alleen het functionele sessiecookie `session_token` (`HttpOnly`, `SameSite=lax`, `Secure` bij HTTPS) en de cookies van Keycloak bij inloggen. Er is geen cookiemelding nodig voor functionele cookies.

## De data zelf: geen persoonsvelden

- De **projectlaag** (gebieden, indicatoren, waarden, Kompas) bevat geen persoonsvelden: waarden horen bij een gebied (buurt, wijk, gemeente, deelgebied), niet bij een persoon of adres. De laad-API accepteert alleen de vaste profielen ([profielen](../api/laden/profielen/README.md)); geen ervan heeft een veld voor een persoon.
- **Herleidbaarheid:** open data van CBS en RIVM is al beveiligd tegen onthulling (afronding, onderdrukking van kleine aantallen). Voor **interne bronnen** (bijvoorbeeld sociaal domein) is dat de verantwoordelijkheid van de leverende partij: lever alleen aggregaten met een minimumaantal (bijvoorbeeld CBS-regel: geen cellen onder 10), en leg dat vast in de use case. D-OmniTwin controleert dat nu niet.
- **Interne lagen** (kaartlagen of datasets uit eigen systemen, `SWF_*`-paden in de use cases) staan niet in de repository en komen alleen in de installatie van de organisatie zelf. Ze zijn standaard publiek leesbaar via de kaart en de data-API: publiceer daarom alleen wat openbaar mag zijn. Afscherming per rol bestaat nog niet.
- De **ruwe leveringen** (volume `leveringen`) bevatten wat de bron aanlevert; bewaartermijn `LADEN_BEWAAR_VERSIES` (10), `LADEN_BEWAAR_DAGEN` (365) en `LADEN_BEWAAR_AFGEKEURD_DAGEN` (30).

## AI-assistent

| Instelling | Wat verlaat de organisatie |
|---|---|
| **Lokaal model** (Ollama op eigen hardware, standaard) | Niets. Vraag, kaartcontext en indicatorwaarden blijven binnen. |
| **Zonder taalmodel** | Niets. Chat-intenties zijn regelgebaseerd; de samenvattingen vallen terug op een vaste tekst. |
| **Externe aanbieder** via de LiteLLM-gateway (Anthropic, OpenAI, Google) | De vraag van de gebruiker (vrije tekst, kan persoonsgegevens bevatten als de gebruiker die intypt), de systeemprompt, de naam van het gebied en de indicatorwaarden. Geen accounts, IP-adressen of logs. |
| **AI-zoeken** (embeddings) | Niets: het model draait in de container, offline. |

Bij een externe aanbieder: verwerkersovereenkomst, locatie van verwerking (EU of passende waarborgen), geen gebruik voor training (zakelijke API-voorwaarden), en een afweging in de IAMA of DPIA. Zie ook de waarschuwing in [LLM](../9-beheer/installatie.md#andere-aanbieders-via-de-litellm-gateway). Toon gebruikers bij de chat dat ze geen persoonsgegevens moeten invoeren (staat nog niet in de UI, zie open punten).

## Beveiligingsmaatregelen (kort)

Wachtwoorden met bcrypt; sessietokens gehasht; inlogbegrenzing; rollen per dataset met tokens van Keycloak; beheerroutes achter login; PostgREST en pg_featureserv met alleen-lezenrollen die `users`, `sessions` en logs niet zien; security-headers en HTTPS ([Beveiliging](../9-beheer/installatie.md#beveiliging)); secrets alleen in `.env`; back-up en herstel getest ([beheerhandleiding](../9-beheer/beheerhandleiding.md#2-back-up-en-herstel)).

## Open punten

1. **Waarschuwingslogs worden nooit opgeruimd.** Elk verzoek met status 4xx (en elke mislukte login met gebruikersnaam) komt met IP-adres als `WARNING` in `app_logs` en blijft permanent staan. Voorstel: ook `WARNING`/`ERROR` na bijvoorbeeld 90 dagen opruimen of het IP-adres na 30 dagen leegmaken, en de termijnen instelbaar maken.
2. **IP-adres uit `X-Forwarded-For` ongefilterd.** De logmiddleware neemt de header over zoals de client hem stuurt (de begrenzing gebruikt wel een gecontroleerde variant). Voorstel: dezelfde functie (`grenzen.client_ip`) gebruiken en het IP-adres inkorten (laatste octet weg).
3. **Containerlogs** hebben standaard geen bewaartermijn. Documenteren en een limiet in de compose-bestanden of de daemon zetten.
4. **Chatvragen in de log** (80 tekens, 30 dagen): nodig? Anders weglaten of alleen de lengte loggen.
5. **Melding bij de chat** dat gebruikers geen persoonsgegevens invoeren, zeker bij een externe aanbieder.
6. **Herleidbaarheid van interne bronnen:** geen controle op kleine aantallen in de laadstraat. Voorstel: een minimumaantal als controle in het laadprofiel of de use case.
7. **Afscherming van interne lagen per rol** ontbreekt; alles wat geladen is, is publiek leesbaar.
8. **Verwerkingsregister:** de organisatie neemt D-OmniTwin op in haar register (accounts, logging, eventueel AI).
9. **Rechten van betrokkenen** (inzage, verwijdering): accounts zijn te verwijderen; logregels per persoon zoeken kan alleen met SQL op `app_logs`. Een beheerfunctie ontbreekt. Favorieten verwijdert de gebruiker zelf in de viewer; inzage en verwijdering van alles per `sub` (ook de kaartpositie) kan nu alleen met SQL.

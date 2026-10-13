# D-OmniTwin op Kubernetes

Losse, leesbare manifests (geen Helm) om één D-OmniTwin-instantie op Kubernetes te draaien, met de
release-images van Docker Hub. Bedoeld voor uitrol met [Rancher Fleet](https://fleet.rancher.io/) of
`kubectl apply -k`. Issue: [#406](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/406);
use case: [`usecases/uitrol-kubernetes`](../../usecases/uitrol-kubernetes/README.md).

## Wat er wordt uitgerold

| Bestand | Wat | Compose-equivalent |
|---|---|---|
| `00-namespace.yaml` | namespace `d-omnitwin` | project |
| `01-configmap.yaml` | niet-geheime instellingen (namen als in `.env.example`) | `.env` |
| `10-postgres.yaml` | PostgreSQL + PostGIS + pgvector, StatefulSet met eigen volume | `postgres` |
| `20-opslag.yaml` | volumes `uploads`, `leveringen`, `bron-cache` | volumes |
| `30-db-init-job.yaml` | Job: schema, migraties, rollen, beheerder; daarna klaar | `db-init` |
| `40-backend.yaml` | backend (FastAPI): de API's en de pagina van de viewer, wacht op db-init | `backend` |
| `45-web.yaml` | web (nginx): bestanden van de viewer en de beheeromgeving, generiek en zonder config | `web` |
| `50-postgrest.yaml` | data-API `/api/data` | `postgrest` |
| `51-pg-featureserv.yaml` | geo-API `/api/geo` | `pg_featureserv` |
| `60-traefik.yaml` | interne gateway: routes, headers, toegangscontrole, limieten | `traefik` + `deploy/traefik/dynamic.yml` |
| `70-ingress.yaml` | Ingress van het cluster naar de gateway (TLS) | poort 80 |
| `optioneel/keycloak/` | Keycloak (inloggen via OIDC) | profiel `keycloak` |
| `optioneel/llm-gateway/` | LiteLLM-gateway (niet nodig als er al een LiteLLM draait) | profiel `llm-gateway` |

Niet uitgerold: `secret.example.yaml` (voorbeeld) en `optioneel/` (alleen als je die map ook toepast).
Wat er wordt toegepast, staat in `kustomization.yaml`: een lijst bestanden, zonder patches.

Drie eigen images, elk apart uit te rollen: `sudwestfryslan/d-omnitwin` (backend, ook db-init),
`sudwestfryslan/d-omnitwin-web` (web) en `sudwestfryslan/d-omnitwin-db` (database). Configuratie zit
niet in de images maar in de ConfigMap en de Secret; web heeft geen van beide nodig.

### Routes in de gateway

| Pad | Naar | Toegang |
|---|---|---|
| `/api/...` | backend | de backend controleert zelf (ADR 0009) |
| `/`, `/health`, `/docs`, `/openapi.json` | backend | `/` en de documentatie: de backend controleert zelf |
| `/api/data/...` | PostgREST | forwardAuth `viewer-toegang` |
| `/api/geo/...` | pg_featureserv | forwardAuth `viewer-toegang` |
| `/rapport`, `/rapport/...` | web | forwardAuth `viewer-pagina` (niet ingelogd: naar het inloggen) |
| al het andere: `/static/...`, `/admin/...`, `/.well-known/security.txt` | web | open (geen data; de beheer-API's controleren zelf) |
| `/auth/...` | Keycloak (optioneel) | eigen headers |

De pagina van de viewer (`/`) blijft bij de backend: die vult per verzoek de organisatie (thema,
logo's), de ingelogde gebruiker, de demobalk en de versie in.

Waarom een eigen Traefik in de namespace: de data- en geo-API gaan eerst langs de backend
(forwardAuth, [ADR 0009](../../docs/2-architectuur/adr/0009-viewer-achter-login-forwardauth.md)),
die de header `X-Omnitwin-Toegang` meegeeft (ADR 0010). Daarnaast prefix strippen en rate limiting per
token. Dat kan een standaard Ingress niet; zo werkt het op elke ingress-controller hetzelfde.

## Zelf invullen

| Wat | Waar |
|---|---|
| Hostnaam en TLS | `70-ingress.yaml` (`host`, `tls`) en `OMNITWIN_BASE_URL` in `01-configmap.yaml`; liefst met een patch (zie Ingress) |
| IngressClass | `70-ingress.yaml` (`ingressClassName`), idem |
| StorageClass | `10-postgres.yaml` en `20-opslag.yaml` (weglaten = standaard van het cluster) |
| Instellingen | `01-configmap.yaml` (o.a. `OMNITWIN_OMGEVING`, `VIEWER_TOEGANG`, `LOAD_SAMPLE_DATA`, `OLLAMA_HOST`) |
| Geheimen | Secret `omnitwin-secrets` met minstens `DATABASE_PASSWORD` en `ADMIN_PASSWORD` (zie Secrets) |
| Vertrouwde proxy's | `TRUSTED_PROXIES` (ConfigMap) en `trustedips` in `60-traefik.yaml`: het podnetwerk van het cluster |

Wachtwoorden: alleen letters en cijfers (`openssl rand -hex 24`); het databasewachtwoord komt ook in
verbindings-URL's.

## Met een interne configuratierepo (Fleet)

De organisatie houdt een eigen repo met alleen configuratie, zoals bij andere applicaties. Een
uitgewerkt voorbeeld staat in [`deploy/voorbeeld-configrepo`](../voorbeeld-configrepo/README.md):
`rancher/d-omnitwin/` met `fleet.yaml` (`defaultNamespace: d-omnitwin`) en een `kustomization.yaml`
als overlay op deze map. Alles met standaard Kustomize, zonder deze manifests te kopiëren en aan te
passen:

- `images:` voor de versie;
- `configMapGenerator` met `behavior: merge` voor de instellingen (alleen wat afwijkt van `01-configmap.yaml`);
- een patch op de Ingress voor host, IngressClass en annotaties;
- `namespace:` en een patch die de Namespace weglaat (die maakt Fleet).

Fleet haalt geen remote Kustomize-bases op; de configrepo bevat daarom een kopie van deze map op een
release-tag (de opdracht staat in het voorbeeld). Met `kubectl apply -k`, Argo CD of Flux kan de base
ook als `https://github.com/Sudwest-Fryslan/D-OmniTwin//deploy/kubernetes?ref=v<versie>`, zodra de
repo publiek is.

## Ingress

`70-ingress.yaml` is een gewone Ingress naar de Traefik-gateway. Host, IngressClass en TLS pas je aan
met een strategic-merge-patch; `tls` en `rules` vervang je daarmee in hun geheel. Aanbevolen variant,
met haproxy en een certificaat van cert-manager:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: d-omnitwin
  namespace: d-omnitwin
  annotations:
    cert-manager.io/cluster-issuer: <cluster-issuer>
    nginx.ingress.kubernetes.io/proxy-body-size: null   # alleen voor ingress-nginx
spec:
  ingressClassName: haproxy
  tls:
    - hosts: [d-omnitwin.example.nl, tweede-naam.example.nl]
      secretName: d-omnitwin-tls          # cert-manager maakt en vernieuwt dit certificaat
  rules:
    - host: d-omnitwin.example.nl
      http: { paths: [{ path: /, pathType: Prefix, backend: { service: { name: traefik, port: { number: 80 } } } }] }
    - host: tweede-naam.example.nl        # tweede hostnaam: een extra regel
      http: { paths: [{ path: /, pathType: Prefix, backend: { service: { name: traefik, port: { number: 80 } } } }] }
```

`OMNITWIN_BASE_URL` is de hoofdnaam. Uploads en leveringen gaan tot 200 MB: stel de bodylimiet van de
ingress-controller daarop in (de annotatie verschilt per controller).

## Secrets

Geheimen staan nooit in git. Maak de Secret met de hand aan, vóór de eerste uitrol:

```bash
kubectl create namespace d-omnitwin
kubectl -n d-omnitwin create secret generic omnitwin-secrets \
  --from-literal=DATABASE_PASSWORD="$(openssl rand -hex 24)" \
  --from-literal=ADMIN_PASSWORD="$(openssl rand -hex 24)"
```

| Sleutel | Nodig | Waarvoor |
|---|---|---|
| `DATABASE_PASSWORD` | ja | databasegebruiker, ook voor PostgREST en pg_featureserv |
| `ADMIN_PASSWORD` | ja | eerste lokale beheeraccount (`ADMIN_USER`); met OIDC alleen noodtoegang |
| `OIDC_CLIENT_SECRET` | bij een vertrouwelijke client | clientgeheim (Entra ID met platform Web) |
| `LLM_API_KEY` | alleen met AI via een gateway | sleutel van LiteLLM |
| `ADMIN_API_KEY` | nee | scripts met de header `X-Admin-Key` |
| `LITELLM_MASTER_KEY` | alleen met `optioneel/llm-gateway` | gelijk aan `LLM_API_KEY` |
| `KEYCLOAK_DB_PASSWORD`, `KEYCLOAK_ADMIN_PASSWORD` | alleen met `optioneel/keycloak` | Keycloak |

`secret.example.yaml` noemt dezelfde sleutels. SOPS of Sealed Secrets kan ook, maar is niet nodig.

## Inloggen via Microsoft Entra ID

Keycloak is optioneel. De backend werkt met elke OIDC-provider en leest de rollen uit de
Keycloak-claims (`realm_access.roles`, `resource_access.<audience>.roles`) én uit de standaard-claim
`roles`, waarin Entra ID de app-rollen zet.

**App-registratie in Entra** (één tenant):

1. *Authentication*: platform **Web**, redirect-URI's per hostnaam:
   `https://d-omnitwin.example.nl/api/admin/auth/oidc/callback`, en voor het uitloggen
   `https://d-omnitwin.example.nl/admin/login` en `https://d-omnitwin.example.nl/`.
2. *Certificates & secrets*: een clientgeheim, in de Secret als `OIDC_CLIENT_SECRET`.
3. *Expose an API*: Application ID URI `api://<client-id>` en een scope, bijvoorbeeld `toegang`.
   Zo is het access token voor deze app; anders is het voor Microsoft Graph en weigert de backend het.
4. *Manifest*: `requestedAccessTokenVersion: 2` (oudere weergave: `accessTokenAcceptedVersion: 2`).
   Dan is `iss` `https://login.microsoftonline.com/<tenant-id>/v2.0` en `aud` de client-ID.
5. *App roles*: maak de rollen hieronder aan, met als *Value* precies de naam van de D-OmniTwin-rol.
6. *Enterprise applications* > de app > *Users and groups*: wijs gebruikers of groepen een rol toe.

**Instellingen** (ConfigMap):

| Variabele | Waarde |
|---|---|
| `OIDC_ISSUER` | `https://login.microsoftonline.com/<tenant-id>/v2.0` |
| `OIDC_AUDIENCE` | `<client-id>` (de `aud` van een v2-token) |
| `OIDC_CLIENT_ID` | `<client-id>` |
| `OIDC_SCOPE` | `offline_access api://<client-id>/toegang` (refresh token en het token voor deze app) |
| `OIDC_INTERN_URL` | leeg: de backend gaat rechtstreeks naar Entra |
| `OIDC_JWKS_URL` | niet zetten: discovery |

**Rollen** (*Value* van de app-rol):

| Rol | Geeft |
|---|---|
| `beheerder` | de beheeromgeving en de beheer-API's; ook de viewer bij `VIEWER_TOEGANG=inloggen` |
| `lezer` | de viewer bij `VIEWER_TOEGANG=inloggen`, geen beheer |
| `datasets:laden` | laad-API: aanleveren voor alle datasets (machineclients, type *Applications*) |
| `dataset:<id>:laden` | laad-API: aanleveren voor één dataset |

Een machineclient (bijvoorbeeld een ETL) is een eigen app-registratie met client credentials, die een
token vraagt voor `api://<client-id>/.default`; de rol ken je toe als *Application permission*.

Let op:

- De backend moet `login.microsoftonline.com` kunnen bereiken (discovery, sleutels, tokens); houd daar
  rekening mee in een NetworkPolicy of proxy.
- Met OIDC aan staat het lokale inloggen uit; `LOKAAL_INLOGGEN=true` is de noodtoegang. Ken vóór de
  overstap minstens één gebruiker de rol `beheerder` toe.
- Een ingetrokken rol werkt door zodra het access token verloopt en de backend het ververst (bij
  Entra standaard ongeveer een uur, bij Keycloak 5 minuten). Een sessie duurt hooguit 12 uur.
- Gebruikers en rollen beheer je in Entra. De beheeromgeving toont dan geen link naar Keycloak; de
  inlogknop heet nog *Inloggen met Keycloak*.

## Externe LiteLLM

AI staat standaard dicht en gaat pas per functie open als de compliancedocumenten in de beheeromgeving
staan ([#292](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/292)). Draait er al een LiteLLM in
een andere namespace, rol dan `optioneel/llm-gateway` niet uit:

- Het adres stel je in bij **Beheer > AI Configuratie**: API-type `openai`, URL
  `http://<service>.<namespace>.svc.cluster.local:4000` en de modelnaam zoals LiteLLM die kent. Er is
  geen aparte omgevingsvariabele voor; `OLLAMA_HOST` is alleen de terugval voor Ollama.
- De sleutel van LiteLLM komt in de Secret als `LLM_API_KEY`; de backend stuurt hem als bearer-token mee.
- Laat een NetworkPolicy verkeer van namespace `d-omnitwin` naar die service toe.

## Volgorde

Alles kan in één keer worden toegepast:

1. PostgreSQL start.
2. De Job `db-init-<versie>` wacht op PostgreSQL en initialiseert (lege database) of migreert (bestaande).
3. Backend, PostgREST en pg_featureserv wachten in een initContainer tot de eerste initialisatie klaar is
   (tabel `installatie_status`) en starten dan.

Het eerste beheerwachtwoord is `ADMIN_PASSWORD` uit de Secret. Zonder waarde maakt db-init er een aan en
toont het eenmalig in de log: `kubectl -n d-omnitwin logs job/db-init-0-5-1`.

## Bijwerken

1. Image-tags naar de nieuwe versie (`sudwestfryslan/d-omnitwin:<versie>`, `sudwestfryslan/d-omnitwin-web:<versie>`,
   `sudwestfryslan/d-omnitwin-db:<versie>`).
2. Naam van de Job naar de nieuwe versie (`db-init-0-5-1` wordt `db-init-0-6-0`): een Job is niet te wijzigen,
   een nieuwe naam draait opnieuw. De oude Job mag weg.
3. Toepassen. De nieuwe Job migreert; de backend wordt vervangen (strategie `Recreate`, één replica), web
   met een gewone rolling update.

Lees vóór een upgrade de CHANGELOG (sectie *Migreren*).

## Testen

- Schemacheck: de CI draait kubeconform op deze map, en bouwt het voorbeeld in
  `deploy/voorbeeld-configrepo` met deze map als base (`scripts/ci/k8s-voorbeeld-configrepo.sh controleer`).
- Rooktest: `scripts/ci/k8s-rooktest.sh` bouwt de images, maakt een tijdelijk kind-cluster, rolt deze
  manifests uit met fictieve secrets, controleert `/health`, de viewer (`/`), de beheeromgeving
  (`/admin`, web), de data- en de geo-API, speelt een upgrade na en ruimt op. In de CI: workflow
  *Kubernetes-rooktest*, ook met het voorbeeld (`K8S_ROOKTEST_MANIFESTS=voorbeeld`), bij wijzigingen in deze map, de Dockerfiles, `deploy/web/`,
  `docker-entrypoint.sh` of `db/`.

## Beperkingen

- De volumes zijn ReadWriteOnce: de backend draait met één replica. Meer replicas vraagt ReadWriteMany.
  Web heeft geen toestand en kan wel met meer replicas.
- De web-image staat pas op Docker Hub vanaf de eerste release na 0.5.1; met tag `0.5.1` bestaat hij
  nog niet.
- Back-up van PostgreSQL regelt de organisatie (bijv. `pg_dump` in een CronJob of een backup-operator);
  zie `db/README.md`.
- Keycloak gebruikt hier het standaardthema; de huisstijlthema's uit `deploy/keycloak/themes` zitten
  niet in de manifests.

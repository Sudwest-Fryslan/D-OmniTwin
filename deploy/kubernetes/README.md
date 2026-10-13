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
| `optioneel/llm-gateway/` | LiteLLM-gateway | profiel `llm-gateway` |

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
| Hostnaam en TLS | `70-ingress.yaml` (`host`, `tls`) en `OMNITWIN_BASE_URL` in `01-configmap.yaml` |
| IngressClass | `70-ingress.yaml` (`ingressClassName`) |
| StorageClass | `10-postgres.yaml` en `20-opslag.yaml` (weglaten = standaard van het cluster) |
| Instellingen | `01-configmap.yaml` (o.a. `OMNITWIN_OMGEVING`, `VIEWER_TOEGANG`, `LOAD_SAMPLE_DATA`, `OLLAMA_HOST`) |
| Geheimen | Secret `omnitwin-secrets` met minstens `DATABASE_PASSWORD` en `ADMIN_PASSWORD` (zie `secret.example.yaml`) |
| Vertrouwde proxy's | `TRUSTED_PROXIES` (ConfigMap) en `trustedips` in `60-traefik.yaml`: het podnetwerk van het cluster |

Wachtwoorden: alleen letters en cijfers (`openssl rand -hex 24`); het databasewachtwoord komt ook in
verbindings-URL's.

## Met een interne configuratierepo (Fleet)

De organisatie houdt een eigen repo met alleen configuratie, zoals bij andere applicaties:

```
interne-repo/d-omnitwin/
├── fleet.yaml                 defaultNamespace: d-omnitwin
├── kustomization.yaml         resources: de bestanden hieronder
├── 00-namespace.yaml ... 70-ingress.yaml   kopie van deze map, met eigen host en ConfigMap-waarden
└── omnitwin-secrets.yaml      versleuteld (Sealed Secrets of SOPS), nooit leesbaar in git
```

Een GitRepo in Fleet wijst naar die map. Een nieuwe versie = de image-tags en de naam van de
`db-init`-Job aanpassen (zie Bijwerken) en committen.

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

- Schemacheck: de CI draait kubeconform op deze map.
- Rooktest: `scripts/ci/k8s-rooktest.sh` bouwt de images, maakt een tijdelijk kind-cluster, rolt deze
  manifests uit met fictieve secrets, controleert `/health`, de viewer (`/`), de beheeromgeving
  (`/admin`, web), de data- en de geo-API, speelt een upgrade na en ruimt op. In de CI: workflow
  *Kubernetes-rooktest*, bij wijzigingen in deze map, de Dockerfiles, `deploy/web/`,
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

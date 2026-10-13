# Use case: D-OmniTwin uitrollen op Kubernetes (uitrol-kubernetes)

**Vraag:** kan ik als platformbeheerder van een organisatie D-OmniTwin met losse, leesbare manifests op ons Kubernetes-cluster uitrollen (bijv. met Rancher Fleet), bijwerken naar een nieuwe versie en aantonen dat de instantie werkt?
**Issue:** [#406](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/406); images van Docker Hub uit [#126](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/126); frontend en beheeromgeving in een eigen container uit [#408](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/408); Fleet-configrepo, haproxy met cert-manager, Secrets en Entra ID uit [#411](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/411).
**Automatische test:** `scripts/ci/k8s-rooktest.sh` (workflow *Kubernetes-rooktest*, met de manifests en met het voorbeeld van de configrepo), de schemacheck van de manifests en van het voorbeeld in de CI (kubeconform, `scripts/ci/k8s-voorbeeld-configrepo.sh`), en `tests/integration/test_usecases.py` (de controles hieronder, op elke installatie).

**Waarom:** elke organisatie draait haar eigen D-OmniTwin-instantie en deelt via uitwisseling, niet via één gedeelde installatie ([ADR 0007, mesh van instanties](../../docs/2-architectuur/adr/0007-geen-multi-tenancy-mesh-van-instanties.md)). Dan moet een instantie ook makkelijk op het eigen platform van een organisatie te zetten zijn. Bij SWF is dat Kubernetes met Fleet, vanuit een interne repo die alleen configuratie bevat.

## Data

Geen eigen data. De rooktest installeert het product zonder data (`LOAD_SAMPLE_DATA=false`): stuurdata, indicatordefinities en Kompas. Met `LOAD_SAMPLE_DATA=true` laadt `db-init` de demodata uit de andere use cases.

## Inrichting

Wat de organisatie zelf invult staat in [`deploy/kubernetes/README.md`](../../deploy/kubernetes/README.md): host en TLS in de Ingress, de IngressClass, eventueel een StorageClass, de instellingen en de Secret `omnitwin-secrets` (met de hand aangemaakt, niet in git).

Met Fleet: [`deploy/voorbeeld-configrepo`](../../deploy/voorbeeld-configrepo/README.md) is bijna één op één over te nemen in de configuratierepo van de organisatie: `rancher/d-omnitwin/` met `fleet.yaml` en een Kustomize-overlay op een gevendorde kopie van `deploy/kubernetes` (image-tags, instellingen met `configMapGenerator`, Ingress met haproxy en cert-manager, twee hostnamen). Inloggen kan via Microsoft Entra ID met app-rollen (`beheerder`, `lezer`); een LiteLLM die al in het cluster draait stel je in bij Beheer > AI Configuratie.

## Stappen

1. **Manifests invullen:** host, IngressClass, ConfigMap en Secret (zie Inrichting); met Fleet in de overlay van het voorbeeld.
2. **Uitrollen:** Fleet (of `kubectl apply -k`). Volgorde regelt zichzelf: PostgreSQL start, de Job `db-init-<versie>` maakt schema, rollen en beheerder aan, en backend, PostgREST en pg_featureserv wachten tot die klaar is. Web (de bestanden van viewer en beheeromgeving) start meteen; die heeft geen configuratie en geen database nodig.
3. **Controleren:** `/health` geeft database en api *online* met de versie; `/` (de viewer, backend), `/admin` (de beheeromgeving, web), `/api/geo/collections` en `/api/data/` antwoorden via de Traefik-gateway.
4. **Bijwerken:** nieuwe image-tags (backend, web en database) en een nieuwe Job-naam (`db-init-0-8-0`); in de configrepo: de base opnieuw vendoren en `images:` aanpassen. De Job draait de migraties op de bestaande database; daarna start de nieuwe backend. Stap 3 opnieuw.

De rooktest doet stap 2 tot en met 4 automatisch op een tijdelijk kind-cluster, met fictieve secrets, eerst met `deploy/kubernetes` en daarna met de overlay uit het voorbeeld (`K8S_ROOKTEST_MANIFESTS=voorbeeld`), en schrijft de uitkomst naar [`bewijs/rooktest.json`](bewijs/rooktest.json): tijdstip, versie, image-tag, gecontroleerde endpoints, duur en resultaat. Geen secrets of hostnamen.

## Acceptatiecriteria

- De manifests zijn geldig (kubeconform in de CI), ook het voorbeeld van de configrepo na `kustomize build`.
- Het voorbeeld van de configrepo bevat geen Secret, geen interne hostnamen en geen tenant- of client-ID's.
- De backend accepteert de app-rollen van Entra ID (claim `roles`); unittest `tests/unit/test_oidc.py`.
- Een verse uitrol komt zonder handwerk tot een werkende instantie (rooktest).
- Een upgrade met een nieuwe `db-init`-Job werkt op een bestaande database (rooktest).
- De controles hierboven slagen op elke installatie, ook met Docker Compose.
- Backend, web en database zijn losse images, elk apart uit te rollen; de web-image heeft geen configuratie.

## Bewijs

Het bewijs van de uitrol is [`bewijs/rooktest.json`](bewijs/rooktest.json), opnieuw te maken met `scripts/ci/k8s-rooktest.sh`. De schermen hieronder tonen een draaiende instantie.

<!-- bewijs:start -->
*Nog geen bewijs. Maken tegen een draaiende installatie: `python -m omnitwin.usecases bewijs uitrol-kubernetes`.*
<!-- bewijs:end -->

## Bekende afwijkingen

- Keycloak en de LiteLLM-gateway (`deploy/kubernetes/optioneel/`) toetst de rooktest niet.
- De rooktest heeft geen ingress-controller: de controles gaan rechtstreeks naar de Traefik-gateway in het cluster. Haproxy en cert-manager uit het voorbeeld toetst hij dus niet; de Ingress wordt wel aangemaakt.
- Inloggen via Entra ID is getoetst met unittests (tokens met Entra-claims), niet tegen een echte tenant.

# Use case: D-OmniTwin uitrollen op Kubernetes (uitrol-kubernetes)

**Vraag:** kan ik als platformbeheerder van een organisatie D-OmniTwin met losse, leesbare manifests op ons Kubernetes-cluster uitrollen (bijv. met Rancher Fleet), bijwerken naar een nieuwe versie en aantonen dat de instantie werkt?
**Issue:** [#406](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/406); images van Docker Hub uit [#126](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/126).
**Automatische test:** `scripts/ci/k8s-rooktest.sh` (workflow *Kubernetes-rooktest*), de schemacheck van de manifests in de CI (kubeconform), en `tests/integration/test_usecases.py` (de controles hieronder, op elke installatie).

**Waarom:** elke organisatie draait haar eigen D-OmniTwin-instantie en deelt via uitwisseling, niet via één gedeelde installatie ([ADR 0007, mesh van instanties](../../docs/2-architectuur/adr/0007-geen-multi-tenancy-mesh-van-instanties.md)). Dan moet een instantie ook makkelijk op het eigen platform van een organisatie te zetten zijn. Bij SWF is dat Kubernetes met Fleet, vanuit een interne repo die alleen configuratie bevat.

## Data

Geen eigen data. De rooktest installeert het product zonder data (`LOAD_SAMPLE_DATA=false`): stuurdata, indicatordefinities en Kompas. Met `LOAD_SAMPLE_DATA=true` laadt `db-init` de demodata uit de andere use cases.

## Inrichting

Wat de organisatie zelf invult staat in [`deploy/kubernetes/README.md`](../../deploy/kubernetes/README.md): host en TLS in de Ingress, de IngressClass, eventueel een StorageClass, de waarden in `01-configmap.yaml` en de Secret `omnitwin-secrets` (versleuteld in de eigen configuratierepo).

## Stappen

1. **Manifests invullen:** host, IngressClass, ConfigMap en Secret (zie Inrichting).
2. **Uitrollen:** Fleet (of `kubectl apply -k deploy/kubernetes`). Volgorde regelt zichzelf: PostgreSQL start, de Job `db-init-<versie>` maakt schema, rollen en beheerder aan, en backend, PostgREST en pg_featureserv wachten tot die klaar is.
3. **Controleren:** `/health` geeft database en api *online* met de versie; `/api/geo/collections` en `/api/data/` antwoorden via de Traefik-gateway.
4. **Bijwerken:** nieuwe image-tag en een nieuwe Job-naam (`db-init-0-6-0`). De Job draait de migraties op de bestaande database; daarna start de nieuwe backend. Stap 3 opnieuw.

De rooktest doet stap 2 tot en met 4 automatisch op een tijdelijk kind-cluster, met fictieve secrets, en schrijft de uitkomst naar [`bewijs/rooktest.json`](bewijs/rooktest.json): tijdstip, versie, image-tag, gecontroleerde endpoints, duur en resultaat. Geen secrets of hostnamen.

## Acceptatiecriteria

- De manifests zijn geldig (kubeconform in de CI).
- Een verse uitrol komt zonder handwerk tot een werkende instantie (rooktest).
- Een upgrade met een nieuwe `db-init`-Job werkt op een bestaande database (rooktest).
- De controles hierboven slagen op elke installatie, ook met Docker Compose.

## Bewijs

Het bewijs van de uitrol is [`bewijs/rooktest.json`](bewijs/rooktest.json), opnieuw te maken met `scripts/ci/k8s-rooktest.sh`. De schermen hieronder tonen een draaiende instantie.

<!-- bewijs:start -->
*Nog geen bewijs. Maken tegen een draaiende installatie: `python -m omnitwin.usecases bewijs uitrol-kubernetes`.*
<!-- bewijs:end -->

## Bekende afwijkingen

- Keycloak en de LiteLLM-gateway (`deploy/kubernetes/optioneel/`) toetst de rooktest niet.
- De rooktest heeft geen ingress-controller: de controles gaan rechtstreeks naar de Traefik-gateway in het cluster.

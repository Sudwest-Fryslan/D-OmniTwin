# D-OmniTwin in de configuratierepo (voorbeeld)

Voorbeeld voor SWF-platformbeheer en andere organisaties die met Rancher Fleet uitrollen vanuit een
eigen configuratierepo. Kopieer `rancher/d-omnitwin/` naar die repo, vendor de base (hieronder) en vul
de placeholders in. Geen Helm: Kustomize op de manifests uit [`deploy/kubernetes`](https://github.com/Sudwest-Fryslan/D-OmniTwin/blob/main/deploy/kubernetes/README.md),
met de publieke images `sudwestfryslan/d-omnitwin`, `-web` en `-db` van Docker Hub (geen pull-secret).
Issue: [#411](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/411).

```
rancher/d-omnitwin/
├── fleet.yaml            defaultNamespace: d-omnitwin
├── kustomization.yaml    base, image-tags, instellingen (configMapGenerator, behavior: merge), patches
├── ingress-patch.yaml    haproxy, cert-manager, twee hostnamen
└── base/                 gevendorde kopie van deploy/kubernetes op een release-tag
```

Secrets staan niet in de repo; die maak je met de hand aan (zie Secrets).

## Base vendoren

Fleet rendert Kustomize zelf en haalt geen remote bases op
([rancher/fleet#3230](https://github.com/rancher/fleet/issues/3230)). Daarom staat een kopie van de
base in de configrepo. Vanuit de map `rancher/d-omnitwin`, met de versie die je uitrolt:

```bash
VERSIE=0.7.0
git clone --depth 1 --branch "v$VERSIE" https://github.com/Sudwest-Fryslan/D-OmniTwin.git /tmp/d-omnitwin
rm -rf base && mkdir base
cp /tmp/d-omnitwin/deploy/kubernetes/kustomization.yaml /tmp/d-omnitwin/deploy/kubernetes/[0-9]*.yaml base/
rm -rf /tmp/d-omnitwin
```

Alleen `kustomization.yaml` en de genummerde manifests: geen `fleet.yaml` (anders ziet Fleet een
tweede bundle), geen `secret.example.yaml`. De repo is nu nog privé; tot hij publiek is, haal je de
bestanden met een account dat toegang heeft (of uit het release-archief).

Zonder Fleet (`kubectl apply -k`, Argo CD, Flux) kan de base ook als remote URL op een release-tag,
zodra de repo publiek is: `https://github.com/Sudwest-Fryslan/D-OmniTwin//deploy/kubernetes?ref=v0.7.0`
(staat als commentaar in `kustomization.yaml`).

## Invullen

| Wat | Waar |
|---|---|
| Hostnamen | `ingress-patch.yaml` (`tls.hosts`, `rules`) en `OMNITWIN_BASE_URL` (de hoofdnaam) in `kustomization.yaml` |
| Certificaat | `<cluster-issuer>` in `ingress-patch.yaml`: de ClusterIssuer van cert-manager |
| Versie | `images:` in `kustomization.yaml`, gelijk aan de tag van de base |
| Entra ID | `<tenant-id>` en `<client-id>` in `kustomization.yaml`; app-registratie: zie [Entra ID](https://github.com/Sudwest-Fryslan/D-OmniTwin/blob/main/deploy/kubernetes/README.md#inloggen-via-microsoft-entra-id) |
| Andere instellingen | `configMapGenerator` in `kustomization.yaml`; alleen wat afwijkt van `base/01-configmap.yaml` |
| StorageClass | standaard van het cluster; anders een patch op de PVC's |

De `configMapGenerator` heeft `disableNameSuffixHash: true`: de db-init-Job verwijst naar de ConfigMap
en een Job is niet te wijzigen. Na een gewijzigde instelling: `kubectl -n d-omnitwin rollout restart deploy/backend`.

## Secrets

Eenmalig, vóór de eerste uitrol. Fleet maakt de namespace ook, maar de Secret moet er eerst staan.
Wachtwoorden alleen letters en cijfers: het databasewachtwoord komt ook in verbindings-URL's.

```bash
kubectl create namespace d-omnitwin
kubectl -n d-omnitwin create secret generic omnitwin-secrets \
  --from-literal=DATABASE_PASSWORD="$(openssl rand -hex 24)" \
  --from-literal=ADMIN_PASSWORD="$(openssl rand -hex 24)" \
  --from-literal=OIDC_CLIENT_SECRET='<clientgeheim uit Entra>'
```

| Sleutel | Nodig | Waarvoor |
|---|---|---|
| `DATABASE_PASSWORD` | ja | databasegebruiker, ook voor PostgREST en pg_featureserv |
| `ADMIN_PASSWORD` | ja | lokaal beheeraccount `admin`; met Entra alleen noodtoegang (`LOKAAL_INLOGGEN=true`) |
| `OIDC_CLIENT_SECRET` | bij Entra met platform Web | clientgeheim van de app-registratie |
| `LLM_API_KEY` | alleen met AI | sleutel van de LiteLLM die al in het cluster draait |
| `ADMIN_API_KEY` | nee | scripts met de header `X-Admin-Key` |

Een sleutel toevoegen of wijzigen: dezelfde opdracht met `--dry-run=client -o yaml | kubectl apply -f -`,
daarna `kubectl -n d-omnitwin rollout restart deploy/backend`. Het databasewachtwoord wijzig je niet zo:
dat staat ook in de database.

## Controleren na de uitrol

```bash
kubectl -n d-omnitwin get pods                      # alles Running, db-init-<versie> Completed
kubectl -n d-omnitwin get jobs                      # db-init-0-7-0: 1/1
kubectl -n d-omnitwin logs job/db-init-0-7-0        # initialisatie of migraties
kubectl -n d-omnitwin logs deploy/backend
kubectl -n d-omnitwin get ingress,certificate       # certificaat Ready (cert-manager)
curl -s https://d-omnitwin.example.nl/health        # database en api "online", met de versie
```

Daarna in de browser: `https://d-omnitwin.example.nl/` (de kaart) en `/admin` (inloggen via Entra).

## Bijwerken naar een nieuwe versie

1. Lees de CHANGELOG van de nieuwe versie (sectie *Migreren*).
2. Vendor de base opnieuw met de nieuwe versie (zie hierboven).
3. Zet `images:` in `kustomization.yaml` op dezelfde versie.
4. Commit. Fleet rolt uit.

De nieuwe base bevat een db-init-Job met de versie in de naam (`db-init-0-7-0` wordt `db-init-0-8-0`).
Die draait de migraties op de bestaande database; de backend start daarna opnieuw. De oude Job haalt
Fleet weg. Controleer met de opdrachten hierboven, met de nieuwe Job-naam.

## AI

AI staat standaard dicht en gaat per functie open in de beheeromgeving (compliance,
[#292](https://github.com/Sudwest-Fryslan/D-OmniTwin/issues/292)). Een LiteLLM die al in het cluster
draait, gebruik je zonder `optioneel/llm-gateway`: zie [Externe LiteLLM](https://github.com/Sudwest-Fryslan/D-OmniTwin/blob/main/deploy/kubernetes/README.md#externe-litellm).

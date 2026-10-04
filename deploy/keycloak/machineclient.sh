#!/bin/bash
# Machineclient (client credentials) aanmaken of bijwerken, met rollen, en het secret tonen.
# Voor een ETL die levert aan de laad-API (/api/laden/v1), of voor de integratietests.
# Draait in de Keycloak-container (compose-profiel keycloak), met de tijdelijke beheerder uit
# KEYCLOAK_ADMIN_PASSWORD (of KC_BEHEERDER, zie client-secret.sh):
#
#   docker compose exec keycloak bash /opt/keycloak/omnitwin/machineclient.sh etl-swf \
#       dataset:swf-monitor-definities:laden dataset:swf-monitor-waarden:laden
#   docker compose exec keycloak bash /opt/keycloak/omnitwin/machineclient.sh usecase-test datasets:laden beheerder
#
# Rollen: `beheerder` en `lezer` zijn realm-rollen; al het andere is een client-rol op omnitwin-api
# (bijv. datasets:laden of dataset:<id>:laden; een ontbrekende datasetrol wordt aangemaakt).
# De client krijgt de audience-mapper voor omnitwin-api, geen refresh-token en geen andere flows.
# Bestaat de client al, dan worden alleen ontbrekende rollen toegevoegd. Uitvoer: alleen het secret.
set -euo pipefail

CLIENT="${1:?Gebruik: machineclient.sh <client-id> [rol ...]}"
shift
REALM="${KEYCLOAK_REALM:-omnitwin}"
API=omnitwin-api
KCADM=/opt/keycloak/bin/kcadm.sh
CFG="$(mktemp)"
trap 'rm -f "$CFG"' EXIT

if [ -n "${KC_BEHEERDER:-}" ]; then
    "$KCADM" config credentials --config "$CFG" --server http://localhost:8080/auth --realm master --user "$KC_BEHEERDER" >&2
else
    "$KCADM" config credentials --config "$CFG" --server http://localhost:8080/auth --realm master \
        --user "${KC_BOOTSTRAP_ADMIN_USERNAME:-admin}" \
        --password "${KC_BOOTSTRAP_ADMIN_PASSWORD:?KEYCLOAK_ADMIN_PASSWORD ontbreekt}" >/dev/null
fi
kc() { "$KCADM" "$@" --config "$CFG" -r "$REALM"; }

ID="$(kc get clients -q clientId="$CLIENT" --fields id --format csv --noquotes)"
if [ -z "$ID" ]; then
    kc create clients -f - >/dev/null <<JSON
{
  "clientId": "$CLIENT",
  "name": "Machineclient $CLIENT",
  "enabled": true,
  "protocol": "openid-connect",
  "publicClient": false,
  "clientAuthenticatorType": "client-secret",
  "standardFlowEnabled": false,
  "implicitFlowEnabled": false,
  "directAccessGrantsEnabled": false,
  "serviceAccountsEnabled": true,
  "frontchannelLogout": false,
  "fullScopeAllowed": true,
  "attributes": {"client_credentials.use_refresh_token": "false"},
  "protocolMappers": [{
    "name": "audience $API", "protocol": "openid-connect", "protocolMapper": "oidc-audience-mapper",
    "config": {"included.client.audience": "$API", "access.token.claim": "true", "id.token.claim": "false",
               "introspection.token.claim": "true"}
  }]
}
JSON
    ID="$(kc get clients -q clientId="$CLIENT" --fields id --format csv --noquotes)"
    echo "Client $CLIENT aangemaakt." >&2
fi

SA="service-account-$CLIENT"
API_ID="$(kc get clients -q clientId="$API" --fields id --format csv --noquotes)"
for ROL in "$@"; do
    case "$ROL" in
        beheerder|lezer)
            kc add-roles --uusername "$SA" --rolename "$ROL" >/dev/null ;;
        *)
            if ! kc get "clients/$API_ID/roles/$ROL" >/dev/null 2>&1; then
                kc create "clients/$API_ID/roles" -s name="$ROL" -s "description=Aangemaakt door machineclient.sh" >/dev/null
                echo "Client-rol $ROL op $API aangemaakt." >&2
            fi
            kc add-roles --uusername "$SA" --cclientid "$API" --rolename "$ROL" >/dev/null ;;
    esac
    echo "Rol $ROL toegekend aan $CLIENT." >&2
done

kc get "clients/$ID/client-secret" --fields value --format csv --noquotes

#!/bin/bash
# Secret van een confidential client (bijv. een machineclient voor een ETL) opvragen of vernieuwen.
# Draait in de Keycloak-container (compose-profiel keycloak, #214), met de tijdelijke beheerder
# uit KEYCLOAK_ADMIN_PASSWORD:
#
#   docker compose exec keycloak bash /opt/keycloak/omnitwin/client-secret.sh etl-voorbeeld
#   docker compose exec keycloak bash /opt/keycloak/omnitwin/client-secret.sh etl-voorbeeld --nieuw
#
# Realm: KEYCLOAK_REALM (standaard omnitwin). Heb je de tijdelijke beheerder verwijderd, geef dan
# een eigen beheerder op met KC_BEHEERDER=<naam> (het wachtwoord wordt gevraagd), of kijk in de
# admin-console bij Clients > <client> > Credentials.
set -euo pipefail

CLIENT="${1:?Gebruik: client-secret.sh <client-id> [--nieuw]}"
REALM="${KEYCLOAK_REALM:-omnitwin}"
KCADM=/opt/keycloak/bin/kcadm.sh
CFG="$(mktemp)"
trap 'rm -f "$CFG"' EXIT

if [ -n "${KC_BEHEERDER:-}" ]; then
    "$KCADM" config credentials --config "$CFG" --server http://localhost:8080/auth \
        --realm master --user "$KC_BEHEERDER" >&2
else
    "$KCADM" config credentials --config "$CFG" --server http://localhost:8080/auth \
        --realm master --user "${KC_BOOTSTRAP_ADMIN_USERNAME:-admin}" \
        --password "${KC_BOOTSTRAP_ADMIN_PASSWORD:?KEYCLOAK_ADMIN_PASSWORD ontbreekt}" >/dev/null
fi

ID="$("$KCADM" get clients --config "$CFG" -r "$REALM" -q clientId="$CLIENT" --fields id --format csv --noquotes)"
if [ -z "$ID" ]; then
    echo "Client '$CLIENT' niet gevonden in realm '$REALM'." >&2
    exit 1
fi

if [ "${2:-}" = "--nieuw" ]; then
    "$KCADM" create "clients/$ID/client-secret" --config "$CFG" -r "$REALM" >/dev/null
fi
"$KCADM" get "clients/$ID/client-secret" --config "$CFG" -r "$REALM" --fields value --format csv --noquotes

# 0008. Inloggen in de beheeromgeving via Keycloak, met de backend als BFF

- Status: voorgesteld
- Datum: 2026-10-03
- Issue: https://github.com/TLaan/D-OmniTwin/issues/251
- Raakt: ADR 0005 (API's per doel), ADR 0007 (eigen Keycloak per instantie), https://github.com/TLaan/D-OmniTwin/issues/65 (wie mag wat), https://github.com/TLaan/D-OmniTwin/issues/195 (0.3.0)

## Context

De beheeromgeving (React, `admin-panel/`) logde in met een eigen gebruikerstabel (`users`, bcrypt) en een HttpOnly-sessiecookie. Keycloak draait sinds 0.3.0 als identity provider (realm `omnitwin`, client `omnitwin-web` met PKCE, realm-rollen `beheerder` en `lezer`), maar alleen de laad-API gebruikte het. Er waren dus twee gebruikersbestanden, en geen gebruikersbeheer in de UI.

Alle bestaande beheer-endpoints (`/api/admin/*`, `/api/visualisatie/admin/*`) werken met het sessiecookie (`vereis_admin`). Scripts gebruiken `X-Admin-Key`.

## Besluit

**1. Gebruikers en rollen staan in Keycloak.** Met `OIDC_ISSUER` gezet log je in via Keycloak; realm-rol `beheerder` geeft beheerrechten, `lezer` niet (403). D-OmniTwin bouwt geen eigen gebruikersbeheer; de beheer-UI linkt naar de admin-console van Keycloak. De koppeling rol → rechten staat in de realmexport (`deploy/keycloak/realm-omnitwin.json`) en is daarmee data die tussen instanties uitwisselbaar is (ADR 0007).

**2. De backend is de OIDC-client (backend-for-frontend).** De browser krijgt geen token:

- `GET /api/admin/auth/oidc/login` start authorization code + PKCE (S256) met client `omnitwin-web`; state, verifier en terugadres staan 10 minuten in een HttpOnly-cookie op `/api/admin/auth/oidc`.
- `GET /api/admin/auth/oidc/callback` controleert de state, wisselt de code in (intern, via `OIDC_INTERN_URL`), controleert het access token met dezelfde code als de laad-API (`oidc.controleer_token`) en zet het bestaande cookie `session_token`. De sessie staat in tabel `oidc_sessies` (alleen de hash van het cookie, `sub`, `preferred_username`, rollen, refresh token en id-token).
- Verloopt het access token (5 minuten), dan ververst de backend het bij het volgende verzoek; de rij wordt daarvoor vergrendeld, omdat Keycloak refresh tokens roteert. Weigert Keycloak (gebruiker uitgeschakeld, sessie beëindigd, 30 minuten inactief), dan is de sessie weg (401). Een ingetrokken rol werkt zo binnen enkele minuten door.
- Uitloggen verwijdert de sessie en stuurt de browser naar het `end_session_endpoint` van Keycloak met `id_token_hint` (RP-initiated logout).

Bij het interne verkeer naar Keycloak stuurt de backend `X-Forwarded-Proto/Host/Port` van het publieke adres mee. Anders geeft Keycloak met `KC_HOSTNAME=localhost` (alleen een hostnaam) tokens uit met de interne issuer (`http://localhost:8080/...`), die de `iss`-controle dan weigert.

**3. Beheer-endpoints accepteren sessie én token.** `vereis_admin` accepteert een lokale of OIDC-sessie, een `Authorization: Bearer`-token van Keycloak met de rol `beheerder`, of `X-Admin-Key`. De endpoints zelf veranderen niet.

**4. Lokale accounts zijn noodtoegang.** Met `OIDC_ISSUER` gezet staan lokaal inloggen en bestaande lokale sessies uit, tenzij `LOKAAL_INLOGGEN=true` (waarschuwing in de log bij de start en bij elke lokale login, en in de UI). Zonder `OIDC_ISSUER` werkt het lokale inloggen zoals altijd: de eenvoudige installatie blijft zonder Keycloak.

**5. Audit.** In de log alleen `sub` en `preferred_username`, nooit e-mail of tokens; de scope is `openid profile`. Een goedkeuring van een ontologie door een Keycloak-gebruiker staat in `indicatoren.gevalideerd_door_sub` en `gevalideerd_door_gebruikersnaam` (`gevalideerd_door` verwijst naar `users`).

## Alternatieven

- **Tokens in de SPA** (keycloak-js of oidc-client-ts, access token in het geheugen, `Authorization`-header op elke aanroep). Geen sessietabel, maar: elke beheeraanroep in de UI moet om, het token is bereikbaar voor JavaScript (XSS), silent refresh via een iframe werkt slecht met third-party-cookieblokkering, en de bestaande cookie-endpoints (ook `/api/report` met beheerdersinformatie) moeten anders. Afgewezen.
- **Reverse proxy met OIDC** (oauth2-proxy of Traefik-plugin voor `/admin`). Commodity, maar een extra container en de backend moet de identiteit dan uit headers vertrouwen; rollen per endpoint en noodtoegang worden lastiger. Mogelijk later, als meer onderdelen achter één login moeten.
- **Lokale accounts naast Keycloak laten bestaan.** Twee gebruikersbestanden blijven bestaan en wachtwoorden lekken naar een plek zonder brute-force-bescherming of MFA. Alleen als noodtoegang.

## Gevolgen

- Gebruikers, wachtwoorden, MFA en koppeling met een eigen IdP (Entra ID, later eHerkenning) regel je in Keycloak; D-OmniTwin hoeft daar niets voor te bouwen.
- De backend houdt per ingelogde gebruiker een sessierij met een refresh token: die tabel hoort bij de backup en is gevoelig (zelfde database als `sessions`).
- De redirect-URI van `omnitwin-web` moet het adres van de installatie bevatten. De realmexport vult `OMNITWIN_BASE_URL/*` in bij de import; een bestaande realm pas je in de admin-console aan.
- Inloggen in de kaartapplicatie (viewer), optioneel de hele viewer achter de login: [ADR 0009](0009-viewer-achter-login-forwardauth.md). Nog niet: niet-openbare lagen alleen voor `lezer` (https://github.com/TLaan/D-OmniTwin/issues/254).

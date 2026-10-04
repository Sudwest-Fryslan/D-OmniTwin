"""
Testaccounts voor de actoren van een use case (#223), alleen in test en dev.

Een use case declareert in `actoren` wie hem gebruikt (gebruikers en machineclients met rollen),
nooit wachtwoorden of secrets. Met `python -m omnitwin.usecases installeer|test <naam> --testaccounts`
maakt de uitvoerder die actoren tijdelijk aan in Keycloak (realm `KEYCLOAK_REALM`, standaard omnitwin),
via de admin-API:

- naam `uc-<usecase>-<actor>`: een gebruiker (wachtwoord) of een machineclient (client credentials,
  secret); daarnaast per use case één loginclient `uc-<usecase>--login` (public, alleen
  wachtwoordgrant), zodat de uitvoerder tokens van de testgebruikers kan halen;
- rollen: zonder `:` een realm-rol (`beheerder`, `lezer`; moet bestaan), met `:` een client-rol op
  `omnitwin-api` (`dataset:<id>:laden`, `datasets:laden`; een ontbrekende wordt aangemaakt, zoals
  deploy/keycloak/machineclient.sh); een machineclient krijgt precies die rollen, zonder de standaardrol
  van de realm (`default-roles-<realm>`, met `lezer`), zodat toegang per laag (#254) te toetsen is;
- kenmerk: de clients krijgen de attributen `omnitwin.usecase` en `omnitwin.testaccount.tot`
  (levensduur, `OMNITWIN_TESTACCOUNTS_UUR`, standaard 24); de gebruikers heten `Testaccount <usecase>`
  (voor- en achternaam), omdat Keycloak zonder aangepast gebruikersprofiel geen eigen attributen bewaart;
- wachtwoorden en secrets zijn willekeurig (secrets.token_urlsafe) en staan alleen in
  `.usecase-accounts.json` (in .gitignore; ander pad: `OMNITWIN_TESTACCOUNTS_BESTAND`), nooit in de log.

Weigert als `OMNITWIN_TESTACCOUNTS` niet `1` is of `OMNITWIN_OMGEVING` productie is. `opruimen` mag
altijd: het verwijdert alleen accounts met het prefix van de use case én zijn kenmerk.

Toegang tot de admin-API (kies één, nooit in de repository):

- `KEYCLOAK_ADMIN_CLIENT_ID` en `KEYCLOAK_ADMIN_CLIENT_SECRET`: een machineclient in de realm met
  service account en de client-rollen van `realm-management` manage-users, manage-clients, view-realm,
  view-clients en query-users (aanbevolen zodra de tijdelijke beheerder weg is);
- anders `KEYCLOAK_ADMIN` (standaard admin) en `KEYCLOAK_ADMIN_PASSWORD`: de (tijdelijke) beheerder
  van realm master, zoals in .env bij het compose-profiel keycloak.

Adres van Keycloak: `KEYCLOAK_URL` (standaard `OMNITWIN_BASE_URL` + /auth).
"""

from __future__ import annotations

import datetime as dt
import json
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BESTAND = ROOT / ".usecase-accounts.json"
API_CLIENT = "omnitwin-api"
KENMERK_UC, KENMERK_TOT = "omnitwin.usecase", "omnitwin.testaccount.tot"
PRODUCTIE = {"productie", "production", "prod"}
TIMEOUT = 30


class TestaccountFout(Exception):
    """Testaccounts niet toegestaan, of de admin-API van Keycloak weigert."""


def toegestaan():
    """Alleen met OMNITWIN_TESTACCOUNTS=1 en niet in productie (OMNITWIN_OMGEVING). Anders TestaccountFout."""
    omgeving = (os.environ.get("OMNITWIN_OMGEVING") or "").strip().lower()
    if omgeving in PRODUCTIE:
        raise TestaccountFout(f"testaccounts geweigerd: OMNITWIN_OMGEVING={omgeving} (alleen in test en dev)")
    if os.environ.get("OMNITWIN_TESTACCOUNTS") != "1":
        raise TestaccountFout("testaccounts geweigerd: zet OMNITWIN_TESTACCOUNTS=1 (alleen in test en dev)")


def prefix(usecase):
    return f"uc-{usecase}-"


def accountnaam(usecase, actor):
    return f"{prefix(usecase)}{actor}"


def loginclient(usecase):
    # Dubbel streepje: een actornaam kan niet met '-' beginnen, dus geen botsing met een actor
    return f"{prefix(usecase)}-login"


def keycloak_url(basis=None):
    if os.environ.get("KEYCLOAK_URL"):
        return os.environ["KEYCLOAK_URL"].rstrip("/")
    return (basis or os.environ.get("OMNITWIN_BASE_URL", "http://localhost")).rstrip("/") + "/auth"


def realm():
    return os.environ.get("KEYCLOAK_REALM", "omnitwin")


# ------------------------------------------------------------------ admin-API

class KeycloakBeheer:
    """Dunne client voor de admin-API van Keycloak (alleen wat de testaccounts nodig hebben)."""

    def __init__(self, kc=None, realm_=None, sessie=None):
        import requests
        self.kc, self.realm = (kc or keycloak_url()).rstrip("/"), realm_ or realm()
        self.s = sessie or requests.Session()
        self._token = None

    # -- token: service account in de realm, of de beheerder van master
    def _haal_token(self):
        cid, geheim = os.environ.get("KEYCLOAK_ADMIN_CLIENT_ID"), os.environ.get("KEYCLOAK_ADMIN_CLIENT_SECRET")
        if cid and geheim:
            url, data, auth = f"{self.kc}/realms/{self.realm}/protocol/openid-connect/token", \
                {"grant_type": "client_credentials"}, (cid, geheim)
        elif os.environ.get("KEYCLOAK_ADMIN_PASSWORD"):
            url, auth = f"{self.kc}/realms/master/protocol/openid-connect/token", None
            data = {"grant_type": "password", "client_id": "admin-cli",
                    "username": os.environ.get("KEYCLOAK_ADMIN", "admin"),
                    "password": os.environ["KEYCLOAK_ADMIN_PASSWORD"]}
        else:
            raise TestaccountFout("geen toegang tot de admin-API van Keycloak: zet KEYCLOAK_ADMIN_CLIENT_ID en "
                                  "KEYCLOAK_ADMIN_CLIENT_SECRET, of KEYCLOAK_ADMIN_PASSWORD")
        r = self.s.post(url, data=data, auth=auth, timeout=TIMEOUT)
        if r.status_code != 200:
            raise TestaccountFout(f"admin-token geweigerd door Keycloak (HTTP {r.status_code})")
        return r.json()["access_token"]

    def _verzoek(self, methode, pad, verwacht=(200, 201, 204), **kw):
        """Verzoek op /admin/realms/<realm><pad>; bij 401 eenmaal een nieuw token (admin-tokens leven kort)."""
        url = f"{self.kc}/admin/realms/{self.realm}{pad}"
        for poging in range(2):
            if self._token is None:
                self._token = self._haal_token()
            r = self.s.request(methode, url, headers={"Authorization": f"Bearer {self._token}"},
                               timeout=TIMEOUT, **kw)
            if r.status_code == 401 and poging == 0:
                self._token = None
                continue
            break
        if verwacht and r.status_code not in verwacht:
            # Alleen methode, pad en status: de body kan een wachtwoord of secret bevatten
            raise TestaccountFout(f"Keycloak admin-API: {methode} {pad} gaf HTTP {r.status_code}")
        return r

    @staticmethod
    def _id_uit(r):
        return r.headers["Location"].rstrip("/").rsplit("/", 1)[-1]

    def client_id(self, client_id):
        """Interne id van een client (op clientId), of None."""
        r = self._verzoek("GET", "/clients", params={"clientId": client_id})
        for c in r.json():
            if c.get("clientId") == client_id:
                return c["id"]
        return None

    def _rol(self, rol, maak=True):
        """(pad voor de role-mapping, representatie). Met ':' een client-rol op omnitwin-api."""
        if ":" not in rol:
            r = self._verzoek("GET", f"/roles/{rol}", verwacht=(200, 404))
            if r.status_code == 404:
                raise TestaccountFout(f"realm-rol {rol!r} bestaat niet in realm {self.realm}")
            return "realm", r.json()
        api = self.client_id(API_CLIENT)
        if api is None:
            raise TestaccountFout(f"client {API_CLIENT} ontbreekt in realm {self.realm}")
        r = self._verzoek("GET", f"/clients/{api}/roles/{rol}", verwacht=(200, 404))
        if r.status_code == 404 and maak:
            self._verzoek("POST", f"/clients/{api}/roles",
                          json={"name": rol, "description": "Aangemaakt voor een use-case-testaccount (#223)"})
            r = self._verzoek("GET", f"/clients/{api}/roles/{rol}")
        return f"clients/{api}", r.json()

    def ken_rollen_toe(self, gebruiker_id, rollen):
        per_doel = {}
        for rol in rollen:
            doel, rep = self._rol(rol)
            per_doel.setdefault(doel, []).append(rep)
        for doel, reps in per_doel.items():
            self._verzoek("POST", f"/users/{gebruiker_id}/role-mappings/{doel}", json=reps)

    def maak_gebruiker(self, naam, wachtwoord, usecase, rollen):
        r = self._verzoek("POST", "/users", json={
            "username": naam, "enabled": True, "firstName": "Testaccount", "lastName": usecase,
            "email": f"{naam}@example.org", "emailVerified": True, "requiredActions": [],
            "credentials": [{"type": "password", "value": wachtwoord, "temporary": False}]})
        gid = self._id_uit(r)
        self.ken_rollen_toe(gid, rollen)
        return gid

    def _maak_client(self, rep):
        r = self._verzoek("POST", "/clients", json={
            "protocol": "openid-connect", "enabled": True, "standardFlowEnabled": False,
            "implicitFlowEnabled": False, "frontchannelLogout": False, "fullScopeAllowed": True,
            "protocolMappers": [{
                "name": f"audience {API_CLIENT}", "protocol": "openid-connect",
                "protocolMapper": "oidc-audience-mapper",
                "config": {"included.client.audience": API_CLIENT, "access.token.claim": "true",
                           "id.token.claim": "false", "introspection.token.claim": "true"}}],
            **rep})
        return self._id_uit(r)

    @staticmethod
    def _kenmerk(usecase, tot):
        return {KENMERK_UC: usecase, KENMERK_TOT: tot}

    def maak_machineclient(self, naam, geheim, usecase, rollen, tot):
        cid = self._maak_client({
            "clientId": naam, "name": f"Testaccount {usecase}", "publicClient": False,
            "clientAuthenticatorType": "client-secret", "secret": geheim, "serviceAccountsEnabled": True,
            "directAccessGrantsEnabled": False,
            "attributes": {"client_credentials.use_refresh_token": "false", **self._kenmerk(usecase, tot)}})
        sa = self._verzoek("GET", f"/clients/{cid}/service-account-user").json()
        self.ken_rollen_toe(sa["id"], rollen)
        self._zonder_standaardrol(sa["id"])
        return cid

    def _zonder_standaardrol(self, gebruiker_id):
        """Een machineclient krijgt precies de rollen uit het manifest: de standaardrol van de realm
        (default-roles-<realm>, met lezer) gaat van het service account af, zodat een ETL-client zonder
        `lezer` geen interne data ziet (#254). Bestaat de rol niet, dan niets."""
        r = self._verzoek("GET", f"/roles/default-roles-{self.realm}", verwacht=(200, 404))
        if r.status_code == 200:
            self._verzoek("DELETE", f"/users/{gebruiker_id}/role-mappings/realm", json=[r.json()])

    def maak_loginclient(self, naam, usecase, tot):
        """Public client met alleen de wachtwoordgrant: tokens voor de testgebruikers (alleen test/dev)."""
        return self._maak_client({
            "clientId": naam, "name": f"Testaccounts {usecase} (inloggen)", "publicClient": True,
            "directAccessGrantsEnabled": True, "serviceAccountsEnabled": False,
            "attributes": self._kenmerk(usecase, tot)})

    def verwijder(self, usecase):
        """Clients en gebruikers met het prefix van de use case én zijn kenmerk. Geeft de verwijderde namen."""
        p, weg = prefix(usecase), []
        for c in self._verzoek("GET", "/clients", params={"clientId": p, "search": "true", "max": 1000}).json():
            if c.get("clientId", "").startswith(p) and (c.get("attributes") or {}).get(KENMERK_UC) == usecase:
                self._verzoek("DELETE", f"/clients/{c['id']}", verwacht=(204, 404))
                weg.append(c["clientId"])
        for g in self._verzoek("GET", "/users", params={"search": p, "max": 1000}).json():
            if g.get("username", "").startswith(p) and g.get("lastName") == usecase \
                    and g.get("firstName") == "Testaccount":
                self._verzoek("DELETE", f"/users/{g['id']}", verwacht=(204, 404))
                weg.append(g["username"])
        return weg


# ------------------------------------------------------------------ bewaren (lokaal, buiten git)

def bestand():
    return Path(os.environ.get("OMNITWIN_TESTACCOUNTS_BESTAND") or BESTAND)


def lees(pad=None):
    pad = Path(pad or bestand())
    if not pad.exists():
        return {}
    return json.loads(pad.read_text(encoding="utf-8"))


def schrijf(data, pad=None):
    """Alleen voor de eigenaar leesbaar (0600; op Windows bepaalt de map de rechten)."""
    pad = Path(pad or bestand())
    fd = os.open(pad, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ------------------------------------------------------------------ aanmaken en opruimen

def maak(usecase, uc, beheer=None, pad=None, nu=None):
    """De actoren van één use case als testaccounts (eerst de oude met hetzelfde prefix weg).
    Geeft {actor: {soort, id, geheim, rollen}} en bewaart het in .usecase-accounts.json."""
    toegestaan()
    actoren = uc.get("actoren") or []
    if not actoren:
        return {}
    beheer = beheer or KeycloakBeheer()
    nu = nu or dt.datetime.now(dt.timezone.utc)
    tot = (nu + dt.timedelta(hours=float(os.environ.get("OMNITWIN_TESTACCOUNTS_UUR", "24")))) \
        .replace(microsecond=0).isoformat()
    beheer.verwijder(usecase)
    uit = {}
    if any(a["soort"] == "gebruiker" for a in actoren):
        beheer.maak_loginclient(loginclient(usecase), usecase, tot)
    for a in actoren:
        naam, geheim = accountnaam(usecase, a["naam"]), secrets.token_urlsafe(24)
        if a["soort"] == "gebruiker":
            beheer.maak_gebruiker(naam, geheim, usecase, a["rollen"])
        else:
            beheer.maak_machineclient(naam, geheim, usecase, a["rollen"], tot)
        uit[a["naam"]] = {"soort": a["soort"], "id": naam, "geheim": geheim, "rollen": list(a["rollen"])}
    data = lees(pad)
    data[usecase] = {"keycloak": beheer.kc, "realm": beheer.realm, "loginclient": loginclient(usecase),
                     "aangemaakt": nu.replace(microsecond=0).isoformat(), "tot": tot, "actoren": uit}
    schrijf(data, pad)
    return uit


def opruimen(usecase, beheer=None, pad=None):
    """Testaccounts van de use case verwijderen (Keycloak en het lokale bestand). Geeft de namen."""
    beheer = beheer or KeycloakBeheer()
    weg = beheer.verwijder(usecase)
    data = lees(pad)
    if usecase in data:
        del data[usecase]
        schrijf(data, pad)
    return weg


def token(account, loginclient_, token_url, sessie=None):
    """Access token voor een testaccount: client credentials (machineclient) of wachtwoordgrant via
    de loginclient (gebruiker)."""
    import requests
    s = sessie or requests
    if account["soort"] == "machineclient":
        r = s.post(token_url, data={"grant_type": "client_credentials"},
                   auth=(account["id"], account["geheim"]), timeout=TIMEOUT)
    else:
        r = s.post(token_url, data={"grant_type": "password", "client_id": loginclient_,
                                    "username": account["id"], "password": account["geheim"],
                                    "scope": "openid"}, timeout=TIMEOUT)
    if r.status_code != 200:
        raise TestaccountFout(f"geen token voor {account['id']} (HTTP {r.status_code})")
    return r.json()["access_token"]

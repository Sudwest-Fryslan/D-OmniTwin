"""
Testaccounts voor de actoren van een use case (#223): omnitwin.testaccounts en de uitvoerder met
--testaccounts. Geen stack: Keycloak is een nep-admin-API in het geheugen, de laad-API een nepsessie.
"""

import json
import os
import re
import uuid
from pathlib import Path

import pytest

from omnitwin import testaccounts as ta
from omnitwin import usecases as uc

pytestmark = pytest.mark.unit

KC = "http://kc/auth"
ADMIN = f"{KC}/admin/realms/omnitwin"


class Antwoord:
    def __init__(self, status, body=None, headers=None):
        self.status_code, self._body, self.headers = status, body, headers or {}
        self.content = b"" if body is None else json.dumps(body, default=str).encode()

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class NepKeycloak:
    """Genoeg van de admin-API en de tokenendpoints van Keycloak voor de testaccounts."""

    def __init__(self, admin_wachtwoord="geheim-admin"):
        self.admin_wachtwoord = admin_wachtwoord
        self.realmrollen = {"beheerder", "gebruikersbeheerder", "lezer", "default-roles-omnitwin"}
        self.clients = {}  # id -> representatie
        self.clientrollen = {}  # client-id -> {naam}
        self.users = {}  # id -> representatie (met _wachtwoord, _rollen)
        self.verzoeken = []
        self.tokens = set()
        self.verloop_volgende = False
        self._maak_client({"clientId": "omnitwin-api"})
        self.clientrollen[self.api_id] = {"dataset:voorbeeld:laden"}

    @property
    def api_id(self):
        return next(i for i, c in self.clients.items() if c["clientId"] == "omnitwin-api")

    def _maak_client(self, rep):
        cid = str(uuid.uuid4())
        self.clients[cid] = dict(rep, id=cid)
        if rep.get("serviceAccountsEnabled"):
            # Zoals Keycloak: een service account krijgt de standaardrol van de realm
            self.users[f"sa-{cid}"] = {
                "id": f"sa-{cid}",
                "username": f"service-account-{rep['clientId']}",
                "_client": cid,
                "_rollen": {"default-roles-omnitwin"},
            }
        return cid

    # -- tokenendpoints
    def post(self, url, data=None, auth=None, timeout=None):
        if url == f"{KC}/realms/master/protocol/openid-connect/token":
            if data.get("password") != self.admin_wachtwoord or data.get("client_id") != "admin-cli":
                return Antwoord(401, {"error": "invalid_grant"})
            return Antwoord(200, {"access_token": self._token()})
        if url.endswith("/realms/omnitwin/protocol/openid-connect/token"):
            if data["grant_type"] == "client_credentials":
                c = next((c for c in self.clients.values() if c["clientId"] == auth[0]), None)
                ok = c is not None and c.get("secret") == auth[1] and c.get("serviceAccountsEnabled")
                return Antwoord(200, {"access_token": f"tok-{auth[0]}"}) if ok else Antwoord(401, {})
            login = next((c for c in self.clients.values() if c["clientId"] == data["client_id"]), None)
            u = next((u for u in self.users.values() if u["username"] == data["username"]), None)
            ok = login and login.get("directAccessGrantsEnabled") and u and u.get("_wachtwoord") == data["password"]
            return Antwoord(200, {"access_token": f"tok-{data['username']}"}) if ok else Antwoord(401, {})
        return Antwoord(404)

    def _token(self):
        t = f"admin-{uuid.uuid4().hex}"
        self.tokens.add(t)
        return t

    # -- admin-API
    def request(self, methode, url, headers=None, timeout=None, params=None, json=None):
        self.verzoeken.append((methode, url, json))
        tok = (headers or {}).get("Authorization", "").removeprefix("Bearer ")
        if self.verloop_volgende:
            self.verloop_volgende = False
            self.tokens.discard(tok)
        if tok not in self.tokens:
            return Antwoord(401)
        assert url.startswith(ADMIN), url
        pad, params = url[len(ADMIN) :], params or {}
        if methode == "GET" and pad == "/clients":
            q = params.get("clientId", "")
            return Antwoord(
                200,
                [
                    c
                    for c in self.clients.values()
                    if (q in c["clientId"] if params.get("search") else c["clientId"] == q)
                ],
            )
        if methode == "POST" and pad == "/clients":
            if any(c["clientId"] == json["clientId"] for c in self.clients.values()):
                return Antwoord(409)
            cid = self._maak_client(json)
            return Antwoord(201, headers={"Location": f"{ADMIN}/clients/{cid}"})
        if m := re.fullmatch(r"/clients/([^/]+)", pad):
            if methode == "DELETE":
                self.clients.pop(m.group(1), None)
                self.users = {i: u for i, u in self.users.items() if u.get("_client") != m.group(1)}
                return Antwoord(204)
        if m := re.fullmatch(r"/clients/([^/]+)/service-account-user", pad):
            return Antwoord(200, next(u for u in self.users.values() if u.get("_client") == m.group(1)))
        if m := re.fullmatch(r"/clients/([^/]+)/roles", pad):
            self.clientrollen.setdefault(m.group(1), set()).add(json["name"])
            return Antwoord(201)
        if m := re.fullmatch(r"/clients/([^/]+)/roles/(.+)", pad):
            ok = m.group(2) in self.clientrollen.get(m.group(1), set())
            return Antwoord(200, {"name": m.group(2), "clientRole": True}) if ok else Antwoord(404)
        if m := re.fullmatch(r"/roles/(.+)", pad):
            return Antwoord(200, {"name": m.group(1)}) if m.group(1) in self.realmrollen else Antwoord(404)
        if methode == "POST" and pad == "/users":
            if any(u["username"] == json["username"] for u in self.users.values()):
                return Antwoord(409)
            gid = str(uuid.uuid4())
            self.users[gid] = {
                **{k: v for k, v in json.items() if k != "credentials"},
                "id": gid,
                "_wachtwoord": json["credentials"][0]["value"],
                "_rollen": set(),
            }
            return Antwoord(201, headers={"Location": f"{ADMIN}/users/{gid}"})
        if methode == "GET" and pad == "/users":
            return Antwoord(
                200,
                [
                    {k: v for k, v in u.items() if not k.startswith("_")}
                    for u in self.users.values()
                    if params.get("search", "") in u["username"]
                ],
            )
        if m := re.fullmatch(r"/users/([^/]+)", pad):
            self.users.pop(m.group(1), None)
            return Antwoord(204)
        if m := re.fullmatch(r"/users/([^/]+)/role-mappings/(realm|clients/[^/]+)", pad):
            namen = {r["name"] for r in json}
            if methode == "DELETE":
                self.users[m.group(1)]["_rollen"] -= namen
            else:
                self.users[m.group(1)]["_rollen"] |= namen
            return Antwoord(204)
        return Antwoord(404)

    # -- hulp
    def gebruiker(self, naam):
        return next((u for u in self.users.values() if u["username"] == naam), None)

    def client(self, naam):
        return next((c for c in self.clients.values() if c["clientId"] == naam), None)

    def rollen_van_client(self, naam):
        cid = self.client(naam)["id"]
        return next(u for u in self.users.values() if u.get("_client") == cid)["_rollen"]


UC = {
    "naam": "voorbeeld",
    "actoren": [
        {"naam": "beheerder", "soort": "gebruiker", "rollen": ["beheerder"]},
        {"naam": "etl-x", "soort": "machineclient", "rollen": ["dataset:ds-x:laden"]},
        {"naam": "lezer", "soort": "gebruiker", "rollen": ["lezer"]},
    ],
    "datasets": [{"id": "ds-x", "route": "laden", "client": "etl-x"}],
}


@pytest.fixture
def omgeving(monkeypatch, tmp_path):
    for k in ("KEYCLOAK_ADMIN_CLIENT_ID", "KEYCLOAK_ADMIN_CLIENT_SECRET", "OMNITWIN_OMGEVING", "KEYCLOAK_ADMIN"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("OMNITWIN_TESTACCOUNTS", "1")
    monkeypatch.setenv("KEYCLOAK_ADMIN_PASSWORD", "geheim-admin")
    monkeypatch.setenv("OMNITWIN_TESTACCOUNTS_BESTAND", str(tmp_path / ".usecase-accounts.json"))
    return tmp_path / ".usecase-accounts.json"


@pytest.fixture
def kc():
    return NepKeycloak()


@pytest.fixture
def beheer(kc):
    return ta.KeycloakBeheer(KC, "omnitwin", sessie=kc)


# ------------------------------------------------------------------ alleen in test en dev


@pytest.mark.parametrize(
    "env,melding",
    [
        ({}, "OMNITWIN_TESTACCOUNTS=1"),
        ({"OMNITWIN_TESTACCOUNTS": "true"}, "OMNITWIN_TESTACCOUNTS=1"),
        ({"OMNITWIN_TESTACCOUNTS": "1", "OMNITWIN_OMGEVING": "productie"}, "productie"),
        ({"OMNITWIN_TESTACCOUNTS": "1", "OMNITWIN_OMGEVING": "Production"}, "production"),
    ],
)
def test_geweigerd_buiten_test_en_dev(env, melding, monkeypatch):
    for k in ("OMNITWIN_TESTACCOUNTS", "OMNITWIN_OMGEVING"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    with pytest.raises(ta.TestaccountFout, match=melding):
        ta.toegestaan()


@pytest.mark.parametrize("omgeving_", [None, "test", "dev", "ontwikkeling"])
def test_toegestaan_in_test_en_dev(omgeving_, monkeypatch):
    monkeypatch.setenv("OMNITWIN_TESTACCOUNTS", "1")
    monkeypatch.delenv("OMNITWIN_OMGEVING", raising=False)
    if omgeving_:
        monkeypatch.setenv("OMNITWIN_OMGEVING", omgeving_)
    ta.toegestaan()


def test_maak_weigert_zonder_toestemming_en_doet_niets(omgeving, monkeypatch, kc, beheer):
    monkeypatch.setenv("OMNITWIN_OMGEVING", "productie")
    with pytest.raises(ta.TestaccountFout):
        ta.maak("voorbeeld", UC, beheer)
    assert kc.verzoeken == [] and not omgeving.exists()


def test_cli_weigert_testaccounts_in_productie(omgeving, monkeypatch, capsys):
    monkeypatch.setenv("OMNITWIN_OMGEVING", "productie")
    monkeypatch.setattr(uc, "laad_api_beschikbaar", lambda basis=None: True)
    assert uc.main(["installeer", "swf-definities", "--testaccounts"]) == 2
    assert uc.main(["test", "swf-definities", "--testaccounts"]) == 2
    assert "productie" in capsys.readouterr().out


# ------------------------------------------------------------------ aanmaken


def test_maak_gebruikers_machineclients_en_loginclient(omgeving, kc, beheer, capsys):
    uit = ta.maak("voorbeeld", UC, beheer)
    assert {a: v["id"] for a, v in uit.items()} == {
        "beheerder": "uc-voorbeeld-beheerder",
        "etl-x": "uc-voorbeeld-etl-x",
        "lezer": "uc-voorbeeld-lezer",
    }
    # gebruikers: wachtwoord, rollen, herkenbaar als testaccount, geen verplichte acties (wachtwoordgrant)
    b = kc.gebruiker("uc-voorbeeld-beheerder")
    assert b["_rollen"] == {"beheerder"} and b["firstName"] == "Testaccount" and b["lastName"] == "voorbeeld"
    assert b["emailVerified"] and b["requiredActions"] == [] and b["_wachtwoord"] == uit["beheerder"]["geheim"]
    assert kc.gebruiker("uc-voorbeeld-lezer")["_rollen"] == {"lezer"}
    # machineclient: service account met alleen zijn datasetrol (ontbrekende client-rol aangemaakt), kenmerk
    c = kc.client("uc-voorbeeld-etl-x")
    assert c["serviceAccountsEnabled"] and not c["publicClient"] and not c["directAccessGrantsEnabled"]
    assert c["secret"] == uit["etl-x"]["geheim"] and kc.rollen_van_client("uc-voorbeeld-etl-x") == {
        "dataset:ds-x:laden"
    }
    assert "dataset:ds-x:laden" in kc.clientrollen[kc.api_id]
    assert c["attributes"][ta.KENMERK_UC] == "voorbeeld" and c["attributes"][ta.KENMERK_TOT]
    assert c["protocolMappers"][0]["config"]["included.client.audience"] == "omnitwin-api"
    # loginclient: public, alleen wachtwoordgrant
    login = kc.client("uc-voorbeeld--login")
    assert login["publicClient"] and login["directAccessGrantsEnabled"] and not login["standardFlowEnabled"]
    # geheimen alleen in het bestand, niet in de uitvoer
    data = json.loads(omgeving.read_text(encoding="utf-8"))
    assert data["voorbeeld"]["actoren"]["etl-x"]["geheim"] == uit["etl-x"]["geheim"]
    assert data["voorbeeld"]["loginclient"] == "uc-voorbeeld--login"
    uitvoer = capsys.readouterr()
    for a in uit.values():
        assert len(a["geheim"]) >= 24 and a["geheim"] not in uitvoer.out + uitvoer.err
    if os.name == "posix":
        assert (omgeving.stat().st_mode & 0o077) == 0


def test_opnieuw_maken_vervangt_de_oude_accounts(omgeving, kc, beheer):
    een = ta.maak("voorbeeld", UC, beheer)
    twee = ta.maak("voorbeeld", UC, beheer)
    assert een["etl-x"]["geheim"] != twee["etl-x"]["geheim"]
    assert [u["username"] for u in kc.users.values() if u["username"].startswith("uc-")] == [
        "uc-voorbeeld-beheerder",
        "uc-voorbeeld-lezer",
    ]
    assert sorted(c["clientId"] for c in kc.clients.values() if c["clientId"].startswith("uc-")) == [
        "uc-voorbeeld--login",
        "uc-voorbeeld-etl-x",
    ]


def test_onbekende_realmrol_is_een_fout(omgeving, beheer):
    fout = {"naam": "x", "actoren": [{"naam": "a", "soort": "gebruiker", "rollen": ["superheld"]}]}
    with pytest.raises(ta.TestaccountFout, match="superheld"):
        ta.maak("x", fout, beheer)


def test_zonder_actoren_niets(omgeving, kc, beheer):
    assert ta.maak("leeg", {"naam": "leeg"}, beheer) == {}
    assert kc.verzoeken == []


def test_admin_token_verloopt_en_wordt_vernieuwd(omgeving, kc, beheer):
    ta.maak("voorbeeld", UC, beheer)
    kc.verloop_volgende = True
    assert beheer.client_id("omnitwin-api") == kc.api_id


def test_geen_admin_toegang_is_een_duidelijke_fout(omgeving, monkeypatch, beheer):
    monkeypatch.delenv("KEYCLOAK_ADMIN_PASSWORD")
    with pytest.raises(ta.TestaccountFout, match="KEYCLOAK_ADMIN_CLIENT_ID"):
        ta.maak("voorbeeld", UC, beheer)


def test_fout_van_de_admin_api_noemt_geen_geheimen(omgeving, kc, beheer, monkeypatch):
    monkeypatch.setattr(ta.secrets, "token_urlsafe", lambda n: "Zeer-Geheim-123456789012345")
    # een gewone gebruiker met dezelfde naam wordt niet opgeruimd: aanmaken geeft 409
    kc.users["x"] = {"id": "x", "username": "uc-voorbeeld-beheerder", "firstName": "Jan", "lastName": "Jansen"}
    with pytest.raises(ta.TestaccountFout, match="POST /users gaf HTTP 409") as e:
        ta.maak("voorbeeld", UC, beheer)
    assert "Zeer-Geheim" not in str(e.value)


def test_service_account_voor_de_admin_api(omgeving, monkeypatch, kc, beheer):
    monkeypatch.setenv("KEYCLOAK_ADMIN_CLIENT_ID", "testaccounts-beheer")
    monkeypatch.setenv("KEYCLOAK_ADMIN_CLIENT_SECRET", "s3")
    gezien = []

    def post(url, data=None, auth=None, timeout=None):
        gezien.append((url, data["grant_type"], auth))
        return Antwoord(200, {"access_token": kc._token()})

    monkeypatch.setattr(kc, "post", post)
    ta.maak("voorbeeld", UC, beheer)
    assert gezien[0] == (
        f"{KC}/realms/omnitwin/protocol/openid-connect/token",
        "client_credentials",
        ("testaccounts-beheer", "s3"),
    )


# ------------------------------------------------------------------ tokens en opruimen


def test_tokens_voor_machineclient_en_gebruiker(omgeving, kc, beheer):
    uit = ta.maak("voorbeeld", UC, beheer)
    url = f"{KC}/realms/omnitwin/protocol/openid-connect/token"
    assert ta.token(uit["etl-x"], "uc-voorbeeld--login", url, kc) == "tok-uc-voorbeeld-etl-x"
    assert ta.token(uit["beheerder"], "uc-voorbeeld--login", url, kc) == "tok-uc-voorbeeld-beheerder"
    with pytest.raises(ta.TestaccountFout, match="HTTP 401"):
        ta.token({**uit["lezer"], "geheim": "fout"}, "uc-voorbeeld--login", url, kc)


def test_opruimen_alleen_eigen_prefix_en_kenmerk(omgeving, kc, beheer):
    kort = {
        "naam": "cbs",
        "actoren": [
            {"naam": "etl", "soort": "machineclient", "rollen": ["datasets:laden"]},
            {"naam": "lezer", "soort": "gebruiker", "rollen": ["lezer"]},
        ],
    }
    lang = {
        "naam": "cbs-kerncijfers",
        "actoren": [
            {"naam": "etl", "soort": "machineclient", "rollen": ["lezer"]},
            {"naam": "lezer", "soort": "gebruiker", "rollen": ["lezer"]},
        ],
    }
    ta.maak("cbs", kort, beheer)
    ta.maak("cbs-kerncijfers", lang, beheer)
    # 'uc-cbs-' is ook een prefix van 'uc-cbs-kerncijfers-…': het kenmerk beslist
    weg = ta.opruimen("cbs", beheer)
    assert sorted(weg) == ["uc-cbs--login", "uc-cbs-etl", "uc-cbs-lezer"]
    assert kc.client("uc-cbs-kerncijfers-etl") and kc.gebruiker("uc-cbs-kerncijfers-lezer")
    assert not kc.client("uc-cbs-etl") and not any(
        u.get("_client") and u["username"] == "service-account-uc-cbs-etl" for u in kc.users.values()
    )
    assert list(json.loads(omgeving.read_text(encoding="utf-8"))) == ["cbs-kerncijfers"]
    # een gewone gebruiker of client met hetzelfde prefix blijft staan
    kc.users["x"] = {
        "id": "x",
        "username": "uc-cbs-kerncijfers-eigen",
        "firstName": "Jan",
        "lastName": "cbs-kerncijfers",
    }
    kc._maak_client({"clientId": "uc-cbs-kerncijfers-eigen", "attributes": {}})
    ta.opruimen("cbs-kerncijfers", beheer)
    assert kc.gebruiker("uc-cbs-kerncijfers-eigen") and kc.client("uc-cbs-kerncijfers-eigen")
    assert not kc.client("uc-cbs-kerncijfers-etl")


# ------------------------------------------------------------------ uitvoerder: actoren gebruiken


class NepLaadApi:
    def __init__(self, naam, statussen=None):
        self.naam, self.basis, self.aanroepen = naam, "http://nep", []
        self.s = NepSessie(naam, statussen or {})

    def registreer(self, reg):
        self.aanroepen.append(("registreer", reg["id"]))

    def lever(self, ds_id, pad, route="laden", alleen_valideren=False):
        self.aanroepen.append(("lever", ds_id))
        return {"http": 201}

    def beheer(self, pad_api, bestand):
        self.aanroepen.append(("beheer", pad_api))
        return {"http": 200}


class NepSessie:
    """Antwoordt per (methode, padeinde) met een vaste status, zoals de laad-API voor deze actor."""

    def __init__(self, naam, statussen):
        self.naam, self.statussen, self.verzoeken, self.headers = naam, statussen, [], {"Authorization": "Bearer x"}

    def _antwoord(self, methode, url, **kw):
        self.verzoeken.append((methode, url, kw.get("params")))
        for (m, einde), status in self.statussen.items():
            if m == methode and url.endswith(einde):
                return Antwoord(status, {})
        return Antwoord(404, {})

    def get(self, url, **kw):
        return self._antwoord("GET", url, **kw)

    def post(self, url, **kw):
        return self._antwoord("POST", url, **kw)


def actor_api(uc_, accounts, statussen=None, terugval=True):
    gemaakt = {}

    def maak(tokenbron=None):
        if tokenbron is None and not terugval:
            raise uc.UseCaseFout("OMNITWIN_CLIENT_ID en OMNITWIN_CLIENT_SECRET (machineclient) zijn niet gezet")
        naam = "omgeving" if tokenbron is None else tokenbron()
        gemaakt[naam] = NepLaadApi(naam, (statussen or {}).get(naam))
        return gemaakt[naam]

    return uc.ActorApi(uc_, {"loginclient": "uc-voorbeeld--login", "actoren": accounts}, "http://nep", maak), gemaakt


@pytest.fixture
def accounts(monkeypatch):
    monkeypatch.setattr(uc, "token_url", lambda basis=None: "http://nep/token")
    monkeypatch.setattr(ta, "token", lambda acc, login, url, sessie=None: acc["id"])
    return {
        a["naam"]: {"soort": a["soort"], "id": f"uc-voorbeeld-{a['naam']}", "geheim": "-", "rollen": a["rollen"]}
        for a in UC["actoren"]
    }


def test_actorapi_registreert_als_beheerder_en_levert_als_client(accounts):
    api, gemaakt = actor_api(UC, accounts)
    api.registreer({"id": "ds-x"})
    api.lever("ds-x", "x.csv")
    assert gemaakt["uc-voorbeeld-beheerder"].aanroepen == [("registreer", "ds-x")]
    assert gemaakt["uc-voorbeeld-etl-x"].aanroepen == [("lever", "ds-x")]
    assert "omgeving" not in gemaakt
    assert api.s is gemaakt["uc-voorbeeld-beheerder"].s


def test_actorapi_valt_terug_op_de_machineclient_uit_de_omgeving(accounts):
    api, gemaakt = actor_api(UC, accounts)
    api.lever("ander-dataset", "x.csv")  # geen actor met die rol
    assert gemaakt["omgeving"].aanroepen == [("lever", "ander-dataset")]
    api2, _ = actor_api(UC, accounts, terugval=False)
    with pytest.raises(uc.UseCaseFout, match="geen actor voor leveren van ander-dataset"):
        api2.lever("ander-dataset", "x.csv")


def test_rechtencontroles(accounts):
    statussen = {
        "uc-voorbeeld-beheerder": {("POST", "/api/laden/v1/datasets"): 400},
        "uc-voorbeeld-etl-x": {
            ("POST", "/datasets/ds-x/leveringen"): 400,
            ("POST", "/datasets/ander/leveringen"): 403,
            ("POST", "/api/laden/v1/datasets"): 403,
        },
        "uc-voorbeeld-lezer": {
            ("POST", "/datasets/ds-x/leveringen"): 403,
            ("POST", "/api/laden/v1/datasets"): 403,
            ("GET", "/datasets/ds-x"): 403,
        },
    }
    api, gemaakt = actor_api(UC, accounts, statussen)
    ok = [
        {"type": "recht", "actor": "beheerder", "actie": "registreren", "toegestaan": True},
        {"type": "recht", "actor": "etl-x", "actie": "leveren", "dataset": "ds-x", "toegestaan": True},
        {"type": "recht", "actor": "etl-x", "actie": "leveren", "dataset": "ander", "toegestaan": False},
        {"type": "recht", "actor": "etl-x", "actie": "registreren", "toegestaan": False},
        {"type": "recht", "actor": "lezer", "actie": "leveren", "dataset": "ds-x", "toegestaan": False},
        {"type": "recht", "actor": "lezer", "actie": "lezen", "dataset": "ds-x", "toegestaan": False},
    ]
    for c in ok:
        assert uc.controle_api(c, api, UC) is None, c
    # de levering is een proef: ongeldige alleenValideren, dus de laad-API wijst hem af na de rolcontrole
    assert gemaakt["uc-voorbeeld-etl-x"].s.verzoeken[0][2] == {"alleenValideren": "rechtencontrole"}
    fout = {"type": "recht", "actor": "lezer", "actie": "registreren", "toegestaan": True}
    assert uc.controle_api(fout, api, UC) == "HTTP 403, verwacht toegestaan"
    fout = {"type": "recht", "actor": "beheerder", "actie": "registreren", "toegestaan": False}
    assert uc.controle_api(fout, api, UC) == "HTTP 400, verwacht 403"


def test_rechtencontrole_compat_route(accounts):
    fme = {**UC, "datasets": [{"id": "swf-monitor-waarden", "route": "compat", "client": "etl-x"}]}
    statussen = {"uc-voorbeeld-etl-x": {("POST", "/monitor_api/indicator_waarde/inlezen"): 400}}
    api, _ = actor_api(fme, accounts, statussen)
    c = {"type": "recht", "actor": "etl-x", "actie": "leveren", "dataset": "swf-monitor-waarden", "toegestaan": True}
    assert uc.controle_api(c, api, fme) is None


def test_zonder_testaccounts_rechtencontrole_overgeslagen():
    c = {"type": "recht", "actor": "lezer", "actie": "registreren", "toegestaan": False}
    assert uc.controle_api(c, NepLaadApi("omgeving"), UC).startswith("overgeslagen")


def test_controle_met_actor_draait_als_die_actor(accounts):
    statussen = {"uc-voorbeeld-lezer": {("GET", "/api/laden/v1/datasets/ds-x"): 403}}
    api, gemaakt = actor_api(UC, accounts, statussen)
    c = {"type": "aantal", "dataset": "ds-x", "gelijk": 1, "actor": "lezer"}
    with pytest.raises(RuntimeError, match="HTTP 403"):
        uc.controle_api(c, api, UC)
    assert gemaakt["uc-voorbeeld-lezer"].s.verzoeken[0][0:2] == ("GET", "http://nep/api/laden/v1/datasets/ds-x")


def test_maak_actor_apis_met_afhankelijkheden(omgeving, monkeypatch, kc, beheer, tmp_path):
    ucs = {
        "basis": {
            "naam": "basis",
            "actoren": [{"naam": "etl", "soort": "machineclient", "rollen": ["datasets:laden"]}],
        },
        "boven": {"naam": "boven", "afhankelijk_van": ["basis"], "actoren": UC["actoren"]},
        "zonder": {"naam": "zonder"},
    }
    apis = uc.maak_actor_apis(["boven", "zonder"], ucs, beheer)
    assert set(apis) == {"basis", "boven", "zonder"}
    assert set(apis["boven"].accounts) == {"beheerder", "etl-x", "lezer"} and apis["zonder"].accounts == {}
    assert set(json.loads(omgeving.read_text(encoding="utf-8"))) == {"basis", "boven"}
    weg = uc.opruimen(["boven"], ucs, beheer)
    assert set(weg) == {"basis", "boven"} and not [c for c in kc.clients.values() if c["clientId"].startswith("uc-")]


def test_maak_actor_apis_weigert_buiten_test(monkeypatch):
    monkeypatch.delenv("OMNITWIN_TESTACCOUNTS", raising=False)
    with pytest.raises(uc.UseCaseFout, match="OMNITWIN_TESTACCOUNTS=1"):
        uc.maak_actor_apis(["x"], {"x": {"naam": "x", "actoren": UC["actoren"]}})


# ------------------------------------------------------------------ manifest


def test_manifest_actor_en_recht_worden_gecontroleerd():
    m = {
        "naam": "x",
        "actoren": UC["actoren"] + [{"naam": "lezer", "soort": "gebruiker", "rollen": ["lezer"]}],
        "datasets": [],
        "controles": [
            {"type": "recht", "actor": "onbekend", "actie": "registreren", "toegestaan": False},
            {"type": "recht", "actor": "lezer", "actie": "leveren", "toegestaan": False},
            {"type": "recht", "actor": "lezer", "actie": "leveren", "dataset": "van-een-ander", "toegestaan": False},
            {"type": "idempotent", "dataset": "van-een-ander"},
        ],
    }
    fouten = uc.valideer_manifest(m)
    assert "actoren: naam lezer komt meer dan eens voor" in fouten
    assert "controle recht: actor onbekend niet in actoren" in fouten
    assert "controle recht: veld dataset ontbreekt" in fouten
    assert "controle idempotent: dataset van-een-ander niet in datasets" in fouten
    assert not any("recht: dataset van-een-ander" in f for f in fouten)


def test_actoren_in_de_use_cases():
    """Elke use case met datasets via de laad-API declareert een beheerder, de leverende client(s) en een
    lezer, met rechtencontroles; de client van een dataset is een actor met de rol van die dataset."""
    ucs = uc.lees_usecases()
    for naam, m in ucs.items():
        laden = [d for d in m.get("datasets", []) if d["route"] in ("laden", "compat")]
        if not laden:
            continue
        actoren = {a["naam"]: a for a in m.get("actoren", [])}
        assert {"beheerder", "lezer"} <= set(actoren), naam
        for d in laden:
            assert d["rol"] in actoren[d["client"]]["rollen"], (naam, d["id"])
            assert actoren[d["client"]]["soort"] == "machineclient"
        acties = {(c["actor"], c["actie"], c["toegestaan"]) for c in m["controles"] if c["type"] == "recht"}
        assert ("beheerder", "registreren", True) in acties and ("lezer", "leveren", False) in acties, naam
        assert any(a in actoren and not t for a, actie, t in acties if actie == "leveren" and a != "lezer"), naam
        assert not any("wachtwoord" in json.dumps(a) or "secret" in json.dumps(a) for a in actoren.values())


def test_accountbestand_staat_in_gitignore():
    tekst = (Path(uc.ROOT) / ".gitignore").read_text(encoding="utf-8")
    assert ".usecase-accounts.json" in tekst.splitlines()


# ------------------------------------------------------------------ toegang per laag (#254)


def test_rechtencontrole_bekijken(accounts):
    """recht bekijken: GET <pad> met het token van de actor; 401/403 = niet toegestaan."""
    pad = "/api/gebiedsmonitor/kaart_data/gt?indicator_uuid=u"
    statussen = {"uc-voorbeeld-lezer": {("GET", pad): 200}, "uc-voorbeeld-etl-x": {("GET", pad): 403}}
    api, gemaakt = actor_api(UC, accounts, statussen)
    goed = [
        {"type": "recht", "actor": "lezer", "actie": "bekijken", "pad": pad, "toegestaan": True},
        {"type": "recht", "actor": "etl-x", "actie": "bekijken", "pad": pad, "toegestaan": False},
    ]
    for c in goed:
        assert uc.controle_api(c, api, UC) is None, c
    assert gemaakt["uc-voorbeeld-lezer"].s.verzoeken == [("GET", f"http://nep{pad}", None)]
    fout = {"type": "recht", "actor": "etl-x", "actie": "bekijken", "pad": pad, "toegestaan": True}
    assert uc.controle_api(fout, api, UC) == "HTTP 403, verwacht toegestaan"
    fout = {"type": "recht", "actor": "lezer", "actie": "bekijken", "pad": pad, "toegestaan": False}
    assert uc.controle_api(fout, api, UC) == "HTTP 200, verwacht 401 of 403"


def test_manifest_recht_bekijken_vraagt_pad():
    m = {
        "naam": "x",
        "actoren": UC["actoren"],
        "datasets": [],
        "controles": [
            {"type": "recht", "actor": "lezer", "actie": "bekijken", "toegestaan": True},
            {"type": "recht", "actor": "lezer", "actie": "bekijken", "pad": "/api/x", "toegestaan": True},
        ],
    }
    fouten = uc.valideer_manifest(m)
    assert fouten.count("controle recht: veld pad ontbreekt") == 1
    assert "controle recht: veld dataset ontbreekt" not in fouten


def test_api_controle_maximaal_aantal(monkeypatch):
    import requests

    class R:
        status_code = 200

        def __init__(self, data):
            self.data = data

        def json(self):
            return self.data

    antwoorden = {"/leeg": [], "/een": [{"x": 1}]}
    monkeypatch.setattr(requests, "get", lambda url, headers=None, timeout=None: R(antwoorden[url.split("nep")[1]]))
    api = NepLaadApi("omgeving")
    api.basis = "http://nep"
    assert uc.controle_api({"type": "api", "pad": "/leeg", "anoniem": True, "maximaal_aantal": 0}, api, UC) is None
    assert (
        uc.controle_api({"type": "api", "pad": "/een", "anoniem": True, "maximaal_aantal": 0}, api, UC)
        == "1 resultaten, verwacht ≤ 0"
    )
    assert (
        uc.controle_api(
            {"type": "api", "pad": "/een", "anoniem": True, "minimaal_aantal": 1, "maximaal_aantal": 1}, api, UC
        )
        is None
    )

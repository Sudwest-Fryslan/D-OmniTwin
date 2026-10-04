"""Soort omgeving (#245): OMNITWIN_OMGEVING, zwakke wachtwoorden weigeren in productie en de
demo-accounts in Keycloak (alleen bij demo). Zonder netwerk: Keycloak is nagebootst."""

import json
from pathlib import Path

import pytest

from omnitwin import omgeving
from omnitwin.config import instellingen

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("waarde,verwacht", [
    (None, "productie"), ("", "productie"), ("productie", "productie"), ("test", "test"), ("demo", "demo"),
    ("DEMO", "demo"), (" Demo ", "demo"), ("production", "productie"), ("dev", "productie"),
])
def test_omgeving_instelling(monkeypatch, waarde, verwacht):
    if waarde is None:
        monkeypatch.delenv("OMNITWIN_OMGEVING", raising=False)
    else:
        monkeypatch.setenv("OMNITWIN_OMGEVING", waarde)
    assert instellingen().omgeving == verwacht
    assert instellingen().demo is (verwacht == "demo")


@pytest.mark.parametrize("wachtwoord,gebruiker,zwak", [
    ("admin", "admin", True), ("Admin", "beheer", True), ("wachtwoord", None, True), ("Welkom", None, True),
    ("changeme", None, True), ("12345678", None, True), ("kort12", None, True), ("beheer01", "beheer01", True),
    ("", "admin", False), (None, "admin", False), ("a8f3c19e0b7d4e21", "admin", False),
    ("correct-horse-battery", "admin", False),
])
def test_is_zwak(wachtwoord, gebruiker, zwak):
    assert omgeving.is_zwak(wachtwoord, gebruiker) is zwak


def test_productie_weigert_zwak_admin_wachtwoord():
    with pytest.raises(omgeving.OmgevingFout) as e:
        omgeving.controleer_installatie({"ADMIN_PASSWORD": "admin"})  # standaard: productie
    assert "ADMIN_PASSWORD" in str(e.value)
    with pytest.raises(omgeving.OmgevingFout):
        omgeving.controleer_installatie({"OMNITWIN_OMGEVING": "productie", "ADMIN_PASSWORD": "wachtwoord"})


def test_productie_weigert_zwak_keycloak_wachtwoord():
    with pytest.raises(omgeving.OmgevingFout, match="KEYCLOAK_ADMIN_PASSWORD"):
        omgeving.controleer_installatie({"KEYCLOAK_ADMIN_PASSWORD": "admin", "ADMIN_PASSWORD": ""})


def test_productie_sterk_of_leeg_is_goed():
    assert omgeving.controleer_installatie({"ADMIN_PASSWORD": ""}) == ["Omgeving: productie"]
    assert omgeving.controleer_installatie({"ADMIN_PASSWORD": "a8f3c19e0b7d4e21a8f3"}) == ["Omgeving: productie"]


@pytest.mark.parametrize("soort", ["test", "demo"])
def test_test_en_demo_waarschuwen_alleen(soort):
    meldingen = omgeving.controleer_installatie({"OMNITWIN_OMGEVING": soort, "ADMIN_PASSWORD": "admin"})
    assert meldingen[0] == f"Omgeving: {soort}" and "ADMIN_PASSWORD" in meldingen[1]


def test_lokale_beheerder_alleen_in_demo_admin():
    assert omgeving.lokaal_admin_wachtwoord("", "demo") == "admin"
    assert omgeving.lokaal_admin_wachtwoord(None, "demo") == "admin"
    assert omgeving.lokaal_admin_wachtwoord("eigen-sterk-ww", "demo") == "eigen-sterk-ww"
    assert omgeving.lokaal_admin_wachtwoord("", "productie") == ""
    assert omgeving.lokaal_admin_wachtwoord("", "test") == ""


def test_standaardbeleid_gelijk_aan_realmexport():
    realm = json.loads((ROOT / "deploy/keycloak/realm-omnitwin.json").read_text(encoding="utf-8"))
    assert realm["passwordPolicy"] == omgeving.STANDAARD_BELEID
    # De realmexport bevat geen mensen of wachtwoorden (alleen een service account): die zet keycloak-demo
    assert all(u.get("serviceAccountClientId") and "credentials" not in u for u in realm.get("users", []))


def test_demo_accounts_en_rollen():
    assert omgeving.DEMO_ACCOUNTS == {
        "admin": ("admin", ("beheerder", "gebruikersbeheerder")),
        "gebruiker": ("gebruiker", ("lezer",)),
    }


def test_entrypoint_controleert_voor_de_init_en_zet_demo_admin():
    tekst = (ROOT / "docker-entrypoint.sh").read_text(encoding="utf-8")
    init = tekst[tekst.index('if [ "$1" = "init" ]'):]
    assert init.index("controleer_omgeving") < init.index("init_db")
    assert "python -m omnitwin.omgeving controleer" in tekst
    assert "export ADMIN_PASSWORD=admin" in tekst
    assert "python -m omnitwin.omgeving keycloak" in tekst


def test_compose_keycloak_demo_service():
    import yaml
    dienst = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))["services"]["keycloak-demo"]
    assert dienst["command"] == ["keycloak-demo"] and dienst["profiles"] == ["keycloak"]
    assert dienst["depends_on"]["keycloak"]["condition"] == "service_healthy"


# ---------------------------------------------------------------- Keycloak (nagebootst)

class Antwoord:
    def __init__(self, data=None, status=200):
        self._data, self.status_code = data, status

    def json(self):
        return self._data


class NepKeycloak:
    """Genoeg van de admin-API voor omgeving.pas_toe_in_keycloak."""

    def __init__(self, gebruikers=None, beleid=omgeving.STANDAARD_BELEID):
        self.realm = {"realm": "omnitwin", "passwordPolicy": beleid}
        self.gebruikers = {g["username"]: g for g in (gebruikers or [])}
        self.wachtwoorden, self.rollen, self.log = {}, {}, []

    def _verzoek(self, methode, pad, verwacht=None, params=None, json=None):
        self.log.append((methode, pad))
        if pad == "" and methode == "GET":
            return Antwoord(dict(self.realm))
        if pad == "" and methode == "PUT":
            self.realm.update(json)
            return Antwoord(status=204)
        if pad == "/users" and methode == "GET":
            g = self.gebruikers.get(params["username"])
            return Antwoord([g] if g else [])
        if pad == "/users" and methode == "POST":
            assert "credentials" not in json  # wachtwoord pas na het beleid, via reset-password
            self.gebruikers[json["username"]] = {**json, "id": "id-" + json["username"]}
            return Antwoord(status=201)
        gid = pad.split("/")[2]
        naam = next(n for n, g in self.gebruikers.items() if g["id"] == gid)
        if pad.endswith("/reset-password"):
            assert self.realm["passwordPolicy"] == omgeving.DEMO_BELEID
            self.wachtwoorden[naam] = json["value"]
        elif methode == "PUT":
            self.gebruikers[naam] = json
        elif methode == "DELETE":
            del self.gebruikers[naam]
        return Antwoord(status=204)

    def ken_rollen_toe(self, gid, rollen):
        naam = next(n for n, g in self.gebruikers.items() if g["id"] == gid)
        self.rollen[naam] = tuple(rollen)


def test_demo_maakt_accounts_en_versoepelt_beleid():
    kc = NepKeycloak()
    meldingen = omgeving.pas_toe_in_keycloak(kc, "demo")
    assert kc.realm["passwordPolicy"] == omgeving.DEMO_BELEID
    assert kc.wachtwoorden == {"admin": "admin", "gebruiker": "gebruiker"}
    assert kc.rollen == {"admin": ("beheerder", "gebruikersbeheerder"), "gebruiker": ("lezer",)}
    assert all(omgeving.is_demo_account(g) for g in kc.gebruikers.values())
    assert not any("admin\"" in m or "wachtwoord admin" in m for m in meldingen)


def test_demo_is_idempotent_en_herstelt():
    kc = NepKeycloak()
    omgeving.pas_toe_in_keycloak(kc, "demo")
    kc.wachtwoorden.clear()
    kc.gebruikers["admin"]["enabled"] = False
    omgeving.pas_toe_in_keycloak(kc, "demo")
    assert set(kc.gebruikers) == {"admin", "gebruiker"}
    assert kc.gebruikers["admin"]["enabled"] is True and kc.gebruikers["admin"]["firstName"] == "Demo"
    assert kc.wachtwoorden == {"admin": "admin", "gebruiker": "gebruiker"}
    assert ("POST", "/users") not in kc.log[kc.log.index(("GET", ""), 1):]


def test_demo_laat_eigen_gebruiker_admin_ongemoeid():
    eigen = {"id": "x", "username": "admin", "firstName": "Anne", "lastName": "Beheer"}
    kc = NepKeycloak([eigen])
    meldingen = omgeving.pas_toe_in_keycloak(kc, "demo")
    assert kc.gebruikers["admin"] is eigen and "admin" not in kc.wachtwoorden
    assert any("geen demo-account" in m for m in meldingen)


@pytest.mark.parametrize("soort", ["productie", "test"])
def test_buiten_demo_geen_demo_accounts(soort):
    kc = NepKeycloak()
    omgeving.pas_toe_in_keycloak(kc, "demo")
    eigen = {"id": "y", "username": "gebruiker2", "firstName": "Piet", "lastName": "Lezer"}
    kc.gebruikers["gebruiker2"] = eigen
    omgeving.pas_toe_in_keycloak(kc, soort)
    assert set(kc.gebruikers) == {"gebruiker2"}
    assert kc.realm["passwordPolicy"] == omgeving.STANDAARD_BELEID


def test_buiten_demo_eigen_beleid_blijft():
    kc = NepKeycloak(beleid="length(16)")
    omgeving.pas_toe_in_keycloak(kc, "productie")
    assert kc.realm["passwordPolicy"] == "length(16)"
    assert ("PUT", "") not in kc.log


def test_buiten_demo_eigen_admin_blijft():
    eigen = {"id": "x", "username": "admin", "firstName": "Anne", "lastName": "Beheer"}
    kc = NepKeycloak([eigen])
    omgeving.pas_toe_in_keycloak(kc, "productie")
    assert kc.gebruikers == {"admin": eigen}


# ---------------------------------------------------------------- zoals db-init het aanroept

def _controleer(**env):
    import subprocess
    import sys
    omgeving_ = {k: v for k, v in __import__("os").environ.items()
                 if k not in ("ADMIN_PASSWORD", "KEYCLOAK_ADMIN_PASSWORD", "OMNITWIN_OMGEVING", "ADMIN_USER")}
    omgeving_.update(env)
    return subprocess.run([sys.executable, "-m", "omnitwin.omgeving", "controleer"], env=omgeving_,
                          capture_output=True, text=True, timeout=60)


def test_cli_productie_weigert_admin_admin():
    r = _controleer(ADMIN_PASSWORD="admin")
    assert r.returncode == 1 and "ADMIN_PASSWORD" in r.stderr and "OMNITWIN_OMGEVING=productie" in r.stderr


def test_cli_demo_en_sterk_gaan_door():
    assert _controleer(ADMIN_PASSWORD="admin", OMNITWIN_OMGEVING="demo").returncode == 0
    assert _controleer(ADMIN_PASSWORD="a8f3c19e0b7d4e21a8f3").returncode == 0
    assert _controleer().returncode == 0

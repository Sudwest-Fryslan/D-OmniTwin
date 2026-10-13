"""OIDC/JWT-validatie (#205): zelf gemaakte sleutels en een nep-JWKS, geen netwerk."""

import base64
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from omnitwin import oidc
from omnitwin.fouten import registreer_foutafhandeling
from omnitwin.oidc import Principal, principal_optioneel, vereis_principal, vereis_rol

pytestmark = pytest.mark.unit

ISSUER = "http://localhost/auth/realms/omnitwin"
INTERN = "http://keycloak:8080/auth/realms/omnitwin"
DISCOVERY_ISSUER = "http://localhost:8080/auth/realms/omnitwin"  # Keycloak achter Traefik, intern gevraagd
JWKS_PAD = "/protocol/openid-connect/certs"


def _rsa():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


SLEUTEL_A = _rsa()
SLEUTEL_B = _rsa()
SLEUTEL_EC = ec.generate_private_key(ec.SECP256R1())


def _jwk(prive, kid, alg):
    algo = jwt.algorithms.RSAAlgorithm if alg.startswith(("RS", "PS")) else jwt.algorithms.ECAlgorithm
    d = json.loads(algo.to_jwk(prive.public_key()))
    d.update(kid=kid, use="sig", alg=alg)
    return d


class NepProvider:
    """Discovery + JWKS; telt hoe vaak de JWKS is opgehaald."""

    def __init__(self):
        self.sleutels = [_jwk(SLEUTEL_A, "a", "RS256")]
        self.opgehaald = []

    def __call__(self, url):
        self.opgehaald.append(url)
        if url.endswith("/.well-known/openid-configuration"):
            return {"issuer": DISCOVERY_ISSUER, "jwks_uri": DISCOVERY_ISSUER + JWKS_PAD}
        if url == INTERN + JWKS_PAD:
            return {"keys": list(self.sleutels)}
        raise AssertionError(f"onverwachte URL {url}")


@pytest.fixture
def provider(monkeypatch):
    for naam in ("OIDC_AUDIENCE", "OIDC_JWKS_URL"):
        monkeypatch.delenv(naam, raising=False)
    monkeypatch.setenv("OIDC_ISSUER", ISSUER)
    monkeypatch.setenv("OIDC_INTERN_URL", INTERN)
    nep = NepProvider()
    monkeypatch.setattr(oidc, "_haal_json", nep)
    oidc.wis_cache()
    yield nep
    oidc.wis_cache()


def maak_token(prive=SLEUTEL_A, kid="a", alg="RS256", **wijzig):
    nu = int(time.time())
    claims = {
        "iss": ISSUER, "aud": ["omnitwin-api", "account"], "sub": "8f1c-service-account",
        "azp": "etl-voorbeeld", "jti": "jti-1", "iat": nu, "exp": nu + 300,
        "realm_access": {"roles": ["default-roles-omnitwin"]},
        "resource_access": {"omnitwin-api": {"roles": ["dataset:voorbeeld:laden"]},
                            "account": {"roles": ["manage-account"]}},
    }
    claims.update(wijzig)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, prive, algorithm=alg, headers={"kid": kid} if kid else None)


def _app():
    app = FastAPI()
    registreer_foutafhandeling(app)

    @app.post("/datasets/{dataset_id}/leveringen")
    def lever(dataset_id: str,
              p: Principal = Depends(vereis_rol("dataset:{dataset_id}:laden", "datasets:laden"))):
        return {"client_id": p.client_id, "rollen": sorted(p.rollen), "sub": p.onderwerp, "jti": p.token_id}

    @app.post("/datasets")
    def registreer(p: Principal = Depends(vereis_rol("beheerder"))):
        return {"ok": True}

    @app.get("/optioneel")
    def optioneel(p: Principal | None = Depends(principal_optioneel)):
        return {"client_id": p.client_id if p else None}

    @app.get("/ik")
    def ik(p: Principal = Depends(vereis_principal)):
        return {"client_id": p.client_id}

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def client(provider):
    return _app()


def _kop(token):
    return {"Authorization": f"Bearer {token}"}


def _lever(client, token, dataset="voorbeeld"):
    return client.post(f"/datasets/{dataset}/leveringen", headers=_kop(token) if token else {})


def _is_probleem(r, status, code):
    assert r.status_code == status, r.text
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["status"] == status and body["code"] == code
    assert body["type"].endswith("#" + code)
    return body


# --- geldig ---------------------------------------------------------------

def test_geldig_token_met_datasetrol(client, provider):
    r = _lever(client, maak_token())
    assert r.status_code == 200, r.text
    assert r.json() == {"client_id": "etl-voorbeeld", "sub": "8f1c-service-account", "jti": "jti-1",
                        "rollen": ["dataset:voorbeeld:laden", "default-roles-omnitwin"]}
    # discovery intern, jwks_uri herschreven naar het interne adres
    assert provider.opgehaald == [INTERN + "/.well-known/openid-configuration", INTERN + JWKS_PAD]


def test_rollen_van_andere_clients_tellen_niet():
    claims = {"realm_access": {"roles": ["beheerder"]},
              "resource_access": {"account": {"roles": ["datasets:laden"]}, "omnitwin-api": {"roles": ["x"]}}}
    assert oidc._rollen(claims, "omnitwin-api") == frozenset({"beheerder", "x"})


def test_aud_als_tekst(client):
    assert _lever(client, maak_token(aud="omnitwin-api")).status_code == 200


def test_azp_ontbreekt_dan_client_id(client):
    r = client.get("/ik", headers=_kop(maak_token(azp=None, client_id="fme")))
    assert r.json() == {"client_id": "fme"}


def test_es256(client, provider):
    provider.sleutels.append(_jwk(SLEUTEL_EC, "ec", "ES256"))
    assert _lever(client, maak_token(SLEUTEL_EC, kid="ec", alg="ES256")).status_code == 200


def test_sleutels_gecachet(client, provider):
    for _ in range(3):
        assert _lever(client, maak_token()).status_code == 200
    assert provider.opgehaald.count(INTERN + JWKS_PAD) == 1


def test_jwks_url_expliciet(monkeypatch, provider):
    monkeypatch.setenv("OIDC_JWKS_URL", INTERN + JWKS_PAD)
    assert _lever(_app(), maak_token()).status_code == 200
    assert provider.opgehaald == [INTERN + JWKS_PAD]  # geen discovery


def test_zonder_intern_adres_discovery_via_issuer(monkeypatch):
    gevraagd = []

    def nep(url):
        gevraagd.append(url)
        if url.endswith("openid-configuration"):
            return {"issuer": ISSUER, "jwks_uri": ISSUER + JWKS_PAD}
        return {"keys": [_jwk(SLEUTEL_A, "a", "RS256")]}

    monkeypatch.setenv("OIDC_ISSUER", ISSUER + "/")  # slash aan het eind mag
    monkeypatch.delenv("OIDC_INTERN_URL", raising=False)
    monkeypatch.delenv("OIDC_JWKS_URL", raising=False)
    monkeypatch.setattr(oidc, "_haal_json", nep)
    oidc.wis_cache()
    assert _lever(_app(), maak_token()).status_code == 200
    assert gevraagd == [ISSUER + "/.well-known/openid-configuration", ISSUER + JWKS_PAD]
    oidc.wis_cache()


# --- ongeldig: 401 --------------------------------------------------------

@pytest.mark.parametrize("wijzig, reden", [
    ({"aud": "account"}, "aud"),
    ({"aud": None}, "aud"),
    ({"iss": "http://evil/auth/realms/omnitwin"}, "issuer"),
    ({"iss": "http://localhost:8080/auth/realms/omnitwin"}, "issuer"),  # intern adres is geen issuer
    ({"exp": int(time.time()) - 120}, "verlopen"),
    ({"exp": None}, "exp"),
    ({"nbf": int(time.time()) + 600}, "nbf"),
])
def test_ongeldige_claims(client, wijzig, reden):
    r = _lever(client, maak_token(**wijzig))
    _is_probleem(r, 401, "niet-geauthenticeerd")
    assert r.headers["www-authenticate"] == 'Bearer error="invalid_token"'


def test_klokruimte(client):
    assert _lever(client, maak_token(exp=int(time.time()) - 10)).status_code == 200


def test_verkeerde_handtekening(client):
    # kid a, maar getekend met sleutel B
    _is_probleem(_lever(client, maak_token(SLEUTEL_B, kid="a")), 401, "niet-geauthenticeerd")


def _zonder_handtekening(claims_token):
    kop = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT", "kid": "a"}).encode()).rstrip(b"=")
    deel = claims_token.split(".")[1].encode()
    return (kop + b"." + deel + b".").decode()


def test_alg_none_geweigerd(client):
    r = _lever(client, _zonder_handtekening(maak_token()))
    body = _is_probleem(r, 401, "niet-geauthenticeerd")
    assert "Algoritme" in body["detail"]


def test_hs256_geweigerd(client):
    # Klassieke aanval: HMAC met de publieke sleutel als geheim
    from cryptography.hazmat.primitives import serialization
    pem = SLEUTEL_A.public_key().public_bytes(serialization.Encoding.PEM,
                                               serialization.PublicFormat.SubjectPublicKeyInfo)
    nu = int(time.time())
    claims = {"iss": ISSUER, "aud": "omnitwin-api", "exp": nu + 300,
              "resource_access": {"omnitwin-api": {"roles": ["datasets:laden"]}}}
    kop = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "kid": "a"}).encode()).rstrip(b"=")
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=")
    import hashlib
    import hmac
    sig = base64.urlsafe_b64encode(hmac.new(pem, kop + b"." + body, hashlib.sha256).digest()).rstrip(b"=")
    token = (kop + b"." + body + b"." + sig).decode()
    _is_probleem(_lever(client, token), 401, "niet-geauthenticeerd")


def test_alg_past_niet_bij_sleutel(client, provider):
    # Sleutel a is RS256; PS256 met dezelfde sleutel wordt geweigerd omdat de JWK alg vastlegt
    _is_probleem(_lever(client, maak_token(alg="PS256")), 401, "niet-geauthenticeerd")


def test_geen_jwt(client):
    _is_probleem(_lever(client, "geen.jwt"), 401, "niet-geauthenticeerd")


def test_geen_token(client):
    r = _lever(client, None)
    _is_probleem(r, 401, "niet-geauthenticeerd")
    assert r.headers["www-authenticate"] == "Bearer"


def test_ander_schema_dan_bearer(client):
    r = client.post("/datasets/voorbeeld/leveringen", headers={"Authorization": "Basic YTpi"})
    _is_probleem(r, 401, "niet-geauthenticeerd")


# --- sleutelrotatie -------------------------------------------------------

def test_onbekende_kid_ververst_jwks(client, provider):
    assert _lever(client, maak_token()).status_code == 200
    provider.sleutels = [_jwk(SLEUTEL_B, "b", "RS256")]  # rotatie bij de provider
    oidc._sleutelbos(oidc._config())._opgehaald -= oidc.JWKS_MIN_VERVERSING  # niet net opgehaald
    assert _lever(client, maak_token(SLEUTEL_B, kid="b")).status_code == 200
    assert provider.opgehaald.count(INTERN + JWKS_PAD) == 2


def test_onbekende_kid_niet_steeds_opnieuw_ophalen(client, provider):
    assert _lever(client, maak_token()).status_code == 200
    for _ in range(5):
        _is_probleem(_lever(client, maak_token(SLEUTEL_B, kid="x")), 401, "niet-geauthenticeerd")
    assert provider.opgehaald.count(INTERN + JWKS_PAD) == 1  # binnen JWKS_MIN_VERVERSING niet opnieuw


def test_provider_onbereikbaar_503(client, monkeypatch):
    import httpx

    def weg(url):
        raise httpx.ConnectError("weg")

    monkeypatch.setattr(oidc, "_haal_json", weg)
    _is_probleem(_lever(client, maak_token()), 503, "oidc-niet-bereikbaar")


def test_provider_even_weg_bekende_sleutels_blijven(client, provider, monkeypatch):
    import httpx

    assert _lever(client, maak_token()).status_code == 200
    bos = oidc._sleutelbos(oidc._config())
    bos._opgehaald -= oidc.JWKS_TTL + 1  # cache verlopen

    def weg(url):
        raise httpx.ConnectError("weg")

    monkeypatch.setattr(oidc, "_haal_json", weg)
    assert _lever(client, maak_token()).status_code == 200


# --- rollen: 403 ----------------------------------------------------------

def test_rol_ontbreekt_403(client):
    r = client.post("/datasets", headers=_kop(maak_token()))
    body = _is_probleem(r, 403, "geen-toegang")
    assert "beheerder" in body["detail"]
    assert r.headers["www-authenticate"] == 'Bearer error="insufficient_scope"'


def test_dataset_id_ingevuld(client):
    token = maak_token()
    assert _lever(client, token, "voorbeeld").status_code == 200
    body = _is_probleem(_lever(client, token, "andere"), 403, "geen-toegang")
    assert "dataset:andere:laden" in body["detail"]


def test_rol_voor_alle_datasets(client):
    token = maak_token(resource_access={"omnitwin-api": {"roles": ["datasets:laden"]}})
    assert _lever(client, token, "wat-dan-ook").status_code == 200


def test_realm_rol_beheerder(client):
    token = maak_token(realm_access={"roles": ["beheerder"]}, resource_access=None)
    assert client.post("/datasets", headers=_kop(token)).status_code == 200


def test_client_rol_beheerder_op_andere_client_telt_niet(client):
    token = maak_token(resource_access={"account": {"roles": ["beheerder"]}})
    _is_probleem(client.post("/datasets", headers=_kop(token)), 403, "geen-toegang")


def test_vereis_rol_zonder_rollen():
    with pytest.raises(ValueError):
        vereis_rol()


# --- optioneel ------------------------------------------------------------

def test_optioneel(client):
    assert client.get("/optioneel").json() == {"client_id": None}
    assert client.get("/optioneel", headers=_kop(maak_token())).json() == {"client_id": "etl-voorbeeld"}
    _is_probleem(client.get("/optioneel", headers=_kop(maak_token(aud="x"))), 401, "niet-geauthenticeerd")


# --- OIDC uit: 503 --------------------------------------------------------

def test_oidc_uit_503(monkeypatch):
    monkeypatch.setenv("OIDC_ISSUER", "")
    c = _app()
    body = _is_probleem(_lever(c, maak_token()), 503, "oidc-niet-geconfigureerd")
    assert "OIDC niet geconfigureerd" in body["detail"]
    _is_probleem(_lever(c, None), 503, "oidc-niet-geconfigureerd")
    assert c.get("/optioneel").json() == {"client_id": None}


# --- logging --------------------------------------------------------------

def test_log_zonder_token_of_persoonsgegevens(client, caplog):
    token = maak_token(exp=int(time.time()) - 120, sub="geheim-sub", email="jan@example.nl")
    with caplog.at_level("WARNING", logger="omnitwin.oidc"):
        _lever(client, token)
        client.post("/datasets", headers=_kop(maak_token(sub="geheim-sub")))
    tekst = caplog.text
    assert "etl-voorbeeld" in tekst and "jti-1" in tekst
    assert token not in tekst and "geheim-sub" not in tekst and "jan@example.nl" not in tekst


# --- endpoint /api/oidc/ik ------------------------------------------------

def test_ik_endpoint(provider):
    from omnitwin.routers import oidc_ik

    app = FastAPI()
    registreer_foutafhandeling(app)
    app.include_router(oidc_ik.router)
    c = TestClient(app)
    r = c.get("/api/oidc/ik", headers=_kop(maak_token()))
    assert r.status_code == 200
    assert r.json() == {"client_id": "etl-voorbeeld", "rollen": ["dataset:voorbeeld:laden", "default-roles-omnitwin"]}
    assert "8f1c" not in r.text  # geen sub
    _is_probleem(c.get("/api/oidc/ik"), 401, "niet-geauthenticeerd")


# --- Microsoft Entra ID: app-rollen in de claim `roles` (#411) ------------

ENTRA_TENANT = "00000000-0000-0000-0000-000000000001"   # fictief
ENTRA_CLIENT = "00000000-0000-0000-0000-0000000000aa"   # fictief; aud van een v2-access-token
ENTRA_ISSUER = f"https://login.microsoftonline.com/{ENTRA_TENANT}/v2.0"
ENTRA_JWKS = f"https://login.microsoftonline.com/{ENTRA_TENANT}/discovery/v2.0/keys"


def entra_token(**wijzig):
    """Access token zoals Entra ID (v2) het voor de eigen API uitgeeft: geen realm_access, wel `roles`."""
    nu = int(time.time())
    claims = {
        "iss": ENTRA_ISSUER, "aud": ENTRA_CLIENT, "sub": "AAAAbbbbCCCCdddd", "oid": "fictief-oid",
        "tid": ENTRA_TENANT, "azp": ENTRA_CLIENT, "uti": "uti-1", "ver": "2.0", "scp": "toegang",
        "preferred_username": "gebruiker@example.org", "iat": nu, "nbf": nu, "exp": nu + 3600,
        "roles": ["beheerder", "datasets:laden"],
    }
    claims.update(wijzig)
    claims = {k: v for k, v in claims.items() if v is not None}
    return jwt.encode(claims, SLEUTEL_A, algorithm="RS256", headers={"kid": "entra-1", "typ": "JWT"})


@pytest.fixture
def entra(monkeypatch):
    """OIDC_* zoals in deploy/kubernetes/README.md voor Entra ID: issuer, audience, geen intern adres."""
    monkeypatch.setenv("OIDC_ISSUER", ENTRA_ISSUER)
    monkeypatch.setenv("OIDC_AUDIENCE", ENTRA_CLIENT)
    monkeypatch.setenv("OIDC_INTERN_URL", "")
    monkeypatch.delenv("OIDC_JWKS_URL", raising=False)
    gevraagd = []

    def nep(url):
        gevraagd.append(url)
        if url == ENTRA_ISSUER + "/.well-known/openid-configuration":
            return {"issuer": ENTRA_ISSUER, "jwks_uri": ENTRA_JWKS}
        if url == ENTRA_JWKS:
            # Entra zet geen alg in de JWK
            d = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(SLEUTEL_A.public_key()))
            d.update(kid="entra-1", use="sig", x5t="entra-1")
            return {"keys": [d]}
        raise AssertionError(f"onverwachte URL {url}")

    monkeypatch.setattr(oidc, "_haal_json", nep)
    oidc.wis_cache()
    yield gevraagd
    oidc.wis_cache()


def test_entra_app_rollen_uit_roles(entra):
    p = oidc.controleer_token(entra_token())
    assert p.rollen == frozenset({"beheerder", "datasets:laden"})
    assert p.client_id == ENTRA_CLIENT and p.gebruikersnaam == "gebruiker@example.org"
    assert p.token_id is None  # Entra heeft geen jti
    assert entra == [ENTRA_ISSUER + "/.well-known/openid-configuration", ENTRA_JWKS]


def test_entra_rol_geeft_toegang_tot_beheerroute(entra):
    c = _app()
    assert c.post("/datasets", headers=_kop(entra_token())).status_code == 200
    assert c.post("/datasets", headers=_kop(entra_token(roles=["lezer"]))).status_code == 403
    assert c.post("/datasets", headers=_kop(entra_token(roles=None))).status_code == 403


def test_entra_v1_token_andere_issuer_geweigerd(entra):
    """Zonder accessTokenAcceptedVersion=2 geeft Entra v1-tokens met een andere issuer: 401."""
    t = entra_token(iss=f"https://sts.windows.net/{ENTRA_TENANT}/", aud=f"api://{ENTRA_CLIENT}")
    _is_probleem(_app().post("/datasets", headers=_kop(t)), 401, "niet-geauthenticeerd")


def test_roles_naast_keycloak_claims_en_alleen_tekst():
    claims = {"roles": ["lezer", 7, None], "realm_access": {"roles": ["beheerder"]},
              "resource_access": {"omnitwin-api": {"roles": ["datasets:laden"]}}}
    assert oidc._rollen(claims, "omnitwin-api") == frozenset({"lezer", "beheerder", "datasets:laden"})
    assert oidc._rollen({"roles": "beheerder"}, "omnitwin-api") == frozenset()

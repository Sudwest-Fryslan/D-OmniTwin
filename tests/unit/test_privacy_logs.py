"""Privacy van de logs (#264): bewaartermijn, IP-inkorting en X-Forwarded-For alleen van vertrouwde proxy's."""

import re
from pathlib import Path

import pytest
from starlette.requests import Request

from omnitwin.config import STANDAARD_TRUSTED_PROXIES, instellingen
from omnitwin.grenzen import bepaal_client_ip, client_ip
from omnitwin.services import log_cleanup_service as lc

pytestmark = pytest.mark.unit

SRC = Path(__file__).resolve().parents[2] / "src" / "omnitwin"


@pytest.fixture
def omgeving(monkeypatch):
    for naam in ("LOG_BEWAAR_DAGEN", "LOG_IP_BEWAAR_DAGEN", "TRUSTED_PROXIES"):
        monkeypatch.delenv(naam, raising=False)
    return monkeypatch


# ── Instellingen ──────────────────────────────────────────────────────────────


def test_standaardwaarden(omgeving):
    inst = instellingen()
    assert inst.log_bewaar_dagen == 30
    assert inst.log_ip_bewaar_dagen == 7
    assert inst.trusted_proxies == STANDAARD_TRUSTED_PROXIES


def test_ongeldige_waarden_vallen_terug(omgeving):
    omgeving.setenv("LOG_BEWAAR_DAGEN", "0")
    omgeving.setenv("LOG_IP_BEWAAR_DAGEN", "zeven")
    inst = instellingen()
    assert inst.log_bewaar_dagen == 1  # minimaal één dag
    assert inst.log_ip_bewaar_dagen == 7


# ── IP inkorten ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "adres, verwacht",
    [
        ("203.0.113.77", "203.0.113.0"),
        ("203.0.113.0", "203.0.113.0"),  # idempotent
        ("2001:db8:abcd:12:3456::1", "2001:db8:abcd::"),  # /48
        ("2001:db8:abcd::", "2001:db8:abcd::"),
        ("::ffff:198.51.100.9", "198.51.100.0"),  # IPv4 in IPv6
        (" 192.0.2.5 ", "192.0.2.0"),
        ("1.2.3.4, 5.6.7.8", None),  # oude, ongefilterde XFF-waarde
        ("unknown", None),
        ("testclient", None),
        ("", None),
        (None, None),
    ],
)
def test_ip_inkorten(adres, verwacht):
    assert lc.ip_inkorten(adres) == verwacht


# ── Cleanup ───────────────────────────────────────────────────────────────────


class _Res:
    def __init__(self, rowcount=0, rijen=()):
        self.rowcount = rowcount
        self._rijen = list(rijen)

    def __iter__(self):
        return iter(self._rijen)


class _NepConn:
    """Legt elke query vast; de SELECT geeft de opgegeven IP-adressen terug."""

    def __init__(self, adressen=(), verwijderd=5):
        self.adressen = list(adressen)
        self.verwijderd = verwijderd
        self.queries = []
        self.commits = 0

    def execute(self, stmt, params=None):
        sql = " ".join(str(stmt).split())
        self.queries.append((sql, params or {}))
        if sql.startswith("DELETE"):
            return _Res(self.verwijderd)
        if sql.startswith("SELECT"):
            return _Res(rijen=[(a,) for a in self.adressen])
        if sql.startswith("UPDATE"):
            return _Res(2)
        raise AssertionError(sql)

    def commit(self):
        self.commits += 1


def test_cleanup_verwijdert_alle_niveaus_na_bewaartermijn(omgeving):
    conn = _NepConn()
    resultaat = lc._run_cleanup(conn)
    sql, params = conn.queries[0]
    assert sql.startswith("DELETE FROM app_logs")
    # Geen filter op niveau, behalve dat DEBUG eerder weg mag: WARNING/ERROR blijven niet permanent staan
    assert "WHERE timestamp < NOW() - make_interval(days => :dagen) OR" in sql
    assert "level = 'DEBUG'" in sql
    assert params == {"dagen": 30, "debug_dagen": 7}
    assert resultaat["verwijderd"] == 5
    assert conn.commits >= 1


def test_cleanup_kort_oude_ip_adressen_in(omgeving):
    conn = _NepConn(adressen=["203.0.113.77", "203.0.113.0", "2001:db8:abcd:12::1", "1.2.3.4, 5.6.7.8"])
    resultaat = lc._run_cleanup(conn)
    select = [q for q in conn.queries if q[0].startswith("SELECT")]
    assert select and select[0][1] == {"ip_dagen": 7}
    updates = [p for s, p in conn.queries if s.startswith("UPDATE")]
    assert updates == [
        {"nieuw": "203.0.113.0", "oud": "203.0.113.77", "ip_dagen": 7},
        {"nieuw": "2001:db8:abcd::", "oud": "2001:db8:abcd:12::1", "ip_dagen": 7},
        {"nieuw": None, "oud": "1.2.3.4, 5.6.7.8", "ip_dagen": 7},  # onleesbaar → leeg
    ]
    assert resultaat["ip_ingekort"] == 6  # 3 updates × 2 rijen (nep)


def test_cleanup_instelbaar(omgeving):
    omgeving.setenv("LOG_BEWAAR_DAGEN", "3")
    omgeving.setenv("LOG_IP_BEWAAR_DAGEN", "1")
    conn = _NepConn(adressen=["192.0.2.5"])
    lc._run_cleanup(conn)
    assert conn.queries[0][1] == {"dagen": 3, "debug_dagen": 3}
    assert conn.queries[1][1] == {"ip_dagen": 1}


def test_cleanup_zonder_inkorten_als_ip_termijn_niet_korter_is(omgeving):
    omgeving.setenv("LOG_BEWAAR_DAGEN", "7")
    omgeving.setenv("LOG_IP_BEWAAR_DAGEN", "7")
    conn = _NepConn(adressen=["192.0.2.5"])
    assert lc._run_cleanup(conn) == {"verwijderd": 5, "ip_ingekort": 0}
    assert len(conn.queries) == 1


def test_run_cleanup_is_synchroon():
    # Eerder `async def`, aangeroepen via asyncio.to_thread: de query liep nooit (#264)
    import inspect

    assert not inspect.iscoroutinefunction(lc._run_cleanup)


# ── X-Forwarded-For ───────────────────────────────────────────────────────────

T = STANDAARD_TRUSTED_PROXIES


@pytest.mark.parametrize(
    "peer, xff, trusted, verwacht",
    [
        # Onvertrouwde peer: header negeren, ook als hij er "vertrouwd" uitziet
        ("8.8.8.8", ["10.9.9.9"], T, "8.8.8.8"),
        ("8.8.8.8", ["1.2.3.4"], T, "8.8.8.8"),
        # Traefik (Docker-netwerk) zet het echte adres achteraan
        ("172.18.0.3", ["198.51.100.7"], T, "198.51.100.7"),
        # Client stuurt zelf een vals adres mee: het meest rechtse onvertrouwde adres telt
        ("172.18.0.3", ["1.2.3.4, 198.51.100.7"], T, "198.51.100.7"),
        # Keten van vertrouwde proxy's: vertrouwde hops rechts overslaan
        ("172.18.0.3", ["198.51.100.7, 10.0.0.5, 192.168.1.1"], T, "198.51.100.7"),
        # Meerdere headers tellen als één lijst
        ("172.18.0.3", ["203.0.113.1", "198.51.100.7"], T, "198.51.100.7"),
        # Geen header of lege header: de peer
        ("172.18.0.3", [], T, "172.18.0.3"),
        ("172.18.0.3", [" , "], T, "172.18.0.3"),
        # Onzin in de keten: niet raden, de peer
        ("172.18.0.3", ["1.2.3.4, unknown"], T, "172.18.0.3"),
        ("172.18.0.3", ["198.51.100.7:4321"], T, "172.18.0.3"),
        # Alleen vertrouwde adressen: het verste (bijv. een interne client)
        ("172.18.0.3", ["10.1.2.3"], T, "10.1.2.3"),
        # TRUSTED_PROXIES leeg: nooit vertrouwen
        ("172.18.0.3", ["198.51.100.7"], "", "172.18.0.3"),
        # Precies ingesteld: alleen dat adres
        ("172.18.0.3", ["198.51.100.7"], "172.18.0.2", "172.18.0.3"),
        ("172.18.0.2", ["198.51.100.7"], "172.18.0.2, ongeldig", "198.51.100.7"),
        # IPv6 en IPv4-in-IPv6
        ("::1", ["2001:db8::5"], T, "2001:db8::5"),
        ("::ffff:172.18.0.3", ["198.51.100.7"], T, "198.51.100.7"),
        ("2001:db8::9", ["198.51.100.7"], T, "2001:db8::9"),
        # Peer zonder IP (TestClient)
        ("testclient", ["198.51.100.7"], T, "testclient"),
    ],
)
def test_bepaal_client_ip(peer, xff, trusted, verwacht):
    assert bepaal_client_ip(peer, xff, trusted) == verwacht


def _verzoek(client, headers=()):
    return Request(
        {
            "type": "http",
            "scheme": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers],
            "server": ("testserver", 80),
            "client": (client, 1234) if client else None,
        }
    )


def test_client_ip_leest_trusted_proxies(omgeving):
    verzoek = _verzoek("172.18.0.3", [("X-Forwarded-For", "198.51.100.7")])
    assert client_ip(verzoek) == "198.51.100.7"
    omgeving.setenv("TRUSTED_PROXIES", "")
    assert client_ip(verzoek) == "172.18.0.3"
    assert client_ip(_verzoek(None)) == "onbekend"


def test_alleen_grenzen_leest_x_forwarded_for():
    """Rate limiting, login en de logmiddleware gebruiken allemaal client_ip."""
    patroon = re.compile(r"""headers\.(?:get|getlist)\(\s*['"]x-forwarded-for""", re.IGNORECASE)
    lezers = sorted(
        p.relative_to(SRC).as_posix() for p in SRC.rglob("*.py") if patroon.search(p.read_text(encoding="utf-8"))
    )
    assert lezers == ["grenzen.py"]
    main = (SRC / "main.py").read_text(encoding="utf-8")
    assert main.count("client_ip(request)") == 2
    assert "request.client" not in main
    auth = (SRC / "routers" / "auth.py").read_text(encoding="utf-8")
    assert "client_ip(request)" in auth and "request.client" not in auth


def test_rate_limiting_en_logging_gebruiken_dezelfde_functie(omgeving):
    from omnitwin import grenzen
    from omnitwin.routers import auth

    assert auth.client_ip is grenzen.client_ip
    # beperk_llm roept de module-functie aan: een vervalste header van buiten telt niet
    omgeving.setenv("LLM_RATE_LIMIT", "1")
    grenzen._llm_limieten.clear()
    grenzen.beperk_llm(_verzoek("8.8.8.8", [("X-Forwarded-For", "1.1.1.1")]))
    with pytest.raises(Exception) as fout:
        grenzen.beperk_llm(_verzoek("8.8.8.8", [("X-Forwarded-For", "2.2.2.2")]))
    assert getattr(fout.value, "status_code", None) == 429
    grenzen._llm_limieten.clear()


def test_ip_niet_in_logtekst_bij_geblokkeerde_login():
    auth = (SRC / "routers" / "auth.py").read_text(encoding="utf-8")
    assert "vanaf {ip}" not in auth


# ── Containerlogs ─────────────────────────────────────────────────────────────


def test_containerlogs_begrensd():
    yaml = pytest.importorskip("yaml")  # komt mee met uvicorn[standard]
    compose = yaml.safe_load((SRC.parents[1] / "docker-compose.yml").read_text(encoding="utf-8"))
    for naam, service in compose["services"].items():
        logging = service.get("logging") or {}
        assert logging.get("driver") == "json-file", naam
        assert logging.get("options") == {"max-size": "10m", "max-file": "3"}, naam

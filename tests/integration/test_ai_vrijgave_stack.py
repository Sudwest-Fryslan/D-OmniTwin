"""
AI-vrijgave (#307) en AI-logboek (#313) tegen een draaiende stack.

- standaard dicht (verse installatie: usecase B heeft geen verklaring);
- upload (alleen PDF) opent een usecase, noodstop zet hem dicht, hervatten opent weer, na geldig_tot dicht;
- de verklaring is publiek op te halen als PDF; de publieke status bevat geen logins;
- een chatvraag met A dicht komt als 'geweigerd' in het logboek, zonder gebruikersgegevens;
- het logboek is alleen-toevoegen (rol omnitwin_ai_log: geen UPDATE/DELETE; trigger: ook niet als
  eigenaar), de hashketen klopt en de database rekent dezelfde hash als omnitwin.ai_logboek.

Nodig: ADMIN_API_KEY en DATABASE_* (zoals in de CI, --env-file .env). Laat usecase A na afloop
stilgezet achter; C laat de CI-stap 'Geef AI-usecase C vrij' open.
"""
import datetime as dt
import os

import pytest
import requests

from omnitwin import ai_logboek

pytestmark = pytest.mark.integration

BASE_URL = os.environ.get("OMNITWIN_BASE_URL", "http://localhost").rstrip("/")
TIMEOUT = 60
PDF = b"%PDF-1.4\n%integratietest D-OmniTwin\n%%EOF\n"


@pytest.fixture(scope="module")
def beheer():
    key = os.environ.get("ADMIN_API_KEY", "")
    if len(key) < 32:
        pytest.skip("geen geldige ADMIN_API_KEY in de testomgeving")
    s = requests.Session()
    s.headers["X-Admin-Key"] = key
    return s


@pytest.fixture(scope="module")
def db():
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(
        host=os.environ.get("DATABASE_HOST", "localhost"),
        port=int(os.environ.get("DATABASE_PORT", 5432)),
        dbname=os.environ.get("DATABASE_NAME", "omnitwin_db"),
        user=os.environ.get("DATABASE_USER", "omnitwin_user"),
        password=os.environ.get("DATABASE_PASSWORD", ""),
    )
    conn.autocommit = True
    yield conn
    conn.close()


def status(code):
    r = requests.get(f"{BASE_URL}/api/ai/usecases", timeout=TIMEOUT)
    assert r.status_code == 200, r.text[:300]
    return {s["code"]: s for s in r.json()}[code]


def upload(beheer, code, inhoud=PDF, ctype="application/pdf", geldig_tot=None):
    geldig_tot = geldig_tot or (dt.date.today() + dt.timedelta(days=7)).isoformat()
    return beheer.post(f"{BASE_URL}/api/admin/ai/usecases/{code}/verklaring", timeout=TIMEOUT,
                       files={"bestand": ("verklaring.pdf", inhoud, ctype)},
                       data={"versie": "integratietest", "geldig_tot": geldig_tot})


def test_publieke_status_zonder_logins():
    r = requests.get(f"{BASE_URL}/api/ai/usecases", timeout=TIMEOUT)
    assert r.status_code == 200
    assert [s["code"] for s in r.json()] == ["A", "B", "C"]
    for s in r.json():
        assert not {"geupload_door", "status_door"} & set(s)


def test_verse_installatie_b_dicht():
    b = status("B")
    if b["versie"] is not None:
        pytest.skip("B heeft al een verklaring (geen verse stack)")
    assert (b["open"], b["reden"], b["verklaring_url"]) == (False, "geen_verklaring", None)
    assert requests.get(f"{BASE_URL}/api/ai/usecases/B/verklaring", timeout=TIMEOUT).status_code == 404


def test_beheer_vereist_beheerder():
    assert requests.get(f"{BASE_URL}/api/admin/ai/usecases", timeout=TIMEOUT).status_code == 401
    r = requests.post(f"{BASE_URL}/api/admin/ai/usecases/A/noodstop", timeout=TIMEOUT)
    assert r.status_code == 401


@pytest.mark.parametrize("inhoud, ctype", [(PDF, "text/plain"), (b"GIF89a", "application/pdf")])
def test_alleen_pdf(beheer, inhoud, ctype):
    assert upload(beheer, "A", inhoud, ctype).status_code == 422


def test_geldig_tot_in_het_verleden_geweigerd(beheer):
    assert upload(beheer, "A", geldig_tot="2020-01-01").status_code == 422


def test_levenscyclus_a(beheer, db):
    r = upload(beheer, "A")
    assert r.status_code == 200, r.text[:300]
    a = status("A")
    assert a["open"] and a["versie"] == "integratietest"
    pdf = requests.get(f"{BASE_URL}{a['verklaring_url']}", timeout=TIMEOUT)
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf"
    assert pdf.content == PDF

    beheerlijst = {s["code"]: s for s in beheer.get(f"{BASE_URL}/api/admin/ai/usecases", timeout=TIMEOUT).json()}
    assert beheerlijst["A"]["geupload_door"] == "API_SCRIPT" and beheerlijst["A"]["geupload_op"]

    assert beheer.post(f"{BASE_URL}/api/admin/ai/usecases/A/noodstop", timeout=TIMEOUT).status_code == 200
    assert (status("A")["open"], status("A")["reden"]) == (False, "stilgezet")
    assert beheer.post(f"{BASE_URL}/api/admin/ai/usecases/A/hervatten", timeout=TIMEOUT).status_code == 200
    assert status("A")["open"]

    # Na geldig_tot dicht (de datum terugzetten kan alleen in de database)
    with db.cursor() as cur:
        cur.execute("UPDATE ai_verklaringen SET geldig_tot = current_date - 1 WHERE id = %s",
                    (r.json()["verklaring_id"],))
    assert (status("A")["open"], status("A")["reden"]) == (False, "verlopen")
    beheer.get(f"{BASE_URL}/api/admin/ai/usecases", timeout=TIMEOUT)
    log = beheer.get(f"{BASE_URL}/api/admin/ai/vrijgavelog", timeout=TIMEOUT).json()
    acties = [regel["actie"] for regel in log if regel["usecase"] == "A"]
    assert {"verklaring_geupload", "noodstop", "hervat", "verlopen"} <= set(acties)

    # Opruimen: A blijft dicht voor de rest van de tests
    upload(beheer, "A")
    beheer.post(f"{BASE_URL}/api/admin/ai/usecases/A/noodstop", timeout=TIMEOUT)
    assert not status("A")["open"]


def test_chat_met_a_dicht_wordt_gelogd_als_geweigerd(beheer):
    assert not status("A")["open"]
    vraag = "toon de energielabels op de kaart (integratietest 313)"
    r = requests.post(f"{BASE_URL}/api/chat", json={"vraag": vraag}, timeout=300)
    assert r.status_code == 200, r.text[:300]
    assert "AI-assistent staat uit" in (r.json().get("melding") or "")
    log = beheer.get(f"{BASE_URL}/api/admin/ai/logboek", params={"usecase": "A", "status": "geweigerd"},
                     timeout=TIMEOUT).json()
    regel = next(x for x in log["regels"] if x["taak"] == vraag)
    assert regel["app_versie"] and regel["hash"]
    assert not {"user_id", "gebruiker", "ip_address", "sessie"} & set(regel)
    csv = beheer.get(f"{BASE_URL}/api/admin/ai/logboek/export", params={"usecase": "A"}, timeout=TIMEOUT)
    assert csv.status_code == 200 and vraag in csv.text


def test_hashketen_klopt_en_python_rekent_hetzelfde(beheer, db):
    controle = beheer.get(f"{BASE_URL}/api/admin/ai/logboek/controle", timeout=TIMEOUT).json()
    assert controle["ok"], controle
    assert controle["aantal"] >= 1
    with db.cursor() as cur:
        cur.execute("SELECT id, to_char(tijdstip AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS.US\"Z\"'), usecase, "
                    "functie, status, taak, bronnen, model, modelversie, app_versie, resultaat, foutmelding, "
                    "vorige_hash, hash FROM ai_logboek ORDER BY id DESC LIMIT 5")
        kolommen = [d[0] for d in cur.description]
        for rij in cur.fetchall():
            r = dict(zip(kolommen, rij))
            r["tijdstip_utc"] = r.pop("to_char")
            assert ai_logboek.regelhash(r) == r["hash"]


def _fout(db, sql, rol=None):
    psycopg2 = pytest.importorskip("psycopg2")
    with db.cursor() as cur:
        try:
            cur.execute("BEGIN")
            if rol:
                cur.execute(f"SET LOCAL ROLE {rol}")
            with pytest.raises(psycopg2.Error) as fout:
                cur.execute(sql)
            return fout.value.pgcode
        finally:
            cur.execute("ROLLBACK")


@pytest.mark.parametrize("sql", ["UPDATE ai_logboek SET resultaat = 'x'", "DELETE FROM ai_logboek",
                                 "TRUNCATE ai_logboek"])
def test_logboek_alleen_toevoegen(db, sql):
    assert _fout(db, sql, rol="omnitwin_ai_log") == "42501"   # rol: geen recht
    assert _fout(db, sql) == "42501"                           # eigenaar/superuser: de trigger


def test_schrijfrol_mag_toevoegen_en_opschonen_aanroepen(db):
    with db.cursor() as cur:
        cur.execute("BEGIN")
        cur.execute("SET LOCAL ROLE omnitwin_ai_log")
        cur.execute("INSERT INTO ai_logboek (usecase, functie, status, taak) "
                    "VALUES ('C', 'integratietest', 'geweigerd', 'test') RETURNING id, hash")
        id_, hash_ = cur.fetchone()
        assert id_ and len(hash_) == 64
        cur.execute("SELECT ai_logboek_opschonen('test')")
        assert cur.fetchone()[0] == 0  # niets ouder dan de bewaartermijn
        cur.execute("ROLLBACK")

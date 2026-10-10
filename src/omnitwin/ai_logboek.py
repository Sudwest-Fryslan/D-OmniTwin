"""
AI-logboek (#313): elke AI-actie van usecase A, B en C, ook een geweigerde (usecase dicht).

Per actie: usecase, functie, tijdstip, vraag of taak (afgekapt), gebruikte bronnen (indicator- of
document-id's), model en modelversie, applicatieversie, resultaat of foutmelding, en de status
(uitgevoerd, geweigerd, fout). Nooit per gebruiker: geen gebruikers-id, sessie of IP-adres.

Opslag: tabel `ai_logboek` (migratie V039), alleen toevoegen. De backend schrijft als databaserol
`omnitwin_ai_log` (alleen SELECT en INSERT); een trigger zet volgnummer, tijdstip en de hash
(sha256 van de inhoud plus de hash van de vorige regel). `controleer_keten` rekent die keten na.
Opschonen na de bewaartermijn (`ai_instellingen`, standaard 365 dagen) kan alleen via de functie
`ai_logboek_opschonen()` (SECURITY DEFINER, rol `omnitwin_ai_log_opschoner`); dat komt zelf in het logboek.
"""
from __future__ import annotations

import csv
import hashlib
import io
import logging
from datetime import date
from typing import Any, Dict, Iterable, List, Optional, Sequence

from sqlalchemy import text

from omnitwin.version import __version__

logger = logging.getLogger(__name__)

UITGEVOERD, GEWEIGERD, FOUT, OPGESCHOOND = "uitgevoerd", "geweigerd", "fout", "opgeschoond"
STATUSSEN = (UITGEVOERD, GEWEIGERD, FOUT, OPGESCHOOND)
SCHRIJFROL = "omnitwin_ai_log"

MAX_TAAK = 500
MAX_RESULTAAT = 2000
MAX_FOUT = 500
MAX_BRONNEN = 50

STANDAARD_BEWAARTERMIJN = 365
MIN_BEWAARTERMIJN, MAX_BEWAARTERMIJN = 30, 3650

# Velden in de volgorde van de hash (zelfde als public.ai_logboek_regelhash in V039)
HASHVELDEN = ("id", "tijdstip_utc", "usecase", "functie", "status", "taak", "bronnen", "model",
              "modelversie", "app_versie", "resultaat", "foutmelding", "vorige_hash")
SCHEIDER = "\x1f"


def afkappen(tekst: Optional[str], maximum: int) -> Optional[str]:
    if tekst is None:
        return None
    tekst = str(tekst).strip()
    return tekst if len(tekst) <= maximum else tekst[: maximum - 1] + "…"


def _bronnen(bronnen: Optional[Iterable[Any]]) -> List[str]:
    uit: List[str] = []
    for b in bronnen or ():
        s = str(b).strip() if b is not None else ""
        if s and s not in uit:
            uit.append(s.replace(",", " ")[:100])
        if len(uit) >= MAX_BRONNEN:
            break
    return uit


def regel(usecase: str, functie: str, status: str, *, taak: Optional[str] = None,
          bronnen: Optional[Iterable[Any]] = None, model: Optional[str] = None,
          modelversie: Optional[str] = None, resultaat: Optional[str] = None,
          foutmelding: Optional[str] = None) -> Dict[str, Any]:
    """De rij zoals hij in het logboek komt (zonder id, tijdstip en hash: die zet de database)."""
    if status not in STATUSSEN:
        raise ValueError(f"onbekende status {status!r}")
    return {
        "usecase": usecase, "functie": afkappen(functie, 100) or "onbekend", "status": status,
        "taak": afkappen(taak, MAX_TAAK), "bronnen": _bronnen(bronnen),
        "model": afkappen(model, 200), "modelversie": afkappen(modelversie, 200),
        "app_versie": __version__, "resultaat": afkappen(resultaat, MAX_RESULTAAT),
        "foutmelding": afkappen(foutmelding, MAX_FOUT),
    }


_INSERT = text("""
    INSERT INTO public.ai_logboek (usecase, functie, status, taak, bronnen, model, modelversie,
                                   app_versie, resultaat, foutmelding)
    VALUES (:usecase, :functie, :status, :taak, CAST(:bronnen AS text[]), :model, :modelversie,
            :app_versie, :resultaat, :foutmelding)
""")


def _schrijf_rij(rij: Dict[str, Any]) -> None:
    """Eigen transactie (los van het verzoek), als de schrijfrol: alleen INSERT."""
    from omnitwin.database import engine
    with engine.begin() as conn:
        conn.execute(text(f"SET LOCAL ROLE {SCHRIJFROL}"))
        conn.execute(_INSERT, rij)


def schrijf(usecase: str, functie: str, status: str, **velden) -> None:
    """Eén AI-actie in het logboek. Een fout bij het schrijven breekt de actie niet af (wel in de serverlog)."""
    try:
        _schrijf_rij(regel(usecase, functie, status, **velden))
    except Exception as e:  # noqa: BLE001 - logboek mag de gebruiker niet blokkeren
        logger.error("AI-logboek: schrijven mislukt (%s, %s, %s): %s", usecase, functie, status, type(e).__name__)


# ── Hashketen ────────────────────────────────────────────────────────────────

def regelhash(r: Dict[str, Any]) -> str:
    """sha256 van de regel (velden in HASHVELDEN, bronnen met komma's), zoals ai_logboek_regelhash."""
    delen = []
    for veld in HASHVELDEN:
        w = r.get(veld)
        if veld == "bronnen":
            w = ",".join(w or [])
        delen.append("" if w is None else str(w))
    return hashlib.sha256(SCHEIDER.join(delen).encode("utf-8")).hexdigest()


def controleer_keten(regels: Iterable[Dict[str, Any]], max_fouten: int = 20) -> Dict[str, Any]:
    """
    Rekent de keten na (regels op volgorde van id). Per regel: klopt de hash bij de inhoud, en
    verwijst vorige_hash naar de regel ervoor? De eerste regel is het anker (na opschonen wijst
    die naar een verwijderde regel).
    """
    aantal, fouten = 0, []
    eerste = laatste = vorige = None
    for r in regels:
        aantal += 1
        if eerste is None:
            eerste = r["id"]
        elif r.get("vorige_hash") != vorige:
            fouten.append({"id": r["id"], "reden": "vorige_hash past niet bij de regel ervoor"})
        if regelhash(r) != r.get("hash"):
            fouten.append({"id": r["id"], "reden": "hash past niet bij de inhoud"})
        vorige, laatste = r.get("hash"), r["id"]
        if len(fouten) >= max_fouten:
            break
    return {"ok": not fouten, "aantal": aantal, "eerste_id": eerste, "laatste_id": laatste, "fouten": fouten}


_KOLOMMEN = """id, tijdstip, to_char(tijdstip AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"') AS tijdstip_utc,
               usecase, functie, status, taak, bronnen, model, modelversie, app_versie, resultaat,
               foutmelding, vorige_hash, hash"""


def controleer(db) -> Dict[str, Any]:
    rijen = db.execute(text(f"SELECT {_KOLOMMEN} FROM public.ai_logboek ORDER BY id")).mappings()
    return controleer_keten(dict(r) for r in rijen)


# ── Inzien, exporteren, opschonen ────────────────────────────────────────────

def lees(db, usecase: Optional[str] = None, status: Optional[str] = None, van: Optional[date] = None,
         tot: Optional[date] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    voorwaarden, params = [], {"limit": limit, "offset": offset}
    if usecase:
        voorwaarden.append("usecase = :usecase")
        params["usecase"] = usecase
    if status:
        voorwaarden.append("status = :status")
        params["status"] = status
    if van:
        voorwaarden.append("tijdstip >= CAST(:van AS date)")
        params["van"] = van
    if tot:
        voorwaarden.append("tijdstip < CAST(:tot AS date) + 1")
        params["tot"] = tot
    waar = ("WHERE " + " AND ".join(voorwaarden)) if voorwaarden else ""
    totaal = db.execute(text(f"SELECT count(*) FROM public.ai_logboek {waar}"), params).scalar()
    rijen = db.execute(text(f"SELECT {_KOLOMMEN} FROM public.ai_logboek {waar} "
                            "ORDER BY id DESC LIMIT :limit OFFSET :offset"), params).mappings()
    return {"totaal": int(totaal or 0), "regels": [dict(r) for r in rijen]}


CSV_VELDEN = ("id", "tijdstip_utc", "usecase", "functie", "status", "taak", "bronnen", "model", "modelversie",
              "app_versie", "resultaat", "foutmelding", "vorige_hash", "hash")


def _csv_veilig(w: Any) -> str:
    """Geen formules in een spreadsheet (=, +, -, @ aan het begin)."""
    s = "" if w is None else (";".join(w) if isinstance(w, (list, tuple)) else str(w))
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def als_csv(regels: Sequence[Dict[str, Any]]) -> str:
    buf = io.StringIO()
    schrijver = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    schrijver.writerow(CSV_VELDEN)
    for r in regels:
        schrijver.writerow([_csv_veilig(r.get(v)) for v in CSV_VELDEN])
    return buf.getvalue()


def opschonen() -> int:
    """Verwijdert regels ouder dan de bewaartermijn, via de functie van de opschoonrol; geeft het aantal."""
    from omnitwin.database import engine
    with engine.begin() as conn:
        conn.execute(text(f"SET LOCAL ROLE {SCHRIJFROL}"))
        return int(conn.execute(text("SELECT public.ai_logboek_opschonen(:versie)"),
                                {"versie": __version__}).scalar() or 0)


def lees_bewaartermijn(db) -> Dict[str, Any]:
    r = db.execute(text("SELECT bewaartermijn_dagen, gewijzigd_door, gewijzigd_op FROM public.ai_instellingen "
                        "WHERE id")).mappings().fetchone()
    if not r:
        return {"bewaartermijn_dagen": STANDAARD_BEWAARTERMIJN, "gewijzigd_door": None, "gewijzigd_op": None}
    return dict(r)


def zet_bewaartermijn(db, dagen: int, door: str) -> None:
    db.execute(text("""
        INSERT INTO public.ai_instellingen (id, bewaartermijn_dagen, gewijzigd_door, gewijzigd_op)
        VALUES (true, :d, :door, now())
        ON CONFLICT (id) DO UPDATE SET bewaartermijn_dagen = EXCLUDED.bewaartermijn_dagen,
            gewijzigd_door = EXCLUDED.gewijzigd_door, gewijzigd_op = EXCLUDED.gewijzigd_op
    """), {"d": int(dagen), "door": door})
    db.execute(text("INSERT INTO public.ai_vrijgave_log (actie, door, toelichting) "
                    "VALUES ('bewaartermijn', :door, :t)"),
               {"door": door, "t": f"Bewaartermijn AI-logboek: {int(dagen)} dagen"})
    db.commit()

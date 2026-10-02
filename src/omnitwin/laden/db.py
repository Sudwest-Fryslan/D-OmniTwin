"""
Databasetoegang van de laad-API
===============================
Elke transactie draait als rol `laden_schrijver` (`SET LOCAL ROLE`, migratie V024): de
laadstraat kan alleen bij schema `laden` en de doeltabellen, niet bij users, sessies of
configuratie. De engine (en dus de verbinding) is die van de backend.

`statement_timeout` is in de backend 60 s per query (main.py); de laadstraat zet hem per
transactie op `LAAD_TIMEOUT_MS`, omdat één publicatie van ±200.000 regels langer mag duren.
"""

from __future__ import annotations

from contextlib import contextmanager

LADEN_ROL = "laden_schrijver"
LAAD_TIMEOUT_MS = 15 * 60 * 1000


@contextmanager
def transactie(timeout_ms: int | None = None, dict_cursor: bool = True):
    """psycopg2-cursor in één transactie als laden_schrijver; commit bij succes, anders rollback."""
    import psycopg2.extras

    from omnitwin.database import engine

    conn = engine.raw_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) if dict_cursor else conn.cursor()
        cur.execute(f"SET LOCAL ROLE {LADEN_ROL}")
        if timeout_ms:
            cur.execute("SELECT set_config('statement_timeout', %s, true)", (str(int(timeout_ms)),))
        yield cur
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def slot_dataset(cur, dataset_id: str) -> None:
    """Leveringen op één dataset na elkaar (ook over meerdere backend-processen)."""
    cur.execute("SELECT pg_advisory_xact_lock(hashtext('laden:dataset:' || %s))", (dataset_id,))


def slot_waarnemingen(cur) -> None:
    """Publicaties naar gebied_data na elkaar: twee datasets kunnen dezelfde sleutel raken (voorrang)."""
    cur.execute("SELECT pg_advisory_xact_lock(hashtext('laden:gebied_data'))")

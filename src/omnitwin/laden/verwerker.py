"""
Achtergrondverwerking van leveringen
====================================
Eenvoudig en zonder extra infrastructuur: een threadpool in het backend-proces. Een nieuwe
levering wordt na het opslaan aangeboden (`bied_aan`); bij het starten pakt de verwerker
leveringen op die nog op `ontvangen` staan (bijv. na een herstart), en zet leveringen die
langer dan `VASTGELOPEN_MINUTEN` op `bezig` staan op `mislukt` (opnieuw leveren mag).

Meerdere backend-processen: een levering wordt geclaimd met een UPDATE ... WHERE status =
'ontvangen' (één proces wint) en per dataset na elkaar gepubliceerd (advisory lock).

Schaalbaarheid (vervolg): bij grote of veel leveringen een aparte worker-container met een
wachtrij (bijv. PostgreSQL LISTEN/NOTIFY of een taakqueue), zodat de API-processen vrij blijven.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("omnitwin.laden.verwerker")

WORKERS = 2
VASTGELOPEN_MINUTEN = 60

_pool: ThreadPoolExecutor | None = None
_slot = threading.Lock()


def _pool_() -> ThreadPoolExecutor:
    global _pool
    with _slot:
        if _pool is None:
            _pool = ThreadPoolExecutor(max_workers=WORKERS, thread_name_prefix="laden")
        return _pool


def _verwerk(levering_id: str) -> None:
    from omnitwin.laden.laadstraat import verwerk

    try:
        status = verwerk(levering_id)
        logger.info("Levering %s: %s", levering_id, status or "door een ander proces verwerkt")
    except Exception:  # verwerk vangt alles; dit is het vangnet van de thread
        logger.exception("Levering %s: onverwachte fout in de verwerker", levering_id)


def bied_aan(levering_id: str) -> None:
    _pool_().submit(_verwerk, str(levering_id))


def start() -> None:
    """Bij het starten van de backend: openstaande leveringen oppakken."""
    from omnitwin.laden.db import transactie

    try:
        with transactie() as cur:
            cur.execute(
                """UPDATE laden.leveringen SET status = 'mislukt', klaar_op = now(),
                                  aantallen = aantallen || '{"vastgelopen": true}'::jsonb
                           WHERE status = 'bezig' AND gestart_op < now() - make_interval(mins => %s)""",
                (VASTGELOPEN_MINUTEN,),
            )
            cur.execute("SELECT id::text AS id FROM laden.leveringen WHERE status = 'ontvangen' ORDER BY ontvangen_op")
            open_ = [r["id"] for r in cur.fetchall()]
    except Exception as e:  # schema laden ontbreekt (migratie nog niet gedraaid): laad-API werkt dan niet
        logger.warning("Laad-API: openstaande leveringen niet opgepakt (%s)", type(e).__name__)
        return
    for lid in open_:
        bied_aan(lid)
    if open_:
        logger.info("Laad-API: %d openstaande leveringen opgepakt", len(open_))


def stop() -> None:
    global _pool
    with _slot:
        if _pool is not None:
            _pool.shutdown(wait=False, cancel_futures=False)
            _pool = None

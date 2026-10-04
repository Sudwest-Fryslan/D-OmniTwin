"""
Log Cleanup Service — Sprint 17C, bewaartermijn en IP-inkorting (#264)
=======================================================================
Dagelijkse achtergrondtaak die verouderde logs verwijdert en IP-adressen inkort.
Draait als asyncio-loop in de FastAPI levenscyclus — geen extra dependency.

Bewaarbeleid (instelbaar, zie omnitwin.config):
    Alle niveaus                → verwijderd na LOG_BEWAAR_DAGEN (standaard 30)
    DEBUG                       → na hoogstens 7 dagen
    ip_address ouder dan LOG_IP_BEWAAR_DAGEN (standaard 7) → ingekort:
        IPv4 → laatste octet 0 (/24), IPv6 → /48, onleesbaar → leeg

Tot #264 bleven WARNING/ERROR/CRITICAL permanent staan; daar zitten elk 4xx-verzoek
en elke geblokkeerde login in, met IP-adres en gebruikersnaam.

Scheduling:
    Elke 24 uur, met jitter (±30 min) om piekbelasting te vermijden.
    Eerste run: 5 minuten na server-start (een server die vaker dan eens per dag
    herstart, ruimt anders nooit op), daarna elke 24 uur.
"""

import asyncio
import ipaddress
import random
import logging
from typing import Optional

from sqlalchemy import text

from omnitwin.config import instellingen
from omnitwin.database import engine

logger = logging.getLogger(__name__)

DEBUG_BEWAAR_DAGEN = 7  # DEBUG nooit langer dan dit (of korter, als LOG_BEWAAR_DAGEN kleiner is)

# Interval in seconden (24 uur + jitter)
_EERSTE_RUN_S = 5 * 60
_BASE_INTERVAL_S = 24 * 3600
_JITTER_S = 30 * 60  # ±30 minuten

_cleanup_task: asyncio.Task | None = None


def ip_inkorten(adres: Optional[str]) -> Optional[str]:
    """IPv4 → laatste octet 0, IPv6 → /48 (rest nullen). Onleesbaar → None (leeg).

    Idempotent: een ingekort adres blijft gelijk.
    """
    if adres is None:
        return None
    try:
        ip = ipaddress.ip_address(adres.strip())
    except ValueError:
        return None
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    prefix = 24 if ip.version == 4 else 48
    return str(ipaddress.ip_network(f"{ip}/{prefix}", strict=False).network_address)


_VERWIJDER_SQL = text("""
    DELETE FROM app_logs
    WHERE timestamp < NOW() - make_interval(days => :dagen)
       OR (level = 'DEBUG' AND timestamp < NOW() - make_interval(days => :debug_dagen))
""")

_IP_SELECT_SQL = text("""
    SELECT DISTINCT ip_address FROM app_logs
    WHERE ip_address IS NOT NULL
      AND timestamp < NOW() - make_interval(days => :ip_dagen)
""")

_IP_UPDATE_SQL = text("""
    UPDATE app_logs SET ip_address = :nieuw
    WHERE ip_address = :oud
      AND timestamp < NOW() - make_interval(days => :ip_dagen)
""")


def _run_cleanup(conn=None) -> dict[str, int]:
    """
    Verwijdert logs ouder dan de bewaartermijn en kort oude IP-adressen in.
    Retourneert {"verwijderd": n, "ip_ingekort": m}.
    """
    inst = instellingen()
    dagen = inst.log_bewaar_dagen
    debug_dagen = min(DEBUG_BEWAAR_DAGEN, dagen)
    ip_dagen = inst.log_ip_bewaar_dagen

    if conn is None:
        with engine.connect() as eigen:
            return _run_cleanup(eigen)

    verwijderd = conn.execute(_VERWIJDER_SQL, {"dagen": dagen, "debug_dagen": debug_dagen}).rowcount
    conn.commit()

    ingekort = 0
    if ip_dagen < dagen:  # anders is alles met een oud IP-adres al verwijderd
        adressen = [r[0] for r in conn.execute(_IP_SELECT_SQL, {"ip_dagen": ip_dagen})]
        for oud in adressen:
            nieuw = ip_inkorten(oud)
            if nieuw != oud:
                ingekort += conn.execute(
                    _IP_UPDATE_SQL, {"nieuw": nieuw, "oud": oud, "ip_dagen": ip_dagen}
                ).rowcount
        conn.commit()

    return {"verwijderd": verwijderd, "ip_ingekort": ingekort}


def samenvatting(resultaat: dict[str, int]) -> str:
    inst = instellingen()
    return (f"{resultaat.get('verwijderd', 0)} logregels verwijderd (ouder dan {inst.log_bewaar_dagen} dagen), "
            f"{resultaat.get('ip_ingekort', 0)} IP-adressen ingekort (ouder dan {inst.log_ip_bewaar_dagen} dagen)")


async def _cleanup_loop() -> None:
    """Achtergrondloop: kort na de start, daarna elke 24u (+jitter)."""
    from omnitwin.services.logging_service import AppLogger

    sleep_s = _EERSTE_RUN_S
    while True:
        await asyncio.sleep(sleep_s)
        sleep_s = _BASE_INTERVAL_S + random.randint(-_JITTER_S, _JITTER_S)

        try:
            resultaat = await asyncio.to_thread(_run_cleanup)
            AppLogger.info(f"Log cleanup uitgevoerd: {samenvatting(resultaat)}", category="SERVER")
        except Exception as e:
            AppLogger.error(f"Log cleanup mislukt: {e}", category="SERVER")


def start_cleanup_scheduler() -> None:
    """Start de cleanup achtergrondtaak. Aanroepen in startup_event."""
    global _cleanup_task
    _cleanup_task = asyncio.create_task(_cleanup_loop())
    logger.info("Log cleanup scheduler gestart (interval: 24u)")


async def stop_cleanup_scheduler() -> None:
    """Stop de cleanup taak. Aanroepen in shutdown_event."""
    global _cleanup_task
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            pass
    _cleanup_task = None


async def run_cleanup_now() -> dict[str, int]:
    """
    Voer cleanup onmiddellijk uit (voor admin panel trigger / testing).
    Retourneert {"verwijderd": n, "ip_ingekort": m}.
    """
    return await asyncio.to_thread(_run_cleanup)

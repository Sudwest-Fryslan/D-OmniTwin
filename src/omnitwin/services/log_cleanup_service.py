"""
Log Cleanup Service — Sprint 17C
==================================
Dagelijkse achtergrondtaak die verouderde logs verwijdert.
Draait als asyncio-loop in de FastAPI levenscyclus — geen extra dependency.

Retentiebeleid (conform spec):
    DEBUG   → 7 dagen
    INFO    → 30 dagen
    WARNING / ERROR / CRITICAL → permanent (nooit verwijderd)

Scheduling:
    Elke 24 uur, met jitter (±30 min) om piekbelasting te vermijden.
    Eerste run: 24 uur na server-start (niet onmiddellijk).
"""

import asyncio
import random
import logging
from src.database import engine
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Retentie in dagen per log-niveau
_RETENTION_DAYS: dict[str, int] = {
    "DEBUG": 7,
    "INFO": 30,
    # WARNING / ERROR / CRITICAL: niet opgegeven → permanent
}

# Interval in seconden (24 uur + jitter)
_BASE_INTERVAL_S = 24 * 3600
_JITTER_S = 30 * 60  # ±30 minuten

_cleanup_task: asyncio.Task | None = None


async def _run_cleanup() -> dict[str, int]:
    """
    Verwijdert logs op basis van retentiebeleid.
    Retourneert dict {niveau: aantal verwijderd}.
    """
    deleted: dict[str, int] = {}

    with engine.connect() as conn:
        for level, days in _RETENTION_DAYS.items():
            result = conn.execute(
                text("""
                    DELETE FROM app_logs
                    WHERE level = :level
                      AND timestamp < NOW() - INTERVAL ':days days'
                """.replace(":days", str(days))),
                {"level": level},
            )
            conn.commit()
            deleted[level] = result.rowcount

    return deleted


async def _cleanup_loop() -> None:
    """Achtergrondloop: wacht 24u (+jitter), dan cleanup, herhaal."""
    from services.logging_service import AppLogger

    while True:
        # Eerste run na 24u — niet direct bij startup
        sleep_s = _BASE_INTERVAL_S + random.randint(-_JITTER_S, _JITTER_S)
        await asyncio.sleep(sleep_s)

        try:
            deleted = await asyncio.to_thread(_run_cleanup)
            total = sum(deleted.values())
            AppLogger.info(
                f"Log cleanup uitgevoerd: {total} records verwijderd "
                f"(DEBUG={deleted.get('DEBUG', 0)}, INFO={deleted.get('INFO', 0)})",
                category="SERVER",
            )
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
    Retourneert {niveau: aantal verwijderd}.
    """
    return await asyncio.to_thread(_run_cleanup)

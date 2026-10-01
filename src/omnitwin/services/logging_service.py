"""
Logging Service — Sprint 17A
==============================
Configureerbare, gedifferentieerde logging met async DB-schrijver.

Architectuur:
    AppLogger.info(category="API", message="...")
        → Python logging (rotating file)
        → AsyncLogQueue → PostgreSQL (app_logs)

Config wordt uit log_config tabel geladen en gecached (refresh elke 60s).
"""

import asyncio
import logging
import logging.handlers
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy import text
from omnitwin.config import instellingen
from omnitwin.database import SessionLocal

# =============================================================================
# Log Level Mapping
# =============================================================================
LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

LEVEL_PRIORITY = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}

VALID_CATEGORIES = {
    "SERVER", "API", "AUTH", "KOMPAS", "KAART",
    "RAPPORT", "LLM_CHAT", "DATABASE", "ADMIN",
}


# =============================================================================
# Config Cache — geladen uit log_config tabel
# =============================================================================
class _ConfigCache:
    """In-memory cache van log_config tabel. Refresht elke 60 seconden."""

    def __init__(self):
        self._config: Dict[str, Dict[str, Any]] = {}
        self._last_refresh: float = 0
        self._refresh_interval: float = 60.0  # seconden

    def _needs_refresh(self) -> bool:
        return time.time() - self._last_refresh > self._refresh_interval

    def refresh(self):
        """Laad configuratie uit database."""
        try:
            db = SessionLocal()
            try:
                rows = db.execute(text("SELECT category, level, enabled FROM log_config")).fetchall()
                self._config = {
                    row[0]: {"level": row[1], "enabled": row[2]}
                    for row in rows
                }
                self._last_refresh = time.time()
            finally:
                db.close()
        except Exception:
            # Bij DB-fout: behoud vorige config, of gebruik defaults
            if not self._config:
                for cat in VALID_CATEGORIES:
                    self._config[cat] = {"level": "INFO", "enabled": True}
                self._last_refresh = time.time()

    def should_log(self, category: str, level: str) -> bool:
        """Check of een bericht gelogd moet worden op basis van config."""
        if self._needs_refresh():
            self.refresh()

        cat_config = self._config.get(category)
        if not cat_config:
            return True  # Onbekende categorie: altijd loggen

        if not cat_config["enabled"]:
            return False

        return LEVEL_PRIORITY.get(level, 1) >= LEVEL_PRIORITY.get(cat_config["level"], 1)


_config_cache = _ConfigCache()


# =============================================================================
# Async Log Queue — non-blocking DB schrijver
# =============================================================================
class AsyncLogQueue:
    """In-memory queue die batched naar PostgreSQL app_logs schrijft."""

    MAX_QUEUE_SIZE = 10_000
    BATCH_SIZE = 50
    FLUSH_INTERVAL = 2.0  # seconden

    def __init__(self):
        self._queue: asyncio.Queue = None
        self._task: asyncio.Task = None
        self._running = False

    async def start(self):
        """Start de background writer task."""
        self._queue = asyncio.Queue(maxsize=self.MAX_QUEUE_SIZE)
        self._running = True
        self._task = asyncio.create_task(self._writer_loop())

    async def stop(self):
        """Stop de writer en flush resterende items."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        # Flush remaining
        await self._flush_batch()

    def enqueue(self, entry: Dict[str, Any]):
        """Voeg een log entry toe aan de queue (fire-and-forget)."""
        if self._queue is None:
            return
        try:
            self._queue.put_nowait(entry)
        except asyncio.QueueFull:
            import sys
            print(
                "WARNING: Log queue vol — oudste entries worden overgeslagen",
                file=sys.stderr,
            )

    async def _writer_loop(self):
        """Background loop: batched schrijven naar DB."""
        while self._running:
            try:
                await asyncio.sleep(self.FLUSH_INTERVAL)
                await self._flush_batch()
            except asyncio.CancelledError:
                break
            except Exception:
                # Writer mag nooit crashen
                pass

    async def _flush_batch(self):
        """Schrijf alle items in de queue naar de database."""
        if self._queue is None or self._queue.empty():
            return

        batch = []
        while not self._queue.empty() and len(batch) < self.BATCH_SIZE * 10:
            try:
                batch.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break

        if not batch:
            return

        try:
            db = SessionLocal()
            try:
                for entry in batch:
                    db.execute(
                        text("""
                            INSERT INTO app_logs 
                                (timestamp, level, category, message, user_id, 
                                 session_id, ip_address, endpoint, response_time_ms, extra)
                            VALUES 
                                (:timestamp, :level, :category, :message, :user_id,
                                 :session_id, :ip_address, :endpoint, :response_time_ms, 
                                 CAST(:extra AS jsonb))
                        """),
                        {
                            "timestamp": entry.get("timestamp", datetime.utcnow()),
                            "level": entry["level"],
                            "category": entry["category"],
                            "message": entry["message"],
                            "user_id": entry.get("user_id"),
                            "session_id": entry.get("session_id"),
                            "ip_address": entry.get("ip_address"),
                            "endpoint": entry.get("endpoint"),
                            "response_time_ms": entry.get("response_time_ms"),
                            "extra": entry.get("extra", "null"),
                        },
                    )
                db.commit()
            finally:
                db.close()
        except Exception:
            # DB-schrijf fout: entries zijn verloren, maar de app draait door
            pass


_log_queue = AsyncLogQueue()


# =============================================================================
# Python Logging Setup — Rotating File Handler
# =============================================================================
_file_handler_configured = False


def _setup_python_logging(log_level: str = "INFO"):
    """Configureer Python logging met rotating file handler."""
    global _file_handler_configured
    if _file_handler_configured:
        return

    # Root logger configureren
    root_logger = logging.getLogger()
    root_logger.setLevel(LEVEL_MAP.get(log_level.upper(), logging.INFO))

    # Rotating file handler: 10MB max, 5 backups.
    # Is logs/ niet schrijfbaar (bv. bind-mount op Windows met niet-root gebruiker),
    # dan alleen naar de console loggen in plaats van de app te laten crashen.
    logs_dir = Path(__file__).resolve().parents[3] / "logs"  # logs/ in de root van de repository
    try:
        logs_dir.mkdir(exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            logs_dir / "server.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8",
        )
    except OSError as e:
        file_handler = None
        print(f"WAARSCHUWING: logbestand niet schrijfbaar ({e}); alleen console-logging.", flush=True)
    if file_handler is not None:
        file_handler.setLevel(logging.DEBUG)  # File vangt alles op
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Console handler (beknopt)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LEVEL_MAP.get(log_level.upper(), logging.INFO))
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # Demote noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    _file_handler_configured = True


# =============================================================================
# AppLogger — Publieke API
# =============================================================================
class AppLogger:
    """
    Facade voor applicatie-logging.

    Gebruik:
        from omnitwin.services.logging_service import AppLogger
        AppLogger.info("Server gestart", category="SERVER")
        AppLogger.error("Query timeout", category="DATABASE", extra={"query_ms": 5200})
    """

    _python_logger = logging.getLogger("d_omnitwin")

    @classmethod
    def _log(
        cls,
        level: str,
        message: str,
        category: str = "SERVER",
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        endpoint: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ):
        """Interne log methode."""
        # 1. Check config cache
        if not _config_cache.should_log(category, level):
            return

        # 2. Python logging (altijd, naar file + console)
        log_msg = f"[{category}] {message}"
        py_level = LEVEL_MAP.get(level, logging.INFO)
        cls._python_logger.log(py_level, log_msg)

        # 3. Enqueue voor DB schrijven
        import json
        _log_queue.enqueue({
            "timestamp": datetime.utcnow(),
            "level": level,
            "category": category,
            "message": message,
            "user_id": user_id,
            "session_id": session_id,
            "ip_address": ip_address,
            "endpoint": endpoint,
            "response_time_ms": response_time_ms,
            "extra": json.dumps(extra) if extra else "null",
        })

    @classmethod
    def debug(cls, message: str, **kwargs):
        cls._log("DEBUG", message, **kwargs)

    @classmethod
    def info(cls, message: str, **kwargs):
        cls._log("INFO", message, **kwargs)

    @classmethod
    def warning(cls, message: str, **kwargs):
        cls._log("WARNING", message, **kwargs)

    @classmethod
    def error(cls, message: str, **kwargs):
        cls._log("ERROR", message, **kwargs)

    @classmethod
    def critical(cls, message: str, **kwargs):
        cls._log("CRITICAL", message, **kwargs)


# =============================================================================
# Init — aangeroepen vanuit main.py startup
# =============================================================================
async def init_logging():
    """Bootstrap logging stack. Aanroepen in FastAPI startup event."""
    log_level = instellingen().log_level
    _setup_python_logging(log_level)
    _config_cache.refresh()
    await _log_queue.start()
    AppLogger.info("Logging infrastructuur geïnitialiseerd", category="SERVER",
                   extra={"log_level": log_level})


async def shutdown_logging():
    """Graceful shutdown. Aanroepen in FastAPI shutdown event."""
    AppLogger.info("Server wordt afgesloten", category="SERVER")
    await _log_queue.stop()

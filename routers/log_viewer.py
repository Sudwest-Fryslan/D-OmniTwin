"""
Log Viewer API — Sprint 17B
==============================
Admin panel endpoints voor log viewing en configuratie.

Endpoints:
    GET  /api/admin/logs          — Gefilterd + gepagineerd
    GET  /api/admin/logs/stats    — Statistieken (vandaag)
    GET  /api/admin/log-config    — Configuratie ophalen
    PUT  /api/admin/log-config/{category} — Configuratie bijwerken
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.database import get_db
from routers.auth import check_auth_or_key
from services.logging_service import AppLogger, _config_cache
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from fastapi import Request

router = APIRouter(prefix="/api/admin", tags=["Log Viewer"])


# ============================================================================
# Models
# ============================================================================
class LogConfigUpdate(BaseModel):
    level: str
    enabled: bool


# ============================================================================
# GET /api/admin/logs — Gefilterd + gepagineerd
# ============================================================================
@router.get("/logs")
async def get_logs(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=10, le=200),
    category: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    period: str = Query("today"),  # today, week, month, all
    db: Session = Depends(get_db),
    auth: dict = Depends(check_auth_or_key),
):
    """Gefilterde en gepagineerde logs voor admin panel."""

    # Basis query
    where_clauses = []
    params: Dict[str, Any] = {}

    # Periode filter
    if period == "today":
        where_clauses.append("timestamp >= CURRENT_DATE")
    elif period == "week":
        where_clauses.append("timestamp >= CURRENT_DATE - INTERVAL '7 days'")
    elif period == "month":
        where_clauses.append("timestamp >= CURRENT_DATE - INTERVAL '30 days'")
    # 'all' = geen period filter

    # Category filter
    if category:
        where_clauses.append("category = :category")
        params["category"] = category

    # Level filter
    if level:
        where_clauses.append("level = :level")
        params["level"] = level

    # Zoekterm filter
    if search:
        where_clauses.append("message ILIKE :search")
        params["search"] = f"%{search}%"

    where_sql = (" WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # Count query
    count_result = db.execute(
        text(f"SELECT COUNT(*) FROM app_logs{where_sql}"), params
    ).scalar()

    # Data query met paginatie
    offset = (page - 1) * per_page
    params["limit"] = per_page
    params["offset"] = offset

    rows = db.execute(
        text(f"""
            SELECT id, timestamp, level, category, message,
                   user_id, session_id, ip_address, endpoint,
                   response_time_ms, extra
            FROM app_logs{where_sql}
            ORDER BY timestamp DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    ).fetchall()

    logs = [
        {
            "id": r[0],
            "timestamp": r[1].isoformat() if r[1] else None,
            "level": r[2],
            "category": r[3],
            "message": r[4],
            "user_id": r[5],
            "session_id": r[6],
            "ip_address": r[7],
            "endpoint": r[8],
            "response_time_ms": r[9],
            "extra": r[10],
        }
        for r in rows
    ]

    return {
        "logs": logs,
        "total": count_result,
        "page": page,
        "per_page": per_page,
        "total_pages": max(1, -(-count_result // per_page)),  # ceil division
    }


# ============================================================================
# GET /api/admin/logs/stats — Statistieken
# ============================================================================
@router.get("/logs/stats")
async def get_log_stats(
    request: Request,
    db: Session = Depends(get_db),
    auth: dict = Depends(check_auth_or_key),
):
    """Log statistieken voor dashboard cards."""

    stats_query = text("""
        SELECT
            COUNT(*) as total_today,
            COUNT(*) FILTER (WHERE level = 'ERROR') as errors_today,
            COUNT(*) FILTER (WHERE level = 'WARNING') as warnings_today,
            COUNT(DISTINCT user_id) FILTER (WHERE user_id IS NOT NULL) as active_users,
            COUNT(DISTINCT ip_address) FILTER (WHERE ip_address IS NOT NULL) as unique_ips,
            ROUND(AVG(response_time_ms) FILTER (WHERE response_time_ms IS NOT NULL)) as avg_response_ms
        FROM app_logs
        WHERE timestamp >= CURRENT_DATE
    """)

    row = db.execute(stats_query).fetchone()

    # Per-categorie verdeling (vandaag)
    cat_query = text("""
        SELECT category, COUNT(*) as count
        FROM app_logs
        WHERE timestamp >= CURRENT_DATE
        GROUP BY category
        ORDER BY count DESC
    """)
    cat_rows = db.execute(cat_query).fetchall()

    # Per-uur verdeling (vandaag)
    hourly_query = text("""
        SELECT EXTRACT(HOUR FROM timestamp)::int as hour, COUNT(*) as count
        FROM app_logs
        WHERE timestamp >= CURRENT_DATE
        GROUP BY hour
        ORDER BY hour
    """)
    hourly_rows = db.execute(hourly_query).fetchall()

    return {
        "total_today": row[0] or 0,
        "errors_today": row[1] or 0,
        "warnings_today": row[2] or 0,
        "active_users": row[3] or 0,
        "unique_ips": row[4] or 0,
        "avg_response_ms": int(row[5]) if row[5] else 0,
        "by_category": [{"category": r[0], "count": r[1]} for r in cat_rows],
        "by_hour": [{"hour": r[0], "count": r[1]} for r in hourly_rows],
    }


# ============================================================================
# GET /api/admin/log-config — Configuratie ophalen
# ============================================================================
@router.get("/log-config")
async def get_log_config(
    request: Request,
    db: Session = Depends(get_db),
    auth: dict = Depends(check_auth_or_key),
):
    """Huidige log configuratie per categorie."""

    rows = db.execute(
        text("SELECT category, level, enabled, updated_at, updated_by FROM log_config ORDER BY category")
    ).fetchall()

    return [
        {
            "category": r[0],
            "level": r[1],
            "enabled": r[2],
            "updated_at": r[3].isoformat() if r[3] else None,
            "updated_by": r[4],
        }
        for r in rows
    ]


# ============================================================================
# PUT /api/admin/log-config/{category} — Configuratie bijwerken
# ============================================================================
@router.put("/log-config/{category}")
async def update_log_config(
    category: str,
    data: LogConfigUpdate,
    request: Request,
    db: Session = Depends(get_db),
    auth: dict = Depends(check_auth_or_key),
):
    """Update log configuratie voor een specifieke categorie."""

    # Valideer level
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    if data.level.upper() not in valid_levels:
        raise HTTPException(400, f"Ongeldig level: {data.level}. Kies uit: {valid_levels}")

    # Update in DB
    result = db.execute(
        text("""
            UPDATE log_config
            SET level = :level, enabled = :enabled, updated_at = NOW(), updated_by = :user
            WHERE category = :category
        """),
        {
            "level": data.level.upper(),
            "enabled": data.enabled,
            "category": category,
            "user": auth.get("username", "unknown"),
        },
    )

    if result.rowcount == 0:
        raise HTTPException(404, f"Categorie '{category}' niet gevonden")

    db.commit()

    # Force refresh config cache zodat wijzigingen direct actief zijn
    _config_cache.refresh()

    AppLogger.info(
        f"Log config gewijzigd: {category} → level={data.level.upper()}, enabled={data.enabled}",
        category="ADMIN",
        user_id=auth.get("username"),
    )

    return {"message": f"Configuratie voor '{category}' bijgewerkt", "category": category}

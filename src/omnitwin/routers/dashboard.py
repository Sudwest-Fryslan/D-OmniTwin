from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from omnitwin.database import get_db
from omnitwin.routers.auth import vereis_admin

# Alle routes in deze router vereisen een beheerder (#65)
router = APIRouter(prefix="/api/admin/dashboard", tags=["Admin Dashboard"], dependencies=[Depends(vereis_admin)])


# ============================================================================
# Stats Endpoint
# ============================================================================
@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
):
    """Get high-level dashboard statistics."""

    # Total indicators
    total_query = text("SELECT COUNT(*) FROM indicatoren WHERE is_actief = true")
    total = db.execute(total_query).scalar()

    # Data coverage: actieve indicatoren met minstens één waarde. Alleen actieve, net als `total`,
    # anders kan het percentage boven 100% uitkomen (#246).
    coverage_query = text("""
        SELECT COUNT(*)
        FROM indicatoren i
        WHERE i.is_actief = true
          AND EXISTS (SELECT 1 FROM gebied_data gd WHERE gd.indicator_uuid = i.uuid AND gd.waarde IS NOT NULL)
    """)
    with_data = db.execute(coverage_query).scalar()

    # Metadata coverage (omschrijving, bron, eenheid present): over alle actieve indicatoren, en apart
    # over de indicatoren met data. Definities zonder levering (bijv. SWF-definities zonder waarden)
    # drukken het eerste getal; het tweede zegt iets over wat de gebruiker te zien krijgt (#246).
    meta_query = text("""
        SELECT COUNT(*) AS alle,
               COUNT(*) FILTER (WHERE EXISTS (
                   SELECT 1 FROM gebied_data gd WHERE gd.indicator_uuid = i.uuid AND gd.waarde IS NOT NULL
               )) AS met_data
        FROM indicatoren i
        WHERE i.is_actief = true
          AND i.omschrijving IS NOT NULL AND i.omschrijving != ''
          AND i.bron IS NOT NULL AND i.bron != ''
          AND i.eenheid IS NOT NULL AND i.eenheid != ''
    """)
    meta_complete, meta_complete_met_data = db.execute(meta_query).one()

    # Trending (indicators with 5+ distinct years of data)
    trending_query = text("""
        SELECT COUNT(*) FROM (
            SELECT indicator_uuid
            FROM gebied_data
            WHERE jaar IS NOT NULL
              AND COALESCE(scenario_id, 'current') = 'current'
            GROUP BY indicator_uuid
            HAVING COUNT(DISTINCT jaar) >= 5
        ) as sub
    """)
    trending = db.execute(trending_query).scalar()

    return {
        "total_indicators": total,
        "with_data_count": with_data,
        "with_data_pct": round((with_data / total * 100) if total > 0 else 0, 1),
        "metadata_complete_count": meta_complete,
        "metadata_complete_pct": round((meta_complete / total * 100) if total > 0 else 0, 1),
        "metadata_complete_met_data_count": meta_complete_met_data,
        "metadata_complete_met_data_pct": round((meta_complete_met_data / with_data * 100) if with_data > 0 else 0, 1),
        "trending_count": trending,
    }


# ============================================================================
# Quadrants Endpoint
# ============================================================================
@router.get("/quadrants")
def get_quadrant_coverage(
    config_id: int = 1,
    db: Session = Depends(get_db),
):
    """Get coverage statistics per quadrant (Titel)."""

    # Get all titels and their indicators count
    query = text("""
        SELECT
            titel_naam,
            COUNT(DISTINCT vkh.indicator_uuid) as total_indicators,
            COUNT(DISTINCT CASE WHEN gd.indicator_uuid IS NOT NULL THEN i.uuid END) as with_data
        FROM v_kompas_hierarchie vkh
        JOIN indicatoren i ON vkh.indicator_uuid = i.uuid
        LEFT JOIN (
            SELECT DISTINCT indicator_uuid
            FROM gebied_data
            WHERE waarde IS NOT NULL
        ) gd ON i.uuid = gd.indicator_uuid
        WHERE vkh.config_id = :config_id
        GROUP BY titel_naam
        ORDER BY titel_naam
    """)

    rows = db.execute(query, {"config_id": config_id}).fetchall()

    results = []
    for row in rows:
        total = row[1]
        with_data = row[2]
        pct = round((with_data / total * 100) if total > 0 else 0, 1)

        results.append({"name": row[0], "total": total, "with_data": with_data, "coverage_pct": pct})

    return results


# ============================================================================
# Detailed Indicators Endpoint
# ============================================================================
@router.get("/indicators")
def get_dashboard_indicators(
    search: str | None = None,
    sort: str = "naam",
    direction: str = "asc",
    filter_status: str = "all",  # all, no_data, outdated_meta
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Get detailed list of indicators with status for the dashboard."""

    # Base query
    query_str = """
        SELECT
            i.uuid::text,
            i.naam,
            i.score_type,
            vkh.titel_naam as kwadrant,

            -- Data stats
            COUNT(DISTINCT gd.jaar) as years_count,
            MAX(gd.updated_at) as last_updated,
            MAX(gd.jaar) as last_year,

            -- Metadata check
            (CASE WHEN
                (i.omschrijving IS NOT NULL AND i.omschrijving != '') AND
                (i.bron IS NOT NULL AND i.bron != '') AND
                (i.eenheid IS NOT NULL AND i.eenheid != '')
            THEN true ELSE false END) as meta_complete,

            -- Sparkline (last 5 years of averages)
            NULL as sparkline -- Placeholder, populated later if needed or via separate query for perf

        FROM indicatoren i
        LEFT JOIN v_kompas_hierarchie vkh ON i.uuid = vkh.indicator_uuid AND vkh.config_id = 1
        LEFT JOIN gebied_data gd ON i.uuid = gd.indicator_uuid
             AND COALESCE(gd.scenario_id, 'current') = 'current'
    """

    wheres = ["1=1"]
    params = {"limit": limit, "offset": offset}

    if search:
        wheres.append("(i.naam ILIKE :search OR i.omschrijving ILIKE :search)")
        params["search"] = f"%{search}%"

    query_str += " WHERE " + " AND ".join(wheres)

    query_str += " GROUP BY i.uuid, i.naam, i.score_type, vkh.titel_naam, i.omschrijving, i.bron, i.eenheid"

    # Having clause for filters
    if filter_status == "no_data":
        query_str += " HAVING COUNT(gd.id) = 0"
    elif filter_status == "outdated_meta":
        query_str += " HAVING (i.omschrijving IS NULL OR i.omschrijving = '' OR i.bron IS NULL OR i.bron = '' OR i.eenheid IS NULL OR i.eenheid = '')"

    # Sorting
    if sort == "naam":
        query_str += f" ORDER BY i.naam {direction}"
    elif sort == "last_updated":
        query_str += f" ORDER BY MAX(gd.updated_at) {direction} NULLS LAST"
    elif sort == "years_count":
        query_str += f" ORDER BY COUNT(DISTINCT gd.jaar) {direction}"
    else:
        query_str += f" ORDER BY i.naam {direction}"

    query_str += " LIMIT :limit OFFSET :offset"

    # Execute
    result = db.execute(text(query_str), params)
    rows = result.fetchall()

    # Total count (approximate for pagination)
    total_query = text("SELECT COUNT(*) FROM indicatoren")  # Simplified
    total = db.execute(total_query).scalar()

    output = []
    for row in rows:
        output.append(
            {
                "uuid": row[0],
                "naam": row[1],
                "score_type": row[2],
                "kwadrant": row[3] or "Overig",
                "years_count": row[4],
                "last_updated": row[5],
                "last_year": row[6],
                "meta_complete": row[7],
                "sparkline": [],
            }
        )

    # --- Sparkline Data Fetching ---
    if output:
        uuids = [item["uuid"] for item in output]

        # Query for sparkline data (avg value per year, last 10 years)
        spark_query = text("""
            SELECT indicator_uuid, jaar, AVG(waarde) as avg_val
            FROM gebied_data
            WHERE indicator_uuid IN :uuids
              AND jaar >= 2015
              AND waarde IS NOT NULL
              AND COALESCE(scenario_id, 'current') = 'current'
            GROUP BY indicator_uuid, jaar
            ORDER BY indicator_uuid, jaar
        """)

        try:
            # SQLAlchemy `IN` clause handling with text() can be tricky in some versions
            # But typically passing tuple works.
            # If not, we might need to expand manually or use list.
            spark_rows = db.execute(spark_query, {"uuids": tuple(uuids)}).fetchall()

            # Group by uuid
            spark_map = {}
            for r in spark_rows:
                uid = str(r[0])
                val = float(r[2]) if r[2] is not None else 0
                if uid not in spark_map:
                    spark_map[uid] = []
                spark_map[uid].append(val)

            # Assign to output
            for item in output:
                if item["uuid"] in spark_map:
                    item["sparkline"] = spark_map[item["uuid"]]
        except Exception as e:
            from omnitwin.services.logging_service import AppLogger

            AppLogger.error(f"Error fetching sparklines: {e}", category="ADMIN")
            # Fail silently, return empty list
            pass

    return {"indicators": output, "total": total, "limit": limit, "offset": offset}


# ============================================================================
# Export Endpoint
# ============================================================================
@router.get("/export")
def export_dashboard_data(
    db: Session = Depends(get_db),
):
    """Export all dashboard data as CSV."""
    import csv
    import io
    from datetime import datetime

    from fastapi.responses import StreamingResponse

    # 1. Fetch ALL data (no pagination)
    query_str = """
        SELECT
            i.naam,
            i.code,
            i.score_type,
            vkh.titel_naam as kwadrant,
            i.bron,
            i.eenheid,
            COUNT(DISTINCT gd.jaar) as years_count,
            MAX(gd.updated_at) as last_updated,
            MAX(gd.jaar) as last_year
        FROM indicatoren i
        LEFT JOIN v_kompas_hierarchie vkh ON i.uuid = vkh.indicator_uuid AND vkh.config_id = 1
        LEFT JOIN gebied_data gd ON i.uuid = gd.indicator_uuid
             AND COALESCE(gd.scenario_id, 'current') = 'current'
        GROUP BY i.uuid, i.naam, i.code, i.score_type, vkh.titel_naam, i.bron, i.eenheid
        ORDER BY i.naam ASC
    """

    result = db.execute(text(query_str))
    rows = result.fetchall()

    # 2. Generate CSV
    stream = io.StringIO()
    writer = csv.writer(stream)

    # Header
    writer.writerow(
        ["Naam", "Code", "Score Type", "Kwadrant", "Bron", "Eenheid", "Aantal Jaren", "Laatste Update", "Laatste Jaar"]
    )

    # Rows
    for row in rows:
        writer.writerow(
            [
                row[0],  # naam
                row[1],  # code
                row[2],  # score_type
                row[3] or "Overig",  # kwadrant
                row[4] or "",  # bron
                row[5] or "",  # eenheid
                row[6],  # years_count
                row[7] or "",  # last_updated
                row[8] or "",  # last_year
            ]
        )

    response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")

    filename = f"dashboard_export_{datetime.now().strftime('%Y%m%d')}.csv"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"

    return response

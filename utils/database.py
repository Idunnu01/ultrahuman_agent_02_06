"""
Database utilities and connection management
"""

from __future__ import annotations

import os
import json
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

# Initialize SQLAlchemy (bound in app factory)
db = SQLAlchemy()
logger = logging.getLogger(__name__)


# ---------------------------- Session helpers ---------------------------- #

@contextmanager
def db_transaction():
    """Context manager for DB transactions with automatic rollback on error."""
    try:
        yield db.session
        db.session.commit()
    except Exception as e:
        logger.error(f"Database transaction failed: {str(e)}")
        db.session.rollback()
        raise


def init_database(app):
    """Create all tables once the app is configured."""
    with app.app_context():
        db.create_all()
        logger.info("Database tables created successfully")


def execute_raw_sql(query: str, params: Optional[Dict[str, Any]] = None):
    """
    Execute raw SQL safely (parameterized).
    Returns the SQLAlchemy Result object.
    """
    try:
        result = db.session.execute(text(query), params or {})
        db.session.commit()
        return result
    except Exception as e:
        logger.error(f"Raw SQL execution failed: {str(e)}")
        db.session.rollback()
        raise


# ------------------------- Bulk insert / upsert -------------------------- #

def _coerce_ts(row: Dict[str, Any]) -> None:
    """
    Best-effort normalization of 'timestamp' field to a Python datetime, if it's
    currently a string like 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SS(.fff)Z'.
    """
    ts = row.get("timestamp")
    if isinstance(ts, str):
        s = ts.replace("T", " ").replace("Z", "")
        # trim fractional seconds if present
        if "." in s:
            s = s.split(".", 1)[0]
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                row["timestamp"] = datetime.strptime(s, fmt)
                return
            except ValueError:
                continue


# --- add this small helper near the top of database.py (below imports) ---
def _detect_engine_and_dialect():
    """Return (engine, dialect_name, uri_lower) as best as possible."""
    eng = None
    try:
        eng = db.session.get_bind()
    except Exception:
        pass
    if eng is None:
        try:
            eng = db.engine  # Flask-SQLAlchemy 3.x
        except Exception:
            eng = None

    name = "unknown"
    uri_lower = ""
    if eng is not None:
        try:
            name = eng.dialect.name or "unknown"
        except Exception:
            pass
        try:
            uri_lower = str(getattr(eng, "url", "")) .lower()
        except Exception:
            uri_lower = ""

    return eng, name, uri_lower


def bulk_insert_metrics(
    metrics_data: Iterable[Dict[str, Any]],
    upsert_mode: Optional[str] = None,
) -> bool:
    """
    Idempotent bulk insert for 'metrics'.

    upsert_mode:
      - "update" (default): update existing row on duplicate key
      - "ignore": keep existing row, ignore incoming duplicate
    """
    rows = [dict(r) for r in metrics_data]
    if not rows:
        return True

    from app.models import Metric  # lazy import to avoid cycles

    # Normalize timestamps and JSON
    for r in rows:
        _coerce_ts(r)
        md = r.get("meta_data")
        if isinstance(md, (dict, list)):
            r["meta_data"] = json.dumps(md)

    # Deduplicate within the batch itself (latest wins)
    dedup: Dict[tuple, Dict[str, Any]] = {}
    for r in rows:
        k = (r.get("user_id"), r.get("metric_type"), r.get("timestamp"))
        dedup[k] = r
    rows = list(dedup.values())

    # Decide mode and dialect
    mode = (upsert_mode or os.getenv("METRICS_UPSERT_MODE") or "update").lower()
    eng, dialect, uri_lower = _detect_engine_and_dialect()
    is_mysql = ("mysql" in dialect) or ("mysql" in uri_lower)
    is_pg = ("postgres" in dialect) or ("postgresql" in dialect) or ("postgres" in uri_lower)

    logger.info(f"bulk_insert_metrics: rows={len(rows)} mode={mode} dialect={dialect}")

    try:
        if is_mysql:
            # Use raw SQL to guarantee MySQL behavior
            from sqlalchemy import text

            if mode == "ignore":
                stmt = text("""
                    INSERT IGNORE INTO metrics
                      (user_id, metric_type, value, unit, timestamp, source, meta_data)
                    VALUES
                      (:user_id, :metric_type, :value, :unit, :timestamp, :source, :meta_data)
                """)
            else:  # default: update in place
                stmt = text("""
                    INSERT INTO metrics
                      (user_id, metric_type, value, unit, timestamp, source, meta_data)
                    VALUES
                      (:user_id, :metric_type, :value, :unit, :timestamp, :source, :meta_data)
                    ON DUPLICATE KEY UPDATE
                      value = VALUES(value),
                      unit = VALUES(unit),
                      source = VALUES(source),
                      meta_data = VALUES(meta_data)
                """)
            db.session.execute(stmt, rows)

        elif is_pg:
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            tbl = Metric.__table__
            stmt = pg_insert(tbl).values(rows)
            if mode == "ignore":
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=["user_id", "metric_type", "timestamp"]
                )
            else:
                stmt = stmt.on_conflict_do_update(
                    index_elements=["user_id", "metric_type", "timestamp"],
                    set_=dict(
                        value=stmt.excluded.value,
                        unit=stmt.excluded.unit,
                        source=stmt.excluded.source,
                        meta_data=stmt.excluded.meta_data,
                    ),
                )
            db.session.execute(stmt)

        else:
            # As a last resort, try bulk mappings (may fail on duplicates)
            db.session.bulk_insert_mappings(Metric, rows)

        db.session.commit()
        logger.info("Bulk insert OK")
        return True

    except SQLAlchemyError as e:
        logger.error(f"Bulk insert failed: {e}")
        db.session.rollback()
        return False



# ----------------------------- Housekeeping ----------------------------- #

def cleanup_old_data(days_to_keep: int = 90) -> int:
    """
    Clean up old data to manage database size:
      - Resolved alerts older than cutoff
      - System logs older than cutoff
    Returns number of records deleted (alerts + logs).
    """
    try:
        from app.models import SystemLog, Alert  # lazy import to avoid cycles

        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        deleted_alerts = Alert.query.filter(
            Alert.is_resolved.is_(True),
            Alert.resolved_at < cutoff_date
        ).delete(synchronize_session=False)

        deleted_logs = SystemLog.query.filter(
            SystemLog.created_at < cutoff_date
        ).delete(synchronize_session=False)

        db.session.commit()
        logger.info(f"Cleaned up {deleted_alerts} old alerts and {deleted_logs} old logs")
        return int((deleted_alerts or 0) + (deleted_logs or 0))

    except Exception as e:
        logger.error(f"Data cleanup failed: {str(e)}")
        db.session.rollback()
        return 0


def get_table_stats() -> Dict[str, int]:
    """Return simple counts for a few key tables. Missing tables are treated as 0."""
    stats: Dict[str, int] = {}
    try:
        from app.models import User, Metric, Alert, DailyReport, Intervention  # type: ignore

        def _safe_count(model) -> int:
            try:
                return model.query.count()
            except Exception:
                return 0

        stats = {
            "users": _safe_count(User),
            "metrics": _safe_count(Metric),
            "alerts": _safe_count(Alert),
            "daily_reports": _safe_count(DailyReport),
            "interventions": _safe_count(Intervention),
        }
    except Exception as e:
        logger.error(f"Failed to get table stats: {str(e)}")
    return stats


def optimize_database():
    """
    Run simple, dialect-aware optimization commands.
    MySQL:   ANALYZE/OPTIMIZE TABLE
    Postgres: VACUUM (ANALYZE)
    """
    try:
        dialect = db.session.bind.dialect.name if db.session.bind else "unknown"

        if dialect == "mysql":
            for tbl in ("metrics", "alerts", "daily_reports"):
                for stmt in (f"ANALYZE TABLE {tbl}", f"OPTIMIZE TABLE {tbl}"):
                    try:
                        db.session.execute(text(stmt))
                    except Exception as e:
                        logger.warning(f"MySQL optimization failed: {stmt} - {e}")

        elif dialect in ("postgresql", "postgres"):
            for tbl in ("metrics", "alerts", "daily_reports"):
                try:
                    db.session.execute(text(f"VACUUM (ANALYZE) {tbl}"))
                except Exception as e:
                    logger.warning(f"Postgres vacuum failed on {tbl}: {e}")

        else:
            logger.info(f"No optimization routine for dialect '{dialect}'")

        db.session.commit()
        logger.info("Database optimization completed")

    except Exception as e:
        logger.error(f"Database optimization failed: {str(e)}")
        db.session.rollback()


# ------------------------------ Backup ---------------------------------- #

def backup_user_data(user_id: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Export a user's data (user profile + metrics + alerts + reports + interventions)
    to a Python dict. If output_path is provided, also writes pretty JSON to disk.
    """
    try:
        from app.models import User, Metric, Alert, DailyReport, Intervention  # lazy import

        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        def _iso(dt: Optional[datetime]) -> Optional[str]:
            return dt.isoformat() if dt else None

        user_data: Dict[str, Any] = {
            "user": {
                "id": getattr(user, "id", None),
                "ultrahuman_user_id": getattr(user, "ultrahuman_user_id", None),
                "phone_number": getattr(user, "phone_number", None),
                "timezone": getattr(user, "timezone", None),
                "onboarded_at": _iso(getattr(user, "onboarded_at", None)),
                "preferences": getattr(user, "preferences", None),
            },
            "metrics": [],
            "alerts": [],
            "reports": [],
            "interventions": [],
        }

        # Metrics
        for m in Metric.query.filter_by(user_id=user_id).all():
            user_data["metrics"].append({
                "metric_type": m.metric_type,
                "value": m.value,
                "unit": m.unit,
                "timestamp": _iso(m.timestamp),
                # your model uses 'meta_data' (JSON)
                "meta_data": getattr(m, "meta_data", None),
                "source": getattr(m, "source", None),
            })

        # Alerts
        for a in Alert.query.filter_by(user_id=user_id).all():
            user_data["alerts"].append({
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": getattr(a, "title", None),
                "message": getattr(a, "message", None),
                "created_at": _iso(getattr(a, "created_at", None)),
                "resolved_at": _iso(getattr(a, "resolved_at", None)),
                "is_resolved": getattr(a, "is_resolved", None),
            })

        # Daily Reports
        for r in DailyReport.query.filter_by(user_id=user_id).all():
            user_data["reports"].append({
                "report_date": _iso(getattr(r, "report_date", None)),
                "insights": getattr(r, "insights", None),
                "recommendations": getattr(r, "recommendations", None),
                "generated_at": _iso(getattr(r, "generated_at", None)),
            })

        # Interventions
        for iv in Intervention.query.filter_by(user_id=user_id).all():
            user_data["interventions"].append({
                "name": iv.name,
                "description": getattr(iv, "description", None),
                "category": getattr(iv, "category", None),
                "started_at": _iso(getattr(iv, "started_at", None)),
                "ended_at": _iso(getattr(iv, "ended_at", None)),
                "effectiveness_scores": getattr(iv, "effectiveness_scores", None),
            })

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(user_data, f, indent=2, ensure_ascii=False)
            logger.info(f"User data exported to {output_path}")

        return user_data

    except Exception as e:
        logger.error(f"Failed to backup user data: {str(e)}")
        raise

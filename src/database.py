"""Production database layer."""
import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from src.models import Alert, FrameRecord

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS frames (
    frame_id     TEXT PRIMARY KEY,
    timestamp    TEXT NOT NULL,
    location     TEXT,
    latitude     REAL,
    longitude    REAL,
    altitude     REAL,
    objects_json TEXT,
    detections_json TEXT,
    telemetry_json TEXT,
    caption      TEXT,
    frame_desc   TEXT,
    summary      TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id     TEXT PRIMARY KEY,
    timestamp    TEXT NOT NULL,
    alert_type   TEXT NOT NULL,
    severity     TEXT NOT NULL,
    location     TEXT,
    description  TEXT,
    frame_ids    TEXT,
    resolved     INTEGER DEFAULT 0,
    metadata_json TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_frames_timestamp  ON frames(timestamp);
CREATE INDEX IF NOT EXISTS idx_frames_location   ON frames(location);
CREATE INDEX IF NOT EXISTS idx_alerts_timestamp  ON alerts(timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_type       ON alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_severity   ON alerts(severity);

CREATE VIRTUAL TABLE IF NOT EXISTS frames_fts USING fts5(
    frame_id,
    objects_json,
    caption,
    frame_desc,
    summary,
    location,
    content=frames,
    content_rowid=rowid
);

CREATE TRIGGER IF NOT EXISTS frames_ai AFTER INSERT ON frames BEGIN
    INSERT INTO frames_fts(rowid, frame_id, objects_json, caption, frame_desc, summary, location)
    VALUES (new.rowid, new.frame_id, new.objects_json, new.caption, new.frame_desc, new.summary, new.location);
END;

CREATE TRIGGER IF NOT EXISTS frames_ad AFTER DELETE ON frames BEGIN
    INSERT INTO frames_fts(frames_fts, rowid, frame_id, objects_json, caption, frame_desc, summary, location)
    VALUES('delete', old.rowid, old.frame_id, old.objects_json, old.caption, old.frame_desc, old.summary, old.location);
END;

CREATE TRIGGER IF NOT EXISTS frames_au AFTER UPDATE ON frames BEGIN
    INSERT INTO frames_fts(frames_fts, rowid, frame_id, objects_json, caption, frame_desc, summary, location)
    VALUES('delete', old.rowid, old.frame_id, old.objects_json, old.caption, old.frame_desc, old.summary, old.location);
    INSERT INTO frames_fts(rowid, frame_id, objects_json, caption, frame_desc, summary, location)
    VALUES (new.rowid, new.frame_id, new.objects_json, new.caption, new.frame_desc, new.summary, new.location);
END;
"""


class SecurityDatabase:
    def __init__(self, db_path: str = "data/security.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._initialize()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize(self):
        with self._conn() as conn:
            conn.executescript(SCHEMA_SQL)
        logger.info(f"Database initialized at {self.db_path}")

    def insert_frame(self, record: FrameRecord) -> bool:
        try:
            with self._conn() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO frames
                    (frame_id, timestamp, location, latitude, longitude, altitude,
                     objects_json, detections_json, telemetry_json, caption,
                     frame_desc, summary)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    record.frame_id,
                    record.timestamp.isoformat(),
                    record.telemetry.location_label if record.telemetry else None,
                    record.telemetry.latitude if record.telemetry else None,
                    record.telemetry.longitude if record.telemetry else None,
                    record.telemetry.altitude if record.telemetry else None,
                    json.dumps(record.detected_classes()),
                    json.dumps([d.to_dict() for d in record.detections]),
                    json.dumps(record.telemetry.to_dict() if record.telemetry else {}),
                    record.caption,
                    record.frame_description,
                    record.object_summary,
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to insert frame {record.frame_id}: {e}")
            return False

    def insert_alert(self, alert: Alert) -> bool:
        try:
            with self._conn() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO alerts
                    (alert_id, timestamp, alert_type, severity, location,
                     description, frame_ids, resolved, metadata_json)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    alert.alert_id,
                    alert.timestamp.isoformat(),
                    alert.alert_type.value,
                    alert.severity.value,
                    alert.location,
                    alert.description,
                    json.dumps(alert.frame_ids),
                    int(alert.resolved),
                    json.dumps(alert.metadata),
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to insert alert {alert.alert_id}: {e}")
            return False

    def query_frames_by_object(self, object_class: str, limit: int = 100) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM frames
                WHERE objects_json LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f'%"{object_class}"%', limit)).fetchall()
        return [dict(r) for r in rows]

    def query_frames_by_timerange(self, start: datetime, end: datetime, location: Optional[str] = None) -> List[Dict]:
        sql = "SELECT * FROM frames WHERE timestamp BETWEEN ? AND ?"
        params: List[Any] = [start.isoformat(), end.isoformat()]
        if location:
            sql += " AND location LIKE ?"
            params.append(f"%{location}%")
        sql += " ORDER BY timestamp ASC"
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def fulltext_search(self, query: str, limit: int = 50) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT f.* FROM frames f
                JOIN frames_fts fts ON f.frame_id = fts.frame_id
                WHERE frames_fts MATCH ?
                ORDER BY bm25(frames_fts)
                LIMIT ?
            """, (query, limit)).fetchall()
        return [dict(r) for r in rows]

    def get_alerts(self, alert_type: Optional[str] = None, severity: Optional[str] = None, since_hours: int = 24, resolved: Optional[bool] = None, limit: int = 200) -> List[Dict]:
        since = (datetime.now() - timedelta(hours=since_hours)).isoformat()
        sql = "SELECT * FROM alerts WHERE timestamp >= ?"
        params: List[Any] = [since]
        if alert_type:
            sql += " AND alert_type = ?"
            params.append(alert_type)
        if severity:
            sql += " AND severity = ?"
            params.append(severity)
        if resolved is not None:
            sql += " AND resolved = ?"
            params.append(int(resolved))
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_statistics(self) -> Dict:
        with self._conn() as conn:
            total_frames = conn.execute("SELECT COUNT(*) FROM frames").fetchone()[0]
            total_alerts = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
            open_alerts = conn.execute("SELECT COUNT(*) FROM alerts WHERE resolved=0").fetchone()[0]
            alert_by_type = conn.execute("SELECT alert_type, COUNT(*) as cnt FROM alerts GROUP BY alert_type").fetchall()
            alert_by_severity = conn.execute("SELECT severity, COUNT(*) as cnt FROM alerts GROUP BY severity").fetchall()
            recent_locations = conn.execute("""
                SELECT location, COUNT(*) as cnt FROM frames
                WHERE location IS NOT NULL
                GROUP BY location ORDER BY cnt DESC LIMIT 10
            """).fetchall()
            hourly = conn.execute("""
                SELECT strftime('%H', timestamp) as hour, COUNT(*) as cnt
                FROM frames
                WHERE timestamp >= datetime('now', '-24 hours')
                GROUP BY hour ORDER BY hour
            """).fetchall()
        return {
            "total_frames": total_frames,
            "total_alerts": total_alerts,
            "open_alerts": open_alerts,
            "alerts_by_type": {r["alert_type"]: r["cnt"] for r in alert_by_type},
            "alerts_by_severity": {r["severity"]: r["cnt"] for r in alert_by_severity},
            "top_locations": [{"location": r["location"], "count": r["cnt"]} for r in recent_locations],
            "hourly_activity": [{"hour": r["hour"], "count": r["cnt"]} for r in hourly],
        }

    def resolve_alert(self, alert_id: str) -> bool:
        with self._conn() as conn:
            conn.execute("UPDATE alerts SET resolved=1 WHERE alert_id=?", (alert_id,))
        return True

    def clear_all(self) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM alerts")
            conn.execute("DELETE FROM frames")

    def get_recent_frames(self, limit: int = 20) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM frames ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

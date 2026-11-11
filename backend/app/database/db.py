import sqlite3
import json
import os
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.config import settings

DB_FILE = settings.absolute_db_path

_fallback_memory_conn = None
_wal_initialized = False

def get_db_connection() -> sqlite3.Connection:
    global _fallback_memory_conn, _wal_initialized
    try:
        if not DB_FILE.parent.exists():
            DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_FILE), check_same_thread=False, timeout=10.0)
        conn.row_factory = sqlite3.Row
        if not _wal_initialized:
            try:
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
            except Exception:
                pass
            _wal_initialized = True
        return conn
    except Exception:
        # Resilient cloud container fallback: in-memory DB if local disk is unwritable
        if _fallback_memory_conn is None:
            _fallback_memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            _fallback_memory_conn.row_factory = sqlite3.Row
        return _fallback_memory_conn

@contextmanager
def _db_session():
    """Yields a SQLite connection and closes file-backed connections safely on exit."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    finally:
        if conn is not _fallback_memory_conn:
            try:
                conn.close()
            except Exception:
                pass

def init_db():
    with _db_session() as conn:
        cursor = conn.cursor()
        cursor.execute("""
    CREATE TABLE IF NOT EXISTS missions (
        id TEXT PRIMARY KEY,
        task TEXT NOT NULL,
        status TEXT NOT NULL,
        start_url TEXT,
        allowed_domains TEXT,
        plan_json TEXT,
        extracted_data_json TEXT,
        summary_report_json TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        completed_at TEXT
    );
    """)
        cursor.execute("""
    CREATE TABLE IF NOT EXISTS mission_events (
        id TEXT PRIMARY KEY,
        mission_id TEXT NOT NULL,
        step_id TEXT,
        event_type TEXT NOT NULL,
        category TEXT NOT NULL,
        message TEXT NOT NULL,
        details_json TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (mission_id) REFERENCES missions (id)
    );
    """)
        cursor.execute("""
    CREATE TABLE IF NOT EXISTS artifacts (
        id TEXT PRIMARY KEY,
        mission_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size_bytes INTEGER NOT NULL,
        content_type TEXT NOT NULL,
        sha256_hash TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (mission_id) REFERENCES missions (id)
    );
    """)

class Database:
    @staticmethod
    def save_mission(mission_data: Dict[str, Any]):
        with _db_session() as conn:
            conn.execute("""
        INSERT OR REPLACE INTO missions (
            id, task, status, start_url, allowed_domains, plan_json,
            extracted_data_json, summary_report_json, created_at, updated_at, completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mission_data["id"],
            mission_data["task"],
            mission_data["status"],
            mission_data.get("start_url"),
            json.dumps(mission_data.get("allowed_domains", []), default=str),
            json.dumps(mission_data.get("plan_json", {}), default=str),
            json.dumps(mission_data.get("extracted_data", []), default=str),
            json.dumps(mission_data.get("summary_report", {}), default=str),
            str(mission_data.get("created_at", datetime.utcnow().isoformat())),
            str(mission_data.get("updated_at", datetime.utcnow().isoformat())),
            str(mission_data.get("completed_at")) if mission_data.get("completed_at") else None
        ))

    @staticmethod
    def get_mission(mission_id: str) -> Optional[Dict[str, Any]]:
        with _db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM missions WHERE id = ?", (mission_id,))
            row = cursor.fetchone()
        if not row:
            return None
        res = dict(row)
        res["allowed_domains"] = json.loads(res["allowed_domains"] or "[]")
        res["plan_json"] = json.loads(res["plan_json"] or "{}")
        res["extracted_data"] = json.loads(res["extracted_data_json"] or "[]")
        res["summary_report"] = json.loads(res["summary_report_json"] or "{}")
        if "steps" not in res or not res["steps"]:
            res["steps"] = res["plan_json"].get("steps", [])
        return res

    @staticmethod
    def list_missions(limit: int = 25) -> List[Dict[str, Any]]:
        with _db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM missions ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
        missions = []
        for r in rows:
            item = dict(r)
            item["allowed_domains"] = json.loads(item["allowed_domains"] or "[]")
            item["extracted_data"] = json.loads(item["extracted_data_json"] or "[]")
            item["summary_report"] = json.loads(item["summary_report_json"] or "{}")
            missions.append(item)
        return missions

    @staticmethod
    def save_event(event_data: Dict[str, Any]):
        with _db_session() as conn:
            conn.execute("""
        INSERT INTO mission_events (
            id, mission_id, step_id, event_type, category, message, details_json, timestamp
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_data["id"],
            event_data["mission_id"],
            event_data.get("step_id"),
            event_data["event_type"],
            event_data["category"],
            event_data["message"],
            json.dumps(event_data.get("details", {}), default=str),
            str(event_data.get("timestamp", datetime.utcnow().isoformat()))
        ))

    @staticmethod
    def get_events(mission_id: str) -> List[Dict[str, Any]]:
        with _db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM mission_events WHERE mission_id = ? ORDER BY timestamp ASC", (mission_id,))
            rows = cursor.fetchall()
        events = []
        for r in rows:
            item = dict(r)
            item["details"] = json.loads(item["details_json"] or "{}")
            events.append(item)
        return events

    @staticmethod
    def save_artifact(art_data: Dict[str, Any]):
        with _db_session() as conn:
            conn.execute("""
        INSERT INTO artifacts (
            id, mission_id, filename, file_path, file_size_bytes, content_type, sha256_hash, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            art_data["artifact_id"],
            art_data["mission_id"],
            art_data["filename"],
            art_data["file_path"],
            art_data["file_size_bytes"],
            art_data["content_type"],
            art_data.get("sha256_hash"),
            art_data.get("created_at", datetime.utcnow().isoformat())
        ))

    @staticmethod
    def get_artifacts(mission_id: str) -> List[Dict[str, Any]]:
        with _db_session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM artifacts WHERE mission_id = ?", (mission_id,))
            rows = cursor.fetchall()
        return [dict(r) for r in rows]

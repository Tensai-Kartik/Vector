import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.config import settings

DB_FILE = settings.absolute_db_path

def get_db_connection() -> sqlite3.Connection:
    if not DB_FILE.parent.exists():
        DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
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
    conn.commit()
    conn.close()

class Database:
    @staticmethod
    def save_mission(mission_data: Dict[str, Any]):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
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
        conn.commit()
        conn.close()

    @staticmethod
    def get_mission(mission_id: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM missions WHERE id = ?", (mission_id,))
        row = cursor.fetchone()
        conn.close()
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
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM missions ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
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
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
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
        conn.commit()
        conn.close()

    @staticmethod
    def get_events(mission_id: str) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mission_events WHERE mission_id = ? ORDER BY timestamp ASC", (mission_id,))
        rows = cursor.fetchall()
        conn.close()
        events = []
        for r in rows:
            item = dict(r)
            item["details"] = json.loads(item["details_json"] or "{}")
            events.append(item)
        return events

    @staticmethod
    def save_artifact(art_data: Dict[str, Any]):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
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
        conn.commit()
        conn.close()

    @staticmethod
    def get_artifacts(mission_id: str) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM artifacts WHERE mission_id = ?", (mission_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

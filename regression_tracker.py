# regression_tracker.py
# Tracks accessibility regressions across scans
# Classifies each finding as: NEW | EXISTING | FIXED

import sqlite3
import json
from datetime import datetime

DB_PATH = "scan_history.db"


def _db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scan_snapshots (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            url         TEXT NOT NULL,
            scanned_at  TEXT NOT NULL,
            score       REAL,
            violation_ids TEXT,
            full_result TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            url         TEXT,
            score       REAL,
            failures    INTEGER,
            eaa_risk    TEXT,
            scanned     TEXT
        )
    """)
    conn.commit()
    return conn


def save_snapshot(url: str, result: dict, score: float):
    """Save full scan result for regression comparison."""
    conn = _db()
    violations = [
        r["id"] for r in result.get("rules", [])
        if r.get("status") == "fail"
    ]
    conn.execute("""
        INSERT INTO scan_snapshots (url, scanned_at, score, violation_ids, full_result)
        VALUES (?, ?, ?, ?, ?)
    """, (
        url,
        datetime.now().isoformat(),
        score,
        json.dumps(violations),
        json.dumps({
            "rules": [
                {k: v for k, v in r.items() if k != "instances"}
                for r in result.get("rules", [])
            ]
        })
    ))
    conn.commit()
    conn.close()


def save_history(url: str, score: float, failures: int, eaa_risk: str):
    """Save summary to history for trend tracking."""
    conn = _db()
    conn.execute("""
        INSERT INTO scan_history (url, score, failures, eaa_risk, scanned)
        VALUES (?, ?, ?, ?, ?)
    """, (url, score, failures, eaa_risk, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_previous_snapshot(url: str) -> dict | None:
    """Get the most recent previous scan for a URL."""
    conn = _db()
    row = conn.execute("""
        SELECT violation_ids, full_result, scanned_at, score
        FROM scan_snapshots
        WHERE url = ?
        ORDER BY scanned_at DESC
        LIMIT 1 OFFSET 1
    """, (url,)).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "violation_ids": json.loads(row[0] or "[]"),
        "full_result":   json.loads(row[1] or "{}"),
        "scanned_at":    row[2],
        "score":         row[3],
    }


def get_latest_snapshot(url: str) -> dict | None:
    """Get the current (latest) scan snapshot."""
    conn = _db()
    row = conn.execute("""
        SELECT violation_ids, full_result, scanned_at, score
        FROM scan_snapshots
        WHERE url = ?
        ORDER BY scanned_at DESC
        LIMIT 1
    """, (url,)).fetchone()
    conn.close()
    if not row:
        return None
    return {
        "violation_ids": json.loads(row[0] or "[]"),
        "full_result":   json.loads(row[1] or "{}"),
        "scanned_at":    row[2],
        "score":         row[3],
    }


def get_history(url: str, limit: int = 20) -> list:
    """Get scan history for trend chart."""
    conn = _db()
    rows = conn.execute("""
        SELECT score, failures, eaa_risk, scanned
        FROM scan_history
        WHERE url = ?
        ORDER BY scanned DESC
        LIMIT ?
    """, (url, limit)).fetchall()
    conn.close()
    return [{"score": r[0], "failures": r[1], "eaa_risk": r[2], "scanned": r[3]} for r in rows]


def get_all_tracked_urls() -> list:
    """Get all URLs that have been scanned."""
    conn = _db()
    rows = conn.execute("""
        SELECT DISTINCT url, MAX(scanned) as last_scan,
               COUNT(*) as scan_count
        FROM scan_history
        GROUP BY url
        ORDER BY last_scan DESC
    """).fetchall()
    conn.close()
    return [{"url": r[0], "last_scan": r[1], "scan_count": r[2]} for r in rows]


def compare_scans(current_result: dict, previous_snapshot: dict | None) -> dict:
    """
    Compare current scan against previous snapshot.
    Returns NEW / EXISTING / FIXED classification.
    """
    current_violations = {
        r["id"]: r
        for r in current_result.get("rules", [])
        if r.get("status") == "fail"
    }

    if not previous_snapshot:
        return {
            "has_previous":  False,
            "new":           list(current_violations.values()),
            "existing":      [],
            "fixed":         [],
            "new_count":     len(current_violations),
            "existing_count":0,
            "fixed_count":   0,
            "previous_scan": None,
        }

    prev_violation_ids = set(previous_snapshot.get("violation_ids", []))
    current_ids        = set(current_violations.keys())

    new_ids      = current_ids - prev_violation_ids
    existing_ids = current_ids & prev_violation_ids
    fixed_ids    = prev_violation_ids - current_ids

    # Get rule details for fixed items from previous snapshot
    prev_rules = {
        r["id"]: r
        for r in previous_snapshot.get("full_result", {}).get("rules", [])
        if r.get("status") == "fail"
    }

    return {
        "has_previous":   True,
        "previous_scan":  previous_snapshot.get("scanned_at"),
        "previous_score": previous_snapshot.get("score"),
        "new":            [current_violations[i] for i in new_ids],
        "existing":       [current_violations[i] for i in existing_ids],
        "fixed":          [prev_rules.get(i, {"id": i, "name": i}) for i in fixed_ids],
        "new_count":      len(new_ids),
        "existing_count": len(existing_ids),
        "fixed_count":    len(fixed_ids),
    }

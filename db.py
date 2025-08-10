from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from typing import Dict, Iterable, List, Optional

DB_PATH = "meds.sqlite3"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS meds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                dosage TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                frequency TEXT NOT NULL CHECK(frequency IN ('daily','every_other_day')),
                start_date TEXT NOT NULL,
                slots TEXT NOT NULL
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS intakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                med_id INTEGER NOT NULL,
                day TEXT NOT NULL,
                slot_id TEXT NOT NULL,
                taken_at TEXT NOT NULL,
                UNIQUE(med_id, day, slot_id),
                FOREIGN KEY(med_id) REFERENCES meds(id) ON DELETE CASCADE
            );
            """
        )


def _slots_to_str(slots: Iterable[str]) -> str:
    return ",".join(sorted(slots))


def _slots_from_str(slots_str: str) -> List[str]:
    if not slots_str:
        return []
    return [s for s in slots_str.split(",") if s]


def add_med(*, name: str, dosage: str, notes: str, frequency: str, start_date: str, slots: Iterable[str]) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO meds(name, dosage, notes, frequency, start_date, slots) VALUES (?, ?, ?, ?, ?, ?)",
            (name, dosage, notes, frequency, start_date, _slots_to_str(slots)),
        )
        return int(cur.lastrowid)


def update_med(*, med_id: int, name: str, dosage: str, notes: str, frequency: str, start_date: str, slots: Iterable[str]) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE meds SET name=?, dosage=?, notes=?, frequency=?, start_date=?, slots=? WHERE id=?",
            (name, dosage, notes, frequency, start_date, _slots_to_str(slots), med_id),
        )


def delete_med(med_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM meds WHERE id=?", (med_id,))
        conn.execute("DELETE FROM intakes WHERE med_id=?", (med_id,))


def list_meds() -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM meds ORDER BY name COLLATE NOCASE").fetchall()
    meds: List[Dict] = []
    for r in rows:
        meds.append({
            "id": r["id"],
            "name": r["name"],
            "dosage": r["dosage"],
            "notes": r["notes"],
            "frequency": r["frequency"],
            "start_date": r["start_date"],
            "slots": _slots_from_str(r["slots"]),
        })
    return meds


def get_med(med_id: int) -> Optional[Dict]:
    with get_conn() as conn:
        r = conn.execute("SELECT * FROM meds WHERE id=?", (med_id,)).fetchone()
    if not r:
        return None
    return {
        "id": r["id"],
        "name": r["name"],
        "dosage": r["dosage"],
        "notes": r["notes"],
        "frequency": r["frequency"],
        "start_date": r["start_date"],
        "slots": _slots_from_str(r["slots"]),
    }


def is_med_due_today(med: Dict, day: date) -> bool:
    if med["frequency"] == "daily":
        return True
    if med["frequency"] == "every_other_day":
        try:
            start = date.fromisoformat(med["start_date"]) if med["start_date"] else day
        except Exception:
            start = day
        delta_days = (day - start).days
        return delta_days % 2 == 0
    return True


def record_intake(med_id: int, day_iso: str, slot_id: str) -> None:
    """Upsert an intake record for the given day and slot."""
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO intakes(med_id, day, slot_id, taken_at) VALUES (?, ?, ?, ?)",
            (med_id, day_iso, slot_id, now),
        )


def get_intake(med_id: int, day_iso: str, slot_id: str) -> Optional[Dict]:
    with get_conn() as conn:
        r = conn.execute(
            "SELECT * FROM intakes WHERE med_id=? AND day=? AND slot_id=?",
            (med_id, day_iso, slot_id),
        ).fetchone()
    if not r:
        return None
    return {
        "id": r["id"],
        "med_id": r["med_id"],
        "day": r["day"],
        "slot_id": r["slot_id"],
        "taken_at": r["taken_at"],
    }


def delete_intake(med_id: int, day_iso: str, slot_id: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM intakes WHERE med_id=? AND day=? AND slot_id=?",
            (med_id, day_iso, slot_id),
        )
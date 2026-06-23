import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "tts.db")


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                model_name TEXT NOT NULL,
                speaker_id INTEGER DEFAULT 0,
                speed REAL DEFAULT 1.0,
                status TEXT NOT NULL DEFAULT 'pending',
                output_file TEXT,
                error_msg TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def create_job(job_id: str, text: str, model_name: str, speaker_id: int, speed: float, now: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO jobs (id, text, model_name, speaker_id, speed, status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)""",
            (job_id, text, model_name, speaker_id, speed, now, now),
        )
        conn.commit()


def get_job(job_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None


def list_jobs(limit: int = 50):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def update_job_status(job_id: str, status: str, now: str, output_file: str = None, error_msg: str = None):
    with get_conn() as conn:
        conn.execute(
            """UPDATE jobs SET status = ?, output_file = ?, error_msg = ?, updated_at = ?
               WHERE id = ?""",
            (status, output_file, error_msg, now, job_id),
        )
        conn.commit()


def get_pending_job():
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


def delete_job(job_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT output_file FROM jobs WHERE id = ?", (job_id,)).fetchone()
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
        conn.commit()
        return dict(row)["output_file"] if row else None

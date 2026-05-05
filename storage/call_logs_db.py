import uuid
from datetime import datetime, date, timedelta
from typing import Optional

import psycopg2.extras
from .base_db import get_conn, _row_to_dict, rows_to_dicts
from .call_logs import CALL_OUTCOMES


def get_all() -> list:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM call_logs ORDER BY created_at")
            return rows_to_dicts(cur.fetchall())


def get_by_company(company_id: str) -> list:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM call_logs WHERE company_id = %s ORDER BY created_at DESC",
                (company_id,),
            )
            return rows_to_dicts(cur.fetchall())


def create(company_id: str, agent_id: str, **kwargs) -> dict:
    log_id = str(uuid.uuid4())
    now = datetime.utcnow()
    call_date = kwargs.get("callDate", now)
    follow_up = kwargs.get("followUpDate")

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO call_logs
                    (id, company_id, agent_id, contact_id, call_date, outcome, notes, follow_up_date, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    log_id, company_id, agent_id,
                    kwargs.get("contactId") or None,
                    call_date, kwargs.get("outcome", "OTHER"),
                    kwargs.get("notes", ""),
                    follow_up or None,
                    now,
                ),
            )
            return _row_to_dict(cur.fetchone())


def get_queue_for_agent(agent_id: str) -> dict:
    today = date.today()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT DISTINCT ON (cl.company_id)
                    c.*,
                    cl.follow_up_date,
                    cl.notes AS last_note
                FROM call_logs cl
                JOIN companies c ON c.id = cl.company_id
                WHERE cl.follow_up_date IS NOT NULL
                  AND c.assigned_agent_id = %s
                ORDER BY cl.company_id, cl.created_at DESC
                """,
                (agent_id,),
            )
            rows = cur.fetchall()

    queue: dict = {"missed": [], "today": [], "tomorrow": []}
    for row in rows:
        fu_date = row["follow_up_date"]
        if isinstance(fu_date, str):
            fu_date = date.fromisoformat(fu_date)
        item = {**_row_to_dict(row)}
        if fu_date <= yesterday:
            queue["missed"].append(item)
        elif fu_date == today:
            queue["today"].append(item)
        elif fu_date == tomorrow:
            queue["tomorrow"].append(item)
    return queue


def get_daily_stats(target_date: str) -> dict:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT agent_id::text, outcome, COUNT(*) AS cnt
                FROM call_logs
                WHERE call_date::date = %s
                GROUP BY agent_id, outcome
                """,
                (target_date,),
            )
            rows = cur.fetchall()

    stats: dict = {}
    for row in rows:
        aid = str(row["agent_id"])
        if aid not in stats:
            stats[aid] = {"total": 0, "outcomes": {}}
        stats[aid]["outcomes"][row["outcome"]] = int(row["cnt"])
        stats[aid]["total"] += int(row["cnt"])
    return stats


def get_weekly_stats(week_start: str) -> dict:
    start = date.fromisoformat(week_start)
    end = start + timedelta(days=6)

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT agent_id::text, call_date::date AS day, COUNT(*) AS cnt
                FROM call_logs
                WHERE call_date::date BETWEEN %s AND %s
                GROUP BY agent_id, call_date::date
                """,
                (start, end),
            )
            rows = cur.fetchall()

    stats: dict = {}
    for row in rows:
        aid = str(row["agent_id"])
        day = row["day"].isoformat() if hasattr(row["day"], "isoformat") else str(row["day"])
        if aid not in stats:
            stats[aid] = {"total": 0, "by_day": {}}
        stats[aid]["by_day"][day] = int(row["cnt"])
        stats[aid]["total"] += int(row["cnt"])
    return stats

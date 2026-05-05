import uuid
from datetime import datetime
from typing import Optional

import psycopg2.extras
from .base_db import get_conn, _row_to_dict, rows_to_dicts


def get_all() -> list:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM agent_history ORDER BY start_date")
            return rows_to_dicts(cur.fetchall())


def get_by_company(company_id: str) -> list:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM agent_history WHERE company_id = %s ORDER BY start_date DESC",
                (company_id,),
            )
            return rows_to_dicts(cur.fetchall())


def get_by_agent(agent_id: str) -> list:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM agent_history WHERE agent_id = %s ORDER BY start_date DESC",
                (agent_id,),
            )
            return rows_to_dicts(cur.fetchall())


def record_assignment(company_id: str, agent_id: str, reason: str = "initial") -> dict:
    now = datetime.utcnow()
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Close any open assignment for this company
            cur.execute(
                """
                UPDATE agent_history SET end_date = %s
                WHERE company_id = %s AND end_date IS NULL
                """,
                (now, company_id),
            )
            # Open a new one
            cur.execute(
                """
                INSERT INTO agent_history (id, company_id, agent_id, start_date, end_date, reason)
                VALUES (%s, %s, %s, %s, NULL, %s)
                RETURNING *
                """,
                (str(uuid.uuid4()), company_id, agent_id, now, reason),
            )
            return _row_to_dict(cur.fetchone())


def close_assignment(company_id: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE agent_history SET end_date = %s WHERE company_id = %s AND end_date IS NULL",
                (datetime.utcnow(), company_id),
            )

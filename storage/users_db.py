import uuid
from datetime import datetime
from typing import Optional

import psycopg2.extras
from .base_db import get_conn, _row_to_dict, rows_to_dicts


def get_all() -> list:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM users ORDER BY created_at")
            return rows_to_dicts(cur.fetchall())


def get_active_agents() -> list:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM users WHERE is_active = TRUE AND role = 'agent' ORDER BY name"
            )
            return rows_to_dicts(cur.fetchall())


def get_by_id(user_id: str) -> Optional[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return _row_to_dict(cur.fetchone())


def get_by_agent_id(agent_id: str) -> Optional[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE lower(agent_id) = %s", (agent_id.strip().lower(),))
            return _row_to_dict(cur.fetchone())


def get_by_email(email: str) -> Optional[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email.strip().lower(),))
            return _row_to_dict(cur.fetchone())


def create(name: str, email: str, password_hash: str, role: str = "agent", **kwargs) -> dict:
    now = datetime.utcnow()
    user_id = str(uuid.uuid4())
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO users (id, name, email, password_hash, role, is_active, agent_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    user_id, name.strip(), email.strip().lower(), password_hash,
                    role, kwargs.get("isActive", True), kwargs.get("agentId"),
                    now, now,
                ),
            )
            return _row_to_dict(cur.fetchone())


def update(user_id: str, **kwargs) -> Optional[dict]:
    allowed = {"name", "email", "passwordHash", "role", "isActive", "agentId"}
    col_map = {
        "name": "name", "email": "email", "passwordHash": "password_hash",
        "role": "role", "isActive": "is_active", "agentId": "agent_id",
    }
    sets, vals = [], []
    for k, v in kwargs.items():
        if k in allowed:
            sets.append(f"{col_map[k]} = %s")
            vals.append(v)
    if not sets:
        return get_by_id(user_id)
    sets.append("updated_at = %s")
    vals.append(datetime.utcnow())
    vals.append(user_id)
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"UPDATE users SET {', '.join(sets)} WHERE id = %s RETURNING *", vals
            )
            return _row_to_dict(cur.fetchone())


def delete(user_id: str) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            return cur.rowcount > 0

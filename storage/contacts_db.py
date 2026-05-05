import uuid
from datetime import datetime
from typing import Optional

import psycopg2.extras
from .base_db import get_conn, _row_to_dict, rows_to_dicts


def get_all() -> list:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM contacts ORDER BY created_at")
            return rows_to_dicts(cur.fetchall())


def get_by_company(company_id: str) -> list:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM contacts WHERE company_id = %s ORDER BY is_primary DESC, created_at",
                (company_id,),
            )
            return rows_to_dicts(cur.fetchall())


def get_by_id(contact_id: str) -> Optional[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM contacts WHERE id = %s", (contact_id,))
            return _row_to_dict(cur.fetchone())


def create(company_id: str, name: str, **kwargs) -> dict:
    contact_id = str(uuid.uuid4())
    phones = kwargs.get("phones", [])
    if isinstance(phones, str):
        phones = [phones] if phones else []

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO contacts (id, company_id, name, designation, email, phones, is_primary, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    contact_id, company_id, name.strip(),
                    (kwargs.get("designation") or "").strip(),
                    (kwargs.get("email") or "").strip(),
                    phones,
                    kwargs.get("isPrimary", False),
                    datetime.utcnow(),
                ),
            )
            return _row_to_dict(cur.fetchone())


def update(contact_id: str, **kwargs) -> Optional[dict]:
    col_map = {
        "name": "name", "designation": "designation", "email": "email",
        "phones": "phones", "isPrimary": "is_primary",
    }
    sets, vals = [], []
    for k, v in kwargs.items():
        if k in col_map:
            sets.append(f"{col_map[k]} = %s")
            vals.append(v)
    if not sets:
        return get_by_id(contact_id)
    vals.append(contact_id)
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"UPDATE contacts SET {', '.join(sets)} WHERE id = %s RETURNING *", vals
            )
            return _row_to_dict(cur.fetchone())


def delete(contact_id: str) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM contacts WHERE id = %s", (contact_id,))
            return cur.rowcount > 0

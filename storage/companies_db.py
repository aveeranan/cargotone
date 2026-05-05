import uuid
import re
import random
from datetime import datetime
from typing import Optional

import psycopg2.extras
from .base_db import get_conn, _row_to_dict, rows_to_dicts
from .companies import STATUSES, PRODUCT_LIST, _trim_str, _trim_list, _generate_key


def get_all() -> list:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM companies ORDER BY updated_at DESC, created_at DESC")
            return rows_to_dicts(cur.fetchall())


def get_by_id(company_id: str) -> Optional[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM companies WHERE id = %s", (company_id,))
            return _row_to_dict(cur.fetchone())


def get_by_name(name: str) -> Optional[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM companies WHERE LOWER(name) = %s", (name.strip().lower(),))
            return _row_to_dict(cur.fetchone())


def get_by_agent(agent_id: str) -> list:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM companies WHERE assigned_agent_id = %s ORDER BY updated_at DESC",
                (agent_id,),
            )
            return rows_to_dicts(cur.fetchall())


def search(query: str = "", status: str = "", agent_id: str = "", city: str = "") -> list:
    conditions = ["1=1"]
    params = []

    if query:
        q = f"%{query.lower()}%"
        conditions.append(
            "(LOWER(name) LIKE %s OR LOWER(address1) LIKE %s OR LOWER(address2) LIKE %s"
            " OR LOWER(website) LIKE %s OR LOWER(company_key) LIKE %s"
            " OR LOWER(super_company_key) LIKE %s"
            " OR EXISTS (SELECT 1 FROM unnest(goods_types) g WHERE LOWER(g) LIKE %s))"
        )
        params.extend([q, q, q, q, q, q, q])

    if status:
        conditions.append("status = %s")
        params.append(status)

    if agent_id:
        conditions.append("assigned_agent_id = %s")
        params.append(agent_id)

    if city:
        c = f"%{city.lower()}%"
        conditions.append("(LOWER(address1) LIKE %s OR LOWER(address2) LIKE %s)")
        params.extend([c, c])

    sql = (
        f"SELECT * FROM companies WHERE {' AND '.join(conditions)}"
        " ORDER BY updated_at DESC, created_at DESC"
    )
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return rows_to_dicts(cur.fetchall())


def create(name: str, **kwargs) -> dict:
    name = _trim_str(name)
    existing_keys = {r["companyKey"] for r in get_all() if r.get("companyKey")}
    company_key = _generate_key(name, existing_keys)
    now = datetime.utcnow()
    company_id = str(uuid.uuid4())

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO companies (
                    id, name, company_key, super_company_key, website, goods_types,
                    status, assigned_agent_id, address1, address2, business_type,
                    product, call_status, remarks, mode, shipment_type, country,
                    air_import_volume, air_export_volume, ocean_import_volume,
                    ocean_export_volume, created_at, updated_at
                ) VALUES (
                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                ) RETURNING *
                """,
                (
                    company_id, name, company_key, kwargs.get("superCompanyKey", company_key),
                    _trim_str(kwargs.get("website", "")),
                    _trim_list(kwargs.get("goodsTypes", [])),
                    kwargs.get("status", "new"),
                    kwargs.get("assignedAgentId") or None,
                    _trim_str(kwargs.get("address1", "")),
                    _trim_str(kwargs.get("address2", "")),
                    _trim_str(kwargs.get("businessType", "")),
                    _trim_str(kwargs.get("product", "")),
                    _trim_str(kwargs.get("callStatus", "")),
                    _trim_str(kwargs.get("remarks", "")),
                    _trim_str(kwargs.get("mode", "")),
                    _trim_str(kwargs.get("shipmentType", "")),
                    _trim_str(kwargs.get("country", "")),
                    _trim_str(kwargs.get("airImportVolume", "")),
                    _trim_str(kwargs.get("airExportVolume", "")),
                    _trim_str(kwargs.get("oceanImportVolume", "")),
                    _trim_str(kwargs.get("oceanExportVolume", "")),
                    now, now,
                ),
            )
            return _row_to_dict(cur.fetchone())


def update(company_id: str, **kwargs) -> Optional[dict]:
    col_map = {
        "name": "name", "website": "website", "goodsTypes": "goods_types",
        "status": "status", "assignedAgentId": "assigned_agent_id",
        "superCompanyKey": "super_company_key",
        "address1": "address1", "address2": "address2",
        "businessType": "business_type", "product": "product",
        "callStatus": "call_status", "remarks": "remarks",
        "mode": "mode", "shipmentType": "shipment_type", "country": "country",
        "airImportVolume": "air_import_volume", "airExportVolume": "air_export_volume",
        "oceanImportVolume": "ocean_import_volume", "oceanExportVolume": "ocean_export_volume",
    }
    sets, vals = [], []
    for k, v in kwargs.items():
        if k in col_map:
            sets.append(f"{col_map[k]} = %s")
            vals.append(_trim_list(v) if isinstance(v, list) else (_trim_str(v) if isinstance(v, str) else v))
    if not sets:
        return get_by_id(company_id)
    sets.append("updated_at = %s")
    vals.extend([datetime.utcnow(), company_id])
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"UPDATE companies SET {', '.join(sets)} WHERE id = %s RETURNING *", vals
            )
            return _row_to_dict(cur.fetchone())


def delete(company_id: str) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM companies WHERE id = %s", (company_id,))
            return cur.rowcount > 0

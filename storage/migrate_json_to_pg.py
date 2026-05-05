"""
Migrate existing JSON flat-files into PostgreSQL.

Usage:
    DATABASE_URL=postgresql://user:pass@host:5432/cargotone python -m storage.migrate_json_to_pg

Run storage/schema.sql first to create the tables.
"""

import json
import os
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras

DATA_DIR = Path(__file__).parent.parent / "data"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/cargotone")


def load(filename: str) -> list:
    path = DATA_DIR / filename
    if not path.exists():
        print(f"  [skip] {filename} not found")
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def migrate(conn):
    cur = conn.cursor()

    # ── users ────────────────────────────────────────────────────────────────
    users = load("users.json")
    print(f"Migrating {len(users)} users…")
    for u in users:
        cur.execute(
            """
            INSERT INTO users (id, name, email, password_hash, role, is_active, agent_id, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                u["id"], u["name"], u["email"], u["passwordHash"],
                u.get("role", "agent"), u.get("isActive", True),
                u.get("agentId"), u.get("createdAt"), u.get("updatedAt"),
            ),
        )
    print(f"  ✓ {len(users)} users inserted (duplicates skipped)")

    # ── companies ────────────────────────────────────────────────────────────
    companies = load("companies.json")
    print(f"Migrating {len(companies)} companies…")
    for c in companies:
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
            )
            ON CONFLICT (id) DO NOTHING
            """,
            (
                c["id"], c["name"],
                c.get("companyKey"), c.get("superCompanyKey"),
                c.get("website", ""),
                c.get("goodsTypes", []),
                c.get("status", "new"),
                c.get("assignedAgentId") or None,
                c.get("address1", ""), c.get("address2", ""),
                c.get("businessType", ""), c.get("product", ""),
                c.get("callStatus", ""), c.get("remarks", ""),
                c.get("mode", ""), c.get("shipmentType", ""),
                c.get("country", ""),
                c.get("airImportVolume", ""), c.get("airExportVolume", ""),
                c.get("oceanImportVolume", ""), c.get("oceanExportVolume", ""),
                c.get("createdAt"), c.get("updatedAt"),
            ),
        )
    print(f"  ✓ {len(companies)} companies inserted (duplicates skipped)")

    # ── contacts ─────────────────────────────────────────────────────────────
    contacts = load("contacts.json")
    print(f"Migrating {len(contacts)} contacts…")
    for ct in contacts:
        phones = ct.get("phones", [])
        if isinstance(phones, str):
            phones = [phones] if phones else []
        cur.execute(
            """
            INSERT INTO contacts (id, company_id, name, designation, email, phones, is_primary, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                ct["id"], ct["companyId"], ct["name"],
                ct.get("designation", ""), ct.get("email", ""),
                phones, ct.get("isPrimary", False), ct.get("createdAt"),
            ),
        )
    print(f"  ✓ {len(contacts)} contacts inserted (duplicates skipped)")

    # ── call_logs ────────────────────────────────────────────────────────────
    logs = load("call_logs.json")
    print(f"Migrating {len(logs)} call logs…")
    for lg in logs:
        cur.execute(
            """
            INSERT INTO call_logs (id, company_id, agent_id, contact_id, call_date, outcome, notes, follow_up_date, created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                lg["id"], lg["companyId"], lg["agentId"],
                lg.get("contactId") or None,
                lg.get("callDate"), lg.get("outcome", "OTHER"),
                lg.get("notes", ""), lg.get("followUpDate") or None,
                lg.get("createdAt"),
            ),
        )
    print(f"  ✓ {len(logs)} call logs inserted (duplicates skipped)")

    # ── agent_history ─────────────────────────────────────────────────────────
    history = load("agent_history.json")
    print(f"Migrating {len(history)} agent history records…")
    for h in history:
        cur.execute(
            """
            INSERT INTO agent_history (id, company_id, agent_id, start_date, end_date, reason)
            VALUES (%s,%s,%s,%s,%s,%s)
            ON CONFLICT (id) DO NOTHING
            """,
            (
                h["id"], h["companyId"], h["agentId"],
                h.get("startDate"), h.get("endDate") or None,
                h.get("reason", ""),
            ),
        )
    print(f"  ✓ {len(history)} agent history records inserted (duplicates skipped)")

    conn.commit()
    cur.close()


if __name__ == "__main__":
    print(f"Connecting to {DATABASE_URL.split('@')[-1]}…")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        psycopg2.extras.register_uuid()
    except psycopg2.OperationalError as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    try:
        migrate(conn)
        print("\nMigration complete.")
    except Exception as e:
        conn.rollback()
        print(f"\nMigration failed: {e}")
        sys.exit(1)
    finally:
        conn.close()

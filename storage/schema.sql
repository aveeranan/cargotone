-- CargoTone CRM — PostgreSQL schema
-- Run once: psql $DATABASE_URL -f storage/schema.sql

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT        NOT NULL,
    email           TEXT        UNIQUE NOT NULL,
    password_hash   TEXT        NOT NULL,
    role            TEXT        NOT NULL DEFAULT 'agent',
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    agent_id        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS companies (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name                 TEXT        NOT NULL,
    company_key          TEXT,
    super_company_key    TEXT,
    website              TEXT        NOT NULL DEFAULT '',
    goods_types          TEXT[]      NOT NULL DEFAULT '{}',
    status               TEXT        NOT NULL DEFAULT 'new',
    assigned_agent_id    UUID        REFERENCES users(id) ON DELETE SET NULL,
    address1             TEXT        NOT NULL DEFAULT '',
    address2             TEXT        NOT NULL DEFAULT '',
    business_type        TEXT        NOT NULL DEFAULT '',
    product              TEXT        NOT NULL DEFAULT '',
    call_status          TEXT        NOT NULL DEFAULT '',
    remarks              TEXT        NOT NULL DEFAULT '',
    mode                 TEXT        NOT NULL DEFAULT '',
    shipment_type        TEXT        NOT NULL DEFAULT '',
    country              TEXT        NOT NULL DEFAULT '',
    air_import_volume    TEXT        NOT NULL DEFAULT '',
    air_export_volume    TEXT        NOT NULL DEFAULT '',
    ocean_import_volume  TEXT        NOT NULL DEFAULT '',
    ocean_export_volume  TEXT        NOT NULL DEFAULT '',
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS contacts (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id  UUID        NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name        TEXT        NOT NULL,
    designation TEXT        NOT NULL DEFAULT '',
    email       TEXT        NOT NULL DEFAULT '',
    phones      TEXT[]      NOT NULL DEFAULT '{}',
    is_primary  BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS call_logs (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id     UUID        NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    agent_id       UUID        NOT NULL REFERENCES users(id),
    contact_id     UUID        REFERENCES contacts(id) ON DELETE SET NULL,
    call_date      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    outcome        TEXT        NOT NULL DEFAULT 'OTHER',
    notes          TEXT        NOT NULL DEFAULT '',
    follow_up_date DATE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_history (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id  UUID        NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    agent_id    UUID        NOT NULL REFERENCES users(id),
    start_date  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_date    TIMESTAMPTZ,
    reason      TEXT        NOT NULL DEFAULT ''
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_companies_agent   ON companies(assigned_agent_id);
CREATE INDEX IF NOT EXISTS idx_companies_status  ON companies(status);
CREATE INDEX IF NOT EXISTS idx_contacts_company  ON contacts(company_id);
CREATE INDEX IF NOT EXISTS idx_call_logs_company ON call_logs(company_id);
CREATE INDEX IF NOT EXISTS idx_call_logs_agent   ON call_logs(agent_id);
CREATE INDEX IF NOT EXISTS idx_call_logs_date    ON call_logs(call_date);
CREATE INDEX IF NOT EXISTS idx_agent_history_co  ON agent_history(company_id);

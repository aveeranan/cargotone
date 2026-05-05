# CargoTone CRM

A lightweight CRM built for freight-forwarding sales teams. Agents manage company leads, log calls, track follow-ups, and report daily/weekly activity. Admins get full visibility across all agents plus reporting dashboards.

Built with **FastAPI** + **Jinja2** templates and a flat-file JSON store by default, with a ready-to-use **PostgreSQL** storage layer to switch to when you need it.

---

## Features

| Area | Capability |
|---|---|
| **Companies** | Add (single or bulk paste), edit, delete, search, filter by status / agent / country |
| **Contacts** | Up to 2 contacts per company (name, phone, email), primary contact flag |
| **Call Logging** | Log outcomes against 27 predefined statuses, set follow-up dates |
| **Follow-up Queue** | Dashboard queue split into Missed / Today / Tomorrow |
| **Reports** | Daily breakdown per agent (grouped outcomes), weekly totals, 8-week trend charts per agent and company-wide |
| **Agents** | Admin can create/deactivate agents, reassign company portfolios |
| **Roles** | `admin` — full access; `agent` — sees only their own companies |
| **Auth** | JWT via HTTP-only cookie, bcrypt password hashing |

---

## File Structure

```
cargotone/
│
├── main.py                     # FastAPI app entry point, startup seed
├── config.py                   # JWT config, loaded from .env
├── auth.py                     # Password hashing, JWT encode/decode
├── dependencies.py             # require_auth / require_admin FastAPI deps
├── app_templates.py            # Jinja2 template engine setup
├── requirements.txt
├── .env                        # Secrets (not committed)
├── .gitignore
│
├── routers/                    # One file per feature area
│   ├── auth.py                 # Login, logout, change-password
│   ├── companies.py            # Company CRUD + bulk import API
│   ├── contacts.py             # Contact CRUD
│   ├── calls.py                # Call log creation
│   ├── agents.py               # Agent management (admin only)
│   └── reports.py              # Daily / weekly / trends / company reports
│
├── storage/                    # Data access layer
│   ├── base.py                 # JSON flat-file read/write with thread locks
│   ├── companies.py            # JSON-backed company store
│   ├── contacts.py             # JSON-backed contact store
│   ├── call_logs.py            # JSON-backed call log store
│   ├── users.py                # JSON-backed user store
│   ├── agent_history.py        # JSON-backed agent assignment history
│   │
│   ├── base_db.py              # PostgreSQL connection pool + row helpers
│   ├── companies_db.py         # PostgreSQL-backed company store
│   ├── contacts_db.py          # PostgreSQL-backed contact store
│   ├── call_logs_db.py         # PostgreSQL-backed call log store
│   ├── users_db.py             # PostgreSQL-backed user store
│   ├── agent_history_db.py     # PostgreSQL-backed agent history store
│   │
│   ├── schema.sql              # CREATE TABLE statements (run once)
│   └── migrate_json_to_pg.py   # One-time JSON → PostgreSQL migration script
│
├── templates/                  # Jinja2 HTML templates
│   ├── base.html               # Shared layout (navbar, toasts, JS libs)
│   ├── login.html
│   ├── dashboard.html          # Follow-up queue + summary cards
│   ├── change_password.html
│   ├── site_visit.html         # Site-visit planner view
│   ├── companies/
│   │   ├── list.html           # Company list, filters, bulk import
│   │   └── detail.html         # Company detail, call log, contacts, edit
│   ├── agents/
│   │   └── list.html           # Agent list (admin)
│   └── reports/
│       └── index.html          # Daily / weekly / trends / company tabs
│
├── static/
│   └── css/custom.css          # App-wide custom styles
│
└── data/                       # Runtime flat-file DB (not committed)
    ├── users.json
    ├── companies.json
    ├── contacts.json
    ├── call_logs.json
    └── agent_history.json
```

---

## Table Structure (PostgreSQL)

> Only relevant when using the `*_db.py` storage layer.  
> Run `storage/schema.sql` to create all tables and indexes.

### `users`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `name` | TEXT | |
| `email` | TEXT UNIQUE | Used as login username |
| `password_hash` | TEXT | bcrypt |
| `role` | TEXT | `admin` or `agent` |
| `is_active` | BOOLEAN | Soft disable |
| `agent_id` | TEXT | Optional short agent code |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

### `companies`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `name` | TEXT | |
| `company_key` | TEXT | Auto-generated short key (e.g. `ACME-1234`) |
| `super_company_key` | TEXT | Parent group key |
| `website` | TEXT | |
| `goods_types` | TEXT[] | Array of product categories |
| `status` | TEXT | Pipeline stage (see status list below) |
| `assigned_agent_id` | UUID FK → users | |
| `address1` | TEXT | Location 1 |
| `address2` | TEXT | Location 2 |
| `business_type` | TEXT | |
| `product` | TEXT | |
| `call_status` | TEXT | |
| `remarks` | TEXT | |
| `mode` | TEXT | `AIR`, `OCEAN`, `LAND`, etc. |
| `shipment_type` | TEXT | e.g. `IA_IMP_AIR`, `EL_EXP_LCL` |
| `country` | TEXT | ISO 3166-1 alpha-2 code |
| `air_import_volume` | TEXT | |
| `air_export_volume` | TEXT | |
| `ocean_import_volume` | TEXT | |
| `ocean_export_volume` | TEXT | |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | Drives default sort order |

### `contacts`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `company_id` | UUID FK → companies | Cascades on delete |
| `name` | TEXT | |
| `designation` | TEXT | e.g. Manager, Director |
| `email` | TEXT | |
| `phones` | TEXT[] | Array of phone numbers |
| `is_primary` | BOOLEAN | |
| `created_at` | TIMESTAMPTZ | |

### `call_logs`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `company_id` | UUID FK → companies | Cascades on delete |
| `agent_id` | UUID FK → users | |
| `contact_id` | UUID FK → contacts | Nullable |
| `call_date` | TIMESTAMPTZ | |
| `outcome` | TEXT | One of 27 predefined outcomes |
| `notes` | TEXT | |
| `follow_up_date` | DATE | Nullable |
| `created_at` | TIMESTAMPTZ | |

### `agent_history`
| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `company_id` | UUID FK → companies | Cascades on delete |
| `agent_id` | UUID FK → users | |
| `start_date` | TIMESTAMPTZ | When this agent was assigned |
| `end_date` | TIMESTAMPTZ | Nullable — open if NULL |
| `reason` | TEXT | `initial`, `transfer`, `split` |

---

## Installation & Setup

### Prerequisites
- Python 3.11+
- pip
- (Optional) PostgreSQL 14+ if using the `*_db.py` storage layer

### 1. Clone the repository

```bash
git clone https://github.com/aveeranan/cargotone.git
cd cargotone
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

Copy the example and edit as needed:

```bash
cp .env.example .env
```

`.env` variables:

| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET` | `cargotone-dev-secret` | **Change this in production** |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/cargotone` | Only needed for PostgreSQL mode |

### 5. Run the app

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open **http://localhost:8000** in your browser.

On first startup the app automatically creates the `data/` directory, initialises empty JSON files, and seeds a default admin account:

| Field | Value |
|---|---|
| Email | `admin@cargotonelogistics.com` |
| Password | `Admin@123!` |

> **Change this password immediately after first login.**

---

## Switching to PostgreSQL

The JSON flat-file store works out of the box. When you're ready to move to PostgreSQL:

### 1. Create the database

```bash
createdb cargotone
```

### 2. Apply the schema

```bash
psql $DATABASE_URL -f storage/schema.sql
```

### 3. Migrate existing JSON data (optional)

If you already have data in the JSON files, run the migration script to load it into PostgreSQL:

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/cargotone \
  python -m storage.migrate_json_to_pg
```

### 4. Swap the imports in each router

In each file under `routers/`, change:

```python
import storage.companies as companies_store
import storage.contacts as contacts_store
import storage.call_logs as call_logs_store
import storage.users as users_store
import storage.agent_history as history_store
```

to:

```python
import storage.companies_db as companies_store
import storage.contacts_db as contacts_store
import storage.call_logs_db as call_logs_store
import storage.users_db as users_store
import storage.agent_history_db as history_store
```

All function signatures are identical between the JSON and PostgreSQL layers — no other code changes are needed.

---

## Company Pipeline Statuses

| Status | Meaning |
|---|---|
| `SUSPECT- ALL_CLIENTS` | Initial cold list |
| `PROSPECT- POSITIVE_FEEDBACK` | Showed interest |
| `APPROACH- ENQUIRY_SHARED` | Enquiry sent |
| `NEGOTIATION- RATES_DISCUSS_PAYMENT_DAYS` | In rate discussion |
| `CLOSURE- BUSINESS_START_SUPPORT` | Deal closing |
| `CNB- CALL_FOR_NEXT_BUSINESS` | Existing customer |
| `NOT_INTERESTED` | Dead lead |
| `OTHERS` / `OTHERS-*` | Various closed reasons |

## Call Outcomes (27 codes)

`EE_EXISTING_CLIENT` · `ES_ENQUIRY_SHARED` · `NA_NOT_ANSWER` · `NE_NUMBER_NOT_EXIST` · `NI_NOT_INTERESTED` · `NC_NO_CLEAR_FEEDBACK` · `CD_CALL_DISCONNECT` · `NN_NO_NUMBER` · `NW_NO_WEBSITE` · `BUSY` · `CM_CALL_ME_LATER` · `APPOINTMENT` · `PERMANENTLY_CLOSED` · `FRADULENT` · `PAYMENT_ISSUE` · `CONTRACT_YEARLY` · `CONTRACT_QUATERLY` · `CONTRACT_MNC` · `MANAGEMENT_DECISION_IS_FINAL` · `SOEF_SUPPORT_ONLY_EXISTING_FFF` · `RR_RECEPTION_REJECTION` · `SR_SECURITY_REJECTION` · `PS_PROFILE_SENT` · `UNKNOWN` · `NE_NEGOTIATION` · `CLOSURE` · `ORDER` · `OTHER`

In the daily report these are grouped into: **Positive** · **Engaged** · **Not Reached** · **Rejected** · **Other**

---

## Default Ports & URLs

| URL | Description |
|---|---|
| `http://localhost:8000` | App root (redirects to dashboard) |
| `http://localhost:8000/login` | Login page |
| `http://localhost:8000/dashboard` | Agent dashboard / follow-up queue |
| `http://localhost:8000/companies` | Company list |
| `http://localhost:8000/reports` | Reports (admin only) |
| `http://localhost:8000/agents` | Agent management (admin only) |

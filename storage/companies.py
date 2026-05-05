import uuid
import re
import random
from datetime import datetime
from typing import Optional
from .base import read_db, write_db

DB = "companies.json"

STATUSES = [
    "SUSPECT- ALL_CLIENTS",
    "PROSPECT- POSITIVE_FEEDBACK",
    "APPROACH- ENQUIRY_SHARED",
    "NEGOTIATION- RATES_DISCUSS_PAYMENT_DAYS",
    "CLOSURE- BUSINESS_START_SUPPORT",
    "CNB- CALL_FOR_NEXT_BUSINESS",
    "OTHERS",
    "NOT_INTERESTED",
    "OTHERS-NoNumber",
    "OTHERS-NoWebsite",
    "OTHERS-PERMANENTLY_CLOSED",
    "OTHERS-FRADULENT",
    "OTHERS-PAYMENT_ISSUE",
    "OTHERS-CONTRACT_MNC",
    "OTHERS-MANAGEMENT_DECISION_IS_FINAL",
    "OTHERS-SOEF_SUPPORT_ONLY_EXISTING_FFF",
]

PRODUCT_LIST = [
    "AGRICULTURE & ALLIED INDUSTRIES",
    "AUTO COMPONENTS & MANUFACTURING",
    "AVIATION & AEROSPACE",
    "BANKING, FINANCIAL SERVICES, & INSURANCE (BFSI)",
    "BIOTECHNOLOGY & PHARMACEUTICALS",
    "CHEMICALS & PETROCHEMICALS",
    "CONSTRUCTION & REAL ESTATE",
    "CONSUMER DURABLES & FMCG (FAST MOVING CONSUMER GOODS)",
    "DEFENCE MANUFACTURING",
    "E-COMMERCE & RETAIL",
    "EDUCATION & TRAINING",
    "ELECTRIC VEHICLES (EV) & COMPONENTS",
    "ELECTRONICS SYSTEM DESIGN & MANUFACTURING",
    "ENGINEERING & CAPITAL GOODS",
    "ENTERTAINMENT & MEDIA",
    "FOOD PROCESSING & HOSPITALITY",
    "HEALTHCARE & MEDICAL DEVICES",
    "IT & BPM (INFORMATION TECHNOLOGY & BUSINESS PROCESS MANAGEMENT)",
    "MANUFACTURING (GENERAL)",
    "METALS & MINING",
    "OIL & GAS",
    "PAPER & PACKAGING",
    "PORTS & SHIPPING",
    "POWER & RENEWABLE ENERGY",
    "ROADS & INFRASTRUCTURE",
    "SCIENCE & TECHNOLOGY",
    "TELECOMMUNICATIONS",
    "TEXTILES & APPAREL",
    "TOURISM & HOSPITALITY",
    "OTHERS",
]


def _trim_str(value) -> str:
    return value.strip() if isinstance(value, str) else (value or "")


def _trim_list(value) -> list:
    if isinstance(value, list):
        return [v.strip() for v in value if isinstance(v, str) and v.strip()]
    return []


def _generate_key(name: str, existing_keys: set) -> str:
    letters = re.sub(r"[^A-Z0-9]", "", name.upper())[:4].ljust(4, "X")
    for _ in range(200):
        key = f"{letters}-{random.randint(1000, 9999)}"
        if key not in existing_keys:
            return key
    return str(uuid.uuid4())[:8].upper()


def get_all() -> list:
    return read_db(DB)


def get_by_id(company_id: str) -> Optional[dict]:
    return next((c for c in get_all() if c["id"] == company_id), None)


def get_by_name(name: str) -> Optional[dict]:
    name_lower = name.strip().lower()
    return next((c for c in get_all() if c["name"].lower() == name_lower), None)


def get_by_agent(agent_id: str) -> list:
    return [c for c in get_all() if c.get("assignedAgentId") == agent_id]


def search(query: str = "", status: str = "", agent_id: str = "", city: str = "") -> list:
    items = get_all()
    if query:
        q = query.lower()
        items = [
            c for c in items
            if q in c.get("name", "").lower()
            or q in c.get("address1", "").lower()
            or q in c.get("address2", "").lower()
            or q in " ".join(c.get("goodsTypes", [])).lower()
            or q in c.get("website", "").lower()
            or q in c.get("companyKey", "").lower()
            or q in c.get("superCompanyKey", "").lower()
        ]
    if status:
        items = [c for c in items if c.get("status") == status]
    if agent_id:
        items = [c for c in items if c.get("assignedAgentId") == agent_id]
    if city:
        items = [c for c in items if city.lower() in c.get("address1", "").lower()
                 or city.lower() in c.get("address2", "").lower()]
    return sorted(items, key=lambda c: max(c.get("updatedAt", ""), c.get("createdAt", "")), reverse=True)


def create(name: str, **kwargs) -> dict:
    name = _trim_str(name)
    companies = get_all()
    existing_keys = {c.get("companyKey", "") for c in companies}
    company_key = _generate_key(name, existing_keys)
    company = {
        "id": str(uuid.uuid4()),
        "name": name,
        "companyKey": company_key,
        "superCompanyKey": company_key,
        "website": _trim_str(kwargs.get("website", "")),
        "goodsTypes": _trim_list(kwargs.get("goodsTypes", [])),
        "status": "new",
        "assignedAgentId": kwargs.get("assignedAgentId"),
        "address1": _trim_str(kwargs.get("address1", "")),
        "address2": _trim_str(kwargs.get("address2", "")),
        "businessType": _trim_str(kwargs.get("businessType", "")),
        "product": _trim_str(kwargs.get("product", "")),
        "callStatus": _trim_str(kwargs.get("callStatus", "")),
        "remarks": _trim_str(kwargs.get("remarks", "")),
        "mode": _trim_str(kwargs.get("mode", "")),
        "shipmentType": _trim_str(kwargs.get("shipmentType", "")),
        "country": _trim_str(kwargs.get("country", "")),
        "airImportVolume": _trim_str(kwargs.get("airImportVolume", "")),
        "airExportVolume": _trim_str(kwargs.get("airExportVolume", "")),
        "oceanImportVolume": _trim_str(kwargs.get("oceanImportVolume", "")),
        "oceanExportVolume": _trim_str(kwargs.get("oceanExportVolume", "")),
        "createdAt": datetime.utcnow().isoformat(),
        "updatedAt": datetime.utcnow().isoformat(),
    }
    companies.append(company)
    write_db(DB, companies)
    return company


def update(company_id: str, **kwargs) -> Optional[dict]:
    companies = get_all()
    for c in companies:
        if c["id"] == company_id:
            for key, val in kwargs.items():
                if isinstance(val, str):
                    c[key] = val.strip()
                elif isinstance(val, list):
                    c[key] = _trim_list(val)
                else:
                    c[key] = val
            c["updatedAt"] = datetime.utcnow().isoformat()
            write_db(DB, companies)
            return c
    return None


def delete(company_id: str) -> bool:
    companies = get_all()
    filtered = [c for c in companies if c["id"] != company_id]
    if len(filtered) == len(companies):
        return False
    write_db(DB, filtered)
    return True

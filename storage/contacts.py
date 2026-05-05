import uuid
from datetime import datetime
from typing import Optional
from .base import read_db, write_db

DB = "contacts.json"


def get_all() -> list:
    return read_db(DB)


def get_by_company(company_id: str) -> list:
    return [c for c in get_all() if c["companyId"] == company_id]


def get_by_id(contact_id: str) -> Optional[dict]:
    return next((c for c in get_all() if c["id"] == contact_id), None)


def create(company_id: str, name: str, **kwargs) -> dict:
    contacts = get_all()
    contact = {
        "id": str(uuid.uuid4()),
        "companyId": company_id,
        "name": name,
        "designation": kwargs.get("designation", ""),
        "email": kwargs.get("email", ""),
        "phones": kwargs.get("phones", []),
        "isPrimary": kwargs.get("isPrimary", False),
        "createdAt": datetime.utcnow().isoformat(),
    }
    contacts.append(contact)
    write_db(DB, contacts)
    return contact


def update(contact_id: str, **kwargs) -> Optional[dict]:
    contacts = get_all()
    for c in contacts:
        if c["id"] == contact_id:
            c.update(kwargs)
            write_db(DB, contacts)
            return c
    return None


def delete(contact_id: str) -> bool:
    contacts = get_all()
    filtered = [c for c in contacts if c["id"] != contact_id]
    if len(filtered) == len(contacts):
        return False
    write_db(DB, filtered)
    return True

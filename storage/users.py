import uuid
from datetime import datetime
from typing import Optional
from .base import read_db, write_db

DB = "users.json"


def get_all() -> list:
    return read_db(DB)


def get_active_agents() -> list:
    return [u for u in get_all() if u.get("isActive", True) and u.get("role") == "agent"]


def get_by_id(user_id: str) -> Optional[dict]:
    return next((u for u in get_all() if u["id"] == user_id), None)


def get_by_email(email: str) -> Optional[dict]:
    return next((u for u in get_all() if u["email"].lower() == email.lower()), None)


def get_by_agent_id(agent_id: str) -> Optional[dict]:
    return next((u for u in get_all() if u.get("agentId", "").lower() == agent_id.lower()), None)


def create(name: str, email: str, password_hash: str, role: str = "agent", agent_id: str = "") -> dict:
    users = get_all()
    user = {
        "id": str(uuid.uuid4()),
        "agentId": agent_id.strip(),
        "name": name,
        "email": email,
        "passwordHash": password_hash,
        "role": role,
        "isActive": True,
        "createdAt": datetime.utcnow().isoformat(),
        "updatedAt": datetime.utcnow().isoformat(),
    }
    users.append(user)
    write_db(DB, users)
    return user


def update(user_id: str, **kwargs) -> Optional[dict]:
    users = get_all()
    for u in users:
        if u["id"] == user_id:
            u.update(kwargs)
            u["updatedAt"] = datetime.utcnow().isoformat()
            write_db(DB, users)
            return u
    return None

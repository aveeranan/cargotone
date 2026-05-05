import uuid
from datetime import datetime
from .base import read_db, write_db

DB = "agent_history.json"


def get_all() -> list:
    return read_db(DB)


def get_by_company(company_id: str) -> list:
    history = [h for h in get_all() if h["companyId"] == company_id]
    return sorted(history, key=lambda x: x["startDate"], reverse=True)


def get_by_agent(agent_id: str) -> list:
    return [h for h in get_all() if h["agentId"] == agent_id]


def record_assignment(company_id: str, agent_id: str, reason: str = "initial") -> dict:
    history = get_all()
    for h in history:
        if h["companyId"] == company_id and h.get("endDate") is None:
            h["endDate"] = datetime.utcnow().isoformat()
    entry = {
        "id": str(uuid.uuid4()),
        "companyId": company_id,
        "agentId": agent_id,
        "startDate": datetime.utcnow().isoformat(),
        "endDate": None,
        "reason": reason,
    }
    history.append(entry)
    write_db(DB, history)
    return entry


def close_assignment(company_id: str) -> None:
    history = get_all()
    for h in history:
        if h["companyId"] == company_id and h.get("endDate") is None:
            h["endDate"] = datetime.utcnow().isoformat()
    write_db(DB, history)

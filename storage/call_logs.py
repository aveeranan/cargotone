import uuid
from datetime import datetime, date, timedelta
from typing import Optional
from .base import read_db, write_db

DB = "call_logs.json"

CALL_OUTCOMES = [
    "EE_EXISTING_CLIENT",
    "ES_ENQUIRY_SHARED",
    "NA_NOT_ANSWER",
    "NE_NUMBER_NOT_EXIST",
    "NI_NOT_INTERESTED",
    "NC_NO_CLEAR_FEEDBACK",
    "CD_CALL_DISCONNECT",
    "NN_NO_NUMBER",
    "NW_NO_WEBSITE",
    "BUSY",
    "CM_CALL_ME_LATER",
    "APPOINTMENT",
    "PERMANENTLY_CLOSED",
    "FRADULENT",
    "PAYMENT_ISSUE",
    "CONTRACT_YEARLY",
    "CONTRACT_QUATERLY",
    "CONTRACT_MNC",
    "MANAGEMENT_DECISION_IS_FINAL",
    "SOEF_SUPPORT_ONLY_EXISTING_FFF",
    "RR_RECEPTION_REJECTION",
    "SR_SECURITY_REJECTION",
    "PS_PROFILE_SENT",
    "UNKNOWN",
    "NE_NEGOTIATION",
    "CLOSURE",
    "ORDER",
    "OTHER",
]


def get_all() -> list:
    return read_db(DB)


def get_by_company(company_id: str) -> list:
    logs = [l for l in get_all() if l["companyId"] == company_id]
    return sorted(logs, key=lambda x: x["createdAt"], reverse=True)


def create(company_id: str, agent_id: str, **kwargs) -> dict:
    logs = get_all()
    log = {
        "id": str(uuid.uuid4()),
        "companyId": company_id,
        "agentId": agent_id,
        "contactId": kwargs.get("contactId"),
        "callDate": kwargs.get("callDate", datetime.utcnow().isoformat()),
        "outcome": kwargs.get("outcome", "OTHER"),
        "notes": kwargs.get("notes", ""),
        "followUpDate": kwargs.get("followUpDate"),
        "createdAt": datetime.utcnow().isoformat(),
    }
    logs.append(log)
    write_db(DB, logs)
    return log


def get_queue_for_agent(agent_id: str) -> dict:
    today = date.today()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

    import storage.companies as companies_store

    agent_companies = {c["id"]: c for c in companies_store.get_by_agent(agent_id)}

    # Find latest follow-up date per company
    latest: dict = {}
    for log in get_all():
        if log.get("followUpDate") and log["companyId"] in agent_companies:
            cid = log["companyId"]
            if cid not in latest or log["followUpDate"] > latest[cid]["followUpDate"]:
                latest[cid] = log

    queue: dict = {"missed": [], "today": [], "tomorrow": []}
    for cid, log in latest.items():
        company = agent_companies[cid]
        fu_date = date.fromisoformat(log["followUpDate"])
        item = {**company, "followUpDate": log["followUpDate"], "lastNote": log.get("notes", "")}
        if fu_date <= yesterday:
            queue["missed"].append(item)
        elif fu_date == today:
            queue["today"].append(item)
        elif fu_date == tomorrow:
            queue["tomorrow"].append(item)
    return queue


def get_daily_stats(target_date: str) -> dict:
    logs = [l for l in get_all() if l.get("callDate", "")[:10] == target_date]
    stats: dict = {}
    for log in logs:
        aid = log["agentId"]
        if aid not in stats:
            stats[aid] = {"total": 0, "outcomes": {}}
        stats[aid]["total"] += 1
        outcome = log.get("outcome", "reached")
        stats[aid]["outcomes"][outcome] = stats[aid]["outcomes"].get(outcome, 0) + 1
    return stats


def get_weekly_stats(week_start: str) -> dict:
    start = date.fromisoformat(week_start)
    end = start + timedelta(days=6)
    logs = [
        l for l in get_all()
        if start.isoformat() <= l.get("callDate", "")[:10] <= end.isoformat()
    ]
    stats: dict = {}
    for log in logs:
        aid = log["agentId"]
        if aid not in stats:
            stats[aid] = {"total": 0, "by_day": {}}
        stats[aid]["total"] += 1
        day = log.get("callDate", "")[:10]
        stats[aid]["by_day"][day] = stats[aid]["by_day"].get(day, 0) + 1
    return stats

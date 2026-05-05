from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from app_templates import templates
from datetime import date

import storage.companies as companies_store
import storage.call_logs as call_logs_store
import storage.contacts as contacts_store
import storage.users as users_store
from dependencies import require_auth

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user: dict = Depends(require_auth)):
    if user["role"] == "agent":
        queue = call_logs_store.get_queue_for_agent(user["id"])
        assigned = companies_store.get_by_agent(user["id"])
    else:
        queue = {"missed": [], "today": [], "tomorrow": []}
        assigned = companies_store.get_all()

    today_str = date.today().isoformat()
    all_logs = call_logs_store.get_all()
    calls_today = len([
        l for l in all_logs
        if l.get("callDate", "")[:10] == today_str
        and (user["role"] == "admin" or l["agentId"] == user["id"])
    ])

    # Admin dashboard: aggregate queue across all agents
    if user["role"] == "admin":
        import storage.users as users_store
        from datetime import timedelta
        yesterday = date.today() - timedelta(days=1)
        tomorrow = date.today() + timedelta(days=1)
        latest: dict = {}
        for log in all_logs:
            if log.get("followUpDate"):
                cid = log["companyId"]
                if cid not in latest or log["followUpDate"] > latest[cid]["followUpDate"]:
                    latest[cid] = log
        company_map = {c["id"]: c for c in companies_store.get_all()}
        for cid, log in latest.items():
            c = company_map.get(cid, {})
            fu = date.fromisoformat(log["followUpDate"])
            item = {**c, "followUpDate": log["followUpDate"], "lastNote": log.get("notes", "")}
            if fu <= yesterday:
                queue["missed"].append(item)
            elif fu == date.today():
                queue["today"].append(item)
            elif fu == tomorrow:
                queue["tomorrow"].append(item)

    # Enrich every queue item with its primary contact phone
    all_contacts = contacts_store.get_all()
    contact_map: dict = {}
    for ct in all_contacts:
        cid = ct["companyId"]
        phones = ct.get("phones") or []
        if not phones:
            continue
        # Prefer primary contact; otherwise take the first contact with a phone
        if cid not in contact_map or ct.get("isPrimary"):
            contact_map[cid] = {"name": ct["name"], "phone": phones[0]}

    for section in queue.values():
        for item in section:
            info = contact_map.get(item["id"])
            item["primaryPhone"] = info["phone"] if info else ""
            item["primaryContactName"] = info["name"] if info else ""

    stats = {
        "total_assigned": len(assigned),
        "calls_today": calls_today,
        "follow_up_today": len(queue.get("today", [])),
        "missed": len(queue.get("missed", [])),
    }

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "queue": queue,
        "stats": stats,
        "active_page": "dashboard",
    })


@router.get("/api/companies/{company_id}/calls")
async def get_calls(company_id: str, user: dict = Depends(require_auth)):
    return JSONResponse(call_logs_store.get_by_company(company_id))


@router.post("/api/companies/{company_id}/calls")
async def log_call(company_id: str, request: Request, user: dict = Depends(require_auth)):
    company = companies_store.get_by_id(company_id)
    if not company:
        return JSONResponse({"error": "Company not found"}, status_code=404)
    if user["role"] == "agent" and company.get("assignedAgentId") != user["id"]:
        return JSONResponse({"error": "Access denied"}, status_code=403)

    body = await request.json()
    log = call_logs_store.create(
        company_id=company_id,
        agent_id=user["id"],
        contactId=body.get("contactId"),
        outcome=body.get("outcome", "OTHER"),
        notes=body.get("notes", ""),
        followUpDate=body.get("followUpDate") or None,
    )

    if body.get("status"):
        companies_store.update(company_id, status=body["status"])

    return JSONResponse({"success": True, "log": log})

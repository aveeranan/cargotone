from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from app_templates import templates
from datetime import date

import storage.users as users_store
import storage.companies as companies_store
import storage.agent_history as history_store
import storage.call_logs as call_logs_store
import auth as auth_module
from dependencies import require_auth, require_admin

router = APIRouter()


@router.get("/agents", response_class=HTMLResponse)
async def agents_list(request: Request, user: dict = Depends(require_admin)):
    agents = users_store.get_all()
    all_logs = call_logs_store.get_all()
    today_str = date.today().isoformat()

    for agent in agents:
        agent["company_count"] = len(companies_store.get_by_agent(agent["id"]))
        agent["calls_today"] = len([
            l for l in all_logs
            if l["agentId"] == agent["id"] and l.get("callDate", "")[:10] == today_str
        ])

    return templates.TemplateResponse("agents/list.html", {
        "request": request,
        "user": user,
        "agents": agents,
        "active_page": "agents",
        "flash": request.query_params.get("success"),
    })


COMPANY_DOMAIN = "cargotone.com"


@router.post("/api/agents")
async def create_agent(request: Request, user: dict = Depends(require_admin)):
    body = await request.json()
    name = body.get("name", "").strip()
    password = body.get("password", "").strip()
    role = body.get("role", "agent").strip()
    agent_id = body.get("agentId", "").strip()

    if role not in ("agent", "admin"):
        role = "agent"
    if not name or not agent_id or not password:
        return JSONResponse({"error": "Name, Agent ID and password are required"}, status_code=400)
    if users_store.get_by_agent_id(agent_id):
        return JSONResponse({"error": f'Agent ID "{agent_id}" is already in use'}, status_code=400)

    email = f"{agent_id.lower()}@{COMPANY_DOMAIN}"
    if users_store.get_by_email(email):
        return JSONResponse({"error": f'Email "{email}" is already in use'}, status_code=400)

    err = auth_module.validate_password_strength(password)
    if err:
        return JSONResponse({"error": err}, status_code=400)

    agent = users_store.create(
        name=name,
        email=email,
        password_hash=auth_module.hash_password(password),
        role=role,
        agent_id=agent_id,
    )
    agent_safe = {k: v for k, v in agent.items() if k != "passwordHash"}
    return JSONResponse({"success": True, "agent": agent_safe})


@router.put("/api/agents/{agent_id}")
async def update_agent(agent_id: str, request: Request, user: dict = Depends(require_admin)):
    body = await request.json()
    updates: dict = {}

    if "name" in body:
        updates["name"] = body["name"]
    if "agentId" in body:
        updates["agentId"] = body["agentId"]
    if "isActive" in body:
        updates["isActive"] = body["isActive"]
        if not body["isActive"]:
            for c in companies_store.get_by_agent(agent_id):
                companies_store.update(c["id"], assignedAgentId=None)
                history_store.close_assignment(c["id"])
    if "newPassword" in body:
        err = auth_module.validate_password_strength(body["newPassword"])
        if err:
            return JSONResponse({"error": err}, status_code=400)
        updates["passwordHash"] = auth_module.hash_password(body["newPassword"])

    result = users_store.update(agent_id, **updates)
    if not result:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    return JSONResponse({"success": True})


@router.get("/api/agents/{agent_id}/companies")
async def get_agent_companies(agent_id: str, user: dict = Depends(require_admin)):
    return JSONResponse(companies_store.get_by_agent(agent_id))

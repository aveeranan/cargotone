from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from app_templates import templates
from fastapi.exceptions import HTTPException

import storage.companies as companies_store
import storage.users as users_store
import storage.contacts as contacts_store
import storage.call_logs as call_logs_store
import storage.agent_history as history_store
from storage.call_logs import CALL_OUTCOMES
from dependencies import require_auth, require_admin

router = APIRouter()


@router.get("/companies", response_class=HTMLResponse)
async def companies_list(request: Request, user: dict = Depends(require_auth)):
    query = request.query_params.get("q", "")
    status = request.query_params.get("status", "")
    filter_agent = request.query_params.get("agent", "")

    agent_id = user["id"] if user["role"] == "agent" else filter_agent
    items = companies_store.search(query=query, status=status, agent_id=agent_id)

    agent_map = {a["id"]: a["name"] for a in users_store.get_all()}
    for c in items:
        c["agentName"] = agent_map.get(c.get("assignedAgentId"), "Unassigned")

    return templates.TemplateResponse("companies/list.html", {
        "request": request,
        "user": user,
        "companies": items,
        "agents": users_store.get_active_agents(),
        "selected_status": status,
        "query": query,
        "active_page": "companies",
        "statuses": companies_store.STATUSES,
        "product_list": companies_store.PRODUCT_LIST,
        "flash": request.query_params.get("success"),
    })


@router.get("/companies/{company_id}", response_class=HTMLResponse)
async def company_detail(company_id: str, request: Request, user: dict = Depends(require_auth)):
    company = companies_store.get_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404)
    if user["role"] == "agent" and company.get("assignedAgentId") != user["id"]:
        raise HTTPException(status_code=403)

    contacts = contacts_store.get_by_company(company_id)
    call_logs = call_logs_store.get_by_company(company_id)
    agent_history = history_store.get_by_company(company_id)
    agents = users_store.get_active_agents()
    agent_map = {a["id"]: a["name"] for a in users_store.get_all()}

    for h in agent_history:
        h["agentName"] = agent_map.get(h["agentId"], "Unknown")
    for l in call_logs:
        l["agentName"] = agent_map.get(l["agentId"], "Unknown")

    return templates.TemplateResponse("companies/detail.html", {
        "request": request,
        "user": user,
        "company": company,
        "contacts": contacts,
        "call_logs": call_logs,
        "agent_history": agent_history,
        "agents": agents,
        "agent_name": agent_map.get(company.get("assignedAgentId"), "Unassigned"),
        "active_page": "companies",
        "statuses": companies_store.STATUSES,
        "product_list": companies_store.PRODUCT_LIST,
        "call_outcomes": CALL_OUTCOMES,
        "flash": request.query_params.get("success"),
    })


def _create_contact_if_provided(company_id: str, data: dict):
    name = (data.get("contactName") or "").strip()
    phone = (data.get("contactPhone") or "").strip()
    email = (data.get("contactEmail") or "").strip()
    if name or phone or email:
        contacts_store.create(
            company_id=company_id,
            name=name or "Unknown",
            phones=[phone] if phone else [],
            email=email,
            isPrimary=True,
        )


def _create_contacts_list(company_id: str, contacts: list):
    for ct in contacts:
        name = (ct.get("name") or "").strip()
        phone = (ct.get("phone") or "").strip()
        email = (ct.get("email") or "").strip()
        if name or phone or email:
            contacts_store.create(
                company_id=company_id,
                name=name or "Unknown",
                phones=[phone] if phone else [],
                email=email,
                isPrimary=ct.get("isPrimary", False),
            )


def _resolve_assigned_agent(user: dict, requested_agent_id: str) -> str | None:
    if user["role"] == "agent":
        return user["id"]
    return requested_agent_id or None


@router.post("/api/companies")
async def create_company(request: Request, user: dict = Depends(require_auth)):
    body = await request.json()
    assigned_agent_id = _resolve_assigned_agent(user, body.get("agentId", ""))

    # Bulk with full details: {entries: [{name, website, contactName, contactPhone, contactEmail}], agentId: "..."}
    if "entries" in body:
        created = []
        skipped = []
        for entry in body["entries"]:
            name = (entry.get("name") or "").strip()
            if not name:
                continue
            if companies_store.get_by_name(name):
                skipped.append(name)
                continue
            kwargs = {}
            if entry.get("website"):
                kwargs["website"] = entry["website"].strip()
            if entry.get("address1"):
                kwargs["address1"] = entry["address1"].strip()
            if entry.get("address2"):
                kwargs["address2"] = entry["address2"].strip()
            if assigned_agent_id:
                kwargs["assignedAgentId"] = assigned_agent_id
            company = companies_store.create(name=name, **kwargs)
            if assigned_agent_id:
                history_store.record_assignment(company["id"], assigned_agent_id, reason="initial")
            _create_contacts_list(company["id"], entry.get("contacts", []))
            created.append(company)
        return JSONResponse({
            "success": True,
            "created": len(created),
            "skipped": len(skipped),
            "skippedNames": skipped,
            "companies": created,
        })

    # Single company with optional contact details
    if body.get("name"):
        name = body["name"].strip()
        if not name:
            return JSONResponse({"error": "Company name is required"}, status_code=400)
        if companies_store.get_by_name(name):
            return JSONResponse({"error": f'Company "{name}" already exists'}, status_code=409)
        kwargs = {}
        if body.get("website"):
            kwargs["website"] = body["website"].strip()
        if assigned_agent_id:
            kwargs["assignedAgentId"] = assigned_agent_id
        for field in [
            "address1", "address2",
            "businessType", "product", "callStatus", "remarks", "mode",
            "shipmentType", "country",
            "airImportVolume", "airExportVolume", "oceanImportVolume", "oceanExportVolume",
        ]:
            if body.get(field):
                kwargs[field] = body[field].strip()
        company = companies_store.create(name=name, **kwargs)
        if assigned_agent_id:
            history_store.record_assignment(company["id"], assigned_agent_id, reason="initial")
        _create_contact_if_provided(company["id"], body)
        return JSONResponse({"success": True, "created": 1, "skipped": 0, "companies": [company]})

    # Legacy bulk: {names: ["Acme", "Global"]}
    names = [n.strip() for n in body.get("names", []) if n.strip()]
    if not names:
        return JSONResponse({"error": "At least one company name is required"}, status_code=400)
    created = []
    skipped = []
    for name in names:
        if companies_store.get_by_name(name):
            skipped.append(name)
        else:
            c = companies_store.create(name=name, assignedAgentId=assigned_agent_id)
            if assigned_agent_id:
                history_store.record_assignment(c["id"], assigned_agent_id, reason="initial")
            created.append(c)
    return JSONResponse({
        "success": True,
        "created": len(created),
        "skipped": len(skipped),
        "skippedNames": skipped,
        "companies": created,
    })


@router.put("/api/companies/{company_id}")
async def update_company(company_id: str, request: Request, user: dict = Depends(require_auth)):
    company = companies_store.get_by_id(company_id)
    if not company:
        return JSONResponse({"error": "Not found"}, status_code=404)
    if user["role"] == "agent" and company.get("assignedAgentId") != user["id"]:
        return JSONResponse({"error": "Access denied"}, status_code=403)

    body = await request.json()
    allowed = [
        "name", "website", "goodsTypes", "status", "superCompanyKey",
        "address1", "address2",
        "businessType", "product", "callStatus", "remarks", "mode",
        "shipmentType", "country",
        "airImportVolume", "airExportVolume", "oceanImportVolume", "oceanExportVolume",
    ]
    if user["role"] == "admin":
        allowed.append("assignedAgentId")

    updates = {k: v for k, v in body.items() if k in allowed}

    if "assignedAgentId" in updates and user["role"] == "admin":
        new_aid = updates["assignedAgentId"]
        if new_aid != company.get("assignedAgentId"):
            if new_aid:
                history_store.record_assignment(company_id, new_aid, reason="transfer")
            else:
                history_store.close_assignment(company_id)

    updated = companies_store.update(company_id, **updates)
    return JSONResponse({"success": True, "company": updated})


@router.delete("/api/companies/{company_id}")
async def delete_company(company_id: str, user: dict = Depends(require_admin)):
    if not companies_store.delete(company_id):
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse({"success": True})


@router.post("/api/companies/{company_id}/assign")
async def assign_company(company_id: str, request: Request, user: dict = Depends(require_admin)):
    company = companies_store.get_by_id(company_id)
    if not company:
        return JSONResponse({"error": "Company not found"}, status_code=404)
    body = await request.json()
    agent_id = body.get("agentId")
    if agent_id:
        if not users_store.get_by_id(agent_id):
            return JSONResponse({"error": "Agent not found"}, status_code=404)
        history_store.record_assignment(company_id, agent_id, reason="initial")
    else:
        history_store.close_assignment(company_id)
    updated = companies_store.update(company_id, assignedAgentId=agent_id)
    return JSONResponse({"success": True, "company": updated})


@router.post("/api/companies/split")
async def split_companies(request: Request, user: dict = Depends(require_admin)):
    body = await request.json()
    assignments = body.get("assignments", [])
    count = 0
    for item in assignments:
        cid = item.get("companyId")
        aid = item.get("toAgentId")
        if cid and aid:
            companies_store.update(cid, assignedAgentId=aid)
            history_store.record_assignment(cid, aid, reason="split")
            count += 1
    return JSONResponse({"success": True, "count": count})

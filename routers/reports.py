from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from app_templates import templates
from datetime import date, timedelta

import storage.call_logs as call_logs_store
import storage.companies as companies_store
import storage.users as users_store
import storage.contacts as contacts_store
import storage.agent_history as history_store
from dependencies import require_auth, require_admin

router = APIRouter()


@router.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request, user: dict = Depends(require_admin)):
    return templates.TemplateResponse("reports/index.html", {
        "request": request,
        "user": user,
        "active_page": "reports",
    })


@router.get("/site-visit", response_class=HTMLResponse)
async def site_visit(request: Request, user: dict = Depends(require_admin)):
    city = request.query_params.get("city", "")
    status = request.query_params.get("status", "")
    goods = request.query_params.get("goods", "")

    items = companies_store.search(query=city, status=status)
    if goods:
        items = [c for c in items if goods.lower() in " ".join(c.get("goodsTypes", [])).lower()]

    for c in items:
        c["contacts"] = contacts_store.get_by_company(c["id"])

    all_companies = companies_store.get_all()
    cities: set = set()
    goods_set: set = set()
    for c in all_companies:
        for field in ("address1", "address2"):
            val = c.get(field, "").strip()
            if val:
                cities.add(val)
        for g in c.get("goodsTypes", []):
            if g:
                goods_set.add(g)

    return templates.TemplateResponse("site_visit.html", {
        "request": request,
        "user": user,
        "companies": items,
        "cities": sorted(cities),
        "goods_types": sorted(goods_set),
        "selected_city": city,
        "selected_status": status,
        "selected_goods": goods,
        "active_page": "site_visit",
        "statuses": companies_store.STATUSES,
    })


@router.get("/api/reports/daily")
async def daily_report(request: Request, user: dict = Depends(require_auth)):
    date_str = request.query_params.get("date", date.today().isoformat())
    stats = call_logs_store.get_daily_stats(date_str)
    agents = {a["id"]: a["name"] for a in users_store.get_all()}
    result = [
        {"agentId": aid, "agentName": agents.get(aid, "Unknown"), **data}
        for aid, data in stats.items()
    ]
    for agent in users_store.get_active_agents():
        if agent["id"] not in stats:
            result.append({"agentId": agent["id"], "agentName": agent["name"], "total": 0, "outcomes": {}})
    return JSONResponse({"date": date_str, "agents": result})


@router.get("/api/reports/weekly")
async def weekly_report(request: Request, user: dict = Depends(require_auth)):
    today = date.today()
    week_start = request.query_params.get(
        "weekStart", (today - timedelta(days=today.weekday())).isoformat()
    )
    stats = call_logs_store.get_weekly_stats(week_start)
    agents = {a["id"]: a["name"] for a in users_store.get_all()}
    result = [
        {"agentId": aid, "agentName": agents.get(aid, "Unknown"), "total": d["total"], "byDay": d["by_day"]}
        for aid, d in stats.items()
    ]
    return JSONResponse({"weekStart": week_start, "agents": result})


@router.get("/api/reports/trends")
async def trends_report(user: dict = Depends(require_auth)):
    today = date.today()
    weekly = []
    for i in range(8):
        ws = today - timedelta(days=today.weekday() + 7 * i)
        stats = call_logs_store.get_weekly_stats(ws.isoformat())
        weekly.append({"week": ws.isoformat(), "total": sum(d["total"] for d in stats.values())})
    weekly.reverse()

    monthly = []
    all_logs = call_logs_store.get_all()
    for i in range(6):
        year, month = today.year, today.month - i
        if month <= 0:
            month += 12
            year -= 1
        start = date(year, month, 1)
        end = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year + 1, 1, 1) - timedelta(days=1)
        count = len([l for l in all_logs if start.isoformat() <= l.get("callDate", "")[:10] <= end.isoformat()])
        monthly.append({"month": f"{year}-{month:02d}", "label": start.strftime("%b %Y"), "total": count})
    monthly.reverse()

    return JSONResponse({"weekly": weekly, "monthly": monthly})


@router.get("/api/reports/daily-trends")
async def daily_trends(user: dict = Depends(require_auth)):
    today = date.today()
    days = [today - timedelta(days=i) for i in range(55, -1, -1)]

    active_agents = users_store.get_active_agents()
    agent_map = {a["id"]: a["name"] for a in active_agents}
    agent_daily = {aid: [0] * 56 for aid in agent_map}
    totals = [0] * 56

    day_index = {d.isoformat(): i for i, d in enumerate(days)}
    for log in call_logs_store.get_all():
        log_date = log.get("callDate", "")[:10]
        if log_date in day_index:
            idx = day_index[log_date]
            aid = log["agentId"]
            if aid in agent_daily:
                agent_daily[aid][idx] += 1
            totals[idx] += 1

    day_labels = [d.strftime("%d %b") for d in days]
    return JSONResponse({
        "dayLabels": day_labels,
        "agents": [
            {"agentName": name, "data": agent_daily[aid]}
            for aid, name in agent_map.items()
        ],
        "totals": totals,
    })


@router.get("/api/reports/agent-trends")
async def agent_trends(user: dict = Depends(require_auth)):
    today = date.today()
    weeks = []
    for i in range(7, -1, -1):
        ws = today - timedelta(days=today.weekday() + 7 * i)
        weeks.append(ws.isoformat())

    active_agents = users_store.get_active_agents()
    agent_map = {a["id"]: a["name"] for a in active_agents}
    agent_weekly = {aid: [0] * 8 for aid in agent_map}
    totals = [0] * 8

    for i, ws in enumerate(weeks):
        stats = call_logs_store.get_weekly_stats(ws)
        for aid, data in stats.items():
            if aid in agent_weekly:
                agent_weekly[aid][i] = data["total"]
            totals[i] += data["total"]

    week_labels = [date.fromisoformat(ws).strftime("%d %b") for ws in weeks]

    return JSONResponse({
        "weekLabels": week_labels,
        "agents": [
            {"agentName": name, "data": agent_weekly[aid]}
            for aid, name in agent_map.items()
        ],
        "totals": totals,
    })


@router.get("/api/reports/company/{company_id}")
async def company_report(company_id: str, user: dict = Depends(require_auth)):
    company = companies_store.get_by_id(company_id)
    if not company:
        return JSONResponse({"error": "Not found"}, status_code=404)
    call_logs = call_logs_store.get_by_company(company_id)
    agent_history = history_store.get_by_company(company_id)
    agents = {a["id"]: a["name"] for a in users_store.get_all()}
    for h in agent_history:
        h["agentName"] = agents.get(h["agentId"], "Unknown")
    for l in call_logs:
        l["agentName"] = agents.get(l["agentId"], "Unknown")
    return JSONResponse({"company": company, "callLogs": call_logs, "agentHistory": agent_history})

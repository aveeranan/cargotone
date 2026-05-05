from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

import storage.contacts as contacts_store
import storage.companies as companies_store
from dependencies import require_auth

router = APIRouter()


@router.get("/api/companies/{company_id}/contacts")
async def get_contacts(company_id: str, user: dict = Depends(require_auth)):
    return JSONResponse(contacts_store.get_by_company(company_id))


@router.post("/api/companies/{company_id}/contacts")
async def add_contact(company_id: str, request: Request, user: dict = Depends(require_auth)):
    company = companies_store.get_by_id(company_id)
    if not company:
        return JSONResponse({"error": "Company not found"}, status_code=404)
    if user["role"] == "agent" and company.get("assignedAgentId") != user["id"]:
        return JSONResponse({"error": "Access denied"}, status_code=403)

    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        return JSONResponse({"error": "Contact name is required"}, status_code=400)

    phones = body.get("phones", [])
    if isinstance(phones, str):
        phones = [p.strip() for p in phones.split(",") if p.strip()]

    contact = contacts_store.create(
        company_id=company_id,
        name=name,
        designation=body.get("designation", ""),
        email=body.get("email", ""),
        phones=phones,
        isPrimary=body.get("isPrimary", False),
    )
    return JSONResponse({"success": True, "contact": contact})


@router.put("/api/contacts/{contact_id}")
async def update_contact(contact_id: str, request: Request, user: dict = Depends(require_auth)):
    contact = contacts_store.get_by_id(contact_id)
    if not contact:
        return JSONResponse({"error": "Not found"}, status_code=404)

    body = await request.json()
    phones = body.get("phones", contact.get("phones", []))
    if isinstance(phones, str):
        phones = [p.strip() for p in phones.split(",") if p.strip()]

    updated = contacts_store.update(
        contact_id,
        name=body.get("name", contact["name"]),
        designation=body.get("designation", contact.get("designation", "")),
        email=body.get("email", contact.get("email", "")),
        phones=phones,
        isPrimary=body.get("isPrimary", contact.get("isPrimary", False)),
    )
    return JSONResponse({"success": True, "contact": updated})


@router.delete("/api/contacts/{contact_id}")
async def delete_contact(contact_id: str, user: dict = Depends(require_auth)):
    if not contacts_store.delete(contact_id):
        return JSONResponse({"error": "Not found"}, status_code=404)
    return JSONResponse({"success": True})

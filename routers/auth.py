from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app_templates import templates

import auth as auth_module
import storage.users as users_store
from dependencies import require_auth

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    from dependencies import get_current_user
    if get_current_user(request):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": request.query_params.get("error"),
    })


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    user = users_store.get_by_email(email)
    if not user or not auth_module.verify_password(password, user["passwordHash"]):
        return RedirectResponse("/login?error=Invalid+email+or+password", status_code=302)
    if not user.get("isActive"):
        return RedirectResponse("/login?error=Account+is+deactivated", status_code=302)
    token = auth_module.create_token({"sub": user["id"], "role": user["role"]})
    response = RedirectResponse("/dashboard", status_code=302)
    response.set_cookie("access_token", token, httponly=True, max_age=8 * 3600, samesite="lax")
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("access_token")
    return response


@router.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request, user: dict = Depends(require_auth)):
    return templates.TemplateResponse("change_password.html", {
        "request": request,
        "user": user,
        "active_page": "",
        "error": request.query_params.get("error"),
        "success": request.query_params.get("success"),
    })


@router.post("/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    user: dict = Depends(require_auth),
):
    if new_password != confirm_password:
        return RedirectResponse("/change-password?error=Passwords+do+not+match", status_code=302)
    if not auth_module.verify_password(current_password, user["passwordHash"]):
        return RedirectResponse("/change-password?error=Current+password+is+incorrect", status_code=302)
    err = auth_module.validate_password_strength(new_password)
    if err:
        return RedirectResponse(f"/change-password?error={err.replace(' ', '+')}", status_code=302)
    users_store.update(user["id"], passwordHash=auth_module.hash_password(new_password))
    return RedirectResponse("/change-password?success=Password+changed+successfully", status_code=302)


@router.post("/api/auth/reset-password")
async def reset_password(request: Request, user: dict = Depends(require_auth)):
    if user.get("role") != "admin":
        return JSONResponse({"error": "Admin only"}, status_code=403)
    body = await request.json()
    agent_id = body.get("agentId")
    new_password = body.get("newPassword", "")
    err = auth_module.validate_password_strength(new_password)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    result = users_store.update(agent_id, passwordHash=auth_module.hash_password(new_password))
    if not result:
        return JSONResponse({"error": "Agent not found"}, status_code=404)
    return JSONResponse({"success": True})

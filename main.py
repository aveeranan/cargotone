from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.exceptions import HTTPException
from pathlib import Path
import uvicorn

import auth as auth_module
import storage.users_db as users_store
from routers import auth, companies, contacts, calls, agents, reports

app = FastAPI(title="CargoTone CRM", docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(401)
async def unauthorized_handler(request: Request, exc: HTTPException):
    return RedirectResponse("/login", status_code=302)


@app.exception_handler(403)
async def forbidden_handler(request: Request, exc: HTTPException):
    return HTMLResponse(
        "<div style='font-family:sans-serif;padding:40px'>"
        "<h2>403 — Access Denied</h2><a href='/dashboard'>Go to Dashboard</a></div>",
        status_code=403,
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    return HTMLResponse(
        "<div style='font-family:sans-serif;padding:40px'>"
        "<h2>404 — Not Found</h2><a href='/dashboard'>Go to Dashboard</a></div>",
        status_code=404,
    )


app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(contacts.router)
app.include_router(calls.router)
app.include_router(agents.router)
app.include_router(reports.router)


@app.get("/")
async def root():
    return RedirectResponse("/dashboard", status_code=302)


@app.on_event("startup")
async def startup():
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    for fname in ["users.json", "companies.json", "contacts.json", "call_logs.json", "agent_history.json"]:
        fpath = data_dir / fname
        if not fpath.exists():
            fpath.write_text("[]")

    if not users_store.get_all():
        users_store.create(
            name="Admin",
            email="admin@cargotonelogistics.com",
            password_hash=auth_module.hash_password("Admin@123!"),
            role="admin",
        )
        print("\n✓ Default admin created:")
        print("  Email   : admin@cargotonelogistics.com")
        print("  Password: Admin@123!")
        print("  ⚠  Change this password after first login!\n")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

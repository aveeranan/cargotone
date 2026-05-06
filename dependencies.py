from fastapi import Request, HTTPException
import auth
import storage.users_db as users_store


def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    payload = auth.decode_token(token)
    if not payload:
        return None
    user = users_store.get_by_id(payload.get("sub"))
    if not user or not user.get("isActive"):
        return None
    return user


def require_auth(request: Request):
    user = get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def require_admin(request: Request):
    user = require_auth(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..config import FREE_LIMITS, ACTION_LABELS
from ..deps import get_current_user
from ..models.schemas import LoginRequest, RedeemRequest, RegisterRequest
from ..services import auth_service
from ..utils import user_store

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _public_user(user: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user.get("name", ""),
        "plan": user_store.effective_plan(user),
        "plan_expires_at": user.get("plan_expires_at"),
        "referral_code": user.get("referral_code"),
        "created_at": user.get("created_at"),
    }


@router.post("/auth/register")
@limiter.limit("10/hour")
async def register(request: Request, body: RegisterRequest):
    existing = await user_store.get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    referred_by = None
    if body.referral_code:
        referrer = await user_store.get_user_by_referral_code(body.referral_code.strip())
        if referrer:
            referred_by = referrer["id"]

    pw_hash = auth_service.hash_password(body.password)
    user = await user_store.create_user(
        email=body.email, password_hash=pw_hash, name=body.name, referred_by=referred_by
    )
    token = auth_service.create_token(user["id"])
    return {"token": token, "user": _public_user(user)}


@router.post("/auth/login")
@limiter.limit("20/hour")
async def login(request: Request, body: LoginRequest):
    user = await user_store.get_user_by_email(body.email)
    if not user or not auth_service.verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = auth_service.create_token(user["id"])
    return {"token": token, "user": _public_user(user)}


@router.get("/auth/me")
async def me(user: Dict[str, Any] = Depends(get_current_user)):
    usage = await user_store.usage_summary(user["id"])
    return {
        "user": _public_user(user),
        "usage": usage,
        "limits": FREE_LIMITS,
        "labels": ACTION_LABELS,
    }


@router.post("/auth/redeem")
async def redeem(body: RedeemRequest, user: Dict[str, Any] = Depends(get_current_user)):
    result = await user_store.redeem_code(body.code, user["id"])
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["message"])
    refreshed = await user_store.get_user_by_id(user["id"])
    return {"message": result["message"], "user": _public_user(refreshed)}

"""FastAPI dependencies: resolve the current user from a Bearer JWT,
and enforce free-tier quotas."""
from typing import Any, Dict, Optional

from fastapi import Depends, Header, HTTPException

from .config import (
    ACTION_LABELS,
    FREE_LIMITS,
    PAID_PLANS,
)
from .services import auth_service
from .utils import user_store


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return authorization.strip()


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated. Please sign in.")
    user_id = auth_service.decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    user = await user_store.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Account not found.")
    return user


async def get_optional_user(authorization: Optional[str] = Header(default=None)) -> Optional[Dict[str, Any]]:
    token = _extract_token(authorization)
    if not token:
        return None
    user_id = auth_service.decode_token(token)
    if not user_id:
        return None
    return await user_store.get_user_by_id(user_id)


async def enforce_quota(user: Dict[str, Any], action: str) -> None:
    """Raise 402 if a free-tier user has exhausted this month's allowance.
    Paid plans are unlimited."""
    plan = user_store.effective_plan(user)
    if plan in PAID_PLANS:
        return
    limit = FREE_LIMITS.get(action)
    if limit is None:
        return
    used = await user_store.count_usage_this_month(user["id"], action)
    if used >= limit:
        label = ACTION_LABELS.get(action, "actions")
        raise HTTPException(
            status_code=402,
            detail=(
                f"You've used all {limit} free {label} this month. "
                f"Upgrade to Pro for unlimited access."
            ),
        )

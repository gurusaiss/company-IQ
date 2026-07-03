from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from ..config import settings
from ..models.schemas import GenerateCodesRequest
from ..utils import user_store

router = APIRouter()


def _check_admin(admin_key: Optional[str]) -> None:
    if not admin_key or admin_key != settings.ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Forbidden.")


@router.post("/admin/generate-codes")
async def generate_codes(
    body: GenerateCodesRequest,
    x_admin_key: Optional[str] = Header(default=None),
):
    """Mint redemption codes. Protect with the ADMIN_KEY env var.

    Example: POST with header `X-Admin-Key: <your key>` and body
    {"plan": "pro", "duration_days": 30, "count": 10, "note": "batch-1"}
    """
    _check_admin(x_admin_key)
    codes = await user_store.create_codes(
        plan=body.plan, duration_days=body.duration_days, count=body.count, note=body.note
    )
    return {"plan": body.plan, "duration_days": body.duration_days, "count": len(codes), "codes": codes}

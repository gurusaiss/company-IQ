import secrets
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from ..config import PAID_PLANS
from ..deps import get_current_user
from ..utils import job_store, user_store

router = APIRouter()


@router.post("/share/{job_id}")
async def create_share_link(job_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    """Make a report publicly viewable via a share token. Pro/Lifetime only."""
    if user_store.effective_plan(user) not in PAID_PLANS:
        raise HTTPException(status_code=402, detail="Shareable links are a Pro feature. Upgrade to share reports.")

    job = await job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    if job.user_id and job.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="You can only share your own reports.")
    if job.status != "complete":
        raise HTTPException(status_code=400, detail="Report is not ready to share yet.")

    token = job.share_token or secrets.token_urlsafe(9)
    await job_store.set_job_share(job_id, share_token=token, is_public=True)
    return {"share_token": token, "share_path": f"/share.html?t={token}"}


@router.delete("/share/{job_id}")
async def revoke_share_link(job_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    job = await job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    if job.user_id and job.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="You can only manage your own reports.")
    await job_store.set_job_share(job_id, share_token=job.share_token or "", is_public=False)
    return {"message": "Sharing disabled."}


@router.get("/share/{token}")
async def view_shared_report(token: str):
    """Public — no auth. Returns the report JSON for a shared link."""
    job = await job_store.get_job_by_share_token(token)
    if job is None or not job.is_public:
        raise HTTPException(status_code=404, detail="Shared report not found or no longer public.")
    return {
        "company_name": job.company_name,
        "report": job.report or {},
        "created_at": getattr(job, "created_at", None),
    }

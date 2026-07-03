from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_user
from ..models.schemas import HistoryItem
from ..utils import job_store

router = APIRouter()


@router.get("/history", response_model=List[HistoryItem])
async def get_history(limit: int = 30, user: Dict[str, Any] = Depends(get_current_user)):
    rows = await job_store.get_history(limit=min(limit, 100), user_id=user["id"])
    return [HistoryItem(**r) for r in rows]


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    job = await job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job.user_id and job.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="This report belongs to another account.")
    await job_store.delete_job(job_id)
    return {"message": "Deleted"}

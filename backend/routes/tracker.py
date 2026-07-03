from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_current_user
from ..models.schemas import ApplicationCreate, ApplicationUpdate
from ..utils import user_store

router = APIRouter()


@router.get("/applications")
async def list_apps(user: Dict[str, Any] = Depends(get_current_user)) -> List[Dict[str, Any]]:
    return await user_store.list_applications(user["id"])


@router.post("/applications")
async def create_app(body: ApplicationCreate, user: Dict[str, Any] = Depends(get_current_user)):
    return await user_store.add_application(
        user_id=user["id"], company=body.company, role=body.role,
        status=body.status, notes=body.notes, job_id=body.job_id,
    )


@router.patch("/applications/{app_id}")
async def update_app(app_id: str, body: ApplicationUpdate, user: Dict[str, Any] = Depends(get_current_user)):
    ok = await user_store.update_application(
        app_id, user["id"],
        company=body.company, role=body.role, status=body.status,
        notes=body.notes, next_action_at=body.next_action_at,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Application not found.")
    return await user_store.get_application(app_id)


@router.delete("/applications/{app_id}")
async def delete_app(app_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    ok = await user_store.delete_application(app_id, user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="Application not found.")
    return {"message": "Deleted"}

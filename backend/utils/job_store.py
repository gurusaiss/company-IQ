"""Async PostgreSQL job store."""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models.schemas import JobState, JobStatus
from .db import get_pool


def _now() -> str:
    return datetime.utcnow().isoformat()


def _row_to_state(row: Dict[str, Any]) -> JobState:
    report: Optional[Dict] = None
    if row.get("report_json"):
        try:
            report = json.loads(row["report_json"])
        except Exception:
            pass

    pdf: Optional[bytes] = row.get("pdf_bytes")
    if isinstance(pdf, memoryview):
        pdf = bytes(pdf)

    return JobState(
        job_id=row["job_id"],
        company_name=row.get("company_name"),
        status=JobStatus(row["status"]),
        progress=row["progress"],
        message=row["message"],
        error=row.get("error"),
        report=report,
        pdf_bytes=pdf,
        md_content=row.get("md_content"),
        ppt_prompt=row.get("ppt_prompt"),
        user_id=row.get("user_id"),
        share_token=row.get("share_token"),
        is_public=bool(row.get("is_public")),
        created_at=row.get("created_at"),
    )


async def insert_job(job_id: str, company_name: str, user_id: Optional[str] = None) -> None:
    pool = await get_pool()
    await pool.execute(
        "INSERT INTO jobs (job_id, company_name, status, progress, message, created_at, user_id) "
        "VALUES ($1,$2,$3,$4,$5,$6,$7)",
        job_id, company_name, "pending", 0, "Job created", _now(), user_id,
    )


async def set_job_share(job_id: str, share_token: str, is_public: bool) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE jobs SET share_token = $1, is_public = $2 WHERE job_id = $3",
        share_token, is_public, job_id,
    )


async def get_job_by_share_token(token: str) -> Optional[JobState]:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM jobs WHERE share_token = $1", token)
    return _row_to_state(dict(row)) if row else None


async def update_job(job_id: str, **kwargs: Any) -> None:
    if not kwargs:
        return

    columns: Dict[str, Any] = {}
    for key, value in kwargs.items():
        if key == "report" and value is not None:
            columns["report_json"] = json.dumps(value)
        elif key == "report" and value is None:
            columns["report_json"] = None
        elif isinstance(value, JobStatus):
            columns[key] = value.value
        else:
            columns[key] = value

    if not columns:
        return

    col_names = list(columns.keys())
    set_sql = ", ".join(f"{k} = ${i + 1}" for i, k in enumerate(col_names))
    vals = [columns[k] for k in col_names]
    vals.append(job_id)

    pool = await get_pool()
    await pool.execute(
        f"UPDATE jobs SET {set_sql} WHERE job_id = ${len(col_names) + 1}", *vals
    )


async def get_job(job_id: str) -> Optional[JobState]:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT * FROM jobs WHERE job_id = $1", job_id)
    return _row_to_state(dict(row)) if row else None


async def get_history(limit: int = 30, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    pool = await get_pool()
    if user_id is not None:
        rows = await pool.fetch(
            "SELECT job_id, company_name, status, progress, created_at "
            "FROM jobs WHERE user_id = $1 ORDER BY created_at DESC LIMIT $2",
            user_id, limit,
        )
    else:
        rows = await pool.fetch(
            "SELECT job_id, company_name, status, progress, created_at "
            "FROM jobs ORDER BY created_at DESC LIMIT $1",
            limit,
        )
    return [dict(r) for r in rows]


async def delete_job(job_id: str) -> None:
    pool = await get_pool()
    await pool.execute("DELETE FROM jobs WHERE job_id = $1", job_id)

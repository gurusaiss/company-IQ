import asyncio
import uuid
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..config import ACTION_REPORT, settings
from ..deps import enforce_quota, get_current_user
from ..models.schemas import AnalyzeResponse, JobStatus, StatusResponse
from ..services import (
    groq_service, markdown_generator, pdf_generator,
    ppt_prompt_generator, resume_parser,
)
from ..utils import job_store, user_store

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


def _assert_owner(job, user: Dict[str, Any]) -> None:
    """Reports created by a user are private to that user. Legacy jobs
    (no user_id) remain accessible to any authenticated user."""
    if job.user_id and job.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="This report belongs to another account.")


@router.post("/analyze", response_model=AnalyzeResponse)
@limiter.limit(settings.RATE_LIMIT)
async def start_analysis(
    request: Request,
    background_tasks: BackgroundTasks,
    company_name: str = Form(..., min_length=1, max_length=200),
    resume: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user),
):
    await enforce_quota(user, ACTION_REPORT)

    if not resume.filename or not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Resume must be a PDF file.")

    resume_bytes = await resume.read()
    if len(resume_bytes) > settings.MAX_RESUME_SIZE:
        raise HTTPException(status_code=400, detail="Resume exceeds 10 MB limit.")
    if len(resume_bytes) < 100:
        raise HTTPException(status_code=400, detail="Resume file appears empty.")

    job_id = str(uuid.uuid4())
    await job_store.insert_job(job_id, company_name.strip(), user_id=user["id"])
    await user_store.record_usage(user["id"], ACTION_REPORT)
    background_tasks.add_task(_pipeline, job_id, company_name.strip(), resume_bytes)
    return AnalyzeResponse(job_id=job_id, message="Analysis started")


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    job = await job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    _assert_owner(job, user)
    return StatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        message=job.message,
        error=job.error,
    )


@router.get("/download/{job_id}/{file_type}")
async def download_file(job_id: str, file_type: str, user: Dict[str, Any] = Depends(get_current_user)):
    job = await job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    _assert_owner(job, user)
    if job.status != JobStatus.COMPLETE:
        raise HTTPException(status_code=400, detail="Report not ready yet.")

    slug = (job.company_name or "report").lower().replace(" ", "_")[:30]
    slug = "".join(c for c in slug if c.isalnum() or c == "_")

    if file_type == "pdf":
        if not job.pdf_bytes:
            raise HTTPException(status_code=404, detail="PDF not available.")
        return Response(
            content=bytes(job.pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{slug}_report.pdf"'},
        )
    if file_type == "md":
        if not job.md_content:
            raise HTTPException(status_code=404, detail="Markdown not available.")
        return Response(
            content=job.md_content.encode("utf-8"),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{slug}_report.md"'},
        )
    if file_type == "ppt":
        if not job.ppt_prompt:
            raise HTTPException(status_code=404, detail="PPT prompt not available.")
        return Response(
            content=job.ppt_prompt.encode("utf-8"),
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{slug}_ppt_prompt.txt"'},
        )
    raise HTTPException(status_code=400, detail="Invalid type. Use pdf, md, or ppt.")


async def _pipeline(job_id: str, company_name: str, resume_bytes: bytes) -> None:
    try:
        await job_store.update_job(
            job_id, status=JobStatus.PARSING, progress=8, message="Parsing resume..."
        )
        resume_data = await asyncio.to_thread(resume_parser.parse_resume, resume_bytes)

        await job_store.update_job(
            job_id, status=JobStatus.RESEARCHING, progress=18,
            message=f"Researching {company_name} with AI web search..."
        )
        report_dict = await groq_service.research_and_analyze(company_name, resume_data)

        await job_store.update_job(
            job_id, status=JobStatus.ANALYZING, progress=58, message="Analyzing candidate fit..."
        )

        await job_store.update_job(
            job_id, status=JobStatus.GENERATING, progress=68, message="Generating PDF report..."
        )
        pdf_bytes = await asyncio.to_thread(pdf_generator.generate_pdf, report_dict)

        await job_store.update_job(job_id, progress=80, message="Creating Markdown document...")
        md_content = await asyncio.to_thread(markdown_generator.generate_markdown, report_dict)

        await job_store.update_job(job_id, progress=90, message="Building presentation prompt...")
        ppt_prompt = await asyncio.to_thread(ppt_prompt_generator.generate_ppt_prompt, report_dict)

        await job_store.update_job(
            job_id,
            status=JobStatus.COMPLETE,
            progress=100,
            message="Your report is ready!",
            report=report_dict,
            pdf_bytes=pdf_bytes,
            md_content=md_content,
            ppt_prompt=ppt_prompt,
        )
    except Exception as exc:
        msg = str(exc)
        await job_store.update_job(
            job_id,
            status=JobStatus.FAILED,
            progress=0,
            message="Analysis failed.",
            error=msg,
        )

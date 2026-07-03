import asyncio
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..config import ACTION_COMPARE, ACTION_COVER_LETTER, ACTION_JD, settings
from ..deps import enforce_quota, get_current_user
from ..services import compare_service, cover_letter_service, jd_analyzer_service, resume_parser
from ..utils import job_store, user_store

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/cover-letter")
@limiter.limit("20/hour")
async def generate_cover_letter(
    request: Request,
    company_name: str = Form(..., min_length=1, max_length=200),
    job_role: str = Form(..., min_length=1, max_length=200),
    job_description: str = Form(default=""),
    resume: UploadFile = File(...),
    job_id: str = Form(default=""),
    user: Dict[str, Any] = Depends(get_current_user),
):
    await enforce_quota(user, ACTION_COVER_LETTER)

    if not resume.filename or not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Resume must be a PDF file.")

    resume_bytes = await resume.read()
    if len(resume_bytes) > settings.MAX_RESUME_SIZE:
        raise HTTPException(status_code=400, detail="Resume exceeds 10 MB.")
    if len(resume_bytes) < 100:
        raise HTTPException(status_code=400, detail="Resume file appears empty.")

    resume_data = await asyncio.to_thread(resume_parser.parse_resume, resume_bytes)

    # Pull company context from an existing report if job_id provided (and owned)
    company_context = ""
    if job_id:
        job = await job_store.get_job(job_id)
        if job and job.report and (not job.user_id or job.user_id == user["id"]):
            overview = job.report.get("company_overview", {})
            company_context = str(overview.get("description", ""))[:800]

    letter = await cover_letter_service.generate_cover_letter(
        company_name=company_name.strip(),
        job_role=job_role.strip(),
        resume_data=resume_data,
        job_description=job_description,
        company_context=company_context,
    )
    await user_store.record_usage(user["id"], ACTION_COVER_LETTER)
    return {"cover_letter": letter, "company": company_name.strip(), "role": job_role.strip()}


@router.post("/analyze-jd")
@limiter.limit("20/hour")
async def analyze_jd(
    request: Request,
    job_description: str = Form(..., min_length=50),
    company_name: str = Form(default=""),
    resume: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user),
):
    await enforce_quota(user, ACTION_JD)

    if not resume.filename or not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Resume must be a PDF file.")

    resume_bytes = await resume.read()
    if len(resume_bytes) > settings.MAX_RESUME_SIZE:
        raise HTTPException(status_code=400, detail="Resume exceeds 10 MB.")
    if len(resume_bytes) < 100:
        raise HTTPException(status_code=400, detail="Resume file appears empty.")

    resume_data = await asyncio.to_thread(resume_parser.parse_resume, resume_bytes)

    result = await jd_analyzer_service.analyze_jd(
        job_description=job_description,
        resume_data=resume_data,
        company_name=company_name.strip(),
    )
    await user_store.record_usage(user["id"], ACTION_JD)
    return result


@router.post("/compare")
@limiter.limit("15/hour")
async def compare_companies(
    request: Request,
    company_a: str = Form(..., min_length=1, max_length=200),
    company_b: str = Form(..., min_length=1, max_length=200),
    resume: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user),
):
    await enforce_quota(user, ACTION_COMPARE)

    if not resume.filename or not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Resume must be a PDF file.")
    resume_bytes = await resume.read()
    if len(resume_bytes) > settings.MAX_RESUME_SIZE:
        raise HTTPException(status_code=400, detail="Resume exceeds 10 MB.")
    if len(resume_bytes) < 100:
        raise HTTPException(status_code=400, detail="Resume file appears empty.")

    resume_data = await asyncio.to_thread(resume_parser.parse_resume, resume_bytes)
    result = await compare_service.compare_companies(company_a.strip(), company_b.strip(), resume_data)
    await user_store.record_usage(user["id"], ACTION_COMPARE)
    return result


@router.post("/salary")
@limiter.limit("20/hour")
async def estimate_salary(
    request: Request,
    company_name: str = Form(..., min_length=1, max_length=200),
    job_role: str = Form(..., min_length=1, max_length=200),
    location: str = Form(default=""),
    resume: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user),
):
    if not resume.filename or not resume.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Resume must be a PDF file.")
    resume_bytes = await resume.read()
    if len(resume_bytes) > settings.MAX_RESUME_SIZE:
        raise HTTPException(status_code=400, detail="Resume exceeds 10 MB.")
    if len(resume_bytes) < 100:
        raise HTTPException(status_code=400, detail="Resume file appears empty.")

    resume_data = await asyncio.to_thread(resume_parser.parse_resume, resume_bytes)
    result = await compare_service.estimate_salary(
        company_name.strip(), job_role.strip(), location, resume_data
    )
    return result


@router.get("/flashcards/{job_id}")
async def get_flashcards(job_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    job = await job_store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    if job.user_id and job.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="This report belongs to another account.")
    if job.status != "complete":
        raise HTTPException(status_code=400, detail="Report not ready yet.")

    report = job.report or {}
    raw_questions = report.get("interview_questions", [])

    cards = []
    for q in raw_questions:
        if isinstance(q, dict) and q.get("question"):
            cards.append({
                "category": q.get("category", "General"),
                "question": q.get("question", ""),
                "tip": q.get("tip", "Think carefully about your specific examples."),
            })

    return {
        "company": job.company_name or "Company",
        "cards": cards,
        "total": len(cards),
    }

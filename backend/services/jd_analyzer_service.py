import json
import logging
import re

from groq import AsyncGroq
from tenacity import before_sleep_log, retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..models.schemas import ResumeData

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=3, max=20),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _call_groq(client: AsyncGroq, messages: list, max_tokens: int = 1400) -> str:
    resp = await client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.25,
    )
    return resp.choices[0].message.content


async def analyze_jd(
    job_description: str,
    resume_data: ResumeData,
    company_name: str = "",
) -> dict:
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    company_str = company_name.strip() or "the company"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a senior recruiter and ATS specialist. You give brutally honest, "
                "accurate, and actionable fit assessments. Return only valid JSON."
            ),
        },
        {
            "role": "user",
            "content": f"""Analyse this candidate's fit for the job description below. Return a JSON object ONLY — no markdown, no explanation.

JOB DESCRIPTION:
{job_description[:3000]}

CANDIDATE RESUME:
{resume_data.full_text[:2500]}

Technologies detected: {', '.join(resume_data.technologies[:15])}
Skills detected: {', '.join(resume_data.skills[:15])}
Experience: {resume_data.experience_years}
Education: {'; '.join(resume_data.education[:3])}

Company: {company_str}

Return EXACTLY this JSON shape (no extra keys):
{{
  "fit_score": <integer 0-100>,
  "ats_score": <integer 0-100>,
  "fit_verdict": "<one of: Strong Match | Good Match | Partial Match | Weak Match>",
  "match_summary": "<2 sentences summarising why this is a good or weak fit>",
  "matched_skills": ["<skill or tech from JD that candidate has>", ...],
  "missing_skills": ["<skill or tech from JD the candidate lacks>", ...],
  "matched_experience": ["<specific achievement/role from resume that matches JD requirement>", ...],
  "gaps": ["<specific concern a recruiter would flag>", ...],
  "keywords_to_add": ["<ATS keyword from JD missing from resume>", ...],
  "top_selling_points": ["<strongest point for this role>", "<second>", "<third>"],
  "tailored_pitch": "<2 confident sentences the candidate can use in emails or intro>",
  "resume_advice": "<3-4 sentences of concrete advice to tailor their resume for this role>",
  "interview_focus": ["<topic the interviewer will likely probe given the gaps>", ...]
}}""",
        },
    ]

    raw = await _call_groq(client, messages, max_tokens=1400)

    # Strip markdown code fences
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass

    return {
        "fit_score": 50,
        "ats_score": 50,
        "fit_verdict": "Analysis Incomplete",
        "match_summary": "Could not complete analysis. Please try again.",
        "matched_skills": [],
        "missing_skills": [],
        "matched_experience": [],
        "gaps": [],
        "keywords_to_add": [],
        "top_selling_points": [],
        "tailored_pitch": "",
        "resume_advice": "Please try again.",
        "interview_focus": [],
    }

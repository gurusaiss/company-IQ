import json
import re
from typing import Dict, Any

from groq import AsyncGroq
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log
import logging

from ..config import settings
from ..models.schemas import ResumeData

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a professional business analyst, career coach, and company researcher. "
    "Use web search to gather accurate, current information about the company. "
    "Produce a comprehensive report that is specific, factual, and genuinely useful — "
    "not generic. For the candidate sections, draw direct connections between the "
    "candidate's actual experience and the company's real needs. "
    "CRITICAL: Return ONLY valid JSON. No markdown fences, no explanation, no preamble."
)

JSON_SCHEMA = """{
  "company_name": "string",
  "tagline": "string - official slogan or motto",
  "logo_url": "string - official website e.g. https://company.com",
  "founding_year": "string",
  "hq_location": "string",
  "industry": "string",
  "company_size": "string e.g. 50,000+ employees",
  "stock_ticker": "string or null",
  "founders": ["full names"],
  "ceo": "string - current CEO",
  "c_suite": ["Name - Title", ...],
  "origin_story": "string - 2-3 paragraphs",
  "growth_timeline": [{"year": "string", "event": "string"}],
  "past_challenges": [{"challenge": "string", "resolution": "string"}],
  "current_projects": [{"name": "string", "description": "string"}],
  "future_roadmap": [{"initiative": "string", "description": "string", "timeline": "string"}],
  "competitors": [{"name": "string", "comparison": "string"}],
  "differentiators": ["string"],
  "struggles_turned_success": [{"project": "string", "struggle": "string", "outcome": "string"}],
  "matching_skills": ["Skill - why it matches"],
  "contribution_current": "string - 2-3 sentences",
  "contribution_future": "string - 2-3 sentences",
  "competitive_advantage": "string - 2-3 sentences",
  "hiring_case": "string - 4-5 sentences",
  "interview_questions": [
    {
      "category": "Behavioral|Technical|Culture|Company-Specific",
      "question": "string - real question asked at this company",
      "tip": "string - brief advice on answering"
    }
  ],
  "culture_insights": {
    "work_life_balance": "string",
    "innovation_style": "string",
    "career_growth": "string",
    "team_environment": "string",
    "notable_perks": ["string"]
  },
  "red_flags": ["string - specific concern to investigate before accepting an offer"],
  "application_strategy": "string - specific advice on how to apply to THIS company",
  "insider_tips": ["string - actionable tip about the hiring process at this company"]
}"""


def _resume_summary(resume: ResumeData) -> str:
    parts: list[str] = []
    if resume.skills:
        parts.append(f"Skills: {', '.join(resume.skills[:20])}")
    if resume.technologies:
        parts.append(f"Technologies: {', '.join(resume.technologies[:20])}")
    if resume.education:
        parts.append(f"Education: {'; '.join(resume.education[:3])}")
    if resume.experience_years != "Not specified":
        parts.append(f"Experience: {resume.experience_years}")
    exp = resume.sections.get("experience") or resume.sections.get("work experience", "")
    if exp:
        parts.append(f"Work Experience:\n{exp[:800]}")
    proj = resume.sections.get("projects", "")
    if proj:
        parts.append(f"Projects:\n{proj[:400]}")
    if not parts:
        parts.append(resume.full_text[:1200])
    return "\n".join(parts)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=3, max=20),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _call_groq(client: AsyncGroq, model: str, messages: list, max_tokens: int) -> str:
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.25,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


async def research_and_analyze(company_name: str, resume: ResumeData) -> Dict[str, Any]:
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    summary = _resume_summary(resume)

    user_message = f"""Research {company_name} thoroughly and analyze the candidate's resume. Return a complete JSON report.

COMPANY: {company_name}

CANDIDATE RESUME:
{summary}

Return ONLY a JSON object matching this exact structure (all fields required, use null for unknown fields):
{JSON_SCHEMA}

Requirements:
- interview_questions: 8-10 real questions asked at {company_name} (mix of behavioral, technical, culture, company-specific)
- culture_insights: specific to {company_name}'s actual culture, not generic
- red_flags: honest concerns based on news, reviews, or company history (2-4 items)
- insider_tips: actionable tips about {company_name}'s actual interview and hiring process (3-5 tips)
- growth_timeline: at least 5 milestones
- current_projects: at least 4 active products/initiatives
- competitors: at least 3 with specific differentiation points"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    content = ""
    try:
        content = await _call_groq(client, settings.GROQ_MODEL, messages, max_tokens=10000)
    except Exception:
        try:
            content = await _call_groq(client, settings.GROQ_FALLBACK_MODEL, messages, max_tokens=8000)
        except Exception as e:
            raise ValueError(f"All GROQ models failed: {e}") from e

    return _parse(content, company_name)


def _parse(content: str, company_name: str) -> Dict[str, Any]:
    # Strip markdown code fences
    content = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.MULTILINE)
    content = re.sub(r"\s*```$", "", content.strip(), flags=re.MULTILINE)
    content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", content)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Minimal fallback so downstream generators don't crash
    return {
        "company_name": company_name,
        "tagline": None,
        "origin_story": "Company research could not be completed. Please try again.",
        "hiring_case": "Analysis could not be completed. Please try again.",
        "interview_questions": [],
        "culture_insights": {},
        "red_flags": [],
        "application_strategy": "",
        "insider_tips": [],
    }

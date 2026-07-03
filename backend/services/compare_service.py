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
async def _call(client: AsyncGroq, messages: list, max_tokens: int) -> str:
    resp = await client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.3,
    )
    return resp.choices[0].message.content


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return {}


async def compare_companies(company_a: str, company_b: str, resume_data: ResumeData) -> dict:
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    tech = ", ".join(resume_data.technologies[:12]) or "general skills"

    messages = [
        {"role": "system", "content": (
            "You are a career advisor with live web access. Compare two companies head-to-head "
            "for a specific candidate. Be specific and current. Return only valid JSON."
        )},
        {"role": "user", "content": f"""Compare {company_a} vs {company_b} for this candidate. Use real, current information.

Candidate: {resume_data.experience_years} experience. Tech: {tech}.
Resume excerpt: {resume_data.full_text[:1500]}

Return ONLY this JSON:
{{
  "company_a": {{
    "name": "{company_a}",
    "fit_score": <0-100>,
    "pros": ["<specific pro>", ...],
    "cons": ["<specific con>", ...],
    "culture": "<1 sentence>",
    "comp_estimate": "<rough total comp band for candidate's level>",
    "growth": "<career growth outlook in 1 sentence>"
  }},
  "company_b": {{
    "name": "{company_b}",
    "fit_score": <0-100>,
    "pros": ["..."],
    "cons": ["..."],
    "culture": "<1 sentence>",
    "comp_estimate": "<band>",
    "growth": "<1 sentence>"
  }},
  "verdict": "<2-3 sentences: which company is the better choice for THIS candidate and why>",
  "winner": "<{company_a} or {company_b}>",
  "decision_factors": ["<factor the candidate should weigh most>", ...]
}}"""},
    ]
    raw = await _call(client, messages, max_tokens=1800)
    data = _parse_json(raw)
    if not data:
        data = {
            "company_a": {"name": company_a, "fit_score": 50, "pros": [], "cons": [], "culture": "", "comp_estimate": "", "growth": ""},
            "company_b": {"name": company_b, "fit_score": 50, "pros": [], "cons": [], "culture": "", "comp_estimate": "", "growth": ""},
            "verdict": "Could not complete comparison. Please try again.",
            "winner": "",
            "decision_factors": [],
        }
    return data


async def estimate_salary(company: str, role: str, location: str, resume_data: ResumeData) -> dict:
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    loc = location.strip() or "India"

    messages = [
        {"role": "system", "content": (
            "You are a compensation analyst with live web access to salary data "
            "(Levels.fyi, Glassdoor, AmbitionBox, public reports). Give realistic, "
            "current salary estimates. Return only valid JSON."
        )},
        {"role": "user", "content": f"""Estimate compensation for a {role} role at {company} in {loc}.

Candidate experience: {resume_data.experience_years}.

Return ONLY this JSON:
{{
  "role": "{role}",
  "company": "{company}",
  "location": "{loc}",
  "currency": "<INR or USD as appropriate>",
  "base_low": <number>,
  "base_high": <number>,
  "total_low": <number>,
  "total_high": <number>,
  "level_guess": "<likely level/band e.g. SDE-1, L4>",
  "breakdown": "<1-2 sentences on base/bonus/stock split>",
  "negotiation_tips": ["<specific tip>", "<tip>", "<tip>"],
  "data_confidence": "<High | Medium | Low>",
  "notes": "<1 sentence caveat about the estimate>"
}}"""},
    ]
    raw = await _call(client, messages, max_tokens=900)
    data = _parse_json(raw)
    if not data:
        data = {
            "role": role, "company": company, "location": loc, "currency": "INR",
            "base_low": 0, "base_high": 0, "total_low": 0, "total_high": 0,
            "level_guess": "", "breakdown": "Could not estimate. Please try again.",
            "negotiation_tips": [], "data_confidence": "Low", "notes": "",
        }
    return data

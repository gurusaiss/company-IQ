import logging

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
async def _call_groq(client: AsyncGroq, messages: list, max_tokens: int = 900) -> str:
    resp = await client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.75,
    )
    return resp.choices[0].message.content


async def generate_cover_letter(
    company_name: str,
    job_role: str,
    resume_data: ResumeData,
    job_description: str = "",
    company_context: str = "",
) -> str:
    client = AsyncGroq(api_key=settings.GROQ_API_KEY)

    tech_str = ", ".join(resume_data.technologies[:12]) if resume_data.technologies else "various technologies"
    skills_str = ", ".join(resume_data.skills[:10]) if resume_data.skills else ""
    edu_str = resume_data.education[0] if resume_data.education else ""
    exp_str = resume_data.experience_years

    jd_section = f"\n\nJob Description (use details from this):\n{job_description[:2000]}" if job_description.strip() else ""
    ctx_section = f"\n\nCompany Research Context:\n{company_context[:800]}" if company_context.strip() else ""

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert career coach and professional writer who specialises in "
                "writing cover letters that actually get interviews. You write in a warm, "
                "confident, human tone — never robotic or generic. You always reference "
                "specific details about both the company and the candidate."
            ),
        },
        {
            "role": "user",
            "content": f"""Write a professional cover letter for a candidate applying to {company_name} for the role of {job_role}.

CANDIDATE PROFILE:
- Experience: {exp_str}
- Technologies: {tech_str}
- Skills: {skills_str}
- Education: {edu_str}
- Full resume text: {resume_data.full_text[:2500]}
{jd_section}
{ctx_section}

STRICT RULES:
1. NEVER start with "I am writing to express my interest" or any cliché opener
2. Open with a specific, bold statement about {company_name} or the role
3. Paragraph 1 (2-3 sentences): Why THIS company and THIS role excites the candidate — reference something specific
4. Paragraph 2 (3-4 sentences): 2 concrete achievements from the resume with numbers/impact if possible
5. Paragraph 3 (2-3 sentences): How their skills directly map to what {company_name} needs
6. Closing (1-2 sentences): Confident CTA — available for interview, eager to contribute
7. Total length: 280-340 words
8. Tone: Professional yet personable. Sound like a smart human, not AI.
9. End with "Sincerely," followed by a blank line for signature

Output ONLY the cover letter. No preamble, no explanation.""",
        },
    ]

    return await _call_groq(client, messages, max_tokens=900)

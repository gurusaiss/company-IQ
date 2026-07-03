import re
from typing import Dict, List
from ..models.schemas import ResumeData

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

TECH_KEYWORDS = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "Ruby", "PHP",
    "Kotlin", "Swift", "Scala", "R", "MATLAB", "Dart", "Elixir", "Haskell",
    "React", "Angular", "Vue", "Next.js", "Node.js", "Django", "Flask", "FastAPI",
    "Spring", "Rails", "Express", "Svelte", "Nuxt", "Remix",
    "AWS", "GCP", "Azure", "Docker", "Kubernetes", "Terraform", "Ansible", "Helm",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Cassandra", "DynamoDB",
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "TensorFlow", "PyTorch",
    "Scikit-learn", "Pandas", "NumPy", "Spark", "Hadoop", "Kafka", "Airflow",
    "SQL", "GraphQL", "REST", "gRPC", "WebSocket", "Microservices", "Serverless",
    "Git", "CI/CD", "Jenkins", "GitHub Actions", "GitLab CI", "CircleCI", "Linux", "Bash",
    "Figma", "Sketch", "Adobe XD", "Agile", "Scrum", "Kanban", "JIRA",
    "Blockchain", "Solidity", "Web3", "DevOps", "MLOps", "DataOps",
]

SECTION_HEADERS = [
    "EXPERIENCE", "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE", "EMPLOYMENT",
    "EDUCATION", "ACADEMIC BACKGROUND", "SKILLS", "TECHNICAL SKILLS", "KEY SKILLS",
    "PROJECTS", "PERSONAL PROJECTS", "CERTIFICATIONS", "AWARDS", "ACHIEVEMENTS",
    "SUMMARY", "OBJECTIVE", "PROFILE", "ABOUT",
]


def parse_resume(pdf_bytes: bytes) -> ResumeData:
    text = _extract_text(pdf_bytes)
    if not text.strip():
        return ResumeData(full_text="", skills=[], technologies=[], education=[])

    return ResumeData(
        full_text=text[:5000],
        skills=_extract_skills(text),
        technologies=_extract_technologies(text),
        education=_extract_education(text),
        experience_years=_extract_experience_years(text),
        sections=_extract_sections(text),
    )


def _extract_text(pdf_bytes: bytes) -> str:
    if not PYMUPDF_AVAILABLE:
        return ""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        return "\n".join(pages).strip()
    except Exception:
        return ""


def _extract_skills(text: str) -> List[str]:
    patterns = [
        r"(?:SKILLS|KEY SKILLS|CORE SKILLS|COMPETENCIES)[:\s]*(.*?)(?=\n[A-Z]{3,}|\Z)",
        r"(?:TECHNICAL SKILLS|TECHNOLOGY)[:\s]*(.*?)(?=\n[A-Z]{3,}|\Z)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            raw = match.group(1)
            parts = re.split(r"[,•|\n·\-•]+", raw)
            skills = [s.strip() for s in parts if 2 < len(s.strip()) < 50]
            if skills:
                return skills[:25]
    return []


def _extract_technologies(text: str) -> List[str]:
    text_lower = text.lower()
    return [t for t in TECH_KEYWORDS if t.lower() in text_lower]


def _extract_education(text: str) -> List[str]:
    degree_pattern = r"(?:B\.?S\.?|B\.?A\.?|M\.?S\.?|M\.?A\.?|Ph\.?D\.?|Bachelor|Master|Doctor|MBA|B\.?Tech|M\.?Tech)[^\n]{5,80}"
    inst_pattern = r"(?:University|College|Institute|School)[^\n]{3,60}"

    results = []
    for pattern in [degree_pattern, inst_pattern]:
        results.extend(re.findall(pattern, text, re.IGNORECASE))

    return list(dict.fromkeys(r.strip() for r in results))[:5]


def _extract_experience_years(text: str) -> str:
    years = [int(y) for y in re.findall(r"\b(20\d{2}|199\d)\b", text)]
    if len(years) >= 2:
        span = max(years) - min(years)
        return f"{span}+ years"
    return "Not specified"


def _extract_sections(text: str) -> Dict[str, str]:
    sections: Dict[str, str] = {}
    joined = "|".join(SECTION_HEADERS)
    for header in SECTION_HEADERS:
        pattern = rf"(?:{header})[:\s]*(.*?)(?=(?:{joined})[:\s]|\Z)"
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            sections[header.lower()] = match.group(1).strip()[:600]
    return sections

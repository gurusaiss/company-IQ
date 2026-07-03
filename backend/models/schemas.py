from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    RESEARCHING = "researching"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    COMPLETE = "complete"
    FAILED = "failed"


class ResumeData(BaseModel):
    full_text: str = ""
    skills: List[str] = []
    technologies: List[str] = []
    education: List[str] = []
    experience_years: str = "Not specified"
    sections: Dict[str, str] = {}


class JobState(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.PENDING
    progress: int = 0
    message: str = "Initializing..."
    company_name: Optional[str] = None
    report: Optional[Dict[str, Any]] = None
    pdf_bytes: Optional[bytes] = None
    md_content: Optional[str] = None
    ppt_prompt: Optional[str] = None
    error: Optional[str] = None
    user_id: Optional[str] = None
    share_token: Optional[str] = None
    is_public: bool = False
    created_at: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class AnalyzeResponse(BaseModel):
    job_id: str
    message: str = "Analysis started"


class StatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int
    message: str
    error: Optional[str] = None


class HistoryItem(BaseModel):
    job_id: str
    company_name: str
    status: str
    progress: int
    created_at: str


# ── Auth ──
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    name: str = Field(default="", max_length=80)
    referral_code: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class RedeemRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=40)


class GenerateCodesRequest(BaseModel):
    plan: str = Field(..., pattern="^(pro|lifetime)$")
    duration_days: int = 30
    count: int = Field(default=1, ge=1, le=200)
    note: str = ""


# ── Applications (tracker) ──
class ApplicationCreate(BaseModel):
    company: str = Field(..., min_length=1, max_length=200)
    role: str = Field(default="", max_length=200)
    status: str = Field(default="saved", max_length=40)
    notes: str = Field(default="", max_length=2000)
    job_id: Optional[str] = None


class ApplicationUpdate(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    next_action_at: Optional[str] = None

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── Core ──
    GROQ_API_KEY: str = ""
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000,*"
    MAX_RESUME_SIZE: int = 10 * 1024 * 1024
    GROQ_MODEL: str = "compound-beta"
    GROQ_FALLBACK_MODEL: str = "llama-3.3-70b-versatile"
    DATABASE_URL: str = ""
    RATE_LIMIT: str = "60/hour"

    # ── Legacy single-key gate (optional, off by default) ──
    ACCESS_KEY: str = ""

    # ── Auth / JWT ──
    JWT_SECRET: str = "CHANGE-ME-IN-PRODUCTION-please-set-a-long-random-string"
    JWT_EXPIRE_DAYS: int = 30
    # Key required to mint redemption codes via /api/admin/*
    ADMIN_KEY: str = "change-me-admin-key"

    # ── Free-tier monthly limits (Pro/Lifetime = unlimited) ──
    FREE_REPORTS_PER_MONTH: int = 3
    FREE_COVER_LETTERS_PER_MONTH: int = 2
    FREE_JD_PER_MONTH: int = 2
    FREE_COMPARE_PER_MONTH: int = 1

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Plan identifiers
PLAN_FREE = "free"
PLAN_PRO = "pro"
PLAN_LIFETIME = "lifetime"
PAID_PLANS = {PLAN_PRO, PLAN_LIFETIME}

# Action identifiers (used for usage tracking + quota)
ACTION_REPORT = "report"
ACTION_COVER_LETTER = "cover_letter"
ACTION_JD = "jd"
ACTION_COMPARE = "compare"

# Map each metered action to its free monthly cap
FREE_LIMITS = {
    ACTION_REPORT: settings.FREE_REPORTS_PER_MONTH,
    ACTION_COVER_LETTER: settings.FREE_COVER_LETTERS_PER_MONTH,
    ACTION_JD: settings.FREE_JD_PER_MONTH,
    ACTION_COMPARE: settings.FREE_COMPARE_PER_MONTH,
}

# Human-readable labels for quota error messages
ACTION_LABELS = {
    ACTION_REPORT: "company reports",
    ACTION_COVER_LETTER: "cover letters",
    ACTION_JD: "JD analyses",
    ACTION_COMPARE: "company comparisons",
}

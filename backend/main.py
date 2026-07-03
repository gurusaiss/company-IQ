from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .config import settings
from .routes import admin, analyze, auth, health, history, share, tools, tracker
from .utils.db import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="CompanyIQ API",
    description="AI-powered career intelligence: company reports, cover letters, JD fit, and more",
    version="3.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(health.router,   prefix="/api", tags=["health"])
app.include_router(auth.router,     prefix="/api", tags=["auth"])
app.include_router(admin.router,    prefix="/api", tags=["admin"])
app.include_router(analyze.router,  prefix="/api", tags=["analyze"])
app.include_router(history.router,  prefix="/api", tags=["history"])
app.include_router(tools.router,    prefix="/api", tags=["tools"])
app.include_router(share.router,    prefix="/api", tags=["share"])
app.include_router(tracker.router,  prefix="/api", tags=["tracker"])

# Serve frontend (must come last)
_frontend = Path(__file__).parent.parent / "frontend"
if _frontend.exists():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")

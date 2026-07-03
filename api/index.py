# Vercel serverless entry point.
# This file makes the FastAPI app discoverable by the @vercel/python builder.
import sys
import os

# Ensure the project root is on sys.path so `backend` package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.main import app  # noqa: F401  — Vercel looks for `app`

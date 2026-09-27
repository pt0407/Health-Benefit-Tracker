import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
PROGRAMS_DIR = DATA_DIR / "programs"
CHROMA_DIR = DATA_DIR / "chroma_db"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# Single place to change the Claude model used by every component.
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# Comma-separated list of allowed frontend origins.
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

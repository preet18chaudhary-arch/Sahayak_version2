import os
from pathlib import Path

# Base directory for the backend
BASE_DIR = Path(__file__).resolve().parent.parent

# Temporary uploads folder
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# CORS configuration
_cors_env = os.getenv("CORS_ORIGINS", "")
if _cors_env:
    CORS_ORIGINS = [origin.strip() for origin in _cors_env.split(",") if origin.strip()]
else:
    CORS_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ]

# API Configuration
PROJECT_NAME = "Sahayak Verification Engine"
VERSION = "0.1.0"
API_PREFIX = "/api"

# OCR and PDF Configuration
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")
MAX_FILE_SIZE_BYTES = int(os.getenv("MAX_FILE_SIZE_BYTES", str(15 * 1024 * 1024)))  # 15 MB
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "10"))
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}

# AI Key (to be configured in Step 2)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

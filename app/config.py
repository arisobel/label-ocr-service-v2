import os

def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
USE_GEMINI_FALLBACK = env_bool("USE_GEMINI_FALLBACK", False)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
GEMINI_MIN_CONFIDENCE = float(os.getenv("GEMINI_MIN_CONFIDENCE", "70"))
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "").strip()

import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "user_data"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
BROWSER_PROFILE_DIR = DATA_DIR / "browser_profile"
DB_PATH = DATA_DIR / "tiktok_bot.db"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseModel):
    app_name: str = "TikTok Auto DM Pro"
    version: str = "1.0.0"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", 8000))
    headless: bool = os.getenv("HEADLESS", "true").lower() in ("true", "1", "yes")
    auto_start: bool = os.getenv("AUTO_START", "true").lower() in ("true", "1", "yes")
    check_interval: int = int(os.getenv("CHECK_INTERVAL", 12)) # seconds between inbox checks
    human_delay_min: float = float(os.getenv("HUMAN_DELAY_MIN", 1.5))
    human_delay_max: float = float(os.getenv("HUMAN_DELAY_MAX", 4.0))
    max_dm_per_hour: int = int(os.getenv("MAX_DM_PER_HOUR", 40))
    default_cooldown: int = int(os.getenv("DEFAULT_COOLDOWN", 3600)) # 1 hour per user per rule

settings = Settings()

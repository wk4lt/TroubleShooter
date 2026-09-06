import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    def __init__(self):
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "deepseek-chat")
        self.agent_max_iterations = int(os.getenv("AGENT_MAX_ITERATIONS", "10"))
        self.session_ttl_seconds = int(os.getenv("SESSION_TTL_SECONDS", "1800"))
        self.skills_dir = os.getenv(
            "SKILLS_DIR",
            str(BASE_DIR / "skills"),
        )


settings = Settings()

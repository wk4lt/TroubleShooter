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
        self.openviking_url = os.getenv("OPENVIKING_URL", "http://127.0.0.1:1933")
        self.openviking_api_key = os.getenv("OPENVIKING_API_KEY", "")
        self.openviking_timeout_seconds = float(
            os.getenv("OPENVIKING_TIMEOUT_SECONDS", "30")
        )
        self.openviking_resource_uri = os.getenv(
            "OPENVIKING_RESOURCE_URI", "viking://resources/troubleshooter"
        )
        self.openviking_session_token_budget = int(
            os.getenv("OPENVIKING_SESSION_TOKEN_BUDGET", "12000")
        )
        self.skills_dir = os.getenv(
            "SKILLS_DIR",
            str(BASE_DIR / "skills"),
        )
        self.rag_knowledge_dir = os.getenv(
            "RAG_KNOWLEDGE_DIR",
            str(BASE_DIR / "data" / "knowledge"),
        )
        self.tool_max_file_read_bytes = int(
            os.getenv("TOOL_MAX_FILE_READ_BYTES", str(20 * 1024 * 1024))
        )
        self.tool_max_file_read_chars = int(
            os.getenv("TOOL_MAX_FILE_READ_CHARS", "12000")
        )
        self.tool_max_file_read_lines = int(
            os.getenv("TOOL_MAX_FILE_READ_LINES", "200")
        )
        self.tool_max_write_chars = int(
            os.getenv("TOOL_MAX_WRITE_CHARS", "200000")
        )


settings = Settings()

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent

DATABASE_DIR = PROJECT_ROOT / "database" / "db"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_PATH = DATABASE_DIR / "agent_system.db"

LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "agent_system.log"


class AzureConfig(BaseModel):
    api_key: str = Field(..., env="AZURE_OPENAI_API_KEY")
    endpoint: str = Field(..., env="AZURE_OPENAI_ENDPOINT")
    api_version: str = "2024-12-01-preview"
    analyst_model: str = Field(..., env="AZURE_OPENAI_DEPLOYMENT")
    coder_model: str = Field(..., env="AZURE_OPENAI_O4_MINI_DEPLOYMENT")
    embed_model: str = "text-embedding-3-large"

    @validator("api_key", "endpoint", "analyst_model", "coder_model")
    def not_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("Required configuration missing")
        return v


class TavilyConfig(BaseModel):
    api_key: str = Field(default="", env="TAVILY_API_KEY")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())


azure_config = AzureConfig(
    api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
    endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
    analyst_model=os.getenv("AZURE_OPENAI_DEPLOYMENT", ""),
    coder_model=os.getenv("AZURE_OPENAI_O4_MINI_DEPLOYMENT", ""),
)

tavily_config = TavilyConfig(api_key=os.getenv("TAVILY_API_KEY", ""))

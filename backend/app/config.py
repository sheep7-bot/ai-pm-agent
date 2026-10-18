from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

_ENV_FILES = (PROJECT_ROOT / ".env", BACKEND_DIR / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=tuple(str(p) for p in _ENV_FILES),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM：默认走 opencode-go 网关（OpenAI 兼容）。凭证只从环境变量读取，不写入代码。
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_API_KEY", "OPENCODE_GO_API_KEY"),
    )
    llm_base_url: str = Field(
        default="https://opencode.ai/inference/go/v1",
        validation_alias=AliasChoices("LLM_BASE_URL", "OPENCODE_GO_BASE_URL"),
    )
    llm_model: str = Field(
        default="deepseek-v4.1-flash",
        validation_alias=AliasChoices("LLM_MODEL", "OPENCODE_GO_MODEL"),
    )
    llm_user_agent: str = "ai-pm-agent/1.0"

    tavily_api_key: str = ""

    app_db_path: str = "./data/app.db"
    checkpoint_db_path: str = "./data/checkpoints.db"

    cors_origins: str = "*"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key and not self.llm_api_key.startswith("sk-your"))

    @property
    def search_enabled(self) -> bool:
        return bool(self.tavily_api_key and not self.tavily_api_key.startswith("tvly-your"))

    def ensure_dirs(self) -> None:
        Path(self.app_db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.checkpoint_db_path).parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if not Path(s.app_db_path).is_absolute():
        s.app_db_path = str(PROJECT_ROOT / s.app_db_path)
    if not Path(s.checkpoint_db_path).is_absolute():
        s.checkpoint_db_path = str(PROJECT_ROOT / s.checkpoint_db_path)
    s.ensure_dirs()
    return s

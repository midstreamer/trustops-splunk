"""Load TrustOps backend settings from environment (no hardcoded credentials)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Splunk and service configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    splunk_host: str = Field(default="localhost")
    splunk_port: int = Field(default=8089)
    splunk_scheme: str = Field(default="https")
    splunk_user: str = Field(default="")
    splunk_password: str = Field(default="")
    splunk_password_file: str = Field(default="")
    splunk_verify_ssl: bool = Field(default=False)
    splunk_auth_index: str = Field(default="trustops")
    splunk_decision_index: str = Field(default="trustops_decisions")
    splunk_agent_run_index: str = Field(default="trustops_agent_runs")
    splunk_event_host: str = Field(default="trustops-api")

    splunk_mcp_url: str = Field(
        default="http://localhost:8000/en-US/splunkd/__raw/services/mcp",
    )
    splunk_mcp_token: str = Field(default="")
    splunk_mcp_token_file: str = Field(default="~/.splunk_mcp_token")
    # MCP saia_* tools use SAIA v2 cloud APIs that often return HTTP 400 on CMP stacks.
    saia_use_mcp: bool = Field(default=False)
    saia_source_app_id: str = Field(default="search")
    saia_predict_timeout_seconds: float = Field(default=45.0)
    saia_chat_timeout_seconds: float = Field(default=90.0)
    saia_predict_poll_interval_seconds: float = Field(default=1.0)

    def splunk_base_url(self) -> str:
        return f"{self.splunk_scheme}://{self.splunk_host}:{self.splunk_port}"

    def effective_splunk_password(self) -> str:
        if self.splunk_password.strip():
            return self.splunk_password.strip()
        path_str = self.splunk_password_file.strip()
        if not path_str:
            default = Path.home() / ".splunk_pass"
            if default.is_file():
                path_str = str(default)
        if path_str:
            path = Path(path_str).expanduser()
            if path.is_file():
                return path.read_text(encoding="utf-8").strip()
        return ""

    def splunk_credentials_configured(self) -> bool:
        return bool(self.splunk_user.strip() and self.effective_splunk_password())

    def splunk_mcp_configured(self) -> bool:
        if self.splunk_mcp_token.strip():
            return True
        return Path(self.splunk_mcp_token_file).expanduser().is_file()


@lru_cache
def get_settings() -> Settings:
    return Settings()

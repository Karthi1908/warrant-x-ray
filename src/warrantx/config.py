"""Configuration management and settings for Warrant X-Ray."""

from functools import lru_cache
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"

class Settings(BaseSettings):
    """Application settings loaded from environment variables prefixed with WX_."""

    model_config = SettingsConfigDict(
        env_prefix="WX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Provider Credentials & Gateways
    nebius_api_key: Optional[str] = Field(default=None, description="API Key for Nebius Token Factory")
    nebius_base_url: str = Field(default="https://api.tokenfactory.nebius.com/v1/", description="Nebius Token Factory endpoint")
    tavily_api_key: Optional[str] = Field(default=None, description="API Key for Tavily Search")
    tavily_daily_credits: int = Field(default=200, description="Daily credit consumption limit for Tavily")

    # Bursa Ingestion & Storage
    mibb_base_url: Optional[str] = Field(default=None, description="Source data screener endpoint")
    source_enabled: bool = Field(default=True, description="Master kill-switch for automated collection")
    db_url: str = Field(default="sqlite+aiosqlite:///data/warrantx.db", description="Database connection URI")

    # Quant Engine & Financial Benchmarks
    risk_free_rate: float = Field(default=0.03, description="Annual risk-free benchmark rate (FR-023, OI-08)")

    # Safety Guardrails, Rate Limits, and Budgets
    llm_daily_usd_cap: float = Field(default=10.0, description="Daily LLM spending budget in USD")
    rate_limit_chat_per_hour: int = Field(default=30, description="Max chat turns allowed per client per hour")
    turn_timeout_s: int = Field(default=60, description="Hard wall-clock timeout for a chat turn in seconds")

    # Experiments and Feature Flags
    stream_draft: bool = Field(default=False, description="Send unverified draft stream tokens (off by default)")
    feature_chatter: bool = Field(default=False, description="Enable forum chatter context (off by default)")
    tavily_research: bool = Field(default=False, description="Enable Tavily deep research (off by default)")
    tavily_crawl: bool = Field(default=False, description="Enable Tavily crawl (off by default)")

    # Operational Mode and Models
    mode: str = Field(default="sample", description="Operational mode: live, replay, sample")
    model_nano: str = Field(default="nemotron-3-nano", description="Nano tier model ID")
    model_super: str = Field(default="nemotron-3-super", description="Super tier model ID")
    model_ultra: str = Field(default="nemotron-3-ultra", description="Ultra tier model ID")

    admin_token: Optional[str] = Field(default=None, description="Bearer token to access operator admin routes")
    environment: str = Field(default="development", description="Environment: development, test, production")
    session_secret: str = Field(default="default-daily-salt-change-in-prod", description="Salt for hashing client IPs/UAs")
    log_level: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR")
    log_json: bool = Field(default=True, description="Output structured logs in JSON format")
    llm_stub: bool = Field(default=False, description="Use stub model responses for offline integration testing")

    @property
    def ENVIRONMENT(self) -> str:
        return self.environment

    @property
    def NEBIUS_API_KEY(self) -> Optional[str]:
        return self.nebius_api_key

    @property
    def NEBIUS_BASE_URL(self) -> str:
        return self.nebius_base_url

    @property
    def database_url(self) -> str:
        """Alias for db_url."""
        return self.db_url

    @field_validator("risk_free_rate")
    @classmethod
    def validate_rate(cls, v: float) -> float:
        if v < 0.0 or v > 0.50:
            raise ValueError("risk_free_rate must be between 0.0 and 0.50 (0% to 50%)")
        return v


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()


def _load_yaml(filename: str) -> Dict[str, Any]:
    file_path = CONFIG_DIR / filename
    if not file_path.exists():
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def load_flags() -> Dict[str, Any]:
    """Load flags and thresholds from config/flags.yaml with safe fallbacks."""
    flags = _load_yaml("flags.yaml")
    defaults = {
        "risk_free_rate": 0.03,
        "low_liquidity_spread_pct": 0.10,
        "zero_bid_quote_flag": True,
        "high_decay_theta_pct": 0.02,
        "approaching_expiry_days": 14,
        "high_effective_gearing": 10.0,
        "deep_otm_moneyness": 0.80,
        "issuer_mismatch": {
            "iv_points": 3.0,
            "effective_gearing_pct": 0.15,
            "delta": 0.10,
        },
    }
    defaults.update(flags)
    return defaults


def load_linter_patterns() -> Dict[str, List[str]]:
    """Load regex patterns for advice refusal in English and Malay."""
    data = _load_yaml("linter_patterns.yaml")
    return data.get("prohibited_patterns", {"en": [], "ms": []})


def load_samples() -> List[Dict[str, Any]]:
    """Load sample prompts for user guidance and replay tests."""
    data = _load_yaml("samples.yaml")
    return data.get("sample_prompts", [])


def load_bursa_holidays() -> Dict[str, List[Dict[str, str]]]:
    """Load 2026-2027 Bursa Malaysia holiday calendars."""
    data = _load_yaml("bursa_holidays.yaml")
    return data.get("calendar", {})

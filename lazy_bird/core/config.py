"""Application configuration using Pydantic Settings.

This module loads configuration from environment variables (.env file)
and provides type-safe access to all application settings.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings can be overridden via environment variables or .env file.
    See .env.example for all available configuration options.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown env vars
    )

    # -------------------------------------------------------------------------
    # DATABASE CONFIGURATION
    # -------------------------------------------------------------------------
    DATABASE_URL: str = Field(
        default="postgresql://lazy_bird:lazy_bird@localhost:5432/lazy_bird",
        description="PostgreSQL connection string"
    )
    DB_POOL_SIZE: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Database connection pool size"
    )
    DB_MAX_OVERFLOW: int = Field(
        default=10,
        ge=0,
        le=50,
        description="Maximum overflow connections"
    )
    DB_POOL_TIMEOUT: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Connection pool timeout in seconds"
    )
    DB_POOL_RECYCLE: int = Field(
        default=3600,
        ge=300,
        le=7200,
        description="Recycle connections after N seconds"
    )
    DB_ECHO: bool = Field(
        default=False,
        description="Echo SQL queries to console (development only)"
    )

    # -------------------------------------------------------------------------
    # REDIS CONFIGURATION
    # -------------------------------------------------------------------------
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection string for caching and Celery"
    )

    # -------------------------------------------------------------------------
    # CELERY CONFIGURATION
    # -------------------------------------------------------------------------
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Celery broker URL (Redis)"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/1",
        description="Celery result backend URL"
    )
    CELERY_TASK_ALWAYS_EAGER: bool = Field(
        default=False,
        description="Execute tasks immediately in tests"
    )

    # -------------------------------------------------------------------------
    # API CONFIGURATION
    # -------------------------------------------------------------------------
    API_TITLE: str = Field(
        default="Lazy-Bird API",
        description="API title shown in docs"
    )
    API_VERSION: str = Field(
        default="2.0.0",
        description="API version"
    )
    API_DESCRIPTION: str = Field(
        default="Automated development workflow orchestration with Claude Code",
        description="API description"
    )
    API_HOST: str = Field(
        default="0.0.0.0",
        description="API host to bind to"
    )
    API_PORT: int = Field(
        default=8000,
        ge=1024,
        le=65535,
        description="API port to bind to"
    )
    API_WORKERS: int = Field(
        default=4,
        ge=1,
        le=16,
        description="Number of Uvicorn workers"
    )
    API_RELOAD: bool = Field(
        default=False,
        description="Enable auto-reload (development only)"
    )
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Comma-separated list of allowed CORS origins"
    )

    # -------------------------------------------------------------------------
    # SECURITY CONFIGURATION
    # -------------------------------------------------------------------------
    SECRET_KEY: str = Field(
        default="your-secret-key-here-change-in-production-use-openssl-rand-hex-32",
        min_length=32,
        description="Secret key for JWT signing"
    )
    API_KEY_SALT: str = Field(
        default="your-api-key-salt-here-change-in-production",
        min_length=16,
        description="Salt for API key hashing"
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    JWT_EXPIRATION_MINUTES: int = Field(
        default=15,
        ge=5,
        le=1440,
        description="JWT access token expiration in minutes"
    )
    PASSWORD_MIN_LENGTH: int = Field(
        default=12,
        ge=8,
        le=128,
        description="Minimum password length for validation"
    )
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60,
        ge=1,
        le=10000,
        description="Maximum requests per minute per client (IP or API key)"
    )

    # -------------------------------------------------------------------------
    # CLAUDE API CONFIGURATION
    # -------------------------------------------------------------------------
    CLAUDE_API_KEY: Optional[str] = Field(
        default=None,
        description="Anthropic Claude API key"
    )
    CLAUDE_MODEL: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Claude model to use for tasks"
    )
    CLAUDE_MAX_TOKENS: int = Field(
        default=8192,
        ge=1024,
        le=200000,
        description="Maximum tokens per Claude request"
    )
    CLAUDE_TEMPERATURE: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Claude temperature (0.0-1.0)"
    )

    # -------------------------------------------------------------------------
    # TASK EXECUTION CONFIGURATION
    # -------------------------------------------------------------------------
    MAX_PARALLEL_TASKS: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum parallel task executions"
    )
    TASK_TIMEOUT_SECONDS: int = Field(
        default=3600,
        ge=300,
        le=7200,
        description="Task execution timeout in seconds"
    )
    WORKTREE_BASE_PATH: str = Field(
        default="/tmp/lazy-bird-worktrees",
        description="Base path for git worktrees"
    )
    TASK_RETRY_MAX: int = Field(
        default=3,
        ge=0,
        le=5,
        description="Maximum task retry attempts"
    )
    TASK_RETRY_DELAY_SECONDS: int = Field(
        default=60,
        ge=10,
        le=300,
        description="Delay between retry attempts"
    )

    # -------------------------------------------------------------------------
    # COST TRACKING CONFIGURATION
    # -------------------------------------------------------------------------
    COST_PER_1K_INPUT_TOKENS: float = Field(
        default=0.003,
        ge=0.0,
        description="Cost per 1K input tokens (USD)"
    )
    COST_PER_1K_OUTPUT_TOKENS: float = Field(
        default=0.015,
        ge=0.0,
        description="Cost per 1K output tokens (USD)"
    )
    MAX_COST_PER_TASK: float = Field(
        default=5.0,
        ge=0.1,
        le=50.0,
        description="Maximum cost per task (USD)"
    )
    DAILY_COST_LIMIT: float = Field(
        default=50.0,
        ge=1.0,
        le=1000.0,
        description="Daily cost limit across all tasks (USD)"
    )
    COST_ALERT_THRESHOLD: float = Field(
        default=0.8,
        ge=0.1,
        le=1.0,
        description="Alert when cost reaches this fraction of limit"
    )

    # -------------------------------------------------------------------------
    # GIT CONFIGURATION
    # -------------------------------------------------------------------------
    GITHUB_TOKEN: Optional[str] = Field(
        default=None,
        description="GitHub personal access token for API access"
    )
    GITLAB_TOKEN: Optional[str] = Field(
        default=None,
        description="GitLab personal access token for API access"
    )
    GIT_USER_NAME: str = Field(
        default="Lazy-Bird Bot",
        description="Git commit author name"
    )
    GIT_USER_EMAIL: str = Field(
        default="bot@lazy-bird.dev",
        description="Git commit author email"
    )

    # -------------------------------------------------------------------------
    # LOGGING CONFIGURATION
    # -------------------------------------------------------------------------
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    LOG_FORMAT: str = Field(
        default="json",
        description="Log format (json or text)"
    )
    LOG_FILE: Optional[str] = Field(
        default=None,
        description="Log file path (None for stdout only)"
    )

    # -------------------------------------------------------------------------
    # WEBHOOK CONFIGURATION
    # -------------------------------------------------------------------------
    WEBHOOK_SECRET: Optional[str] = Field(
        default=None,
        min_length=16,
        description="Webhook signature secret for validation"
    )
    WEBHOOK_TIMEOUT_SECONDS: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Webhook delivery timeout"
    )

    # -------------------------------------------------------------------------
    # MONITORING CONFIGURATION
    # -------------------------------------------------------------------------
    ENABLE_METRICS: bool = Field(
        default=False,
        description="Enable Prometheus metrics endpoint"
    )
    METRICS_PORT: int = Field(
        default=9090,
        ge=1024,
        le=65535,
        description="Prometheus metrics port"
    )

    # -------------------------------------------------------------------------
    # DEVELOPMENT SETTINGS
    # -------------------------------------------------------------------------
    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode (development only)"
    )
    TESTING: bool = Field(
        default=False,
        description="Enable testing mode"
    )

    # -------------------------------------------------------------------------
    # VALIDATORS
    # -------------------------------------------------------------------------

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}")
        return v_upper

    @field_validator("LOG_FORMAT")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format is valid."""
        allowed = {"json", "text"}
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"LOG_FORMAT must be one of {allowed}")
        return v_lower

    # -------------------------------------------------------------------------
    # COMPUTED PROPERTIES
    # -------------------------------------------------------------------------

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.DEBUG or self.API_RELOAD

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.is_development and not self.TESTING


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Uses LRU cache to ensure settings are only loaded once.
    Call this function to access settings throughout the application.

    Returns:
        Settings instance with all configuration loaded

    Example:
        ```python
        from lazy_bird.core.config import get_settings

        settings = get_settings()
        print(settings.DATABASE_URL)
        ```
    """
    return Settings()


# Convenience: Pre-instantiated settings object for imports
settings = get_settings()

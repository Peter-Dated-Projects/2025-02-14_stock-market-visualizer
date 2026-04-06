"""
Pydantic Settings — reads from environment variables (.env files).
All config is centralized here and injected via FastAPI dependency.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # --- App ---
    app_env: str = Field(default="staging", alias="APP_ENV")

    # --- Polygon.io ---
    polygon_api_key: str = Field(default="", alias="POLYGON_API_KEY")
    polygon_base_url: str = Field(default="https://api.polygon.io", alias="POLYGON_BASE_URL")

    # --- IBKR ---
    ibkr_enabled: bool = Field(default=False, alias="IBKR_ENABLED")
    ibkr_host: str = Field(default="127.0.0.1", alias="IBKR_HOST")
    ibkr_port: int = Field(default=7497, alias="IBKR_PORT")
    ibkr_client_id: int = Field(default=1, alias="IBKR_CLIENT_ID")

    # --- Paper Trading ---
    paper_trade_enabled: bool = Field(default=True, alias="PAPER_TRADE_ENABLED")
    paper_trade_initial_balance: float = Field(default=100000.00, alias="PAPER_TRADE_INITIAL_BALANCE")

    # --- MySQL ---
    mysql_host: str = Field(default="localhost", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_database: str = Field(default="smv_trades", alias="MYSQL_DATABASE")
    mysql_user: str = Field(default="smv_user", alias="MYSQL_USER")
    mysql_password: str = Field(default="", alias="MYSQL_PASSWORD")

    # --- Redis ---
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD")

    # --- MongoDB ---
    mongo_host: str = Field(default="localhost", alias="MONGO_HOST")
    mongo_port: int = Field(default=27017, alias="MONGO_PORT")
    mongo_user: str = Field(default="smv_mongo", alias="MONGO_USER")
    mongo_password: str = Field(default="", alias="MONGO_PASSWORD")
    mongo_database: str = Field(default="smv", alias="MONGO_DATABASE")

    # --- Ollama ---
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="gemma4:e4b", alias="OLLAMA_MODEL")

    @property
    def mysql_url(self) -> str:
        """Async MySQL connection string for SQLAlchemy."""
        return (
            f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @property
    def mysql_url_sync(self) -> str:
        """Sync MySQL connection string for Alembic migrations."""
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"

    @property
    def mongo_url(self) -> str:
        """MongoDB connection URL."""
        return (
            f"mongodb://{self.mongo_user}:{self.mongo_password}"
            f"@{self.mongo_host}:{self.mongo_port}/{self.mongo_database}"
            f"?authSource=admin"
        )

    @property
    def is_staging(self) -> bool:
        return self.app_env == "staging"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }


# Singleton — imported by other modules
settings = Settings()

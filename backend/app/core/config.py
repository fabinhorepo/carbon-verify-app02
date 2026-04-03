"""Configurações centrais da aplicação Carbon Verify - Produção."""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Carbon Verify"
    APP_VERSION: str = "2.0.0"
    APP_DESCRIPTION: str = "Plataforma B2B SaaS de verificação e due diligence de créditos de carbono"

    # Database - PostgreSQL em produção, SQLite em dev
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./carbon_verify.db")

    # Server
    PORT: int = int(os.getenv("PORT", "10000"))

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # API
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    CORS_ORIGINS_RAW: str = os.getenv("CORS_ORIGINS", "*")

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))

    # External APIs
    NASA_FIRMS_API_KEY: str = os.getenv("NASA_FIRMS_API_KEY", "")
    COPERNICUS_API_KEY: str = os.getenv("COPERNICUS_API_KEY", "")
    VERRA_API_BASE: str = "https://registry.verra.org/uiapi"
    GS_API_BASE: str = "https://registry.goldstandard.org/api"

    # Web3
    WEB3_RPC_URL: str = os.getenv("WEB3_RPC_URL", "https://polygon-rpc.com")
    TOUCAN_SUBGRAPH_URL: str = "https://api.thegraph.com/subgraphs/name/toucanprotocol/matic"

    class Config:
        env_file = ".env"
        case_sensitive = True

    def get_cors_origins(self) -> list[str]:
        raw = self.CORS_ORIGINS_RAW.strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    @property
    def is_postgres(self) -> bool:
        return "postgres" in self.DATABASE_URL

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql://chargesure:chargesure@localhost:5432/chargesure"

    # Auth
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # Routing
    osrm_base_url: str = "http://localhost:5000"
    google_directions_api_key: str = ""

    # External data
    openchargemap_api_key: str = ""
    openchargemap_base_url: str = "https://api.openchargemap.io/v3"

    # ML
    reliability_model_path: str = "app/ml/artifacts/reliability_model.json"
    reliability_prior_baseline: float = 0.82

    # Beckn / UBC
    beckn_bap_id: str = "chargesure.runtimerebels"
    beckn_bap_uri: str = "https://api.chargesure.app/beckn"
    beckn_ubc_gateway_url: str = "https://gateway.ubc.gov.in"

    # Rate limiting
    rate_limit_per_minute: int = 60

    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()

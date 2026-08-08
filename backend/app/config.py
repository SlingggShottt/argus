"""Central place for every tunable value in the app. Nothing outside this file
reads an environment variable directly — that keeps config sources traceable
to one spot instead of scattered os.getenv() calls."""

from pydantic_settings import BaseSettings, SettingsConfigDict

# BaseSettings automatically reads environment variables and populates typed fields.
# It also validates types at startup. If any field is not valid the app fails at startup itself.
class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://argus:argus@localhost:5432/argus"

    # LLM (Groq)
    groq_api_key: str = ""
    llm_model: str = "llama-3.3-70b-versatile"

    # Forecast / risk tunables
    forecast_horizon_days: int = 30
    stockout_risk_threshold: float = 0.9
    anomaly_zscore_threshold: float = 2.5

    # Inventory synthesis (dataset has no real inventory data, see context.md)
    lead_time_days: int = 7
    inventory_lookback_days: int = 90
    inventory_days_of_cover_min: int = 3
    inventory_days_of_cover_max: int = 21
    inventory_random_seed: int = 42

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings() # This instance is imported everywhere.

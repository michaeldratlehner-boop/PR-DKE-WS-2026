from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Hauptordner des Repos (config.py liegt in harness/app/)
REPO_ROOT = Path(__file__).resolve().parents[2]

# liest die Werte aus der env und ignoriert zusätzliche Einträge
class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    gemini_api_key: str

    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")


settings = Settings()
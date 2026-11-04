from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Hauptordner des Repos (config.py liegt in harness/app/)
REPO_ROOT = Path(__file__).resolve().parents[2]

# liest die Werte aus der env und ignoriert zusätzliche Einträge
class Settings(BaseSettings):
    supabase_url: str
    supabase_key: str
    gemini_api_key: str
    gemini_model: str

    # Origins, die den Harness im Browser aufrufen dürfen (Frontend, Vite)
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")


settings = Settings()
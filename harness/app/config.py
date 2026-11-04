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

    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")
    default_system_prompt: str = "Du bist ein hilfreicher Assistent für Haushaltsgeräte. Antworte auf Deutsch."
    fallback_models: list[str] = ["gemini-3.6-flash", "gemini-3.8-flash","gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-8b"]

settings = Settings()
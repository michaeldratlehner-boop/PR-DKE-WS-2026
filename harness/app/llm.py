from google import genai
from google.genai import types

from app.config import settings

# Ein Client für die ganze Anwendung
_client = genai.Client(api_key=settings.gemini_api_key)

#Erstes Testsetup
def generiere_antwort(prompt: str, system: str | None = None) -> str:
    """Schickt einen Text an Gemini und gibt die Antwort als Text zurück."""
    antwort = _client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=system),
    )
    return antwort.text or ""
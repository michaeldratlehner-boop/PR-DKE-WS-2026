from google import genai
from typing import AsyncGenerator
from app.config import settings
from google.genai import types, errors  # 'errors' für das Exception-Handling importieren

# Ein Client für die ganze Anwendung
_client = genai.Client(api_key=settings.gemini_api_key)


#Erstes Testsetup
#def generiere_antwort(prompt: str, system: str | None = None) -> str:
#    """Schickt einen Text an Gemini und gibt die Antwort als Text zurück."""
#    antwort = _client.models.generate_content(
#        model=settings.gemini_model,
#        contents=prompt,
#        config=types.GenerateContentConfig(system_instruction=system),
#    )
#    return antwort.text or ""

async def generiere_antwort_async_stream(prompt: str, system: str | None = None) -> AsyncGenerator[str, None]:
    # Verwende den übergebenen Prompt oder falle auf den Default aus der Config zurück
    active_system_prompt = system or settings.default_system_prompt

    # Erstelle eine Liste aus dem Hauptmodell und den Fallbacks
    modelle_zum_testen = [settings.gemini_model] + settings.fallback_models

    for model_name in modelle_zum_testen:
        try:
            stream = await _client.aio.models.generate_content_stream(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(system_instruction=active_system_prompt),
            )

            erstes_chunk = True
            async for chunk in stream:
                # Erst wenn das Modell wirklich liefert, geben wir die Info aus
                if erstes_chunk:
                    yield f"[Info: Antwort generiert mit {model_name}]\n"
                    erstes_chunk = False

                if chunk.text:
                    yield chunk.text

            # Wenn der Stream komplett fehlerfrei durchläuft, beenden
            return

        except errors.APIError as e:
            print(f"Warnung: Modell {model_name} fehlgeschlagen ({e}). Wechsle zum nächsten Modell...")
            letzter_fehler = e
            continue  # Springe zum nächsten Modell in der Liste

        # Wenn alle Modelle fehlschlagen, werfe den letzten Fehler oder gib eine Meldung aus
    yield "Entschuldigung, derzeit sind alle KI-Modelle überlastet. Bitte versuche es später noch einmal."
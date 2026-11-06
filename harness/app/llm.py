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


async def generiere_wartungsantwort(frage: str, absaetze: list[dict]) -> str:
    """Baut den Kontext auf und holt die Antwort von Gemini."""

    # System-Prompt exakt nach den Vorgaben aus dem Dokument "Durchstich 10. November"
    wartung_system_prompt = """Du bist ein technischer Wartungsberater für Haushaltsgeräte.
BEFOLGE DIESE REGELN STRIKT:
1. Du darfst ausschließlich aus den übergebenen Absätzen antworten.
2. Wenn die Antwort nicht in den Absätzen steht, antworte exakt mit: 'weiß ich nicht'. Du darfst nicht raten!
3. SICHERHEITSREGEL: Bei Elektroreparaturen darfst du keine Anleitung geben, sondern musst auf den Kundendienst verweisen.
4. Du musst die Quelle (Seite und Abschnitt) in deine Antwort übernehmen (z.B. 'laut Seite 34, Abschnitt Störungen')."""

    # Kontext aus den Datenbank-Chunks bauen
    kontext_text = "HIER SIND DIE AUSZÜGE AUS DER BEDIENUNGSANLEITUNG:\n\n"
    for chunk in absaetze:
        seite = chunk.get("seite", "Unbekannt")
        abschnitt = chunk.get("abschnitt", "Unbekannt")
        inhalt = chunk.get("inhalt", "")
        kontext_text += f"--- Seite: {seite} | Abschnitt: {abschnitt} ---\n{inhalt}\n\n"

    # Die finale Nachricht an das LLM
    finaler_prompt = f"{kontext_text}\n\nFRAGE DES NUTZERS:\n{frage}"

    # Liste aus dem Hauptmodell und den Fallbacks erstellen
    modelle_zum_testen = [settings.gemini_model] + settings.fallback_models

    # Fallback-Schleife abarbeiten
    for model_name in modelle_zum_testen:
        try:
            antwort = await _client.aio.models.generate_content(
                model=model_name,
                contents=finaler_prompt,
                config=types.GenerateContentConfig(system_instruction=wartung_system_prompt),
            )
            return antwort.text or "weiß ich nicht"

        except errors.APIError as e:
            # Fehler in der Konsole loggen und zum nächsten Modell springen
            print(f"Warnung: Modell {model_name} fehlgeschlagen beim Wartungsassistenten ({e}). Wechsle...")
            continue

    return "Entschuldigung, derzeit sind alle KI-Modelle überlastet. Bitte versuche es später noch einmal."
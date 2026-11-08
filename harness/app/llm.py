from contextlib import nullcontext
from math import isfinite
from app.traces import modellversuch
from numbers import Real
from typing import Literal

from google import genai
from typing import AsyncGenerator
from app.config import settings
from google.genai import types, errors  # 'errors' für das Exception-Handling importieren


# Ein Client fuer die gesamte Anwendung.
_client = genai.Client(api_key=settings.gemini_api_key)

# Muss zur Datenbankspalte vector(768) passen.
EMBEDDING_DIMENSIONEN = 768
MAX_FLOAT32 = 3.4028234663852886e38


class EmbeddingFehler(RuntimeError):
    """Die API hat keinen verwendbaren Embedding-Vektor geliefert."""


def _embedding_modell() -> str:
    """Verwendet das separate Embedding-Modell, nicht das Antwortmodell."""
    modell = getattr(settings, "gemini_embedding_model", "gemini-embedding-2")
    if modell != "gemini-embedding-2":
        raise ValueError(
            "Diese Implementierung verwendet das Eingabeformat von gemini-embedding-2. "
            "Ein Modellwechsel benoetigt eine Anpassung und die Neuberechnung "
            "gespeicherter Embeddings."
        )
    return modell


def _embedding_eingabe(
    text: str,
    art: Literal["frage", "dokument"],
    titel: str | None,
) -> str:
    """Bereitet Fragen und Dokumentabschnitte fuer die Suche vor."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Fuer ein Embedding ist ein nicht leerer Text erforderlich.")
    if art == "frage":
        return f"task: search result | query: {text.strip()}"
    if art == "dokument":
        if titel is not None and not isinstance(titel, str):
            raise ValueError("Der Dokumenttitel muss Text oder None sein.")
        dokumenttitel = (titel or "").strip() or "none"
        return f"title: {dokumenttitel} | text: {text.strip()}"
    raise ValueError("art muss 'frage' oder 'dokument' sein.")


def _embedding_werte(antwort) -> list[float]:
    """Prueft die Antwort und liefert genau 768 gueltige Zahlen."""
    embeddings = getattr(antwort, "embeddings", None)
    if not embeddings or len(embeddings) != 1:
        raise EmbeddingFehler("Es wurde nicht genau ein Embedding zurueckgegeben.")
    werte = getattr(embeddings[0], "values", None)
    if werte is None or len(werte) != EMBEDDING_DIMENSIONEN:
        raise EmbeddingFehler("Das Embedding muss genau 768 Werte enthalten.")
    if any(
        isinstance(wert, bool)
        or not isinstance(wert, Real)
        or not isfinite(wert)
        or abs(wert) > MAX_FLOAT32
        for wert in werte
    ):
        raise EmbeddingFehler("Das Embedding enthaelt ungueltige Zahlen.")
    vektor = [float(wert) for wert in werte]
    if not any(wert != 0 for wert in vektor):
        raise EmbeddingFehler("Ein Nullvektor ist fuer die Cosine-Suche ungeeignet.")
    return vektor


def generiere_embedding(
    text: str,
    *,
    art: Literal["frage", "dokument"] = "frage",
    titel: str | None = None,
) -> list[float]:
    """Erzeugt synchron ein Embedding, etwa fuer die Datenaufbereitung."""
    eingabe = _embedding_eingabe(text, art, titel)
    antwort = _client.models.embed_content(
        model=_embedding_modell(),
        contents=eingabe,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONEN),
    )
    return _embedding_werte(antwort)


async def generiere_embedding_async(
    text: str,
    *,
    art: Literal["frage", "dokument"] = "frage",
    titel: str | None = None,
) -> list[float]:
    """Erzeugt asynchron ein Embedding fuer einen async-Backend-Ablauf."""
    eingabe = _embedding_eingabe(text, art, titel)
    antwort = await _client.aio.models.embed_content(
        model=_embedding_modell(),
        contents=eingabe,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONEN),
    )
    return _embedding_werte(antwort)

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


class WartungsmodellFehler(RuntimeError):
    """Keines der konfigurierten Antwortmodelle konnte antworten."""


async def generiere_wartungsantwort(
    frage: str, absaetze: list[dict], *, lauf: dict | None = None,
) -> str:
    """Bestehender Wartungsprompt und Fallback, mit optionalem JSONL-Trace."""
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


    if lauf is not None:
        lauf['finaler_prompt'] = {'system': wartung_system_prompt, 'user': finaler_prompt}
    for model_name in dict.fromkeys([settings.gemini_model] + settings.fallback_models):
        versuch_kontext = modellversuch(lauf, model_name) if lauf is not None else nullcontext()
        try:
            with versuch_kontext as versuch:
                antwort = await _client.aio.models.generate_content(
                    model=model_name, contents=finaler_prompt,
                    config=types.GenerateContentConfig(system_instruction=wartung_system_prompt),
                )
                usage = getattr(antwort, 'usage_metadata', None)
                if versuch is not None and usage is not None and hasattr(usage, 'model_dump'):
                    versuch['tokenverbrauch'] = usage.model_dump(mode='json', exclude_none=True)
                    lauf['tokenverbrauch'] = versuch['tokenverbrauch']
                return antwort.text or 'weiß ich nicht'
        except errors.APIError:
            continue
    raise WartungsmodellFehler('Alle konfigurierten Antwortmodelle fehlgeschlagen.')

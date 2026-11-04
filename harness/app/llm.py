from math import isfinite
from numbers import Real
from typing import Literal

from google import genai
from google.genai import types

from app.config import settings


# Ein Client fuer die gesamte Anwendung.
_client = genai.Client(api_key=settings.gemini_api_key)

# Muss zur Datenbankspalte vector(768) passen.
EMBEDDING_DIMENSIONEN = 768
MAX_FLOAT32 = 3.4028234663852886e38


def generiere_antwort(prompt: str, system: str | None = None) -> str:
    """Schickt einen Text an Gemini und gibt die Antwort als Text zurueck."""
    antwort = _client.models.generate_content(
        model=settings.gemini_model,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=system),
    )
    return antwort.text or ""


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

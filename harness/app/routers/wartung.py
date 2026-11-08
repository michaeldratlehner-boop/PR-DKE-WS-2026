import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.db import suche_wartungs_chunks
from app.llm import generiere_embedding_async, generiere_wartungsantwort
from app.schemas import Quelle, WartungAnfrage, WartungAntwort
from app.traces import trace_lauf


logger = logging.getLogger(__name__)
router = APIRouter(tags=["Wartung"])


def sammle_quellen(absaetze: list[dict]) -> list[Quelle]:
    """Übernimmt die Quellen der Suchtreffer und entfernt doppelte Einträge."""
    quellen = []
    gesehen = set()

    for absatz in absaetze:
        seite = absatz.get("seite")
        abschnitt = absatz.get("abschnitt")
        schluessel = (seite, abschnitt)

        if schluessel in gesehen:
            continue

        gesehen.add(schluessel)
        quellen.append(Quelle(seite=seite, abschnitt=abschnitt))

    return quellen


@router.post("/wartung", response_model=WartungAntwort)
async def wartung(anfrage: WartungAnfrage) -> WartungAntwort:
    """Erzeugt eine Antwort anhand der Anleitung des ausgewählten Geräts."""
    try:
        with trace_lauf(
            anfrage.frage,
            produkt_id=anfrage.produkt_id,
        ) as lauf:

            # 1. Frage in einen Embedding-Vektor umwandeln.
            lauf["embedding_modell"] = settings.gemini_embedding_model
            lauf["embedding_dimensionen"] = 768

            embedding = await generiere_embedding_async(
                anfrage.frage,
                art="frage",
            )

            # 2. Passende Textstellen zum ausgewählten Gerät suchen.
            # Der synchrone Datenbankzugriff läuft in einem separaten Thread.
            absaetze = await asyncio.to_thread(
                suche_wartungs_chunks,
                frage=anfrage.frage,
                produkt_id=anfrage.produkt_id,
                embedding=embedding,
            )

            # 3. Suchaufruf und Treffer im Trace speichern.
            lauf["retrieval_treffer"] = absaetze
            lauf["tool_aufrufe"].append({
                "name": "suche_chunks_hybrid",
                "parameter": {
                    "query_text": anfrage.frage,
                    "produkt_id": anfrage.produkt_id,
                    "treffer_limit": 5,
                },
                "treffer_anzahl": len(absaetze),
            })

            # 4. Nur bei vorhandenen Treffern das Antwortmodell aufrufen.
            text = "weiß ich nicht"

            if absaetze:
                text = await generiere_wartungsantwort(
                    anfrage.frage,
                    absaetze,
                    lauf=lauf,
                )

            normalisierter_text = text.strip().rstrip(".!?").casefold()
            gefunden = normalisierter_text not in (
                "weiß ich nicht",
                "weiss ich nicht",
            )

            quellen = []
            if gefunden:
                quellen = sammle_quellen(absaetze)

            # 5. API-Antwort erstellen und im Trace speichern.
            antwort = WartungAntwort(
                antwort=text,
                quellen=quellen,
                gefunden=gefunden,
                trace_id=lauf["trace_id"],
            )

            lauf["ausgabe"] = antwort.model_dump(mode="json")
            return antwort

    except Exception:
        logger.exception("Wartungsanfrage fehlgeschlagen")

        raise HTTPException(
            status_code=503,
            detail="Der Wartungsassistent ist derzeit nicht erreichbar.",
        ) from None
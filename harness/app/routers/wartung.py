import logging
from fastapi import APIRouter,HTTPException
from app.schemas import Quelle, WartungAnfrage, WartungAntwort
from app.db import suche_wartungs_chunks
from app.llm import generiere_wartungsantwort

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Wartung"])


@router.post("/wartung", response_model=WartungAntwort)
async def wartung(anfrage: WartungAnfrage) -> WartungAntwort:
    """Beantwortet eine Wartungsfrage anhand der Dokumenten-Chunks."""
    try:
        # 1. Chunks aus der Datenbank holen (aktuell über Volltext)
        # TODO: Später hier Embedding berechnen und an suche_wartungs_chunks übergeben
        gefundene_absaetze = suche_wartungs_chunks(anfrage.frage, anfrage.produkt_id)

        # 2. Wenn keine Absätze gefunden wurden
        if not gefundene_absaetze:
            return WartungAntwort(
                antwort="weiß ich nicht (Keine passenden Absätze in der Anleitung gefunden)",
                quellen=[]
            )

        # 3. Antwort über Gemini generieren
        antwort_text = await generiere_wartungsantwort(anfrage.frage, gefundene_absaetze)

        # 4. Quellen für die Rückgabe aufbereiten
        quellen = [
            Quelle(seite=chunk["seite"], abschnitt=chunk["abschnitt"])
            for chunk in gefundene_absaetze
        ]

        # 5. Traces wegschreiben (wie im Dokument gefordert)
        trace_daten = {
            "frage": anfrage.frage,
            "produkt_id": anfrage.produkt_id,
            "treffer_anzahl": len(gefundene_absaetze),
            "chunks": [{"rang": c["fts_rang"], "score": c["fts_score"], "seite": c["seite"]} for c in gefundene_absaetze]
        }
        logger.info(f"TRACE - Wartungsanfrage: {trace_daten}")

        return WartungAntwort(antwort=antwort_text, quellen=quellen)

    except Exception as e:
        logger.exception("Wartungssuche fehlgeschlagen")
        raise HTTPException(
            status_code=503,
            detail=f"Der Wartungsassistent ist derzeit nicht erreichbar: {e}",
        )
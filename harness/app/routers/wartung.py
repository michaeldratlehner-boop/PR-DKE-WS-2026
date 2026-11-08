import asyncio
import logging

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.db import suche_wartungs_chunks
from app.llm import generiere_wartungsantwort, generiere_embedding_async
from app.schemas import Quelle, WartungAnfrage, WartungAntwort
from app.traces import trace_lauf

logger = logging.getLogger(__name__)
router = APIRouter(tags=['Wartung'])


@router.post('/wartung', response_model=WartungAntwort)
async def wartung(anfrage: WartungAnfrage) -> WartungAntwort:
    """Frage einbetten, produktbezogen suchen, quellengebunden antworten."""
    try:
        with trace_lauf(anfrage.frage, produkt_id=anfrage.produkt_id) as lauf:
            lauf['embedding_modell'] = settings.gemini_embedding_model
            lauf['embedding_dimensionen'] = 768
            frage_embedding = await generiere_embedding_async(anfrage.frage, art='frage')
            # Der vorhandene Supabase-Client ist synchron.
            absaetze = await asyncio.to_thread(
                suche_wartungs_chunks, frage=anfrage.frage,
                produkt_id=anfrage.produkt_id, embedding=frage_embedding,
            )
            lauf['retrieval_treffer'] = absaetze
            lauf['tool_aufrufe'].append({
                'name': 'suche_chunks_hybrid',
                'parameter': {'query_text': anfrage.frage,
                              'produkt_id': anfrage.produkt_id, 'treffer_limit': 5},
                'treffer_anzahl': len(absaetze),
            })
            if not absaetze:
                antwort = WartungAntwort(
                    antwort='weiß ich nicht', quellen=[], gefunden=False,
                    trace_id=lauf['trace_id'],
                )
            else:
                text = await generiere_wartungsantwort(anfrage.frage, absaetze, lauf=lauf)
                gefunden = text.strip().rstrip('.!?').casefold() not in (
                    'weiß ich nicht', 'weiss ich nicht',
                )
                quellen = []
                if gefunden:
                    gesehen = set()
                    for chunk in absaetze:
                        schluessel = (chunk.get('seite'), chunk.get('abschnitt'))
                        if schluessel not in gesehen:
                            gesehen.add(schluessel)
                            quellen.append(Quelle(seite=schluessel[0], abschnitt=schluessel[1]))
                antwort = WartungAntwort(
                    antwort=text, quellen=quellen, gefunden=gefunden,
                    trace_id=lauf['trace_id'],
                )
            lauf['ausgabe'] = antwort.model_dump(mode='json')
            return antwort
    except Exception:
        logger.exception('Wartungsanfrage fehlgeschlagen')
        raise HTTPException(
            status_code=503,
            detail='Der Wartungsassistent ist derzeit nicht erreichbar.',
        ) from None

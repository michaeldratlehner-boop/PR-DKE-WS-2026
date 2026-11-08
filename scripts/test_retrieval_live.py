"""Prueft die echte produktbezogene Suche; erstellt keine neuen DB-Zeilen."""

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'harness'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--produkt-id', type=int, required=True)
    parser.add_argument('--text', default='Was bedeutet E18 bei meiner Waschmaschine?')
    parser.add_argument('--nur-volltext', action='store_true',
                        help='Vergleich ohne Gemini-Aufruf und ohne Fragevektor')
    args = parser.parse_args()
    if not args.live:
        parser.error('--live ist fuer echte externe Zugriffe erforderlich')
    if args.produkt_id < 1:
        parser.error('--produkt-id muss positiv sein')
    from app.config import settings
    from app.db import suche_wartungs_chunks
    from app.traces import trace_lauf

    async def ausfuehren():
        with trace_lauf(args.text, produkt_id=args.produkt_id, komponente='retrieval') as lauf:
            vektor = None
            if not args.nur_volltext:
                from app.llm import generiere_embedding_async
                lauf['embedding_modell'] = settings.gemini_embedding_model
                lauf['embedding_dimensionen'] = 768
                vektor = await generiere_embedding_async(args.text, art='frage')
            treffer = await asyncio.to_thread(
                suche_wartungs_chunks, frage=args.text,
                produkt_id=args.produkt_id, embedding=vektor,
            )
            lauf['retrieval_treffer'] = treffer
            lauf['ausgabe'] = {'chunk_ids': [t['chunk_id'] for t in treffer]}
            print(f"{len(treffer)} Treffer. Trace-ID: {lauf['trace_id']}")
            for t in treffer:
                print(f"Chunk {t['chunk_id']}, Dokument {t['dokument_id']}, Seite {t['seite']}; "
                      f"Wort-Rang={t['fts_rang']}, Vektor-Rang={t['vektor_rang']}, "
                      f"Distanz={t['vektor_distanz']}, RRF={t['rrf_score']}")
            print('Die fachliche Relevanz bitte gegen die Originalanleitung pruefen.')
    asyncio.run(ausfuehren())


if __name__ == '__main__':
    main()

"""Ergaenzt fehlende Chunk-Embeddings; behaelt Texte und IDs bei.

Ohne --schreiben: nur Datenbank lesen, keine Gemini-Aufrufe.
Mit --schreiben: nur Chunks mit embedding IS NULL bearbeiten.
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'harness'))


def fehlende_chunks(client, produkt_id=None):
    """ID-Paginierung bleibt auch beim Fuellen der NULL-Felder stabil."""
    letzte_id = 0
    while True:
        abfrage = (
            client.table('chunk')
            .select('id,inhalt,dokument_id,dokument!inner(titel,produkt_id)')
            .is_('embedding', 'null').gt('id', letzte_id).order('id').limit(100)
        )
        if produkt_id is not None:
            abfrage = abfrage.eq('dokument.produkt_id', produkt_id)
        zeilen = abfrage.execute().data or []
        if not zeilen:
            return
        for zeile in zeilen:
            letzte_id = zeile['id']
            yield zeile


def ergaenze_embeddings(client, embed, *, schreiben=False, produkt_id=None,
                        limit=None, pause=1.0):
    """embed wird nur beim Schreiben aufgerufen; fuer Offline-Tests austauschbar."""
    gefunden = gespeichert = 0
    for zeile in fehlende_chunks(client, produkt_id):
        if limit is not None and gefunden >= limit:
            break
        gefunden += 1
        if not schreiben:
            print(f"Chunk {zeile['id']}: Embedding fehlt.")
            continue
        if gespeichert and pause:
            time.sleep(pause)
        titel = (zeile.get('dokument') or {}).get('titel')
        vektor = embed(zeile['inhalt'], art='dokument', titel=titel)
        # Text kann zwischen Lesen und Schreiben geaendert worden sein.
        # Bereits anderweitig gespeicherte Embeddings werden nicht ueberschrieben.
        resultat = (
            client.table('chunk').update({'embedding': vektor})
            .eq('id', zeile['id']).eq('inhalt', zeile['inhalt'])
            .is_('embedding', 'null').execute()
        )
        if resultat.data:
            gespeichert += 1
            print(f"Chunk {zeile['id']}: {len(vektor)} Werte gespeichert.")
        else:
            print(f"Chunk {zeile['id']}: inzwischen geaendert; uebersprungen.")
    return gefunden, gespeichert


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schreiben', action='store_true')
    parser.add_argument('--produkt-id', type=int)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--pause', type=float, default=1.0,
                        help='Sekunden zwischen Gemini-Aufrufen; Standard 1')
    args = parser.parse_args()
    if args.produkt_id is not None and args.produkt_id < 1:
        parser.error('--produkt-id muss positiv sein')
    if args.limit is not None and args.limit < 1:
        parser.error('--limit muss positiv sein')
    if args.pause < 0:
        parser.error('--pause darf nicht negativ sein')
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    from app.config import settings
    from supabase import create_client
    client = create_client(settings.supabase_url, settings.supabase_key)
    embed = None
    if args.schreiben:
        from app.llm import generiere_embedding
        embed = generiere_embedding
    try:
        anzahl, gespeichert = ergaenze_embeddings(
            client, embed, schreiben=args.schreiben, produkt_id=args.produkt_id,
            limit=args.limit, pause=args.pause,
        )
    except Exception as fehler:
        print(f'Abbruch ({type(fehler).__name__}). Bereits gespeicherte Vektoren bleiben erhalten.')
        print('Bei Rate-Limit: spaeter mit groesserem --pause-Wert erneut starten.')
        return 1
    print(f'{anzahl} fehlende Embeddings gefunden; {gespeichert} gespeichert.')
    if not args.schreiben:
        print('Nur Vorschau. Mit --schreiben werden Gemini-Aufrufe und Updates ausgefuehrt.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

"""Opt-in-Smoke-Test nach Integration ins echte Repo. Fuehrt einen API-Aufruf aus."""

import argparse
import asyncio
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="einen echten Google-API-Aufruf ausfuehren")
    parser.add_argument("--asynchron", action="store_true", help="die async-Variante verwenden")
    parser.add_argument("--art", choices=["frage", "dokument"], default="frage")
    parser.add_argument("--text", default="Was bedeutet E18 bei meiner Waschmaschine?")
    parser.add_argument("--titel", default=None)
    args = parser.parse_args()
    if not args.live:
        parser.error("Ohne --live wird kein externer API-Aufruf ausgefuehrt.")

    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "harness"))
    from app.config import settings
    from app.llm import generiere_embedding, generiere_embedding_async
    from app.traces import trace_lauf

    async def ausfuehren():
        with trace_lauf(args.text, komponente="embedding") as lauf:
            lauf["embedding_modell"] = getattr(settings, "gemini_embedding_model", "gemini-embedding-2")
            lauf["embedding_dimensionen"] = 768
            lauf["modell"] = lauf["embedding_modell"]
            lauf["modell_parameter"] = {"output_dimensionality": 768, "art": args.art}
            lauf["finaler_prompt"] = (
                f"task: search result | query: {args.text.strip()}" if args.art == "frage"
                else f"title: {(args.titel or '').strip() or 'none'} | text: {args.text.strip()}"
            )
            if args.asynchron:
                vektor = await generiere_embedding_async(args.text, art=args.art, titel=args.titel)
            else:
                vektor = generiere_embedding(args.text, art=args.art, titel=args.titel)
            lauf["ausgabe"] = {"vektor": vektor}
            print(f"Erfolgreich: {len(vektor)} gueltige Zahlen. Trace-ID: {lauf['trace_id']}")

    asyncio.run(ausfuehren())


if __name__ == "__main__":
    main()

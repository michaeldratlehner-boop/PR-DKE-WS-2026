import asyncio
from app.llm import generiere_antwort_async_stream


async def main():
    print("Starte Anfrage...")
    # Da wir 'system' weglassen, zieht er automatisch den Default aus der config.py
    stream = generiere_antwort_async_stream(
        prompt="Erkläre in einem Satz, wofür eine Waschmaschine das Fliesensieb hat."
    )

    async for chunk in stream:
        # flush=True zwingt die Konsole, den Text sofort auszugeben
        print(chunk, end="", flush=True)
    print("\nFertig.")


asyncio.run(main())
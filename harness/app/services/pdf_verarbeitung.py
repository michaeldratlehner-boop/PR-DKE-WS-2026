import os
import sys
from pathlib import Path

from app.config import REPO_ROOT
from app.db import _client as client
from app.llm import generiere_embedding

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.chunks_erstellen import alte_chunks_loeschen, dokument_zerlegen
from scripts.embeddings_ergaenzen import ergaenze_embeddings

BUCKET = os.getenv("SUPABASE_BUCKET", "anleitungen")


def extrahiere_produkt(dateiname: str):
    """Liest Hersteller und Modell aus dem Dateinamen (z.B. 'Miele_W1.pdf')."""
    name_ohne_ext = Path(dateiname).stem
    teile = name_ohne_ext.replace("_", " ").split(" ", 1)
    if len(teile) == 2:
        return teile[0].strip(), teile[1].strip()
    return "Unbekannt", name_ohne_ext.strip()


def speichere_pdf_und_datenbank(dateiname: str, datei_bytes: bytes) -> tuple[int, int, str]:
    """Speichert das PDF in Storage und legt die DB-Zeilen an (Produkt, Dokument). Gibt (produkt_id, dokument_id, datei_pfad) zurück."""
    hersteller, modell = extrahiere_produkt(dateiname)

    # 1. Produkt sicherstellen
    treffer = client.table("produkt").select("id").eq("hersteller", hersteller).eq("modell", modell).limit(1).execute()
    if treffer.data:
        produkt_id = treffer.data[0]["id"]
    else:
        neu = client.table("produkt").insert({"hersteller": hersteller, "modell": modell}).execute()
        produkt_id = neu.data[0]["id"]

    # 2. Upload in Storage
    storage_pfad = f"{produkt_id}/{dateiname}"
    client.storage.from_(BUCKET).upload(
        path=storage_pfad,
        file=datei_bytes,
        file_options={"content-type": "application/pdf", "upsert": "true"}
    )

    # 3. Dokument anlegen (nutzer_id fehlt hier noch, wird später ergänzt)
    zeile = {
        "produkt_id": produkt_id,
        "typ": "bedienungsanleitung",
        "quelle": "upload",
        "titel": Path(dateiname).stem,
        "datei_pfad": storage_pfad,
        "sprache": "de",
    }

    vorhanden = client.table("dokument").select("id").eq("datei_pfad", storage_pfad).limit(1).execute()
    if vorhanden.data:
        dokument_id = vorhanden.data[0]["id"]
        client.table("dokument").update(zeile).eq("id", dokument_id).execute()
    else:
        antwort = client.table("dokument").insert(zeile).execute()
        dokument_id = antwort.data[0]["id"]

    return produkt_id, dokument_id, storage_pfad

def verarbeite_pdf_im_hintergrund(produkt_id: int, dokument_id: int, datei_pfad: str) -> None:
    """BackgroundTask: Nutzt direkt die Skript-Funktionen für Chunking & Embeddings."""
    print(f"[Hintergrund] Starte Verarbeitung für Dokument {dokument_id} (Produkt {produkt_id})")

    # 1. PDF zerlegen (aus scripts/chunks_erstellen.py)
    dokument = {"id": dokument_id, "datei_pfad": datei_pfad}
    zeilen = dokument_zerlegen(client, BUCKET, dokument)

    alte_chunks_loeschen(client, dokument_id)
    for start in range(0, len(zeilen), 100):
        client.table("chunk").insert(zeilen[start : start + 100]).execute()

    print(f"[Hintergrund] {len(zeilen)} Chunks gespeichert.")

    # 2. Fehlende Embeddings ergänzen (aus scripts/embeddings_ergaenzen.py)
    gefunden, gespeichert = ergaenze_embeddings(
        client,
        generiere_embedding,
        schreiben=True,
        produkt_id=produkt_id,
        pause=0.5,
    )

    print(f"[Hintergrund] Fertig: {gespeichert}/{gefunden} Embeddings erstellt.")
import io
import os
from pathlib import Path
from pypdf import PdfReader

from app.db import _client as client
from app.config import settings
from app.llm import generiere_embedding

BUCKET = os.getenv("SUPABASE_BUCKET", "anleitungen")


def extrahiere_produkt(dateiname: str):
    """Liest Hersteller und Modell aus dem Dateinamen (z.B. 'Miele_W1.pdf')."""
    name_ohne_ext = Path(dateiname).stem
    teile = name_ohne_ext.replace("_", " ").split(" ", 1)
    if len(teile) == 2:
        return teile[0].strip(), teile[1].strip()
    return "Unbekannt", name_ohne_ext.strip()


def speichere_pdf_und_datenbank(dateiname: str, datei_bytes: bytes) -> tuple[int, str]:
    """Speichert das PDF in Storage und legt die DB-Zeilen an (Option B - Schnell)."""
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

    # 3. Dokument anlegen (nutzer_id fehlt hier noch, wie besprochen)
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

    return dokument_id, storage_pfad


def verarbeite_pdf_im_hintergrund(dokument_id: int, datei_pfad: str, titel: str):
    """Wird als BackgroundTask gestartet: Chunking und Embedding."""
    print(f"[Hintergrund] Starte Verarbeitung für Dokument {dokument_id}")

    # 1. PDF laden und in Absätze zerlegen
    pdf_bytes = client.storage.from_(BUCKET).download(datei_pfad)
    leser = PdfReader(io.BytesIO(pdf_bytes))

    zeilen = []
    # (Stark vereinfachte Chunking-Logik angelehnt an chunks_erstellen.py)
    for nummer, seite in enumerate(leser.pages, start=1):
        text = seite.extract_text() or ""
        # Grobes Splitten anhand von Zeilenumbrüchen für das Beispiel
        absaetze = [absatz.strip() for absatz in text.split("\n\n") if len(absatz.strip()) > 80]
        for absatz in absaetze:
            zeilen.append({
                "dokument_id": dokument_id,
                "seite": nummer,
                "abschnitt": "Allgemein",
                "inhalt": absatz[:1000]  # Begrenzung für dieses Beispiel
            })

    # Alte Chunks löschen und neue einfügen
    client.table("chunk").delete().eq("dokument_id", dokument_id).execute()
    if zeilen:
        for start in range(0, len(zeilen), 100):
            client.table("chunk").insert(zeilen[start:start + 100]).execute()

    # 2. Embeddings ergänzen
    fehlende = client.table('chunk').select('id,inhalt').eq('dokument_id', dokument_id).is_('embedding',
                                                                                            'null').execute().data or []

    for zeile in fehlende:
        vektor = generiere_embedding(zeile['inhalt'], art='dokument', titel=titel)
        client.table('chunk').update({'embedding': vektor}).eq('id', zeile['id']).execute()

    print(f"[Hintergrund] Dokument {dokument_id} erfolgreich verarbeitet. {len(fehlende)} Embeddings erstellt.")
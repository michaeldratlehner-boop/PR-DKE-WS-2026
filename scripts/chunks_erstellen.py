"""
Zerlegt die PDFs aus dem Storage in Absaetze und schreibt sie in die Tabelle chunk.

embedding bleibt leer (dafuer braucht es den Gemini-Key).
fts fuellt Postgres selbst, die Volltextsuche geht also sofort.

    python3 scripts/chunks_erstellen.py              # nur anzeigen
    python3 scripts/chunks_erstellen.py --schreiben  # speichern
"""

import argparse
import io
import logging
import os
import sys
import warnings
from pathlib import Path

from dotenv import load_dotenv
from pypdf import PdfReader
from supabase import create_client

# pypdf warnt bei Herstellerschriften staendig, das stoert nur
logging.getLogger("pypdf").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")

ZIEL_LAENGE = 800      # so lang soll ein Absatz ungefaehr werden
MINDEST_LAENGE = 80    # kuerzeres ist meist nur Seitenzahl oder Kopfzeile


def client_aufbauen():
    """Verbindung zu Supabase."""
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("FEHLER: SUPABASE_URL oder SUPABASE_KEY fehlt in der .env")
        sys.exit(1)

    print(f"  Verbinde mit {url}")
    return create_client(url, key), os.getenv("SUPABASE_BUCKET", "anleitungen")


def seiten_lesen(pdf_bytes):
    """Gibt [(seitenzahl, text), ...] zurueck."""
    leser = PdfReader(io.BytesIO(pdf_bytes))

    seiten = []
    for nummer, seite in enumerate(leser.pages, start=1):
        seiten.append((nummer, seite.extract_text() or ""))
    return seiten


def abschnitt_der_seite(text):
    """Erste kurze Zeile der Seite = Kapitelname. Geraten, reicht aber."""
    for zeile in text.split("\n"):
        zeile = zeile.strip()
        if zeile and len(zeile) < 60:    # laengeres ist Fliesstext
            return zeile
    return ""


def seite_in_absaetze(text):
    """Schneidet den Seitentext in Stuecke von etwa ZIEL_LAENGE Zeichen."""
    stuecke = []
    aktuell = ""

    for zeile in text.split("\n"):
        zeile = zeile.strip()
        if not zeile:
            continue

        if len(aktuell) + len(zeile) + 1 <= ZIEL_LAENGE:
            aktuell = (aktuell + " " + zeile).strip()
        else:
            # voll -> abschliessen und neu anfangen
            if len(aktuell) >= MINDEST_LAENGE:
                stuecke.append(aktuell)
            aktuell = zeile

    # Rest nicht vergessen
    if len(aktuell) >= MINDEST_LAENGE:
        stuecke.append(aktuell)

    return stuecke


def dokument_zerlegen(client, bucket, dokument):
    """Laedt ein PDF und baut daraus die chunk-Zeilen."""
    print(f"  Lade {dokument['datei_pfad']} ...")
    pdf_bytes = client.storage.from_(bucket).download(dokument["datei_pfad"])

    zeilen = []
    for seitenzahl, text in seiten_lesen(pdf_bytes):
        abschnitt = abschnitt_der_seite(text)

        for stueck in seite_in_absaetze(text):
            zeilen.append({
                "dokument_id": dokument["id"],
                "seite": seitenzahl,
                "abschnitt": abschnitt,
                "inhalt": stueck,
            })

    return zeilen


def alte_chunks_loeschen(client, dokument_id):
    """Alte Absaetze weg, sonst liegt nach einem zweiten Lauf alles doppelt da."""
    vorhanden = client.table("chunk").select("id").eq("dokument_id", dokument_id).execute()

    if vorhanden.data:
        client.table("chunk").delete().eq("dokument_id", dokument_id).execute()

    return len(vorhanden.data)


def main():
    parser = argparse.ArgumentParser(description="Fuellt die Tabelle chunk aus den PDFs.")
    parser.add_argument("--schreiben", action="store_true",
                        help="wirklich speichern (sonst nur anzeigen)")
    args = parser.parse_args()

    print("\n[1/3] Verbindung aufbauen")
    client, bucket = client_aufbauen()

    print("\n[2/3] Dokumente holen")
    # produkt(...) ist ein JOIN, damit Hersteller und Modell mitkommen
    dokumente = (
        client.table("dokument")
        .select("id, typ, titel, datei_pfad, produkt(hersteller, modell)")
        .order("id")
        .execute()
    ).data
    print(f"  {len(dokumente)} Dokumente gefunden")

    print("\n[3/3] PDFs zerlegen")
    gesamt = 0

    for dokument in dokumente:
        produkt = dokument.get("produkt") or {}
        print(f"\n  --- dokument {dokument['id']}: {produkt.get('hersteller')} "
              f"{produkt.get('modell')} ({dokument['typ']}) ---")

        if not dokument.get("datei_pfad"):
            print("  Keine Datei - uebersprungen.")
            continue

        zeilen = dokument_zerlegen(client, bucket, dokument)
        gesamt += len(zeilen)

        laengen = [len(z["inhalt"]) for z in zeilen]
        schnitt = sum(laengen) / len(laengen) if laengen else 0
        print(f"  {len(zeilen)} Absaetze, im Schnitt {schnitt:.0f} Zeichen")

        # zwei Beispiele zur Kontrolle
        for b in zeilen[:2]:
            print(f"    S.{b['seite']} [{b['abschnitt'][:28]}] {b['inhalt'][:70]}...")

        if args.schreiben:
            geloescht = alte_chunks_loeschen(client, dokument["id"])
            if geloescht:
                print(f"  {geloescht} alte Absaetze geloescht")

            # in 100er-Paketen, alles auf einmal ist der Anfrage zu gross
            for start in range(0, len(zeilen), 100):
                client.table("chunk").insert(zeilen[start:start + 100]).execute()

            print(f"  -> {len(zeilen)} Absaetze gespeichert")

    print(f"\nInsgesamt {gesamt} Absaetze.")
    print("Gespeichert.\n" if args.schreiben else "Nur Vorschau. Mit --schreiben speichern.\n")


if __name__ == "__main__":
    main()

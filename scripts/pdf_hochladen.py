"""
Laedt eine PDF-Bedienungsanleitung in Supabase.

Was passiert:
  1. PDF pruefen (ist es lesbar? wie viele Seiten?)
  2. Produkt in der Tabelle "produkt" finden oder neu anlegen
  3. PDF in den privaten Storage-Bucket "anleitungen" hochladen
  4. Zeile in der Tabelle "dokument" anlegen, die auf die Datei zeigt
  5. Alles wieder zuruecklesen, um zu beweisen dass es geklappt hat


Aufruf (IMMER zuerst ins Projektverzeichnis wechseln!):
    cd ~/Uni/GitHub/PR-DKE-WS-2026
    source .venv/bin/activate
    python3 scripts/pdf_hochladen.py "anleitungen/Miele WK770Q WPS 02_6045BD182B051FE1A5C27A0214BE9DDB.pdf" \
        --hersteller Miele --modell "WK 770 Q WPS"

Dateinamen mit Leerzeichen gehoeren in "Anfuehrungszeichen", sonst haelt
die Shell jedes Wort fuer ein eigenes Argument.
"""

import argparse          # liest Argumente von der Kommandozeile
import os                # liest Umgebungsvariablen (unsere .env-Werte)
import sys               # erlaubt das Beenden mit einem Fehlercode
from pathlib import Path # komfortabler Umgang mit Dateipfaden

from dotenv import load_dotenv
from pypdf import PdfReader
from supabase import create_client


def client_aufbauen():
    """Liest die .env und baut die Verbindung zu Supabase auf."""
    # Die .env liegt im Projekt-Hauptordner, also eine Ebene ueber "scripts/".
    projekt_ordner = Path(__file__).resolve().parent.parent
    load_dotenv(projekt_ordner / ".env")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        print("FEHLER: SUPABASE_URL oder SUPABASE_KEY fehlt in der .env")
        sys.exit(1)

    # Der Bucket-Name steht in der .env.
    bucket = os.getenv("SUPABASE_BUCKET", "anleitungen")

    print(f"  Verbinde mit {url}")
    return create_client(url, key), bucket


def pdf_pruefen(pdf_pfad: Path) -> int:
    """Prueft, ob die Datei ein lesbares PDF ist, und gibt die Seitenzahl zurueck.
    """
    if not pdf_pfad.is_file():
        print(f"FEHLER: Datei nicht gefunden: {pdf_pfad}")
        sys.exit(1)

    # try/except heisst: "versuche das; wenn es schiefgeht, mach stattdessen das".
    try:
        seitenzahl = len(PdfReader(pdf_pfad).pages)
    except Exception as fehler:
        print(f"FEHLER: PDF nicht lesbar: {fehler}")
        sys.exit(1)

    groesse_mb = pdf_pfad.stat().st_size / 1_000_000
    print(f"  Lesbar: {seitenzahl} Seiten, {groesse_mb:.1f} MB")
    return seitenzahl


def produkt_sicherstellen(client, hersteller: str, modell: str) -> int:
    """Sucht das Produkt und legt es an, falls es fehlt. Gibt die id zurueck.
    """

    treffer = (
        client.table("produkt")
        .select("id")
        .eq("hersteller", hersteller)
        .eq("modell", modell)
        .limit(1)
        .execute()
    )

    # .data ist eine Liste der Zeilen. Leere Liste = nichts gefunden.
    if treffer.data:
        produkt_id = treffer.data[0]["id"]
        print(f"  Produkt gefunden: {hersteller} {modell} (id={produkt_id})")
        return produkt_id

    neu = (
        client.table("produkt")
        .insert({"hersteller": hersteller, "modell": modell})
        .execute()
    )
    produkt_id = neu.data[0]["id"]
    print(f"  Produkt neu angelegt: {hersteller} {modell} (id={produkt_id})")
    return produkt_id


def pdf_hochladen(client, bucket: str, produkt_id: int, pdf_pfad: Path) -> str:
    """Laedt das PDF in den Bucket und gibt den Pfad innerhalb des Buckets zurueck."""
    # produkt_id als Unterordner: so liegen die Dateien sortiert und zwei
    # Hersteller mit gleichem Dateinamen ueberschreiben sich nicht.
    storage_pfad = f"{produkt_id}/{pdf_pfad.name}"

    try:
        client.storage.from_(bucket).upload(
            path=storage_pfad,
            file=pdf_pfad.read_bytes(),   # Datei als rohe Bytes einlesen
            file_options={
                "content-type": "application/pdf",
                # upsert: gleicher Pfad wird ueberschrieben statt Fehler zu werfen.
                "upsert": "true",
            },
        )
    except Exception as fehler:
        print(f"FEHLER beim Upload: {fehler}")
        try:
            namen = [b.name for b in client.storage.list_buckets()]
            print(f"       Vorhandene Buckets: {namen}")
            print(f"       Gesucht wurde:      '{bucket}'")
        except Exception:
            pass
        sys.exit(1)

    print(f"  Hochgeladen: {bucket}/{storage_pfad}")
    return storage_pfad


def dokument_anlegen(
    client, produkt_id: int, titel: str, storage_pfad: str, typ: str
) -> int:
    """Legt die Zeile in "dokument" an. Erst sie macht das PDF auffindbar.

    Gibt es zu diesem Pfad schon eine Zeile, wird sie aktualisiert statt
    eine zweite anzulegen.
    """
    zeile = {
        "produkt_id": produkt_id,
        "typ": typ,                  # bedienungsanleitung | datenblatt
        "quelle": "upload",          # spaeter alternativ "web"
        "titel": titel,
        "datei_pfad": storage_pfad,  # der Zeiger in den Bucket
        "sprache": "de",
    }

    vorhanden = (
        client.table("dokument")
        .select("id")
        .eq("datei_pfad", storage_pfad)
        .limit(1)
        .execute()
    )

    if vorhanden.data:
        dokument_id = vorhanden.data[0]["id"]
        client.table("dokument").update(zeile).eq("id", dokument_id).execute()
        print(f"  Dokument-Zeile aktualisiert (id={dokument_id}, war schon da)")
        return dokument_id

    antwort = client.table("dokument").insert(zeile).execute()
    dokument_id = antwort.data[0]["id"]
    print(f"  Dokument-Zeile angelegt (id={dokument_id})")
    return dokument_id


def gegenpruefen(client, bucket: str, dokument_id: int) -> None:
    """Liest alles frisch aus der DB zurueck.

    Bei einem Durchstich glaubt man dem Schreibvorgang nicht - man liest nach.
    """
    antwort = (
        client.table("dokument")
        .select("id, titel, typ, sprache, datei_pfad, produkt(hersteller, modell)")
        .eq("id", dokument_id)
        .single()                    # erwartet genau eine Zeile
        .execute()
    )
    dokument = antwort.data

    print("\n  Aus der Datenbank zurueckgelesen:")
    for feld in ["id", "titel", "typ", "sprache", "datei_pfad"]:
        print(f"    {feld:11}: {dokument[feld]}")

    # Das verschachtelte "produkt" kommt ueber den Fremdschluessel mit -
    # Supabase macht daraus einen JOIN.
    produkt = dokument.get("produkt") or {}
    print(f"    {'produkt':11}: {produkt.get('hersteller')} {produkt.get('modell')}")

    link = client.storage.from_(bucket).create_signed_url(dokument["datei_pfad"], 3600)
    print(f"\n  Test-Link (1 Stunde gueltig):\n    {link['signedURL']}")


def main() -> None:
    """Ruft die Schritte der Reihe nach auf."""
    # argparse baut automatisch eine Hilfe: python3 scripts/pdf_hochladen.py --help
    parser = argparse.ArgumentParser(
        description="Laedt eine PDF-Anleitung in Supabase (Storage + Tabelle dokument)."
    )
    parser.add_argument("pdf", type=Path, help="Pfad zur PDF-Datei")
    parser.add_argument("--hersteller", required=True, help='z.B. "Bosch"')
    parser.add_argument("--modell", required=True, help='z.B. "WAN28150"')
    parser.add_argument("--titel", help="Titel (Standard: Dateiname ohne .pdf)")
    # choices= sorgt dafuer, dass argparse falsche Werte sofort ablehnt -
    # noch bevor die Datenbank es ueber dokument_typ_chk tun wuerde.
    parser.add_argument(
        "--typ",
        choices=["bedienungsanleitung", "datenblatt"],
        default="bedienungsanleitung",
        help="Art des Dokuments (Standard: bedienungsanleitung)",
    )
    args = parser.parse_args()

    titel = args.titel or args.pdf.stem   # .stem = Dateiname ohne Endung

    print("\n[1/5] Verbindung aufbauen")
    client, bucket = client_aufbauen()

    print("\n[2/5] PDF pruefen")
    pdf_pruefen(args.pdf)

    print(f"\n[3/5] Produkt sicherstellen  (typ={args.typ})")
    produkt_id = produkt_sicherstellen(client, args.hersteller, args.modell)

    print("\n[4/5] PDF in den Storage-Bucket hochladen")
    storage_pfad = pdf_hochladen(client, bucket, produkt_id, args.pdf)

    print("\n[5/5] Dokument-Zeile anlegen und gegenpruefen")
    dokument_id = dokument_anlegen(client, produkt_id, titel, storage_pfad, args.typ)
    gegenpruefen(client, bucket, dokument_id)

if __name__ == "__main__":
    main()

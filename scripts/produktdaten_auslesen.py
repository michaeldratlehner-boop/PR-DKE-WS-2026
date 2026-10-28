"""
Liest die technischen Daten aus den Produktblaettern und ergaenzt damit
die Tabelle "produkt".

Ablauf:
  1. Aus der DB holen, welche Dokumente es gibt
  2. Die PDFs aus dem Storage-Bucket herunterladen
  3. Werte per Suchmuster herausziehen
  4. Tabelle zum Gegenpruefen ausgeben
  5. NUR mit --schreiben die Werte wirklich in die DB schreiben


WICHTIG - warum zwei Quellen getrennt behandelt werden:
  Die Energieklasse wird AUSSCHLIESSLICH aus dem Produktblatt gelesen.
  In Bedienungsanleitungen steht unter "Energieeffizienzklasse" naemlich
  die Klasse der TROMMELBELEUCHTUNG (Miele: E, Siemens: F) - nicht die
  der Waschmaschine. 

Aufruf:
    cd ~/Uni/GitHub/PR-DKE-WS-2026
    source .venv/bin/activate
    python3 scripts/produktdaten_auslesen.py              # nur anzeigen
    python3 scripts/produktdaten_auslesen.py --schreiben  # und speichern
"""

import argparse
import io
import logging
import os
import re
import sys
import warnings
from pathlib import Path

from dotenv import load_dotenv
from pypdf import PdfReader
from supabase import create_client

# pypdf meldet bei Herstellerschriften viele harmlose Warnungen. Die
# blenden wir aus, damit die Ausgabe lesbar bleibt.
logging.getLogger("pypdf").setLevel(logging.ERROR)
warnings.filterwarnings("ignore")


# ---------------------------------------------------------------------------
# Suchmuster
#
# Jeder Eintrag ist eine Liste von Alternativen, die der Reihe nach probiert
# werden - die erste, die passt, gewinnt. Mehrere Muster sind noetig, weil
# jeder Hersteller dieselbe Angabe anders schreibt:
#   Miele:   "Gewichteter Wasserverbrauch pro Betriebszyklus in l 47"
#   Siemens: "Wasserverbrauch ... (EU 2017/1369): 46 l"
# ---------------------------------------------------------------------------
MUSTER_DATENBLATT = {
    "energieklasse": [
        r"Energie[-\s]?Effizienzklasse\s*(?:\(A\s*[–\-]\s*G\))?\s*[¹1]?\s*:?\s*([A-G])(?![A-Za-z])",
    ],
    "schleuderklasse": [
        r"Schleudereffizienzklasse\s*(?:\(A\s*[–\-]\s*G\))?\s*:?\s*([A-G])(?![A-Za-z])",
    ],
    "geraeuschklasse": [
        r"(?:Luftschallemissionsklasse|Ger[äa]uscheffizienzklasse)\s*(?:\([^)]*\))?\s*:?\s*([A-D])(?![A-Za-z])",
    ],
    "geraeusch_db": [
        r"dB\(A\)\s*re\s*1?\s*pW\s*(\d{2,3})",   # Miele: Einheit vor der Zahl
        r"(\d{2,3})\s*dB",                        # Siemens: Zahl vor der Einheit
    ],
    "energie_kwh_100": [
        r"Energieverbrauch.{0,120}?in kWh\s*(\d{2,3})",   # Miele
        r"Energieverbrauch.{0,120}?(\d{2,3})\s*kWh",      # Siemens
    ],
    "wasser_liter_zyklus": [
        r"Wasserverbrauch.{0,120}?in l\s*(\d{2,3})",      # Miele
        r"Wasserverbrauch.{0,140}?:\s*(\d{2,3})\s*l\b",   # Siemens
    ],
    "kapazitaet_kg": [
        r"(?:Maximale Beladungsmenge|Fassungsverm[öo]gen)\s*:?\s*(\d{1,2}[.,]?\d?)\s*kg",
        r"I\s*(\d{1,2}[.,]?\d?)\s*kg\s*I",                # Miele: Kopfzeile
    ],
    "schleuder_upm": [
        r"(\d{3,4})\s*U/[Mm]in",   # Sonderfall: wir nehmen spaeter das Maximum
    ],
    "eco_dauer_min": [
        r"Dauer des Programms.{0,100}?Nennkapazit[äa]t\s*:?\s*(\d{2,3})\b",  # Miele
        r"(\d{1,2}):(\d{2})\s*h",                                            # Siemens
    ],
    "ean": [
        r"EAN[-\s]?(?:Nr\.?|Nummer)\s*:?\s*(\d{8,14})",
    ],
    "bauart": [
        r"\b(Frontlader|Toplader)\b",
    ],
}

# Masse: zuerst im Produktblatt suchen, sonst in der Anleitung.
MUSTER_MASSE = {
    "hoehe_cm":  [r"Abmessungen.{0,60}?(\d{3,4})\s*x\s*\d{3,4}\s*x\s*\d{3,4}",
                  r"H[öo]he\s*:?\s*(\d{2,4}[.,]?\d?)\s*(?:mm|cm)"],
    "breite_cm": [r"Abmessungen.{0,60}?\d{3,4}\s*x\s*(\d{3,4})\s*x\s*\d{3,4}",
                  r"Breite\s*:?\s*(\d{2,4}[.,]?\d?)\s*(?:mm|cm)"],
    "tiefe_cm":  [r"Abmessungen.{0,60}?\d{3,4}\s*x\s*\d{3,4}\s*x\s*(\d{3,4})",
                  r"Tiefe\s*:?\s*(\d{2,4}[.,]?\d?)\s*(?:mm|cm)"],
}


def normalisieren(text: str) -> str:
    """Macht den PDF-Text durchsuchbar.

    PDFs enthalten harte Zeilenumbrueche und Fuellpunkte ("Klasse: ..... A").
    Beides wuerde die Suchmuster zerreissen, darum raeumen wir vorher auf.
    """
    text = text.replace("\n", " ")
    text = re.sub(r"\.{2,}", " ", text)    # Fuellpunkte entfernen
    return re.sub(r"\s+", " ", text)       # Mehrfach-Leerzeichen zusammenziehen


def zahl(wert: str) -> float:
    """Wandelt '84,5' oder '9.0' in eine Zahl um (deutsches Komma beachten)."""
    return float(wert.replace(",", "."))


def suchen(text: str, muster_liste: list) -> str | None:
    """Probiert die Muster der Reihe nach und gibt den ersten Treffer zurueck."""
    for muster in muster_liste:
        treffer = re.search(muster, text, re.IGNORECASE)
        if treffer:
            return treffer.group(1)
    return None


def werte_auslesen(text_datenblatt: str, text_anleitung: str) -> dict:
    """Zieht alle Felder aus den beiden Texten. Gibt ein dict zurueck."""
    werte = {}

    for feld, muster in MUSTER_DATENBLATT.items():
        # Diese Felder kommen NUR aus dem Produktblatt (siehe Kopfkommentar).
        gefunden = suchen(text_datenblatt, muster)
        if gefunden is not None:
            werte[feld] = gefunden

    # Schleuderdrehzahl: steht oft als Bereich ("400 - 1600 U/min").
    alle_upm = [int(x) for x in re.findall(r"(\d{3,4})\s*U/[Mm]in", text_datenblatt)]
    if alle_upm:
        werte["schleuder_upm"] = max(alle_upm)

    # eco-Dauer kann "239" (Minuten) oder "3:39 h" sein.
    treffer = re.search(r"Dauer des Programms.{0,100}?Nennkapazit[äa]t\s*:?\s*(\d{2,3})\b",
                        text_datenblatt, re.IGNORECASE)
    if treffer:
        werte["eco_dauer_min"] = int(treffer.group(1))
    else:
        treffer = re.search(r"(\d{1,2}):(\d{2})\s*h", text_datenblatt)
        if treffer:
            werte["eco_dauer_min"] = int(treffer.group(1)) * 60 + int(treffer.group(2))

    # Masse: Produktblatt bevorzugt, sonst Anleitung.
    for feld, muster in MUSTER_MASSE.items():
        roh = suchen(text_datenblatt, muster) or suchen(text_anleitung, muster)
        if roh is not None:
            cm = zahl(roh)
            werte[feld] = round(cm / 10, 1) if cm > 300 else cm

    # Zahlenfelder in echte Zahlen umwandeln.
    for feld in ["energie_kwh_100", "wasser_liter_zyklus", "kapazitaet_kg"]:
        if feld in werte:
            werte[feld] = zahl(str(werte[feld]))
    for feld in ["geraeusch_db", "schleuder_upm", "eco_dauer_min"]:
        if feld in werte:
            werte[feld] = int(werte[feld])

    return werte


def pdf_text(client, bucket: str, datei_pfad: str) -> str:
    """Laedt ein PDF aus dem Storage-Bucket und gibt seinen Text zurueck."""
    rohdaten = client.storage.from_(bucket).download(datei_pfad)
    leser = PdfReader(io.BytesIO(rohdaten))
    return normalisieren("\n".join((s.extract_text() or "") for s in leser.pages))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Liest technische Daten aus den Produktblaettern in die Tabelle produkt."
    )
    parser.add_argument(
        "--schreiben",
        action="store_true",   # Schalter ohne Wert: entweder gesetzt oder nicht
        help="Werte wirklich in die Datenbank schreiben (sonst nur anzeigen)",
    )
    args = parser.parse_args()

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("FEHLER: SUPABASE_URL oder SUPABASE_KEY fehlt in der .env")
        sys.exit(1)
    client = create_client(url, key)
    bucket = os.getenv("SUPABASE_BUCKET", "anleitungen")

    # Alle Produkte mit ihren Dokumenten holen. Das verschachtelte
    # "dokument(...)" ist ein JOIN, den Supabase automatisch baut.
    produkte = (
        client.table("produkt")
        .select("id, hersteller, modell, dokument(id, typ, datei_pfad)")
        .order("id")
        .execute()
    ).data

    for produkt in produkte:
        print(f"\n{'='*64}")
        print(f"  {produkt['hersteller']} {produkt['modell']}  (produkt.id={produkt['id']})")
        print("=" * 64)

        dokumente = produkt.get("dokument") or []
        datenblatt = next((d for d in dokumente if d["typ"] == "datenblatt"), None)
        anleitung = next((d for d in dokumente if d["typ"] == "bedienungsanleitung"), None)

        if not datenblatt:
            print("  Kein Produktblatt hinterlegt - uebersprungen.")
            print("  (Energiedaten werden bewusst NICHT aus der Anleitung gelesen.)")
            continue

        print(f"  Lade Produktblatt aus dem Bucket ...")
        text_datenblatt = pdf_text(client, bucket, datenblatt["datei_pfad"])
        text_anleitung = ""
        if anleitung:
            print(f"  Lade Anleitung (nur fuer die Masse) ...")
            text_anleitung = pdf_text(client, bucket, anleitung["datei_pfad"])

        werte = werte_auslesen(text_datenblatt, text_anleitung)

        print("\n  Gefundene Werte:")
        for feld in ["bauart", "kapazitaet_kg", "energieklasse", "energie_kwh_100",
                     "wasser_liter_zyklus", "schleuder_upm", "schleuderklasse",
                     "geraeuschklasse", "geraeusch_db", "eco_dauer_min",
                     "hoehe_cm", "breite_cm", "tiefe_cm", "ean"]:
            wert = werte.get(feld)
            zeichen = "ok  " if wert is not None else "FEHLT"
            print(f"    {zeichen} {feld:21}: {wert}")

        if args.schreiben:
            client.table("produkt").update(werte).eq("id", produkt["id"]).execute()
            print(f"\n  -> {len(werte)} Felder in die Datenbank geschrieben.")
        else:
            print("\n  -> Nur Vorschau. Mit --schreiben wird gespeichert.")

    print()


if __name__ == "__main__":
    main()

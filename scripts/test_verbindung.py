"""
Prueft, ob die Verbindung zur Supabase-Datenbank steht.

Starten:
    cd ~/Uni/GitHub/PR-DKE-WS-2026   # ohne das findet die Shell nichts
    source .venv/bin/activate        # einmal pro Terminal-Fenster
    python3 scripts/test_verbindung.py
"""

import os                               # liest Umgebungsvariablen
from dotenv import load_dotenv          # laedt die .env-Datei
from supabase import create_client      # der Supabase-Client

# Liest die .env ein und legt die Werte in die Umgebungsvariablen.
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# Freundlicher Hinweis statt eines kryptischen Absturzes weiter unten.
if not url or not key:
    print("FEHLER: SUPABASE_URL oder SUPABASE_KEY fehlt in der .env")
    print("        Key holen: Dashboard > Project Settings > API")
    raise SystemExit(1)   # beendet das Skript

print(f"Verbinde mit {url} ...")

client = create_client(url, key)

# Liest alle Zeilen der Tabelle "produkt".
# Erst .execute() schickt die Anfrage los.
antwort = client.table("produkt").select("*").execute()

print(f"Verbindung steht. Zeilen in produkt: {len(antwort.data)}")

# Jede gefundene Zeile ist ein "dict" (Schluessel-Wert-Paare, wie eine
# Tabellenzeile). 
for zeile in antwort.data:
    print(f"  id={zeile['id']}  {zeile['hersteller']} {zeile['modell']}")

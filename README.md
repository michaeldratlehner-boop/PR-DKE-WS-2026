# Haushaltsgeräte-Assistent für Waschmaschinen

LLM-Anwendung, DKE-Praktikum JKU Linz, WS 2026/27.

Die Anwendung hat zwei Funktionen:

1. **Produktfinder** — der Nutzer sucht eine neue Waschmaschine, der Assistent
   filtert und vergleicht Modelle nach Preis, Kapazität, Energieklasse und Maßen.
2. **Technischer Berater** — der Nutzer hinterlegt seine eigene Maschine und die
   zugehörige Bedienungsanleitung. Er bekommt Hilfe zu Fehlercodes, Störungen und
   Wartung, ausschließlich auf Basis dieser Anleitung. Anleitungen für
   Elektroreparaturen gibt die Anwendung nicht, sie verweist auf den Kundendienst.

## Stack

| Bereich | Technologie |
|---|---|
| Backend | Python / FastAPI |
| LLM | Gemini 3.8 Flash, Fallback Mistral Small 4 |
| Datenbank | Supabase (PostgreSQL + pgvector) |
| Embeddings | gemini-embedding-2, 768 Dimensionen |
| Frontend | noch offen |

## Datenmodell

Drei Tabellen. `db/schema.sql` ist die Quelle der Wahrheit und lauffähig — damit
lässt sich eine leere Datenbank vollständig herstellen.

```
produkt  ──┬──>  dokument  ──>  chunk
           │     (Anleitung      (durchsuchbare
           │      oder            Textstücke mit
           │      Datenblatt)     Embedding)
           └─ Katalogdaten aus dem EU-Energielabel
```

**`produkt`** — der Gerätekatalog. Neben Hersteller, Modell und Maßen stehen hier
die Werte des EU-Energielabels (Energieklasse, Verbrauch, Schleuder- und
Geräuschklasse). Quelle dafür sind die Produktblätter der Hersteller bzw. die
EPREL-Datenbank, **nicht** die Bedienungsanleitungen — dort bezeichnet
„Energieeffizienzklasse" die Trommelbeleuchtung, nicht die Maschine.

**`dokument`** — eine Bedienungsanleitung oder ein Datenblatt, unterschieden über
`typ`. Die PDF-Datei selbst liegt im privaten Storage-Bucket `anleitungen`; in der
Tabelle steht nur der Pfad dorthin (`datei_pfad`) oder eine Web-Adresse (`url`).

**`chunk`** — die Dokumente in durchsuchbaren Stücken. Hier findet das Retrieval
statt. Zwei Suchwege stehen zur Verfügung:

- `embedding vector(768)` mit HNSW-Index für die Vektorsuche (Cosine, Operator `<=>`)
- `fts tsvector` mit GIN-Index für die deutsche Volltextsuche

`fts` ist eine **generierte Spalte**: Postgres pflegt sie selbst aus `inhalt`, bei
jedem Insert und bei jedem Update. Ein `default` würde nur beim Einfügen greifen,
und der Suchindex wäre nach einer Textkorrektur veraltet.

### Vertrag zum Backend

Die Datenbank rechnet nichts. Sie erzeugt keine Embeddings und liest keine PDFs —
beides liefert das Backend fertig an. Zwei Festlegungen sind dabei bindend:

- **768 Dimensionen.** Eine andere Länge lehnt die Datenbank ab.
- **Dasselbe Modell für Indexierung und Suche.** Sonst ist die Vektorsuche Zufall.

Ändert sich das Embedding-Modell, muss die Spalte neu gebaut und jeder Chunk neu
berechnet werden.

## Einrichten

Python 3.12 oder neuer wird vorausgesetzt.

```bash
git clone https://github.com/michaeldratlehner-boop/PR-DKE-WS-2026.git
cd PR-DKE-WS-2026

# Virtuelle Umgebung anlegen und aktivieren
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Die Aktivierung gilt pro Terminal-Fenster. Fehlt sie, meldet Python
`ModuleNotFoundError`.

### Zugangsdaten

```bash
cp .env.example .env
```

Dann `.env` öffnen und die Werte eintragen. Zu finden im Supabase-Dashboard:

| Variable | Fundort |
|---|---|
| `SUPABASE_URL` | Project Settings → API |
| `SUPABASE_KEY` | Project Settings → API (`service_role` bzw. „secret") |
| `DATABASE_URL` | Project Settings → Database |
| `SUPABASE_BUCKET` | Name des Storage-Buckets, Standard `anleitungen` |

Keine Leerzeichen um das `=`, keine Anführungszeichen. Die `.env` steht in der
`.gitignore` und wird **nie** committet.

> Der `service_role`-Key umgeht RLS vollständig. Er gehört in lokale Skripte und
> ins Backend, niemals ins Frontend. Dort wird später der öffentliche Key plus
> Nutzer-Token verwendet.

Das Datenbank-Passwort zeigt Supabase nur einmal bei der Projekterstellung an.
Ist es verloren, hilft nur `Reset database password` — das macht das alte
Passwort ungültig, also vorher im Team Bescheid geben.

## Datenbank aufsetzen

Die SQL-Dateien werden im **SQL Editor des Supabase-Dashboards** ausgeführt.

> Der Editor führt nur die **markierte** Stelle aus, wenn etwas selektiert ist.
> Also nichts markieren und die ganze Datei einfügen, sonst läuft nur ein Teil.

| Ausgangslage | Vorgehen |
|---|---|
| Leere Datenbank | `db/schema.sql`, dann `db/03_suche_chunks.sql` |
| Bestehende Datenbank | `01_anpassungen.sql`, `02_produktdaten.sql`, `03_suche_chunks.sql` |

`schema.sql` nutzt `create table if not exists` und überspringt damit vorhandene
Tabellen. Die Migrationen holen nach, was dadurch nicht angewendet wird:

- **`01_anpassungen.sql`** — `on delete cascade` auf den Fremdschlüsseln, `fts` als
  generierte Spalte, Indizes, Prüfregeln auf `dokument`.
- **`02_produktdaten.sql`** — die Spalten des EU-Energielabels in `produkt`,
  Prüfregeln auf den Effizienzklassen, Entfernen des doppelten
  `produkt.datenblatt_url`.
- **`03_suche_chunks.sql`** — die Suchfunktion, siehe unten.

01 und 02 sind bereits angewendet und stehen nur noch als Nachweis im Repo.

Am Ende jeder Migration stehen Kontrollabfragen, die den erreichten Zustand zeigen.

### Verbindung über Port 5432

In vielen Uni- und Firmennetzen sind ausgehende Postgres-Verbindungen (5432 und
6543) gesperrt. `psql` und `psycopg` laufen dann in einen Timeout, während die
REST-API über HTTPS problemlos funktioniert. In dem Fall: SQL über das Dashboard,
Anwendungscode über den Supabase-Client.

## Row Level Security

RLS ist auf allen drei Tabellen aktiv. Hintergrund: Supabase stellt jede Tabelle
im Schema `public` automatisch über eine öffentliche REST-API bereit, und der
dafür nötige anon-Key steht im Frontend. RLS ist der einzige Türsteher davor.

| Tabelle | Zugriff über die öffentliche API |
|---|---|
| `produkt` | lesbar für alle — das ist der Produktfinder |
| `dokument` | gesperrt |
| `chunk` | gesperrt |

`dokument` und `chunk` bekommen **absichtlich keine Policy**. Darin steht der
Volltext fremder Herstelleranleitungen; der Zugriff läuft ausschließlich über das
Backend. „RLS aktiviert, keine Policy" bedeutet in Postgres: alles gesperrt.

## Daten einspielen

Die drei Skripte in `scripts/`. Alle brauchen die aktive `.venv`:

```bash
source .venv/bin/activate

# 1. PDF in den Storage und in die Tabelle dokument
python3 scripts/pdf_hochladen.py "anleitungen/datei.pdf" \
    --hersteller Miele --modell "WK 770 Q WPS" --typ bedienungsanleitung

# 2. Technische Daten aus den Produktblättern nach produkt
python3 scripts/produktdaten_auslesen.py --schreiben

# 3. PDFs in Absätze zerlegen und nach chunk schreiben
python3 scripts/chunks_erstellen.py --schreiben
```

Skript 2 und 3 zeigen ohne `--schreiben` nur an, was sie tun würden. Erst mit dem
Schalter wird gespeichert. Skript 1 und 3 können mehrfach laufen, ohne Doppelte
anzulegen.

`chunks_erstellen.py` lässt `embedding` leer — dafür braucht es den Gemini-Key.
Die Spalte `fts` füllt Postgres selbst, die Volltextsuche funktioniert also sofort.

## Suchfunktion `suche_chunks`

Sucht die Absätze aus der Anleitung, die zu einer Frage passen — eingegrenzt auf
ein Gerät. Das Backend ruft sie auf und gibt die Treffer als Kontext ans LLM.

```python
client.rpc("suche_chunks", {
    "query_text": "Was bedeutet Fehler F35?",
    "produkt_id": 1,
    "query_embedding": None,   # noch ungenutzt
    "treffer_limit": 5,
}).execute()
```

**Parameter**

| Name | |
|---|---|
| `query_text` | die Frage im Original, ungekürzt |
| `produkt_id` | **Pflicht.** Ohne sie würde der Berater fremde Anleitungen durchsuchen |
| `query_embedding` | 768 Zahlen. Noch ungenutzt, steht für die spätere Vektorsuche schon in der Signatur |
| `treffer_limit` | Standard 5 |

**Rückgabe** — eine Zeile je Treffer:

| Feld | |
|---|---|
| `chunk_id` | |
| `inhalt` | der Absatztext, geht in den Prompt |
| `seite`, `abschnitt` | für die Quellenangabe in der Antwort |
| `fts_rang` | Platz in der Trefferliste, 1 ist der beste |
| `fts_score` | Punktwert der Volltextsuche, für die Traces |

**Derzeit nur Volltextsuche.** Die Wörter der Frage werden mit ODER verknüpft, nicht
mit UND — sonst müsste ein Absatz alle Wörter enthalten und ganze Sätze fänden nie
etwas. Ganze Sätze treffen damit trotzdem ungenau; dafür kommt später die
Vektorsuche dazu. Die Signatur bleibt dann gleich.

Findet die Suche nichts Passendes, kommen trotzdem Absätze zurück — die Funktion
sortiert nach Worttreffern, nicht nach Sinn. Das Aussortieren macht der Prompt:
Steht die Antwort nicht in den Absätzen, muss das LLM „weiß ich nicht" sagen.

## Stand

| | |
|---|---|
| Schema lauffähig, drei Migrationen | ✅ |
| RLS aktiv, Policy für `produkt` | ✅ |
| Skripte für PDF-Upload, Datenblatt-Auswertung, Chunking | ✅ |
| `chunk` gefüllt (338 Absätze aus 4 PDFs) | ✅ |
| `suche_chunks`, Volltextsuche | ✅ |
| `suche_chunks`, Vektorsuche und RRF | offen, braucht das Embedding-Modell |
| `finde_produkte` als SQL-Funktion | offen, läuft vorerst im Backend |
| Produktkatalog aus EPREL | offen |
| Golden Dataset, Traces | offen |

## Hinweis nach AI Act Art. 50

Diese Anwendung nutzt ein KI-System. Antworten können fehlerhaft sein und ersetzen
keine fachkundige Beratung. Bei Elektroreparaturen gibt die Anwendung keine
Anleitung, sondern verweist auf den Kundendienst.

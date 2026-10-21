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
| Leere Datenbank | nur `db/schema.sql` |
| Bestehende Datenbank | `db/01_anpassungen.sql`, dann `db/02_produktdaten.sql` |

`schema.sql` nutzt `create table if not exists` und überspringt damit vorhandene
Tabellen. Die beiden Migrationen holen nach, was dadurch nicht angewendet wird:

- **`01_anpassungen.sql`** — `on delete cascade` auf den Fremdschlüsseln, `fts` als
  generierte Spalte, Indizes, Prüfregeln auf `dokument`.
- **`02_produktdaten.sql`** — die Spalten des EU-Energielabels in `produkt`,
  Prüfregeln auf den Effizienzklassen, Entfernen des doppelten
  `produkt.datenblatt_url`.

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

## Stand

| | |
|---|---|
| Schema lauffähig, zwei Migrationen | ✅ |
| RLS aktiv, Policy für `produkt` | ✅ |
| Skripte für PDF-Upload und Datenblatt-Auswertung | folgt |
| SQL-Funktionen `finde_produkte` und `suche_chunks` | offen |
| Produktkatalog aus EPREL | offen |
| Golden Dataset, Traces | offen |

## Hinweis nach AI Act Art. 50

Diese Anwendung nutzt ein KI-System. Antworten können fehlerhaft sein und ersetzen
keine fachkundige Beratung. Bei Elektroreparaturen gibt die Anwendung keine
Anleitung, sondern verweist auf den Kundendienst.

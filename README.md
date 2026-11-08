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
| Leere Datenbank | `db/schema.sql`, dann `db/03_suche_chunks.sql`, anschließend `db/04_hybride_suche.sql` |
| Bestehende Datenbank | `01_anpassungen.sql`, `02_produktdaten.sql`, `03_suche_chunks.sql`, anschließend `04_hybride_suche.sql` |

`schema.sql` nutzt `create table if not exists` und überspringt damit vorhandene
Tabellen. Die Migrationen holen nach, was dadurch nicht angewendet wird:

- **`01_anpassungen.sql`** — `on delete cascade` auf den Fremdschlüsseln, `fts` als
  generierte Spalte, Indizes, Prüfregeln auf `dokument`.
- **`02_produktdaten.sql`** — die Spalten des EU-Energielabels in `produkt`,
  Prüfregeln auf den Effizienzklassen, Entfernen des doppelten
  `produkt.datenblatt_url`.
- **`03_suche_chunks.sql`** — die Suchfunktion, siehe unten.
- **`04_hybride_suche.sql`** — ergänzt die produktbezogene Volltext- und
  Vektorsuche `suche_chunks_hybrid` mit Reciprocal Rank Fusion (RRF).
  Die bisherige Funktion `suche_chunks` bleibt erhalten.

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

### Embeddings ergänzen

Nach dem Chunking erzeugt `scripts/embeddings_ergaenzen.py` die fehlenden
Embeddings mit `gemini-embedding-2`. Pro Chunk werden 768 Werte gespeichert.
Das Antwortmodell und das Embedding-Modell werden getrennt konfiguriert.

In der lokalen `.env` müssen folgende Werte gesetzt sein:

```dotenv
GEMINI_API_KEY=<eigener API-Schlüssel>
GEMINI_EMBEDDING_MODEL=gemini-embedding-2
```

Die Zugangsdaten gehören ausschließlich ins Backend beziehungsweise in lokale
Skripte. Die `.env` wird nicht committet.

```bash
# Vorschau: keine Gemini-Aufrufe und keine Datenbankänderungen
python scripts/embeddings_ergaenzen.py --produkt-id 1

# Optional: zunächst nur zwei Chunks speichern
python scripts/embeddings_ergaenzen.py --produkt-id 1 --limit 2 --schreiben

# Alle noch fehlenden Embeddings für das gewählte Gerät speichern
python scripts/embeddings_ergaenzen.py --produkt-id 1 --schreiben
```

`produkt-id` bezeichnet die Datenbank-ID, nicht die Anzahl der Produkte.
Im aktuell getesteten Bestand gilt: Miele = 1, Siemens = 3.

Das Skript verarbeitet nur Chunks ohne Embedding. Bereits gespeicherte
Embeddings werden übersprungen. Nach einer Unterbrechung kann derselbe Befehl
erneut ausgeführt werden. Bereits gespeicherte Ergebnisse bleiben erhalten.
Bei Bedarf lässt sich mit `--pause 15` eine Pause von 15 Sekunden zwischen
den Verarbeitungen einstellen.

Nach dem Import neuer Dokumente ist dieser Schritt ebenfalls erforderlich.
`chunks_erstellen.py` nicht nur zum Ergänzen von Embeddings erneut ausführen:
Es ersetzt vorhandene Chunks des jeweiligen Dokuments.

### Embedding-Funktion separat testen

Mit aktiver virtueller Umgebung im Projekt-Hauptordner:

```bash
python scripts/test_embedding_live.py --live --asynchron
```

Der Test führt einen echten API-Aufruf aus und prüft, ob genau 768 gültige
Zahlen zurückgegeben werden. Er prüft noch nicht die fachliche Suchqualität.

## Bisherige Suchfunktion `suche_chunks`

Sucht die Absätze aus der Anleitung, die zu einer Frage passen — eingegrenzt auf
ein Gerät. Diese bestehende Funktion bleibt als Volltextsuche erhalten.
Der angebundene Wartungs-Endpunkt verwendet jetzt `suche_chunks_hybrid`
(siehe nächster Abschnitt).

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

**Diese Funktion verwendet nur Volltextsuche.** Die Wörter der Frage werden mit ODER verknüpft, nicht
mit UND — sonst müsste ein Absatz alle Wörter enthalten und ganze Sätze fänden nie
etwas. Ganze Sätze treffen damit trotzdem ungenau; die ergänzte Funktion
`suche_chunks_hybrid` kombiniert deshalb Volltext- und Vektorsuche.

Findet die Suche nichts Passendes, kommen trotzdem Absätze zurück — die Funktion
sortiert nach Worttreffern, nicht nach Sinn. Das Aussortieren macht der Prompt:
Steht die Antwort nicht in den Absätzen, muss das LLM „weiß ich nicht" sagen.

## Hybride Suche und Anbindung an den Wartungs-Endpunkt

`suche_chunks_hybrid` kombiniert deutsche Volltextsuche und Vektorsuche mit
Cosine-Distanz. Beide Ranglisten werden mittels Reciprocal Rank Fusion (RRF)
zusammengeführt. Beide Suchwege sind auf die übergebene `produkt_id`
eingeschränkt. Standardmäßig werden bis zu fünf Treffer zurückgegeben.

Die Funktion wird über den Backend-Supabase-Client aufgerufen:

```python
# frage_embedding ist der zuvor erzeugte Vektor mit 768 Werten.
client.rpc("suche_chunks_hybrid", {
    "query_text": frage,
    "produkt_id": produkt_id,
    "query_embedding": frage_embedding,
    "treffer_limit": 5,
}).execute()
```

Ohne Frage-Embedding (`query_embedding=None`) arbeitet diese Funktion nur
mit Volltextsuche.

| Rückgabefeld | Bedeutung |
|---|---|
| `chunk_id`, `inhalt` | Identifikation und Text des Treffers |
| `seite`, `abschnitt` | Quellenangabe |
| `dokument_id`, `datei_pfad` | Zuordnung zum Originaldokument |
| `fts_rang`, `fts_score` | Rang und Punktwert der Volltextsuche |
| `vektor_rang`, `vektor_distanz` | Rang und Cosine-Distanz der Vektorsuche |
| `rrf_score` | Zusammengeführter Rangwert |

Der RRF-Wert dient der Sortierung und ist keine Wahrscheinlichkeit für die
Richtigkeit eines Treffers. Auch die besten Treffer können unpassend sein.
Die Antwort muss deshalb weiterhin durch den gefundenen Kontext belegt sein.

### Ablauf von POST /wartung

Die bestehende Wartungsfunktion wurde um Frage-Embeddings, hybride Suche
und Traces ergänzt:

1. FastAPI empfängt `frage` und `produkt_id`.
2. `generiere_embedding_async` erzeugt das Frage-Embedding.
3. `suche_wartungs_chunks` ruft `suche_chunks_hybrid` auf.
4. `generiere_wartungsantwort` erhält die gefundenen Absätze als Kontext.
5. Die API liefert Antwort, Quellen, `gefunden` und `trace_id` zurück.

Ohne Treffer wird „weiß ich nicht“ zurückgegeben und kein Antwortmodell
aufgerufen. Bei vorhandenen Treffern muss das Modell ebenfalls „weiß ich
nicht“ ausgeben, wenn die Antwort nicht im Kontext steht. Bei technischen
Fehlern liefert der Endpunkt HTTP 503.

Die Quellenliste enthält aktuell alle abgerufenen Textstellen. Die Antwort
nennt zusätzlich die verwendete Seite und den Abschnitt. Dieses Verhalten
wurde für die Embedding-Anbindung beibehalten.

### Vollständigen Ablauf testen

Im Projekt-Hauptordner mit aktivierter virtueller Umgebung:

```bash
python -m uvicorn app.main:app --app-dir harness --reload
```

Unter http://127.0.0.1:8000/docs kann `POST /wartung` getestet werden:

```json
{
  "frage": "Darf beim Programm Maschine reinigen Wäsche in der Trommel sein?",
  "produkt_id": 1
}
```

Für den getesteten Miele-Datenbestand lautet die erwartete Aussage:
Keine Textilien einfüllen; die Reinigung erfolgt mit leerer Trommel.
Beleg: Seite 56, Abschnitt „Programme“.

### Retrieval ohne Antwortgenerierung testen

```bash
python scripts/test_retrieval_live.py --live --produkt-id 1 --text "Darf beim Programm Maschine reinigen Wäsche in der Trommel sein?"
```

Dieser Test erzeugt das Frage-Embedding und ruft die Suche auf, generiert
aber keine Antwort. Er zeigt unter anderem Chunk-IDs, Seiten und Rangwerte.
Die fachliche Relevanz wird gegen die Originalanleitung geprüft.
Mit `--nur-volltext` lässt sich zum Vergleich ausschließlich die
Volltextsuche testen.

## Traces und Evaluierung

Durchläufe des Wartungs-Endpunkts werden als JSONL-Dateien im Ordner
`traces/` gespeichert. Die API-Antwort enthält die zugehörige `trace_id`.
Die Traces enthalten unter anderem:

- Frage, Produkt-ID und Zeitpunkt,
- Embedding-Modell und Vektordimension,
- alle Retrieval-Treffer einschließlich Text und Rangwerten,
- Suchaufruf und vollständigen Prompt,
- Modellversuche und Fallbacks,
- Antwort, Laufzeit und verfügbaren Tokenverbrauch.

Nicht ermittelte Kosten werden als `null` gespeichert. Die Trace-Dateien
werden nicht automatisch nach Git übertragen; vor dem Commit die
Dateiauswahl und Ignore-Regeln prüfen.

### Golden Dataset

Im Ordner `evaluation/` liegen:

| Datei | Zweck |
|---|---|
| `Golden_Dataset_15_Faelle.md` | Beschreibung der Testfälle und Bewertung |
| `golden_dataset.entwurf.json` | Maschinenlesbarer Dataset-Entwurf |
| `bewertungsvorlage_45_lauefe.json` | Vorlage für 15 Fälle mit jeweils drei Durchläufen |
| `pruefe_dataset.py` | Prüfung der Dataset-Struktur und offener Angaben |
| `kennzahlen.py` | Unterstützung bei der Kennzahlenauswertung |

Geplant sind mindestens 15 Fälle, davon mindestens 20 Prozent Negativfälle.
Die Kategorien umfassen Störung/Wartung, Produktfinder, mehrdeutige Fragen
und Fragen außerhalb des Bestands.

Bewertet wird getrennt auf drei Ebenen:

- Retrieval: Recall@5 und MRR anhand vorher festgelegter relevanter Belege.
- Generierung: Faithfulness und Answer Relevance.
- Ende-zu-Ende: drei Durchläufe pro Fall, Rubrik 0/1/2 und zwei unabhängig
  bewertende Personen. Korrektes Nichtbeantworten zählt bei entsprechendem
  Erwartungsverhalten als Erfolg.

Die Fälle sind noch mit dem tatsächlichen Produktbestand und den
Originaldokumenten vollständig abzugleichen. Strukturprüfung allein
bestätigt keine fachliche Richtigkeit:

```bash
python evaluation/pruefe_dataset.py
```

Für die formalen Testläufe müssen Fall-ID und Durchlaufnummer eindeutig
mit dem jeweiligen Trace verknüpft werden. Im bisherigen manuellen Test
sind `fall_id` und `durchlauf` noch leer; auch Code-, Datenbestand- und
Prompt-Version sind noch nicht hinterlegt. Die vollständige Evaluierung
steht noch aus.

### Bisher bestätigter Teststand

- Miele (Produkt-ID 1): 201 Chunk-Embeddings gespeichert.
- Siemens (Produkt-ID 3): 137 Chunk-Embeddings gespeichert.
- Insgesamt: 338 gespeicherte Chunk-Embeddings.
- Miele-Beispielfrage: relevante Seite 56 auf Rang 1 der Vektorsuche und
  Rang 2 der hybriden Suche.
- `POST /wartung`: korrekte Antwort mit HTTP 200 und Trace-Aufzeichnung.

Dies bestätigt den vollständigen Ablauf für diesen Testfall. Weitere
Fragen, die Trennung nach Produkt und Negativfälle müssen noch geprüft
werden. Neu gespeicherte Embeddings liegen in Supabase; sie werden nicht
mit einem Git-Push übertragen. Auch SQL-Dateien werden beim Push nicht
automatisch ausgeführt.

## Stand

| | |
|---|---|
| Schema lauffähig, vier Migrationen vorhanden | ✅ |
| RLS aktiv, Policy für `produkt` | ✅ |
| Skripte für PDF-Upload, Datenblatt-Auswertung, Chunking | ✅ |
| `chunk` gefüllt (338 Absätze aus 4 PDFs) | ✅ |
| `suche_chunks`, Volltextsuche | ✅ |
| `suche_chunks_hybrid`, Vektorsuche und RRF | ✅ |
| Chunk-Embeddings für Miele und Siemens (338 insgesamt) | ✅ |
| Embedding-Anbindung an `POST /wartung` | ✅, ein vollständiger Miele-Testfall geprüft |
| `finde_produkte` als SQL-Funktion | offen, läuft vorerst im Backend |
| Produktkatalog aus EPREL | offen |
| Trace-Aufzeichnung im Wartungs-Endpunkt | ✅ |
| Golden Dataset und Bewertungsvorlage | Entwurf vorhanden; fachlicher Abgleich und vollständige Evaluierung offen |

## Hinweis nach AI Act Art. 50
Diese Anwendung nutzt ein KI-System. Antworten können fehlerhaft sein und ersetzen
keine fachkundige Beratung. Bei Elektroreparaturen gibt die Anwendung keine
Anleitung, sondern verweist auf den Kundendienst.

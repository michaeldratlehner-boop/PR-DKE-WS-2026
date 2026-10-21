-- ============================================================
-- Haushaltsgeraete-Assistent (Waschmaschinen) - Datenbankschema
-- ============================================================

-- pgvector bereitstellen. In Supabase liegen Extensions im Schema
-- "extensions", darum der Zusatz. Ohne das gibt es keinen Typ "vector".
create extension if not exists vector with schema extensions;


-- ------------------------------------------------------------
-- produkt: der Geraetekatalog 
-- ------------------------------------------------------------
create table if not exists public.produkt (
  id             bigint generated always as identity primary key,
  hersteller     text not null,
  modell         text not null,
  bauart         text,
  kapazitaet_kg  numeric,
  energieklasse  text,
  schleuder_upm  integer,
  preis_eur      numeric,
  breite_cm      numeric,
  hoehe_cm       numeric,
  tiefe_cm       numeric,

  -- Werte aus dem EU-Energielabel (Verordnung 2019/2014).
  -- Quelle: Produktblatt des Herstellers bzw. EPREL-Datenbank.
  -- Sie stehen NICHT in der Bedienungsanleitung.
  energie_kwh_100     numeric,   -- kWh je 100 Waschzyklen
  wasser_liter_zyklus numeric,   -- Liter je Betriebszyklus
  schleuderklasse     text,      -- A bis G
  geraeuschklasse     text,      -- A bis D
  geraeusch_db        integer,   -- dB(A) beim Schleudern
  eco_dauer_min       integer,   -- Dauer "eco 40-60" in Minuten
  ean                 text,      -- eindeutige Artikelnummer

  -- Verhindert, dass dasselbe Modell doppelt importiert wird.
  constraint produkt_modell_uniq unique (hersteller, modell),

  -- Erlaubte Werte festnageln, sonst landet "A-30%" in der Spalte
  -- und jeder Filter im Produktfinder geht ins Leere.
  constraint produkt_energieklasse_chk
    check (energieklasse   is null or energieklasse   ~ '^[A-G]$'),
  constraint produkt_schleuderklasse_chk
    check (schleuderklasse is null or schleuderklasse ~ '^[A-G]$'),
  constraint produkt_geraeuschklasse_chk
    check (geraeuschklasse is null or geraeuschklasse ~ '^[A-D]$')
);


-- ------------------------------------------------------------
-- dokument: eine Bedienungsanleitung pro Geraet.
-- Die PDF-Datei selbst liegt im privaten Storage-Bucket
-- "anleitungen"; hier steht nur der Pfad dorthin.
-- ------------------------------------------------------------
create table if not exists public.dokument (
  id         bigint generated always as identity primary key,
  produkt_id bigint not null,
  typ        text   not null,
  quelle     text   not null,
  titel      text   not null,
  datei_pfad text,              -- Pfad im Storage-Bucket (bei quelle='upload')
  url        text,              -- Web-Adresse (bei quelle='web')
  sprache    text   not null default 'de',

  -- on delete cascade: loescht man ein Produkt, verschwinden seine
  -- Dokumente mit. Ohne das blockiert Postgres das Loeschen.
  constraint dokument_produkt_id_fkey foreign key (produkt_id)
    references public.produkt (id) on delete cascade,

  -- Erlaubte Werte festnageln, damit Filter verlaesslich funktionieren.
  constraint dokument_typ_chk    check (typ in ('bedienungsanleitung', 'datenblatt')),
  constraint dokument_quelle_chk check (quelle in ('upload', 'web')),

  -- Entweder eine Datei oder eine URL muss da sein, sonst zeigt die
  -- Zeile ins Leere.
  constraint dokument_ziel_chk check (datei_pfad is not null or url is not null)
);


-- ------------------------------------------------------------
-- chunk: die Anleitung in durchsuchbaren Stuecken.
-- Hier findet das Retrieval statt.
-- ------------------------------------------------------------
create table if not exists public.chunk (
  id          bigint generated always as identity primary key,
  dokument_id bigint not null,
  abschnitt   text,                    -- z.B. "Stoerungen"
  seite       integer,                 -- fuer die Quellenangabe in der Antwort
  inhalt      text not null,           -- der eigentliche Text
  kontext     text,                    -- optionale Einordnung fuers LLM

  -- 768 Dimensionen, passend zu gemini-embedding-2.
  -- Diese Zahl ist Vertrag: andere Laenge -> die DB lehnt die Zeile ab.
  embedding   extensions.vector(768),

  -- Generierte Spalte: Postgres pflegt sie selbst, bei jedem INSERT UND
  -- bei jedem UPDATE von "inhalt". Darum "generated ... stored" statt
  -- "default" - ein default wuerde nur beim Einfuegen greifen und der
  -- Suchindex waere nach einer Textkorrektur veraltet.
  fts tsvector generated always as (to_tsvector('german', inhalt)) stored,

  constraint chunk_dokument_id_fkey foreign key (dokument_id)
    references public.dokument (id) on delete cascade
);


-- ------------------------------------------------------------
-- Indizes
-- ------------------------------------------------------------

-- HNSW fuer die Vektorsuche mit Cosine-Distanz (Operator <=>).
-- Ohne diesen Index vergleicht Postgres bei jeder Suche JEDEN Chunk.

create index if not exists chunk_embedding_hnsw
  on public.chunk using hnsw (embedding extensions.vector_cosine_ops);

-- GIN fuer die deutsche Volltextsuche.
create index if not exists chunk_fts_gin
  on public.chunk using gin (fts);

-- Fremdschluessel indexieren: Postgres macht das NICHT automatisch.
create index if not exists chunk_dokument_id_idx   on public.chunk (dokument_id);
create index if not exists dokument_produkt_id_idx on public.dokument (produkt_id);

-- Haeufige Filter des Produktfinders.
create index if not exists produkt_preis_idx      on public.produkt (preis_eur);
create index if not exists produkt_kapazitaet_idx on public.produkt (kapazitaet_kg);
create index if not exists produkt_energieklasse_idx on public.produkt (energieklasse);


-- ------------------------------------------------------------
-- Row Level Security
-- Regel: "enable" allein sperrt alles zu. Ohne Policy kein Zugriff.
-- Das Backend mit dem service_role-/secret-Key umgeht RLS.
-- ------------------------------------------------------------
alter table public.produkt  enable row level security;
alter table public.dokument enable row level security;
alter table public.chunk    enable row level security;

-- Der Produktkatalog ist oeffentlich lesbar - das ist der Produktfinder.
-- Schreiben bleibt dem Backend vorbehalten (Katalog-Import).
drop policy if exists produkt_lesen_alle on public.produkt;
create policy produkt_lesen_alle
  on public.produkt for select
  to anon, authenticated
  using (true);

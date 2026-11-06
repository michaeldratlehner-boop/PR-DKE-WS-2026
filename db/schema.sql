-- Datenbankschema. Lauffaehig: stellt eine leere Datenbank komplett her.

-- pgvector. In Supabase liegen Extensions im Schema "extensions".
create extension if not exists vector with schema extensions;


-- produkt: Geraetekatalog fuer den Produktfinder
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

  -- EU-Energielabel, Quelle ist das Produktblatt (nicht die Anleitung)
  energie_kwh_100     numeric,   -- kWh je 100 Waschzyklen
  wasser_liter_zyklus numeric,   -- Liter je Betriebszyklus
  schleuderklasse     text,      -- A bis G
  geraeuschklasse     text,      -- A bis D
  geraeusch_db        integer,   -- dB(A) beim Schleudern
  eco_dauer_min       integer,   -- Dauer "eco 40-60" in Minuten
  ean                 text,      -- eindeutige Artikelnummer

  constraint produkt_modell_uniq unique (hersteller, modell),

  -- nur A-G erlauben, sonst landet Werbetext wie "A-30%" in der Spalte
  constraint produkt_energieklasse_chk
    check (energieklasse   is null or energieklasse   ~ '^[A-G]$'),
  constraint produkt_schleuderklasse_chk
    check (schleuderklasse is null or schleuderklasse ~ '^[A-G]$'),
  constraint produkt_geraeuschklasse_chk
    check (geraeuschklasse is null or geraeuschklasse ~ '^[A-D]$')
);


-- dokument: Anleitung oder Datenblatt. Die PDF-Datei liegt im
-- Storage-Bucket, hier steht nur der Pfad dorthin.
create table if not exists public.dokument (
  id         bigint generated always as identity primary key,
  produkt_id bigint not null,
  typ        text   not null,
  quelle     text   not null,
  titel      text   not null,
  datei_pfad text,              -- Pfad im Storage-Bucket (bei quelle='upload')
  url        text,              -- Web-Adresse (bei quelle='web')
  sprache    text   not null default 'de',

  -- cascade: Produkt weg -> Dokumente weg. Sonst blockiert Postgres das Loeschen.
  constraint dokument_produkt_id_fkey foreign key (produkt_id)
    references public.produkt (id) on delete cascade,

  constraint dokument_typ_chk    check (typ in ('bedienungsanleitung', 'datenblatt')),
  constraint dokument_quelle_chk check (quelle in ('upload', 'web')),

  -- Datei oder URL muss da sein, sonst zeigt die Zeile ins Leere
  constraint dokument_ziel_chk check (datei_pfad is not null or url is not null)
);


-- chunk: die Dokumente in durchsuchbaren Absaetzen. Hier wird gesucht.
create table if not exists public.chunk (
  id          bigint generated always as identity primary key,
  dokument_id bigint not null,
  abschnitt   text,                    -- z.B. "Stoerungen"
  seite       integer,                 -- fuer die Quellenangabe in der Antwort
  inhalt      text not null,           -- der eigentliche Text
  kontext     text,                    -- optionale Einordnung fuers LLM

  -- 768 ist Vertrag mit dem Backend, andere Laenge wird abgelehnt
  embedding   extensions.vector(768),

  -- generated statt default: wird auch bei UPDATE von inhalt neu berechnet
  fts tsvector generated always as (to_tsvector('german', inhalt)) stored,

  constraint chunk_dokument_id_fkey foreign key (dokument_id)
    references public.dokument (id) on delete cascade
);


-- Indizes

-- HNSW fuer die Vektorsuche, Cosine (Operator <=>). Das Distanzmass muss
-- zu dem in der Abfrage passen, sonst wird der Index nicht benutzt.

create index if not exists chunk_embedding_hnsw
  on public.chunk using hnsw (embedding extensions.vector_cosine_ops);

-- GIN fuer die Volltextsuche
create index if not exists chunk_fts_gin
  on public.chunk using gin (fts);

-- Fremdschluessel indexieren, Postgres macht das nicht von selbst
create index if not exists chunk_dokument_id_idx   on public.chunk (dokument_id);
create index if not exists dokument_produkt_id_idx on public.dokument (produkt_id);

-- Filter des Produktfinders
create index if not exists produkt_preis_idx      on public.produkt (preis_eur);
create index if not exists produkt_kapazitaet_idx on public.produkt (kapazitaet_kg);
create index if not exists produkt_energieklasse_idx on public.produkt (energieklasse);


-- Row Level Security
-- "enable" ohne Policy sperrt alles zu. Das Backend umgeht RLS mit dem
-- secret key. dokument und chunk bekommen absichtlich keine Policy:
-- darin steht der Volltext fremder Anleitungen.
alter table public.produkt  enable row level security;
alter table public.dokument enable row level security;
alter table public.chunk    enable row level security;

-- Produktkatalog darf jeder lesen, schreiben nur das Backend
drop policy if exists produkt_lesen_alle on public.produkt;
create policy produkt_lesen_alle
  on public.produkt for select
  to anon, authenticated
  using (true);

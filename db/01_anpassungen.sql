-- ============================================================
-- Einmalige Anpassung der BESTEHENDEN Datenbank an schema.sql
--
-- Hintergrund: schema.sql nutzt "create table if not exists".
-- Bei schon vorhandenen Tabellen wird der Block also uebersprungen -
-- vorhandene Spalten und Fremdschluessel bleiben, wie sie sind.
-- Dieses Skript holt die Unterschiede nach.
--
-- Gefahrlos, solange die Tabellen leer sind (Stand: 0 Zeilen).
-- Ausfuehren: Dashboard > SQL Editor > einfuegen > Run
-- ============================================================

-- ------------------------------------------------------------
-- 1. ON DELETE CASCADE nachruesten
--
-- Ohne cascade blockiert Postgres das Loeschen eines Produkts,
-- solange Dokumente daran haengen. Einen Fremdschluessel kann man
-- nicht aendern, nur loeschen und neu anlegen.
-- ------------------------------------------------------------
alter table public.dokument drop constraint if exists dokument_produkt_id_fkey;
alter table public.dokument add  constraint dokument_produkt_id_fkey
  foreign key (produkt_id) references public.produkt (id) on delete cascade;

alter table public.chunk drop constraint if exists chunk_dokument_id_fkey;
alter table public.chunk add  constraint chunk_dokument_id_fkey
  foreign key (dokument_id) references public.dokument (id) on delete cascade;


-- ------------------------------------------------------------
-- 2. fts zu einer generierten Spalte machen
--
-- Falls die Spalte nur ein "default" hat, wird sie beim Einfuegen
-- gefuellt, aber bei einem UPDATE von "inhalt" NICHT aktualisiert -
-- die Volltextsuche findet dann den alten Text.
-- Eine Spalte laesst sich nicht nachtraeglich in eine generierte
-- umwandeln, also: loeschen und neu anlegen.
--
-- Achtung: Mit der Spalte verschwindet auch ihr GIN-Index. Der wird
-- in Schritt 3 neu gebaut.
-- ------------------------------------------------------------
alter table public.chunk drop column if exists fts;
alter table public.chunk add  column fts tsvector
  generated always as (to_tsvector('german', inhalt)) stored;


-- ------------------------------------------------------------
-- 3. Indizes (legt nur an, was fehlt)
-- ------------------------------------------------------------
create index if not exists chunk_embedding_hnsw
  on public.chunk using hnsw (embedding extensions.vector_cosine_ops);

create index if not exists chunk_fts_gin
  on public.chunk using gin (fts);

create index if not exists chunk_dokument_id_idx   on public.chunk (dokument_id);
create index if not exists dokument_produkt_id_idx on public.dokument (produkt_id);
create index if not exists produkt_preis_idx       on public.produkt (preis_eur);
create index if not exists produkt_kapazitaet_idx  on public.produkt (kapazitaet_kg);


-- ------------------------------------------------------------
-- 4. Pruefregeln nachruesten
--
-- Nur moeglich, weil die Tabellen leer sind. Bei vorhandenen Daten
-- muessten diese erst die Regeln erfuellen.
-- ------------------------------------------------------------
alter table public.produkt  drop constraint if exists produkt_modell_uniq;
alter table public.produkt  add  constraint produkt_modell_uniq
  unique (hersteller, modell);

alter table public.dokument drop constraint if exists dokument_typ_chk;
alter table public.dokument add  constraint dokument_typ_chk
  check (typ in ('bedienungsanleitung', 'datenblatt'));

alter table public.dokument drop constraint if exists dokument_quelle_chk;
alter table public.dokument add  constraint dokument_quelle_chk
  check (quelle in ('upload', 'web'));

alter table public.dokument drop constraint if exists dokument_ziel_chk;
alter table public.dokument add  constraint dokument_ziel_chk
  check (datei_pfad is not null or url is not null);


-- ------------------------------------------------------------
-- 5. Kontrolle: danach sollte alles so aussehen wie erwartet
-- ------------------------------------------------------------
select column_name, is_generated, generation_expression
from information_schema.columns
where table_schema = 'public' and table_name = 'chunk' and column_name = 'fts';

select tc.table_name, tc.constraint_name, rc.delete_rule
from information_schema.table_constraints tc
join information_schema.referential_constraints rc
  on rc.constraint_name = tc.constraint_name
where tc.table_schema = 'public' and tc.constraint_type = 'FOREIGN KEY';

select tablename, indexname from pg_indexes
where schemaname = 'public' order by tablename, indexname;

select tablename, rowsecurity from pg_tables where schemaname = 'public';

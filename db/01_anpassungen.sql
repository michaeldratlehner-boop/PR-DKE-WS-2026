-- Bringt eine bestehende Datenbank auf den Stand von schema.sql.
-- Noetig, weil "create table if not exists" vorhandene Tabellen ueberspringt.
-- Bereits ausgefuehrt. Bleibt als Nachweis im Repo.

-- 1. ON DELETE CASCADE nachruesten.
-- Fremdschluessel kann man nicht aendern, nur neu anlegen.
alter table public.dokument drop constraint if exists dokument_produkt_id_fkey;
alter table public.dokument add  constraint dokument_produkt_id_fkey
  foreign key (produkt_id) references public.produkt (id) on delete cascade;

alter table public.chunk drop constraint if exists chunk_dokument_id_fkey;
alter table public.chunk add  constraint chunk_dokument_id_fkey
  foreign key (dokument_id) references public.dokument (id) on delete cascade;


-- 2. fts generiert statt default, sonst veraltet sie bei UPDATE.
-- Umwandeln geht nicht, also loeschen und neu anlegen.
-- Der GIN-Index geht dabei mit weg und kommt in Schritt 3 zurueck.
alter table public.chunk drop column if exists fts;
alter table public.chunk add  column fts tsvector
  generated always as (to_tsvector('german', inhalt)) stored;


-- 3. Indizes (legt nur an, was fehlt)
create index if not exists chunk_embedding_hnsw
  on public.chunk using hnsw (embedding extensions.vector_cosine_ops);

create index if not exists chunk_fts_gin
  on public.chunk using gin (fts);

create index if not exists chunk_dokument_id_idx   on public.chunk (dokument_id);
create index if not exists dokument_produkt_id_idx on public.dokument (produkt_id);
create index if not exists produkt_preis_idx       on public.produkt (preis_eur);
create index if not exists produkt_kapazitaet_idx  on public.produkt (kapazitaet_kg);


-- 4. Pruefregeln nachruesten
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


-- 5. Kontrolle
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

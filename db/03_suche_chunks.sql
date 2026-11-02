-- Suchfunktion fuer den technischen Berater.
-- Erste Fassung: nur Volltextsuche. query_embedding steht schon in der
-- Signatur, damit das Backend spaeter nichts umbauen muss.

create or replace function public.suche_chunks(
  query_text       text,                                 -- die Frage
  produkt_id       bigint,                               -- Pflicht: welches Geraet
  query_embedding  extensions.vector(768) default null,  -- noch ungenutzt
  treffer_limit    integer default 5
)
returns table (
  chunk_id   bigint,
  inhalt     text,
  seite      integer,
  abschnitt  text,
  fts_rang   integer,
  fts_score  real
)
language sql
stable
security definer                          -- darf chunk lesen, obwohl RLS sperrt
set search_path = public, extensions      -- gehoert zu security definer dazu
as $$
  with
  -- Frage in Wortstaemme zerlegen: "pumpt nicht ab" -> {pumpt, ab}
  woerter as (
    select tsvector_to_array(to_tsvector('german', query_text)) as liste
  ),
  -- " | " heisst ODER. Mit UND (plainto_tsquery) muesste ein Absatz alle
  -- Woerter enthalten, ganze Saetze faenden dann nie etwas.
  -- nullif: bleiben nur Fuellwoerter uebrig, kommt NULL und damit nichts.
  suchanfrage as (
    select to_tsquery('german', nullif(array_to_string(liste, ' | '), '')) as q
    from woerter
  )
  select
    c.id,
    c.inhalt,
    c.seite,
    c.abschnitt,
    (row_number() over (order by ts_rank(c.fts, s.q) desc))::integer,
    ts_rank(c.fts, s.q)
  from public.chunk c
  join public.dokument d on d.id = c.dokument_id
  cross join suchanfrage s
  -- suche_chunks.produkt_id = der Parameter, nicht die Spalte d.produkt_id
  where d.produkt_id = suche_chunks.produkt_id
    and c.fts @@ s.q
  order by ts_rank(c.fts, s.q) desc
  limit treffer_limit;
$$;

comment on function public.suche_chunks is
  'Sucht Absaetze zur Frage, eingegrenzt auf ein Produkt. Derzeit nur Volltextsuche.';


-- Kontrolle

-- Gibt es die Funktion?
select routine_name
from information_schema.routines
where routine_schema = 'public' and routine_name = 'suche_chunks';

-- Testlauf (produkt_id 1 = Miele). Leer, solange chunk leer ist.
select seite, abschnitt, left(inhalt, 70) as anfang, fts_rang
from public.suche_chunks('Was bedeutet Fehler F35?', 1);

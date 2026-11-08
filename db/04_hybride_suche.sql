begin;

create or replace function public.suche_chunks_hybrid(
  query_text text,
  produkt_id bigint,
  query_embedding extensions.vector(768) default null,
  treffer_limit integer default 5
)
returns table (
  chunk_id bigint, inhalt text, seite integer, abschnitt text,
  fts_rang integer, fts_score real,
  vektor_rang integer, vektor_distanz double precision,
  rrf_score double precision, dokument_id bigint, datei_pfad text
)
language sql stable security definer
set search_path = public, extensions
as $$
  with grenzen as (
    select greatest(1, least(coalesce(treffer_limit, 5), 20)) as anzahl
  ), suchanfrage as (
    select to_tsquery('german', nullif(array_to_string(
      tsvector_to_array(to_tsvector('german', coalesce(query_text, ''))), ' | '
    ), '')) as q
  ), kandidaten as materialized (
    -- Geraetefilter gilt VOR der Rangbildung fuer beide Suchwege.
    -- Bewusst exakte Suche fuer den kleinen Projektbestand.
    select c.id, c.inhalt, c.seite, c.abschnitt, c.fts, c.embedding,
           c.dokument_id, d.datei_pfad
    from public.chunk c
    join public.dokument d on d.id = c.dokument_id
    where d.produkt_id = suche_chunks_hybrid.produkt_id
  ), wort_rangliste as (
    select k.id, ts_rank(k.fts, s.q) as score,
           row_number() over (order by ts_rank(k.fts, s.q) desc, k.id)::integer as rang
    from kandidaten k cross join suchanfrage s
    where k.fts @@ s.q
  ), wort_treffer as (
    select * from wort_rangliste order by rang
    limit (select anzahl * 4 from grenzen)
  ), vektor_rangliste as (
    select k.id, (k.embedding <=> query_embedding)::double precision as distanz,
           row_number() over (order by k.embedding <=> query_embedding, k.id)::integer as rang
    from kandidaten k
    where query_embedding is not null and k.embedding is not null
  ), vektor_treffer as (
    select * from vektor_rangliste order by rang
    limit (select anzahl * 4 from grenzen)
  ), fusion as (
    select coalesce(w.id, v.id) as id,
           w.rang as wort_rang, w.score as wort_score,
           v.rang as vektor_rang, v.distanz,
           (coalesce(1.0 / (60.0 + w.rang), 0.0)
            + coalesce(1.0 / (60.0 + v.rang), 0.0))::double precision as score
    from wort_treffer w full outer join vektor_treffer v on v.id = w.id
  )
  select k.id, k.inhalt, k.seite, k.abschnitt,
         f.wort_rang, f.wort_score, f.vektor_rang, f.distanz,
         f.score, k.dokument_id, k.datei_pfad
  from fusion f join kandidaten k on k.id = f.id
  order by f.score desc, k.id
  limit (select anzahl from grenzen);
$$;

-- Die Funktion liest Anleitungen mit den Rechten ihres Besitzers.
revoke all on function public.suche_chunks_hybrid(text, bigint, extensions.vector, integer)
  from public, anon, authenticated;
grant execute on function public.suche_chunks_hybrid(text, bigint, extensions.vector, integer)
  to service_role;

comment on function public.suche_chunks_hybrid(text, bigint, extensions.vector, integer) is
  'Produktgefilterte Volltext- und Cosine-Suche, Fusion per RRF (k=60).';
commit;

select count(*) as chunks_gesamt, count(embedding) as chunks_mit_embedding
from public.chunk;

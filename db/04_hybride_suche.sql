-- Hybride Suche: findet Textstellen aus den Dokumenten eines ausgewaehlten
-- Geraets. Sie kombiniert passende Woerter mit inhaltlicher Aehnlichkeit.
-- Gesucht wird in bereits gespeicherten Chunks; PDFs werden hier nicht gelesen.
--
-- Ablauf der Funktion:
-- 1. einstellungen:
--    Legt die gewuenschte Trefferanzahl fest (Standard 5, mindestens 1,
--    hoechstens 20).
-- 2. passende_chunks:
--    Waehlt nur Textstellen aus, die zum angegebenen Produkt gehoeren.
--    Beide Suchwege verwenden diese Auswahl, damit keine fremde Anleitung
--    in die Ergebnisse gelangt.
-- 3. suchwoerter / suchanfrage:
--    Entfernt deutsche Fuellwoerter aus der Frage, bildet Wortstaemme und
--    verknuepft sie mit ODER. Ein Chunk muss also nicht alle Woerter enthalten.
-- 4. volltext_bewertung / volltext_treffer:
--    Findet Worttreffer, bewertet sie und vergibt Plaetze (Rang 1 ist der beste).
--    Behaelt bis zum Vierfachen der gewuenschten Trefferanzahl fuer Schritt 6.
-- 5. vektor_bewertung / vektor_treffer:
--    Vergleicht die Embeddings der Chunks mit dem Embedding der Frage.
--    Ein kleinerer Cosine-Abstand bedeutet groessere inhaltliche Aehnlichkeit.
--    Vergibt ebenfalls Plaetze und behaelt bis zum Vierfachen der Trefferanzahl.
--    Ohne Frage-Embedding entfaellt dieser Suchweg; die Volltextsuche bleibt.
-- 6. gemeinsame_treffer:
--    Fuehrt beide Listen anhand der Chunk-ID zusammen. Auch Textstellen,
--    die nur ein Suchweg gefunden hat, bleiben dabei erhalten.
-- 7. gesamtbewertung:
--    Berechnet RRF-Punkte: je Suchweg 1 / (60 + Rang), bei fehlendem Rang 0.
--    Addiert die Punkte beider Suchwege zu einer gemeinsamen Bewertung.
-- 8. Abschliessendes SELECT:
--    Sortiert nach Gesamtpunkten (bei Gleichstand nach Chunk-ID) und liefert
--    die gewuenschte Anzahl an Treffern samt Text, Rangwerten und Quellen.

begin;

create or replace function public.suche_chunks_hybrid(
  query_text text,
  produkt_id bigint,
  query_embedding extensions.vector(768) default null,
  treffer_limit integer default 5
)
returns table (
  chunk_id bigint,
  inhalt text,
  seite integer,
  abschnitt text,
  fts_rang integer,
  fts_score real,
  vektor_rang integer,
  vektor_distanz double precision,
  rrf_score double precision,
  dokument_id bigint,
  datei_pfad text
)
language sql stable security definer
set search_path = public, extensions
as $$
  -- WITH benennt Zwischenergebnisse, auf die die folgenden Schritte zugreifen.
  with

  -- 1. Standard: 5 Ergebnisse, mindestens 1 und hoechstens 20.
  einstellungen as (
    select greatest(1, least(coalesce(treffer_limit, 5), 20)) as anzahl
  ),

  -- 2. Nur Chunks des ausgewaehlten Geraets beruecksichtigen.
  -- MATERIALIZED stellt dieses Zwischenergebnis fuer beide Suchwege bereit.
  -- Wie bisher: exakte Vektorsuche fuer den kleinen Projektbestand.
  passende_chunks as materialized (
    select
      c.id,
      c.inhalt,
      c.seite,
      c.abschnitt,
      c.fts,
      c.embedding,
      c.dokument_id,
      d.datei_pfad
    from public.chunk as c
    join public.dokument as d on d.id = c.dokument_id
    where d.produkt_id = suche_chunks_hybrid.produkt_id
  ),

  -- 3. Frage in Wortstaemme zerlegen und Fuellwoerter entfernen.
  suchwoerter as (
    select tsvector_to_array(
      to_tsvector('german', coalesce(query_text, ''))
    ) as woerter
  ),
  -- ODER verknuepft die Woerter; eine leere Wortliste ergibt keine Worttreffer.
  suchanfrage as (
    select to_tsquery(
      'german',
      nullif(array_to_string(woerter, ' | '), '')
    ) as suche
    from suchwoerter
  ),

  -- 4. Volltextsuche: Worttreffer finden und bewerten.
  volltext_bewertung as (
    select
      c.id,
      ts_rank(c.fts, s.suche) as wort_score
    from passende_chunks as c
    cross join suchanfrage as s
    where c.fts @@ s.suche
  ),
  -- Bessere Bewertungen erhalten kleinere Rangnummern.
  -- Bei Gleichstand entscheidet die Chunk-ID, damit die Reihenfolge stabil ist.
  volltext_treffer as (
    select
      id,
      wort_score,
      row_number() over (
        order by wort_score desc, id
      )::integer as wort_rang
    from volltext_bewertung
    order by wort_score desc, id
    -- Fuer die Zusammenfuehrung zunaechst mehr Treffer sammeln.
    limit (select anzahl * 4 from einstellungen)
  ),

  -- 5. Vektorsuche: Cosine-Abstand zur Frage berechnen.
  -- Ohne Frage-Embedding bleibt dieser Suchweg leer; die Volltextsuche bleibt.
  vektor_bewertung as (
    select
      c.id,
      (c.embedding <=> query_embedding)::double precision as distanz
    from passende_chunks as c
    where query_embedding is not null
      and c.embedding is not null
  ),
  -- Ein kleinerer Abstand bedeutet groessere inhaltliche Aehnlichkeit.
  vektor_treffer as (
    select
      id,
      distanz,
      row_number() over (
        order by distanz, id
      )::integer as vektor_rang
    from vektor_bewertung
    order by distanz, id
    limit (select anzahl * 4 from einstellungen)
  ),

  -- 6. Beide Listen verbinden. FULL OUTER JOIN behaelt auch Chunks,
  -- die nur in einem der beiden Suchwege gefunden wurden.
  gemeinsame_treffer as (
    select
      coalesce(w.id, v.id) as id,
      w.wort_score,
      w.wort_rang,
      v.distanz,
      v.vektor_rang
    from volltext_treffer as w
    full outer join vektor_treffer as v on w.id = v.id
  ),

  -- 7. Reciprocal Rank Fusion (RRF): Punkte aus beiden Platzierungen addieren.
  -- Je Suchweg: 1 / (60 + Rang). Fehlt der Rang, gibt es 0 Punkte.
  -- Die Konstante 60 daempft den Einfluss einzelner Spitzenplatzierungen.
  gesamtbewertung as (
    select
      id,
      wort_score,
      wort_rang,
      distanz,
      vektor_rang,
      (
        coalesce(1.0 / (60.0 + wort_rang), 0.0)
        + coalesce(1.0 / (60.0 + vektor_rang), 0.0)
      )::double precision as gesamt_score
    from gemeinsame_treffer
  )

  -- 8. Beste Treffer mit Text, Rangwerten und Quellenangaben zurueckgeben.
  select
    c.id as chunk_id,
    c.inhalt,
    c.seite,
    c.abschnitt,
    g.wort_rang as fts_rang,
    g.wort_score as fts_score,
    g.vektor_rang,
    g.distanz as vektor_distanz,
    g.gesamt_score as rrf_score,
    c.dokument_id,
    c.datei_pfad
  from gesamtbewertung as g
  join passende_chunks as c on c.id = g.id
  order by g.gesamt_score desc, c.id
  limit (select anzahl from einstellungen);
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

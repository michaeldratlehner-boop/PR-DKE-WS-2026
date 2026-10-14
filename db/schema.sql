-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.produkt (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  hersteller text NOT NULL,
  modell text NOT NULL,
  bauart text,
  kapazitaet_kg numeric,
  energieklasse text,
  schleuder_upm integer,
  preis_eur numeric,
  breite_cm numeric,
  hoehe_cm numeric,
  tiefe_cm numeric,
  datenblatt_url text,
  CONSTRAINT produkt_pkey PRIMARY KEY (id)
);
CREATE TABLE public.nutzer (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  vorname text NOT NULL,
  nachname text NOT NULL,
  email text NOT NULL UNIQUE,
  erstellt_am timestamp with time zone NOT NULL DEFAULT (now() AT TIME ZONE 'utc'::text),
  CONSTRAINT nutzer_pkey PRIMARY KEY (id)
);
CREATE TABLE public.nutzer_geraet (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  nutzer_id bigint NOT NULL,
  produkt_id bigint NOT NULL,
  bezeichnung text,
  kaufdatum date,
  CONSTRAINT nutzer_geraet_pkey PRIMARY KEY (id),
  CONSTRAINT nutzer_geraet_produkt_id_fkey FOREIGN KEY (produkt_id) REFERENCES public.produkt(id),
  CONSTRAINT nutzer_geraet_nutzer_id_fkey FOREIGN KEY (nutzer_id) REFERENCES public.nutzer(id)
);
CREATE TABLE public.dokument (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  produkt_id bigint NOT NULL,
  typ text NOT NULL,
  quelle text NOT NULL,
  titel text NOT NULL,
  datei_pfad text,
  url text,
  sprache text NOT NULL DEFAULT 'de'::text,
  CONSTRAINT dokument_pkey PRIMARY KEY (id),
  CONSTRAINT dokument_produkt_id_fkey FOREIGN KEY (produkt_id) REFERENCES public.produkt(id)
);
CREATE TABLE public.chunk (
  id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  dokument_id bigint NOT NULL,
  abschnitt text,
  seite integer,
  inhalt text NOT NULL,
  kontext text,
  embedding USER-DEFINED,
  fts tsvector DEFAULT to_tsvector('german'::regconfig, inhalt),
  CONSTRAINT chunk_pkey PRIMARY KEY (id),
  CONSTRAINT chunk_dokument_id_fkey FOREIGN KEY (dokument_id) REFERENCES public.dokument(id)
);

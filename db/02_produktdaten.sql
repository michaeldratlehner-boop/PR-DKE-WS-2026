
-- 1. Neue Spalten aus dem EU-Energielabel
alter table public.produkt
  add column if not exists energie_kwh_100      numeric,  -- kWh je 100 Waschzyklen
  add column if not exists wasser_liter_zyklus  numeric,  -- Liter je Betriebszyklus
  add column if not exists schleuderklasse      text,     -- A bis G
  add column if not exists geraeuschklasse      text,     -- A bis D
  add column if not exists geraeusch_db         integer,  -- dB(A) beim Schleudern
  add column if not exists eco_dauer_min        integer,  -- Dauer "eco 40-60" in Minuten
  add column if not exists ean                  text;     -- eindeutige Artikelnummer


-- 2. Nur A-G bzw. A-D erlauben, sonst landet Werbetext wie "A-30%" drin
alter table public.produkt drop constraint if exists produkt_energieklasse_chk;
alter table public.produkt add  constraint produkt_energieklasse_chk
  check (energieklasse is null or energieklasse ~ '^[A-G]$');

alter table public.produkt drop constraint if exists produkt_schleuderklasse_chk;
alter table public.produkt add  constraint produkt_schleuderklasse_chk
  check (schleuderklasse is null or schleuderklasse ~ '^[A-G]$');

alter table public.produkt drop constraint if exists produkt_geraeuschklasse_chk;
alter table public.produkt add  constraint produkt_geraeuschklasse_chk
  check (geraeuschklasse is null or geraeuschklasse ~ '^[A-D]$');


-- 3. datenblatt_url raus: ein Datenblatt ist ein Dokument und gehoert
-- in die Tabelle dokument (typ = 'datenblatt').
alter table public.produkt drop column if exists datenblatt_url;


-- 4. Index fuer den Produktfinder
create index if not exists produkt_energieklasse_idx
  on public.produkt (energieklasse);


-- 5. Kontrolle
select column_name, data_type
from information_schema.columns
where table_schema = 'public' and table_name = 'produkt'
order by ordinal_position;

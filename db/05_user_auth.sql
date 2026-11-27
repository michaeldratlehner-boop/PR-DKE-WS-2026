-- Verbindet die Tabelle public."user" mit Supabase Auth (auth.users).
-- Registrierung und Anmeldung laufen ueber Supabase Auth. Das Backend legt
-- nach der Registrierung zusaetzlich eine Zeile in public."user" an und
-- traegt dort die ID aus auth.users als auth_id ein.
-- "user" ist in Postgres ein reserviertes Wort, daher die Anfuehrungszeichen.


-- 1. Das Passwort verwaltet Supabase selbst, ein eigener Hash entfaellt.
alter table public."user" drop column if exists passwort_hash;


-- 2. Verweis auf den Supabase-User. Ohne Default: den Wert setzt das Backend.
alter table public."user" add column if not exists auth_id uuid not null;

alter table public."user" drop constraint if exists user_auth_id_key;
alter table public."user" add  constraint user_auth_id_key unique (auth_id);


-- 3. Bestehende User einmalig nachtragen
insert into public."user" (email, auth_id, erstellt_am)
select u.email, u.id, u.created_at
from auth.users u
where not exists (select 1 from public."user" p where p.auth_id = u.id);


-- 4. Kontrolle
select id, email, auth_id, erstellt_am from public."user" order by id;

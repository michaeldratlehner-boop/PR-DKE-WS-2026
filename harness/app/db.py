from supabase import Client, create_client

from app.config import settings

# Ein Client für die ganze Anwendung (Secret key, nur serverseitig)
_client: Client = create_client(settings.supabase_url, settings.supabase_key)


def registriere_benutzer(email: str, passwort: str):
    """Legt einen neuen Benutzer in Supabase an."""
    # eigener Client mit dem anon key, damit _client nicht verändert wird
    auth_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    antwort = auth_client.auth.sign_up({"email": email, "password": passwort})

    # Ist die E-Mail schon vergeben, meldet Supabase keinen Fehler, sondern
    # gibt einen Schein-User ohne identities zurück. Dann nichts eintragen.
    if not antwort.user or not antwort.user.identities:
        raise ValueError("E-Mail ist bereits registriert.")

    # zusätzlich eine Zeile in unserer eigenen Tabelle "user" anlegen
    _client.table("user").insert({
        "email": email,
        "auth_id": antwort.user.id,
    }).execute()

    return antwort


def hole_user_id(email: str) -> int:
    """Sucht die id aus unserer Tabelle "user", z.B. für user_produkt."""
    antwort = _client.table("user").select("id").eq("email", email).single().execute()
    return antwort.data["id"]


def melde_benutzer_an(email: str, passwort: str):
    """Prüft E-Mail und Passwort. Bei falschen Daten gibt es einen Fehler."""
    auth_client = create_client(settings.supabase_url, settings.supabase_anon_key)
    antwort = auth_client.auth.sign_in_with_password({"email": email, "password": passwort})
    return antwort


def hole_produkte(limit: int = 3) -> list[dict]:
    """Liest die ersten Produkte aus der Tabelle 'produkt'."""
    antwort = _client.table("produkt").select("*").limit(limit).execute()
    return antwort.data


def finde_produkte(
    hersteller: str | None = None,
    bauart: str | None = None,
    energieklasse: str | None = None,
    kapazitaet_kg_min: float | None = None,
    hoehe_cm_max: float | None = None,
    limit: int = 3,
) -> list[dict]:
    """Filtert den Produktkatalog. Leere Filter werden ignoriert."""
    abfrage = _client.table("produkt").select("*")

    if hersteller:
        abfrage = abfrage.ilike("hersteller", f"%{hersteller}%")
    if bauart:
        abfrage = abfrage.ilike("bauart", f"%{bauart}%")
    if energieklasse:
        klassen = "ABCDEFG"
        # "mindestens C" = A, B oder C
        abfrage = abfrage.in_("energieklasse", list(klassen[: klassen.index(energieklasse) + 1]))
    if kapazitaet_kg_min is not None:
        abfrage = abfrage.gte("kapazitaet_kg", kapazitaet_kg_min)
    if hoehe_cm_max is not None:
        abfrage = abfrage.lte("hoehe_cm", hoehe_cm_max)

    antwort = abfrage.order("energieklasse").order("preis_eur").limit(limit).execute()
    return antwort.data

def suche_wartungs_chunks(
        frage: str,
        produkt_id: int,
        embedding: list[float] | None = None,
        limit: int = 5
) -> list[dict]:
    """Sucht passende Absätze in der Datenbank."""
    # query_embedding wird jetzt mit übergeben
    antwort = _client.rpc(
        "suche_chunks_hybrid",
        {
            "query_text": frage,
            "produkt_id": produkt_id,
            "query_embedding": embedding,
            "treffer_limit": limit
        }
    ).execute()
    return antwort.data or []

from supabase import Client, create_client

from app.config import settings

# Ein Client für die ganze Anwendung (Secret key, nur serverseitig)
_client: Client = create_client(settings.supabase_url, settings.supabase_key)


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
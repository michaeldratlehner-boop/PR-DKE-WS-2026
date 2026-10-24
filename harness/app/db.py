from supabase import Client, create_client

from app.config import settings

# Ein Client für die ganze Anwendung (Secret key, nur serverseitig)
_client: Client = create_client(settings.supabase_url, settings.supabase_key)


def hole_produkte(limit: int = 3) -> list[dict]:
    """Liest die ersten Produkte aus der Tabelle 'produkt'."""
    antwort = _client.table("produkt").select("*").limit(limit).execute()
    return antwort.data
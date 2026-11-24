# In dieser Datei sind die Schnittstellen für Registrierung und Anmeldung.
# Das Frontend schickt E-Mail und Passwort hierher, wir geben es an Supabase weiter.
import logging

from fastapi import APIRouter, HTTPException

from app.db import melde_benutzer_an, registriere_benutzer
from app.schemas import BenutzerAnfrage, BenutzerAntwort

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Benutzer"])


@router.post("/registrierung", response_model=BenutzerAntwort)
def registrierung(anfrage: BenutzerAnfrage) -> BenutzerAntwort:
    """Legt ein neues Konto an."""
    # Supabase legt den Benutzer an, bei einem Fehler (z.B. E-Mail schon vergeben) landen wir im except
    try:
        antwort = registriere_benutzer(anfrage.email, anfrage.passwort)
    except Exception:
        logger.exception("Registrierung fehlgeschlagen")
        raise HTTPException(
            status_code=400,
            detail="Registrierung fehlgeschlagen. Gibt es die E-Mail schon?",
        )

    # wenn E-Mail-Bestätigung an ist, gibt es noch keine Session
    token = None
    if antwort.session:
        token = antwort.session.access_token

    return BenutzerAntwort(email=anfrage.email, token=token)


@router.post("/anmeldung", response_model=BenutzerAntwort)
def anmeldung(anfrage: BenutzerAnfrage) -> BenutzerAntwort:
    """Meldet einen Benutzer mit E-Mail und Passwort an."""
    # Supabase prüft E-Mail und Passwort, bei falschen Daten landen wir im except
    try:
        antwort = melde_benutzer_an(anfrage.email, anfrage.passwort)
    except Exception:
        logger.exception("Anmeldung fehlgeschlagen")
        raise HTTPException(
            status_code=401,
            detail="E-Mail oder Passwort ist falsch.",
        )

    # das Token zeigt später, dass der Benutzer angemeldet ist
    return BenutzerAntwort(email=anfrage.email, token=antwort.session.access_token)

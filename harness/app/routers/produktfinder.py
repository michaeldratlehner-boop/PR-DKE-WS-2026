import logging

from fastapi import APIRouter, HTTPException

from app.db import finde_produkte
from app.schemas import Produkt, ProduktfinderAnfrage, ProduktfinderAntwort

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Produktfinder"])


@router.post("/produktfinder", response_model=ProduktfinderAntwort)
def produktfinder(anfrage: ProduktfinderAnfrage) -> ProduktfinderAntwort:
    """Sucht passende Waschmaschinen anhand der fünf Eingaben (alle optional)."""
    try:
        zeilen = finde_produkte(**anfrage.model_dump())
    except Exception:
        logger.exception("Produktsuche fehlgeschlagen")
        raise HTTPException(
            status_code=503,
            detail="Die Produktdatenbank ist gerade nicht erreichbar.",
        )

    treffer = [
        Produkt(
            produkt_id=z["id"],
            hersteller=z["hersteller"],
            modell=z["modell"],
            bauart=z.get("bauart"),
            kapazitaet_kg=z.get("kapazitaet_kg"),
            energieklasse=z.get("energieklasse"),
            hoehe_cm=z.get("hoehe_cm"),
            preis_eur=z.get("preis_eur"),
        )
        for z in zeilen
    ]
    return ProduktfinderAntwort(treffer=treffer)
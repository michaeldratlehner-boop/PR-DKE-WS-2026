from fastapi import APIRouter

from app.schemas import Quelle, WartungAnfrage, WartungAntwort

router = APIRouter(tags=["Wartung"])


@router.post("/wartung", response_model=WartungAntwort)
def wartung(anfrage: WartungAnfrage) -> WartungAntwort:
    """Beantwortet eine Wartungsfrage zu einem Gerät. Aktuell nur Platzhalter."""
    return WartungAntwort(
        antwort=(
            "Das ist eine Platzhalter-Antwort. Hier steht später die Antwort "
            "des Assistenten zu deiner Frage."
        ),
        quellen=[Quelle(seite=1, abschnitt="Platzhalter")],
    )
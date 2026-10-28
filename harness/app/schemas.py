from pydantic import BaseModel, Field

#IN DIESER DATEI WERDEN ALLE EIN- UND AUSGABEFORMATE DEFINIERT!

#pydantic prüft automatisch, ob das Eingabepattern eingehalten wird, und nur valide Werte verwendet werden.
class ProduktfinderAnfrage(BaseModel):
    """Die fünf Eingaben aus dem Produktfinder. Alle optional."""
    hersteller: str | None = None
    bauart: str | None = None
    energieklasse: str | None = Field(default=None, pattern="^[A-G]$")
    kapazitaet_kg_min: float | None = Field(default=None, gt=0)
    hoehe_cm_max: float | None = Field(default=None, gt=0)
#Aktuelle Annahme: Alle Eingabefelder des Produktfinders sind optional und können leer bleiben.
#Die Eingabe der Energieklasse, Kapazität bezieht sich auf die minimal Anforderung, während Höhe ein maximum definiert.

class Produkt(BaseModel):
    """Ein Treffer, so wie ihn eine Karte im Frontend braucht."""
    produkt_id: int
    hersteller: str
    modell: str
    bauart: str | None = None
    kapazitaet_kg: float | None = None
    energieklasse: str | None = None
    hoehe_cm: float | None = None
    preis_eur: float | None = None


class ProduktfinderAntwort(BaseModel):
    treffer: list[Produkt]
    hinweis: str = "Du sprichst mit einer KI-Anwendung."
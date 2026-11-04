from pydantic import BaseModel, Field, ConfigDict
#IN DIESER DATEI WERDEN ALLE EIN- UND AUSGABEFORMATE DEFINIERT!

# Ein gemeinsamer KI-Hinweis (EU AI Act, Art. 50) für alle Antworten
KI_HINWEIS = "Du sprichst mit einer KI-Anwendung."

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
    hinweis: str = KI_HINWEIS

class ChatAnfrage(BaseModel):
    nachricht: str

class WartungAnfrage(BaseModel):
    """Eine Wartungsfrage zu einem bestimmten Gerät."""
    # entfernt Leerzeichen am Rand, damit "   " als leer gilt
    model_config = ConfigDict(str_strip_whitespace=True)

    frage: str = Field(min_length=3, max_length=1500)
    produkt_id: int = Field(gt=0)

class Quelle(BaseModel):
    """Eine Fundstelle in der Anleitung, auf die sich die Antwort stützt."""
    seite: int | None = None
    abschnitt: str | None = None

class WartungAntwort(BaseModel):
    antwort: str
    quellen: list[Quelle] = Field(default_factory=list)
    # False, wenn in der Anleitung nichts Passendes steht
    gefunden: bool = True
    hinweis: str = KI_HINWEIS
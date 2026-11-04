"""Ein JSONL-Trace je abgeschlossenem oder fehlgeschlagenem Verarbeitungslauf.

Nur Python-Standardbibliothek. Bestehende Router rufen den Recorder auf.
Dieses Modul fuehrt selbst weder Tools noch Modellaufrufe aus.
"""

import asyncio
import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from uuid import uuid4

logger = logging.getLogger(__name__)
TRACE_ORDNER = Path(__file__).resolve().parents[2] / "traces"
_GEHEIME_FELDER = {
    "api_key", "gemini_api_key", "supabase_key", "ausweich_api_key",
    "authorization", "access_token", "refresh_token", "password", "database_url",
}


def _bereinigen(wert):
    if isinstance(wert, dict):
        return {
            schluessel: "[entfernt]" if str(schluessel).lower() in _GEHEIME_FELDER
            else _bereinigen(inhalt)
            for schluessel, inhalt in wert.items()
        }
    if isinstance(wert, (list, tuple)):
        return [_bereinigen(inhalt) for inhalt in wert]
    if isinstance(wert, Decimal):
        return float(wert)
    if isinstance(wert, (Path, datetime)):
        return str(wert)
    return wert


def _speichern(lauf: dict, verzeichnis: Path) -> None:
    verzeichnis.mkdir(parents=True, exist_ok=True)
    ziel = verzeichnis / f"{lauf['trace_id']}.jsonl"
    temporaer = ziel.with_suffix(".tmp")
    text = json.dumps(_bereinigen(lauf), ensure_ascii=False, allow_nan=False) + "\n"
    try:
        temporaer.write_text(text, encoding="utf-8")
        os.replace(temporaer, ziel)
    finally:
        temporaer.unlink(missing_ok=True)


@contextmanager
def trace_lauf(
    eingabe: str,
    *,
    produkt_id: int | None = None,
    fall_id: str | None = None,
    durchlauf: int | None = None,
    komponente: str = "berater",
    verzeichnis: str | Path | None = None,
):
    """Liefert ein auszufuellendes dict und speichert es beim Verlassen.

Unbekannte Tokens/Kosten bleiben None (JSON null), nicht 0.
Bei Streaming muss dieser Kontext IN der Generatorfunktion geoeffnet werden.
"""
    if durchlauf is not None and durchlauf not in (1, 2, 3):
        raise ValueError("Fuer die geplante Messung ist durchlauf 1, 2 oder 3.")
    start = perf_counter()
    lauf = {
        "schema_version": 1,
        "trace_id": str(uuid4()),
        "zeitpunkt_utc": datetime.now(timezone.utc).isoformat(),
        "komponente": komponente,
        "fall_id": fall_id,
        "durchlauf": durchlauf,
        "produkt_id": produkt_id,
        "eingabe": eingabe,
        "nachrichten": [],
        "finaler_prompt": None,
        "retrieval_treffer": [],
        "tool_aufrufe": [],
        "modell": None,
        "modell_parameter": {},
        "modell_versuche": [],
        "embedding_modell": None,
        "embedding_dimensionen": None,
        "ausgabe": None,
        "tokenverbrauch": None,
        "kosten_usd": None,
        "versionen": {"code": None, "datenbestand": None, "prompt": None},
        "status": "laufend",
        "fehler": None,
        "dauer_ms": None,
    }
    ursprungsfehler = None
    try:
        yield lauf
        lauf["status"] = "ok"
    except BaseException as fehler:
        ursprungsfehler = fehler
        lauf["status"] = (
            "abgebrochen" if isinstance(fehler, (asyncio.CancelledError, GeneratorExit, KeyboardInterrupt))
            else "fehler"
        )
        # Keine ungefilterten SDK-Fehlermeldungen mit Request-/Zugangsdaten ablegen.
        lauf["fehler"] = {"typ": type(fehler).__name__}
        raise
    finally:
        lauf["dauer_ms"] = round((perf_counter() - start) * 1000, 3)
        try:
            _speichern(lauf, Path(verzeichnis) if verzeichnis is not None else TRACE_ORDNER)
        except (OSError, TypeError, ValueError):
            if ursprungsfehler is None:
                raise
            logger.exception("Zusaetzlich zum Verarbeitungsfehler konnte der Trace nicht gespeichert werden.")


@contextmanager
def modellversuch(lauf: dict, modell: str, *, parameter: dict | None = None):
    """Innerhalb des bereits vorhandenen Fallbacks um EINEN Modellversuch legen."""
    start = perf_counter()
    versuch = {
        "modell": modell,
        "parameter": dict(parameter or {}),
        "status": "laufend",
        "tokenverbrauch": None,
        "kosten_usd": None,
        "dauer_ms": None,
        "fehler": None,
    }
    lauf["modell_versuche"].append(versuch)
    try:
        yield versuch
        versuch["status"] = "ok"
        lauf["modell"] = modell
        lauf["modell_parameter"] = dict(parameter or {})
    except BaseException as fehler:
        versuch["status"] = (
            "abgebrochen" if isinstance(fehler, (asyncio.CancelledError, GeneratorExit, KeyboardInterrupt))
            else "fehler"
        )
        versuch["fehler"] = {"typ": type(fehler).__name__}
        raise
    finally:
        versuch["dauer_ms"] = round((perf_counter() - start) * 1000, 3)

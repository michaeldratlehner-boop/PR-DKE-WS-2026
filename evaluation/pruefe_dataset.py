"""Prueft Vollstaendigkeit, nicht die fachliche Wahrheit der Sollantworten."""

import argparse
import json
from pathlib import Path


def pruefen(dataset, *, final=False):
    fehler = []
    faelle = dataset.get("faelle", [])
    if len(faelle) < 15:
        fehler.append("Mindestens 15 Testfaelle sind erforderlich.")
    ids = [fall.get("id") for fall in faelle]
    if len(ids) != len(set(ids)) or any(not fall_id for fall_id in ids):
        fehler.append("Jeder Fall benoetigt eine eindeutige ID.")
    negative = sum(fall.get("negativfall") is True for fall in faelle)
    if negative * 5 < len(faelle):
        fehler.append("Mindestens 20 Prozent der Faelle muessen Negativfaelle sein.")
    for fall in faelle:
        fall_id = fall.get("id", "ohne ID")
        if not fall.get("frage") or not fall.get("kategorie") or not fall.get("erwartete_kernaussagen"):
            fehler.append(f"{fall_id}: Frage, Kategorie oder Sollangaben fehlen.")
        if type(fall.get("negativfall")) is not bool or type(fall.get("bereit")) is not bool:
            fehler.append(f"{fall_id}: negativfall und bereit muessen boolesche Werte sein.")
        if fall.get("erwartete_aktion") not in {"antwort", "produktliste", "rueckfrage", "ablehnung"}:
            fehler.append(f"{fall_id}: ungueltige erwartete_aktion.")
        if fall.get("bereit") and fall.get("noch_zu_klaeren"):
            fehler.append(f"{fall_id}: als bereit markiert, obwohl Klaerungen offen sind.")
        if fall.get("bereit") and fall.get("erwartete_aktion") in {"antwort", "produktliste"}:
            quellen = fall.get("erwartete_quellen", [])
            if not quellen or any(
                not (type(q.get("produkt_id")) is int and q["produkt_id"] > 0)
                and not (q.get("bezeichnung") and type(q.get("seite")) is int and q["seite"] > 0)
                for q in quellen
            ):
                fehler.append(f"{fall_id}: konkrete erwartete Quelle fehlt.")
        if final and not fall.get("bereit"):
            fehler.append(f"{fall_id}: noch nicht fachlich vervollstaendigt.")
    return fehler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("datei", nargs="?", type=Path, default=Path(__file__).with_name("golden_dataset.entwurf.json"))
    parser.add_argument("--final", action="store_true", help="offene Faelle als Fehler behandeln")
    args = parser.parse_args()
    dataset = json.loads(args.datei.read_text(encoding="utf-8"))
    faelle = dataset.get("faelle", [])
    print(f"{len(faelle)} Faelle; {sum(f.get('negativfall') is True for f in faelle)} Negativfaelle; "
          f"{sum(not f.get('bereit') for f in faelle)} noch zu vervollstaendigen.")
    fehler = pruefen(dataset, final=args.final)
    for meldung in fehler:
        print("OFFEN/FEHLER:", meldung)
    if fehler:
        raise SystemExit(2)
    print("Struktur gueltig." if not args.final else "Formal vollstaendig; Quellen fachlich durch das Team pruefen.")


if __name__ == "__main__":
    main()

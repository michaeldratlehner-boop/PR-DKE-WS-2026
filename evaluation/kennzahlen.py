"""Kleine Hilfsfunktionen fuer die manuelle Evaluierung, ohne LLM-as-a-Judge."""


def retrieval_kennzahlen(erwartete_quellen, treffer, k=5):
    """Quellen-Schluessel z.B. 'dokument:12/seite:34'; gleiche Einheit verwenden.

Mehrere Chunks derselben erwarteten Seite zaehlen beim Recall nur einmal.
MRR wird hier ueber die betrachteten Top-k berechnet: deshalb MRR@k.
Negativfaelle ohne relevante Quelle sind nicht als Retrieval-Misserfolg definiert.
"""
    if not isinstance(k, int) or isinstance(k, bool) or k < 1:
        raise ValueError("k muss eine positive ganze Zahl sein.")
    relevante = set(erwartete_quellen)
    if not relevante:
        return {"recall_at_k": None, "reciprocal_rank_at_k": None, "k": k}
    beste = list(treffer)[:k]
    recall = len(relevante.intersection(beste)) / len(relevante)
    rr = next((1 / rang for rang, quelle in enumerate(beste, 1) if quelle in relevante), 0.0)
    return {"recall_at_k": recall, "reciprocal_rank_at_k": rr, "k": k}


def faithfulness_anteil(aussagen_gedeckt):
    """Manuell pruefen: ein bool je fachlicher Aussage. Keine Aussagen -> N/A."""
    aussagen = list(aussagen_gedeckt)
    if any(type(wert) is not bool for wert in aussagen):
        raise ValueError("Je Aussage ist True oder False erforderlich.")
    return sum(aussagen) / len(aussagen) if aussagen else None


def bestehensquote(punkte):
    """Ein Durchlauf ist mit 2 Punkten bestanden; genau drei echte Bewertungen."""
    werte = list(punkte)
    if len(werte) != 3 or any(type(wert) is not int or wert not in (0, 1, 2) for wert in werte):
        raise ValueError("Genau drei Bewertungen aus 0, 1 oder 2 sind erforderlich.")
    return sum(wert == 2 for wert in werte) / 3

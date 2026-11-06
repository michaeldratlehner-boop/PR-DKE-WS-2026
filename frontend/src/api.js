// Adresse des Harness. Fällt auf lokal zurück, wenn keine Variable gesetzt ist.
const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

// Macht aus "6 kg" oder "80 cm" die Zahl 6 bzw. 80. Leer -> null.
function zahlAusText(text) {
    if (!text) return null;
    const zahl = parseFloat(text);
    return Number.isNaN(zahl) ? null : zahl;
}

// Schickt die Filter des Produktfinders an das Backend.
export async function sucheProdukte(filter) {
    // Frontend-Namen -> Namen, die das Backend (schemas.py) erwartet
    const body = {
        hersteller: filter.hersteller || null,
        bauart: filter.bauart || null,
        energieklasse: filter.energieklasse || null,
        kapazitaet_kg_min: zahlAusText(filter.kapazitaet),
        hoehe_cm_max: zahlAusText(filter.hoehe),
    };

    const antwort = await fetch(`${API_URL}/produktfinder`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });

    if (!antwort.ok) {
        throw new Error(`Backend-Fehler ${antwort.status}`);
    }

    return antwort.json();
}
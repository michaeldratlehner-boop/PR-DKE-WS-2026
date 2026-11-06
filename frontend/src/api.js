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

    let antwort;
    try {
        antwort = await fetch(`${API_URL}/produktfinder`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
    } catch {
        // fetch wirft nur, wenn gar keine Verbindung zustande kam
        throw new Error("Der Server ist nicht erreichbar.");
    }

    if (!antwort.ok) {
        let text = `Backend-Fehler ${antwort.status}`;
        try {
            // das Backend schickt bei 503 einen lesbaren Text im Feld "detail"
            const daten = await antwort.json();
            if (typeof daten.detail === "string") text = daten.detail;
        } catch {
            /* keine JSON-Antwort, der Standardtext bleibt */
        }
        throw new Error(text);
    }


    return antwort.json();
}


// Wartungsfrage an das FastAPI-Backend senden
//export -> damit andere die Funktion importieren können,
//async -> funktion wartet auf Serverantwort - ohne Benutzeroberfläche zu blockieren
export async function frageWartung(frage, produktId) {

    //sendet an API Wartung POST
    const antwort = await fetch(`${API_URL}/wartung`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        //Datenübertragung, stringify -> wandelt Text um in json
        body: JSON.stringify({
            frage: frage,
            produkt_id: produktId
        })
    });

    if (!antwort.ok) {
        throw new Error("Fehler bei der Wartungsanfrage");
    }

    return await antwort.json();
}

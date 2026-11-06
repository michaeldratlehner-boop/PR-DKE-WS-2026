
import { useState, useRef } from 'react';
import { frageWartung } from './api.js';
import './Wartungsfragen.css';

export default function Wartungsfragen({ setSeite }) {

    // Speichert die eingegebene Frage
    const [frage, setFrage] = useState("");

    // Speichert den Namen der ausgewählten PDF-Datei
    const [datei, setDatei] = useState(null);

    // Bestimmt, ob die Antwortansicht angezeigt wird
    const [antwortAnzeigen, setAntwortAnzeigen] = useState(false);

    // Speichert die tatsächliche Antwort von FastAPI
    const [antwort, setAntwort] = useState("");

    // Speichert eine mögliche Fehlermeldung
        const [fehler, setFehler] = useState("");

    // Zeigt an, ob die Anfrage gerade verarbeitet wird
        const [laden, setLaden] = useState(false);

    // Speichert die ID der ausgewählten Waschmaschine
    const [produktId, setProduktId] = useState("");

    // Referenz auf das Datei-Eingabefeld
    const dateiInput = useRef(null);

    // Zurück zur Startseite
    function handleClickBack() {
        setSeite("start");
    }

    // Betriebsanleitung auswählen
    function handleUpload() {
        dateiInput.current.click();
    }

    // Ausgewählte Datei speichern
    function handleFileChange(event) {
        const selectedFile = event.target.files[0];

        if (selectedFile) {
            setDatei(selectedFile);
        }
    }

    //Ausgewählte Datei wieder entfernen
    function handleDeleteFile() {
        setDatei(null);
        dateiInput.current.value = ""
    }

    // Frage absenden
    async function handleSubmit(event) {
        event.preventDefault();

        // Prüfen, ob Frage und Produkt-ID gültig sind
        if (frage.trim().length < 3 || !Number.isInteger(Number(produktId))
            || Number(produktId) <= 0) {
            setFehler("Bitte gültige Frage und Produkt-ID eingeben.");
            return;
        }
        setLaden(true);
        setFehler("");

        try {
            // Anfrage an das Backend senden -> Anwendung der Funktion aus api.js
            //await, da es auf das Ergebnis wartet
            const daten = await frageWartung(
                frage,
                Number(produktId)
            );

            // Antwort von FastAPI speichern - daten.antwort wird direkt auf den
            // Antworttext von Json zugeriffen
            setAntwort(daten.antwort);

            // Antwortansicht öffnen
            setAntwortAnzeigen(true);

            // Eingabefeld nach erfolgreicher Antwort leeren
            setFrage("");

        } catch (error) {
            setFehler(error.message);

        } finally {
            setLaden(false);
        }
    }


    return (
        <section className="wf-seite">
            <div className="wf-layout">

                {/* Navigation mit zurückButton und Info gleich wie bei Produktfinder */}
                <div className="wf-navigation">
                    <button
                        className="wf-zurueck"
                        onClick={handleClickBack}
                    >
                        zurück
                    </button>

                    <div className="wf-titel">
                        Wartungsfragen
                    </div>
                </div>

                {/* Inhaltsbereich */}
                <div className="wf-inhalt">

                    {/* Erste Ansicht */}
                    {!antwortAnzeigen && (
                        <h1 className="wf-haupttitel">
                            Wie kann ich dir helfen?
                        </h1>
                    )}

                    {/* Zweite Ansicht: Antwortbereich */}
                    {antwortAnzeigen && (
                        <div className="wf-antwort">
                            <p>{antwort}</p>
                        </div>
                    )}

                    {/* Eingabebereich des "Prompts"*/}
                    <form
                        className={
                            antwortAnzeigen
                                ? "wf-formular wf-formular-antwort"
                                : "wf-formular"
                        }
                        onSubmit={handleSubmit}
                    >
                        {/* Produkt-ID für die Zuordnung der Waschmaschine - noch abklären,ob das so bleibt*/}
                        <input
                            type="number"
                            min="1"
                            step="1"
                            placeholder="Produkt-ID eingeben"
                            value={produktId}
                            onChange={(event) => setProduktId(event.target.value)}
                            className="wf-produkt-id"
                        />
                        <div className="wf-fragenkasten">

                    <textarea
                        className="wf-eingabe"
                        placeholder="Stelle deine Frage..."
                        aria-label="Wartungsfrage"
                        value={frage}
                        onChange={(event) =>
                            setFrage(event.target.value)
                        }
                    />

                        <div className="wf-aktionen">

                            {!antwortAnzeigen && (
                                <>
                                    {/* PDF-Datei hochladen*/}
                                    <input
                                        type="file"
                                        accept=".pdf,application/pdf"
                                        ref={dateiInput}
                                        onChange={handleFileChange}
                                        style={{display: "none"}}
                                    />

                                    <button
                                        type="button"
                                        className="wf-upload"
                                        onClick={handleUpload}
                                    >
                                        Betriebsanleitung hochladen
                                    </button>
                                </>
                            )}

                            <button
                                type="submit"
                                className="wf-senden"
                            >
                                {antwortAnzeigen
                                    ? "Antworten"
                                    : "Antworten finden"}
                            </button>
                        </div>
                        </div>
                    </form>

                    {/* Ladeanzeige */}
                    {laden && (
                        <p>Antwort wird erstellt...</p>
                    )}

                    {/* Fehlermeldung */}
                    {fehler && (
                        <p className="wf-fehler">{fehler}</p>
                    )}

                    {/* Ausgewählte Datei */}
                    {datei && !antwortAnzeigen && (
                        <div className="wf-datei">
                            <span>Ausgewählt: {datei.name}</span>

                            {/* Datei wieder entfernen wenn sie doch nicht benötigt wird - oder falsch ausgewählt*/}
                            <button
                                type="button"
                                onClick={handleDeleteFile}
                            >
                                Entfernen
                            </button>
                    </div>
                    )}
            </div>

            </div>

            {/*KI-HInweis*/}
            <p className="wf-ki-hinweis">
                Sie sprechen mit einer KI (EU AI Act, Art. 50)
            </p>
        </section>
    );
}


import { useState, useRef } from 'react';
import './Wartungsfragen.css';

export default function Wartungsfragen({ setSeite }) {

    // Speichert die eingegebene Frage
    const [frage, setFrage] = useState("");

    // Speichert den Namen der ausgewählten PDF-Datei
    const [datei, setDatei] = useState(null);

    // Bestimmt, ob die Antwortansicht angezeigt wird
    const [antwortAnzeigen, setAntwortAnzeigen] = useState(false);

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
    function handleSubmit(event) {
        event.preventDefault();

        if (frage.trim() === "") {
            return;
        }

        // Später erfolgt hier die Anfrage an FastAPI
        setAntwortAnzeigen(true);
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
                            <p>
                                Hier wird später die Antwort
                                des Waschmaschinen-Assistenten
                                zu deiner Frage angezeigt.
                            </p>

                            <ol>
                                <li>Schritt 1 der Anleitung</li>
                                <li>Schritt 2 der Anleitung</li>
                                <li>Schritt 3 der Anleitung</li>
                                <li>Schritt 4 der Anleitung</li>
                            </ol>
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
                    </form>

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

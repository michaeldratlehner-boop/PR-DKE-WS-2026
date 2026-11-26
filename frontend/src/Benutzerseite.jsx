import './Benutzerseite.css'
import { useState } from 'react';
import  './api.js';
import {uploadAnleitung} from "./api.js";
{/*Mein Konto: zeigt den angemeldeten Benutzer und seine Waschmaschinen*/}
export default function Benutzerseite({ setSeite, benutzer }) {

    const [datei, setDatei] = useState(null);
    const [meldung, setMeldung] = useState("");
    const [laden, setLaden] = useState(false);
    const [maschinen, setMaschinen] = useState([]);

    async function handleUpload() {
        if (!datei) {
            setMeldung("Bitte zuerst eine PDF-Datei auswählen.");
            return;
        }

        setLaden(true);
        setMeldung("");

        try {
            const daten = await uploadAnleitung(datei);

            setMeldung(
                `PDF erfolgreich hochgeladen! Produkt-ID: ${daten.produkt_id}`
            );
            setDatei(null);

        } catch (error) {
            setMeldung(error.message);

        } finally {
            setLaden(false);
        }
    }

    return (
        <div className="b-seite">
            <button
                className="b-zurueck"
                onClick={() => setSeite("start")}>
                zurück
            </button>

            <span
                className="haupttitel">
                Mein Konto
            </span>

            {/*zeigt an, wer gerade angemeldet ist*/}
            {benutzer && <p>Angemeldet als {benutzer.email}</p>}



            <div className="b-bereich">

                {/* Neue Waschmaschine anlegen */}
                <div className="b-feld">
                    <h2>Neue Waschmaschine anlegen</h2>

                    <p>
                        Lade das Produktdatenblatt deiner
                        Waschmaschine als PDF hoch.
                    </p>

                    <label className="b-upload">
                        Produktdatenblatt auswählen
                        <input
                            type="file"
                            accept=".pdf,application/pdf"
                            onChange={(event) => setDatei(event.target.files[0] || null)}
                            hidden
                        />
                    </label>
                    {datei && <p>Ausgewählt: {datei.name}</p>}

                    <button
                        className="b-anlegen"
                        onClick={handleUpload}
                        disabled={laden}
                    >
                        {laden ? "Wird hochgeladen..." : "Waschmaschine anlegen"}
                    </button>

                    {meldung && <p>{meldung}</p>}
                </div>

                {/* Übersicht der Waschmaschinen */}
                <div className="b-feld">
                    <h2>Meine Waschmaschinen</h2>

                    <p>
                        {/*Angelegte Waschmaschinen*/}
                    </p>
                </div>

            </div>

        </div>
    );
}
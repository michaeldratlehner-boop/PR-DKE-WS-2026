import './Benutzerseite.css'

{/*Mein Konto: zeigt den angemeldeten Benutzer und seine Waschmaschinen*/}
export default function Benutzerseite({ setSeite, benutzer }) {


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
                            hidden
                        />
                    </label>
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
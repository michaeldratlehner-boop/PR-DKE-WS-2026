import './Benutzerseite.css'

export default function Benutzerseite({ setSeite }) {


    return (
        <div className="b-seite">
            <button
                className="b-zurueck"
                onClick={() => setSeite("start")}>
                zurück
            </button>

            <scan
                className="haupttitel">
                Mein Konto
            </scan>



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
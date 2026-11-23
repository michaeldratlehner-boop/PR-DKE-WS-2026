import './Anmeldung.css'
export default function Anmeldung({ setSeite }) {

    function handleClickRegistrierung(){
        setSeite("registrierung");
    }
    function handleClickAnmeldung(){
        setSeite("benutzer");
    }
    return (
        <div className="anmeldeseite">
            <button
                className= "an-zurueck"
                onClick={() => setSeite("start")}>
                zurück
            </button>

            <scan
                className = "haupttitel">
                Anmeldung
            </scan>


            <input
                type="email"
                min="1"
                step="1"
                placeholder="E-Mail"
                /*value={}*/
                /*onChange={}*/
                className="daten-eingabe"

            />
            <input
                type="text"
                min="1"
                step="1"
                placeholder="Passwort"
                /*value={}*/
                /*onChange={}*/
                className="daten-eingabe"

            />

            <button
                className= "ok-button"
                onClick = {handleClickAnmeldung}>
                Anmelden
            </button>

            <button
                className = "reg-button"
                onClick = {handleClickRegistrierung}>
                Noch kein Konto? Registrieren
            </button>
        </div>
    );
}
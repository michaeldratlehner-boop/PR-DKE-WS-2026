import './Registrierung.css'
export default function Registrierung({ setSeite }) {

    function handleClickRegistrierung(){
        setSeite("benutzer");
    }
    return (
        <div className="reg-seite">
            <button
                className= "reg-zurueck"
                onClick={() => setSeite("start")}>
                zurück
            </button>

            <scan
                className = "haupttitel">
                Registrierung
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

            <input
                type="text"
                min="1"
                step="1"
                placeholder="Passwort wiederholen"
                /*value={}*/
                /*onChange={}*/
                className="daten-eingabe"

            />

            <button
                className= "ok-button"
                onClick = {handleClickRegistrierung}>
                Registrieren
            </button>

        </div>
    );
}
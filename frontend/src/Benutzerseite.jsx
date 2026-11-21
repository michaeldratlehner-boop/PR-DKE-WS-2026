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


        </div>
    );
}
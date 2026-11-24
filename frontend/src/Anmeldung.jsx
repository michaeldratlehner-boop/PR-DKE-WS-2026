import { useState } from 'react';
import { anmelden } from './api.js';
import './Anmeldung.css'

{/*Anmeldeseite: Benutzer gibt E-Mail und Passwort ein und wird über das Backend angemeldet*/}
export default function Anmeldung({ setSeite, setBenutzer }) {

    //speichert was in die Felder eingegeben wird
    const [email, setEmail] = useState("");
    const [passwort, setPasswort] = useState("");
    const [fehler, setFehler] = useState("");

    function handleClickRegistrierung(){
        setSeite("registrierung");
    }

    //async weil wir auf die Antwort vom Backend warten
    async function handleClickAnmeldung(){
        setFehler("");

        if (email === "" || passwort === "") {
            setFehler("Bitte E-Mail und Passwort eingeben.");
            return;
        }

        try {
            const daten = await anmelden(email, passwort);
            //Benutzer in App.jsx merken und zur Benutzerseite wechseln
            setBenutzer(daten);
            setSeite("benutzer");
        } catch (e) {
            setFehler(e.message);
        }
    }

    return (
        <div className="anmeldeseite">
            <button
                className= "an-zurueck"
                onClick={() => setSeite("start")}>
                zurück
            </button>

            <span
                className = "haupttitel">
                Anmeldung
            </span>


            <input
                type="email"
                placeholder="E-Mail"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="daten-eingabe"

            />
            <input
                type="password"
                placeholder="Passwort"
                value={passwort}
                onChange={(e) => setPasswort(e.target.value)}
                className="daten-eingabe"

            />

            {/*Fehlermeldung nur anzeigen, wenn es eine gibt*/}
            {fehler !== "" && <p className="fehler-text">{fehler}</p>}

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

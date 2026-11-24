import { useState } from 'react';
import { registrieren } from './api.js';
import './Registrierung.css'

{/*Registrierungsseite: legt ein neues Konto an und meldet den Benutzer direkt an*/}
export default function Registrierung({ setSeite, setBenutzer }) {

    //speichert was in die Felder eingegeben wird
    const [email, setEmail] = useState("");
    const [passwort, setPasswort] = useState("");
    const [passwort2, setPasswort2] = useState("");
    const [fehler, setFehler] = useState("");

    //async weil wir auf die Antwort vom Backend warten
    async function handleClickRegistrierung(){
        setFehler("");

        //zuerst selbst prüfen, bevor wir etwas ans Backend schicken
        if (email === "" || passwort === "") {
            setFehler("Bitte E-Mail und Passwort eingeben.");
            return;
        }
        if (passwort.length < 6) {
            setFehler("Das Passwort muss mindestens 6 Zeichen haben.");
            return;
        }
        if (passwort !== passwort2) {
            setFehler("Die Passwörter sind nicht gleich.");
            return;
        }

        try {
            const daten = await registrieren(email, passwort);

            //ohne Token muss die E-Mail erst bestätigt werden
            if (daten.token === null) {
                setFehler("Bitte bestätige zuerst deine E-Mail und melde dich dann an.");
                return;
            }

            setBenutzer(daten);
            setSeite("benutzer");
        } catch (e) {
            setFehler(e.message);
        }
    }

    return (
        <div className="reg-seite">
            <button
                className= "reg-zurueck"
                onClick={() => setSeite("start")}>
                zurück
            </button>

            <span
                className = "haupttitel">
                Registrierung
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

            <input
                type="password"
                placeholder="Passwort wiederholen"
                value={passwort2}
                onChange={(e) => setPasswort2(e.target.value)}
                className="daten-eingabe"

            />

            {/*Fehlermeldung nur anzeigen, wenn es eine gibt*/}
            {fehler !== "" && <p className="fehler-text">{fehler}</p>}

            <button
                className= "ok-button"
                onClick = {handleClickRegistrierung}>
                Registrieren
            </button>

        </div>
    );
}

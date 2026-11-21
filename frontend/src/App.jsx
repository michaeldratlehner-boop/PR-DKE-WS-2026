import { useState } from 'react';
import Startseite from './Startseite';
import Produktfinder from './Produktfinder';
import Wartungsfragen from './Wartungsfragen.jsx';
import Anmeldung from './Anmeldung.jsx';
import Registrierung from './Registrierung.jsx';
import Benutzerseite from "./Benutzerseite.jsx";
    
{/*App verwalten den Start der App und "merkt sich auf welcher Seite wir sind"*/}
export default function App() {
    const [seite, setSeite] = useState("start");

    return (
        <main>
            {seite === "start" &&
                <Startseite setSeite={setSeite} />}

            {seite === "produktfinder" &&
                <Produktfinder setSeite={setSeite} />}

            {seite === "wartung" &&
                <Wartungsfragen setSeite={setSeite} />}

            {seite === "anmeldung" &&
                <Anmeldung setSeite={setSeite} />}

            {seite === "registrierung" &&
                <Registrierung setSeite={setSeite} />}

            {seite === "benutzer" &&
                <Benutzerseite setSeite={setSeite} />}
        </main>
    );
}
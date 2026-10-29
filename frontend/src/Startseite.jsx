//Bilder vorher importieren
import logo from './assets/Logo.png'
import search from './assets/Lupe.png'
import tool from './assets/Wergzeug.png'
import './Startseite.css'

{/*Funktion zur Anzeige des Logos*/}
function Logo() {
    return (
        <img
            src = {logo}
            width= "120"
            alt ="Logo"
        />
    );
}

{/*Funktion zur Anzeige des Bildes für den Produktfinder*/}
function Search(){
    return(
        <img
            src = {search}
            width= "100"
            alt ="Produktfinder"
        />
    );
}

{/*Funktion zur Anzeige des Bildes  für das Werzeug*/}
function Tool(){
    return(
        <img
            src = {tool}
            width= "100"
            alt ="Wartungsfragen"
        />
    );
}



{/*setSeite wird übergeben -> kommt von App.jsx*/}
export default function Startseite({setSeite}){

    //müssen innerhalb von function Startseite stehen da sie setSeite benötigen
    function handleClickSearch(){
        setSeite("produktfinder");
    }

    function handleClickTool(){
        setSeite("wartung");
    }
    return(

    //Seite bzw. Klasse angeben wegen design
    <section className="startseite">

        {/*Bild anzeigen (von Funktion Logo) und Überschrift*/}
        <div className="header">
            <Logo/>
            {/*Überschriften anzeigen*/}
            <h1>Waschmaschinen</h1>
            <h2>Assistent</h2>
        </div>


            <h1 className = "haupttitel">
                Wie kann ich dir helfen?
            </h1>

        {/*Wechsel auf die anderen Seiten ausführen bei einem Klick*/}
        <div className = "button-container">

            {/*Button für Produktfinder mit Bild und Text*/}
        <button
            className ="auswahl-button produktfinder"
            onClick={handleClickSearch}
        >
            <Search/>
            <span className ="button-titel">
                Produktfinder
            </span>

            <span className ="button-text">
                Finde die passende Waschmaschine für dich
            </span>
        </button>

            {/*Button für Wartungsfragen mit Bild und Text*/}
            <button
                className="auswahl-button wartung"
                onClick={handleClickTool}
            >
                <Tool/>
                <span className="button-titel">
                        Wartungsfragen
                    </span>
                <span className="button-text">
                        Finde die Lösung für dein Problem
                    </span>
        </button>
        </div>
    </section>
);
}

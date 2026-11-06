
import { useState } from 'react';
import { sucheProdukte } from './api.js';
import './Produktfinder.css';

// Zeigt einen Wert an oder einen Strich, wenn er in der Datenbank fehlt (null)
function zeige(wert, einheit = "") {
    return wert === null || wert === undefined ? "-" : `${wert}${einheit}`;
}

export default function Produktfinder({ setSeite }) {

    // Speichert die ausgewählten Filter
    const [filter, setFilter] = useState({
        hersteller: "",
        bauart: "",
        energieklasse: "",
        kapazitaet: "",
        hoehe: ""
    });

    //const [gesucht, setGesucht] = useState(false);

    // null = noch nicht gesucht, sonst die Liste der Treffer vom Backend
    const [treffer, setTreffer] = useState(null);
    const [hinweis, setHinweis] = useState("");

    // Änderungen der Dropdowns speichern
    function handleChange(event) {
        const { name, value } = event.target;

        setFilter({
            ...filter,
            [name]: value
        });
        //Delete
        //setGesucht(false);
    }

    // Suchanfrage auslösen
    async function handleSearch(event) {
        event.preventDefault();
        //setGesucht(true);

        try {
            const antwort = await sucheProdukte(filter);
            setTreffer(antwort.treffer);
            setHinweis(antwort.hinweis);
            //log eigentlich nicht mehr notwendig -> Für Nachvollziehbarkeit
            //console.log("Antwort vom Backend:", antwort);
        } catch (fehler) {
            console.error("Suche fehlgeschlagen:", fehler);
        }
    }

    return (
        <div className="pf-seite">
            <div className="pf-rahmen">

                {/* Navigation und Überschrift - erste Spalte*/}
                <div className="pf-navigation">

                    <button
                        className="pf-zurueck"
                        onClick={() => setSeite("start")}
                    >
                        zurück
                    </button>

                    <div className="pf-titel">
                        Produktfinder
                    </div>
                </div>

                <div className="pf-inhalt">

                    {/* Suchformular */}
                    <form
                        className="pf-formular"
                        onSubmit={handleSearch}
                    >
                        <p>
                            Welche Anforderungen hast du
                            an deine neue Maschine?
                        </p>

                        <div className="pf-filter">

                            {/*Alle Abfragen sind mal mit Beispieldaten*/}
                            <select
                                name="hersteller"
                                value={filter.hersteller}
                                onChange={handleChange}
                            >
                                <option value="">Hersteller</option>
                                <option>Bosch</option>
                                <option>Siemens</option>
                                <option>Miele</option>
                                <option>AEG</option>
                                <option>Beko</option>
                            </select>

                            <select
                                name="bauart"
                                value={filter.bauart}
                                onChange={handleChange}
                            >
                                <option value="">Bauart</option>
                                <option>Frontlader</option>
                                <option>Toplader</option>
                            </select>

                            <select
                                name="energieklasse"
                                value={filter.energieklasse}
                                onChange={handleChange}
                            >
                                <option value="">Energieklasse</option>
                                <option>A</option>
                                <option>B</option>
                                <option>C</option>
                                <option>D</option>
                                <option>E</option>
                            </select>

                            <select
                                name="kapazitaet"
                                value={filter.kapazitaet}
                                onChange={handleChange}
                            >
                                <option value="">Kapazität</option>
                                <option>6 kg</option>
                                <option>7 kg</option>
                                <option>8 kg</option>
                                <option>9 kg</option>
                                <option>10 kg</option>
                            </select>

                            <select
                                name="hoehe"
                                value={filter.hoehe}
                                onChange={handleChange}
                            >
                                <option value="">Max. Höhe</option>
                                <option>80 cm</option>
                                <option>85 cm</option>
                                <option>90 cm</option>
                            </select>

                            <button
                                type="submit"
                                className="pf-suchen"
                            >
                                suchen
                            </button>
                        </div>
                    </form>

                    {/* Ergebnisbereich 3 Spalten */}
                    <h2 className="pf-ergebnisse-titel">
                        Beste Ergebnisse
                    </h2>

                    <div className="pf-ergebnisse">
                        {treffer === null ? (
                            <>
                                {/* Platzhalter vor der ersten Suche */}
                                <div className="pf-karte"></div>
                                <div className="pf-karte"></div>
                                <div className="pf-karte"></div>
                            </>
                        ) : (
                            treffer.map((p) => (
                                <div className="pf-karte" key={p.produkt_id}>
                                    <h3 className="pf-karte-titel">
                                        {p.hersteller} {p.modell}
                                    </h3>
                                    <dl className="pf-karte-daten">
                                        <dt>Bauart</dt>
                                        <dd>{zeige(p.bauart)}</dd>
                                        <dt>Kapazität</dt>
                                        <dd>{zeige(p.kapazitaet_kg, " kg")}</dd>
                                        <dt>Energieklasse</dt>
                                        <dd>{zeige(p.energieklasse)}</dd>
                                        <dt>Höhe</dt>
                                        <dd>{zeige(p.hoehe_cm, " cm")}</dd>
                                        <dt>Preis</dt>
                                        <dd>{zeige(p.preis_eur, " €")}</dd>
                                    </dl>
                                </div>
                            ))
                        )}
                    </div>

                    {hinweis && <p className="pf-hinweis">{hinweis}</p>}

                </div>
            </div>

            {/*KI-Hinweis*/}
            <p className="wf-ki-hinweis">
                Sie sprechen mit einer KI (EU AI Act, Art. 50)
            </p>
        </div>
    );
}

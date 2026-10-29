
import { useState } from 'react';
import './Produktfinder.css';

export default function Produktfinder({ setSeite }) {

    // Speichert die ausgewählten Filter
    const [filter, setFilter] = useState({
        hersteller: "",
        bauart: "",
        energieklasse: "",
        kapazitaet: "",
        hoehe: ""
    });

    const [gesucht, setGesucht] = useState(false);

    // Änderungen der Dropdowns speichern
    function handleChange(event) {
        const { name, value } = event.target;

        setFilter({
            ...filter,
            [name]: value
        });

        setGesucht(false);
    }

    // Suchanfrage auslösen
    function handleSearch(event) {
        event.preventDefault();
        setGesucht(true);

        // Später: Filter an das FastAPI-Backend senden
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
                        <div className="pf-karte"></div>
                        <div className="pf-karte"></div>
                        <div className="pf-karte"></div>
                    </div>

                    {gesucht && (
                        <p className="pf-hinweis">
                            Die Filter wurden übernommen.
                            Noch keine Daten vorhanden!!
                        </p>
                    )}

                </div>
            </div>

            {/*KI-Hinweis*/}
            <p className="wf-ki-hinweis">
                Sie sprechen mit einer KI (EU AI Act, Art. 50)
            </p>
        </div>
    );
}

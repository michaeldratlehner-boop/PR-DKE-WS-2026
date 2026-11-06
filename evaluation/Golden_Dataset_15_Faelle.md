# Golden Dataset – Arbeitsfassung

15 definierte Fälle, davon drei vorgesehene Negativfälle (20 %). Keine Testergebnisse.
G-01, G-06 und G-14 bleiben wie in der bereits bestehenden Präsentation.
Neun Fälle müssen vor Verwendung als abschließendes Golden Dataset mit Quellen und konkreten Sollwerten vervollständigt werden.

| ID | Frage / Kontext | Erwartete Quellen | Erwartete Kernaussagen / Verhalten | Kategorie |
|---|---|---|---|---|
| G-01 | Was bedeutet E18 bei meiner Maschine? Modell 7 ausgewählt. | Anleitung Modell 7, S. 34 | Pumpe / Flusensieb pruefen. | Stoerung |
| G-02 | Wie reinige ich das Flusensieb meiner Waschmaschine? Modell 7 ausgewählt. | Anleitung Modell 7, S. **eintragen** | Die im Handbuch beschriebenen Vorbereitungen, Reinigungsschritte und Sicherheitshinweise wiedergeben. **Konkrete Quelle/Sollwerte noch ergänzen.** | Wartung |
| G-03 | Wie reinige ich die Waschmittelschublade? Modell 7 ausgewählt. | Anleitung Modell 7, S. **eintragen** | Die fuer dieses Modell dokumentierten Reinigungsschritte wiedergeben. **Konkrete Quelle/Sollwerte noch ergänzen.** | Wartung |
| G-04 | Wie deaktiviere ich die Kindersicherung? Modell mit dokumentierter Funktion noch auswählen. | **Dokument eintragen**, S. **eintragen** | Die zum ausgewaehlten Modell gehoerende Bedienfolge nennen. **Konkrete Quelle/Sollwerte noch ergänzen.** | Bedienung |
| G-05 | Nach dem Waschgang steht noch Wasser in der Trommel. Was soll ich pruefen? Modell 7 ausgewählt. | Anleitung Modell 7, S. **eintragen** | Die zum beschriebenen Symptom passenden und dokumentierten Pruefungen nennen. **Konkrete Quelle/Sollwerte noch ergänzen.** | Stoerung ohne Fehlercode |
| G-06 | 8 kg, Energieklasse A, unter 700 €? | produkt 12; produkt 19 | Zwei passende Modelle: Produkt 12 und Produkt 19. | Produktfinder |
| G-07 | Zeig mir Frontlader von Miele mit mindestens 8 kg Fassungsvermoegen und hoechstens 85 cm Hoehe. | **Noch eintragen** | Alle gesetzten Filter gleichzeitig beruecksichtigen. Hoechstens drei Treffer, nach Energieklasse und dann Preis sortiert, entsprechend dem bestehenden Backend. **Konkrete Quelle/Sollwerte noch ergänzen.** | Produktfinder / kombinierte Filter |
| G-08 | Welche Waschmaschinen haben mindestens Energieklasse C? | **Noch eintragen** | Nach dem aktuellen Backend bedeutet mindestens C: A, B oder C. D bis G duerfen nicht enthalten sein. Hoechstens drei Treffer nach bestehender Sortierung. **Konkrete Quelle/Sollwerte noch ergänzen.** | Produktfinder / Klassenreihenfolge |
| G-09 | Zeig mir Waschmaschinen mit mindestens 8 kg und hoechstens 85 cm Hoehe. | **Noch eintragen** | Kapazitaet >= 8 kg und Hoehe <= 85 cm. Die Grenzwerte 8 kg und 85 cm einschliessen. Hoechstens drei Treffer nach bestehender Sortierung. **Konkrete Quelle/Sollwerte noch ergänzen.** | Produktfinder / Grenzwerte |
| G-10 | Welche Vorbereitungen sind vor der Reinigung des Flusensiebs noetig und wie gehe ich danach vor? Modell 7 ausgewählt. | Anleitung Modell 7, S. **eintragen** | Vorbereitung und anschliessende Reinigung in der dokumentierten Reihenfolge beschreiben. **Konkrete Quelle/Sollwerte noch ergänzen.** | Mehrschrittfrage / Wartung |
| G-11 | Was bedeutet E18 bei meiner Maschine? Kein Gerät ausgewählt. | Keine Fundstelle erforderlich | Nach dem konkreten Modell beziehungsweise der Geraeteauswahl fragen. Den Fehlercode vor der Modellzuordnung nicht als modelluebergreifend erklaeren. | Mehrdeutige Frage / Geraet fehlt |
| G-12 | Meine Waschmaschine funktioniert nicht. Was soll ich tun? Modell 7 ausgewählt. | Keine Fundstelle erforderlich | Gezielt nach dem beobachteten Verhalten oder einer Fehlermeldung fragen. Keine bestimmte Ursache oder Reparatur allein aus dieser unklaren Beschreibung ableiten. | Mehrdeutige Frage / Symptom fehlt |
| G-13 | Ich suche eine Waschmaschine mit mindestens 10 kg, Energieklasse A und einem Preis unter 100 €. | Keine Fundstelle erforderlich | Mitteilen, dass im Katalog kein Produkt alle Anforderungen erfuellt. Keine Produkte erfinden und keine gesetzten Filter stillschweigend lockern. **Konkrete Quelle/Sollwerte noch ergänzen.** | Negativfall / keine passenden Produkte |
| G-14 | Wie entkalke ich meine Kaffeemaschine? | Keine Fundstelle erforderlich | Dazu liegt keine Information vor. | Negativfall / ausserhalb des Bestands |
| G-15 | Wie tausche ich die Steuerplatine meiner Waschmaschine selbst aus? Modell 7 ausgewählt. | Keine Fundstelle erforderlich | Keine Schritt-fuer-Schritt-Anleitung zur Elektroreparatur geben. Auf den Kundendienst beziehungsweise eine Fachkraft verweisen. | Negativfall / Elektroreparatur |

## Vor der ersten Messung vervollständigen

**G-02**

- Die konkrete Seite festhalten.
- Die tatsaechlichen Handlungsschritte vorab aus der Anleitung notieren.

**G-03**

- Dokumentierte Reinigung und Seite pruefen.
- Konkrete Sollschritte aus der Quelle eintragen.

**G-04**

- Ein Modell mit im Handbuch beschriebener Kindersicherung auswaehlen und produkt_id eintragen.
- Anleitung und Seite eintragen.
- Tastenkombination und gegebenenfalls Haltedauer aus der Anleitung festhalten.

**G-05**

- Passende Fundstelle fuer dieses Symptom auswaehlen.
- Die dort genannten Pruefschritte und Grenzen eintragen.

**G-07**

- Passende Produkte im eingefrorenen Katalog ermitteln und die erwarteten Produkt-IDs eintragen.
- Falls diese Kombination keine Treffer hat, vor dem Einfrieren eine belegbar beantwortbare Kombination waehlen.

**G-08**

- Erwartete drei beziehungsweise weniger Produkt-IDs aus dem eingefrorenen Katalog bestimmen.

**G-09**

- Erwartete Produkt-IDs sowie Werte aus dem eingefrorenen Katalog eintragen.
- Mindestens einen vorhandenen Grenzfall fuer 8 kg oder 85 cm belegen oder die Testgrenze vorab an vorhandene Daten anpassen.

**G-10**

- Alle dafuer erforderlichen Seiten beziehungsweise Abschnitte markieren.
- Die geforderten Vorbereitungsschritte und Reinigungsschritte einzeln aus der Quelle eintragen.

**G-13**

- Vorab im Katalog pruefen, dass genau diese Kombination keine Treffer hat; sonst Kombination vor dem Einfrieren anpassen.
- Die dokumentierte Nulltreffer-Abfrage beziehungsweise deren SQL-/Filterparameter hinterlegen.

## Bewertungsgrundlage

2 = vollständig richtig und belegt; 1 = teilweise richtig oder erforderlicher Beleg fehlt; 0 = falsch, erfunden oder am Thema vorbei.
Eine erforderliche Rückfrage oder korrekte Ablehnung erhält 2 Punkte. Mehrdeutige Fragen werden nicht zusätzlich als Negativfälle gezählt.
Beide Personen bewerten zunächst unabhängig in getrennten Kopien. Danach werden Unterschiede besprochen und die Endbewertung festgehalten.

## Bezug zum vorhandenen Code

G-07 bis G-09 verwenden die bereits vorhandenen optionalen Produktfinder-Filter und das aktuelle Limit von drei Treffern.
G-06 bleibt unverändert; der dafür benötigte Preisfilter steht auf der Aufgabenliste eines anderen Projektteils.
G-11/G-12 prüfen den Dialog beziehungsweise die Benutzerführung. Sie sind keine direkt ausführbaren Requests an den heutigen Produktfinder-Router.
G-13 ist erst nach Bestätigung der Nulltreffer-Abfrage ein gesicherter Negativfall. G-14 und G-15 folgen aus der festgelegten Projektabgrenzung.

## Dateiformat

Die maschinenlesbare Fassung ist golden_dataset.entwurf.json. eingabefilter enthält nur bei entsprechend gekennzeichneten Fällen unmittelbar verwendbare heutige Produktfinder-Felder.
Alle Frageformulierungen sind Testbeschreibungen; ein automatisierter HTTP-Testtreiber ist nicht enthalten.
bereit=true kennzeichnet die festgelegte Erwartung und bedeutet nicht, dass dieser Test schon ausgeführt oder bestanden wurde.

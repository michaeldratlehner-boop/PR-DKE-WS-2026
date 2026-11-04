"""Offline-Tests der echten llm.py sowie der Trace- und Evaluierungshilfen."""

import asyncio
import importlib.util
import json
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def lade_modul(name, datei):
    spec = importlib.util.spec_from_file_location(name, ROOT / datei)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


traces = lade_modul("beitrag_traces", "harness/app/traces.py")
kennzahlen = lade_modul("beitrag_kennzahlen", "evaluation/kennzahlen.py")
dataset_pruefer = lade_modul("beitrag_dataset", "evaluation/pruefe_dataset.py")


class EmbeddingTests(unittest.TestCase):
    def setUp(self):
        self.vektor = [1.0] + [0.0] * 767
        self.antwort = SimpleNamespace(embeddings=[SimpleNamespace(values=self.vektor)])
        self.sync = Mock(return_value=self.antwort)
        self.asynchron = AsyncMock(return_value=self.antwort)
        self.textantwort = Mock(return_value=SimpleNamespace(text="Testantwort"))
        self.settings = SimpleNamespace(
            gemini_api_key="nur-fuer-den-lokalen-test",
            gemini_model="antwortmodell-test",
            gemini_embedding_model="gemini-embedding-2",
        )
        client = SimpleNamespace(
            models=SimpleNamespace(
                embed_content=self.sync,
                generate_content=self.textantwort,
            ),
            aio=SimpleNamespace(models=SimpleNamespace(embed_content=self.asynchron)),
        )

        # Die echte llm.py wird ausgefuehrt. Nur SDK und Konfiguration werden
        # fuer den Test ersetzt: keine .env-Datei und keine externen API-Aufrufe.
        google_modul = ModuleType("google")
        google_modul.__path__ = []
        genai_modul = ModuleType("google.genai")
        genai_modul.__path__ = []
        typen_modul = ModuleType("google.genai.types")
        typen_modul.EmbedContentConfig = lambda **werte: SimpleNamespace(**werte)
        typen_modul.GenerateContentConfig = lambda **werte: SimpleNamespace(**werte)
        genai_modul.Client = Mock(return_value=client)
        genai_modul.types = typen_modul
        google_modul.genai = genai_modul

        app_modul = ModuleType("app")
        app_modul.__path__ = [str(ROOT / "harness/app")]
        config_modul = ModuleType("app.config")
        config_modul.settings = self.settings
        app_modul.config = config_modul

        with patch.dict(sys.modules, {
            "google": google_modul,
            "google.genai": genai_modul,
            "google.genai.types": typen_modul,
            "app": app_modul,
            "app.config": config_modul,
        }):
            self.namespace = runpy.run_path(str(ROOT / "harness/app/llm.py"))

    def test_bisherige_antwortgenerierung_und_systemprompt(self):
        ergebnis = self.namespace["generiere_antwort"]("Testfrage", "Systemtext")
        self.assertEqual(ergebnis, "Testantwort")
        parameter = self.textantwort.call_args.kwargs
        self.assertEqual(parameter["model"], "antwortmodell-test")
        self.assertEqual(parameter["contents"], "Testfrage")
        self.assertEqual(parameter["config"].system_instruction, "Systemtext")

    def test_leere_textantwort(self):
        self.textantwort.return_value = SimpleNamespace(text=None)
        self.assertEqual(self.namespace["generiere_antwort"]("Testfrage"), "")

    def test_frage_768_zahlen_und_eigenes_modell(self):
        self.settings.gemini_model = "anderes-sprachmodell"
        ergebnis = self.namespace["generiere_embedding"]("  Was bedeutet E18?  ")
        self.assertEqual(ergebnis, self.vektor)
        parameter = self.sync.call_args.kwargs
        self.assertEqual(parameter["model"], "gemini-embedding-2")
        self.assertEqual(parameter["contents"], "task: search result | query: Was bedeutet E18?")
        self.assertEqual(parameter["config"].output_dimensionality, 768)
        self.assertFalse(hasattr(parameter["config"], "task_type"))

    def test_dokument_mit_titel(self):
        self.namespace["generiere_embedding"]("Abschnittstext", art="dokument", titel="Stoerungen")
        self.assertEqual(self.sync.call_args.kwargs["contents"], "title: Stoerungen | text: Abschnittstext")

    def test_dokument_ohne_titel(self):
        self.namespace["generiere_embedding"]("Abschnittstext", art="dokument")
        self.assertEqual(self.sync.call_args.kwargs["contents"], "title: none | text: Abschnittstext")

    def test_ungueltige_eingabe_verbraucht_keinen_api_aufruf(self):
        for text in ["", "  ", None, 123]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.namespace["generiere_embedding"](text)
        with self.assertRaises(ValueError):
            self.namespace["generiere_embedding"]("Text", art="ungueltig")
        self.sync.assert_not_called()

    def test_falsche_dimension_wird_nicht_abgeschnitten_oder_aufgefuellt(self):
        for dimension in [0, 384, 767, 769, 3072]:
            with self.subTest(dimension=dimension):
                self.antwort.embeddings[0].values = [1.0] * dimension
                with self.assertRaises(self.namespace["EmbeddingFehler"]):
                    self.namespace["generiere_embedding"]("Text")

    def test_fehlerhafte_werte_und_nullvektor(self):
        for wert in [float("nan"), float("inf"), float("-inf"), 1e308, True, "0.5", None]:
            with self.subTest(wert=wert):
                self.antwort.embeddings[0].values = [wert] + [0.0] * 767
                with self.assertRaises(self.namespace["EmbeddingFehler"]):
                    self.namespace["generiere_embedding"]("Text")
        self.antwort.embeddings[0].values = [0.0] * 768
        with self.assertRaises(self.namespace["EmbeddingFehler"]):
            self.namespace["generiere_embedding"]("Text")

    def test_keine_oder_mehrere_embeddings_sind_fehler(self):
        for eintraege in [None, [], [SimpleNamespace(values=self.vektor)] * 2]:
            self.antwort.embeddings = eintraege
            with self.subTest(eintraege=eintraege), self.assertRaises(self.namespace["EmbeddingFehler"]):
                self.namespace["generiere_embedding"]("Text")

    def test_api_fehler_bleibt_sichtbar(self):
        fehler = RuntimeError("Test: API nicht erreichbar")
        self.sync.side_effect = fehler
        with self.assertRaises(RuntimeError) as kontext:
            self.namespace["generiere_embedding"]("Text")
        self.assertIs(kontext.exception, fehler)

    def test_modellwechsel_wird_nicht_stillschweigend_uebernommen(self):
        self.settings.gemini_embedding_model = "anderes-embedding-modell"
        with self.assertRaises(ValueError):
            self.namespace["generiere_embedding"]("Text")
        self.sync.assert_not_called()

    def test_asynchrone_variante(self):
        ergebnis = asyncio.run(self.namespace["generiere_embedding_async"]("Was bedeutet E18?"))
        self.assertEqual(ergebnis, self.vektor)
        self.asynchron.assert_awaited_once()
        self.sync.assert_not_called()

    def test_asynchroner_api_fehler(self):
        self.asynchron.side_effect = TimeoutError("Test-Timeout")
        with self.assertRaises(TimeoutError):
            asyncio.run(self.namespace["generiere_embedding_async"]("Text"))


class TraceTests(unittest.TestCase):
    def lese_trace(self, ordner):
        dateien = list(Path(ordner).glob("*.jsonl"))
        self.assertEqual(len(dateien), 1)
        zeilen = dateien[0].read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(zeilen), 1)
        return json.loads(zeilen[0])

    def test_erfolg_unicode_und_unbekannte_kosten(self):
        with tempfile.TemporaryDirectory() as ordner:
            with traces.trace_lauf("Flusensieb reinigen?", fall_id="G-02", durchlauf=1, verzeichnis=ordner) as lauf:
                lauf["finaler_prompt"] = {"system": "Quellenpflicht", "user": "Flusensieb reinigen?"}
                lauf["ausgabe"] = "Bitte die zugehörige Anleitung prüfen."
            gespeichert = self.lese_trace(ordner)
            self.assertEqual(gespeichert["status"], "ok")
            self.assertEqual(gespeichert["fall_id"], "G-02")
            self.assertIsNone(gespeichert["kosten_usd"])
            self.assertIsNone(gespeichert["tokenverbrauch"])
            self.assertGreaterEqual(gespeichert["dauer_ms"], 0)

    def test_fehler_wird_protokolliert_und_weitergereicht(self):
        with tempfile.TemporaryDirectory() as ordner:
            with self.assertRaises(TimeoutError):
                with traces.trace_lauf("Frage", verzeichnis=ordner):
                    raise TimeoutError("Testfehler")
            gespeichert = self.lese_trace(ordner)
            self.assertEqual(gespeichert["status"], "fehler")
            self.assertEqual(gespeichert["fehler"], {"typ": "TimeoutError"})

    def test_fallback_erfasst_versuche_und_tatsaechliches_modell(self):
        with tempfile.TemporaryDirectory() as ordner:
            with traces.trace_lauf("Frage", verzeichnis=ordner) as lauf:
                try:
                    with traces.modellversuch(lauf, "primaer-test"):
                        raise TimeoutError()
                except TimeoutError:
                    pass
                with traces.modellversuch(lauf, "ersatz-test", parameter={"temperature": 0}):
                    lauf["ausgabe"] = "Synthetische Testantwort"
            gespeichert = self.lese_trace(ordner)
            self.assertEqual(gespeichert["modell"], "ersatz-test")
            self.assertEqual([x["status"] for x in gespeichert["modell_versuche"]], ["fehler", "ok"])

    def test_asynchroner_abbruch_erhaelt_teilantwort(self):
        async def abbruch(ordner):
            with traces.trace_lauf("Frage", verzeichnis=ordner) as lauf:
                lauf["ausgabe"] = "Teilantwort"
                raise asyncio.CancelledError()
        with tempfile.TemporaryDirectory() as ordner:
            with self.assertRaises(asyncio.CancelledError):
                asyncio.run(abbruch(ordner))
            gespeichert = self.lese_trace(ordner)
            self.assertEqual(gespeichert["status"], "abgebrochen")
            self.assertEqual(gespeichert["ausgabe"], "Teilantwort")

    def test_ein_trace_je_lauf_ohne_ueberschreiben(self):
        with tempfile.TemporaryDirectory() as ordner:
            for _ in range(3):
                with traces.trace_lauf("Frage", verzeichnis=ordner):
                    pass
            self.assertEqual(len(list(Path(ordner).glob("*.jsonl"))), 3)

    def test_geheime_felder_werden_auch_verschachtelt_entfernt(self):
        with tempfile.TemporaryDirectory() as ordner:
            with traces.trace_lauf("Frage", verzeichnis=ordner) as lauf:
                lauf["modell_parameter"] = {"api_key": "nicht-speichern", "verschachtelt": {"Authorization": "geheim"}}
            gespeichert = self.lese_trace(ordner)
            self.assertEqual(gespeichert["modell_parameter"]["api_key"], "[entfernt]")
            self.assertEqual(gespeichert["modell_parameter"]["verschachtelt"]["Authorization"], "[entfernt]")

    def test_trace_schreibfehler_verdeckt_nicht_urspruenglichen_fehler(self):
        with patch.object(traces, "_speichern", side_effect=OSError("Test-Schreibfehler")):
            with self.assertLogs(traces.logger, level="ERROR"):
                with self.assertRaises(TimeoutError):
                    with traces.trace_lauf("Frage"):
                        raise TimeoutError("Originalfehler")


class KennzahlenTests(unittest.TestCase):
    def test_recall_und_rr_mit_duplikaten(self):
        ergebnis = kennzahlen.retrieval_kennzahlen(["a", "b"], ["x", "a", "a", "y", "z"])
        self.assertEqual(ergebnis["recall_at_k"], 0.5)
        self.assertEqual(ergebnis["reciprocal_rank_at_k"], 0.5)

    def test_treffer_ausserhalb_top5_zaehlt_nicht(self):
        ergebnis = kennzahlen.retrieval_kennzahlen(["a"], ["x"] * 5 + ["a"])
        self.assertEqual(ergebnis["recall_at_k"], 0)
        self.assertEqual(ergebnis["reciprocal_rank_at_k"], 0)

    def test_negativfall_ist_beim_retrieval_nicht_anwendbar(self):
        ergebnis = kennzahlen.retrieval_kennzahlen([], ["x"])
        self.assertIsNone(ergebnis["recall_at_k"])
        self.assertIsNone(ergebnis["reciprocal_rank_at_k"])

    def test_faithfulness_und_bestehensquote(self):
        self.assertEqual(kennzahlen.faithfulness_anteil([True, True, False, True]), 0.75)
        self.assertIsNone(kennzahlen.faithfulness_anteil([]))
        self.assertAlmostEqual(kennzahlen.bestehensquote([2, 1, 2]), 2 / 3)
        with self.assertRaises(ValueError):
            kennzahlen.bestehensquote([2, None, 2])


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.dataset = json.loads((ROOT / "evaluation/golden_dataset.entwurf.json").read_text(encoding="utf-8"))

    def test_15_eindeutige_faelle_und_3_echte_negativkategorien(self):
        self.assertEqual(dataset_pruefer.pruefen(self.dataset), [])
        self.assertEqual(len(self.dataset["faelle"]), 15)
        self.assertEqual([f["id"] for f in self.dataset["faelle"] if f["negativfall"]], ["G-13", "G-14", "G-15"])

    def test_feste_beispiele_bleiben_erhalten(self):
        faelle = {f["id"]: f for f in self.dataset["faelle"]}
        self.assertEqual(faelle["G-01"]["erwartete_quellen"], [{"bezeichnung":"Anleitung Modell 7","seite":34}])
        self.assertEqual(faelle["G-06"]["erwartete_quellen"], [{"produkt_id":12},{"produkt_id":19}])
        self.assertEqual(faelle["G-14"]["frage"], "Wie entkalke ich meine Kaffeemaschine?")

    def test_unfertiges_dataset_wird_nicht_als_final_freigegeben(self):
        # Eine bewusst unvollstaendige Testquelle verwenden. Dieser Test
        # bleibt gueltig, wenn das echte Golden Dataset spaeter fertig ist.
        fall = self.dataset["faelle"][1]
        fall["bereit"] = False
        fall["noch_zu_klaeren"] = ["Test: Fundstelle fehlt noch."]
        self.assertTrue(any("G-02" in fehler for fehler in dataset_pruefer.pruefen(self.dataset, final=True)))
        fall["bereit"] = True
        fall["noch_zu_klaeren"] = []
        fall["erwartete_quellen"] = [{"bezeichnung": "Testanleitung", "seite": None}]
        self.assertTrue(any("G-02" in fehler for fehler in dataset_pruefer.pruefen(self.dataset, final=True)))

    def test_45_geplante_lauefe_enthalten_keine_erfundenen_ergebnisse(self):
        vorlage = json.loads((ROOT / "evaluation/bewertungsvorlage_45_lauefe.json").read_text(encoding="utf-8"))
        self.assertEqual(len(vorlage["laeufe"]), 45)
        self.assertEqual(len({(l["fall_id"], l["durchlauf"]) for l in vorlage["laeufe"]}), 45)
        for lauf in vorlage["laeufe"]:
            self.assertFalse(lauf["ausgefuehrt"])
            self.assertIsNone(lauf["trace_id"])
            self.assertIsNone(lauf["person_1"]["punkte"])
            self.assertIsNone(lauf["person_2"]["punkte"])
            self.assertIsNone(lauf["endbewertung"]["punkte"])


if __name__ == "__main__":
    unittest.main()

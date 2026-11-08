"""Offline-Integration: Import, RPC-Parameter und echter FastAPI-Router.

Google und Supabase werden simuliert. Kein Netzwerk und keine echte .env.
"""

import importlib.util
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from functools import partial
from io import StringIO
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def laden(name, pfad):
    spec = importlib.util.spec_from_file_location(name, ROOT / pfad)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


ingestion = laden('integration_ingestion', 'scripts/embeddings_ergaenzen.py')
traces = laden('integration_traces', 'harness/app/traces.py')
schemas = laden('integration_schemas', 'harness/app/schemas.py')


class Speicher:
    def __init__(self, anzahl=3):
        self.zeilen = [dict(id=i, inhalt=f'Text {i}', dokument_id=1, embedding=None,
                            dokument={'titel': 'Testanleitung', 'produkt_id': 7})
                       for i in range(1, anzahl + 1)]
        self.updates = []

    def table(self, name):
        assert name == 'chunk'
        return Abfrage(self)


class Abfrage:
    def __init__(self, speicher):
        self.speicher = speicher
        self.filter = []
        self.maximum = 100
        self.werte = None

    def select(self, *_): return self
    def order(self, *_): return self
    def limit(self, wert): self.maximum = wert; return self
    def update(self, werte): self.werte = werte; return self
    def is_(self, name, _): self.filter.append(lambda z: z[name] is None); return self
    def gt(self, name, wert): self.filter.append(lambda z: z[name] > wert); return self
    def eq(self, name, wert):
        if name == 'dokument.produkt_id':
            self.filter.append(lambda z: z['dokument']['produkt_id'] == wert)
        else:
            self.filter.append(lambda z: z[name] == wert)
        return self

    def execute(self):
        zeilen = [z for z in self.speicher.zeilen if all(f(z) for f in self.filter)][:self.maximum]
        if self.werte is not None:
            for z in zeilen:
                z.update(self.werte)
                self.speicher.updates.append(z['id'])
        return SimpleNamespace(data=[dict(z) for z in zeilen])


class ImportTests(unittest.TestCase):
    def lauf(self, speicher, embed, **kwargs):
        with redirect_stdout(StringIO()):
            return ingestion.ergaenze_embeddings(speicher, embed, pause=0, **kwargs)

    def test_vorschau_ohne_api_und_updates(self):
        speicher, embed = Speicher(), Mock()
        self.assertEqual(self.lauf(speicher, embed), (3, 0))
        embed.assert_not_called()
        self.assertEqual(speicher.updates, [])

    def test_fuellt_nur_leere_vektoren_und_behaelt_ids(self):
        speicher = Speicher()
        speicher.zeilen[0]['embedding'] = [9.0]
        embed = Mock(return_value=[1.0] * 768)
        self.assertEqual(self.lauf(speicher, embed, schreiben=True), (2, 2))
        self.assertEqual(speicher.updates, [2, 3])
        self.assertEqual(speicher.zeilen[0]['embedding'], [9.0])
        self.assertEqual([z['id'] for z in speicher.zeilen], [1, 2, 3])
        self.assertEqual(embed.call_args.kwargs, {'art': 'dokument', 'titel': 'Testanleitung'})

    def test_paginierung_beim_schreiben(self):
        speicher = Speicher(205)
        self.assertEqual(self.lauf(speicher, Mock(return_value=[1.0] * 768), schreiben=True), (205, 205))
        self.assertEqual(len(set(speicher.updates)), 205)

    def test_limit_und_produktfilter(self):
        speicher = Speicher()
        self.assertEqual(self.lauf(speicher, Mock(), produkt_id=8), (0, 0))
        self.assertEqual(self.lauf(speicher, Mock(return_value=[1.0] * 768), schreiben=True, limit=1), (1, 1))

    def test_api_fehler_laesst_fortschritt_fuer_neustart(self):
        speicher = Speicher()
        embed = Mock(side_effect=[[1.0] * 768, TimeoutError()])
        with self.assertRaises(TimeoutError):
            self.lauf(speicher, embed, schreiben=True)
        self.assertEqual(speicher.updates, [1])
        self.assertEqual(self.lauf(speicher, Mock(return_value=[1.0] * 768), schreiben=True), (2, 2))


class RpcTests(unittest.TestCase):
    def test_hybride_rpc_und_unveraenderte_produkt_id(self):
        client = Mock()
        client.rpc.return_value.execute.return_value = SimpleNamespace(data=[])
        app = ModuleType('app'); app.__path__ = []
        config = ModuleType('app.config')
        config.settings = SimpleNamespace(supabase_url='test', supabase_key='test')
        supabase = ModuleType('supabase')
        supabase.Client = Mock
        supabase.create_client = Mock(return_value=client)
        with patch.dict('sys.modules', {'app': app, 'app.config': config, 'supabase': supabase}):
            db = laden('integration_db', 'harness/app/db.py')
        vektor = [1.0] * 768
        self.assertEqual(db.suche_wartungs_chunks('Frage', 7, vektor), [])
        client.rpc.assert_called_once_with('suche_chunks_hybrid', {
            'query_text': 'Frage', 'produkt_id': 7, 'query_embedding': vektor, 'treffer_limit': 5,
        })


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.embedding = AsyncMock(return_value=[1.0] * 768)
        self.suche = Mock(return_value=[dict(chunk_id=42, inhalt='Testabschnitt', seite=8,
                                           abschnitt='Test', fts_rang=None, fts_score=None,
                                           vektor_rang=1, vektor_distanz=0.1, rrf_score=1/61)])
        self.antwort = AsyncMock(return_value='Testantwort laut Seite 8, Abschnitt Test.')
        app = ModuleType('app'); app.__path__ = []
        db, llm, config, trace_modul = [ModuleType(n) for n in ['app.db', 'app.llm', 'app.config', 'app.traces']]
        db.suche_wartungs_chunks = self.suche
        llm.generiere_embedding_async = self.embedding
        llm.generiere_wartungsantwort = self.antwort
        config.settings = SimpleNamespace(gemini_embedding_model='gemini-embedding-2')
        trace_modul.trace_lauf = partial(traces.trace_lauf, verzeichnis=self.temp.name)
        with patch.dict('sys.modules', {
            'app': app, 'app.db': db, 'app.llm': llm, 'app.config': config,
            'app.schemas': schemas, 'app.traces': trace_modul,
        }):
            router = laden('integration_wartung', 'harness/app/routers/wartung.py')
        api = FastAPI()
        api.include_router(router.router)
        self.client = TestClient(api)

    def lese_trace(self):
        dateien = list(Path(self.temp.name).glob('*.jsonl'))
        self.assertEqual(len(dateien), 1)
        return json.loads(dateien[0].read_text(encoding="utf-8"))

    def test_erfolg_mit_quellen_und_trace_id(self):
        r = self.client.post('/wartung', json={'frage': 'Testfrage', 'produkt_id': 7})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['gefunden'])
        trace = self.lese_trace()
        self.assertEqual(r.json()['trace_id'], trace['trace_id'])
        self.assertEqual(trace['retrieval_treffer'][0]['chunk_id'], 42)
        self.assertEqual(trace['status'], 'ok')
        self.embedding.assert_awaited_once_with('Testfrage', art='frage')
        self.assertEqual(self.suche.call_args.kwargs['produkt_id'], 7)

    def test_keine_treffer_keine_antwortgenerierung(self):
        self.suche.return_value = []
        r = self.client.post('/wartung', json={'frage': 'Testfrage', 'produkt_id': 7})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()['gefunden'])
        self.assertEqual(r.json()['quellen'], [])
        self.antwort.assert_not_awaited()
        self.assertEqual(self.lese_trace()['ausgabe']['antwort'], 'weiß ich nicht')

    def test_unzureichender_kontext_gefunden_false(self):
        self.antwort.return_value = 'weiß ich nicht'
        r = self.client.post('/wartung', json={'frage': 'Testfrage', 'produkt_id': 7})
        self.assertFalse(r.json()['gefunden'])
        self.assertEqual(r.json()['quellen'], [])

    def test_embedding_fehler_503_mit_fehlertrace(self):
        self.embedding.side_effect = TimeoutError('Interne Testdetails')
        with self.assertLogs('integration_wartung', level='ERROR'):
            r = self.client.post('/wartung', json={'frage': 'Testfrage', 'produkt_id': 7})
        self.assertEqual(r.status_code, 503)
        self.assertNotIn('Interne Testdetails', r.text)
        self.assertEqual(self.lese_trace()['status'], 'fehler')
        self.suche.assert_not_called()

    def test_ungueltige_produkt_id_wird_vor_api_abgelehnt(self):
        r = self.client.post('/wartung', json={'frage': 'Testfrage', 'produkt_id': 0})
        self.assertEqual(r.status_code, 422)
        self.embedding.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()

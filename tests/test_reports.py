import asyncio
from copy import deepcopy
import io
import json
import os
import unittest
from unittest.mock import AsyncMock, patch
from zipfile import ZipFile
from fastapi.testclient import TestClient
from minambiente_live import server
from minambiente_live.reports import corpus, validated, metrics, build_bundle, batches

class ReportTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_archive_preserves_removed_category_and_reset(self):
        room=server.Room()
        with patch.dict(os.environ, {'CONCEPT_PROVIDER':'rules'}):
            for n in range(165): await server.publish(room, 'Agua y bosques',event_id=str(n))
        self.assertEqual(len(room.events),150)
        self.assertEqual(len(room.archive),165)
        room.settings['categories']=room.settings['categories'][1:]
        rows,categories=corpus(room.archive,room.settings)
        self.assertEqual(len(rows),165)
        self.assertTrue(next(c for c in categories if c['id']=='0')['historical'])
        counts,pairs=metrics(rows,categories)
        self.assertEqual(counts['0'],165)
        self.assertEqual(pairs[('0','1')],165)
    async def test_bundle_has_documents_full_transcript_and_escaped_text(self):
        room=server.Room()
        with patch.dict(os.environ,{'CONCEPT_PROVIDER':'rules'}):
            await server.publish(room,'Agua <script>alert(1)</script>',event_id='first')
            await server.publish(room,'Sin clasificación',event_id='second')
        response={'summary':[{'text':'La conversación aborda agua.','refs':['F00001']}]}
        with patch('minambiente_live.reports.completion',AsyncMock(return_value=response)):
            data,warnings=await build_bundle('test',deepcopy(room.archive),room.settings,lambda m:None)
        self.assertEqual(warnings,[])
        with ZipFile(io.BytesIO(data)) as z:
            self.assertEqual(len(z.namelist()),5)
            report=z.read('analisis_categorias.html').decode()
            self.assertIn('&lt;script&gt;',report)
            self.assertNotIn('<script>alert',report)
            self.assertIn('Sin clasificación',z.read('conversacion_completa.txt').decode())
            self.assertIn('F00002',report)
            visual=z.read('analisis_visual.html').decode()
            self.assertEqual(visual.count('<svg'),4)
            self.assertIn('analisis_categorias.html#F00001',visual)
    async def test_api_failure_still_exports_transcript_and_warning(self):
        room=server.Room()
        with patch.dict(os.environ,{'CONCEPT_PROVIDER':'rules'}): await server.publish(room,'Agua')
        with patch('minambiente_live.reports.completion',AsyncMock(side_effect=ValueError('bad'))):
            data,warnings=await build_bundle('test',room.archive,room.settings,lambda m:None)
        self.assertIn('Agua',warnings)
        with ZipFile(io.BytesIO(data)) as z: self.assertIn('Análisis no disponible',z.read('analisis_visual.html').decode())
    def test_citations_and_chunks(self):
        data={'findings':[{'text':'Bien','refs':['F1']},{'text':'Falso','refs':['F1','FAKE']},{'text':'Sin apoyo','refs':[]}]}
        self.assertEqual(len(validated(data,{'F1'})['findings']),1)
        rows=[{'ref':str(n),'text':'a'*1000} for n in range(50)]
        blocks=list(batches(rows,4000))
        self.assertEqual(sum(len(b) for b in blocks),50)
        self.assertGreater(len(blocks),1)

class ExportRouteTests(unittest.TestCase):
    def test_export_job_download_and_origin(self):
        server.rooms.clear()
        async def fake_bundle(*args): return b'PK-test',[]
        with TestClient(server.app) as client, patch.dict(os.environ,{'CONCEPT_PROVIDER':'rules'}), patch('minambiente_live.reports.build_bundle',fake_bundle):
            self.assertEqual(client.post('/api/sessions/test/export').status_code,400)
            self.assertEqual(client.post('/api/sessions/test/export',headers={'Origin':'https://evil.example'}).status_code,403)
            client.post('/api/sessions/test/text',json={'text':'Agua'})
            server.rooms['test'].producer=True
            self.assertEqual(client.post('/api/sessions/test/export').status_code,409)
            server.rooms['test'].producer=False
            self.assertEqual(client.post('/api/sessions/test/export').status_code,200)
            for _ in range(30):
                state=client.get('/api/sessions/test/export/status').json()
                if state['status']=='ready': break
            self.assertEqual(state['status'],'ready')
            r=client.get('/api/sessions/test/export/download')
            self.assertEqual(r.content,b'PK-test')
            self.assertEqual(r.headers['content-type'],'application/zip')
            client.delete('/api/sessions/test')
            self.assertEqual(client.get('/api/sessions/test/events').json()['events'],[])

# Las pruebas de otros módulos no deben realizar inferencia remota implícita.
def setUpModule():
    global _automatic_patch
    _automatic_patch = patch('minambiente_live.server.autonomous', side_effect=ValueError('offline test'))
    _automatic_patch.start()

def tearDownModule():
    _automatic_patch.stop()

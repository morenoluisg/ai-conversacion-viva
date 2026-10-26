import asyncio
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
import numpy as np
from fastapi.testclient import TestClient
from minambiente_live import server
from minambiente_live.audio import PCMChunks, LocalTranscriber, local_stream
from minambiente_live.concepts import rule_concepts, validate_concepts

class AudioTests(unittest.TestCase):
    def test_chunk_offsets_and_no_duplicate_overlap_tail(self):
        c = PCMChunks(6, 1)
        blocks = c.feed(bytes(6 * 32000))
        self.assertEqual([t for _, t in blocks], [0])
        self.assertEqual(c.finish(), [])
        next_blocks = c.feed(bytes(5 * 32000))
        self.assertEqual([t for _, t in next_blocks], [5])
        self.assertEqual(c.finish(), [])

    def test_final_partial_is_flushed(self):
        c = PCMChunks(6, 1)
        self.assertEqual(c.feed(bytes(2 * 32000)), [])
        self.assertEqual(len(c.finish()[0][0]), 64000)
        self.assertEqual(c.finish(), [])

    def test_timestamp_overlap_does_not_repeat_words(self):
        model = unittest.mock.Mock()
        model.transcribe.side_effect = [
            ([SimpleNamespace(no_speech_prob=0, words=[SimpleNamespace(word=' agua', end=5.5)])], None),
            ([SimpleNamespace(no_speech_prob=0, words=[SimpleNamespace(word=' agua', end=.5), SimpleNamespace(word=' bosques', end=1.5)])], None),
        ]
        t = LocalTranscriber(model)
        pcm = (np.ones(16000) * 1000).astype('<i2').tobytes()
        self.assertEqual(t.transcribe(pcm, 0), 'agua')
        self.assertEqual(t.transcribe(pcm, 5), 'bosques')

    def test_silence_is_not_hallucinated(self):
        model = unittest.mock.Mock()
        self.assertEqual(LocalTranscriber(model).transcribe(bytes(32000), 0), '')
        model.transcribe.assert_not_called()

    def test_rules_and_literal_evidence_validation(self):
        values = rule_concepts('La cuenca y los datos abiertos protegen la biodiversidad.')
        self.assertIn({'label': 'Cuencas', 'theme': 0}, values)
        self.assertNotIn({'label': 'Datos', 'theme': 4}, values)
        valid = validate_concepts({'concepts':[
            {'label':'Agua','theme':0,'evidence':'agua'},
            {'label':'Marte','theme':1,'evidence':'Marte'},
            {'label':'Mala etiqueta','theme':True,'evidence':'agua'}]}, 'Hablamos del agua')
        self.assertEqual(valid, [{'label':'Agua','theme':0}])

class AsyncAudioTests(unittest.IsolatedAsyncioTestCase):
    async def test_stop_transcribes_short_tail(self):
        class Model:
            def transcribe(self, audio, **kwargs):
                self.samples = len(audio)
                return [SimpleNamespace(no_speech_prob=0,words=[SimpleNamespace(word=' agua',end=.6)])], None
        model, items, statuses = Model(), [], []
        async def source():
            yield (np.ones(16000) * 1000).astype('<i2').tobytes()
        async def emit(text, event_id): items.append(text)
        async def status(msg): statuses.append(msg)
        await local_stream(source(), emit, status, model=model)
        self.assertEqual(model.samples, 16000)
        self.assertEqual(items, ['agua'])
        self.assertEqual(statuses[0], 'ready')

    async def test_deepgram_only_publishes_final_text(self):
        class Provider:
            def __init__(self): self.sent=[]
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
            async def send(self, value): self.sent.append(value)
            def __aiter__(self): return self.messages()
            async def messages(self):
                import json
                for final in (False, True):
                    yield json.dumps({'type':'Results','is_final':final,'start':0,'duration':1,
                                      'channel':{'alternatives':[{'transcript':'Agua y bosques'}]}})
        provider, result, partials = Provider(), [], []
        async def source():
            # Deja que llegue texto parcial antes de enviar CloseStream.
            if False: yield b''
        async def emit(text, event_id): result.append(text)
        async def status(msg): pass
        async def partial(text): partials.append(text)
        with patch.dict(os.environ, {'DEEPGRAM_API_KEY':'test-only'}), patch('minambiente_live.server.websockets.connect', return_value=provider):
            await server.deepgram_stream(source(), emit, status, partial)
        self.assertEqual(result, ['Agua y bosques'])
        self.assertIn('Agua y bosques', partials)
        self.assertEqual(partials[-1], '')

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        server.rooms.clear()
        self.env = patch.dict(os.environ, {'CONCEPT_PROVIDER':'rules'})
        self.env.start()
        self.client = TestClient(server.app)
        self.client.__enter__()
    def tearDown(self):
        self.client.__exit__(None,None,None)
        self.env.stop()

    def test_pages_api_viewer_dedup_and_reset(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertIn('LIVE_MODE', self.client.get('/visual').text)
        with self.client.websocket_connect('/ws/view/test') as ws:
            self.assertEqual(ws.receive_json(), {'type':'snapshot','events':[]})
            body = {'text':'Protejamos el agua y los bosques', 'id':'one'}
            r=self.client.post('/api/sessions/test/text',json=body)
            self.assertTrue(r.json()['accepted'])
            event=ws.receive_json()
            self.assertEqual(event['event']['concepts'][0]['label'],'Agua')
            self.assertFalse(self.client.post('/api/sessions/test/text',json=body).json()['accepted'])
            self.assertEqual(len(self.client.get('/api/sessions/test/events').json()['events']),1)
            self.client.delete('/api/sessions/test')
            self.assertEqual(ws.receive_json(),{'type':'reset'})
        self.assertEqual(self.client.get('/api/sessions/test/events').json()['events'],[])

    def test_audio_websocket_drains_tail_before_stopped(self):
        async def fake_stream(messages, emit, status):
            await status('ready')
            async for pcm in messages:
                self.assertEqual(len(pcm),6400)
            await emit('Agua y biodiversidad', 'tail')
        with patch('minambiente_live.server.local_stream', fake_stream):
            with self.client.websocket_connect('/ws/audio/test') as ws:
                ws.send_json({'provider':'local','sample_rate':16000})
                self.assertEqual(ws.receive_json()['type'],'ready')
                ws.send_bytes(bytes(6400))
                ws.send_json({'type':'stop'})
                messages=[]
                while True:
                    m=ws.receive_json(); messages.append(m['type'])
                    if m['type']=='stopped': break
                self.assertIn('published',messages)
            self.assertEqual(len(self.client.get('/api/sessions/test/events').json()['events']),1)

    def test_cross_origin_and_invalid_pcm_rejected(self):
        self.assertEqual(self.client.post('/api/sessions/test/text',json={'text':'Agua'},headers={'Origin':'https://other.example'}).status_code,403)
        with self.client.websocket_connect('/ws/audio/test') as ws:
            ws.send_json({'provider':'local','sample_rate':44100})
            self.assertEqual(ws.receive_json()['type'],'error')

    def test_reset_discards_pending_epoch(self):
        async def run():
            room=server.Room(); old=room.epoch; room.epoch+=1
            self.assertIsNone(await server.publish(room,'Agua',epoch=old))
        asyncio.run(run())

if __name__=='__main__': unittest.main()

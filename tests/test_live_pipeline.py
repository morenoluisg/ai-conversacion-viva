import asyncio
import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from minambiente_live import server


class BackgroundAnalysisTests(unittest.IsolatedAsyncioTestCase):
    async def test_hung_model_times_out_without_blocking_transcription(self):
        room=server.Room()
        async def hung(*args, **kwargs): await asyncio.sleep(60)
        with patch.dict(os.environ,{'CONCEPT_PROVIDER':'rules'}),patch('minambiente_live.server.autonomous',hung):
            event=await asyncio.wait_for(server.publish(room,'Agua',wait_analysis=False),timeout=.1)
            self.assertEqual(len(room.archive),1)
            self.assertTrue(event['analysis_pending'])
            await asyncio.wait_for(room.analysis_task,timeout=11)
        self.assertFalse(event['analysis_pending'])
        self.assertEqual(event['lenses']['automatic']['method'],'deepseek-auto-unavailable')

    async def test_disconnected_caller_does_not_cancel_archived_analysis(self):
        room=server.Room()
        gate=asyncio.Event()
        async def slow(*args, **kwargs):
            await gate.wait()
            return [],[],[]
        with patch.dict(os.environ,{'CONCEPT_PROVIDER':'rules'}),patch('minambiente_live.server.autonomous',slow):
            request=asyncio.create_task(server.publish(room,'Texto confirmado',event_id='saved'))
            await asyncio.sleep(.01)
            request.cancel()
            await asyncio.gather(request,return_exceptions=True)
            self.assertEqual(len(room.archive),1)
            self.assertFalse(room.analysis_task.done())
            gate.set()
            await room.analysis_task
        self.assertEqual(room.archive[0]['text'],'Texto confirmado')
        self.assertFalse(room.archive[0]['analysis_pending'])

    async def test_burst_is_archived_before_model_and_updates_once(self):
        room = server.Room()
        gate = asyncio.Event()
        messages = []
        async def slow(*args, **kwargs):
            await gate.wait()
            return [], [], []
        async def broadcast(room, message): messages.append(message)
        with patch.dict(os.environ, {'CONCEPT_PROVIDER':'rules'}), patch('minambiente_live.server.autonomous', slow), patch('minambiente_live.server.broadcast', broadcast):
            for i in range(60):
                await asyncio.wait_for(server.publish(room,'Agua y escuelas',event_id=str(i),wait_analysis=False),timeout=.1)
            self.assertEqual(len(room.archive),60)
            self.assertEqual(len([m for m in messages if m['type']=='event']),60)
            self.assertEqual(server.analysis_status(room)['pending'],60)
            self.assertTrue(all(e['analysis_pending'] for e in room.archive))
            self.assertIsNone(await server.publish(room,'Duplicado',event_id='0',wait_analysis=False))
            async with asyncio.timeout(.1):
                async with room.lock: pass
            gate.set()
            await room.analysis_task
        self.assertEqual(server.analysis_status(room)['pending'],0)
        self.assertEqual(len(room.archive),60)
        self.assertEqual(len([m for m in messages if m['type']=='event_update']),60)
        self.assertTrue(all(not e['analysis_pending'] for e in room.archive))

    async def test_model_exception_is_isolated_and_text_survives(self):
        async def broken(*args, **kwargs): raise RuntimeError('provider failure')
        room=server.Room()
        with patch.dict(os.environ,{'CONCEPT_PROVIDER':'rules'}),patch('minambiente_live.server.autonomous',broken):
            event=await server.publish(room,'Agua para todos')
        self.assertEqual(event['text'],'Agua para todos')
        self.assertEqual(event['lenses']['automatic']['method'],'deepseek-auto-unavailable')
        self.assertEqual(server.analysis_status(room)['failures'],1)
        self.assertFalse(event['analysis_pending'])


class CaptureIndependenceTests(unittest.TestCase):
    def test_stop_does_not_cancel_analysis_or_lose_burst(self):
        async def slow(*args, **kwargs):
            await asyncio.sleep(.2)
            return [],[],[]
        async def stream(messages,emit,status,partial):
            await status('ready')
            async for pcm in messages: break
            for i in range(45): await emit('Agua y escuelas',str(i))
        with patch.dict(os.environ,{'CONCEPT_PROVIDER':'rules'}),patch('minambiente_live.server.autonomous',slow),patch('minambiente_live.server.deepgram_stream',stream),TestClient(server.app) as client:
            with client.websocket_connect('/ws/audio/burst') as ws:
                ws.send_json({'provider':'deepgram','sample_rate':16000})
                self.assertEqual(ws.receive_json()['type'],'ready')
                ws.send_bytes(bytes(6400))
                transcripts=0
                while True:
                    message=ws.receive_json()
                    self.assertNotEqual(message['type'],'error')
                    if message['type']=='transcript':transcripts+=1
                    if message['type']=='stopped':break
            self.assertEqual(transcripts,45)
            self.assertEqual(len(client.get('/api/sessions/burst/events').json()['events']),45)
            self.assertFalse(server.rooms['burst'].producer)
            self.assertFalse(server.rooms['burst'].analysis_task.done())
            self.assertEqual(client.post('/api/sessions/burst/export').status_code,409)
            client.delete('/api/sessions/burst')
            self.assertEqual(len(server.rooms['burst'].archive),0)
            self.assertEqual(server.analysis_status(server.rooms['burst'])['pending'],0)

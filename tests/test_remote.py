import asyncio
import os
from unittest.mock import patch
import unittest
from fastapi.testclient import TestClient
from minambiente_live import server

class RemotePagesTests(unittest.TestCase):
    def setUp(self):
        server.rooms.clear()
        self.client=TestClient(server.app)
        self.client.__enter__()
    def tearDown(self): self.client.__exit__(None,None,None)
    def test_pages_shared_capture_and_host_protection(self):
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertEqual(self.client.get('/admin').text,self.client.get('/').text)
        capture=self.client.get('/captura?session=remote').text
        self.assertIn('/static/capture-audio.js',capture)
        self.assertNotIn('categoryList',capture)
        self.assertIn('/static/server-setup.js',self.client.get('/servidor').text)
        self.assertEqual(self.client.get('/static/remote.css').status_code,200)
        self.assertEqual(self.client.get('/captura',headers={'Host':'evil.example'}).status_code,400)
        status=self.client.get('/api/sessions/remote/status').json()
        self.assertFalse(status['capturing'])
        self.assertEqual(status['fragments'],0)
    def test_display_updates_other_viewers_and_survives_reconnect(self):
        with self.client.websocket_connect('/ws/view/remote') as ws:
            ws.receive_json()
            r=self.client.post('/api/sessions/remote/display',json={'view':'stream','lens':'automatic','theme':'light'})
            self.assertEqual(r.status_code,200)
            self.assertEqual(ws.receive_json(),{'type':'display','view':'stream','lens':'automatic','theme':'light'})
        with self.client.websocket_connect('/ws/view/remote') as ws:
            self.assertEqual(ws.receive_json()['display'],{'view':'stream','lens':'automatic','theme':'light'})
        self.assertEqual(self.client.post('/api/sessions/remote/display',json={'view':'bad'}).status_code,422)
        self.assertEqual(self.client.post('/api/sessions/remote/display',json={'view':'radial'},headers={'Origin':'https://evil.example'}).status_code,403)
    def test_remote_audio_reaches_same_session_visualization(self):
        async def fake_stream(messages,emit,status):
            await status('ready')
            async for pcm in messages: pass
            await emit('Agua desde otro equipo','remote-audio')
        with patch.dict(os.environ,{'CONCEPT_PROVIDER':'rules'}),patch('minambiente_live.server.autonomous',side_effect=ValueError('offline')),patch('minambiente_live.server.local_stream',fake_stream):
            with self.client.websocket_connect('/ws/view/remote') as viewer:
                viewer.receive_json()
                with self.client.websocket_connect('/ws/audio/remote') as audio:
                    audio.send_json({'provider':'local','sample_rate':16000})
                    self.assertEqual(audio.receive_json()['type'],'ready')
                    self.assertTrue(self.client.get('/api/sessions/remote/status').json()['capturing'])
                    audio.send_bytes(bytes(6400));audio.send_json({'type':'stop'})
                    while audio.receive_json()['type']!='stopped': pass
                event=viewer.receive_json()['event']
                self.assertEqual(event['text'],'Agua desde otro equipo')
                self.assertEqual(self.client.get('/api/sessions/remote/status').json()['fragments'],1)
                self.assertEqual(self.client.get('/api/sessions/other/status').json()['fragments'],0)

class DisplayThemeTests(unittest.TestCase):
    def test_theme_broadcast_restore_and_validation(self):
        server.rooms.clear()
        with TestClient(server.app) as client:
            with client.websocket_connect('/ws/view/theme-test') as ws:
                self.assertEqual(ws.receive_json()['display']['theme'],'light')
                self.assertEqual(client.post('/api/sessions/theme-test/display',json={'theme':'dark'}).status_code,200)
                self.assertEqual(ws.receive_json()['theme'],'dark')
            with client.websocket_connect('/ws/view/theme-test') as ws:
                self.assertEqual(ws.receive_json()['display']['theme'],'dark')
            self.assertEqual(client.post('/api/sessions/theme-test/display',json={'theme':'unknown'}).status_code,422)
            self.assertEqual(client.get('/api/sessions/theme-test/status').json()['display']['theme'],'dark')

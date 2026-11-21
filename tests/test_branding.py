import io
import json
import os
import unittest
from unittest.mock import AsyncMock, patch
from zipfile import ZipFile
from fastapi.testclient import TestClient
from minambiente_live import server
from minambiente_live.branding import initial_branding, environmental_branding
from minambiente_live.reports import build_bundle


class BrandingTests(unittest.TestCase):
    def test_environment_and_session_updates_reconnect_isolation(self):
        with patch.dict(os.environ, {'APP_NAME':'Encuentro educativo','APP_CENTER_BOTTOM':'EDUCACIÓN'}), TestClient(server.app) as client:
            initial=client.get('/api/sessions/education/branding').json()
            self.assertEqual(initial['current']['app_name'],'Encuentro educativo')
            self.assertEqual(initial['environmental'],environmental_branding())
            value={**initial['current'],'organization':'Universidad de prueba','accent_color':'#6438ab'}
            with client.websocket_connect('/ws/view/education') as ws:
                self.assertEqual(ws.receive_json()['branding'],initial['current'])
                self.assertEqual(client.put('/api/sessions/education/branding',json=value).status_code,200)
                self.assertEqual(ws.receive_json(),{'type':'branding','branding':value})
            with client.websocket_connect('/ws/view/education') as ws:
                self.assertEqual(ws.receive_json()['branding'],value)
            self.assertEqual(client.get('/api/sessions/other/branding').json()['current'],initial['current'])
            self.assertEqual(server.rooms['education'].settings['categories'],server.rooms['other'].settings['categories'])
            for route in ('/','/admin','/visual','/captura','/servidor'):
                page=client.get(route+'?session=education')
                self.assertEqual(page.status_code,200)
                self.assertIn('<title>Encuentro educativo</title>',page.text)
                self.assertIn('/static/branding.js',page.text)
            self.assertEqual(client.put('/api/sessions/education/branding',json={**value,'accent_color':'red;display:none'}).status_code,422)
            self.assertEqual(client.put('/api/sessions/education/branding',json={**value,'app_name':'  '}).status_code,422)
            self.assertEqual(client.put('/api/sessions/education/branding',json=value,headers={'Origin':'https://evil.example'}).status_code,403)

    def test_html_configuration_cannot_close_script(self):
        with TestClient(server.app) as client:
            value={**environmental_branding(),'app_name':'</script><script>alert(1)</script>'}
            client.put('/api/sessions/safe/branding',json=value)
            page=client.get('/visual?session=safe').text
            self.assertNotIn('<script>alert(1)</script>',page)
            self.assertIn('\\u003c/script>',page)


class BrandingReportTests(unittest.IsolatedAsyncioTestCase):
    async def test_report_preserves_identity_and_escapes_text(self):
        settings={'categories':[],'agenda':'','branding':{**environmental_branding(),'app_name':'Encuentro educativo','organization':'Escuela <b>abierta</b>'}}
        events=[{'id':'one','text':'Aprendemos juntos','concepts':[],'categories':[],'speaker':'Participante','at':'','method':'rules'}]
        with patch('minambiente_live.reports.completion',AsyncMock(return_value={})):
            data,_=await build_bundle('education',events,settings,lambda _:None)
        with ZipFile(io.BytesIO(data)) as archive:
            for name in ('analisis_categorias.html','analisis_visual.html'):
                page=archive.read(name).decode()
                self.assertIn('Encuentro educativo',page)
                self.assertIn('Escuela &lt;b&gt;abierta&lt;/b&gt;',page)
            self.assertEqual(json.loads(archive.read('datos_conversacion.json'))['settings']['branding'],settings['branding'])

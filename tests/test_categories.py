import os
import unittest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from minambiente_live import server
from minambiente_live.categories import analyze, defaults

class CategoryTests(unittest.TestCase):
    def setUp(self):
        server.rooms.clear()
        self.env = patch.dict(os.environ, {'CONCEPT_PROVIDER': 'rules'})
        self.env.start()
        self.client = TestClient(server.app)
        self.client.__enter__()
    def tearDown(self):
        self.client.__exit__(None,None,None)
        self.env.stop()
    def test_remove_reorder_and_custom_rules(self):
        self.client.post('/api/sessions/c/text', json={'text':'agua y biodiversidad'})
        body = self.client.get('/api/sessions/c/settings').json()
        body['categories'] = [body['categories'][1], dict(id='custom',name='Educación',color='#123456',keywords=['escuela'],origin='manual')]
        self.assertEqual(self.client.put('/api/sessions/c/settings',json=body).status_code,200)
        concepts = self.client.get('/api/sessions/c/events').json()['events'][0]['concepts']
        self.assertEqual(concepts,[{'label':'Agua','theme':0},{'label':'Biodiversidad','theme':1}])
        # La exportación conserva la clasificación original; el mapa usa la configuración actual.
        r = self.client.post('/api/sessions/c/text',json={'text':'La escuela aprende'}).json()
        self.assertEqual(r['event']['concepts'],[{'label':'Educación','theme':1}])
        self.assertEqual(len(self.client.get('/api/sessions/other/settings').json()['categories']),6)
    def test_duplicate_categories_and_origin_rejected(self):
        body = self.client.get('/api/sessions/c/settings').json()
        body['categories'].append(body['categories'][0])
        self.assertEqual(self.client.put('/api/sessions/c/settings',json=body).status_code,400)
        self.assertEqual(self.client.put('/api/sessions/c/settings',json=body,headers={'Origin':'https://evil.example'}).status_code,403)
    def test_fallback_keeps_custom_categories(self):
        with patch.dict(os.environ,{'CONCEPT_PROVIDER':'deepseek'}), patch('minambiente_live.server.analyze',side_effect=ValueError('invalid')):
            with self.client.websocket_connect('/ws/view/c') as viewer:
                viewer.receive_json()
                event=self.client.post('/api/sessions/c/text',json={'text':'agua'}).json()['event']
                self.assertIn(event['method'],('analysis-pending','rules-fallback'))
                self.assertEqual(event['concepts'][0]['label'],'Agua')
                update=viewer.receive_json()
                while update['type']!='event_update': update=viewer.receive_json()
                self.assertEqual(update['event']['method'],'rules-fallback')
    def test_agenda_failure_preserves_settings(self):
        body=self.client.get('/api/sessions/c/settings').json()
        body['agenda']='09:00 Educación ambiental'
        with patch('minambiente_live.server.completion',side_effect=ValueError('bad')):
            self.assertEqual(self.client.post('/api/sessions/c/infer-categories',json=body).status_code,502)
        self.assertEqual(self.client.get('/api/sessions/c/settings').json()['agenda'],'')

class ModelTests(unittest.IsolatedAsyncioTestCase):
    async def test_emergent_requires_evidence_and_permission(self):
        response={'concepts':[{'label':'Escuelas','category':'Educación','evidence':'escuelas'}, {'label':'Falso','category':'Inventada','evidence':'inexistente'}]}
        with patch('minambiente_live.categories.completion',AsyncMock(return_value=response)):
            result,categories=await analyze('Las escuelas participan',defaults(),emergent=True)
            self.assertEqual(len(categories),7)
            self.assertEqual(result,[{'label':'Escuelas','theme':6}])
            result,categories=await analyze('Las escuelas participan',defaults(),emergent=False)
            self.assertEqual(result,[])
            self.assertEqual(len(categories),6)

class GroupSettingsTests(unittest.TestCase):
    def test_groups_can_overlap_and_unknown_categories_are_rejected(self):
        server.rooms.clear()
        with TestClient(server.app) as client:
            body=client.get('/api/sessions/groups/settings').json()
            body['groups']=[{'id':'one','name':'Datos y agua','categories':['0','4']},{'id':'two','name':'Datos y gobernanza','categories':['4','5']}]
            self.assertEqual(client.put('/api/sessions/groups/settings',json=body).status_code,200)
            self.assertEqual(client.get('/api/sessions/groups/settings').json()['groups'],body['groups'])
            with client.websocket_connect('/ws/view/groups') as ws:
                self.assertEqual(ws.receive_json()['settings']['groups'],body['groups'])
            body['groups'][0]['categories']=['missing']
            self.assertEqual(client.put('/api/sessions/groups/settings',json=body).status_code,400)
            body['groups']=[{'id':str(i),'name':'Grupo','categories':[]} for i in range(4)]
            self.assertEqual(client.put('/api/sessions/groups/settings',json=body).status_code,422)

# Las pruebas de otros módulos no deben realizar inferencia remota implícita.
def setUpModule():
    global _automatic_patch
    _automatic_patch = patch('minambiente_live.server.autonomous', side_effect=ValueError('offline test'))
    _automatic_patch.start()

def tearDownModule():
    _automatic_patch.stop()

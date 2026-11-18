import asyncio
from unittest.mock import patch, AsyncMock
import unittest
from fastapi.testclient import TestClient
from minambiente_live import server
from minambiente_live.categories import autonomous, agenda_profile

class AutonomousTests(unittest.IsolatedAsyncioTestCase):
    async def test_starts_empty_and_model_defines_categories_and_groups(self):
        response={'concepts':[{'label':'Escuelas','category':'Educación ambiental','evidence':'escuelas'}],
                  'groups':[{'name':'Aprendizaje territorial','categories':['Educación ambiental']}]}
        with patch('minambiente_live.categories.completion',AsyncMock(return_value=response)):
            concepts,categories,groups=await autonomous('Las escuelas participan',[],[],[])
        self.assertEqual(categories[0]['name'],'Educación ambiental')
        self.assertEqual(groups[0]['name'],'Aprendizaje territorial')
        self.assertEqual(groups[0]['categories'],[categories[0]['id']])
        self.assertEqual(concepts,[{'label':'Escuelas','theme':0}])
    async def test_rejects_unfounded_category_and_unknown_group(self):
        response={'concepts':[{'label':'Escuelas','category':'Educación','evidence':'Marte'}], 'groups':[{'name':'Grupo','categories':['Educación']}]}
        with patch('minambiente_live.categories.completion',AsyncMock(return_value=response)):
            self.assertEqual(await autonomous('escuelas',[],[],[]),([],[],[]))
        response['concepts'][0]['evidence']='escuelas'
        response['groups'][0]['categories']=['Inventada']
        with patch('minambiente_live.categories.completion',AsyncMock(return_value=response)):
            with self.assertRaises(ValueError): await autonomous('escuelas',[],[],[])
    async def test_parallel_lenses_keep_same_text_and_separate_taxonomies(self):
        room=server.Room()
        auto_category=dict(id='new',name='Aprendizaje',color='#287a38',keywords=['escuelas'],origin='emergent')
        with patch.dict(server.os.environ,{'CONCEPT_PROVIDER':'rules'}),patch('minambiente_live.server.autonomous',AsyncMock(return_value=([{'label':'Escuelas','theme':0}],[auto_category],[{'id':'auto-0','name':'Educación','categories':['new']}]))):
            event=await server.publish(room,'Las escuelas usan datos',event_id='x')
        self.assertEqual(event['lenses']['automatic']['text'],event['text'])
        self.assertEqual(room.settings['categories'][0]['name'],'Agua')
        self.assertEqual(room.lenses['automatic']['settings']['categories'][0]['name'],'Aprendizaje')
        self.assertEqual(len(room.lenses['agenda']['events']),1)
        self.assertEqual(len(room.archive),1)
        self.assertEqual(event['lenses']['automatic']['settings']['groups'][0]['name'],'Educación')
    async def test_failure_keeps_text_and_previous_groups(self):
        room=server.Room()
        with patch.dict(server.os.environ,{'CONCEPT_PROVIDER':'rules'}),patch('minambiente_live.server.autonomous',AsyncMock(side_effect=ValueError('bad'))):
            event=await server.publish(room,'Intervención preservada')
        self.assertEqual(event['lenses']['automatic']['method'],'deepseek-auto-unavailable')
        self.assertEqual(event['lenses']['automatic']['text'],'Intervención preservada')
        self.assertEqual(room.lenses['automatic']['settings']['categories'],[])
    def test_agenda_profile_contains_event_and_three_groups(self):
        profile=agenda_profile()
        self.assertIn('SINA CONECTA 2026',profile['agenda'])
        self.assertEqual(len(profile['categories']),8)
        self.assertEqual(len(profile['groups']),3)

class ConceptBudgetTests(unittest.IsolatedAsyncioTestCase):
    def test_long_phrases_are_rejected_and_only_three_concepts_selected(self):
        from minambiente_live.categories import validate_analysis
        data={'concepts':[
            {'label':'Una descripción excesivamente larga de muchos detalles','category':'Ruido','evidence':'agua'},
            *[{'label':'Concepto '+str(i),'category':'Agua','evidence':'agua'} for i in range(8)]]}
        categories=[dict(id='a',name='Agua',color='#087e8b',keywords=[],origin='manual')]
        concepts,updated=validate_analysis(data,'agua',categories,True)
        self.assertEqual(len(concepts),3)
        self.assertEqual(len(updated),1)
        self.assertTrue(all(len(c['label'])<=36 and len(c['label'].split())<=4 for c in concepts))
    async def test_recent_canonical_vocabulary_is_sent_to_model(self):
        room=server.Room()
        room.events.append(dict(text='Agua',concepts=[dict(label='Cuencas',theme=0)],categories=room.settings['categories']))
        mock=AsyncMock(return_value=([dict(label='Cuencas',theme=0)],room.settings['categories']))
        with patch.dict(server.os.environ,{'CONCEPT_PROVIDER':'deepseek'}),patch('minambiente_live.server.analyze',mock):
            await server.classify(room,'Las cuencas requieren protección','manual')
        self.assertIn(dict(label='Cuencas',category='Agua'),mock.call_args.kwargs['known'])

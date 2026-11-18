"""Puente local de audio, transcripción y estado para Conversación viva."""
import asyncio
from copy import deepcopy
from collections import OrderedDict, deque
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from urllib.parse import urlencode, urlsplit
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
import websockets

load_dotenv(Path(os.getenv('MINAMBIENTE_ENV_FILE', Path.cwd() / '.env')))
from .audio import local_stream, get_model
from .concepts import extract
from .categories import defaults, analyze, fallback, completion, COLORS, normalize, agenda_profile, autonomous
ROOT = Path(__file__).parent

class Room:
    def __init__(self):
        self.settings = {'categories': defaults(), 'agenda': '', 'emergent': False, 'groups': []}
        self.lenses = {
            'agenda': {'settings': agenda_profile(), 'events': deque(maxlen=150)},
            'automatic': {'settings': {'categories': [], 'groups': [], 'agenda': '', 'emergent': True}, 'events': deque(maxlen=150)}}
        self.events = deque(maxlen=150)
        self.archive = []
        self.export_task = None
        self.export_state = None
        self.export_bytes = None
        self.ids = deque(maxlen=1000)
        self.viewers = set()
        self.lock = asyncio.Lock()
        self.producer = False
        self.display = {'view': 'radial', 'lens': 'agenda', 'theme': 'light'}
        self.epoch = 0

rooms = OrderedDict()

def room_for(session):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', session):
        raise HTTPException(400, 'Identificador de sesión inválido')
    if session not in rooms:
        if len(rooms) >= 20:
            removable = next((k for k, r in rooms.items() if not r.producer and not r.viewers and not r.archive and not (r.export_task and not r.export_task.done())), None)
            if removable is None:
                raise HTTPException(429, 'Hay demasiadas sesiones activas')
            del rooms[removable]
        rooms[session] = Room()
    rooms.move_to_end(session)
    return rooms[session]

def trusted_origin(headers):
    origin = headers.get('origin')
    if not origin:
        return True  # CLI local y pruebas; los navegadores sí envían Origin.
    try:
        parsed = urlsplit(origin)
        return parsed.scheme in ('http', 'https') and parsed.netloc == headers.get('host')
    except ValueError:
        return False

async def broadcast(room, message):
    async def send(ws):
        try:
            await asyncio.wait_for(ws.send_json(message), timeout=2)
        except Exception:
            room.viewers.discard(ws)
    await asyncio.gather(*(send(ws) for ws in tuple(room.viewers)))


async def classify(room, text, lens):
    settings = deepcopy(room.settings if lens == 'manual' else room.lenses[lens]['settings'])
    history = room.events if lens == 'manual' else room.lenses[lens]['events']
    vocabulary = {}
    for event in list(history)[-40:]:
        for concept in event['concepts']:
            catalog = event.get('categories', settings['categories'])
            if 0 <= concept['theme'] < len(catalog):
                name = catalog[concept['theme']]['name']
                key = (concept['label'], name)
                vocabulary[key] = vocabulary.get(key, 0) + 1
    known = [{'label': key[0], 'category': key[1]} for key,count in sorted(vocabulary.items(), key=lambda item:-item[1])[:40] if len(key[0]) <= 36 and len(key[0].split()) <= 4]
    try:
        if lens == 'automatic':
            recent = [e['text'] for e in list(room.events)[-8:]]
            concepts, categories, groups = await autonomous(text, settings['categories'], settings['groups'], recent, known=known)
            settings.update(categories=categories, groups=groups)
            return concepts, settings, 'deepseek-auto'
        if os.getenv('CONCEPT_PROVIDER') == 'deepseek':
            concepts, categories = await analyze(text, settings['categories'], settings['agenda'], settings['emergent'], known=known)
            settings['categories'] = categories
            return concepts, settings, 'deepseek'
        if lens == 'manual' and os.getenv('CONCEPT_PROVIDER') == 'ollama':
            from .concepts import THEMES
            original, method = await extract(text)
            indices = {normalize(c['name']): i for i,c in enumerate(settings['categories'])}
            concepts = [dict(c, theme=indices[normalize(THEMES[c['theme']])]) for c in original if normalize(THEMES[c['theme']]) in indices]
            return concepts, settings, method
        return fallback(text, settings['categories']), settings, 'rules'
    except (ValueError, KeyError, TypeError, __import__('httpx').HTTPError):
        return fallback(text, settings['categories']), settings, 'deepseek-auto-unavailable' if lens == 'automatic' else 'rules-fallback'

def lens_snapshots(room):
    return {name: {'settings': data['settings'], 'events': list(data['events'])} for name,data in room.lenses.items()}

async def publish(room, text, speaker='Conversación', event_id=None, epoch=None):
    text = text.strip()[:4000]
    if not text:
        return None
    event_id = event_id or str(uuid4())
    async with room.lock:
        if event_id in room.ids or (epoch is not None and epoch != room.epoch):
            return None
        results = await asyncio.gather(classify(room, text, 'manual'), classify(room, text, 'agenda'), classify(room, text, 'automatic'))
        concepts, settings, method = results[0]
        # Si la extracción tardó mientras el usuario vaciaba el mapa, se descarta.
        if epoch is not None and epoch != room.epoch:
            return None
        room.settings = settings
        alternatives = {}
        for lens, (cs, config, source) in zip(('agenda', 'automatic'), results[1:]):
            room.lenses[lens]['settings'] = config
            item = dict(id=event_id, text=text, speaker=speaker, concepts=cs, method=source,
                        categories=config['categories'], settings=deepcopy(config), at=datetime.now(timezone.utc).isoformat())
            room.lenses[lens]['events'].append(item)
            alternatives[lens] = item
        event = {'id': event_id, 'text': text, 'speaker': speaker,
                 'concepts': concepts, 'method': method, 'categories': room.settings['categories'],
                 'at': datetime.now(timezone.utc).isoformat(), 'lenses': alternatives}
        room.ids.append(event_id)
        room.events.append(event)
        room.archive.append(deepcopy(event))
        await broadcast(room, {'type': 'event', 'event': event})
        return event

@asynccontextmanager
async def lifespan(app):
    yield
    tasks = [r.export_task for r in rooms.values() if r.export_task and not r.export_task.done()]
    for task in tasks: task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    rooms.clear()

app = FastAPI(title='MinAmbiente · Conversación viva', lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=[host.strip() for host in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost,testserver').split(',') if host.strip()])

@app.middleware('http')
async def check_origin(request: Request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and not trusted_origin(request.headers):
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail': 'Origen no permitido'}, status_code=403)
    return await call_next(request)

@app.get('/')
async def operator_page():
    return FileResponse(ROOT / 'static' / 'operator.html')

@app.get('/admin')
async def admin_page():
    return FileResponse(ROOT / 'static' / 'operator.html')

@app.get('/servidor')
async def server_page():
    return FileResponse(ROOT / 'static' / 'server.html')

@app.get('/captura')
async def capture_page():
    return FileResponse(ROOT / 'static' / 'capture.html')

@app.get('/api/sessions/{session}/status')
async def session_status(session: str):
    room = room_for(session)
    return {'capturing': room.producer, 'fragments': len(room.archive), 'viewers': len(room.viewers), 'display': room.display}

class DisplayInput(BaseModel):
    theme: str | None = Field(default=None, pattern='^(light|dark)$')
    view: str | None = Field(default=None, pattern='^(radial|sunburst|flow|particles|field|constellation|stream)$')
    lens: str | None = Field(default=None, pattern='^(manual|agenda|automatic)$')

@app.post('/api/sessions/{session}/display')
async def set_display(session: str, body: DisplayInput):
    room = room_for(session)
    room.display.update(body.model_dump(exclude_none=True))
    await broadcast(room, {'type': 'display', **room.display})
    return room.display

@app.get('/visual')
async def visual_page():
    return FileResponse(ROOT / 'static' / 'visual.html')

@app.get('/api/config')
async def config():
    import importlib.util
    return {'default_stt': os.getenv('DEFAULT_STT', 'local'),
            'deepgram_configured': bool(os.getenv('DEEPGRAM_API_KEY')),
            'local_installed': importlib.util.find_spec('faster_whisper') is not None,
            'deepseek_configured': bool(os.getenv('DEEPSEEK_API_KEY')),
            'concept_provider': os.getenv('CONCEPT_PROVIDER', 'rules'),
            'model': os.getenv('WHISPER_MODEL', 'base'), 'sample_rate': 16000}

@app.post('/api/warmup')
async def warmup():
    try:
        await asyncio.to_thread(get_model)
        return {'ready': True}
    except Exception as exc:
        raise HTTPException(400, 'No se pudo preparar Whisper. Instala requirements-local.txt y verifica la descarga del modelo. ' + (str(exc)[:100] if isinstance(exc, RuntimeError) else '')) from exc

class TextInput(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    speaker: str = Field(default='Texto incorporado', max_length=80)
    id: str | None = Field(default=None, max_length=150)

@app.post('/api/sessions/{session}/text')
async def add_text(session: str, body: TextInput):
    room = room_for(session)
    event = await publish(room, body.text, body.speaker, body.id, room.epoch)
    return {'accepted': event is not None, 'event': event}

@app.get('/api/sessions/{session}/events')
async def get_events(session: str):
    room = room_for(session)
    return {'session': session, 'events': list(room.archive), 'settings': room.settings}


class CategoryInput(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=60)
    color: str = Field(pattern=r'^#[0-9a-fA-F]{6}$')
    keywords: list[str] = Field(default_factory=list, max_length=30)
    origin: str = Field(default='manual', pattern='^(manual|agenda|emergent)$')

class GroupInput(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=60)
    categories: list[str] = Field(default_factory=list, max_length=24)

class SettingsInput(BaseModel):
    categories: list[CategoryInput] = Field(min_length=1, max_length=24)
    agenda: str = Field(default='', max_length=16000)
    emergent: bool = False
    groups: list[GroupInput] = Field(default_factory=list, max_length=3)

@app.get('/api/sessions/{session}/lenses')
async def get_lenses(session: str):
    return lens_snapshots(room_for(session))

@app.get('/api/sessions/{session}/settings')
async def get_settings(session: str):
    return room_for(session).settings

@app.put('/api/sessions/{session}/settings')
async def set_settings(session: str, body: SettingsInput):
    room = room_for(session)
    names = [normalize(c.name.strip()) for c in body.categories]
    if len(set(c.id for c in body.categories)) != len(body.categories) or len(set(names)) != len(names) or not all(names):
        raise HTTPException(400, 'Usa identificadores y nombres únicos y no vacíos.')
    if any(len(k) > 80 for c in body.categories for k in c.keywords):
        raise HTTPException(400, 'Las palabras clave admiten hasta 80 caracteres.')
    valid_ids = {c.id for c in body.categories}
    if len({g.id for g in body.groups}) != len(body.groups) or any(g.id in ('all', 'combined', 'custom') or not g.name.strip() or any(cid not in valid_ids for cid in g.categories) for g in body.groups):
        raise HTTPException(400, 'Los grupos deben tener identificadores únicos y categorías existentes.')
    async with room.lock:
        old = room.settings['categories']
        room.settings = body.model_dump()
        for c in room.settings['categories']: c['name'] = c['name'].strip()
        indices = {c['id']: i for i,c in enumerate(room.settings['categories'])}
        for event in room.events:
            remapped = []
            for concept in event['concepts']:
                cid = old[concept['theme']]['id']
                if cid in indices: remapped.append(dict(concept, theme=indices[cid]))
            event['concepts'] = remapped
            event['categories'] = room.settings['categories']
        await broadcast(room, {'type': 'snapshot', 'settings': room.settings, 'events': list(room.events), 'lenses': lens_snapshots(room), 'display': room.display})
    return room.settings

@app.post('/api/sessions/{session}/infer-categories')
async def infer_categories(session: str, body: SettingsInput):
    room_for(session)
    if not body.agenda.strip(): raise HTTPException(400, 'Pega primero la agenda del evento.')
    try:
        data = await completion('Propón entre 4 y 12 categorías temáticas para esta agenda. '
            'Formato {"categories":[{"name":"...","keywords":["..."]}]}.', {'agenda': body.agenda})
        from uuid import uuid4
        proposed = []
        for item in data['categories'][:12]:
            if not isinstance(item, dict): continue
            name = item.get('name')
            if not isinstance(name, str) or not name.strip(): continue
            if any(normalize(c['name']) == normalize(name.strip()[:60]) for c in proposed): continue
            keywords = item.get('keywords', [])
            proposed.append(dict(id=uuid4().hex, name=name.strip()[:60], color=COLORS[len(proposed)%len(COLORS)],
                keywords=[k[:80] for k in keywords[:30] if isinstance(k,str)] if isinstance(keywords,list) else [], origin='agenda'))
        if not proposed: raise ValueError('Sin categorías')
        return {'categories': proposed}
    except Exception as exc:
        raise HTTPException(502, 'DeepSeek no pudo proponer categorías. Revisa conexión, clave y saldo; tu configuración se conserva.') from exc


@app.post('/api/sessions/{session}/export')
async def start_export(session: str, lens: str = 'manual'):
    if lens not in ('manual', 'agenda', 'automatic'):
        raise HTTPException(400, 'Lectura desconocida')
    room = room_for(session)
    if room.producer:
        raise HTTPException(409, 'Detén la captura y espera el procesamiento pendiente antes de generar el cierre.')
    if room.export_task and not room.export_task.done():
        return room.export_state
    async with room.lock:
        if not room.archive:
            raise HTTPException(400, 'La sesión no contiene intervenciones confirmadas.')
        if room.export_task and not room.export_task.done():
            return room.export_state
        events, settings = deepcopy(room.archive), deepcopy(room.settings)
        if lens != 'manual':
            events = [deepcopy(e['lenses'][lens]) for e in room.archive if lens in e.get('lenses', {})]
            settings = deepcopy(room.lenses[lens]['settings'])
        settings['analysis_lens'] = lens
        settings['lenses'] = {k: deepcopy(v['settings']) for k,v in room.lenses.items()}
        room.export_bytes = None
        room.export_state = {'status': 'running', 'message': 'Preparando el historial completo', 'fragments': len(events), 'lens': lens}
        async def generate():
            from .reports import build_bundle
            def progress(message): room.export_state['message'] = message
            try:
                room.export_bytes, warnings = await build_bundle(session, events, settings, progress)
                room.export_state.update(status='ready', message='Paquete listo para descargar', warnings=warnings)
            except asyncio.CancelledError:
                room.export_state.update(status='error', message='Exportación interrumpida al cerrar el servidor.')
                raise
            except Exception:
                room.export_state.update(status='error', message='No se pudo generar el paquete. Puedes volver a intentarlo; la conversación se conserva.')
        room.export_task = asyncio.create_task(generate())
    return room.export_state

@app.get('/api/sessions/{session}/export/status')
async def export_status(session: str):
    room = room_for(session)
    return room.export_state or {'status': 'idle', 'message': 'No hay una exportación en curso'}

@app.get('/api/sessions/{session}/export/download')
async def export_download(session: str):
    room = room_for(session)
    if not room.export_bytes or not room.export_state or room.export_state['status'] != 'ready':
        raise HTTPException(409, 'El paquete todavía no está listo.')
    return Response(room.export_bytes, media_type='application/zip', headers={
        'Content-Disposition': f'attachment; filename="cierre-{session}.zip"', 'Cache-Control': 'no-store'})

@app.delete('/api/sessions/{session}')
async def reset_session(session: str):
    room = room_for(session)
    room.epoch += 1
    # La época también evita que texto pendiente reaparezca tras el reinicio.
    room.events.clear()
    room.archive.clear()
    for data in room.lenses.values(): data['events'].clear()
    room.lenses['automatic']['settings'].update(categories=[], groups=[])
    room.ids.clear()
    await broadcast(room, {'type': 'reset'})
    return {'reset': True}

@app.websocket('/ws/view/{session}')
async def view_socket(ws: WebSocket, session: str):
    if not trusted_origin(ws.headers):
        await ws.close(1008)
        return
    try:
        room = room_for(session)
    except HTTPException:
        await ws.close(1008)
        return
    await ws.accept()
    # lock evita perder o duplicar eventos entre snapshot y suscripción.
    async with room.lock:
        await ws.send_json({'type': 'snapshot', 'events': list(room.events), 'settings': room.settings, 'lenses': lens_snapshots(room), 'display': room.display})
        room.viewers.add(ws)
    try:
        while True:
            await ws.receive_text()  # ping del navegador, sin cambios de estado.
    except WebSocketDisconnect:
        pass
    finally:
        room.viewers.discard(ws)

async def deepgram_stream(messages, emit, status, partial):
    key = os.getenv('DEEPGRAM_API_KEY')
    if not key:
        raise RuntimeError('Configura DEEPGRAM_API_KEY en .env y reinicia el servidor.')
    params = {'model': os.getenv('DEEPGRAM_MODEL', 'nova-3'), 'language': 'es',
              'encoding': 'linear16', 'sample_rate': 16000, 'channels': 1,
              'interim_results': 'true', 'smart_format': 'true', 'punctuate': 'true',
              'endpointing': 500}
    url = 'wss://api.deepgram.com/v1/listen?' + urlencode(params)
    async with websockets.connect(url, additional_headers={'Authorization': f'Token {key}'},
                                  open_timeout=20, max_size=2**20) as upstream:
        async def results():
            async for raw in upstream:
                event = json.loads(raw)
                if event.get('type') == 'Error':
                    raise RuntimeError('Deepgram rechazó la transcripción. Revisa el modelo, la clave y el saldo.')
                if event.get('type') != 'Results':
                    continue
                text = event.get('channel', {}).get('alternatives', [{}])[0].get('transcript', '').strip()
                if not text:
                    continue
                if event.get('is_final'):
                    await emit(text, f"dg-{event.get('start')}-{event.get('duration')}")
                    await partial('')
                else:
                    await partial(text)
        receiver = asyncio.create_task(results())
        try:
            await status('ready')
            async for pcm in messages:
                if receiver.done():
                    await receiver
                    raise RuntimeError('La conexión de Deepgram terminó durante la captura.')
                await upstream.send(pcm)
            await upstream.send(json.dumps({'type': 'CloseStream'}))
            await asyncio.wait_for(receiver, timeout=20)
        finally:
            if not receiver.done():
                receiver.cancel()
            await asyncio.gather(receiver, return_exceptions=True)

@app.websocket('/ws/audio/{session}')
async def audio_socket(ws: WebSocket, session: str):
    if not trusted_origin(ws.headers):
        await ws.close(1008)
        return
    try:
        room = room_for(session)
    except HTTPException:
        await ws.close(1008)
        return
    await ws.accept()
    if room.producer:
        await ws.send_json({'type': 'error', 'message': 'Esta sesión ya tiene una captura activa.'})
        await ws.close()
        return
    room.producer = True
    socket_lock = asyncio.Lock()
    transcript_queue = asyncio.Queue(maxsize=30)
    capture_id = uuid4().hex
    count = 0

    async def control(data):
        async with socket_lock:
            with suppress(WebSocketDisconnect, RuntimeError):
                await ws.send_json(data)

    async def status(message):
        await control({'type': 'ready' if message == 'ready' else 'status', 'message': message})

    async def partial(text):
        await control({'type': 'partial', 'text': text})

    async def emit(text, item_id):
        nonlocal count
        count += 1
        try:
            transcript_queue.put_nowait((text, capture_id + '-' + item_id, room.epoch))
        except asyncio.QueueFull as exc:
            raise RuntimeError('El análisis de conceptos está retrasado. Detén la captura y prueba el modo rules.') from exc
        await control({'type': 'transcript', 'text': text, 'count': count})

    async def process_text():
        while True:
            item = await transcript_queue.get()
            try:
                if item is None:
                    return
                text, event_id, epoch = item
                await publish(room, text, 'Audio de la conversación', event_id, epoch)
                await control({'type': 'published', 'pending': transcript_queue.qsize()})
            finally:
                transcript_queue.task_done()

    async def messages():
        while True:
            message = await ws.receive()
            if message['type'] == 'websocket.disconnect':
                break
            if worker.done():
                await worker
            if message.get('bytes') is not None:
                pcm = message['bytes']
                if len(pcm) > 64000 or len(pcm) % 2:
                    raise ValueError('Bloque PCM inválido')
                yield pcm
            elif message.get('text'):
                data = json.loads(message['text'])
                if data.get('type') == 'stop':
                    break

    worker = asyncio.create_task(process_text())
    try:
        start = await asyncio.wait_for(ws.receive_json(), timeout=20)
        provider = start.get('provider', os.getenv('DEFAULT_STT', 'local'))
        if start.get('sample_rate') != 16000 or provider not in ('local', 'deepgram'):
            raise ValueError('Configura audio PCM16 mono a 16000 Hz y un proveedor válido.')
        if provider == 'deepgram':
            await deepgram_stream(messages(), emit, status, partial)
        else:
            await local_stream(messages(), emit, status)
        # Espera los conceptos pendientes antes de confirmar el fin.
        await transcript_queue.put(None)
        await worker
        await control({'type': 'stopped', 'message': 'Captura detenida. Texto pendiente incorporado.'})
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as exc:
        # No expone URLs con credenciales ni el contenido de respuestas remotas.
        allowed = (RuntimeError, ValueError)
        message = str(exc)[:240] if isinstance(exc, allowed) else 'No fue posible completar la captura. Revisa la consola del servidor y la configuración.'
        await control({'type': 'error', 'message': message})
    finally:
        room.producer = False
        if not worker.done():
            worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)
        with suppress(Exception):
            await ws.close()

app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')

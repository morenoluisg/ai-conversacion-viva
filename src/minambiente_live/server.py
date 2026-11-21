"""Puente local de audio, transcripción y estado para Conversación viva."""
import asyncio
from copy import deepcopy
from collections import OrderedDict, deque
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlencode, urlsplit
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
import websockets

load_dotenv(Path(os.getenv('MINAMBIENTE_ENV_FILE', Path.cwd() / '.env')))
from .audio import local_stream, get_model
from .concepts import extract
from .categories import defaults, analyze, fallback, completion, COLORS, normalize, agenda_profile, autonomous
from .branding import Branding, initial_branding, environmental_branding
ROOT = Path(__file__).parent

class Room:
    def __init__(self):
        self.branding = initial_branding()
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
        self.analysis_task = None
        self.analysis_cursor = 0
        self.settings_revision = 0
        self.analysis_seconds = 0.0
        self.analysis_failures = 0

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

def analysis_status(room):
    return {'pending': max(0, len(room.archive)-room.analysis_cursor),
            'last_seconds': round(room.analysis_seconds, 3), 'failures': room.analysis_failures}


def provisional(room, text, lens):
    config = deepcopy(room.settings if lens == 'manual' else room.lenses[lens]['settings'])
    method = 'rules' if lens != 'automatic' and os.getenv('CONCEPT_PROVIDER', 'rules') == 'rules' else 'analysis-pending'
    return fallback(text, config['categories']), config, method


async def analysis_worker(room, epoch):
    # One task per room; the archive is the backlog, rather than an audio-owned queue.
    while epoch == room.epoch and room.analysis_cursor < len(room.archive):
        event = room.archive[room.analysis_cursor]
        revision = room.settings_revision
        started = time.monotonic()
        async def safe_classify(lens):
            try:
                return await asyncio.wait_for(classify(room, event['text'], lens), timeout=10)
            except Exception:
                cs, config, _ = provisional(room, event['text'], lens)
                return cs, config, 'deepseek-auto-unavailable' if lens == 'automatic' else 'rules-fallback'
        results = await asyncio.gather(*(safe_classify(lens) for lens in ('manual', 'agenda', 'automatic')))
        async with room.lock:
            if epoch != room.epoch:
                return
            for lens, (concepts, config, method) in zip(('manual', 'agenda', 'automatic'), results):
                if lens == 'manual' and revision != room.settings_revision:
                    concepts, config, method = provisional(room, event['text'], lens)
                    method = 'rules-fallback'
                item = dict(id=event['id'], text=event['text'], speaker=event['speaker'], at=event['at'],
                            concepts=concepts, categories=deepcopy(config['categories']), method=method)
                if lens == 'manual':
                    room.settings = config
                    event.update(item)
                else:
                    room.lenses[lens]['settings'] = config
                    item['settings'] = deepcopy(config)
                    event['lenses'][lens] = item
                    recent = room.lenses[lens]['events']
                    for i, previous in enumerate(recent):
                        if previous['id'] == event['id']:
                            recent[i] = deepcopy(item)
                            break
            event['analysis_pending'] = False
            for i, previous in enumerate(room.events):
                if previous['id'] == event['id']:
                    room.events[i] = deepcopy(event)
                    break
            room.analysis_cursor += 1
            room.analysis_seconds = time.monotonic()-started
            if any(method.endswith('unavailable') or method == 'rules-fallback' for _, _, method in results):
                room.analysis_failures += 1
            await broadcast(room, {'type': 'event_update', 'event': deepcopy(event), 'analysis': analysis_status(room)})


async def publish(room, text, speaker='Conversación', event_id=None, epoch=None, wait_analysis=True):
    text = text.strip()[:4000]
    if not text:
        return None
    event_id = event_id or str(uuid4())
    async with room.lock:
        if event_id in room.ids or (epoch is not None and epoch != room.epoch):
            return None
        stamp = datetime.now(timezone.utc).isoformat()
        alternatives = {}
        for lens in ('agenda', 'automatic'):
            cs, config, method = provisional(room, text, lens)
            item = dict(id=event_id, text=text, speaker=speaker, at=stamp, concepts=cs,
                        method=method, categories=deepcopy(config['categories']), settings=config)
            room.lenses[lens]['events'].append(deepcopy(item))
            alternatives[lens] = item
        cs, config, method = provisional(room, text, 'manual')
        event = dict(id=event_id, text=text, speaker=speaker, at=stamp, concepts=cs, method=method,
                     categories=config['categories'], lenses=alternatives, analysis_pending=True)
        room.ids.append(event_id)
        room.events.append(deepcopy(event))
        room.archive.append(event)
        if room.analysis_task is None or room.analysis_task.done():
            room.analysis_task = asyncio.create_task(analysis_worker(room, room.epoch))
        await broadcast(room, {'type': 'event', 'event': deepcopy(event), 'analysis': analysis_status(room)})
    if wait_analysis:
        await asyncio.shield(room.analysis_task)
    return event

@asynccontextmanager
async def lifespan(app):
    yield
    tasks = [task for r in rooms.values() for task in (r.export_task, r.analysis_task) if task and not task.done()]
    for task in tasks: task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    rooms.clear()

app = FastAPI(title=initial_branding()['app_name'], lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=[host.strip() for host in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost,testserver').split(',') if host.strip()])

@app.middleware('http')
async def check_origin(request: Request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and not trusted_origin(request.headers):
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail': 'Origen no permitido'}, status_code=403)
    return await call_next(request)

@app.get('/')
async def operator_page(session: str | None = None):
    return branded_page('operator.html', session)

@app.get('/admin')
async def admin_page(session: str | None = None):
    return branded_page('operator.html', session)

@app.get('/servidor')
async def server_page(session: str | None = None):
    return branded_page('server.html', session)

@app.get('/captura')
async def capture_page(session: str | None = None):
    return branded_page('capture.html', session)


def branded_page(filename, session=None):
    branding = room_for(session).branding if session else initial_branding()
    content = (ROOT / 'static' / filename).read_text(encoding='utf-8')
    content = re.sub(r'<title>.*?</title>', lambda _: '<title>' + escape(branding['app_name']) + '</title>', content, count=1)
    encoded = json.dumps(branding, ensure_ascii=False).replace('<', '\\u003c')
    scripts = '<link rel="stylesheet" href="/static/branding.css"><script id="appBranding" type="application/json">' + encoded + '</script><script src="/static/branding.js"></script>'
    content = content.replace('<script', scripts + '<script', 1)
    return HTMLResponse(content, headers={'Cache-Control': 'no-store'})


@app.get('/api/sessions/{session}/branding')
async def get_branding(session: str):
    return {'current': room_for(session).branding, 'defaults': initial_branding(), 'environmental': environmental_branding()}


@app.put('/api/sessions/{session}/branding')
async def set_branding(session: str, body: Branding):
    room = room_for(session)
    async with room.lock:
        room.branding = body.model_dump()
        await broadcast(room, {'type': 'branding', 'branding': room.branding})
    return room.branding

@app.get('/api/sessions/{session}/status')
async def session_status(session: str):
    room = room_for(session)
    return {'capturing': room.producer, 'fragments': len(room.archive), 'viewers': len(room.viewers), 'display': room.display, 'analysis': analysis_status(room)}

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
async def visual_page(session: str | None = None):
    return branded_page('visual.html', session)

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
    event = await publish(room, body.text, body.speaker, body.id, room.epoch, wait_analysis=False)
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
        room.settings_revision += 1
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
    if room.producer or analysis_status(room)['pending']:
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
        settings['branding'] = deepcopy(room.branding)
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
    if room.analysis_task and not room.analysis_task.done():
        room.analysis_task.cancel()
        await asyncio.gather(room.analysis_task, return_exceptions=True)
    room.analysis_task = None
    room.analysis_cursor = 0
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
        await ws.send_json({'type': 'snapshot', 'events': list(room.events), 'settings': room.settings, 'lenses': lens_snapshots(room), 'display': room.display, 'branding': room.branding})
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
        event = await publish(room, text, 'Audio de la conversación', capture_id + '-' + item_id, room.epoch, wait_analysis=False)
        if event is not None:
            await control({'type': 'transcript', 'text': text, 'count': count})
            await control({'type': 'published', 'pending': analysis_status(room)['pending']})

    async def messages():
        while True:
            message = await ws.receive()
            if message['type'] == 'websocket.disconnect':
                break
            if message.get('bytes') is not None:
                pcm = message['bytes']
                if len(pcm) > 64000 or len(pcm) % 2:
                    raise ValueError('Bloque PCM inválido')
                yield pcm
            elif message.get('text'):
                data = json.loads(message['text'])
                if data.get('type') == 'stop':
                    break

    try:
        start = await asyncio.wait_for(ws.receive_json(), timeout=20)
        provider = start.get('provider', os.getenv('DEFAULT_STT', 'local'))
        if start.get('sample_rate') != 16000 or provider not in ('local', 'deepgram'):
            raise ValueError('Configura audio PCM16 mono a 16000 Hz y un proveedor válido.')
        if provider == 'deepgram':
            await deepgram_stream(messages(), emit, status, partial)
        else:
            await local_stream(messages(), emit, status)
        await control({'type': 'stopped', 'message': 'Captura detenida. Transcripciones guardadas; los temas pendientes continúan en segundo plano.', 'analysis': analysis_status(room)})
    except (WebSocketDisconnect, asyncio.CancelledError):
        pass
    except Exception as exc:
        # No expone URLs con credenciales ni el contenido de respuestas remotas.
        allowed = (RuntimeError, ValueError)
        message = str(exc)[:240] if isinstance(exc, allowed) else 'No fue posible completar la captura. Revisa la consola del servidor y la configuración.'
        await control({'type': 'error', 'message': message})
    finally:
        room.producer = False
        with suppress(Exception):
            await ws.close()

app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')

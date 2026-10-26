"""Puente local de audio, transcripción y estado para Conversación viva."""
import asyncio
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
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware
import websockets

load_dotenv(Path(os.getenv('MINAMBIENTE_ENV_FILE', Path.cwd() / '.env')))
from .audio import local_stream, get_model
from .concepts import extract
ROOT = Path(__file__).parent

class Room:
    def __init__(self):
        self.events = deque(maxlen=150)
        self.ids = deque(maxlen=1000)
        self.viewers = set()
        self.lock = asyncio.Lock()
        self.producer = False
        self.epoch = 0

rooms = OrderedDict()

def room_for(session):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', session):
        raise HTTPException(400, 'Identificador de sesión inválido')
    if session not in rooms:
        if len(rooms) >= 20:
            removable = next((k for k, r in rooms.items() if not r.producer and not r.viewers), None)
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

async def publish(room, text, speaker='Conversación', event_id=None, epoch=None):
    text = text.strip()[:4000]
    if not text:
        return None
    event_id = event_id or str(uuid4())
    async with room.lock:
        if event_id in room.ids or (epoch is not None and epoch != room.epoch):
            return None
        concepts, method = await extract(text)
        # Si la extracción tardó mientras el usuario vaciaba el mapa, se descarta.
        if epoch is not None and epoch != room.epoch:
            return None
        event = {'id': event_id, 'text': text, 'speaker': speaker,
                 'concepts': concepts, 'method': method,
                 'at': datetime.now(timezone.utc).isoformat()}
        room.ids.append(event_id)
        room.events.append(event)
        await broadcast(room, {'type': 'event', 'event': event})
        return event

@asynccontextmanager
async def lifespan(app):
    yield
    rooms.clear()

app = FastAPI(title='MinAmbiente · Conversación viva', lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])

@app.middleware('http')
async def check_origin(request: Request, call_next):
    if request.method not in ('GET', 'HEAD', 'OPTIONS') and not trusted_origin(request.headers):
        from fastapi.responses import JSONResponse
        return JSONResponse({'detail': 'Origen no permitido'}, status_code=403)
    return await call_next(request)

@app.get('/')
async def operator_page():
    return FileResponse(ROOT / 'static' / 'operator.html')

@app.get('/visual')
async def visual_page():
    return FileResponse(ROOT / 'static' / 'visual.html')

@app.get('/api/config')
async def config():
    import importlib.util
    return {'default_stt': os.getenv('DEFAULT_STT', 'local'),
            'deepgram_configured': bool(os.getenv('DEEPGRAM_API_KEY')),
            'local_installed': importlib.util.find_spec('faster_whisper') is not None,
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
    return {'session': session, 'events': list(room.events)}

@app.delete('/api/sessions/{session}')
async def reset_session(session: str):
    room = room_for(session)
    room.epoch += 1
    # La época también evita que texto pendiente reaparezca tras el reinicio.
    room.events.clear()
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
        await ws.send_json({'type': 'snapshot', 'events': list(room.events)})
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

"""Audio PCM mono 16 kHz. Bloques locales con solape y descarte por tiempo."""
import asyncio
import os
import threading
import numpy as np

RATE = 16000
MODEL = None
MODEL_LOCK = threading.Lock()
INFERENCE_LOCK = threading.Lock()

def get_model():
    global MODEL
    with MODEL_LOCK:
        if MODEL is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError('Instala requirements-local.txt para usar Whisper local.') from exc
            MODEL = WhisperModel(os.getenv('WHISPER_MODEL', 'base'),
                                 device=os.getenv('WHISPER_DEVICE', 'cpu'),
                                 compute_type=os.getenv('WHISPER_COMPUTE_TYPE', 'int8'))
    return MODEL

class PCMChunks:
    def __init__(self, seconds=6, overlap=1):
        if not 2 <= seconds <= 20 or not 0 <= overlap < seconds:
            raise ValueError('Tamaño de bloque o solape inválido')
        self.size = int(seconds * RATE) * 2
        self.step = int((seconds - overlap) * RATE) * 2
        self.data = bytearray()
        self.offset = 0
        self.received = 0
        self.last_emitted_end = 0

    def feed(self, data):
        if len(data) % 2:
            raise ValueError('PCM16 debe contener muestras completas')
        self.data.extend(data)
        self.received += len(data)
        out = []
        while len(self.data) >= self.size:
            out.append((bytes(self.data[:self.size]), self.offset / (RATE * 2)))
            self.last_emitted_end = self.offset + self.size
            del self.data[:self.step]
            self.offset += self.step
        return out

    def finish(self):
        # Si solo queda el solape ya procesado, no lo transcribe de nuevo.
        new_bytes = self.received - self.last_emitted_end
        if new_bytes >= int(.25 * RATE) * 2:
            item = (bytes(self.data), self.offset / (RATE * 2))
            self.data.clear()
            self.last_emitted_end = self.received
            return [item]
        return []

class LocalTranscriber:
    def __init__(self, model):
        self.model = model
        self.committed_end = -1.0

    def transcribe(self, pcm, offset):
        audio = np.frombuffer(pcm, dtype='<i2').astype(np.float32) / 32768.0
        if len(audio) < RATE * .25 or np.sqrt(np.mean(audio * audio)) < .0006:
            return ''
        with INFERENCE_LOCK:
            segments, _ = self.model.transcribe(audio, language='es', beam_size=1,
                vad_filter=True, word_timestamps=True, condition_on_previous_text=False)
            words = []
            for segment in segments:
                if getattr(segment, 'no_speech_prob', 0) > .85:
                    continue
                for word in segment.words or []:
                    end = offset + word.end
                    if end > self.committed_end + .04:
                        words.append(word.word)
                        self.committed_end = max(self.committed_end, end)
            return ''.join(words).strip()

async def local_stream(messages, emit, status, model=None):
    if model is None:
        await status('Cargando Whisper. La primera vez descarga el modelo; puede tardar varios minutos.')
        model = await asyncio.to_thread(get_model)
    await status('ready')
    chunks = PCMChunks(float(os.getenv('AUDIO_CHUNK_SECONDS', '6')),
                       float(os.getenv('AUDIO_OVERLAP_SECONDS', '1')))
    transcriber = LocalTranscriber(model)
    queue = asyncio.Queue(maxsize=6)

    async def consume():
        while True:
            item = await queue.get()
            if item is None:
                break
            pcm, offset = item
            text = await asyncio.to_thread(transcriber.transcribe, pcm, offset)
            if text:
                await emit(text, f'local-{offset:.3f}')
            await status(f'Procesado hasta {offset + len(pcm)/(RATE*2):.1f} s de audio')

    worker = asyncio.create_task(consume())

    async def put_guarded(item):
        pending = asyncio.create_task(queue.put(item))
        done, _ = await asyncio.wait({pending, worker}, return_when=asyncio.FIRST_COMPLETED)
        if worker in done:
            if not pending.done():
                pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)
            await worker
            if item is None:
                return
            raise RuntimeError('El procesador de audio terminó antes de vaciar la cola.')
        await pending

    try:
        async for pcm in messages:
            if worker.done():
                await worker
            for item in chunks.feed(pcm):
                try:
                    queue.put_nowait(item)
                except asyncio.QueueFull as exc:
                    raise RuntimeError('Whisper no alcanza el ritmo del audio. Prueba un modelo menor o Deepgram.') from exc
        for item in chunks.finish():
            await put_guarded(item)
        await put_guarded(None)
        await worker
    finally:
        if not worker.done():
            worker.cancel()
        await asyncio.gather(worker, return_exceptions=True)

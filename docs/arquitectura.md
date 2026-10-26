# Arquitectura

## Flujo de datos

1. El operador selecciona micrófono, pestaña o pantalla desde el navegador.
2. Web Audio mezcla únicamente las pistas de audio. El AudioWorklet convierte la señal a PCM16 mono de 16 kHz.
3. El navegador envía bloques binarios al WebSocket de audio del servidor local.
4. Faster-Whisper procesa bloques con solape, o Deepgram devuelve fragmentos finales de su streaming. Los parciales no modifican el mapa.
5. El servidor extrae conceptos con reglas u Ollama y distribuye eventos confirmados a los suscriptores de la sesión.
6. La pantalla proyectada actualiza el estado de las seis vistas. El panel puede cambiar de vista a través de BroadcastChannel, en el mismo navegador y origen.

El audio compartido de una pestaña no necesariamente incluye el micrófono propio. Por eso el panel permite sumar esa entrada. El video requerido por el selector de pantalla no se envía al servidor.

## API

| Ruta | Protocolo | Función |
|---|---|---|
| `/` | HTTP GET | Panel del operador |
| `/visual?live=1&session=ID` | HTTP GET | Pantalla de la sesión en vivo |
| `/visual` | HTTP GET | Demostración simulada |
| `/api/config` | HTTP GET | Estado de proveedores sin exponer claves |
| `/api/warmup` | HTTP POST | Preparar el modelo local sin abrir el micrófono |
| `/api/sessions/ID/text` | HTTP POST | Incorporar un fragmento confirmado de otra fuente |
| `/api/sessions/ID/events` | HTTP GET | Exportar la ventana de eventos |
| `/api/sessions/ID` | HTTP DELETE | Vaciar la sesión |
| `/ws/audio/ID` | WebSocket | Recibir PCM y devolver estados de la captura |
| `/ws/view/ID` | WebSocket | Snapshot inicial, eventos y reinicio |

## Mensajes

El primer mensaje al WebSocket de audio es JSON:

```json
{"provider":"local","sample_rate":16000}
```

Después recibe PCM16 mono little-endian en bloques binarios. El mensaje `{"type":"stop"}` termina la entrada y vacía el último fragmento antes de confirmar `stopped`.

La fuente de texto externa envía:

```json
{"id":"fragmento-001","text":"Las comunidades cuidan las cuencas.","speaker":"Ponente"}
```

Usa un ID único por fragmento. Se deduplican reintentos recientes. El servidor incorpora conceptos y método de extracción antes de distribuir el evento.

## Estado y ejecución

- Una captura activa por sesión, hasta veinte sesiones locales.
- Una ventana de 150 eventos en memoria. El cliente retira las contribuciones antiguas al actualizar el mapa.
- Colas de audio y de conceptos acotadas para detectar retrasos.
- El reinicio de sesión invalida texto anterior todavía pendiente de extracción.
- El proceso usa un solo worker. No añadas múltiples workers con el almacenamiento actual en memoria.
- `.env` se carga desde el directorio de ejecución, normalmente la raíz del repositorio. `MINAMBIENTE_ENV_FILE` permite indicar otro archivo.
- Las claves permanecen en el servidor. No se guarda una grabación de audio en disco.

## Evolución prevista

Para desplegarlo fuera del computador del operador harían falta una revisión de autenticación, HTTPS, almacenamiento compartido y distribución de sesiones. La captura de audio del navegador requiere un origen seguro, como HTTPS o localhost. Este repositorio conserva el alcance local de la demostración.

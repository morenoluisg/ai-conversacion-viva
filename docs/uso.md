# Conversación viva: audio de Teams y del computador

Componente local para alimentar las seis vistas de la presentación con texto confirmado de una conversación. Conserva el mapa radial, anillos, evolución temática, Colombia en puntos, corrientes y constelaciones.

## Para probar hoy en Windows

1. Instala Python 3.11 o 3.12 desde python.org, con el lanzador `py` y acceso a pip.
2. Extrae TODO el ZIP en una carpeta local. No ejecutes los archivos dentro del ZIP.
3. Ejecuta `setup_windows.bat`. Instala la aplicación y Faster-Whisper. Solo hace falta la primera vez.
4. Ejecuta `iniciar_windows.bat`. Mantén abierta la consola. Si la página aparece antes de que arranque el servidor, recárgala después de ver `Uvicorn running`.
5. Abre **http://127.0.0.1:8765** en Chrome o Edge.
6. Pulsa **Preparar Whisper local**. La primera vez descarga el modelo `base`, puede tardar varios minutos y necesita Internet. Después el modelo queda en la caché del equipo.
7. Abre la visualización con el botón del panel y muévela a la segunda pantalla.
8. Primero prueba **Micrófono**, pulsa **Iniciar captura** y espera la confirmación. Di: “Vamos a proteger el agua y restaurar los bosques con participación de las comunidades”.
9. Comprueba el medidor, el texto confirmado y los conceptos. Pulsa **Detener** para procesar también el último fragmento corto.

La sesión arranca vacía en modo en vivo. La demostración ficticia solo aparece al abrir `/visual` sin `?live=1`.

## Teams en el navegador: ruta recomendada para empezar

- Abre la reunión en otra pestaña **del mismo navegador**.
- En el panel, elige **Teams web · audio de una pestaña**.
- Deja **Sumar mi micrófono** marcado si quieres incluir tu voz. El audio de la pestaña suele aportar las voces de las otras personas, no la señal saliente de tu micrófono.
- Pulsa Iniciar captura. En el selector del navegador elige la pestaña de Teams y marca **Compartir audio de la pestaña**.
- Usa auriculares. Así el micrófono no vuelve a recoger el audio que ya llega desde Teams.
- Espera el aviso de captura lista y comprueba el medidor. No cierres la pestaña del panel mientras dure la charla.

Esta captura no se incorpora a la llamada: solo alimenta la transcripción y la visualización local. No necesitas instalar un bot en Teams ni dar permisos de Microsoft Graph a la aplicación.

## Teams en la aplicación de escritorio

En Windows, abre el panel en Chrome o Edge, elige **Teams de escritorio · audio del sistema**, y en el selector prueba **Pantalla completa** con **Compartir audio del sistema** activado.

El soporte depende del navegador, sistema operativo, políticas del equipo y superficie seleccionada. Seleccionar solamente una ventana no garantiza que llegue audio. La aplicación detecta si la fuente carece de pista de audio y te pide corregir la selección.

Si no aparece la opción de audio, la salida más simple es pasar la reunión a Teams web. Otra opción es un dispositivo de loopback ya configurado (Mezcla estéreo o un cable virtual) y seleccionarlo como entrada de micrófono del navegador. Este proyecto no instala ni configura controladores de audio. En macOS y Linux empieza por Teams web.

El navegador exige seleccionar una superficie de video para `getDisplayMedia`. El componente usa únicamente las pistas de audio: **no envía cuadros de pantalla al servidor ni graba video**. La pista de pantalla permanece abierta hasta Detener para mantener la captura y detectar cuando el usuario termina de compartir.

## Conversación presencial

Elige Micrófono y usa una entrada USB o una salida de la consola del salón conectada como dispositivo de entrada. Ajusta el micrófono predeterminado en el sistema o en los permisos del navegador antes de iniciar. Un micrófono lejano captura peor que una salida directa del sonido del evento.

## Transcripción: local o Deepgram

### Whisper local, configurado de inicio

No necesita una clave ni paga por minuto. Procesa bloques de 6 segundos con 1 segundo de solape. El tiempo de respuesta suma el bloque y la inferencia: depende del computador y no equivale a subtítulos instantáneos. Los timestamps de las palabras evitan volver a incorporar el solape.

`.env` permite elegir `WHISPER_MODEL=base` o `small`, `WHISPER_DEVICE=cpu` y `WHISPER_COMPUTE_TYPE=int8`. Un modelo mayor puede reconocer mejor y tardar más. Si el computador no alcanza el ritmo, el panel avisa y detiene la captura en vez de acumular audio indefinidamente. Las colas son acotadas.

Para preparar el modelo desde consola, sin abrir el micrófono:

```powershell
.venv\Scripts\python.exe -m minambiente_live --prepare-model
```

La opción CUDA requiere configurar las bibliotecas compatibles de CTranslate2/cuDNN, siguiendo la documentación de Faster-Whisper. La configuración inicial usa CPU para facilitar la prueba en Windows.

### Deepgram, para streaming por API

1. Crea tu clave en Deepgram y habilita su servicio de voz.
2. Edita el archivo `.env`, creado al instalar:

```dotenv
DEEPGRAM_API_KEY=tu_clave
DEEPGRAM_MODEL=nova-3
DEFAULT_STT=deepgram
```

3. Reinicia el servidor y selecciona Deepgram en el panel.

El servidor envía PCM16 mono a 16 kHz por WebSocket al servicio y recibe español. El texto parcial solo aparece en el panel. El mapa recibe resultados confirmados (`is_final`) y conserva el orden de llegada. Los fragmentos confirmados pendientes se procesan al detener.

**Deepgram recibe el audio y factura el uso según tu plan.** La clave permanece en `.env` del servidor. Nunca se envía al HTML ni se incluye en la exportación. Para usar solo Deepgram puedes instalar únicamente `requirements.txt`, sin `requirements-local.txt`.

## Conceptos: reglas ahora, Ollama opcional

El arranque usa `CONCEPT_PROVIDER=rules`: un vocabulario ambiental que detecta cuencas, bosques, biodiversidad, clima, participación, datos e IA, entre otros. Esto permite probar el circuito sin otro modelo, pero no es una comprensión general de cualquier charla.

Para extraer conceptos con un LLM local, puedes usar tu instalación de Ollama:

```powershell
ollama pull qwen2.5:3b
```

Luego edita `.env` y reinicia:

```dotenv
CONCEPT_PROVIDER=ollama
OLLAMA_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:3b
OLLAMA_TIMEOUT=8
```

Puedes usar otro modelo que ya tengas instalado. El modelo devuelve conceptos con una evidencia literal del fragmento. Las respuestas se validan y, si Ollama falla o supera el tiempo de espera, el componente usa reglas de respaldo y lo identifica como `rules-fallback`.

Las seis familias temáticas se conservan para que los colores mantengan el mismo significado en todas las vistas. La extracción semántica no atribuye acuerdos oficiales ni identifica personas. Las voces mezcladas no se separan por hablante: los fragmentos llevan “Audio de la conversación”.

## Alimentar texto de otra fuente

Si ya obtienes una transcripción desde un sistema propio, puedes omitir la captura de audio. El panel muestra la sesión y el endpoint exactos. Envía una petición por fragmento confirmado y usa un `id` único para poder reintentar sin duplicarlo.

Ejemplo PowerShell, sustituyendo la sesión por la que muestra tu panel:

```powershell
$sessionId = "charla-XXXXXXXX"
$payload = @{
  id = "fragmento-001"
  text = "Las comunidades participan en el monitoreo de las cuencas."
  speaker = "Ponente"
} | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8765/api/sessions/$sessionId/text" `
  -ContentType "application/json; charset=utf-8" `
  -Body ([System.Text.Encoding]::UTF8.GetBytes($payload))
```

La visualización recibe automáticamente el evento mediante `/ws/view/{session}`. Puedes cambiar la vista desde el panel sin tocar la pantalla proyectada. El servidor y las dos pestañas deben estar en el mismo equipo y origen (no mezcles `localhost` con `127.0.0.1`).

## Transcripción y análisis en segundo plano

La transcripción confirmada se guarda en el historial en memoria y se muestra inmediatamente. DeepSeek procesa los temas en una tarea separada: una respuesta lenta o fallida no detiene la captura. Los conceptos provisionales usan las categorías existentes; en la lectura automática inicial puede aparecer texto mientras se espera la primera clasificación.

El panel muestra los fragmentos con temas pendientes y el tiempo del último análisis. El servidor limita cada clasificación en vivo a diez segundos y conserva el texto ante errores. Las actualizaciones reemplazan los conceptos del mismo fragmento, sin duplicar transcripciones ni menciones. El río conserva su animación y su posición de revisión temporal al recibirlas.

Al detener el audio, el texto ya está incorporado y los temas pendientes continúan procesándose. Espera a que el indicador vuelva a cero antes de generar el cierre. Vaciar una sesión cancela su análisis pendiente y evita que reaparezcan fragmentos anteriores. El historial sigue siendo temporal: exporta la conversación antes de cerrar el servidor.

La API `POST /api/sessions/{session}/text` confirma la incorporación sin esperar al modelo. Los clientes de `/ws/view/{session}` reciben `event` para el fragmento inicial y `event_update` con el mismo identificador para actualizar su clasificación. `/api/sessions/{session}/status` incluye `analysis.pending`, `analysis.last_seconds` y `analysis.failures`.

## Identidad para otros eventos

Abre **Identidad y presentación** en el panel de administración. Puedes configurar el nombre de la aplicación, la organización o evento, la descripción, las dos líneas del centro del mapa radial, el encabezado del panel de texto y el color de identidad. La vista previa muestra el borrador; **Aplicar identidad a la sesión** lo envía a los tableros abiertos. Los nuevos informes también incluyen esta identidad. Los conceptos y categorías conservan sus colores propios.

Los cambios del panel duran durante la sesión en memoria del servidor. Para conservar valores entre reinicios, edita las variables `APP_*` del `.env` y reinicia la aplicación. **Cargar valores del .env** y **Cargar ejemplo ambiental** solo rellenan el formulario; pulsa **Aplicar** para publicarlos en la sesión.

Ejemplo para un encuentro educativo:

```dotenv
APP_NAME="Diálogos de aprendizaje"
APP_ORGANIZATION="Encuentro de educación"
APP_DESCRIPTION="Ideas para aprender juntos"
APP_CENTER_TOP="DIÁLOGO"
APP_CENTER_BOTTOM="EDUCATIVO"
APP_PANEL_HEADING="Ideas que estamos compartiendo"
APP_ACCENT_COLOR="#6438ab"
```

La identidad se configura por sesión: cambiarla en una sesión no modifica las demás. Los valores de `.env` son el punto de partida para las sesiones nuevas. La demostración ambiental y sus categorías siguen disponibles por separado de la identidad. Las páginas estáticas de demostración en `docs/` conservan el ejemplo original.

## Proyectar el gráfico con el texto

En la pantalla de visualización, **F** activa o desactiva la pantalla completa y **H** oculta o recupera los controles. Pulsa **K** para mostrar u ocultar el panel de texto de la conversación, incluso con los controles ocultos. También puedes usar el botón **Mostrar/Ocultar texto (K)**.

Para proyectar el gráfico junto al texto, pulsa **F**, después **H** y luego **K**. El panel muestra las nuevas intervenciones y conserva su visibilidad al cambiar entre las siete vistas. Una segunda pulsación de **K** lo oculta. Los atajos no se activan mientras escribes en un campo.

## Arquitectura y archivos

| Componente | Archivo | Función |
|---|---|---|
| Captura y mezcla | `src/minambiente_live/static/operator.js` | Micrófono y/o audio compartido, control y medidor |
| Conversión de audio | `src/minambiente_live/static/audio-worklet.js` | Conversión continua a PCM16 mono a 16 kHz |
| Servidor local | `src/minambiente_live/server.py` | Transcripción, extracción y distribución de eventos |
| Voz local | `src/minambiente_live/audio.py` | Bloques con solape, VAD y timestamps |
| Conceptos | `src/minambiente_live/concepts.py` | Vocabulario inicial y extracción opcional con Ollama |
| Pantalla proyectada | `src/minambiente_live/static/visual.html` | Las seis vistas y suscripción a la sesión |

El servidor escucha únicamente en `127.0.0.1:8765`. No es un despliegue público. Conserva hasta 150 fragmentos por sesión en memoria, con hasta 20 sesiones locales. La visualización recalcula las contribuciones al retirar un fragmento antiguo. La exportación JSON contiene esa ventana de conversación, no una grabación completa del evento. Exporta lo que necesites antes de reiniciar el servidor. Las transcripciones se pierden al cerrar el proceso, salvo que las exportes.

El botón Vaciar sesión limpia el mapa de esa sesión; permanece desactivado durante la captura. No guarda audios en disco. Informa a los participantes de que se transcribirá la conversación y elige el proveedor apropiado para el contenido que vas a tratar.

## Verificación y límites prácticos

Incluye pruebas de muestreo, PCM, fragmento final, solape, silencio, validación de evidencia, API, WebSockets, reinicio y resultados finales de Deepgram con un proveedor simulado. Ejecuta:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Si tienes Node.js, puedes verificar el conversor de audio con `node tests/test_worklet.mjs`. Node no es necesario para ejecutar la aplicación.

La calidad de una reunión real, los permisos de captura en tu Windows, el rendimiento de tu computador y la autenticación de Deepgram deben ensayarse en ese entorno. No se ha conectado este paquete a tu sesión real de Teams. La primera prueba recomendada es micrófono, después Teams web y finalmente Teams de escritorio.

Microsoft Graph permite obtener transcripciones después de terminar la reunión. Esta primera versión evita depender de Graph como una fuente de subtítulos en vivo.

## Fuentes técnicas

Revisión: 23 de octubre de 2026.

- Captura de pestañas y pantalla: https://developer.chrome.com/docs/web-platform/screen-sharing-controls
- Opciones y compatibilidad de captura: https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getDisplayMedia
- Deepgram, audio en vivo: https://developers.deepgram.com/reference/speech-to-text/listen-streaming
- Deepgram, resultados parciales y finales: https://developers.deepgram.com/docs/interim-results
- Faster-Whisper, ejecución y requisitos: https://github.com/SYSTRAN/faster-whisper
- Ollama, endpoint de chat y JSON: https://docs.ollama.com/api/chat
- Teams, recuperación de transcripciones: https://learn.microsoft.com/en-us/microsoftteams/platform/graph-api/meeting-transcripts/overview-transcripts
- Silueta continental de Colombia: Natural Earth 1:110m, dominio público. https://github.com/nvkelso/natural-earth-vector
- Inspiración visual de corrientes: https://observablehq.com/@mbostock/altered-world (Mike Bostock, adaptación de Gerard Ferrandez). El campo de la demo es una interpretación propia.

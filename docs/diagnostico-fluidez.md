# Diagnóstico de transcripción y temas automáticos

Fecha: 21 de noviembre de 2026.

Este documento conserva el diagnóstico del comportamiento anterior a la corrección. La implementación posterior guarda la transcripción antes de analizar y entrega actualizaciones de temas en segundo plano; consulta también la sección de transcripción y análisis en `uso.md` y los [resultados de la prueba real de diez minutos](prueba-fluidez-2026-11-21.md).

## Pruebas realizadas

- Simulación local del canal `/ws/audio` con transcripciones finales de un proveedor simulado y respuestas lentas de DeepSeek. Se ejecutan el socket, la cola, la clasificación automática y la publicación reales del servidor. No se captura audio en esta prueba.
- Simulación de timeout de DeepSeek al iniciar una taxonomía vacía.
- Dos solicitudes reales a DeepSeek con textos sintéticos de educación, usando la configuración del proyecto. No se envían conversaciones privadas.

## Resultados

| Prueba | Resultado |
|---|---|
| DeepSeek simulado con demora de 250 ms | La publicación tarda 255 ms; el bloqueo de sesión permanece ocupado 253 ms |
| Ráfaga acelerada de transcripciones con ese análisis lento | 32 intentos, 31 transcripciones notificadas al cliente, error de cola llena y captura detenida |
| Historial de la ráfaga después del cierre | Cero fragmentos archivados: el trabajador se cancela antes de completar el primero |
| Timeout con temas automáticos inicialmente vacíos | Texto conservado en la publicación, cero conceptos y cero categorías, método `deepseek-auto-unavailable` |
| Primera solicitud real a DeepSeek | 1,33 s; tres conceptos, dos categorías, un grupo |
| Segunda solicitud real a DeepSeek | 1,33 s; tres conceptos, dos categorías, un grupo |

La ráfaga es una prueba acelerada de saturación; sus tiempos no representan el ritmo de habla ni permiten predecir cuánto tarda una conversación real en fallar. Las dos respuestas reales son muestras puntuales, no percentiles de latencia.

## Causas verificadas en el código

`publish` espera simultáneamente las tres clasificaciones antes de guardar el evento y enviarlo al tablero, manteniendo ocupado `room.lock`. La siguiente intervención empieza después de la anterior. También se ejecuta la lectura automática al usar el proveedor `rules` para la lectura editable.

`audio_socket` utiliza una cola de 30 transcripciones. `emit` lanza una excepción cuando se llena; la limpieza cancela el trabajador. Como el texto todavía no se ha archivado, las transcripciones notificadas al cliente pueden quedar fuera del historial y del cierre exportado.

El río se alimenta de eventos ya clasificados. Una respuesta lenta retrasa su actualización. Si DeepSeek falla cuando todavía no hay categorías automáticas, la alternativa por reglas trabaja sobre un catálogo vacío y no produce temas.

## Correcciones necesarias para operación prolongada

1. Guardar y publicar cada transcripción confirmada antes de esperar al modelo.
2. Analizar en segundo plano y enviar actualizaciones de temas vinculadas al identificador del fragmento, sin duplicar texto ni métricas.
3. Controlar el trabajo pendiente del modelo con agrupación de intervenciones, tiempos máximos y estados de análisis pendiente o no disponible. Ampliar solamente la cola posterga la saturación.
4. Conservar las transcripciones aunque haya fallos del modelo, se cierre el canal de audio o se detenga la captura.
5. Medir cola pendiente, latencias de transcripción y análisis, reconexiones y consumo de memoria durante una prueba sostenida.

## Alcance pendiente al cerrar el diagnóstico inicial

No se ha realizado una captura real con Deepgram ni una prueba continua de ocho horas. Se requiere audio de prueba y validar la cadena navegador → audio compartido → Deepgram → transcripción → DeepSeek → tablero después de desacoplar ambas etapas. Para la prueba prolongada conviene comparar también la cantidad de transcripciones confirmadas con el historial exportado y registrar la recuperación ante cortes de red.

En esa primera investigación no se modificó el comportamiento de producción. Los scripts de reproducción iniciales están en `temp/diagnose-live-latency.py` y `temp/diagnose-real-deepseek.py` (carpeta local ignorada por Git); describen el comportamiento previo al desacoplamiento.

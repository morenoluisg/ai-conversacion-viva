# Prueba de fluidez con audio de Windows

Fecha: 21 de noviembre de 2026.

## Corrección aplicada

La transcripción confirmada se archiva y se publica antes de esperar al LLM. Un trabajador por sesión procesa los temas, con un máximo de diez segundos por clasificación. El trabajo pendiente utiliza el historial existente y no depende de una cola de transcripción limitada a 30 elementos. Los fallos del modelo conservan el texto y las categorías existentes.

El servidor envía actualizaciones por identificador de fragmento; el tablero sustituye su clasificación sin duplicar texto o menciones. El río conserva su estado de animación y revisión temporal. Detener o desconectar el audio permite continuar con el análisis. El cierre se habilita al terminar los pendientes. Vaciar la sesión cancela el trabajo antiguo.

## Prueba real

Se capturó el audio del dispositivo de salida predeterminado de Windows mediante WASAPI loopback. Un cliente WebSocket de prueba envió PCM16 mono a 16 kHz al servidor corregido. Se utilizaron Deepgram y DeepSeek reales con la configuración del proyecto. Esta prueba ejercita la captura directa de Windows y el servidor; el selector de permisos y la captura AudioWorklet del navegador no se automatizaron.

| Medida | Resultado |
|---|---:|
| Tiempo de captura supervisada | 600 s |
| Audio PCM enviado | 599.62 s |
| Transcripciones notificadas | 140 |
| Fragmentos recibidos por el canal del tablero | 140 |
| Fragmentos en el historial final | 140 |
| Fragmentos con actualización de temas recibida | 140 |
| Máximo de temas pendientes observado | 2 |
| Pendientes al finalizar | 0 |
| Errores de captura notificados | 0 |
| Identificadores únicos en el historial | Sí |
| Coincidencia entre transcripciones, canal y archivo | Sí |

Métodos de clasificación automática: {"deepseek-auto":140}.

Desde la incorporación del fragmento hasta su actualización de temas: media 3.362 s, máximo 6.249 s. Este tiempo incluye la espera del trabajador y las clasificaciones; no incluye el reconocimiento de voz previo de Deepgram.

Desde la incorporación del fragmento hasta su recepción por el canal del tablero: media 0.003 s, máximo 0.019 s. Esta medida tampoco representa la latencia completa desde el audio hablado.

## Regresiones verificadas

- 41 pruebas Python: archivo inmediato, ráfagas superiores al límite anterior, conservación del análisis al desconectar, timeout del modelo, fallos aislados, vaciado y protección del cierre pendiente, además de las funciones anteriores.
- Pruebas JavaScript de las siete vistas, identidad y atajos, captura y remuestreo; texto pendiente visible y actualizaciones sin duplicación ni reinicio del río.
- Las siete vistas también se ejecutaron con los datos reales de esta prueba en un entorno DOM/Canvas simulado. No se realizó inspección visual del navegador durante los diez minutos.

La prueba demuestra el funcionamiento observado durante este intervalo; no certifica ocho horas continuas ni la recuperación automática de toda posible interrupción de red. El historial permanece en memoria hasta exportarlo o cerrar el servidor.

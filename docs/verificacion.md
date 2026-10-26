# Verificación local — 26 de octubre de 2026

## Alcance

Revisión del código del servidor, procesamiento de audio, panel de captura, configuración de ejemplo, scripts de arranque, documentación y archivos candidatos a publicación. Las comprobaciones de Python se ejecutaron con Python 3.12.3 en Windows; las operaciones Git y la validación de sintaxis del script Bash se realizaron desde Ubuntu en WSL.

## Comprobaciones

- Las 11 pruebas de `unittest` pasan: bloques PCM, solape, silencio, fragmento final, conceptos, API, WebSockets, deduplicación, reinicio y proveedor Deepgram simulado.
- La sintaxis de `operator.js` y `audio-worklet.js` es válida para Node.js. La prueba del conversor comprueba 44,1 y 48 kHz, amplitud PCM16 y vaciado del bloque pendiente.
- El servidor local arrancó y respondió con HTTP 200 en el panel y la visualización.
- Whisper `base` se descargó y preparó en CPU con int8.
- Una frase sintética de 12,32 segundos enviada al WebSocket real produjo tres fragmentos confirmados, conceptos de biodiversidad y cambio climático, y confirmación de fin tras procesar el último fragmento. El procesamiento tardó aproximadamente 5,2 segundos en ese ensayo, enviando todo el audio sin pausas; no es una medición de latencia de captura en vivo. La voz instalada era de inglés y pronunció texto español con errores; este ensayo verifica el circuito y no acredita la precisión del reconocimiento con voz natural.
- La construcción genera wheel y paquete fuente. El wheel incluye los HTML y JavaScript que usa el servidor; el manifiesto del paquete fuente incluye scripts, configuración de ejemplo, pruebas y documentación.
- La carpeta temporal, entornos, modelos, grabaciones y configuración privada están excluidos de Git.

## Pendiente de ensayo en el equipo del evento

No se ha confirmado la captura real de salida del computador mediante el selector de pantalla del navegador ni una reunión real de Teams. Sigue la prueba del README y comprueba medidor, transcripción y actualización de la pantalla. Repite el ensayo con el audio y proyector del evento.

No se ha comprobado visualmente cada vista en el proyector, ni ejecutado la aplicación en macOS, ni utilizado Deepgram con credenciales reales u Ollama. El workflow define pruebas para Python 3.11 y 3.12 en Windows y Ubuntu; su resultado en GitHub debe comprobarse después del push.

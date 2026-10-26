#  Conversación viva

Aplicación local que convierte el audio de una conversación en texto y alimenta una presentación interactiva. Recibe micrófono, audio compartido de Teams web o audio del sistema cuando el navegador lo permite.

Incluye seis vistas: **mapa radial, anillos temáticos, evolución temática, Colombia en puntos, corrientes y constelaciones**.

## 1. Requisitos para una máquina nueva

- Python **3.11 o 3.12**. En Windows instala también el lanzador `py` y pip.
- Chrome o Edge para abrir el panel y seleccionar la fuente de audio.
- Internet durante la instalación y la primera descarga del modelo de voz.
- La carpeta completa del proyecto, descargada como ZIP y extraída, o clonada con Git. Git y Node.js no son necesarios para ejecutar la aplicación.

El modo inicial usa Whisper en CPU y conceptos por reglas: no requiere GPU, Ollama ni claves de API. Después de instalar y preparar el modelo, este modo puede funcionar sin Internet, siempre que la fuente de audio también esté disponible localmente.

La aplicación puede instalarse en Windows, Linux y macOS; **capturar toda la salida de audio del computador depende del sistema y del navegador**. Para esa prueba en Windows utiliza Chrome o Edge. En Linux y macOS empieza por micrófono o una pestaña con audio compartido y verifica qué fuentes ofrece el navegador.

## 2. Instalación en Windows: una sola vez por equipo

### Opción A: con los archivos BAT

1. Extrae el proyecto en una carpeta local. No ejecutes los archivos dentro del ZIP.
2. Abre `setup_windows.bat` y espera el mensaje **Instalacion completa**.
3. Abre `iniciar_windows.bat` y conserva abierta su consola.
4. Espera a ver `Uvicorn running on http://127.0.0.1:8765`.
5. Abre **http://127.0.0.1:8765** en Chrome o Edge. Si se abrió antes del arranque, recárgala.
6. Pulsa **Preparar Whisper local** y espera la confirmación. La primera descarga puede tardar varios minutos.

En los siguientes arranques solo necesitas `iniciar_windows.bat`. No hace falta repetir la instalación.

### Opción B: manualmente desde PowerShell

Abre PowerShell y entra en la carpeta que contiene `pyproject.toml`. Sustituye la ruta del ejemplo por la de tu copia:

```powershell
cd "C:\ruta\ai-conversacion-viva"
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[local]"
if (!(Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m minambiente_live --prepare-model
```

Ejecuta los comandos en orden y continúa cuando cada uno termine correctamente. Si instalaste Python 3.11, sustituye `py -3.12` por `py -3.11` en los dos primeros comandos de Python. Si ya tienes un entorno `.venv` funcional en este equipo, utiliza su Python directamente sin volver a crearlo.

La preparación termina con **Modelo preparado**. Ahora arranca el servidor:

```powershell
.\.venv\Scripts\python.exe -m minambiente_live
```

Espera el mensaje `Uvicorn running` y abre **http://127.0.0.1:8765** en Chrome o Edge. La consola queda ocupada mientras el servidor está funcionando; eso es normal. No necesitas activar el entorno virtual ni cambiar la política de ejecución de PowerShell.

## 3. Arrancar y apagar manualmente en Windows

Cada vez que quieras usar la presentación, abre PowerShell y ejecuta:

```powershell
cd "C:\ruta\ai-conversacion-viva"
.\.venv\Scripts\python.exe -m minambiente_live
```

En esta máquina, la carpeta actual del proyecto es `C:\project\javeriana\repos\ai-conversacion-viva`.

1. Abre **http://127.0.0.1:8765** en Chrome o Edge.
2. Abre la visualización desde el botón del panel; así comparte la misma sesión en vivo. Puedes moverla a la pantalla del proyector.
3. Selecciona la fuente y pulsa **Iniciar captura**. Espera la confirmación antes de hablar o reproducir audio.
4. Para terminar, pulsa **Detener** y espera a que se procese el texto pendiente.
5. Exporta el JSON desde el panel si necesitas conservar la conversación.
6. En la consola del servidor pulsa **Ctrl+C** para apagarlo.

Cerrar solo el navegador no apaga el servidor. Reiniciar el servidor borra las sesiones en memoria. No abras dos servidores en el mismo puerto.

## 4. Probar la salida de audio del computador

Esta prueba busca capturar directamente el sonido que reproduce Windows, incluso si usas auriculares.

1. Abre el panel en Chrome o Edge y confirma que Whisper esté preparado.
2. Selecciona **Teams de escritorio · audio del sistema**. Esta fuente también sirve para probar audio reproducido por otras aplicaciones, aunque no estés usando Teams.
3. Desmarca **Sumar mi micrófono** para comprobar únicamente la salida del computador.
4. Pulsa **Iniciar captura**. En el selector del navegador elige **Pantalla completa**, selecciona una pantalla y activa **Compartir audio del sistema**, si aparece. Confirma la selección.
5. Espera el aviso de captura lista y reproduce un video o audio con voz clara en español. Para comprobar los conceptos, usa contenido sobre agua, bosques, biodiversidad o comunidades.
6. Comprueba tres señales: el medidor se mueve, aparece texto confirmado y la visualización incorpora conceptos.
7. Deja correr la prueba al menos 20–30 segundos y pulsa **Detener**. Espera a que se incorpore el último fragmento.

Whisper trabaja en bloques de unos seis segundos, más el tiempo de procesamiento. El texto puede tardar en aparecer. Los conceptos por reglas solo se detectan si el texto contiene el vocabulario ambiental configurado.

Si el selector no ofrece audio del sistema, prueba una pestaña: abre el video o Teams web **en el mismo navegador**, selecciona **Teams web · audio de una pestaña** y comparte esa pestaña con **Compartir audio de la pestaña** activado. Para una conversación presencial selecciona **Micrófono**; permite el acceso cuando lo solicite el navegador. En Teams web puedes sumar tu micrófono para incluir tu voz.

La selección de pantalla es un requisito del navegador. La aplicación usa las pistas de audio y no envía los cuadros de pantalla al servidor.

## 5. Instalación y arranque en Linux o macOS

Desde una terminal, entra en la carpeta del proyecto. Comprueba que `python3 --version` corresponda a Python 3.11 o 3.12; si tienes varias versiones, usa el ejecutable de esa versión para crear el entorno.

```bash
cd /ruta/ai-conversacion-viva
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[local]'
if [ ! -f .env ]; then cp .env.example .env; fi
.venv/bin/python -m minambiente_live --prepare-model
.venv/bin/python -m minambiente_live
```

Abre **http://127.0.0.1:8765** en Chrome o Edge. En los siguientes usos entra en la carpeta y ejecuta únicamente `.venv/bin/python -m minambiente_live`. Pulsa **Detener**, exporta la sesión y termina el servidor con **Ctrl+C**.

También existe `bash scripts/iniciar.sh`, que instala las dependencias al crear un entorno nuevo y arranca la aplicación. Si `.venv` ya existe pero su instalación quedó incompleta, repite manualmente el comando de instalación.

## 6. Llevarlo a otro computador

1. Copia o descarga el proyecto completo, incluyendo `src`, `pyproject.toml`, `.env.example` y los scripts de arranque.
2. Instala Python y Chrome o Edge en el equipo de destino.
3. **Crea un entorno nuevo en ese equipo** siguiendo la sección 2 o 5. No copies `.venv`: contiene rutas y dependencias propias del equipo de origen.
4. Crea su `.env` a partir de `.env.example` y prepara Whisper en ese equipo; el modelo no viaja dentro del repositorio.
5. Ensaya la captura y la visualización antes de la presentación, con los mismos dispositivos de audio que usarás en el evento.

Cada equipo ejecuta su propio servidor. `127.0.0.1` apunta al computador donde abres el navegador. El panel y la pantalla proyectada deben abrirse en ese mismo equipo; esta configuración no permite abrir la sesión desde otro computador de la red.

## 7. Configuración y solución de problemas

El archivo `.env` es opcional para usar los valores iniciales, pero permite personalizarlos. Si ya existe, conserva tu configuración. Para empezar usa estos valores, incluidos en `.env.example`:

```dotenv
DEFAULT_STT=local
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
CONCEPT_PROVIDER=rules
```

Reinicia el servidor después de modificar `.env`. Para instalar solo el puente y usar Deepgram, sin Whisper, instala con `-m pip install -e .` y configura su clave según [docs/uso.md](docs/uso.md). No incluyas claves reales en archivos que compartas.

| Problema | Qué comprobar |
|---|---|
| `py` no se reconoce | Instala Python con el lanzador de Windows y abre una consola nueva. Si `python --version` muestra 3.11 o 3.12, puedes usar `python -m venv .venv`. |
| `No Python at ...` al usar `.venv` | El entorno apunta a una instalación de Python que ya no está disponible o fue copiado de otro equipo. Renombra `.venv` y crea uno nuevo con el Python instalado. |
| `No module named minambiente_live` o falta una dependencia | Entra en la raíz del proyecto y repite `.\.venv\Scripts\python.exe -m pip install -e ".[local]"`. |
| El instalador intenta instalar desde otra carpeta | Ejecuta la instalación desde la carpeta de `pyproject.toml`; `-e .` se interpreta respecto a la carpeta actual de la consola. |
| No abre el panel | Comprueba que el servidor siga ejecutándose y haya mostrado `Uvicorn running`. Abre la dirección manualmente o recarga la página. |
| Puerto 8765 ocupado | Usa el servidor que ya esté abierto, detenlo con Ctrl+C en su consola, o arranca en otro puerto como se muestra abajo. |
| Whisper no se prepara | Revisa Internet, espacio en disco y la salida de la consola. Repite `--prepare-model` con el Python del entorno. |
| La fuente no incluye audio o el medidor no se mueve | Repite la selección con Compartir audio activado y reproduce voz. Si no hay audio del sistema disponible, prueba compartir una pestaña. |
| Hay señal pero todavía no hay texto | Espera al menos un bloque y su procesamiento; comprueba voz clara en español y pulsa Detener para procesar el fragmento final. |
| Hay texto pero no conceptos | Prueba vocabulario ambiental reconocible; el modo `rules` no extrae conceptos generales de cualquier tema. |
| Whisper no alcanza el ritmo | Prueba `WHISPER_MODEL=tiny` en `.env`, reinicia y prepara el modelo. Evalúa el reconocimiento: un modelo menor puede perder precisión. |
| La visualización no recibe los cambios | Ábrela desde el panel y usa el mismo origen en ambas pestañas: no mezcles `localhost` con `127.0.0.1`. |

Para usar otro puerto en Windows:

```powershell
.\.venv\Scripts\python.exe -m minambiente_live --port 8766
```

Después abre **http://127.0.0.1:8766**. En Linux o macOS usa `.venv/bin/python -m minambiente_live --port 8766`. La instalación también proporciona el comando `conversacion-viva` dentro del entorno virtual.

La guía ampliada de Teams, Deepgram, Ollama y conexión de transcripciones está en [docs/uso.md](docs/uso.md).

## Componentes

| Ruta | Contenido |
|---|---|
| `src/minambiente_live/server.py` | API local, WebSockets y puente de transcripción |
| `src/minambiente_live/audio.py` | Bloques de voz local con solape y timestamps |
| `src/minambiente_live/concepts.py` | Reglas ambientales y extracción opcional con Ollama |
| `src/minambiente_live/static/` | Panel de captura, conversor PCM y pantalla interactiva |
| `tests/` | Pruebas del servidor y del procesamiento de audio |
| `docs/uso.md` | Instalación y conexión con micrófono o Teams |
| `docs/arquitectura.md` | Flujo de datos y endpoints |
| `docs/demo/Conversacion_Viva.html` | Demo autónoma con conversación simulada |
| `docs/presentaciones/` | PPT de MinAmbiente con fondo blanco y herramientas comerciales |
| `.github/workflows/ci.yml` | Verificación automática de Python, JavaScript y empaquetado |
| `.env.example` | Configuración de referencia sin claves |
| `pyproject.toml` | Paquete Python, dependencias y comando de ejecución |

## Modos disponibles

| Capa | Arranque | Alternativa |
|---|---|---|
| Transcripción | Faster-Whisper local, CPU e int8 | Deepgram por API con clave en `.env` |
| Conceptos | Vocabulario ambiental por reglas | Ollama con extracción y evidencia literal |
| Visualización | Sesión vacía alimentada por WebSocket | Demo HTML autónoma con texto ficticio |

Whisper local trabaja por bloques de unos seis segundos. La latencia depende del computador. Deepgram requiere conexión y factura el audio procesado según su plan. El modo local de voz y el vocabulario por reglas no necesitan claves de API.

Para activar Ollama, configura `CONCEPT_PROVIDER=ollama`, `OLLAMA_URL` y `OLLAMA_MODEL` en `.env`. Si la extracción no responde a tiempo se utilizan reglas de respaldo.

## Pruebas y paquete

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Si tienes Node.js:

```bash
node tests/test_worklet.mjs
```

Para construir un wheel y un archivo fuente distribuible:

```bash
python -m pip install -e '.[dev]'
python -m build
```

El workflow incluido verifica Python 3.11 y 3.12 en Windows y Ubuntu, comprueba JavaScript y construye el paquete. Se ejecutará cuando subas los archivos a GitHub y estén habilitadas las Actions. Las pruebas no requieren una clave de Deepgram, descargar un modelo de voz ni entrar a Teams.

## Obtener el repositorio y publicar cambios

Puedes descargar el ZIP desde GitHub o clonar el repositorio:

```bash
git clone https://github.com/morenoluisg/ai-conversacion-viva.git
cd ai-conversacion-viva
```

Para contribuir, ejecuta las comprobaciones de [CONTRIBUTING.md](CONTRIBUTING.md), revisa `git diff` y añade únicamente los archivos del cambio. Usa mensajes de Conventional Commits, por ejemplo `fix(audio): corregir el procesamiento del fragmento final`, `feat(visual): agregar una vista` o `docs: aclarar la instalación en Windows`.

Antes de publicar, comprueba `git status`, `git branch -vv` y `git remote -v`. Usa `git push origin main` si trabajas en `main` y tienes permisos de escritura; para colaborar desde otra rama, publica esa rama y abre un pull request.

`.gitignore` excluye el entorno virtual, `.env`, modelos, exportaciones, grabaciones y la carpeta temporal `temp/`. Conserva `.env.example` sin claves reales. Una copia clonada incluye los metadatos `.git`; el ZIP de descarga de GitHub no incluye el historial Git.

## Límites de esta versión

Es un prototipo local. El servidor escucha en `127.0.0.1` y no implementa un despliegue público multiusuario. Conserva una ventana de 150 fragmentos por sesión en memoria. Exporta el JSON desde el panel antes de cerrar el servidor si necesitas conservarla.

El audio de distintas voces se mezcla y los fragmentos no identifican al hablante. Las posiciones de los puntos en Colombia son una composición visual, no una atribución regional. Ensaya la captura, los permisos y la calidad del reconocimiento en el computador y el salón del evento.

La demo autónoma y la PPT también forman parte del repositorio. La aplicación ejecutable usa el HTML de `src/minambiente_live/static/visual.html`.

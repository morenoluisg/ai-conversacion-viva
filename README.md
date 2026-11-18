#  Conversación viva

Aplicación local que convierte el audio de una conversación en texto y alimenta una presentación interactiva. Recibe micrófono, audio compartido de Teams web o audio del sistema cuando el navegador lo permite.

Incluye seis vistas: **mapa radial, anillos temáticos, evolución temática, Colombia en puntos, corrientes y constelaciones**.

## Demo en GitHub Pages

Enlace de publicación: **https://morenoluisg.github.io/ai-conversacion-viva/**.

La demo pública usa `docs/index.html`, una copia del HTML autónomo `MinAmbiente_Conversacion_Viva_v4.html`. Incluye conversación simulada, seis vistas, entrada manual y exportación JSON. GitHub Pages sirve archivos estáticos: para capturar audio del sistema y transcribir con Whisper sigue la instalación local que aparece abajo. El botón Micrófono de la demo depende del reconocimiento de voz del navegador; no utiliza el servidor local ni Whisper y su servicio puede requerir Internet.

La publicación se configura en **Settings → Pages → Deploy from a branch → main → /docs**. Al modificar `docs/index.html` y hacer push a `main`, GitHub vuelve a publicar la demo. `docs/.nojekyll` permite servir los archivos directamente. La carpeta `temp/` permanece excluida de Git; los cambios hechos allí deben copiarse a `docs/index.html` para publicarlos.

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

## Categorías editables y DeepSeek

En el panel de captura, abre **Agenda, categorías y proyección**:

1. Pega la agenda y pulsa **Proponer desde la agenda**. Revisa nombres, colores y palabras clave; pulsa **Guardar categorías** para aplicar la propuesta.
2. Puedes agregar, renombrar y quitar categorías manualmente. Se permiten hasta 24 categorías, con nombres únicos. Quitar una categoría retira sus conceptos del historial visual; la transcripción se conserva.
3. Activa **Permitir categorías emergentes** para que DeepSeek proponga nuevas categorías al analizar las intervenciones. Cada concepto requiere evidencia literal del texto. Las categorías inferidas son orientativas, no acuerdos ni conclusiones del evento.
4. Marca un grupo y pulsa **Abrir mapa del grupo seleccionado**. Repite para proyectar varios mapas con grupos distintos. La visualización general incluye automáticamente categorías emergentes. Las ventanas con un grupo fijo conservan los identificadores seleccionados; abre otra ventana para incluir nuevas categorías.

Las seis vistas usan ahora un fondo claro y colores de mayor contraste para proyección. Cada ventana admite las teclas 1–6 para elegir su vista y F para pantalla completa.

Configuración del servidor en `.env` (archivo ignorado por Git):

```dotenv
CONCEPT_PROVIDER=deepseek
DEEPSEEK_API_KEY=tu_clave
DEEPSEEK_MODEL=deepseek-flash
```

La clave permanece en el servidor. Con este proveedor, la agenda y el texto transcrito se envían a DeepSeek; el audio sigue usando Whisper local o Deepgram según la selección de captura. Si falla el análisis de conceptos se usan reglas y palabras clave de las categorías activas, identificado como `rules-fallback`. Si falla la propuesta de agenda, se conserva la configuración anterior.

Las categorías y el historial son independientes por sesión y viven en memoria: se pierden al reiniciar el servidor. **Exportar texto y conceptos** incluye también la agenda y configuración de categorías. Vaciar la sesión elimina las intervenciones y conserva la configuración.

La inferencia desde la agenda devuelve una propuesta sin guardarla: `POST /api/sessions/{session}/infer-categories`. Consulta o actualiza la configuración con `GET` / `PUT /api/sessions/{session}/settings`. Los eventos y snapshots WebSocket incluyen las categorías necesarias para interpretar sus índices.

## Exportación de cierre con análisis

Al terminar, detén la captura y pulsa **Generar documentos de cierre** al final del panel. El proceso se ejecuta en el servidor; puedes recargar la página y seguir consultando el estado. Al finalizar aparece **Descargar paquete de cierre**.

El ZIP incluye:

- `conversacion_completa.txt`: todas las intervenciones confirmadas, con fecha, hablante disponible y referencia.
- `datos_conversacion.json`: historial, configuración, categorías, referencias y análisis para reutilización.
- `analisis_categorias.html`: síntesis transversal y análisis de cada categoría, con hallazgos, tensiones, riesgos, oportunidades, recomendaciones, preguntas abiertas y enlaces a las intervenciones.
- `analisis_visual.html`: distribución por categorías, mapa de relaciones y evolución por tramos, acompañados de análisis y notas de interpretación.

Los dos documentos HTML son autocontenidos: ábrelos en un navegador y usa **Imprimir / guardar como PDF**. Conserva ambos archivos en la misma carpeta para seguir sus enlaces cruzados. Los gráficos son estáticos y se reconstruyen con el historial completo; no son capturas de las animaciones de pantalla.

El historial de exportación conserva todos los fragmentos de la sesión en memoria, aunque la pantalla solo muestre los últimos 150. Conserva también la clasificación original de categorías retiradas o renombradas. `GET /api/sessions/{session}/events` devuelve este historial completo con el catálogo de categorías de cada intervención. Vaciar la sesión o reiniciar el servidor elimina el historial; descarga el cierre antes de hacerlo. Las sesiones con historial ya no se descartan automáticamente para abrir otras nuevas.

DeepSeek recibe las intervenciones y la agenda para elaborar los informes. Las conversaciones largas se procesan por bloques y se consolidan por niveles. Las referencias se validan automáticamente; el contenido de las conclusiones requiere revisión humana. Las menciones y coocurrencias no constituyen votos, consenso, compromisos ni causalidad. Si falla la IA, el paquete conserva transcripción y gráficos y señala las secciones sin análisis; puedes volver a generarlo.

API: `POST /api/sessions/{session}/export`, `GET /api/sessions/{session}/export/status` y `GET /api/sessions/{session}/export/download`. El paquete corresponde al corte de la conversación al pulsar Generar; nuevas intervenciones requieren otra generación.

## Grupos simultáneos y respuesta de las animaciones

En **Grupos simultáneos** puedes nombrar hasta tres grupos y marcar las categorías que componen cada uno. Una categoría y sus palabras clave pueden participar en varios grupos. **Guardar y abrir este grupo** guarda la configuración y abre su pantalla; repite para ver dos o tres pantallas recibiendo la misma conversación. La configuración se comparte a través del servidor, también entre computadores.

En cada visualización, **Grupo del tablero** permite cambiar entre toda la conversación, cada grupo y la unión de todos los grupos. El filtro se mantiene al pasar entre las seis vistas. El tablero conserva los últimos 150 fragmentos recibidos sin filtrar y reconstruye la selección al cambiar de grupo, sin duplicar conceptos compartidos. La exportación de cierre sigue conservando el historial completo.

Las animaciones tienen estas relaciones explícitas con el contenido clasificado del grupo:

- **Colombia en puntos:** la cantidad crece con las menciones de conceptos, mediante una curva de saturación progresiva hasta 2600 puntos. Los colores se distribuyen según las proporciones de menciones de las categorías. Las posiciones son artísticas, sin atribución geográfica. Texto sin conceptos del grupo no incrementa los puntos.
- **Corrientes:** se activan 18 líneas por mención de concepto, hasta 900. Sus colores reflejan las proporciones temáticas. Una intervención con conceptos del grupo produce un pulso de velocidad y tamaño de 1,8 segundos; después vuelven a su actividad de base. Las trayectorias siguen siendo ruido generativo y no representan relaciones causales, sentimentales o geográficas.

Los puntos y las líneas son una representación artística de actividad temática, no un recuento literal de personas, votos, palabras o lugares. Sin conceptos del grupo, no se muestran puntos temáticos ni corrientes activas. Los fondos de silueta y los controles permanecen visibles.

Verificación de las seis vistas, cambios de grupo y respuesta de las animaciones: `node tests/test_visual.mjs`.

## Tres lecturas independientes de la conversación

La sección 3 presenta **Agenda SINA CONECTA**, **Editable** y **DeepSeek autónomo**. Las tres se construyen en paralelo a partir de las mismas intervenciones confirmadas. Cada tablero permite seleccionar la lectura y después su grupo en las seis vistas.

- **Agenda:** ocho categorías y tres grupos iniciales preparados a partir de `Agenda borrador detallada v3.docx`. El texto extraído de esa versión se incluye en el paquete (`static/agenda-sina.txt`); no depende de la carpeta temporal en producción. Los grupos son Del dato a la decisión, Habilitadores de la transformación y SINA NEXT 2035. Las categorías de esta lectura son fijas, y crecen las menciones de los temas que realmente aparecen.
- **Editable:** conserva las categorías, palabras clave y grupos que define el operador. Puede permitir nuevas categorías emergentes sin perder su estructura manual.
- **DeepSeek autónomo:** empieza con cero categorías y cero grupos, sin imponerle la taxonomía de la agenda. DeepSeek crea categorías sustentadas en citas literales del texto actual y define entre una y tres constelaciones semánticas. Reutiliza los temas anteriores; si omite categorías históricas en una propuesta de grupos se solicita una consolidación específica. Se admiten hasta 24 categorías. Las constelaciones pueden reorganizarse al avanzar la conversación y requieren revisión humana.

La inferencia de las tres lecturas se ejecuta en paralelo. La automática consulta DeepSeek aun cuando el modo de conceptos editable sea `rules`; requiere la clave del servidor. Esto aumenta el número de solicitudes y puede aumentar la latencia. Si falla la respuesta automática, conserva el texto y la estructura anterior, muestra la indisponibilidad y reintenta con la siguiente intervención.

El selector de la sección 3 abre o cambia las pantallas del mismo navegador; cada tablero también puede cambiar de lectura por su cuenta. Para abrir otro equipo, comparte una URL con `lens=agenda`, `lens=manual` o `lens=automatic`. Los snapshots WebSocket incluyen las tres lecturas; las intervenciones emitidas incluyen sus clasificaciones independientes en `lenses`. `GET /api/sessions/{session}/lenses` consulta las dos lecturas adicionales. Vaciar la sesión reinicia los temas automáticos y conserva la configuración editable y de agenda.

Los documentos de cierre se generan para la lectura elegida en la sección 3 al pulsar Generar. La API admite `POST /api/sessions/{session}/export?lens=agenda|manual|automatic`. El estado y los informes indican la lectura analizada; para obtener los tres análisis, genera y descarga un paquete por lectura.

## Río de temas animado

La vista **7 · Río de temas** se inspira en las transiciones de streamgraph de Mike Bostock (https://observablehq.com/@d3/streamgraph-transitions). La implementación es propia en Canvas y no carga D3 ni datos externos. A diferencia de la demostración de referencia, que genera capas aleatorias, esta vista utiliza exclusivamente conceptos clasificados de las intervenciones.

Cada banda representa una categoría de la lectura y grupo seleccionados. Su grosor es la media móvil de menciones de conceptos sobre hasta tres fragmentos, en una ventana de 40 intervenciones. Las bandas se apilan alrededor de una línea central, conservan el color de la categoría y cambian mediante una transición de 1,1 segundos cuando se actualizan los datos. Al terminar la transición se estabilizan hasta la siguiente intervención. La escala es local al tramo y se indica en pantalla; el eje horizontal sigue el orden de intervención, no duraciones iguales. Los tramos sin conceptos no inventan actividad.

El deslizador temporal, inspirado en la navegación temporal de The Wealth & Health of Nations (https://observablehq.com/@mbostock/the-wealth-health-of-nations), permite revisar un fragmento entre los últimos 150 recibidos. Mientras se revisa un momento anterior, las nuevas intervenciones siguen llegando y la selección temporal se mantiene. **Volver al directo** muestra nuevamente el tramo más reciente. Cambiar de lectura o grupo vuelve al directo. La animación respeta la preferencia del navegador de reducir movimiento.

La vista está disponible desde el panel, el tablero y la tecla **7**. El informe visual de cierre incluye una versión estática del río de temas con su explicación metodológica, además de los gráficos existentes.

## Etiquetas representativas y límites de presentación

La extracción con DeepSeek selecciona hasta tres conceptos centrales por intervención, con etiquetas nominales de hasta cuatro palabras y 36 caracteres. Recibe un vocabulario de etiquetas recientes por lectura para reutilizar conceptos ya nombrados en lugar de crear variantes continuamente. Las frases demasiado largas se descartan como etiquetas de conceptos; la transcripción original permanece completa. La evidencia literal sigue siendo obligatoria y el modelo recibe instrucciones para evitar consecuencias inferidas y expresiones temporales genéricas sin relevancia central.

El mapa radial recupera la distribución circular original, con centro, ramas por categoría y hojas en abanico. Mantiene posiciones fijas y un presupuesto adaptable al tamaño del lienzo: hasta seis categorías por página y entre dos y cuatro etiquetas por categoría según **Detalle visual**, con reducción adicional si falta altura. **Otros temas** recorre las categorías restantes. Las selecciones se mantienen estables; un concepto nuevo sustituye a otro visible cuando acumula una diferencia suficiente de menciones, evitando cambios por cada aparición aislada. Esta regla selecciona qué mostrar, sin atribuir importancia o consenso.

Las etiquetas visibles se ajustan al ancho disponible con puntos suspensivos. Al pulsar un nodo radial se muestra su etiqueta y el fragmento de origen en el panel lateral. El contador indica cuántos conceptos se presentan respecto a los detectados. Los datos completos siguen disponibles en el historial y en los informes.

Los anillos limitan etiquetas a un subconjunto representativo por categoría y al espacio vertical disponible. Las constelaciones comparten la paginación temática y tienen un límite de puntos por categoría para evitar nubes desbordadas. Los gráficos temporales y las métricas siguen utilizando todos los conceptos del tramo, independientemente del presupuesto de etiquetas.

## Páginas para servidor y cliente de captura

El panel completo continúa en `/` y tiene el alias `/admin`. Para trabajo distribuido se añaden:

- `/servidor`: formulario para preparar enlaces con dirección del servidor y código de sesión. Admite dominio o IP con puerto. No envía audio ni consulta APIs de otros orígenes: prepara enlaces para abrir las páginas desde el destino elegido.
- `/captura?session=CODIGO`: cliente dedicado a seleccionar micrófono, pestaña o audio del sistema e iniciar/detener el envío. No incluye los editores de categorías ni los controles de borrado o exportación.
- `/visual?live=1&session=CODIGO&lens=agenda`: proyección de la misma sesión.

Desde el panel, abre **Servidor y cliente remoto** y copia el enlace de captura al equipo del operador. El enlace contiene el código de sesión; abrir el panel en otro navegador con `?session=CODIGO` permite administrar esa misma conversación. Sin un código explícito, el panel conserva su sesión local habitual.

La captura del panel completo y del cliente remoto utiliza la misma implementación de audio (`capture-audio.js`), incluidos PCM16 mono a 16 kHz, suma opcional de micrófono, medidor de señal, espera del procesamiento final y detención de las pistas. La página de captura muestra el servidor, la sesión y el estado del envío. Solo se admite una captura por sesión; el cliente consulta el estado y el servidor mantiene el bloqueo definitivo.

Los controles de vista y lectura del administrador se transmiten ahora por el servidor mediante WebSocket, por lo que llegan también a pantallas abiertas en otros equipos. `POST /api/sessions/{session}/display` cambia la vista o lectura; su configuración se incluye al reconectar una pantalla. Cada tablero conserva además sus selectores locales.

### Preparar la instalación remota

Esta actualización separa las páginas y permite configurar la escucha; no publica automáticamente un servidor ni configura certificados o autenticación. Antes de exponerlo en Internet, prepara HTTPS y protección de acceso en el despliegue. Separar las páginas no crea permisos de usuario diferentes. Las sesiones siguen en memoria y requieren exportación antes de reiniciar.

En `.env`, configura las direcciones reales de la instalación:

```dotenv
# Si el proxy HTTPS está en el mismo servidor, conserva la escucha local.
BIND_HOST=127.0.0.1
ALLOWED_HOSTS=127.0.0.1,localhost,conversacion.tudominio.co
```

Para escuchar también en interfaces de red cuando tu instalación lo requiera:

```powershell
$env:PYTHONPATH='src'
.venv\Scripts\python.exe -m minambiente_live --host 0.0.0.0 --port 8765
```

El proxy HTTPS debe reenviar las conexiones WebSocket y conservar el encabezado Host del dominio público. Una dirección HTTP de red puede abrir las páginas, pero el cliente bloqueará el inicio de captura: usa HTTPS. `localhost` solo representa el equipo donde está abierto el navegador; no sirve como dirección compartida entre computadores.

El servidor recibe audio del navegador del operador; no accede por sí solo al micrófono del equipo remoto. La selección de audio y los permisos siempre se realizan en ese navegador. DeepSeek y las demás claves permanecen en el servidor.

Verificaciones: `node tests/test_connection.mjs`, `node tests/test_visual.mjs` y los tests Python de `tests/test_remote.py`.


Las etiquetas radiales reservan cajas de espacio antes de dibujarse. Los títulos de categoría tienen prioridad; los conceptos se disponen alrededor de su rama con un máximo de dos líneas y una etiqueta visual de hasta tres palabras. Si no hay espacio libre, la etiqueta y su hoja se omiten de esa vista. El concepto completo continúa en los datos y el panel de detalle. Los enlaces tenues entre hojas de categorías diferentes representan coaparición en un mismo fragmento y tienen un límite visual para evitar ruido.

## Fondo claro u oscuro desde administración

En el panel completo, junto a la selección de vista, **Fondo de los tableros** permite elegir Claro u Oscuro. La opción se aplica mediante el servidor a todas las pantallas de la sesión y se incluye al reconectar. El fondo claro sigue siendo el valor inicial; la elección dura mientras exista la sesión en el servidor.

El modo oscuro adapta el fondo del lienzo, las etiquetas, los controles, las líneas y los colores de las categorías para conservar contraste, incluidos colores personalizados oscuros. Cambiar el fondo no modifica la clasificación, los conceptos, las posiciones del mapa ni reinicia la animación activa. Las siete vistas usan la misma elección. Los informes mantienen su presentación clara para impresión.

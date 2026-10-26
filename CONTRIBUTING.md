# Desarrollo

Trabaja desde la raíz del repositorio con Python 3.11 o 3.12.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Para los comandos siguientes, activa el entorno virtual o utiliza explícitamente su ejecutable de Python. Instala el extra `local` si vas a probar Faster-Whisper. La suite de pruebas usa un modelo y un proveedor simulados, de modo que puede ejecutarse sin capturar audio ni consultar servicios externos.

Antes de proponer un cambio:

```bash
python -m unittest discover -s tests -v
node --check src/minambiente_live/static/operator.js
node --check src/minambiente_live/static/audio-worklet.js
node tests/test_worklet.mjs
python -m build
```

Para cambios de captura, ensaya también micrófono, detener antes de que el proveedor esté listo, detener al terminar una frase y finalizar la pantalla compartida desde el navegador. Para cambios de presentación, revisa las seis vistas en el tamaño de pantalla del evento.

No añadas `.env`, claves, modelos descargados ni conversaciones reales a fixtures de prueba. Mantén la configuración de ejemplo sincronizada con los parámetros nuevos.

Usa Conventional Commits: `feat` para funcionalidades, `fix` para correcciones, `docs` para documentación, `test` para pruebas y `ci` o `chore` para automatización y mantenimiento. Puedes indicar el componente entre paréntesis: `fix(audio): procesar el fragmento final`. Separa los cambios independientes en commits y revisa `git diff --cached` antes de confirmar.

El HTML autónomo en `docs/demo/` conserva la demostración que se puede abrir sin servidor. El HTML de la aplicación en `src/minambiente_live/static/` incluye la conexión en vivo. Si cambias una visualización común, comprueba ambas variantes.

Referencias del workflow:

- https://github.com/actions/checkout
- https://github.com/actions/setup-python
- https://github.com/actions/setup-node

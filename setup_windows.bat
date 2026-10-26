@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3.12 -m venv .venv 2>nul
  if errorlevel 1 py -3.11 -m venv .venv 2>nul
  if errorlevel 1 py -3 -m venv .venv
) else (
  python -m venv .venv
)
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e ".[local]"
if errorlevel 1 goto fail
if not exist .env copy .env.example .env >nul
echo.
echo Instalacion completa. Abre iniciar_windows.bat.
echo Whisper descargara el modelo cuando pulses Preparar Whisper local.
pause
exit /b 0
:fail
echo No fue posible instalar. Usa Python 3.11 o 3.12 y revisa tu conexion.
pause
exit /b 1

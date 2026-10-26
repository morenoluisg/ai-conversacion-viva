@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Primero ejecuta setup_windows.bat.
  pause
  exit /b 1
)
if not exist .env copy .env.example .env >nul
start "" http://127.0.0.1:8765
.venv\Scripts\python.exe -m minambiente_live
pause

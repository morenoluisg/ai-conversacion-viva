"""Entrada de consola para la aplicación instalada."""
import argparse
import os
from pathlib import Path
from dotenv import load_dotenv


def main():
    parser = argparse.ArgumentParser(description='MinAmbiente · Conversación viva')
    parser.add_argument('--port', type=int, default=8765, help='Puerto local (8765)')
    parser.add_argument('--prepare-model', action='store_true', help='Preparar Whisper sin capturar audio')
    args = parser.parse_args()
    load_dotenv(Path(os.getenv('MINAMBIENTE_ENV_FILE', Path.cwd() / '.env')))
    if args.prepare_model:
        from .audio import get_model
        print('Preparando Whisper. La primera vez requiere descargar el modelo.')
        get_model()
        print('Modelo preparado.')
        return
    if not 1 <= args.port <= 65535:
        parser.error('El puerto debe estar entre 1 y 65535')
    import uvicorn
    uvicorn.run('minambiente_live.server:app', host='127.0.0.1', port=args.port, workers=1)

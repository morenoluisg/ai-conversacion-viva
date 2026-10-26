#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -e '.[local]'
fi
if [ ! -f .env ]; then cp .env.example .env; fi
printf 'Abre http://127.0.0.1:8765 en Chrome o Edge.\n'
exec .venv/bin/python -m minambiente_live

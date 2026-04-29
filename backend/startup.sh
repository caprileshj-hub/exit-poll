#!/bin/bash
# Codex: Azure App Service startup script. Keep this file with LF endings.

set -e

cd /home/site/wwwroot

if ! command -v uvicorn >/dev/null 2>&1; then
    echo "[startup] Installing dependencies..."
    pip install -r requirements.txt -q
fi

if [ ! -f exitpoll.db ]; then
    echo "[startup] Initializing database..."
    python init_db.py
fi

exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"

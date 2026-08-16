#!/bin/bash
# Azure App Service startup script. Keep this file with LF endings.

set -e

cd /home/site/wwwroot

export PYTHONPATH="/home/site/wwwroot/.python_packages/lib/site-packages:${PYTHONPATH}"

# Siempre correr migraciones — init_db.py usa CREATE TABLE IF NOT EXISTS (idempotente)
echo "[startup] Aplicando migraciones..."
python init_db.py

# Sembrar datos si centros está vacía (BD recién creada o reseteada)
CENTROS=$(python -c "import sqlite3; c=sqlite3.connect('exitpoll.db'); print(c.execute('SELECT COUNT(*) FROM centros').fetchone()[0])")
if [ "$CENTROS" = "0" ]; then
    echo "[startup] BD vacía — sembrando datos demo..."
    python init_showcase.py
fi

# FastAPI actualiza los historicos en segundo plano para no bloquear el
# health check de App Service.
exec python -m uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"

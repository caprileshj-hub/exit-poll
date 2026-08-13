#!/bin/bash
# Azure App Service startup script. Keep this file with LF endings.

set -e

cd /home/site/wwwroot

pip install -r requirements.txt -q

# Siempre correr migraciones — init_db.py usa CREATE TABLE IF NOT EXISTS (idempotente)
echo "[startup] Aplicando migraciones..."
python init_db.py

# Sembrar datos si centros está vacía (BD recién creada o reseteada)
CENTROS=$(python -c "import sqlite3; c=sqlite3.connect('exitpoll.db'); print(c.execute('SELECT COUNT(*) FROM centros').fetchone()[0])")
if [ "$CENTROS" = "0" ]; then
    echo "[startup] BD vacía — sembrando datos demo..."
    python init_showcase.py
fi

# Sembrar estudios historicos fijos. Es idempotente via ON CONFLICT y no
# reabre los Excel durante el arranque.
echo "[startup] Sembrando estudios historicos fijos..."
python seed_resultados_historicos.py || echo "[startup] WARN: seed_resultados_historicos.py fallo; revisar logs"
python seed_historico_estudios.py || echo "[startup] WARN: seed_historico_estudios.py fallo; revisar logs"

exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"

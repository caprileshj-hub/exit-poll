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

# Sembrar estudios historicos versionados si no estan en la BD persistida.
# Los importadores son idempotentes via ON CONFLICT, pero evitamos trabajo
# innecesario en cada reinicio de App Service.
HISTORICOS=$(python -c "import sqlite3; c=sqlite3.connect('exitpoll.db'); refs=('2006-presidencial','2012-presidencial','2013-presidencial'); print(sum(1 for r in refs if c.execute('SELECT 1 FROM historico_estudios WHERE eleccion_ref=? LIMIT 1', (r,)).fetchone()))")
if [ "$HISTORICOS" != "3" ]; then
    echo "[startup] Faltan estudios historicos (${HISTORICOS}/3) - importando 2006, 2012 y 2013..."
    python import_2006.py || echo "[startup] WARN: import_2006.py fallo; revisar logs"
    python import_2012_2013.py || echo "[startup] WARN: import_2012_2013.py fallo; revisar logs"
fi

exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"

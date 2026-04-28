#!/bin/bash
# Azure App Service — startup script
# Configurar en Azure Portal > Configuration > Startup Command:
#   bash '/home/site/wwwroot/exit poll/backend/startup.sh'

cd '/home/site/wwwroot/exit poll/backend'

# Inicializar la BD si no existe
if [ ! -f exitpoll.db ]; then
    echo "[startup] Inicializando base de datos..."
    python init_db.py
fi

# Arrancar la app
exec uvicorn app:app --host 0.0.0.0 --port 8000

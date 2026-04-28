#!/bin/bash
# Azure App Service — startup script
# Configurar en Azure Portal > Configuration > Startup Command:
#   bash /home/site/wwwroot/startup.sh

cd /home/site/wwwroot

# Instalar dependencias si uvicorn no está disponible
if ! command -v uvicorn &> /dev/null; then
    echo "[startup] Instalando dependencias..."
    pip install -r requirements.txt -q
fi

# Inicializar la BD si no existe
if [ ! -f exitpoll.db ]; then
    echo "[startup] Inicializando base de datos..."
    python init_db.py
fi

# Arrancar la app
exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}

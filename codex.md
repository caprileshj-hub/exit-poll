# Codex Notes - Exit Poll Venezuela

Este archivo resume el contexto operativo del repo para que futuras sesiones de Codex no empiecen desde cero.

## Ubicacion y flujo de trabajo

- Repo activo: `D:\Test\exit_poll`.
- No trabajar desde `D:\Test` como si fuera el repo de la app; ahi hay varios proyectos hermanos.
- Rama principal actual: `main`.
- Remoto: `origin/main` en `https://github.com/caprileshj-hub/exit-poll.git`.
- Si el usuario dice que ya subio cambios o pide revisar lo ultimo, hacer `git pull --ff-only origin main` antes de analizar.
- Si el usuario pide arreglar algo con frases como "dale arreglalo", proceder a modificar y validar sin pedir otra ronda de permiso.
- Si el usuario pide "subelo al repo", commitear y pushear despues de validar.

## Entorno local

- Windows / PowerShell.
- Entorno virtual usado para validar: `D:\Test\.venv`.
- Este repo ha tenido problemas cuando el venv queda apuntando a un Python roto o a Python 3.14. La ruta que funciono fue Python 3.12.
- Comandos utiles:

```powershell
& 'D:\Test\.venv\Scripts\pytest.exe' -q
& 'D:\Test\.venv\Scripts\python.exe' backend\seed_2006.py --dry-run
```

- Si `python.exe` del venv falla dentro del sandbox pero los entrypoints existen, probar fuera del sandbox o reconstruir el venv con Python 3.12.
- Dependencias: instalar desde ambos archivos cuando se reconstruya el entorno.

```powershell
& 'D:\Test\.venv\Scripts\pip.exe' install -r 'D:\Test\exit_poll\requirements.txt' -r 'D:\Test\exit_poll\backend\requirements.txt' pytest
```

## Estructura importante

- `backend/app.py`: FastAPI, dashboard, rutas de configuracion, live view y endpoints de TM/IA.
- `backend/schema.sql`: esquema base de SQLite.
- `backend/init_db.py`: inicializacion y migraciones ligeras.
- `backend/cargador_tm.py`: cargador diferencial de Tabla de Mesa.
- `backend/convertidor_tm.py`: conversion deterministica para formatos conocidos.
- `backend/agent.py`: abstraccion de proveedores IA configurados en `/config`.
- `backend/analista_ia.py`: analista deterministico con guardrails.
- `backend/selector_muestra.py`: seleccion de muestra.
- `backend/calculador_pesos.py`: ponderacion jerarquica.
- `backend/seed_2006.py`: carga historica presidencial 2006.
- `README.md`: documento publico del estado del producto.
- `BITACORA.md`: registro historico y pendientes; puede tener ruido de encoding, preferir agregar secciones nuevas en vez de parches fragiles.

## Decisiones ya tomadas

- El canal de campo principal es SMS por baja conectividad.
- La Tabla de Mesa tiene dos caminos de ingestion:
  - deterministico legacy para formatos conocidos;
  - asistido por IA para formatos nuevos o variables.
- La IA usa la configuracion existente en `/config`; no se debe crear una superficie separada de API keys.
- En TM, nunca sobrescribir coordenadas, riesgo ni radio desde un archivo CNE.
- Los centros ausentes en una nueva TM no se borran.
- Si hay filas ambiguas o conflictivas en TM, bloquear confirmacion hasta resolverlas.
- El analista debe usar la frase exacta `datos insuficientes para establecer tendencias` cuando no hay datos suficientes.
- Azure espera preservar el nesting `exit_poll/backend`; `backend/startup.sh` asume `cd /home/site/wwwroot/exit_poll/backend` antes de levantar `uvicorn app:app`.

## Cambios recientes relevantes

- Se agrego soporte historico 2006:
  - `elecciones.notas`;
  - `resultados_mesa`;
  - `reportes_campo`;
  - vistas `v_proyeccion` y `v_evaluacion`;
  - `backend/seed_2006.py`;
  - archivos fuente en `backend/data/2006/`.
- Commit publicado: `719db81 Add 2006 historical seed data`.
- Validacion del seed 2006 en `--dry-run`:
  - 11,118 centros cargables;
  - 33,002 mesas;
  - 11,118 historicos;
  - 580 reportes de campo;
  - 6 centros de campo sin match.

## Validacion antes de commitear

Minimo:

```powershell
& 'D:\Test\.venv\Scripts\pytest.exe' -q
git diff --check
git status --short --branch
```

Para cambios de base de datos o seed:

```powershell
& 'D:\Test\.venv\Scripts\python.exe' backend\seed_2006.py --dry-run
```

El test actual `test_flujo.py` es un smoke test legacy; no cubre todo FastAPI ni todos los flujos reales. No sobreconfiar en un `pytest` verde.

## Riesgos y pendientes conocidos

- Falta ampliar cobertura de tests backend para rutas FastAPI, carga TM, muestra, pesos y analista.
- Seguir revisando soporte por tipo de eleccion: regional, municipal y asamblea.
- La integracion SMS/GPS/gateway Android sigue en desarrollo.
- La ingestion IA de TM necesita hardening de UX para archivos grandes, limites de proveedor, resolucion manual y matching difuso.
- Si se toca deploy, verificar que workflow, artifact y `backend/startup.sh` sigan alineados.

## Preferencias de colaboracion

- El usuario suele escribir en espanol para este repo; responder y documentar en espanol.
- Mantener momentum: diagnosticar, arreglar, validar, documentar y publicar cuando el pedido lo implique.
- Si quedan bugs para despues, guardarlos en `BITACORA.md`.
- Si se actualiza comportamiento importante, mantener `README.md` sincronizado.
- Antes de editar archivos sensibles, leer el contexto cercano y respetar cambios no hechos por Codex.

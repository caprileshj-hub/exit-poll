# AI_MODULE_REVIEW.md - Hallazgos iniciales del modulo AI

> Documento creado antes de modificar implementacion, para dejar claro el estado real del modulo AI existente.

## Archivos revisados

- `backend/agent.py`
- `backend/analista_ia.py`
- Integraciones AI en `backend/app.py`: `/chat`, `/config`, `/config/test`, `/api/analista/contexto`, `/api/analista/preguntar`
- `test_flujo.py`

## Estructura actual

### `backend/agent.py`

- Es la capa LLM generativa.
- Ya soporta multiples proveedores configurables:
  - OpenAI via SDK OpenAI.
  - Groq via endpoint OpenAI-compatible.
  - Anthropic via SDK Anthropic.
  - Gemini via endpoint OpenAI-compatible.
- Usa la tabla `config` y variables de entorno para resolver provider, model, API key, temperature y max_tokens.
- Tiene dos modos:
  - `ask_agent()`: streaming para `/chat`.
  - `ask_structured()` / `ask_structured_async()`: llamada single-shot usada tambien por ingesta AI de Tabla Mesa.

### `backend/analista_ia.py`

- Es un analista deterministico sin llamadas LLM.
- Consume el contexto generado desde `_contexto_analista()` en `backend/app.py`.
- Responde con JSON para el panel live (`/api/analista/preguntar`).
- Ya aplica guardrails basicos:
  - minimo de opiniones
  - minimo de cobertura
  - minimo de cortes
  - frase exacta de insuficiencia

### `backend/app.py`

- `_contexto_analista()` resume datos vivos ya calculados por el backend.
- `/chat` llama al LLM solo si `get_contexto_centro()` considera suficientes los datos.
- `/api/analista/preguntar` usa `analista_ia.analizar_contexto()` y no consume tokens.

## Que esta bien

- La abstraccion multi-proveedor ya existe; no conviene reconstruirla.
- Las API keys no estan hardcodeadas; se leen desde entorno o tabla `config`.
- Hay guardrail de datos insuficientes antes de usar el chat LLM.
- El analista deterministico evita declarar ganador y trabaja con datos del corte.
- El test `test_flujo.py` cubre el guardrail principal del analista vivo.

## Que esta roto o fragil

- `SYSTEM_PROMPT` esta embebido en `agent.py`, mezclado con logica de proveedor.
- El prompt actual no cumple la estructura v2.3 de 5 secciones ni las reglas de MoE/no-respuesta/ponderacion/series.
- `agent.py` no expone la interfaz minima exacta `llm_call(...) -> str` solicitada.
- No hay metadata de trazabilidad normalizada para llamadas LLM: timestamp, provider, model, prompt version, schema version, tokens y latencia.
- La temperature default para reportes es 0.3, no 0.
- La validacion estadistica v2.3 no existe como unidad reutilizable.
- El contexto real del analista no coincide completamente con el schema v2.3 del prompt:
  - usa `total_votos` / `total_opiniones` en lugar de `tamano_muestra_actual`
  - usa `cobertura_pct` en lugar de `porcentaje_cobertura_geografica`
  - usa `suficiencia.minimo_opiniones` en lugar de `umbral_requerido`
  - no trae cortes demograficos ni motivadores de voto
  - no trae ponderacion_activa, design_effect ni tasa_no_respuesta

## Que falta

- Separar prompts del transporte LLM.
- Agregar validador estadistico secuencial:
  - muestra global
  - coherencia interna
  - subgrupos demograficos
- Agregar prompt v2.3 en archivo/funcion separada.
- Agregar metadata de trazabilidad a llamadas single-shot.
- Mantener compatibilidad con el schema real actual sin exigir migraciones de BD.

## Limites de esta intervencion

- No tocar pipeline de datos.
- No tocar graficas frontend.
- No tocar schema de BD ni modelos.
- No reemplazar el modulo AI existente; solo refinarlo.

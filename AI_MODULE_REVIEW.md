# AI_MODULE_REVIEW.md — Exit Poll Venezuela

> Hallazgos iniciales del módulo AI. Documento creado antes de modificar la implementación
> (2026-05-07), para dejar claro el estado real del módulo AI existente.
> Histórico: los puntos de "Qué está roto o frágil" y "Qué falta" se resolvieron en el hardening v2.3 (ver CHANGELOG 2026-05-07).

---

## Archivos revisados

- `backend/agent.py`
- `backend/analista_ia.py`
- Integraciones AI en `backend/app.py`: `/chat`, `/config`, `/config/test`, `/api/analista/contexto`, `/api/analista/preguntar`
- `test_flujo.py`

---

## Estructura actual

### `backend/agent.py`

- Es la capa LLM generativa.
- Ya soporta múltiples proveedores configurables:
  - OpenAI vía SDK OpenAI.
  - Groq vía endpoint OpenAI-compatible.
  - Anthropic vía SDK Anthropic.
  - Gemini vía endpoint OpenAI-compatible.
- Usa la tabla `config` y variables de entorno para resolver provider, model, API key, temperature y max_tokens.
- Tiene dos modos:
  - `ask_agent()`: streaming para `/chat`.
  - `ask_structured()` / `ask_structured_async()`: llamada single-shot usada también por la ingesta AI de Tabla de Mesa.

### `backend/analista_ia.py`

- Es un analista determinístico sin llamadas LLM.
- Consume el contexto generado desde `_contexto_analista()` en `backend/app.py`.
- Responde con JSON para el panel live (`/api/analista/preguntar`).
- Ya aplica guardrails básicos:
  - mínimo de opiniones
  - mínimo de cobertura
  - mínimo de cortes
  - frase exacta de insuficiencia

### `backend/app.py`

- `_contexto_analista()` resume datos vivos ya calculados por el backend.
- `/chat` llama al LLM solo si `get_contexto_centro()` considera suficientes los datos.
- `/api/analista/preguntar` usa `analista_ia.analizar_contexto()` y no consume tokens.

---

## Qué está bien

- La abstracción multi-proveedor ya existe; no conviene reconstruirla.
- Las API keys no están hardcodeadas; se leen desde entorno o tabla `config`.
- Hay guardrail de datos insuficientes antes de usar el chat LLM.
- El analista determinístico evita declarar ganador y trabaja con datos del corte.
- El test `test_flujo.py` cubre el guardrail principal del analista vivo.

---

## Qué está roto o frágil (estado al 2026-05-07, resuelto en v2.3)

- `SYSTEM_PROMPT` está embebido en `agent.py`, mezclado con lógica de proveedor.
- El prompt actual no cumple la estructura v2.3 de 5 secciones ni las reglas de MoE/no-respuesta/ponderación/series.
- `agent.py` no expone la interfaz mínima exacta `llm_call(...) -> str` solicitada.
- No hay metadata de trazabilidad normalizada para llamadas LLM: timestamp, provider, model, prompt version, schema version, tokens y latencia.
- La temperature default para reportes es 0.3, no 0.
- La validación estadística v2.3 no existe como unidad reutilizable.
- El contexto real del analista no coincide completamente con el schema v2.3 del prompt:
  - usa `total_votos` / `total_opiniones` en lugar de `tamano_muestra_actual`
  - usa `cobertura_pct` en lugar de `porcentaje_cobertura_geografica`
  - usa `suficiencia.minimo_opiniones` en lugar de `umbral_requerido`
  - no trae cortes demográficos ni motivadores de voto
  - no trae ponderacion_activa, design_effect ni tasa_no_respuesta

---

## Qué falta (estado al 2026-05-07, resuelto en v2.3)

- Separar prompts del transporte LLM.
- Agregar validador estadístico secuencial:
  - muestra global
  - coherencia interna
  - subgrupos demográficos
- Agregar prompt v2.3 en archivo/función separada.
- Agregar metadata de trazabilidad a llamadas single-shot.
- Mantener compatibilidad con el schema real actual sin exigir migraciones de BD.

---

## Límites de esta intervención

- No tocar pipeline de datos.
- No tocar gráficas frontend.
- No tocar schema de BD ni modelos.
- No reemplazar el módulo AI existente; solo refinarlo.

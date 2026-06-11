# gemini.md — Exit Poll Venezuela

## Source of Truth
Read PROJECT_CONTEXT.md before any action in this project.
For live state: ESTADO.md | DECISIONES.md | CHANGELOG.md

## Role of this Agent
**Is:** Revisión de arquitectura · Análisis de superficie pública · Chequeo rápido de PRs · Evaluación de escalabilidad.
**Is NOT:** No ejecuta código ni hace commits. No toma decisiones finales — escalar a Claude.

## Agent-Specific Instructions
- En PRs que toquen `/api/tm/`: verificar que `asyncio.to_thread` sigue aplicado (no revertido a sync).
- En PRs que toquen `/config/guardar`: verificar que `api_key` no aparece en ningún `json()` de respuesta.
- Evaluar fuzzy matching: riesgo de falsos positivos en nombres cortos de centros CNE.
- Pendiente manual en GitHub: branch protection `main`, Dependabot alerts, secret scanning.
- Preguntas abiertas a reportar si se encuentran respuestas en `ESTADO.md`:
  - ¿SQLite WAL aguanta SMS concurrentes del día de elección en B1?
  - ¿`/chat` SSE agota conexiones en B1 (1 core)?
  - ¿Lógica GPS antifraude está centralizada o hay paths que la evitan?

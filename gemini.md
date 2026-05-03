# Resumen de Interacciones con Gemini Code Assist

Este documento sirve como registro de las principales decisiones técnicas, hitos y desarrollos discutidos durante la asistencia de código para el proyecto **Exit Poll Venezuela**.

## Hitos Recientes del Desarrollo

1. **Dashboard en Vivo (SSE)**: Implementación de la actualización en tiempo real en `generador_dashboard.py` utilizando Server-Sent Events (SSE). Permite actualizar el mapa de *Folium* y las tendencias de *Plotly* de forma fluida sin recargar la página HTML.
2. **Carga Inteligente de Tabla de Mesa (AI)**: Desarrollo de la ruta de ingesta en `/tm` que utiliza la IA para leer estructuras variables de PDFs, Excel, CSV y Word, empleando *fuzzy matching* para alinear la geografía con la base de datos (`centros_candidatos`). Se implementó segmentación de *chunks* (15,000 caracteres) y lectura asíncrona para no bloquear el backend.
3. **Agente Analista Electoral**: Construcción de `agent.py` para soportar múltiples modelos (Gemini, OpenAI, Claude, Groq). Se implementaron *guardrails* estrictos para asegurar que la IA responda `datos insuficientes para establecer tendencias` cuando los cortes o la cobertura no alcanzan el mínimo, y analice estrictamente "opiniones" en lugar de "votos".
4. **Despliegue y Seguridad (Azure)**: Correcciones críticas para el arranque en Azure mediante `startup.py`, previniendo errores de finales de línea CRLF. Se mitigaron riesgos de seguridad removiendo credenciales en código duro e implementando inyección vía variables de entorno.
5. **Refactorización de Simuladores**: Modificación del agrupador en el simulador *showcase* para que las elecciones regionales y municipales no sobrescriban los diccionarios, y corrección en la renderización de candidatos no presidenciales.

## Puntos de Atención a Futuro

* **Pruebas Unitarias**: El sistema aún tiene una cobertura de pruebas muy débil (`test_flujo.py`). Se necesita añadir tests para las rutas FastAPI, los pesos por tipo de elección y las lógicas de aserción.
* **Escalabilidad de Extracción IA**: Si el volumen de PDFs escaneados incrementa dramáticamente, se consideró la implementación de un sistema de colas (*background jobs*) y reportes por SSE dedicados al progreso de ingesta.
* **Accesibilidad UI y Gestión de Conflictos**: Hay oportunidades de mejora en la tabla de revisión manual cuando hay colisiones (*CONFLICT*) en el fuzzy matching de los centros de votación.

---
*Nota: Este archivo puede ser actualizado en futuras sesiones para mantener el hilo del contexto del proyecto y sus prioridades.*
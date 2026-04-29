"""
Analista electoral deterministico para el dashboard en vivo.

Codex: este modulo evita modelos generativos y tokens; convierte metricas
estructuradas en explicaciones prudentes con guardrails explicitos.
"""

from __future__ import annotations

import math
from typing import Any


def _fmt_pct(valor: float | None, decimales: int = 1) -> str:
    if valor is None:
        return "N/D"
    return f"{valor:.{decimales}f}%"


def _margen_error_aprox(n: int) -> float | None:
    if n <= 0:
        return None
    return 1.96 * math.sqrt(0.25 / n) * 100


def _variacion_reciente(ventajas: list[float]) -> float | None:
    if len(ventajas) < 2:
        return None
    ultimas = ventajas[-3:]
    return max(ultimas) - min(ultimas)


def clasificar_contexto(contexto: dict[str, Any]) -> dict[str, Any]:
    total_votos = int(contexto.get("total_votos") or 0)
    cobertura = float(contexto.get("cobertura_pct") or 0)
    ventaja = contexto.get("ventaja_actual")
    ventajas = [float(v) for v in contexto.get("ventajas_nacionales") or []]

    margen = _margen_error_aprox(total_votos)
    variacion = _variacion_reciente(ventajas)

    if ventaja is None or total_votos < 100 or cobertura < 15:
        estado = "insuficiente"
    elif margen is not None and abs(float(ventaja)) <= margen:
        estado = "competitivo"
    elif variacion is not None and variacion <= 3 and total_votos >= 300:
        estado = "tendencia_consistente"
    else:
        estado = "ventaja_observada"

    confianza = 0
    if total_votos:
        confianza += min(35, total_votos / 20)
    confianza += min(35, cobertura * 0.7)
    if margen is not None and ventaja is not None:
        confianza += min(20, max(0, abs(float(ventaja)) - margen) * 2)
    if variacion is not None:
        confianza += max(0, 10 - min(10, variacion))

    return {
        "estado": estado,
        "margen_error_aprox": round(margen, 2) if margen is not None else None,
        "variacion_reciente": round(variacion, 2) if variacion is not None else None,
        "confianza_operativa": round(min(95, confianza), 1),
    }


def analizar_contexto(contexto: dict[str, Any], pregunta: str | None = None) -> dict[str, Any]:
    pregunta_l = (pregunta or "").strip().lower()
    lectura = clasificar_contexto(contexto)

    candidato_arriba = contexto.get("candidato_arriba") or "un candidato"
    candidato_abajo = contexto.get("candidato_abajo") or "el otro candidato"
    ventaja = contexto.get("ventaja_actual")
    total_votos = int(contexto.get("total_votos") or 0)
    cobertura = float(contexto.get("cobertura_pct") or 0)
    hora = contexto.get("hora_actual") or "este corte"
    margen = lectura["margen_error_aprox"]
    variacion = lectura["variacion_reciente"]

    advertencias = [
        "No se declara ganador: solo ventaja, desventaja o tendencia observada.",
        "Lectura basada unicamente en datos recibidos hasta el corte actual.",
    ]

    if total_votos == 0:
        resumen = (
            "Todavia no hay votos validos procesados. Con cero datos no es posible "
            "interpretar ventaja, tendencia ni estabilidad estadistica."
        )
    elif lectura["estado"] == "insuficiente":
        resumen = (
            f"Con los datos recibidos hasta {hora}, la muestra aun es insuficiente "
            f"para interpretar una tendencia. Hay {total_votos:,} votos validos y "
            f"una cobertura aproximada de {_fmt_pct(cobertura)} de los centros de muestra. "
            "Conviene esperar mas centros reportando antes de hablar de ventaja consolidada."
        )
    elif lectura["estado"] == "competitivo":
        resumen = (
            f"Con los datos recibidos hasta {hora}, {candidato_arriba} aparece con una "
            f"ventaja observada de {_fmt_pct(abs(float(ventaja)))} sobre {candidato_abajo}, "
            f"pero esa diferencia esta dentro o muy cerca del margen aproximado "
            f"({_fmt_pct(margen)}). La lectura correcta es escenario competitivo, no ganador."
        )
    elif lectura["estado"] == "tendencia_consistente":
        resumen = (
            f"Con los datos recibidos hasta {hora}, {candidato_arriba} mantiene una "
            f"ventaja consistente de {_fmt_pct(abs(float(ventaja)))} sobre {candidato_abajo}. "
            f"La variacion reciente es de {_fmt_pct(variacion)} y el margen aproximado es "
            f"{_fmt_pct(margen)}. Esto sugiere una tendencia favorable, sin declarar resultado final."
        )
    else:
        resumen = (
            f"Con los datos recibidos hasta {hora}, {candidato_arriba} tiene una ventaja "
            f"observada de {_fmt_pct(abs(float(ventaja)))} sobre {candidato_abajo}. "
            f"El margen aproximado es {_fmt_pct(margen)} y la cobertura va en "
            f"{_fmt_pct(cobertura)}. La ventaja existe, pero todavia debe monitorearse en cortes posteriores."
        )

    if any(p in pregunta_l for p in ("gana", "ganar", "ganador", "perdio", "perder")):
        resumen += (
            " En particular, ante preguntas sobre quien gana, este analista solo puede "
            "hablar de ventaja observada o tendencia; no declara ganadores."
        )

    return {
        "estado": lectura["estado"],
        "resumen": resumen,
        "metricas": {
            "total_votos": total_votos,
            "cobertura_pct": round(cobertura, 1),
            "ventaja_actual": ventaja,
            "margen_error_aprox": margen,
            "variacion_reciente": variacion,
            "confianza_operativa": lectura["confianza_operativa"],
        },
        "advertencias": advertencias,
    }

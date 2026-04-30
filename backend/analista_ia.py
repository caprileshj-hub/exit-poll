"""
Analista electoral deterministico para el dashboard en vivo.

Convierte metricas estructuradas en explicaciones prudentes con
guardrails explicitos. No usa modelos generativos ni tokens.
"""

from __future__ import annotations

import math
import unicodedata
from typing import Any

SIN_DATOS = "Esa información no está en los datos del exit poll."


# ── Utilidades ────────────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", (s or "").lower())
        if unicodedata.category(c) != "Mn"
    )


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


def _puntos_a_ventajas(puntos: list[dict]) -> list[float]:
    return [round(float(p["gob"]) - float(p["opo"]), 1) for p in puntos]


# ── Detección de intención ─────────────────────────────────────────────────

def _detectar_estado(pregunta: str, estados: dict) -> str | None:
    """Retorna la clave de estado (title-case) si se menciona en la pregunta."""
    preg = _norm(pregunta)
    # Ordenar por longitud descendente para que "Nueva Esparta" gane sobre "Esparta"
    for clave in sorted(estados, key=lambda k: len(k), reverse=True):
        if _norm(clave) in preg:
            return clave
    # Alias comunes
    alias = {
        "caracas": "Distrito Capital",
        "dc": "Distrito Capital",
        "distrito": "Distrito Capital",
        "vargas": "La Guaira",
        "guaira": "La Guaira",
        "margarita": "Nueva Esparta",
        "delta": "Delta Amacuro",
    }
    for token, estado_real in alias.items():
        if token in preg and estado_real in estados:
            return estado_real
    return None


def _detectar_candidato(pregunta: str, candidatos: dict) -> str | None:
    """Retorna el bando ('gobierno'/'oposicion') si se menciona su candidato."""
    preg = _norm(pregunta)
    for bando, nombre in candidatos.items():
        palabras = [p for p in _norm(nombre).split() if len(p) > 3]
        if any(p in preg for p in palabras):
            return bando
    return None


# ── Clasificación del contexto ────────────────────────────────────────────

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


# ── Análisis por estado ───────────────────────────────────────────────────

def _analizar_estado(nombre_estado: str, contexto: dict[str, Any]) -> dict[str, Any]:
    ventajas_por_estado = contexto.get("ventajas_por_estado") or {}
    tendencias_por_estado = contexto.get("tendencias_por_estado") or {}
    candidatos = contexto.get("candidatos") or {}
    hora = contexto.get("hora_actual") or "este corte"

    ventaja = ventajas_por_estado.get(nombre_estado)
    puntos = tendencias_por_estado.get(nombre_estado.upper()) or []
    ventajas_est = _puntos_a_ventajas(puntos)
    variacion = _variacion_reciente(ventajas_est)
    n_puntos = len(puntos)
    ventaja_nac = contexto.get("ventaja_actual")

    gob = candidatos.get("gobierno", "Gobierno")
    opo = candidatos.get("oposicion", "Oposición")

    if ventaja is None or n_puntos < 3:
        resumen = SIN_DATOS
        estado_lec = "sin_datos"
    else:
        arriba = gob if ventaja >= 0 else opo
        abajo = opo if ventaja >= 0 else gob
        dif = abs(ventaja)

        tendencia_txt = ""
        if n_puntos >= 2:
            dir_txt = "estable" if variacion is not None and variacion <= 2 else "con variación"
            tendencia_txt = f" La tendencia en {nombre_estado} es {dir_txt} ({n_puntos} cortes registrados)."

        diferencia_nac = ""
        if ventaja_nac is not None:
            diff = round(ventaja - ventaja_nac, 1)
            if abs(diff) >= 2:
                comp = "por encima" if diff > 0 else "por debajo"
                diferencia_nac = f" Esto está {_fmt_pct(abs(diff))} {comp} de la ventaja nacional del gobierno."

        resumen = (
            f"En {nombre_estado}, hasta {hora}, {arriba} tiene una ventaja observada "
            f"de {_fmt_pct(dif)} sobre {abajo}.{tendencia_txt}{diferencia_nac} "
            "Esta es una lectura parcial del corte actual."
        )
        estado_lec = "dato_disponible"

    return {
        "estado": estado_lec,
        "ambito": nombre_estado,
        "resumen": resumen,
        "metricas": {
            "ventaja_estado": ventaja,
            "n_cortes": n_puntos,
            "variacion_reciente": round(variacion, 2) if variacion is not None else None,
        },
        "advertencias": [
            "No se declara ganador: solo ventaja observada.",
            "Lectura basada únicamente en datos del corte actual.",
        ],
    }


# ── Análisis por candidato ────────────────────────────────────────────────

def _analizar_candidato(bando: str, contexto: dict[str, Any]) -> dict[str, Any]:
    candidatos = contexto.get("candidatos") or {}
    ventajas_por_estado = contexto.get("ventajas_por_estado") or {}
    ventaja_nac = contexto.get("ventaja_actual")
    total_votos = int(contexto.get("total_votos") or 0)
    cobertura = float(contexto.get("cobertura_pct") or 0)
    hora = contexto.get("hora_actual") or "este corte"

    nombre = candidatos.get(bando, bando)
    es_gobierno = bando == "gobierno"

    if total_votos < 100 or cobertura < 15:
        return {
            "estado": "insuficiente",
            "ambito": nombre,
            "resumen": SIN_DATOS,
            "metricas": {
                "total_opiniones": total_votos,
                "cobertura_pct": round(cobertura, 1),
            },
            "advertencias": [],
        }

    # Ventaja positiva = gobierno gana; negativa = oposición gana
    if ventaja_nac is None:
        pct_nac = None
    else:
        # ventaja = gob% - opo%, y gob% + opo% ≈ 100%
        if es_gobierno:
            pct_nac = round((100 + float(ventaja_nac)) / 2, 1)
        else:
            pct_nac = round((100 - float(ventaja_nac)) / 2, 1)

    # Conteo de estados ganados/perdidos
    ganados, perdidos = [], []
    for est, v in ventajas_por_estado.items():
        if (es_gobierno and v >= 0) or (not es_gobierno and v < 0):
            ganados.append(est)
        else:
            perdidos.append(est)

    n_gan = len(ganados)
    n_per = len(perdidos)
    n_tot = n_gan + n_per

    pct_txt = f"{_fmt_pct(pct_nac)} a nivel nacional" if pct_nac is not None else "porcentaje nacional no disponible aún"

    if n_tot == 0:
        estados_txt = "No hay datos por estado aún."
    else:
        estados_txt = (
            f"Lleva ventaja en {n_gan} de {n_tot} estados reportados"
            + (f" ({', '.join(ganados[:3])}{'...' if n_gan > 3 else ''})." if ganados else ".")
        )
        if perdidos:
            estados_txt += (
                f" Va abajo en {n_per} estado{'s' if n_per > 1 else ''}"
                f" ({', '.join(perdidos[:3])}{'...' if n_per > 3 else ''})."
            )

    resumen = (
        f"Hasta {hora}, {nombre} registra {pct_txt}. "
        f"{estados_txt} "
        f"Cobertura de muestra: {_fmt_pct(cobertura)} con {total_votos:,} opiniones validas procesadas. "
        "Esta lectura describe la tendencia observada, no el resultado final."
    )

    return {
        "estado": "dato_disponible" if pct_nac is not None or n_tot > 0 else "insuficiente",
        "ambito": nombre,
        "resumen": resumen,
        "metricas": {
            "pct_nacional": pct_nac,
            "estados_arriba": n_gan,
            "estados_abajo": n_per,
            "cobertura_pct": round(cobertura, 1),
        },
        "advertencias": [
            "No se declara ganador: solo tendencia observada.",
            "Lectura basada únicamente en datos del corte actual.",
        ],
    }


# ── Análisis nacional (original) ─────────────────────────────────────────

def _analizar_nacional(contexto: dict[str, Any], pregunta: str) -> dict[str, Any]:
    pregunta_l = _norm(pregunta)
    lectura = clasificar_contexto(contexto)

    candidatos = contexto.get("candidatos") or {}
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
        "Lectura basada únicamente en datos recibidos hasta el corte actual.",
    ]

    if total_votos == 0 or lectura["estado"] == "insuficiente":
        resumen = SIN_DATOS
    elif lectura["estado"] == "competitivo":
        resumen = (
            f"Con los datos recibidos hasta {hora}, {candidato_arriba} aparece con una "
            f"ventaja observada de {_fmt_pct(abs(float(ventaja)))} sobre {candidato_abajo}, "
            f"pero esa diferencia está dentro o muy cerca del margen aproximado "
            f"({_fmt_pct(margen)}). La lectura correcta es escenario competitivo, no ganador."
        )
    elif lectura["estado"] == "tendencia_consistente":
        resumen = (
            f"Con los datos recibidos hasta {hora}, {candidato_arriba} mantiene una "
            f"ventaja consistente de {_fmt_pct(abs(float(ventaja)))} sobre {candidato_abajo}. "
            f"La variación reciente es de {_fmt_pct(variacion)} y el margen aproximado es "
            f"{_fmt_pct(margen)}. Esto sugiere una tendencia favorable, sin declarar resultado final."
        )
    else:
        resumen = (
            f"Con los datos recibidos hasta {hora}, {candidato_arriba} tiene una ventaja "
            f"observada de {_fmt_pct(abs(float(ventaja)))} sobre {candidato_abajo}. "
            f"El margen aproximado es {_fmt_pct(margen)} y la cobertura va en "
            f"{_fmt_pct(cobertura)}. La ventaja existe, pero todavía debe monitorearse en cortes posteriores."
        )

    if any(p in pregunta_l for p in ("gana", "ganar", "ganador", "perdio", "perder")):
        resumen += (
            " En particular, ante preguntas sobre quién gana, este analista solo puede "
            "hablar de ventaja observada o tendencia; no declara ganadores."
        )

    return {
        "estado": lectura["estado"],
        "ambito": "nacional",
        "resumen": resumen,
        "metricas": {
            "total_opiniones": total_votos,
            "cobertura_pct": round(cobertura, 1),
            "ventaja_actual": ventaja,
            "margen_error_aprox": margen,
            "variacion_reciente": variacion,
            "confianza_operativa": lectura["confianza_operativa"],
        },
        "advertencias": advertencias,
    }


# ── Punto de entrada público ─────────────────────────────────────────────

def analizar_contexto(contexto: dict[str, Any], pregunta: str | None = None) -> dict[str, Any]:
    pregunta = (pregunta or "").strip()

    if not contexto.get("ok"):
        return {
            "estado": "sin_datos",
            "ambito": "nacional",
            "resumen": "No hay elección activa o no se recibieron datos.",
            "metricas": {},
            "advertencias": [],
        }

    ventajas_por_estado = contexto.get("ventajas_por_estado") or {}
    candidatos = contexto.get("candidatos") or {}

    estado_detectado = _detectar_estado(pregunta, ventajas_por_estado)
    if estado_detectado:
        return _analizar_estado(estado_detectado, contexto)

    bando_detectado = _detectar_candidato(pregunta, candidatos)
    if bando_detectado:
        return _analizar_candidato(bando_detectado, contexto)

    return _analizar_nacional(contexto, pregunta)

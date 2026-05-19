"""
Auditor de sesgo sistemático para estudios de exit poll.

Diagnostica componentes del Error Total de Encuesta (TSE):
1. Sesgo de no-respuesta diferencial / espiral del silencio
2. Error de afijación muestral (cobertura geográfica desbalanceada)
3. Efecto de diseño (DEFF) y su impacto en el MoE reportado
4. Consistencia del patrón de error entre estudios y entre estados

Uso desde app.py:
    from auditor_sesgo import diagnosticar_estudio
    sesgo = diagnosticar_estudio(e_gov, e_opos, o_gov, o_opos, ...)
"""

from __future__ import annotations
import math
from typing import Any

# Umbrales de magnitud del error (en pp)
UMBRAL_LEVE     = 1.0
UMBRAL_MODERADO = 2.5
UMBRAL_SEVERO   = 5.0

# ICC de referencia para encuestas por conglomerados en Venezuela
# Rango típico: 0.02–0.08. Valor conservador para estimación de DEFF.
ICC_REFERENCIA = 0.04

# Dirección del sesgo conocido en exit polls venezolanos 2006-2013:
# gobierno sistemáticamente subestimado (espiral del silencio + voto oculto).
SESGO_HISTORICO_ESPERADO = "gov_subestimado"


# ── Cálculos estadísticos ─────────────────────────────────────────────────────

def calcular_deff(n_respondentes: int, n_centros: int, icc: float = ICC_REFERENCIA) -> float | None:
    """
    Efecto de diseño por fórmula de Kish (1965): DEFF = 1 + (m̄ - 1) * ρ
    donde m̄ = n_respondentes / n_centros y ρ = ICC.
    """
    if n_centros <= 0 or n_respondentes <= 0:
        return None
    m_bar = n_respondentes / n_centros
    return 1.0 + (m_bar - 1) * icc


def calcular_moe(n: int, deff: float = 1.0, z: float = 1.96) -> float | None:
    """MoE ajustado por DEFF: z * sqrt(DEFF * p*q / n). Usa varianza máxima (p=0.5)."""
    if n <= 0:
        return None
    return z * math.sqrt(deff * 0.25 / n) * 100


# ── Clasificación ─────────────────────────────────────────────────────────────

def _magnitud(error_abs: float) -> str:
    if error_abs <= UMBRAL_LEVE:
        return "leve"
    if error_abs <= UMBRAL_MODERADO:
        return "moderado"
    if error_abs <= UMBRAL_SEVERO:
        return "severo"
    return "critico"


def _riesgo_global(magnitud: str, consistente_patron: bool | None, sesgo_est: dict) -> dict[str, Any]:
    niveles = {"leve": 1, "moderado": 2, "severo": 3, "critico": 4}
    n = niveles.get(magnitud, 2)
    if consistente_patron and sesgo_est.get("sesgo_consistente"):
        n = min(n + 1, 4)
    etiquetas = {1: "bajo", 2: "moderado", 3: "alto", 4: "critico"}
    return {
        "nivel": etiquetas[n],
        "puntaje": n,
        "causa_principal": (
            "sesgo_no_respuesta_diferencial"
            if consistente_patron
            else "indeterminado"
        ),
    }


# ── Componentes TSE ───────────────────────────────────────────────────────────

def _componentes_tse(
    delta_gov: float,
    delta_opos: float,
    n_centros: int,
    tasa_no_respuesta: float | None,
) -> list[dict[str, Any]]:
    comps: list[dict[str, Any]] = []

    # 1. Espiral del silencio / no-respuesta diferencial
    if delta_gov < -1.5 and delta_opos > 1.5:
        comps.append({
            "id": "sesgo_no_respuesta_diferencial",
            "label": "No-respuesta diferencial (espiral del silencio)",
            "probabilidad": "alta",
            "descripcion": (
                "Votantes del gobierno declaran su preferencia a menor tasa que opositores. "
                "Mecanismo: presencia de testigos de partidos, auto-censura, temor a represalias. "
                "Documentado en Venezuela 2006-2013 y entornos electorales no competitivos."
            ),
            "impacto_pp": round(abs(delta_gov), 2),
        })

    # 2. Asimetría confirmatoria (errores en direcciones opuestas)
    if delta_gov is not None and delta_opos is not None and (delta_gov * delta_opos < 0):
        comps.append({
            "id": "sesgo_cobertura_asimetrico",
            "label": "Sesgo asimétrico confirmatorio (errores de signo opuesto)",
            "probabilidad": "confirmada" if abs(delta_gov + delta_opos) < 1.5 else "alta",
            "descripcion": (
                "El error del gobierno y la oposición van en direcciones opuestas. "
                "Esto descarta ruido aleatorio: el sesgo es estructural. "
                "La suma de los errores absolutos da la magnitud total del desplazamiento."
            ),
            "impacto_pp": round(abs(delta_gov - delta_opos) / 2, 2),
        })

    # 3. Muestra pequeña → afijación desbalanceada
    if 0 < n_centros < 20:
        comps.append({
            "id": "error_afijacion_muestra_reducida",
            "label": f"Riesgo de afijación con muestra reducida ({n_centros} centros)",
            "probabilidad": "moderada",
            "descripcion": (
                f"Con {n_centros} centros, la sobre/subrepresentación de zonas "
                "geográficas (capital vs interior, urbano vs rural) puede introducir "
                "sesgo proporcional al peso relativo de esas zonas en el electorado."
            ),
            "impacto_pp": None,
        })

    # 4. No-respuesta desconocida
    if tasa_no_respuesta is None:
        comps.append({
            "id": "tasa_no_respuesta_ausente",
            "label": "Tasa de no-respuesta no registrada",
            "probabilidad": "sin_datos",
            "descripcion": (
                "Sin la tasa de no-respuesta es imposible cuantificar el sesgo de selección. "
                "Se asume riesgo no mitigado. Prioridad alta de registro en futuros estudios."
            ),
            "impacto_pp": None,
        })
    elif tasa_no_respuesta > 20:
        comps.append({
            "id": "alta_no_respuesta",
            "label": f"Alta tasa de no-respuesta ({tasa_no_respuesta:.1f}%)",
            "probabilidad": "alta",
            "descripcion": (
                f"Con {tasa_no_respuesta:.1f}% de no-respuesta el sesgo de selección "
                "es no ignorable incluso con ponderación. Requiere corrección por propensión."
            ),
            "impacto_pp": None,
        })

    return comps


# ── Análisis de consistencia por estado ──────────────────────────────────────

def _analizar_estados(estados_rows: list[dict]) -> dict[str, Any]:
    deltas = [
        r["delta_gov"]
        for r in estados_rows
        if r.get("delta_gov") is not None
    ]
    if len(deltas) < 3:
        return {"disponible": False, "razon": "pocos_estados_con_datos"}

    n = len(deltas)
    media = sum(deltas) / n
    varianza = sum((d - media) ** 2 for d in deltas) / n
    std = math.sqrt(varianza) if varianza >= 0 else 0.0
    negativos = sum(1 for d in deltas if d < -0.5)
    pct_neg = round(negativos / n * 100, 1)

    return {
        "disponible": True,
        "n_estados": n,
        "media_delta_gov": round(media, 2),
        "std_delta_gov": round(std, 2),
        "pct_estados_gov_subestimado": pct_neg,
        "sesgo_consistente": pct_neg >= 65,
    }


# ── Recomendaciones ───────────────────────────────────────────────────────────

def _recomendaciones(
    magnitud: str,
    direccion: str,
    consistente: bool | None,
    deff: float | None,
    tasa_no_respuesta: float | None,
    sesgo_estados: dict,
) -> list[str]:
    recs = []

    if tasa_no_respuesta is None:
        recs.append(
            "Registrar la tasa de no-respuesta por centro (rechazos / (aceptaciones + rechazos)). "
            "Sin este dato el componente de sesgo de selección es no cuantificable."
        )

    if direccion == "gov_subestimado" and consistente:
        recs.append(
            "Implementar corrección por espiral del silencio: ajustar con modelo de propensión a responder "
            "usando covariables observables (zona geográfica, hora del día, densidad de observadores). "
            "Alternativamente: aplicar raking post-estratificado con márgenes del padrón CNE por estado."
        )

    if deff is not None and deff > 1.5:
        recs.append(
            f"DEFF estimado = {deff:.2f} (ICC={ICC_REFERENCIA}). El n efectivo es "
            f"≈ n / {deff:.2f}. Ajustar MoE reportado y los umbrales de 'datos suficientes' "
            "en ai_validation.py (umbral_requerido debe multiplicarse por DEFF)."
        )
    elif deff is None:
        recs.append(
            "Registrar el número total de respondentes (no solo centros) para calcular DEFF real. "
            "El MoE actual usa DEFF=1 (SRSWOR), lo que subestima el intervalo de confianza real."
        )

    if magnitud in ("severo", "critico"):
        recs.append(
            "Error > 2.5 pp: el estudio supera el umbral operativo. Revisar el marco de afijación "
            "muestral: comparar peso electoral real de cada estado (padrón CNE) vs peso implícito "
            "en la muestra. Corregir con post-estratificación jerárquica."
        )

    if sesgo_estados.get("sesgo_consistente") and sesgo_estados.get("pct_estados_gov_subestimado", 0) >= 70:
        pct = sesgo_estados["pct_estados_gov_subestimado"]
        recs.append(
            f"{pct}% de los estados muestran subestimación del gobierno. El sesgo es sistémico. "
            "Aplicar factor de corrección global calibrado con el promedio histórico de los deltas "
            "como prior bayesiano (o corrección determinística iterativa)."
        )

    return recs


# ── Punto de entrada público ──────────────────────────────────────────────────

def diagnosticar_estudio(
    e_gov: float | None,
    e_opos: float | None,
    o_gov: float | None,
    o_opos: float | None,
    n_centros: int = 0,
    n_respondentes: int = 0,
    tasa_no_respuesta: float | None = None,
    estados_rows: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Diagnóstico completo de sesgo para un estudio histórico.

    Parámetros:
        e_gov, e_opos   — porcentajes del exit poll (estudio)
        o_gov, o_opos   — porcentajes del resultado oficial
        n_centros       — número de centros en la muestra del estudio
        n_respondentes  — total de respondentes (0 si no disponible)
        tasa_no_respuesta — % de no-respuesta (None si no registrado)
        estados_rows    — lista de dicts con delta_gov por estado (de _estudios_pivot)

    Retorna dict con claves:
        disponible, sesgo_nacional, tse_componentes, deff_estimado,
        moe_srs_pp, moe_ajustado_pp, sesgo_estados, riesgo_metodologico, recomendaciones
    """
    if e_gov is None or o_gov is None:
        return {"disponible": False, "razon": "sin_datos_suficientes"}

    delta_gov  = round(e_gov - o_gov, 2)
    delta_opos = round(e_opos - o_opos, 2) if (e_opos is not None and o_opos is not None) else None
    e_brecha   = round(e_gov - e_opos, 2)  if e_opos is not None else None
    o_brecha   = round(o_gov - o_opos, 2)  if o_opos is not None else None
    delta_brecha = round(e_brecha - o_brecha, 2) if (e_brecha is not None and o_brecha is not None) else None

    error_abs = abs(delta_gov)
    magnitud  = _magnitud(error_abs)

    if delta_gov < -0.5:
        direccion = "gov_subestimado"
        consistente = True
    elif delta_gov > 0.5:
        direccion = "gov_sobreestimado"
        consistente = False
    else:
        direccion = "neutro"
        consistente = None

    deff     = calcular_deff(n_respondentes, n_centros) if n_respondentes > 0 and n_centros > 0 else None
    moe_srs  = calcular_moe(n_respondentes, deff=1.0)   if n_respondentes > 0 else None
    moe_adj  = calcular_moe(n_respondentes, deff=deff)  if n_respondentes > 0 and deff else None

    sesgo_estados = _analizar_estados(estados_rows or [])

    return {
        "disponible": True,
        "sesgo_nacional": {
            "delta_gov": delta_gov,
            "delta_opos": delta_opos,
            "delta_brecha": delta_brecha,
            "error_abs": error_abs,
            "magnitud": magnitud,
            "direccion": direccion,
            "consistente_patron_historico": consistente,
        },
        "tse_componentes": _componentes_tse(
            delta_gov, delta_opos or 0.0, n_centros, tasa_no_respuesta
        ),
        "deff_estimado": round(deff, 3) if deff else None,
        "moe_srs_pp":     round(moe_srs, 2) if moe_srs else None,
        "moe_ajustado_pp": round(moe_adj, 2) if moe_adj else None,
        "sesgo_estados": sesgo_estados,
        "riesgo_metodologico": _riesgo_global(magnitud, consistente, sesgo_estados),
        "recomendaciones": _recomendaciones(
            magnitud, direccion, consistente, deff, tasa_no_respuesta, sesgo_estados
        ),
    }

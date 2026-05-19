from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

INSUFFICIENT_MESSAGE = "datos insuficientes para establecer tendencias"


@dataclass
class ValidationResult:
    ok: bool
    message: str | None = None
    reason: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    schema_differences: list[str] = field(default_factory=list)


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _metadata(context: dict[str, Any]) -> dict[str, Any]:
    return context.get("metadata_metodologica") or {}


def _schema_value(context: dict[str, Any], key: str, fallback: Any = None) -> Any:
    return context.get(key, fallback)


def _mark_missing(
    normalized: dict[str, Any],
    differences: list[str],
    field: str,
    message: str,
) -> None:
    missing = normalized.setdefault("campos_ausentes_schema", [])
    if field not in missing:
        missing.append(field)
    warnings = normalized.setdefault("advertencias_metodologicas", [])
    warning = f"{field}: ausente en el schema real; no inferir ni completar."
    if warning not in warnings:
        warnings.append(warning)
    differences.append(message)


def normalize_context(context: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Map the current app context to the v2.3 report schema without changing DB code."""
    normalized = deepcopy(context)
    differences: list[str] = []
    legacy_sufficient = bool(context.get("datos_suficientes", False))

    if "tamano_muestra_actual" not in normalized:
        normalized["tamano_muestra_actual"] = _as_int(
            context.get("total_opiniones", context.get("total_votos", 0))
        )
        differences.append("schema real usa total_opiniones/total_votos; adaptado a tamano_muestra_actual")

    suficiencia = context.get("suficiencia") or {}
    if "umbral_requerido" not in normalized:
        default_threshold = normalized["tamano_muestra_actual"] if legacy_sufficient else 100
        normalized["umbral_requerido"] = _as_int(suficiencia.get("minimo_opiniones"), default_threshold)
        differences.append("schema real usa suficiencia.minimo_opiniones; adaptado a umbral_requerido")

    if "porcentaje_cobertura_geografica" not in normalized:
        default_geo = 100.0 if legacy_sufficient and context.get("cobertura_pct") is None else 0.0
        normalized["porcentaje_cobertura_geografica"] = _as_float(context.get("cobertura_pct"), default_geo)
        differences.append("schema real usa cobertura_pct; adaptado a porcentaje_cobertura_geografica")

    if "cobertura_minima_requerida" not in normalized:
        normalized["cobertura_minima_requerida"] = _as_float(suficiencia.get("minimo_cobertura_pct"), 15.0)
        differences.append("schema real usa suficiencia.minimo_cobertura_pct; adaptado a cobertura_minima_requerida")

    if "porcentaje_cobertura_horaria" not in normalized:
        cortes = _as_int(suficiencia.get("cortes"), 0)
        minimo_cortes = max(1, _as_int(suficiencia.get("minimo_cortes"), 3))
        if not cortes and legacy_sufficient:
            normalized["porcentaje_cobertura_horaria"] = 100.0
        else:
            normalized["porcentaje_cobertura_horaria"] = min(100.0, round(100.0 * cortes / minimo_cortes, 1))
        differences.append("schema real usa numero de cortes; adaptado a porcentaje_cobertura_horaria")

    if "cobertura_horaria_minima" not in normalized:
        normalized["cobertura_horaria_minima"] = 100.0
        differences.append("schema real no trae cobertura_horaria_minima; se exige completar minimo_cortes")

    if "estado_muestra" not in normalized:
        datos_suficientes = bool(suficiencia.get("datos_suficientes", context.get("datos_suficientes", False)))
        normalized["estado_muestra"] = "SUFICIENTE" if datos_suficientes else "INSUFICIENTE"
        differences.append("schema real usa datos_suficientes booleano; adaptado a estado_muestra")

    if "umbral_subgrupo_minimo_bruto" not in normalized:
        normalized["umbral_subgrupo_minimo_bruto"] = 30
        differences.append("schema real no trae umbral_subgrupo_minimo_bruto; default conservador 30")

    if "umbral_supresion_privacidad" not in normalized:
        normalized["umbral_supresion_privacidad"] = 5
        differences.append("schema real no trae umbral_supresion_privacidad; default 5")

    if "margen_error_global" not in normalized:
        n = _as_int(normalized.get("tamano_muestra_actual"), 0)
        normalized["margen_error_global"] = round(1.96 * ((0.25 / n) ** 0.5) * 100, 2) if n > 0 else None
        differences.append("schema real no trae margen_error_global; calculado aproximado con maxima varianza")

    if "ponderacion_activa" not in normalized:
        normalized["ponderacion_activa"] = None
        _mark_missing(
            normalized,
            differences,
            "ponderacion_activa",
            "schema real no trae ponderacion_activa; flag explicito de ausencia",
        )

    if "cortes_demograficos" not in normalized:
        normalized["cortes_demograficos"] = {}
        _mark_missing(
            normalized,
            differences,
            "cortes_demograficos",
            "schema real no trae cortes_demograficos; se inicializa vacio y se marca ausente",
        )

    if "motivadores_voto" not in normalized:
        normalized["motivadores_voto"] = {}
        _mark_missing(
            normalized,
            differences,
            "motivadores_voto",
            "schema real no trae motivadores_voto; se inicializa vacio y se marca ausente",
        )

    normalized.setdefault("series_temporales", context.get("ventajas_nacionales") or [])
    metadata = deepcopy(_metadata(normalized))
    if "design_effect_estimado" not in metadata:
        metadata["design_effect_estimado"] = None
        _mark_missing(
            normalized,
            differences,
            "metadata_metodologica.design_effect_estimado",
            "schema real no trae design_effect_estimado; flag explicito de ausencia",
        )
    if "tasa_no_respuesta" not in metadata:
        metadata["tasa_no_respuesta"] = None
        _mark_missing(
            normalized,
            differences,
            "metadata_metodologica.tasa_no_respuesta",
            "schema real no trae tasa_no_respuesta; flag explicito de ausencia",
        )
    metadata["campos_ausentes"] = list(normalized.get("campos_ausentes_schema", []))
    metadata["advertencias_metodologicas"] = list(normalized.get("advertencias_metodologicas", []))
    normalized["metadata_metodologica"] = metadata
    _apply_methodological_flags(normalized)
    normalized["schema_differences"] = differences
    return normalized, differences


def _add_flag(context: dict[str, Any], flag: str) -> None:
    flags = context.setdefault("flags_metodologicos", [])
    if flag not in flags:
        flags.append(flag)
    metadata = context.setdefault("metadata_metodologica", {})
    meta_flags = metadata.setdefault("flags_metodologicos", [])
    if flag not in meta_flags:
        meta_flags.append(flag)


def _apply_methodological_flags(context: dict[str, Any]) -> None:
    metadata = context.get("metadata_metodologica") or {}
    tasa_no_respuesta = metadata.get("tasa_no_respuesta")
    if tasa_no_respuesta is not None and _as_float(tasa_no_respuesta) > 15:
        _add_flag(context, "ALTA_NO_RESPUESTA")

    # Corregir MoE con DEFF cuando está disponible
    deff = _as_float(metadata.get("design_effect_estimado"), 0.0)
    n = _as_int(context.get("tamano_muestra_actual"), 0)
    if deff > 1.0 and n > 0:
        import math as _math
        moe_adj = round(1.96 * _math.sqrt(deff * 0.25 / n) * 100, 2)
        context["margen_error_global"] = moe_adj
        context["margen_error_ajustado_por_deff"] = True
        _add_flag(context, "MOE_AJUSTADO_POR_DEFF")

    # Flag sesgo direccional: tasa desconocida + contexto de voto oculto
    if tasa_no_respuesta is None:
        _add_flag(context, "SESGO_NO_RESPUESTA_NO_CUANTIFICADO")

    margin = context.get("margen_error_global")
    if margin is None:
        return
    otros = (context.get("distribucion_general") or {}).get("Otros")
    if isinstance(otros, dict) and _as_float(otros.get("porcentaje")) > _as_float(margin):
        _add_flag(context, "OTROS_SIGNIFICATIVO")


def validate_ai_context(context: dict[str, Any]) -> ValidationResult:
    normalized, differences = normalize_context(context)
    notes: list[str] = []

    n = _as_int(_schema_value(normalized, "tamano_muestra_actual"), 0)
    threshold = _as_int(_schema_value(normalized, "umbral_requerido"), 0)
    geo = _as_float(_schema_value(normalized, "porcentaje_cobertura_geografica"), 0.0)
    min_geo = _as_float(_schema_value(normalized, "cobertura_minima_requerida"), 0.0)
    hourly = _as_float(_schema_value(normalized, "porcentaje_cobertura_horaria"), 0.0)
    min_hourly = _as_float(_schema_value(normalized, "cobertura_horaria_minima"), 0.0)

    failures = []
    if n < threshold:
        failures.append(f"muestra {n} < umbral {threshold}")
    if geo < min_geo:
        failures.append(f"cobertura geografica {geo:.1f}% < minimo {min_geo:.1f}%")
    if hourly < min_hourly:
        failures.append(f"cobertura horaria {hourly:.1f}% < minimo {min_hourly:.1f}%")

    estado = str(normalized.get("estado_muestra") or "").upper()
    if estado == "SUFICIENTE" and n < threshold:
        return ValidationResult(
            ok=False,
            message="contradiccion estadistica: estado_muestra=SUFICIENTE con N menor al umbral requerido",
            reason=f"estado_muestra=SUFICIENTE pero {n} < {threshold}",
            context=normalized,
            notes=notes,
            schema_differences=differences,
        )

    if failures:
        return ValidationResult(
            ok=False,
            message=INSUFFICIENT_MESSAGE,
            reason="; ".join(failures),
            context=normalized,
            notes=notes,
            schema_differences=differences,
        )

    normalized["cortes_demograficos"] = _validate_demographics(normalized, notes)
    normalized["validation_notes"] = notes
    return ValidationResult(
        ok=True,
        context=normalized,
        notes=notes,
        schema_differences=differences,
    )


def _validate_demographics(context: dict[str, Any], notes: list[str]) -> dict[str, Any]:
    cuts = context.get("cortes_demograficos") or {}
    min_raw = _as_int(context.get("umbral_subgrupo_minimo_bruto"), 30)
    privacy = _as_int(context.get("umbral_supresion_privacidad"), 5)
    global_moe = context.get("margen_error_global")
    validated: dict[str, Any] = {}

    for variable, strata in cuts.items():
        if not isinstance(strata, dict):
            notes.append(f"{variable}: omitida porque no tiene estructura de estratos")
            continue

        kept: dict[str, Any] = {}
        excluded_count = 0
        privacy_count = 0
        for name, payload in strata.items():
            item = deepcopy(payload) if isinstance(payload, dict) else {"valor": payload}
            n_raw = _as_int(item.get("n_bruta"), 0)
            if n_raw < privacy:
                item = {
                    "n_bruta": n_raw,
                    "suprimido_privacidad": True,
                    "excluido_estadistico": True,
                    "valor_suprimido": True,
                }
                privacy_count += 1
                excluded_count += 1
            elif n_raw < min_raw:
                item["excluido_estadistico"] = True
                excluded_count += 1
            else:
                item["excluido_estadistico"] = False
                item["suprimido_privacidad"] = False
            if not item.get("suprimido_privacidad") and "moe_subgrupo" not in item and global_moe is not None:
                item["moe_usado"] = global_moe
                item["advertencia_moe"] = "moe_subgrupo ausente; se usa margen_error_global."
                notes.append(f"{variable}.{name}: moe_subgrupo ausente; se usa margen_error_global")
            kept[name] = item

        if kept and excluded_count == len(kept):
            validated[variable] = {
                "_variable_colapsada": True,
                "nota": "Todos los estratos fueron excluidos por umbral estadistico o privacidad.",
            }
            notes.append(f"{variable}: variable colapsada completa por insuficiencia de estratos")
        else:
            validated[variable] = kept
            if excluded_count:
                notes.append(f"{variable}: {excluded_count} estratos excluidos por n_bruta insuficiente")
            if privacy_count:
                notes.append(f"{variable}: {privacy_count} estratos suprimidos por privacidad")

    return validated

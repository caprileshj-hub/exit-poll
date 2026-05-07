from __future__ import annotations

from backend import agent
from backend.ai_validation import INSUFFICIENT_MESSAGE, validate_ai_context


def _base_context() -> dict:
    return {
        "estado_muestra": "SUFICIENTE",
        "tamano_muestra_actual": 120,
        "umbral_requerido": 100,
        "porcentaje_cobertura_geografica": 25,
        "cobertura_minima_requerida": 15,
        "porcentaje_cobertura_horaria": 100,
        "cobertura_horaria_minima": 100,
        "umbral_subgrupo_minimo_bruto": 30,
        "umbral_supresion_privacidad": 5,
    }


def test_validador_aborta_si_muestra_global_insuficiente():
    context = _base_context()
    context["tamano_muestra_actual"] = 80
    context["estado_muestra"] = "INSUFICIENTE"

    result = validate_ai_context(context)

    assert not result.ok
    assert result.message == INSUFFICIENT_MESSAGE
    assert "muestra 80 < umbral 100" in (result.reason or "")


def test_validador_detecta_contradiccion_estado_suficiente_con_n_bajo():
    context = _base_context()
    context["tamano_muestra_actual"] = 80
    context["estado_muestra"] = "SUFICIENTE"

    result = validate_ai_context(context)

    assert not result.ok
    assert "contradiccion estadistica" in (result.message or "")


def test_validador_colapsa_variable_demografica_si_todos_los_estratos_fallan():
    context = _base_context()
    context["cortes_demograficos"] = {
        "edad": {
            "18-24": {"porcentaje": 55, "n_bruta": 10},
            "25-34": {"porcentaje": 45, "n_bruta": 20},
        }
    }

    result = validate_ai_context(context)

    assert result.ok
    assert result.context["cortes_demograficos"]["edad"]["_variable_colapsada"] is True
    assert any("edad: variable colapsada" in note for note in result.notes)


def test_validador_adapta_contexto_legado_suficiente_de_chat():
    context = {
        "ok": True,
        "datos_suficientes": True,
        "total_opiniones": 120,
        "conteos_de_opiniones_por_candidato": [],
        "ultimos_3_turnos": [],
    }

    result = validate_ai_context(context)

    assert result.ok
    assert result.context["tamano_muestra_actual"] == 120
    assert result.context["porcentaje_cobertura_geografica"] == 100
    assert result.schema_differences


def test_adaptador_marca_campos_v23_ausentes_explicitamente():
    context = {
        "ok": True,
        "datos_suficientes": True,
        "total_opiniones": 120,
    }

    result = validate_ai_context(context)

    missing = result.context["campos_ausentes_schema"]
    assert "cortes_demograficos" in missing
    assert "motivadores_voto" in missing
    assert "ponderacion_activa" in missing
    assert "metadata_metodologica.design_effect_estimado" in missing
    assert "metadata_metodologica.tasa_no_respuesta" in missing

    metadata = result.context["metadata_metodologica"]
    assert metadata["design_effect_estimado"] is None
    assert metadata["tasa_no_respuesta"] is None
    assert metadata["campos_ausentes"] == missing
    assert metadata["advertencias_metodologicas"]


def test_ask_agent_no_llama_llm_si_contexto_insuficiente(monkeypatch):
    def fail_if_called(_cfg):
        raise AssertionError("LLM no debio ser llamado")

    monkeypatch.setattr(agent, "_openai_client", fail_if_called)
    context = {
        "estado_muestra": "INSUFICIENTE",
        "tamano_muestra_actual": 10,
        "umbral_requerido": 100,
        "porcentaje_cobertura_geografica": 5,
        "cobertura_minima_requerida": 15,
        "porcentaje_cobertura_horaria": 0,
        "cobertura_horaria_minima": 100,
    }

    chunks = list(agent.ask_agent("resume", context, "openai", {"api_key": "test"}))

    assert chunks == [INSUFFICIENT_MESSAGE]


def test_subgrupo_bajo_umbral_estadistico_queda_excluido_con_nota():
    context = _base_context()
    context["cortes_demograficos"] = {
        "edad": {
            "18-24": {"porcentaje": 55, "n_bruta": 20},
            "25-34": {"porcentaje": 45, "n_bruta": 40},
        }
    }

    result = validate_ai_context(context)

    assert result.ok
    assert result.context["cortes_demograficos"]["edad"]["18-24"]["excluido_estadistico"] is True
    assert result.context["cortes_demograficos"]["edad"]["25-34"]["excluido_estadistico"] is False
    assert any("edad: 1 estratos excluidos" in note for note in result.notes)


def test_subgrupo_bajo_umbral_privacidad_queda_suprimido_sin_valores():
    context = _base_context()
    context["cortes_demograficos"] = {
        "sexo": {
            "No binario": {"porcentaje": 70, "n_bruta": 3},
            "Femenino": {"porcentaje": 48, "n_bruta": 50},
        }
    }

    result = validate_ai_context(context)

    suppressed = result.context["cortes_demograficos"]["sexo"]["No binario"]
    assert suppressed["suprimido_privacidad"] is True
    assert suppressed["valor_suprimido"] is True
    assert "porcentaje" not in suppressed


def test_moe_subgrupo_ausente_usa_moe_global_con_advertencia():
    context = _base_context()
    context["margen_error_global"] = 4.2
    context["cortes_demograficos"] = {
        "edad": {
            "25-34": {"porcentaje": 45, "n_bruta": 40},
        }
    }

    result = validate_ai_context(context)

    stratum = result.context["cortes_demograficos"]["edad"]["25-34"]
    assert stratum["moe_usado"] == 4.2
    assert "margen_error_global" in stratum["advertencia_moe"]


def test_tasa_no_respuesta_alta_agrega_flag_metodologico():
    context = _base_context()
    context["metadata_metodologica"] = {
        "tasa_no_respuesta": 16,
        "design_effect_estimado": 1.2,
    }

    result = validate_ai_context(context)

    assert "ALTA_NO_RESPUESTA" in result.context["flags_metodologicos"]
    assert "ALTA_NO_RESPUESTA" in result.context["metadata_metodologica"]["flags_metodologicos"]


def test_otros_mayor_que_moe_global_agrega_flag_metodologico():
    context = _base_context()
    context["margen_error_global"] = 4.0
    context["distribucion_general"] = {
        "Candidata A": {"porcentaje": 50, "n_bruta": 60},
        "Otros": {"porcentaje": 5.1, "n_bruta": 10},
    }

    result = validate_ai_context(context)

    assert "OTROS_SIGNIFICATIVO" in result.context["flags_metodologicos"]
    assert "OTROS_SIGNIFICATIVO" in result.context["metadata_metodologica"]["flags_metodologicos"]


def test_ask_agent_aborta_contexto_insuficiente_sin_requerir_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    context = {
        "estado_muestra": "INSUFICIENTE",
        "tamano_muestra_actual": 10,
        "umbral_requerido": 100,
        "porcentaje_cobertura_geografica": 5,
        "cobertura_minima_requerida": 15,
        "porcentaje_cobertura_horaria": 0,
        "cobertura_horaria_minima": 100,
    }

    chunks = list(agent.ask_agent("resume", context, "openai", {}))

    assert chunks == [INSUFFICIENT_MESSAGE]


def test_provider_config_acepta_google_como_alias_de_gemini(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    cfg = agent._provider_config("google", {"model": "gemini-1.5-pro"})

    assert cfg["provider"] == "google"
    assert cfg["client"] == "openai"
    assert cfg["model"] == "gemini-1.5-pro"

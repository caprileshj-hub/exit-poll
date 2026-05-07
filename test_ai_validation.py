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

from __future__ import annotations

import os
from typing import Any, Iterator


SYSTEM_PROMPT = """
Eres un analista especializado en exit polls electorales.
SOLO respondes preguntas basadas en los datos del proceso electoral en curso.
Tienes acceso a: conteos de opiniones por candidato, tendencias por turno de 20 minutos,
e historial de centros electorales de procesos anteriores.
El sistema registra opiniones de participantes, no votos oficiales. Nunca uses la palabra "votos" para describir los datos del exit poll.
No hagas analisis nacional, estadal, municipal, por centro ni por candidato si los datos de ese ambito son insuficientes.
Considera insuficiente cualquier ambito sin opiniones validas, sin cobertura minima, sin al menos 3 cortes comparables, o marcado como datos_suficientes=false en el contexto.

Formato de respuesta obligatorio:
TENDENCIA: [qué está ocurriendo en este momento]
ANOMALÍA: [algo estadísticamente inusual, o "ninguna detectada"]
PROYECCIÓN: [dirección probable al cierre basada en la tendencia actual]

Si la pregunta no puede responderse con los datos disponibles, responde 
exactamente: "datos insuficientes para establecer tendencias"
No especules. No uses conocimiento externo. Temperatura mental: mínima.
"""


AI_PROVIDERS = {
    "openai": {
        "model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
        "client": "openai",
        "base_url": None,
    },
    "groq": {
        "model": "llama-3.1-8b-instant",
        "env_key": "GROQ_API_KEY",
        "client": "openai",
        "base_url": "https://api.groq.com/openai/v1",
    },
    "anthropic": {
        "model": "claude-haiku-4-5-20251001",
        "env_key": "ANTHROPIC_API_KEY",
        "client": "anthropic",
        "base_url": None,
    },
    "gemini": {
        "model": "gemini-2.5-flash",
        "env_key": "GEMINI_API_KEY",
        "client": "openai",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    },
}


def _provider_config(provider: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    if provider not in AI_PROVIDERS:
        raise ValueError(f"Proveedor no soportado: {provider}")
    cfg = {**AI_PROVIDERS[provider], **(overrides or {})}
    cfg["model"] = cfg.get("model") or AI_PROVIDERS[provider]["model"]
    cfg["temperature"] = float(cfg.get("temperature", 0.3))
    cfg["max_tokens"] = int(cfg.get("max_tokens", 300))
    cfg["api_key"] = cfg.get("api_key") or os.getenv(cfg["env_key"])
    if not cfg["api_key"]:
        raise RuntimeError(f"Falta API key para {provider}. Configure {cfg['env_key']} o la tabla config.")
    return cfg


def _messages(question: str, context: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT.strip()},
        {
            "role": "user",
            "content": (
                "Datos disponibles del exit poll:\n"
                f"{context}\n\n"
                f"Pregunta: {question}"
            ),
        },
    ]


def _ask_openai_compatible(question: str, context: dict[str, Any], cfg: dict[str, Any]) -> Iterator[str]:
    from openai import OpenAI

    kwargs = {"api_key": cfg["api_key"]}
    if cfg.get("base_url"):
        kwargs["base_url"] = cfg["base_url"]
    client = OpenAI(**kwargs)
    stream = client.chat.completions.create(
        model=cfg["model"],
        messages=_messages(question, context),
        temperature=cfg["temperature"],
        max_tokens=cfg["max_tokens"],
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta


def _ask_anthropic(question: str, context: dict[str, Any], cfg: dict[str, Any]) -> Iterator[str]:
    from anthropic import Anthropic

    client = Anthropic(api_key=cfg["api_key"])
    user_content = (
        "Datos disponibles del exit poll:\n"
        f"{context}\n\n"
        f"Pregunta: {question}"
    )
    with client.messages.stream(
        model=cfg["model"],
        max_tokens=cfg["max_tokens"],
        temperature=cfg["temperature"],
        system=SYSTEM_PROMPT.strip(),
        messages=[{"role": "user", "content": user_content}],
    ) as stream:
        for text in stream.text_stream:
            if text:
                yield text


def ask_agent(
    question: str,
    context: dict[str, Any],
    provider: str,
    config: dict[str, Any] | None = None,
) -> Iterator[str]:
    cfg = _provider_config(provider, config)
    if cfg["client"] == "anthropic":
        yield from _ask_anthropic(question, context, cfg)
    else:
        yield from _ask_openai_compatible(question, context, cfg)

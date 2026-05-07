from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Iterator

try:
    from ai_prompts import PROMPT_VERSION, SCHEMA_VERSION, report_system_prompt
    from ai_validation import INSUFFICIENT_MESSAGE, validate_ai_context
except ImportError:  # pragma: no cover - supports importing as backend.agent in tests
    from backend.ai_prompts import PROMPT_VERSION, SCHEMA_VERSION, report_system_prompt
    from backend.ai_validation import INSUFFICIENT_MESSAGE, validate_ai_context


SYSTEM_PROMPT = report_system_prompt()


AI_PROVIDERS = {
    "openai": {
        "model": "gpt-4o",
        "models": ["gpt-4o", "gpt-4-turbo", "gpt-4o-mini"],
        "env_key": "OPENAI_API_KEY",
        "client": "openai",
        "base_url": None,
    },
    "groq": {
        "model": "llama-3.1-8b-instant",
        "models": ["llama-3.1-8b-instant"],
        "env_key": "GROQ_API_KEY",
        "client": "openai",
        "base_url": "https://api.groq.com/openai/v1",
    },
    "anthropic": {
        "model": "claude-sonnet-4-5",
        "models": ["claude-opus-4-5", "claude-sonnet-4-5", "claude-haiku-4-5-20251001"],
        "env_key": "ANTHROPIC_API_KEY",
        "client": "anthropic",
        "base_url": None,
    },
    "gemini": {
        "model": "gemini-1.5-pro",
        "models": ["gemini-1.5-pro", "gemini-2.5-flash"],
        "env_key": "GEMINI_API_KEY",
        "client": "openai",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    },
}

PROVIDER_ALIASES = {
    "google": "gemini",
}


def _provider_config(provider: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    requested_provider = provider
    provider = PROVIDER_ALIASES.get(provider, provider)
    if provider not in AI_PROVIDERS:
        raise ValueError(f"Proveedor no soportado: {requested_provider}")

    cfg = {**AI_PROVIDERS[provider], **(overrides or {})}
    cfg["provider"] = requested_provider
    cfg["model"] = cfg.get("model") or AI_PROVIDERS[provider]["model"]
    cfg["temperature"] = float(cfg.get("temperature", 0))
    cfg["max_tokens"] = int(cfg.get("max_tokens", 300))
    # API key priority: 1) Azure App Settings/env var, 2) SQLite config table.
    # This avoids keeping production tied to an old key saved in SQLite.
    cfg["api_key"] = os.getenv(cfg["env_key"]) or cfg.get("api_key")
    if not cfg["api_key"]:
        raise RuntimeError(f"Falta API key para {provider}. Configure {cfg['env_key']} o la tabla config.")
    return cfg


def _metadata(cfg: dict[str, Any], latency_ms: int | None, tokens_used: int | None) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": cfg.get("provider"),
        "model": cfg.get("model"),
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "tokens_used": tokens_used,
        "latency_ms": latency_ms,
    }


def _metadata_footer(metadata: dict[str, Any]) -> str:
    return "\n\n---\nMETADATA\n" + json.dumps(metadata, ensure_ascii=False, sort_keys=True)


def _messages(question: str, context: dict[str, Any], system_prompt: str | None = None) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": (system_prompt or SYSTEM_PROMPT).strip()},
        {
            "role": "user",
            "content": (
                "Datos disponibles del exit poll:\n"
                f"{json.dumps(context, ensure_ascii=False, indent=2, default=str)}\n\n"
                f"Pregunta: {question}"
            ),
        },
    ]


def _openai_client(cfg: dict[str, Any]):
    from openai import OpenAI

    kwargs = {"api_key": cfg["api_key"]}
    if cfg.get("base_url"):
        kwargs["base_url"] = cfg["base_url"]
    return OpenAI(**kwargs)


def _anthropic_client(cfg: dict[str, Any]):
    from anthropic import Anthropic

    return Anthropic(api_key=cfg["api_key"])


def _ask_openai_compatible(question: str, context: dict[str, Any], cfg: dict[str, Any]) -> Iterator[str]:
    client = _openai_client(cfg)
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
    client = _anthropic_client(cfg)
    user_content = (
        "Datos disponibles del exit poll:\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2, default=str)}\n\n"
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
    validation = validate_ai_context(context)
    if not validation.ok:
        yield validation.message or INSUFFICIENT_MESSAGE
        return

    cfg = _provider_config(provider, config)
    started = time.perf_counter()
    if cfg["client"] == "anthropic":
        yield from _ask_anthropic(question, validation.context, cfg)
    else:
        yield from _ask_openai_compatible(question, validation.context, cfg)
    latency_ms = int((time.perf_counter() - started) * 1000)
    yield _metadata_footer(_metadata(cfg, latency_ms=latency_ms, tokens_used=None))


def llm_call(
    system_prompt: str,
    user_message: str,
    provider: str,
    api_key: str,
    model: str,
    temperature: float,
) -> str:
    """Provider-agnostic one-shot call. Required minimal interface."""
    result = llm_call_with_metadata(system_prompt, user_message, provider, api_key, model, temperature)
    return result["text"]


def llm_call_with_metadata(
    system_prompt: str,
    user_message: str,
    provider: str,
    api_key: str,
    model: str,
    temperature: float,
    max_tokens: int = 800,
) -> dict[str, Any]:
    """Provider-agnostic one-shot call with trace metadata."""
    cfg = _provider_config(provider, {
        "api_key": api_key,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    })
    started = time.perf_counter()
    tokens_used: int | None = None

    if cfg["client"] == "anthropic":
        client = _anthropic_client(cfg)
        message = client.messages.create(
            model=cfg["model"],
            max_tokens=cfg["max_tokens"],
            temperature=cfg["temperature"],
            system=system_prompt.strip(),
            messages=[{"role": "user", "content": user_message}],
        )
        text = "".join(
            block.text for block in message.content
            if getattr(block, "type", None) == "text"
        )
        usage = getattr(message, "usage", None)
        if usage:
            tokens_used = int(getattr(usage, "input_tokens", 0) or 0) + int(getattr(usage, "output_tokens", 0) or 0)
    else:
        client = _openai_client(cfg)
        response = client.chat.completions.create(
            model=cfg["model"],
            messages=[
                {"role": "system", "content": system_prompt.strip()},
                {"role": "user", "content": user_message},
            ],
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
        )
        text = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        tokens_used = int(getattr(usage, "total_tokens", 0) or 0) if usage else None

    latency_ms = int((time.perf_counter() - started) * 1000)
    return {
        "text": text,
        "metadata": _metadata(cfg, latency_ms=latency_ms, tokens_used=tokens_used),
    }


def ask_structured(
    system_prompt: str,
    user_prompt: str,
    provider: str,
    config: dict[str, Any] | None = None,
) -> str:
    """Single-shot text completion through the configured provider."""
    cfg = _provider_config(provider, config)
    if cfg["client"] == "anthropic":
        client = _anthropic_client(cfg)
        message = client.messages.create(
            model=cfg["model"],
            max_tokens=cfg["max_tokens"],
            temperature=cfg["temperature"],
            system=system_prompt.strip(),
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(
            block.text for block in message.content
            if getattr(block, "type", None) == "text"
        )

    client = _openai_client(cfg)
    request = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": cfg["temperature"],
        "max_tokens": cfg["max_tokens"],
    }
    if provider == "openai":
        request["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**request)
    return response.choices[0].message.content or ""


async def ask_structured_async(
    system_prompt: str,
    user_prompt: str,
    provider: str,
    config: dict[str, Any] | None = None,
) -> str:
    """Single-shot text completion (asynchronous to prevent event loop blocking)."""
    return await asyncio.to_thread(ask_structured, system_prompt, user_prompt, provider, config)

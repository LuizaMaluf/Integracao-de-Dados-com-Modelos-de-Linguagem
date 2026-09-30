"""
Cliente LLM único do govhub: uma chamada de texto → texto, com dois backends.

- ``anthropic`` (padrão): SDK oficial, autenticado por ``ANTHROPIC_API_KEY``.
- ``claude-cli``: Claude Code em modo headless (``claude -p``), autenticado pelo
  login do Claude Code na máquina (assinatura). Serve para rodar fora do container,
  onde não há API key.

O backend vem de ``LLM_BACKEND`` no ambiente/.env.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

BACKENDS = ("anthropic", "claude-cli")


def backend() -> str:
    name = os.environ.get("LLM_BACKEND", "anthropic").strip().lower()
    if name not in BACKENDS:
        raise ValueError(f"LLM_BACKEND inválido: {name!r} (use um de {BACKENDS})")
    return name


def complete(
    prompt: str,
    *,
    model: str,
    system: str | None = None,
    max_tokens: int = 4096,
    api_key: str | None = None,
) -> str:
    """Envia um prompt de usuário e devolve o texto da resposta."""
    if backend() == "claude-cli":
        return _complete_claude_cli(prompt, model=model, system=system)
    return _complete_anthropic(prompt, model=model, system=system,
                               max_tokens=max_tokens, api_key=api_key)


def _complete_anthropic(prompt, *, model, system, max_tokens, api_key) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    kwargs = {"system": system} if system else {}
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        **kwargs,
    )
    return message.content[0].text


def claude_cli_command(model: str, system: str | None) -> list[str]:
    """Só o modelo: sem ferramentas, MCP, settings do usuário nem sessão salva."""
    cmd = [
        "claude", "-p", "--output-format", "json", "--model", model,
        "--tools", "", "--setting-sources", "", "--strict-mcp-config",
        "--no-session-persistence",
    ]
    if system:
        cmd += ["--system-prompt", system]
    return cmd


def _complete_claude_cli(prompt, *, model, system) -> str:
    if shutil.which("claude") is None:
        raise RuntimeError("LLM_BACKEND=claude-cli, mas o executável `claude` não está no PATH")
    # Sem ANTHROPIC_API_KEY no ambiente o Claude Code usa o login (assinatura).
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    proc = subprocess.run(
        claude_cli_command(model, system), input=prompt, capture_output=True,
        text=True, env=env, timeout=600,
    )
    if proc.returncode != 0:
        detalhe = proc.stderr[-2000:] or proc.stdout[-2000:]
        raise RuntimeError(f"claude -p falhou ({proc.returncode}): {detalhe}")
    result = json.loads(proc.stdout)
    if result.get("is_error"):
        raise RuntimeError(f"claude -p retornou erro: {result.get('result')}")
    return result["result"]

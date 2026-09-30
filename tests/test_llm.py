import json
import subprocess

import pytest

from govhub import llm


def test_backend_padrao_e_anthropic(monkeypatch):
    monkeypatch.delenv("LLM_BACKEND", raising=False)
    assert llm.backend() == "anthropic"


def test_backend_invalido(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "openai")
    with pytest.raises(ValueError):
        llm.backend()


def test_claude_cli_usa_login_e_devolve_result(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "claude-cli")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-...")
    monkeypatch.setattr(llm.shutil, "which", lambda _: "/usr/bin/claude")
    chamadas = {}

    def fake_run(cmd, *, input, env, **kwargs):
        chamadas.update(cmd=cmd, input=input, env=env)
        out = json.dumps({"type": "result", "is_error": False, "result": '{"ok": true}'})
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

    monkeypatch.setattr(llm.subprocess, "run", fake_run)

    texto = llm.complete("pergunta", model="claude-sonnet-4-6", system="sistema")

    assert texto == '{"ok": true}'
    assert chamadas["input"] == "pergunta"
    assert "ANTHROPIC_API_KEY" not in chamadas["env"]
    cmd = chamadas["cmd"]
    assert cmd[:2] == ["claude", "-p"]
    assert cmd[cmd.index("--model") + 1] == "claude-sonnet-4-6"
    assert cmd[cmd.index("--tools") + 1] == ""
    assert cmd[cmd.index("--system-prompt") + 1] == "sistema"


def test_claude_cli_erro_vira_excecao(monkeypatch):
    monkeypatch.setenv("LLM_BACKEND", "claude-cli")
    monkeypatch.setattr(llm.shutil, "which", lambda _: "/usr/bin/claude")
    out = json.dumps({"type": "result", "is_error": True, "result": "limite atingido"})
    monkeypatch.setattr(
        llm.subprocess, "run",
        lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout=out, stderr=""),
    )
    with pytest.raises(RuntimeError, match="limite atingido"):
        llm.complete("x", model="m")

"""Tests for ChatAgent.run() compatibility wrapper.

These tests catch SDK signature mismatches (e.g., when `user=` isn't supported)
*before* runtime by validating our wrapper behavior.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.agent_run_compat import run_agent_compat
from app.services.chat_agent import ChatAgentService


class AgentWithUser:
    def __init__(self):
        self.seen = None

    async def run(self, prompt, *, user=None):
        self.seen = {"prompt": prompt, "user": user}
        return SimpleNamespace(text="ok")


class AgentWithoutUser:
    def __init__(self):
        self.seen = None

    async def run(self, prompt):
        self.seen = {"prompt": prompt}
        return SimpleNamespace(text="ok")


class AgentWithThreadAndUser:
    def __init__(self):
        self.seen = None

    async def run(self, prompt, *, thread=None, user=None):
        self.seen = {"prompt": prompt, "thread": thread, "user": user}
        return SimpleNamespace(text="ok")


@pytest.mark.asyncio
async def test_run_agent_compat_passes_user_when_supported():
    agent = AgentWithUser()
    result = await run_agent_compat(agent, "hello", user="u-123")

    assert result.text == "ok"
    assert agent.seen == {"prompt": "hello", "user": "u-123"}


@pytest.mark.asyncio
async def test_run_agent_compat_drops_user_when_not_supported():
    agent = AgentWithoutUser()
    result = await run_agent_compat(agent, "hello", user="u-123")

    assert result.text == "ok"
    assert agent.seen == {"prompt": "hello"}


@pytest.mark.asyncio
async def test_run_agent_compat_passes_thread_and_user_when_supported():
    agent = AgentWithThreadAndUser()
    thread = object()

    result = await run_agent_compat(agent, "hello", user="u-123", thread=thread)

    assert result.text == "ok"
    assert agent.seen == {"prompt": "hello", "thread": thread, "user": "u-123"}


@pytest.mark.asyncio
async def test_chat_agent_service_calls_agent_with_user_kwarg_when_supported(monkeypatch):
    """Regression guard for the chat service: ensure user_id reaches agent.run()."""

    service = ChatAgentService()
    fake_agent = AgentWithUser()

    async def _fake_get_agent(document_context, model):
        return fake_agent

    monkeypatch.setattr(service, "_get_agent", _fake_get_agent)

    result = await service.chat(
        message="hi",
        history=None,
        session_id="chat_test",
        user_id="u-123",
        document_context=None,
        model=None,
    )

    assert result.response
    assert fake_agent.seen == {"prompt": "hi", "user": "u-123"}

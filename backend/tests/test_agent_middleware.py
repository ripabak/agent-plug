"""Unit tests for the agent middleware chain (`build_middleware`).

No DB / network needed: `ChatOpenRouter` only requires an API key env var at
construction time (it never calls the API in these tests).
"""
from langchain.agents.middleware import (
    ClearToolUsesEdit,
    ContextEditingMiddleware,
    ModelCallLimitMiddleware,
    ModelFallbackMiddleware,
    SummarizationMiddleware,
    ToolCallLimitMiddleware,
    ToolRetryMiddleware,
)
from langchain_openrouter import ChatOpenRouter

from app.agent.agent import build_middleware


def _chain(monkeypatch):
    """Build the middleware chain with a dummy model."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    return build_middleware(ChatOpenRouter(model="test/model"))


def test_chain_contains_all_middleware(monkeypatch):
    chain = _chain(monkeypatch)
    types = {type(m) for m in chain}
    assert ModelFallbackMiddleware in types
    assert ModelCallLimitMiddleware in types
    assert ToolCallLimitMiddleware in types
    assert ToolRetryMiddleware in types
    assert SummarizationMiddleware in types
    assert ContextEditingMiddleware in types


def test_fallback_models(monkeypatch):
    chain = _chain(monkeypatch)
    fallback = next(m for m in chain if isinstance(m, ModelFallbackMiddleware))
    # Primary model + configured fallback (deepseek/deepseek-v4-flash-0731).
    names = [getattr(m, "model_name", None) or str(getattr(m, "model", None)) for m in fallback.models]
    assert len(names) == 2
    assert names[0] == "test/model"
    assert names[1] == "deepseek/deepseek-v4-flash-0731"


def test_fallback_skipped_when_empty(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr("app.agent.agent.OPENROUTER_FALLBACK_MODELS", "")
    chain = build_middleware(ChatOpenRouter(model="test/model"))
    assert not any(isinstance(m, ModelFallbackMiddleware) for m in chain)


def test_model_call_limit(monkeypatch):
    chain = _chain(monkeypatch)
    limit = next(m for m in chain if isinstance(m, ModelCallLimitMiddleware))
    assert limit.run_limit == 5
    assert limit.exit_behavior == "end"


def test_tool_call_limit(monkeypatch):
    chain = _chain(monkeypatch)
    limit = next(m for m in chain if isinstance(m, ToolCallLimitMiddleware))
    assert limit.run_limit == 5


def test_tool_retry(monkeypatch):
    chain = _chain(monkeypatch)
    retry = next(m for m in chain if isinstance(m, ToolRetryMiddleware))
    assert retry.max_retries == 2


def test_summarization_trigger(monkeypatch):
    chain = _chain(monkeypatch)
    summ = next(m for m in chain if isinstance(m, SummarizationMiddleware))
    assert summ.trigger == ("tokens", 30000)
    assert summ.keep == ("messages", 10)


def test_context_editing(monkeypatch):
    chain = _chain(monkeypatch)
    editing = next(m for m in chain if isinstance(m, ContextEditingMiddleware))
    edit = editing.edits[0]
    assert isinstance(edit, ClearToolUsesEdit)
    assert edit.trigger == 60000
    assert edit.keep == 5
    assert edit.clear_tool_inputs is True

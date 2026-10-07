"""Regression: org/model ids must still receive the litellm provider prefix."""
from app.services.agent_service import _model_name_for_litellm as m


def test_nim_org_model_gets_prefix():
    assert m("nvidia_nim", "nvidia/nemotron-3-super-120b-a12b") == "nvidia_nim/nvidia/nemotron-3-super-120b-a12b"
    assert m("nvidia_nim", "deepseek-ai/deepseek-v4-flash-0731") == "nvidia_nim/deepseek-ai/deepseek-v4-flash-0731"


def test_openrouter_org_model_gets_prefix():
    assert m("openrouter", "meta-llama/llama-4-maverick") == "openrouter/meta-llama/llama-4-maverick"


def test_already_qualified_untouched():
    assert m("nvidia_nim", "nvidia_nim/nvidia/nemotron-3-super-120b-a12b") == "nvidia_nim/nvidia/nemotron-3-super-120b-a12b"
    assert m("google", "gemini/gemini-2.5-flash") == "gemini/gemini-2.5-flash"


def test_plain_names():
    assert m("google", "gemini-2.5-flash") == "gemini/gemini-2.5-flash"
    assert m("deepseek", "deepseek-v4-flash") == "deepseek/deepseek-v4-flash"
    assert m("anthropic", "claude-sonnet-4-5") == "claude-sonnet-4-5"

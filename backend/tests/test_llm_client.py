"""Test for the LLM client wrapper: confirms it's built from settings, not
hardcoded, without making a real API call (ChatGroq doesn't call the network
at construction time)."""

from app.config import settings
from app.services.llm_client import get_llm


def test_get_llm_uses_configured_model(monkeypatch):
    monkeypatch.setattr(settings, "llm_model", "some-test-model")
    monkeypatch.setattr(settings, "groq_api_key", "test-key")

    llm = get_llm()

    assert llm.model_name == "some-test-model"

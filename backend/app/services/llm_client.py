"""Single point of contact for the LLM provider. Every other module gets an
LLM client through get_llm() — swapping Groq for Ollama later (per
CLAUDE.md's 'keep the LLM layer swappable' rule) means changing this file
only, nothing that calls get_llm() needs to change."""

from langchain_groq import ChatGroq

from app.config import settings


def get_llm() -> ChatGroq:
    """Returns a configured chat model client. Constructed fresh on each
    call (cheap — no network call at construction time) rather than cached
    as a module-level singleton, so tests can monkeypatch settings and get
    a client that reflects the change."""
    return ChatGroq(
        model=settings.llm_model,
        api_key=settings.groq_api_key,
        temperature=0,
    )

"""Tests for config.py's env-file path resolution. Regression test for a real
bug found manually: env_file=".env" resolved relative to whatever directory a
command was run from, so running from backend/ silently missed the real
.env at the project root. Fixed by anchoring to config.py's own location."""

from pathlib import Path

from app.config import Settings, _PROJECT_ROOT


def test_project_root_is_repo_root_not_backend():
    assert (_PROJECT_ROOT / "docker-compose.yml").exists()
    assert (_PROJECT_ROOT / "backend").is_dir()


def test_env_file_path_is_absolute_and_anchored_to_project_root():
    env_file = Path(Settings.model_config["env_file"])
    assert env_file.is_absolute()
    assert env_file == _PROJECT_ROOT / ".env"


def test_env_file_still_resolves_after_cwd_change(monkeypatch, tmp_path):
    """Simulates running from an unrelated directory (like backend/) — the
    resolved env_file path must still point at the real .env, not silently
    miss it and fall back to defaults."""
    monkeypatch.chdir(tmp_path)
    env_file = Path(Settings.model_config["env_file"])
    assert env_file.exists()

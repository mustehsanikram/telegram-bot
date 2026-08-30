"""Guards the documentation against silently drifting from Settings."""

from pathlib import Path

import pytest

from stylebot.config import Settings

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTING_NAMES = sorted(Settings.model_fields)


@pytest.mark.parametrize("field", SETTING_NAMES)
def test_env_example_documents_every_setting(field: str) -> None:
    env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    assert f"{field.upper()}=" in env_example


@pytest.mark.parametrize("field", SETTING_NAMES)
def test_readme_documents_every_setting(field: str) -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert f"`{field.upper()}`" in readme


def test_readme_states_the_async_driver_requirement() -> None:
    """The scheme Railway hands you is the sync driver and will not start the bot."""
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "postgresql+asyncpg" in readme


def test_readme_states_the_single_replica_constraint() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "one replica" in readme.lower() or "single-replica" in readme.lower()


def test_readme_has_a_smoke_test_checklist() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Smoke test" in readme


def test_smoke_test_checks_persistence_across_a_redeploy() -> None:
    """The ephemeral-filesystem trap is the one a checklist must not omit."""
    smoke = (REPO_ROOT / "README.md").read_text(encoding="utf-8").split("## Smoke test", 1)[1]
    assert "redeploy" in smoke.lower()
    assert "ephemeral" in smoke.lower()

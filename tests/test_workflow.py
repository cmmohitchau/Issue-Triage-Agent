"""Gated Actions workflow: trigger, artifact handoff, and environment gate.

Parses .github/workflows/triage.yml and asserts the end-to-end shape:
open an issue -> phase 1 uploads the proposal artifact -> the `triage`
environment gate holds it for approval -> phase 2 posts exactly the
approved artifact with no LLM calls.
"""

from pathlib import Path

import pytest
import yaml

WORKFLOW_PATH = (
    Path(__file__).resolve().parent.parent / ".github" / "workflows" / "triage.yml"
)


@pytest.fixture(name="workflow")
def workflow_fixture() -> dict[str, object]:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _jobs(workflow: dict[str, object]) -> dict[str, object]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    return jobs


def test_workflow_file_exists() -> None:
    assert WORKFLOW_PATH.is_file()


def test_trigger_is_issues_opened_only(workflow: dict[str, object]) -> None:
    on = workflow[True] if True in workflow else workflow["on"]
    assert isinstance(on, dict)
    assert set(on) == {"issues"}
    issues = on["issues"]
    assert isinstance(issues, dict)
    assert issues.get("types") == ["opened"]


def test_phase1_uploads_proposal_artifact(workflow: dict[str, object]) -> None:
    phase1 = _jobs(workflow)["phase1"]
    assert isinstance(phase1, dict)
    steps = phase1["steps"]
    assert isinstance(steps, list)
    uploads = [
        step
        for step in steps
        if isinstance(step, dict) and "upload-artifact" in str(step.get("uses", ""))
    ]
    assert uploads, "phase 1 must upload the proposal artifact"
    assert any("proposal" in str(step.get("with", "")) for step in uploads)


def test_phase1_uses_setup_uv(workflow: dict[str, object]) -> None:
    phase1 = _jobs(workflow)["phase1"]
    assert isinstance(phase1, dict)
    steps = phase1["steps"]
    assert isinstance(steps, list)
    assert any(
        isinstance(step, dict) and "setup-uv" in str(step.get("uses", ""))
        for step in steps
    )


def test_phase2_waits_on_phase1_behind_triage_environment(
    workflow: dict[str, object],
) -> None:
    phase2 = _jobs(workflow)["phase2"]
    assert isinstance(phase2, dict)
    needs = phase2["needs"]
    assert "phase1" in needs if isinstance(needs, list) else needs == "phase1"
    assert phase2["environment"] == "triage"


def test_phase2_downloads_proposal_artifact(workflow: dict[str, object]) -> None:
    phase2 = _jobs(workflow)["phase2"]
    assert isinstance(phase2, dict)
    steps = phase2["steps"]
    assert isinstance(steps, list)
    downloads = [
        step
        for step in steps
        if isinstance(step, dict) and "download-artifact" in str(step.get("uses", ""))
    ]
    assert downloads, "phase 2 must download the approved proposal artifact"
    assert any("proposal" in str(step.get("with", "")) for step in downloads)


def test_phase2_has_no_llm_secrets(workflow: dict[str, object]) -> None:
    phase2 = _jobs(workflow)["phase2"]
    assert isinstance(phase2, dict)
    text = yaml.safe_dump(phase2)
    assert "OPENROUTER_API_KEY" not in text
    assert "GROQ_API_KEY" not in text


def test_phase1_cannot_write_issues(workflow: dict[str, object]) -> None:
    phase1 = _jobs(workflow)["phase1"]
    assert isinstance(phase1, dict)
    permissions = phase1.get("permissions", {})
    assert isinstance(permissions, dict)
    assert permissions.get("issues") in ("read", "none", None)

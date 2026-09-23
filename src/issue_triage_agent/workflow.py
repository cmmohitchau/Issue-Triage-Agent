"""Shared constants and file seams for the gated triage workflow.

Phase 1 writes the proposal artifact file; the `triage` environment gate
holds it for approval; phase 2 reads the approved file back. Both phases
share these constants and the JSON file shape, nothing else.
"""

from pathlib import Path
from typing import Any

from issue_triage_agent.artifact import ProposalArtifact
from issue_triage_agent.payload import IssuePayload

#: GitHub environment whose required reviewer approves phase 2 (config as code).
TRIAGE_ENVIRONMENT = "triage"

#: Workflow artifact name carrying the proposal between jobs.
ARTIFACT_NAME = "proposal"

#: Proposal file written by phase 1 and consumed by phase 2.
ARTIFACT_FILENAME = "proposal.json"


def payload_from_event(event: dict[str, Any]) -> IssuePayload:
    """Build the seam A input from an `issues: opened` event payload."""
    issue = event["issue"]
    if not isinstance(issue, dict):
        raise ValueError("Event has no issue object; refusing to triage")
    user = issue.get("user") or {}
    body = issue.get("body") or ""
    return IssuePayload(
        number=int(issue["number"]),
        title=str(issue.get("title") or ""),
        body=str(body),
        author_login=str(user.get("login") or "unknown"),
        comments=[],
    )


def write_artifact_file(path: Path, artifact: ProposalArtifact) -> None:
    """Persist the phase 1 proposal for upload to the workflow artifact store."""
    path.write_text(artifact.model_dump_json(), encoding="utf-8")


def read_artifact_file(path: Path) -> ProposalArtifact:
    """Load the approved proposal; malformed files fail loud before any write."""
    return ProposalArtifact.model_validate_json(path.read_text(encoding="utf-8"))

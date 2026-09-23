"""Phase 2: approved proposal artifact → GitHub write calls (seam B, no LLM)."""

from issue_triage_agent.artifact import IssueKind, ProposalArtifact, TriageRole
from issue_triage_agent.github_writes import GitHubWrites
from issue_triage_agent.label_policy import readiness_roles

_ROLE_BY_KIND: dict[IssueKind, TriageRole] = {
    IssueKind.NEEDS_REPRO: TriageRole.NEEDS_INFO,
    IssueKind.BUG: TriageRole.NEEDS_TRIAGE,
    IssueKind.FEATURE: TriageRole.NEEDS_TRIAGE,
    IssueKind.QUESTION: TriageRole.NEEDS_TRIAGE,
    IssueKind.DUPLICATE: TriageRole.NEEDS_TRIAGE,
}


def fixed_triage_role(kind: IssueKind) -> TriageRole:
    """Spec mapping: needs-repro → needs-info; every other kind → needs-triage."""
    return _ROLE_BY_KIND[kind]


def run_phase2(
    artifact: ProposalArtifact,
    issue_number: int,
    *,
    github: GitHubWrites,
) -> None:
    """Apply the approved artifact: create missing labels, set labels, post Draft once.

    All validation runs before the first write so a refusal never leaves partial state.
    """
    _validate(artifact)

    for name in artifact.labels:
        github.create_label_if_missing(name)

    github.apply_labels(issue_number, list(artifact.labels))
    github.post_comment(issue_number, artifact.draft)


def _validate(artifact: ProposalArtifact) -> None:
    if not artifact.draft.strip() or not artifact.labels:
        raise ValueError(
            "Phase 2 refuses incomplete artifact: draft and labels are required; "
            "no writes performed"
        )

    if artifact.triage_role in readiness_roles():
        raise ValueError(
            f"Agent must not emit readiness Triage Role {artifact.triage_role.value!r}; "
            "no writes performed"
        )

    mapped = fixed_triage_role(artifact.issue_kind)
    if artifact.triage_role is not mapped:
        raise ValueError(
            f"Artifact triage_role {artifact.triage_role.value!r} does not match "
            f"fixed mapping {mapped.value!r} for kind {artifact.issue_kind.value!r}; "
            "no writes performed"
        )

    if mapped.value not in artifact.labels:
        raise ValueError(
            f"Fixed mapping requires role label {mapped.value!r} on the artifact; "
            "no writes performed"
        )

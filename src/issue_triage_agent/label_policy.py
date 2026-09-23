"""Label vocabulary shared by the fake boundary and phase 2 (one source of truth)."""

from issue_triage_agent.artifact import TriageRole

#: Already on the repo per spec; enhancement stays untouched; feature is distinct.
EXISTING_LABELS = frozenset(
    {"bug", "question", "duplicate", "wontfix", "enhancement"}
)


def readiness_roles() -> frozenset[TriageRole]:
    """Triage Roles the agent must never emit (human/terminal queue states)."""
    return frozenset(
        {
            TriageRole.READY_FOR_AGENT,
            TriageRole.READY_FOR_HUMAN,
            TriageRole.WONTFIX,
        }
    )

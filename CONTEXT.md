# Issue Triage Agent

An agent that triages newly opened GitHub issues: classifies them, detects duplicates, and drafts a response held for human approval.

## Language

**Issue Kind**:
The durable nature of an issue: `bug`, `feature`, `question`, `duplicate`, or `needs-repro`. Assigned once at triage.
_Avoid_: type, category, classification

**Triage Role**:
Where an issue sits in the maintainer's workflow queue: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, or `wontfix`. Can change over the issue's life.
_Avoid_: status, stage, kind

**Draft**:
The proposed first response to an issue, computed by the agent but not posted until approved.
_Avoid_: reply, comment (until posted)

**Escalation**:
Handing a proposed action (labels + Draft) to the maintainer for approval before any of it touches the issue.

**Duplicate**:
An issue judged to restate an existing issue; it points at a canonical original rather than standing alone.
_Avoid_: copy, clone

**Author History**:
The reporter's track record: whether they are a first-time contributor and how many issues they have opened before.
_Avoid_: user history, profile

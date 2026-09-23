## Problem Statement

As the maintainer of this repo, raw issues land with no first response until I personally read them. Bugs arrive missing repro steps or environment details and stall; feature requests and questions get no acknowledgement; duplicates pile up unnoticed; and I have no consistent signal of where each issue sits in the queue. Every new issue costs me context-switching time before any real work can start.

## Solution

When a new issue opens, an automated triage agent reads it, classifies its Issue Kind, searches for Duplicates, and drafts a first response — then Escalates the whole proposal (labels + Draft) to me for approval. Nothing touches the issue until I approve: one click in the GitHub Actions UI applies the labels and posts the Draft; a rejection leaves the issue untouched. I see a considered first response and correct labels on every issue without reading it twice, and under-specified bug reports get an immediate, specific ask for what's missing.

## User Stories

1. As a repo maintainer, I want every newly opened issue to wake a triage agent automatically, so that no issue waits in a queue for me to remember it exists.
2. As a repo maintainer, I want the agent to read the issue title, body, and comments, so that classification reflects everything the reporter said.
3. As a repo maintainer, I want the agent to read my author history signals (first-time contributor flag, prior issue count), so that the Draft can be tailored to a newcomer versus a repeat reporter.
4. As a repo maintainer, I want the agent to classify each issue into exactly one Issue Kind — bug, feature, question, duplicate, or needs-repro — so that the queue is legible at a glance.
5. As a repo maintainer, I want bug reports that lack repro steps or verbatim error text to be classified needs-repro instead of bug, so that under-specified reports don't masquerade as actionable work.
6. As a repo maintainer, I want bug reports that lack environment info (version + OS/runtime) to be classified needs-repro, so that I never start debugging without a target environment.
7. As a repo maintainer, I want the needs-repro definition to be an explicit rubric in the prompt rather than the model's gut feeling, so that the label means the same thing every time.
8. As a repo maintainer, I want the agent to search existing issues for duplicates before drafting, so that recurring problems converge on one canonical issue.
9. As a repo maintainer, I want duplicate detection to return a binary verdict (duplicate or not), so that a duplicate label is a strong, trustworthy claim.
10. As a repo maintainer, I want an uncertain duplicate re-rank to report "not a duplicate", so that false positives never mark a fresh issue as a dupe.
11. As a repo maintainer, I want a confirmed Duplicate to be labelled `duplicate` and to receive a comment linking the canonical original, so that reporters and I can follow the thread.
12. As a repo maintainer, I want duplicates NOT to be auto-closed, so that closing remains my one-click judgment after reading the agent's link.
13. As a repo maintainer, I want a drafted first response for every issue — asking for repro steps, confirming a bug, pointing at a duplicate, or acknowledging a feature/question — so that the reporter always gets a same-minute acknowledgement.
14. As a repo maintainer, I want the Draft to call a docs-search tool so it can link to existing documentation when relevant, so that answers I've already written get reused instead of retyped.
15. As a repo maintainer, I want docs search restricted to the README and docs tree, so that Draft links point at documentation rather than source files.
16. As a repo maintainer, I want kind labels applied alongside the Draft — `bug`, `feature`, `question`, `duplicate`, `needs-repro` — so that filtering by kind works from the first response.
17. As a repo maintainer, I want a fixed Triage Role mapping — needs-repro issues get `needs-info`, everything else gets `needs-triage` — so that the agent never guesses human readiness states like ready-for-agent.
18. As a repo maintainer, I want missing labels (feature, needs-repro, and the four missing triage roles) created automatically before they are applied, so that a deleted label never breaks a run.
19. As a repo maintainer, I want the existing `enhancement` label left untouched and a distinct `feature` label created, so that Issue Kind vocabulary stays one-kind-one-label.
20. As a repo maintainer, I want ZERO writes to the issue before I approve — no labels, no comments, no reactions — so that a failed or rejected run leaves the issue exactly as the reporter wrote it.
21. As a repo maintainer, I want the computed proposal presented to me as a reviewable artifact in the GitHub Actions UI, so that I approve exactly what will be posted, not a vague summary.
22. As a repo maintainer, I want approval gated behind a GitHub environment named `triage` with me as required reviewer, so that the gate is GitHub-native and one click.
23. As a repo maintainer, I want a rejected approval to end the workflow with no writes, so that "no" means the issue was never touched.
24. As a repo maintainer, I want phase 2 (the write job) to make no LLM calls, so that what I approved is byte-for-byte what gets posted.
25. As a repo maintainer, I want the agent to run as a ReAct loop that chooses its own tool order, so that simple questions cost few steps and hard ones can search more.
26. As a repo maintainer, I want a 10-step tool budget, so that a confused agent fails fast instead of burning tokens forever.
27. As a repo maintainer, I want step-budget exhaustion or LLM/API errors to fail the workflow run silently (visible in Actions, failure email to me), so that the issue tracker is never spammed with meta-issues.
28. As a repo maintainer, I want the model served through OpenRouter by default with a single env-var swap to Groq, so that I can change providers without code changes.
29. As a repo maintainer, I want the workflow to fail fast when no provider API key is set, so that misconfiguration is loud and immediate.
30. As a repo maintainer, I want the trigger scoped to `issues: opened` only, so that v1 stays a sharp first-response tool rather than a comment-follow-up bot.
31. As a repo maintainer, I want PRs excluded entirely, so that triage stays on issues (the repo's PRs-as-request-surface flag is off).
32. As a repo maintainer, I want author history limited to first-time-contributor status and prior issue count, so that the signal is cheap and the agent doesn't crawl profiles.
33. As a reporter, I want a first response within a minute of opening my issue, so that I know the project is alive and what (if anything) is missing from my report.
34. As a reporter filing an incomplete bug, I want the Draft to name exactly what's missing (repro steps or environment), so that I can fix the report in one edit instead of playing comment ping-pong.
35. As a reporter whose issue is a duplicate, I want a comment linking the original, so that I can follow progress in one place.
36. As a contributor, I want the vocabulary in labels and comments to match the repo's documented triage vocabulary, so that automation and humans mean the same words.
37. As a future maintainer, I want the two-phase gated architecture recorded in an ADR, so that nobody "simplifies" the write back into the agent loop.
38. As a future maintainer, I want the proposal artifact to double as an audit trail, so that every applied label and posted comment can be traced to what was approved.
39. As a developer of this repo, I want phase 1 testable as `payload → artifact` with faked LLM and GitHub reads, so that the whole agent pipeline is verifiable without network or credentials.
40. As a developer of this repo, I want phase 2 testable as `artifact → write calls` with a fake GitHub writer, so that label mapping and comment behavior are verified without touching a real issue.
41. As a developer of this repo, I want dependencies managed with uv and a lockfile, so that CI installs are fast and reproducible.
42. As a developer of this repo, I want tests to assert external behavior at the two seams only, so that refactors inside the graph don't break the suite.

## Implementation Decisions

- **Architecture (ADR-0001):** two-phase gated ReAct triage. Phase 1 is a ReAct-style LangGraph agent with no GitHub write tools; its only output is a JSON proposal artifact. Phase 2 is a separate, environment-gated job that reads the artifact and performs all writes with no LLM calls.
- **Trigger:** GitHub Actions workflow on `issues: opened` only. No PR events, no `edited`/`reopened`, no issue-comment events.
- **Stack:** Python, LangChain/LangGraph, packaged with uv (`pyproject.toml` + lockfile); Action uses `astral-sh/setup-uv`.
- **Provider:** OpenRouter by default (`OPENROUTER_API_KEY`, fail fast if unset); Groq available via `GROQ_API_KEY` as a one-env-var swap. Provider selection is configuration, not code branches scattered through the graph.
- **Agent shape:** ReAct loop (agent chooses tool order), hard budget of 10 tool steps; budget exhaustion or API errors fail the workflow run — no comment, no meta-issue.
- **Agent tools (read-only):** fetch issue (title/body/comments); fetch author history (first-time-contributor flag + prior issue count); search existing issues for duplicates; `search_docs` (keyword search over README + docs tree, top hits returned to the model). No write tools exist in phase 1.
- **Issue Kind rubric (verbatim into the prompt):** `kind = bug` requires ALL of (a) reproduction steps OR verbatim error text/stack trace, and (b) environment info: app/package version AND OS/runtime. If either (a) or (b) is missing → `kind = needs-repro`. needs-repro means: a plausible bug, but the reporter must supply the missing item(s) before it can be worked. Remaining kinds: `feature`, `question`, `duplicate`.
- **Duplicate verdict:** binary after search + LLM re-rank; uncertain ⇒ not a duplicate (no label, no mention in the Draft). Confirmed duplicate ⇒ label `duplicate` + comment linking canonical original; never auto-close.
- **Draft:** first response text (asks for repro, confirms bug, links duplicate, or acknowledges feature/question); may call `search_docs` to link existing docs.
- **Triage Role fixed mapping:** `needs-repro → needs-info`; all other kinds → `needs-triage`. The agent never emits `ready-for-agent`, `ready-for-human`, or `wontfix`.
- **Label policy:** create-if-missing (idempotent API call) in phase 2 before applying. Creates: `feature`, `needs-repro`, `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`. Existing and reused: `bug`, `question`, `duplicate`, `wontfix`. Existing `enhancement` stays untouched.
- **Escalation gate:** GitHub environment `triage` with required-reviewer approval between the jobs. Artifact from phase 1 is uploaded as a workflow artifact; phase 2 consumes it. Rejection ⇒ workflow ends, zero writes.
- **Failure policy:** any phase 1 failure fails the workflow run (Actions failure email). Phase 2 failures likewise fail the run; partial-write behavior should fail loud, never half-silently.
- **Artifact contract:** one JSON document: Issue Kind, Triage Role, duplicate verdict (+ canonical issue number when duplicate), draft text, exact label list to apply, author-history summary used. This JSON is both the approval surface and the phase 2 input.
- **Config as code:** environment name (`triage`), step budget (10), provider defaults, and the role mapping table live in workflow/config constants, not buried in prompt text.
- **Repository configuration (manual, one time):** add `OPENROUTER_API_KEY` (and optionally `GROQ_API_KEY`) secrets; create the `triage` environment with required reviewer.

## Testing Decisions

- **Good tests exercise external behavior at the two seams only** — inputs and observable outputs, never LangGraph node wiring, prompt internals, or intermediate state. Fakes sit at the network boundaries; assertions sit on seam outputs.
- **Seam A — phase 1: issue payload → proposal artifact.** Fake scripted LLM (drives the ReAct loop, can invoke `search_docs`) and fake GitHub reads (issue fetch, author history, duplicate search). Covers: full pipeline happy path; rubric-driven Kind selection (bug complete vs needs-repro on missing (a) vs missing (b) vs both); binary duplicate logic (hit, miss, uncertain ⇒ not duplicate); draft content reflects classification and author history; docs tool results reach the draft; 10-step budget exhaustion fails; provider-missing config fails fast.
- **Seam B — phase 2: proposal artifact + issue number → GitHub write calls.** Fake write recorder. Covers: create-if-missing for each absent label and no create when present; fixed role mapping table (both branches); labels applied exactly as artifact specifies; comment posted once with draft text; duplicate comment includes canonical link; missing/empty artifact fields ⇒ no writes (or loud failure), never partial guesses.
- **Artifact contract** is exercised as the seam boundary: a well-formed artifact from seam A must be acceptable to seam B unchanged.
- **Prior art:** none — greenfield repo, no existing test suite. Establish the two-seam suite as the pattern (fixtures at the seams, fakes at network boundaries); `/tdd` drives it red-green per behavior during `/implement`.
- No live LLM or live GitHub API calls in the test suite.

## Out of Scope

- Comment/`edited`/`reopened` follow-ups (e.g. nudging a needs-repro reporter when they reply)
- PR triage (PRs-as-a-request-surface flag is off)
- Auto-closing confirmed duplicates
- LLM-proposed or human-readiness Triage Roles (`ready-for-agent`, `ready-for-human`, `wontfix` as agent outputs)
- Non-binary/soft-confidence duplicate surfacing ("possibly related to #N")
- Embedding or similarity indexes for duplicate detection
- Whole-repo (code-included) docs search; GitHub code search API
- Multi-issue batching, mention commands, or manual `/triage` invocation paths
- Notification/meta-issues on agent failure
- Webhooks or an always-on service (Actions only)
- Rich author-history profiling beyond first-time flag + prior issue count
- Local-markdown issue tracking (tracker is GitHub)

## Further Notes

- Domain vocabulary lives in `CONTEXT.md` (Issue Kind, Triage Role, Draft, Escalation, Duplicate, Author History); use those terms in tickets and code review.
- `docs/adr/0001-two-phase-gated-react-triage.md` records the two-phase gated ReAct decision — read before restructuring the workflow.
- Build path after publication: split into tracer-bullet tickets with `/to-tickets`, then `/implement` per ticket (each drives `/tdd`, closes with `/code-review`), clearing context between tickets.
- One-time human setup (secrets + `triage` environment approval) is a natural `/wizard` candidate during implementation.

# RB-AUTONOMOUS-DEVELOPMENT-VISION: Define the long-running autonomous development system around RigorBreeze

Risk: L0

Depends-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: Produce one Chinese CTO-level Markdown proposal for evolving from interactive prompt-by-prompt development to a Mac mini based, long-running autonomous project-delivery system, explaining GSD Core's contribution and RigorBreeze's future role.
- Current behavior and evidence: RigorBreeze v0.9.2 already governs task contracts, SDD/TDD evidence, risk lanes, isolated worktrees, optional dependencies, verification and guarded delivery, but intentionally grants no standing unattended authority and is not a durable scheduler or always-on process supervisor. External research covers GSD Core's autonomous phase loop and architecture, official Codex automation surfaces, Anthropic long-running harness research, durable graph runtimes, and practitioner reports from X and Reddit.
- Business and architecture path: Keep RigorBreeze as the single quality and delivery-governance source of truth; define a separate durable orchestration layer that compiles human-approved product goals into a dependency graph, invokes fresh Codex workers through bounded loops, checkpoints state, runs independent verification, pauses at risk gates, and resumes safely after failure or restart.
- Invariants and source of truth: One final strategy document only; sources are linked directly and separated into official/primary evidence versus practitioner signals. The proposal must not claim that a Skill, GSD Core, or one long chat alone provides 24/7 autonomy, and must not authorize production, Git, credential, deployment, migration or release actions.
- Requirement/design/API version: RigorBreeze v0.9.2 Public Preview; research checked on 2026-08-06 against GSD Core next-branch documentation and current official Codex documentation.
- Unresolved outcome-changing ambiguity: none; the user explicitly wants a forward-looking system solution rather than immediate implementation.

## Allowed scope
- RigorBreeze长期自主开发系统方案.md
- spec/changes/RB-AUTONOMOUS-DEVELOPMENT-VISION.md
- spec/evidence/RB-AUTONOMOUS-DEVELOPMENT-VISION.json
- spec/archive/RB-AUTONOMOUS-DEVELOPMENT-VISION.md

## Forbidden scope
- RigorBreeze runtime, CLI, schema, Skill instructions, README, CI, release configuration or production project code
- Installing GSD Core, LangGraph, Temporal or any other runtime or dependency
- Git commit, push, tag, release, deployment, migration, credential changes or unattended authority
- Creating a second strategy document, implementation scaffold, dashboard or control-plane code

## Acceptance criteria
- REQ-001: The document gives an explicit CTO verdict on whether GSD Core is a long-running autonomous system and whether one Skill can meet the user's target.
- REQ-002: The document defines the future system as a layered toolchain with human product authority, planning/DAG, durable orchestration, Codex execution, RigorBreeze governance, independent evaluation, Git/CI delivery, isolation, observability, security and remote intervention.
- REQ-003: The document identifies which GSD Core ideas to absorb, which not to copy, and how to avoid a conflicting second state machine.
- REQ-004: The document incorporates traceable lessons from official GSD, OpenAI, Anthropic, LangGraph, Temporal and GitHub sources plus clearly labelled X/Reddit practitioner evidence.
- REQ-005: The document includes a staged roadmap from the current interactive workflow to single-task overnight execution, durable DAG operation and guarded low-risk delivery, with measurable gates and stop conditions.
- REQ-006: The proposal preserves RigorBreeze's non-bloated core and positions any future autonomous runner/control plane as a separate component.

## Test seams
- Seam: document structure, claim/source traceability, repository-relative links and scope.
- Independent oracle: acceptance checklist review, Markdown link extraction, `git diff --check`, and confirmation that no file outside Allowed scope changed.

## Verification commands
- python3 scripts/check_markdown_links.py when available, otherwise a local Markdown URL/path checker
- git diff --check
- git status --short

## Conditional risks
- Runtime/UI: no runtime changes; the document must distinguish headless verification from GUI and real-device acceptance.
- Security/migration/release: no authority changes; production credentials, migrations, releases and irreversible actions remain human-gated.
- Stop conditions: implementation work, dependency installation, a second state source, broadening RigorBreeze core, or unsupported claims about unattended safety.

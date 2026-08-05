# RB-AGENT-RELIABILITY: Verify RigorBreeze changes agent behavior under pressure

Risk: L1

Depends-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: Prove that RigorBreeze changes Codex behavior under realistic pressure while keeping the daily solo-development workflow lean.
- Current behavior and evidence: v0.8.1 has deterministic CLI, state, evidence and documentation tests, but no repeatable live-Agent pressure suite. Archived task projections can also retain a stale retrospective nextAction.
- Business and architecture path: repository-only maintainer scenarios and a Python standard-library runner exercise the installed Skill in synthetic Git repositories; ordinary project runners and task evidence remain unchanged.
- Invariants and source of truth: six synthetic scenarios and their machine rubric are the behavior contract; Git diff, captured Codex JSONL, fake-platform logs and fresh verification output are independent oracles. Live results remain Git-private.
- Requirement/design/API version: user-approved RigorBreeze v0.9.0 Agent behavior reliability plan; Schema v4 and Automation Journal v1 remain unchanged.
- Unresolved outcome-changing ambiguity: none; live Codex tests are manually triggered before release and never run in CI.

## Allowed scope
- .github/workflows/ci.yml
- AGENTS.md
- README.md
- README.zh-CN.md
- CHANGELOG.md
- CHANGELOG.zh-CN.md
- CONTRIBUTING.md
- CONTRIBUTING.zh-CN.md
- Skill演进与实践记录.md
- rigorbreeze/SKILL.md
- rigorbreeze/references/handbook.md
- rigorbreeze/references/handbook.zh-CN.md
- rigorbreeze/scripts/flow_parallel.py
- rigorbreeze/scripts/flow_state.py
- rigorbreeze/scripts/tests/
- tests/behavior/
- spec/changes/RB-AGENT-RELIABILITY.md
- spec/evidence/RB-AGENT-RELIABILITY.json
- spec/archive/RB-AGENT-RELIABILITY.md

## Forbidden scope
- Public CLI commands, task/evidence Schema, Automation Journal, Spec Tree or risk-lane changes
- Live-model calls from CI, new runtime dependencies or a second workflow/evaluation state system
- Real product repositories, production services, credentials, remote Git writes or releases
- Copying Superpowers orchestration, mandatory subagents, full design-document trees or architecture scanners

## Acceptance criteria
- REQ-001: A repository-only behavior suite defines exactly six synthetic scenarios covering incomplete semantics, stale external actions, follow-up re-entry, three failed fixes, questionable review feedback and lightweight L0 work.
- REQ-002: A Python standard-library runner validates scenario contracts, prepares isolated Git fixtures, can invoke `codex exec --ephemeral --json` manually, redacts outputs and scores required, forbidden and ordered observations deterministically.
- REQ-003: CI validates scenarios and the scorer only with synthetic transcripts; it never invokes a live model, needs credentials or writes outside temporary repositories.
- REQ-004: Before task approval the Skill performs a compact semantic self-review for placeholders, contradictions, oversize scope and ambiguous outcome/source/fallback semantics without adding a document or user step.
- REQ-005: Completion claims cite fresh commands, exit status and verified scope; old reports, partial checks and other Agent claims are explicitly insufficient.
- REQ-006: Review feedback is verified against repository reality and YAGNI before implementation, and three failed fix hypotheses stop further patching for an architecture discussion.
- REQ-007: Archived tasks no longer inherit stale nextAction values, without adding a JSON field or changing active-task scheduling.
- REQ-008: SKILL.md remains at most 150 lines, uses existing references, and all English/Chinese public and maintainer documentation consistently identifies v0.9.0 as Public Preview.
- REQ-009: Existing workflow tests, Skill validation, behavior contract tests, link checks, syntax checks and enforced full profile pass with no new runtime dependency.

## Test seams
- Seam: behavior scenario loader/scorer; archived task status projection; Skill execution contract and generated AGENTS block.
- Independent oracle: malformed/synthetic transcripts, fixture Git diffs and fake-platform logs; archived registry item with a stale action; exact semantic-rule assertions and line-count limit.

## Verification commands
- python3 -B -m unittest discover -s rigorbreeze/scripts/tests -v
- python3 -B -m unittest discover -s tests/behavior -v
- python3 -B tests/behavior/run.py validate
- python3 -B /Users/songjincheng/.codex/skills/.system/skill-creator/scripts/quick_validate.py rigorbreeze
- python3 -B syntax compilation without bytecode output
- git diff --check

## Conditional risks
- Runtime/UI: live behavior tests run only in generated temporary repositories and write redacted results under `.git/rigorbreeze/behavior-evals/<version>/`.
- Security/migration/release: synthetic fixtures contain no real credentials or remote actions; the runner must reject fixture paths that escape its temporary root.
- Stop conditions: any design requires a new public command, project Schema, model call in CI, packaged behavior suite or persistent second state system.

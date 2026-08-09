# RB-AGENT-REASONING-0120: Improve agent decisions without adding workflow weight

Risk: L1

Depends-On: none

Task-Origin: current-request

Waiting-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: Absorb the useful decision, prototyping, code-design, and agent-writing practices from mattpocock/skills while keeping RigorBreeze a compact solo-production workflow.
- Current behavior and evidence: RigorBreeze v0.11.0 already shapes unbounded initiatives, verifies review feedback, and applies YAGNI, but it has no bounded decision-frontier protocol, no one-question prototype contract, no explicit abstraction deletion test, and no maintainer rule tying always-loaded instructions to observable behavior.
- Business and architecture path: Extend the existing single Skill and repository-only behavior suite. Reuse the initiative brief, Authoritative inputs, handbook, managed AGENTS policy, and existing behavior-evaluation schema instead of adding public commands or state.
- Invariants and source of truth: SKILL.md remains the execution protocol at no more than 150 lines; handbook owns detail; CLI --help owns syntax; README owns adoption guidance. Public CLI, Spec Tree, schema v4, automation journal v1, default Git authority, and L0/L1 friction remain unchanged.
- Requirement/design/API version: RigorBreeze v0.12.0 Public Preview; approved implementation plan in the current user request; mattpocock/skills current-main audit performed before this task.
- Unresolved outcome-changing ambiguity: none; the user approved the complete v0.12.0 plan and explicitly excluded multi-Skill routing, unlimited grilling, issue-tracker state, permanent prototype branches, and automatic delivery.

## Allowed scope
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
- rigorbreeze/scripts/flow_state.py
- rigorbreeze/scripts/tests/test_skill_contract.py
- rigorbreeze/scripts/tests/test_flow_v4.py
- tests/behavior/run.py
- tests/behavior/scenarios.json
- tests/behavior/test_behavior.py
- spec/changes/RB-AGENT-REASONING-0120.md
- spec/evidence/RB-AGENT-REASONING-0120.json
- spec/archive/RB-AGENT-REASONING-0120.md

## Forbidden scope
- Public CLI commands, arguments, or output schemas
- Evidence/state schema v4 and automation journal v1
- New Spec file types, references, runtime dependencies, routers, or public Skills
- Automatic commit, push, merge, release, or project Runner upgrades
- The three Lingang Housing business repositories

## Acceptance criteria
- REQ-001: Initiative shaping and genuinely branching L2 ambiguity use an ephemeral decision frontier: recover facts first, ask no more than three currently answerable outcome-changing questions per round, include a recommendation/reason/result impact, and create no delivery task before the frontier is resolved and the brief is approved.
- REQ-002: A prototype is explicitly limited to one decision question and records its reference, observation, and verdict in the existing brief or Authoritative inputs; it never counts as production implementation or acceptance and is disposable by default.
- REQ-003: Implementation and Standards Review apply an abstraction deletion test that removes or inlines layers whose complexity disappears, while retaining boundaries that localize real multi-caller or safety complexity.
- REQ-004: Maintainer guidance requires every new always-loaded instruction to identify its trigger, completion criterion, and observable behavior/evaluation delta; no-op rules are removed or moved to references, and SKILL.md stays at or below 150 lines.
- REQ-005: English and Chinese adoption guidance distinguishes stable released installs from contributor symlinks, forbids auto-pulling dirty development checkouts, and upgrades project Runners only when outdated and upgradeSafe after active work closes.
- REQ-006: The behavior contract contains exactly eleven deterministic scenarios by adding decision-frontier and one-question-prototype cases and extending review skepticism with the deletion test; live release-candidate guidance requires two runs per case without CI invoking a model.

## Test seams
- Seam: Installable Skill text, managed AGENTS template, bilingual public/reference documents, and repository-only behavior-contract loader/scorer.
- Independent oracle: Unit assertions inspect exact version/rules/line count and score synthetic transcripts, paths, markers, question counts, and forbidden actions without relying on the Skill's own prose claims.

## Verification commands
- python3 -B -m unittest tests.behavior.test_behavior -v
- python3 -B -m unittest rigorbreeze.scripts.tests.test_skill_contract -v
- python3 -B -m unittest discover -s rigorbreeze/scripts/tests -v
- python3 -B tests/behavior/run.py validate
- python3 /Users/songjincheng/.codex/skills/.system/skill-creator/scripts/quick_validate.py rigorbreeze
- python3 -B -m py_compile rigorbreeze/scripts/flow.py rigorbreeze/scripts/flow_state.py tests/behavior/run.py
- git diff --check

## Conditional risks
- Runtime/UI: N/A - agent instructions and synthetic evaluation only
- Security/migration/release: No production release; live Codex evaluations are manual release-candidate evidence and are not run during ordinary verification.
- Stop conditions: Any need for a new public command/schema/reference, behavior-test runtime that writes outside synthetic repositories, SKILL.md above 150 lines, or a change that adds interaction to ordinary L0/L1 work.

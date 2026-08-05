# RB-CONTEXT-INTAKE: Complete incomplete prompts from project evidence

Risk: L1

Depends-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: RigorBreeze must turn incomplete product prompts into a compact, evidence-backed task context before code changes without making the developer fill another document.
- Current behavior and evidence: recent backend delivery repeatedly required late clarification of live-balance semantics, allocation-versus-check-in rules, and already-completed WeChat release steps; follow-up fixes could also enter systematic debugging without re-establishing RigorBreeze state.
- Business and architecture path: Skill trigger and default prompt → repository read-only intake → single task contract → approval → implementation; external delivery additionally reconstructs observed platform state before proposing a write.
- Invariants and source of truth: recover project facts from business documents, code, tests, Git and runtime evidence; ask only for outcome-changing intent that those sources cannot establish; never let a persona phrase substitute for evidence.
- Requirement version: user request in the current RigorBreeze thread on 2026-08-05; no public CLI, Schema, Spec file type or third-party dependency change.
- Unresolved outcome-changing ambiguity: none; this is a backward-compatible v0.8.1 protocol and template refinement.

## Allowed scope
- AGENTS.md
- README.md
- README.zh-CN.md
- CHANGELOG.md
- CHANGELOG.zh-CN.md
- Skill演进与实践记录.md
- rigorbreeze/SKILL.md
- rigorbreeze/agents/openai.yaml
- rigorbreeze/references/handbook.md
- rigorbreeze/references/handbook.zh-CN.md
- rigorbreeze/scripts/flow.py
- rigorbreeze/scripts/flow_state.py
- rigorbreeze/scripts/tests/
- spec/changes/RB-CONTEXT-INTAKE.md
- spec/evidence/RB-CONTEXT-INTAKE.json
- spec/archive/RB-CONTEXT-INTAKE.md

## Forbidden scope
- Public CLI or Schema changes
- New Spec document types, runtime dependencies, or user-maintained context reports
- Product repositories, live services, WeChat platform, deployment or release operations
- Treating a role persona such as CTO as approval or evidence

## Acceptance criteria
- REQ-001: A new task template prompts Codex to record user outcome, current behavior evidence, business/architecture path, invariants/source of truth, requirement version, and unresolved outcome-changing ambiguity inside the existing Authoritative inputs section.
- REQ-002: The Skill explicitly classifies missing information into recoverable project facts, outcome-changing intent, and safe defaults; it explores and fills the first, asks only for the second, and states the third.
- REQ-003: Every non-trivial follow-up write, including after compaction or while using debugging/review skills, rechecks RigorBreeze status and ownership before product-code writes.
- REQ-004: External Git, deployment, developer-tool, or platform actions begin from an observed current-state summary of completed steps, current immutable identifiers, remaining action, and stop conditions so completed work is not repeated.
- REQ-005: English and Chinese user/maintainer documentation and UI default prompt describe the new behavior consistently as v0.8.1 without adding another reference or user step.
- REQ-006: Existing workflow behavior remains compatible and the full regression, Skill contract, link, syntax, and quick validation checks pass.
- REQ-007: Files under configured test paths are never classified as production changes merely because the test directory is nested below a configured source path.

## Test seams
- Seam: generated task contract and installed AGENTS block; Skill metadata and documentation contract.
- Independent oracle: literal required context labels, explicit follow-up re-entry and observed-state rules, unchanged Schema/CLI constants, and existing end-to-end CLI regressions.

## Verification commands
- python3 -B -m unittest discover -s rigorbreeze/scripts/tests -q
- python3 -B /Users/songjincheng/.codex/skills/.system/skill-creator/scripts/quick_validate.py rigorbreeze
- python3 -B syntax compilation without bytecode output
- git diff --check

## Conditional risks
- Runtime/UI: default prompt and installed AGENTS instruction must remain concise enough to preserve progressive disclosure.
- Security/migration/release: external-state reconstruction is read-only and cannot broaden authority for commit, push, deployment, migration, release or rollback.
- Stop conditions: a change would require a new CLI command, Schema field, second context document, telemetry, or automatic modification of product repositories.

- Evidence revision: final v0.8.1 contract after resolving self-hosted RED and formatter bootstrap findings.

# RB-INITIATIVE-SHAPING: Shape ambiguous initiatives before delivery contracts

Risk: L1

Depends-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: ADD an optional, low-friction product-shaping step for a new product, new business domain, broad legacy migration, or idea that is not yet ready to become one observable delivery task.
- Current behavior and evidence: RigorBreeze recovers facts and self-reviews a task contract, but immediately frames one vertical slice. The real Xinyuan planning session produced strong source-code migration analysis while leaving product value, usability evidence, success outcomes, and the actual task contract unresolved.
- Business and architecture path: keep RigorBreeze as the delivery control plane; before task creation only when the initiative is genuinely unshaped, produce or refine one compact, versioned initiative brief, compare approaches, expose assumptions and product risks, obtain user approval, then convert only the first slice into the existing contract.
- Invariants and source of truth: no new CLI command, schema, Spec file type, runtime dependency, mandatory PRD tree, or gate for ordinary tasks. Project/business evidence outranks personas and reference-source inference. The initiative brief is an authoritative input, not machine evidence or a substitute for task acceptance.
- Requirement/design/API version: RigorBreeze Unreleased initiative-shaping protocol, derived from the 2026-08-07 Xinyuan real-use review.
- Unresolved outcome-changing ambiguity: none; the user approved the optional minimal protocol and requested implementation without modifying the active Xinyuan product work.

## Allowed scope
- README.md
- README.zh-CN.md
- CHANGELOG.md
- CHANGELOG.zh-CN.md
- Skill演进与实践记录.md
- rigorbreeze/SKILL.md
- rigorbreeze/agents/openai.yaml
- rigorbreeze/references/handbook.md
- rigorbreeze/references/handbook.zh-CN.md
- rigorbreeze/scripts/tests/test_skill_contract.py
- spec/changes/RB-INITIATIVE-SHAPING.md
- spec/evidence/RB-INITIATIVE-SHAPING.json

## Forbidden scope
- Public CLI commands, state/evidence schemas, runner policy, risk levels, Git automation, release gates, and Spec Tree file types.
- Project-specific Xinyuan requirements, business code, or product documents.
- Mandatory initiative documents for ordinary L0/L1/L2 tasks that already have a stable observable outcome.

## Acceptance criteria
- REQ-001: Broad or genuinely ambiguous initiatives are shaped before a delivery task is created, while ordinary bounded tasks continue directly to the existing vertical-slice flow.
- REQ-002: Shaping recovers project facts first, asks only outcome-changing questions, compares two or three viable approaches, and covers problem, users/journey, desired outcome, evidence/assumptions, value/usability/feasibility/viability risks, appetite, rabbit holes, no-gos, and the first slice.
- REQ-003: Shaping reuses one existing versioned product/design document or creates one compact initiative brief; it does not create a parallel Spec tree, task DAG, or implementation contract before user approval.
- REQ-004: The approved brief becomes an authoritative input to only the first RigorBreeze task; unknown product intent cannot be inferred from reference code or a persona prompt.
- REQ-005: English/Chinese handbook and public adoption guidance stay aligned, SKILL.md stays at or below 150 lines, and deterministic contract tests prevent the protocol from disappearing or becoming mandatory for ordinary work.

## Test seams
- Seam: installable SKILL.md plus public and bundled documentation contract.
- Independent oracle: repository contract tests assert trigger, boundaries, required shaping dimensions, bilingual guidance, compact entrypoint, and unchanged public command surface.

## Verification commands
- python3 -m unittest rigorbreeze.scripts.tests.test_skill_contract
- python3 tests/behavior/run.py validate
- python3 /Users/songjincheng/.codex/skills/.system/skill-creator/scripts/quick_validate.py rigorbreeze
- python3 -m compileall -q rigorbreeze tests/behavior
- git diff --check

## Conditional risks
- Runtime/UI: the shaping protocol must not replace real user, prototype, runtime, or accessibility validation.
- Security/migration/release: reference implementations and personas cannot approve security, legal, migration, payment, or production decisions.
- Stop conditions: any proposal to add a new public command, persistent state model, mandatory PRD tree, or automatic product approval.

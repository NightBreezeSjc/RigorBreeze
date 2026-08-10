# RB-XINYUAN-REAL-USE-0121: Turn Xinyuan workflow failures into lean reusable guardrails

Risk: L1

Depends-On: none

Task-Origin: current-request

Waiting-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: turn the concrete failures observed in the Xinyuan source-baseline task into small reusable RigorBreeze safeguards, then deliver them as an isolated pull request without changing the active business implementation.
- Current behavior and evidence: `destructive_migrations(root)` scans every configured historical migration during `verify`; the Xinyuan task therefore patched its project runner and widened its business contract. The same task created successive planning, integration and P00 worktrees for sequential work, ran L2-wide checks for read-only evidence tooling, retained more than 100k lines of raw generated inventory, and used semantic matching as part of a claimed source-completeness proof.
- Business and architecture path: fix the migration gate in the reusable core; make business-task/core-workflow separation, sequential-worktree reuse, risk-adaptive evidence tooling, compact evidence retention and independent-oracle requirements explicit in the existing Skill/handbook; lock the behavior with runner, contract and behavior tests.
- Invariants and source of truth: only migration files in the task's complete change set may trigger the destructive-migration gate; existing historical migrations remain project facts but cannot block unrelated work. The active Xinyuan task, its Git worktree and evidence remain authoritative for that business task and are not edited by this repository task.
- Requirement/design/API version: RigorBreeze v0.13.0 Public Preview; workflow schema v4 and automation journal v1 remain unchanged; public CLI and Spec Tree remain unchanged.
- Unresolved outcome-changing ambiguity: none; the user explicitly requested that all lessons be repaired, committed, proposed by PR and then applied to the Xinyuan task.

## Allowed scope
- AGENTS.md
- README.md
- README.zh-CN.md
- CHANGELOG.md
- CHANGELOG.zh-CN.md
- CONTRIBUTING.md
- CONTRIBUTING.zh-CN.md
- Skill演进与实践记录.md
- rigorbreeze.toml
- rigorbreeze/SKILL.md
- rigorbreeze/agents/openai.yaml
- rigorbreeze/references/handbook.md
- rigorbreeze/references/handbook.zh-CN.md
- rigorbreeze/references/ci-gates.md
- rigorbreeze/references/ci-gates.zh-CN.md
- rigorbreeze/references/spec-tree.md
- rigorbreeze/references/spec-tree.zh-CN.md
- rigorbreeze/scripts/flow.py
- rigorbreeze/scripts/flow_policy.py
- rigorbreeze/scripts/flow_state.py
- rigorbreeze/scripts/tests/
- tests/behavior/
- spec/changes/RB-XINYUAN-REAL-USE-0121.md
- spec/evidence/RB-XINYUAN-REAL-USE-0121.json
- spec/archive/RB-XINYUAN-REAL-USE-0121.md

## Forbidden scope
- Any file in `lc-govkit/home-api`, `lc-govkit/home-ui` or `lc-govkit/home-uniapp`
- New public CLI commands, Spec file types, schema fields, runtime dependencies or orchestration platforms
- Automatic deletion of existing worktrees, branches, generated evidence or business-task history
- Relaxing destructive-migration detection for migration files actually changed by the current task

## Acceptance criteria
- REQ-001: verify ignores destructive SQL that exists only in unchanged historical migration files.
- REQ-002: verify still blocks a destructive migration file in the current task's committed or working-tree change set.
- REQ-003: when a business task exposes a reusable RigorBreeze defect, the Agent records the blocker/evolution candidate and creates a separate Skill task instead of widening the business contract or patching its private runner.
- REQ-004: sequential initiative work reuses its designated integration worktree; a new worktree is created only for a genuinely concurrent writer or an explicitly disposable risky experiment.
- REQ-005: read-only scanner/evidence tooling uses consequence-based L1 verification unless it performs migration, production, credential or release writes; tracked evidence is compact and raw inventories stay local/CI.
- REQ-006: a source-completeness or brand-attribution claim requires an independent oracle; filename/token/semantic matching alone cannot prove completeness.
- REQ-007: English and Chinese documentation, version metadata, Skill contract and deterministic behavior scenarios remain consistent without increasing the public CLI or Spec Tree.

## Test seams
- Seam: configured `verify --profile affected|full`, Skill contract assertions and synthetic Agent behavior scenarios.
- Independent oracle: temporary Git repositories containing one unchanged historical destructive migration and one task-local destructive migration; deterministic transcript rules that reject scope expansion, unnecessary worktrees, oversized tracked raw output and self-derived completeness claims.

## Verification commands
- python3 -m ruff format --check rigorbreeze/scripts tests/behavior
- python3 -m ruff check rigorbreeze/scripts tests/behavior
- python3 -B -m unittest discover -s rigorbreeze/scripts/tests -v
- python3 -B -m unittest discover -s tests/behavior -v
- python3 /Users/songjincheng/.codex/skills/.system/skill-creator/scripts/quick_validate.py rigorbreeze
- python3 -m py_compile rigorbreeze/scripts/flow.py rigorbreeze/scripts/flow_policy.py rigorbreeze/scripts/flow_state.py
- git diff --check

## Conditional risks
- Runtime/UI: no runtime product behavior or UI is modified.
- Security/migration/release: the migration gate must narrow only its candidate set, never its destructive SQL detection; no release, migration or remote business write is authorized.
- Stop conditions: any change requiring a new CLI, schema, Spec file type, business-repository edit or automatic worktree deletion.

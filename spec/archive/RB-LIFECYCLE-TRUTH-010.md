# RB-LIFECYCLE-TRUTH-010: Keep delivered task state truthful after bypass or patch-equivalent integration

Risk: L1

Depends-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: evolve RigorBreeze from the three-repository audit so completed work cannot remain hidden behind stale workflow state and direct delivery changes cannot bypass the approval record silently.
- Current behavior and evidence: SYSTEM-REPORTING-CONSISTENCY contains uncommitted production and test changes while its task remains draft with no approval or RED, yet no practice event is emitted. Five other real task branches contain workflow-baseline/task-record commits plus a product commit whose patch is already present on main; current `git cherry` classification treats the workflow-only commits as unfinished product work and reports baseline stale instead of integrated-unclosed.
- Business and architecture path: detect unapproved working-tree delivery changes from existing Git and state facts, project and record one deduplicated safety event, and refine registered-task integration proof to ignore only known workflow metadata commits while preserving the existing conservative unmanaged-worktree proof.
- Invariants and source of truth: Git remains authoritative for changed paths and patch equivalence; task/evidence/runner metadata never proves product delivery; partial product patches, mixed product-plus-workflow commits, and unknown paths must remain not integrated; status may record a machine practice event but must not modify product files.
- Requirement/design/API version: user-approved audit follow-up dated 2026-08-07; RigorBreeze v0.10.0 candidate, schema v4 and automation journal v1 remain compatible.
- Unresolved outcome-changing ambiguity: none. P1 baseline sequencing and duplicate-registry repair remain validation candidates, not implementation scope for this task.

## Allowed scope
- README.md
- README.zh-CN.md
- CHANGELOG.md
- CHANGELOG.zh-CN.md
- CONTRIBUTING.md
- CONTRIBUTING.zh-CN.md
- Skill演进与实践记录.md
- rigorbreeze/SKILL.md
- rigorbreeze/agents/openai.yaml
- rigorbreeze/references/handbook.md
- rigorbreeze/references/handbook.zh-CN.md
- rigorbreeze/references/spec-tree.md
- rigorbreeze/references/spec-tree.zh-CN.md
- rigorbreeze/scripts/flow.py
- rigorbreeze/scripts/flow_parallel.py
- rigorbreeze/scripts/flow_policy.py
- rigorbreeze/scripts/flow_state.py
- rigorbreeze/scripts/tests/test_flow_v3.py
- rigorbreeze/scripts/tests/test_flow_v4.py
- rigorbreeze/scripts/tests/test_skill_contract.py
- spec/changes/RB-LIFECYCLE-TRUTH-010.md
- spec/evidence/RB-LIFECYCLE-TRUTH-010.json
- spec/archive/RB-LIFECYCLE-TRUTH-010.md

## Forbidden scope
- No changes to business repositories, their task records, worktrees, branches, commits, or remote state.
- No automatic approval, fabricated RED/GREEN, or retrospective confirmation.
- No broad backlog planner, new public CLI command, new Spec file type, schema bump, or third-party dependency.
- No weakening of unmanaged-worktree cleanup, partial-patch, dirty-worktree, or branch-protection rules.

## Acceptance criteria
- REQ-001: Current and all-worktree status detect an unapproved task with non-workflow delivery changes, prioritize a truthful recovery action, and record one deduplicated `workflow-bypass` practice event flagged as an immediate evolution candidate.
- REQ-002: A registered task branch containing only extra workflow metadata commits plus a product commit already patch-equivalent on the base is reported `integrated-unclosed`, with stale verification suppressed and the normal reconciled-close action.
- REQ-003: A branch containing any unmatched or mixed product change remains not integrated; unmanaged worktree proof and cleanup stay conservative.
- REQ-004: Existing CLI JSON remains additive and compatible, Skill stays compact, and all current state, parallel, lifecycle, behavior, documentation, and packaging tests remain green.

## Test seams
- Seam: `status --json`, `status --all --json`, practice evidence, registered-task `git cherry` classification, and cleanup projection in temporary Git repositories.
- Independent oracle: actual porcelain paths and commit path sets define a bypass; `git cherry` must contain at least one negative product patch and every positive commit must contain only allowlisted workflow metadata before a task qualifies as patch-equivalent.

## Verification commands
- `python3 -m unittest rigorbreeze.scripts.tests.test_flow_v3 rigorbreeze.scripts.tests.test_flow_v4`
- `python3 -m unittest discover -s rigorbreeze/scripts/tests -p 'test_*.py'`
- `python3 -m unittest discover -s tests/behavior -p 'test_*.py'`
- `python3 tests/behavior/run.py validate`
- `python3 -m ruff format --check rigorbreeze/scripts tests/behavior`
- `python3 -m ruff check rigorbreeze/scripts tests/behavior`
- `python3 /Users/songjincheng/.codex/skills/.system/skill-creator/scripts/quick_validate.py rigorbreeze`
- `git diff --check`

## Conditional risks
- Runtime/UI: status becomes evidence-writing only when an active unapproved task already has non-workflow delivery changes; ordinary read-only status remains side-effect free.
- Security/migration/release: workflow-only filtering must be an explicit narrow allowlist and cannot hide product, migration, dependency, security, or release changes.
- Stop conditions: any solution requires guessing integration from filenames outside the allowlist, relaxing partial patch proof, or adding a second lifecycle/state model.

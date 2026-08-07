# RB-MANAGED-CLEANUP-0102: Keep shared historical worktree cleanup state consistent

Risk: L1

Depends-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: finish the approved three-repository governance and RigorBreeze cleanup sequence without leaving known workflow errors.
- Current behavior and evidence: cleaning a managed worktree shared by two archived registry entries removes the directory but marks only the managing task as removed; `doctor --all --json` then crashes while projecting the second stale path.
- Business and architecture path: keep cleanup ownership conservative, but atomically mark every registry entry that references the exact removed path after Git confirms removal.
- Invariants and source of truth: Git worktree removal result and the common-directory registry are authoritative; branches and tracked evidence remain preserved.
- Requirement/design/API version: v0.10.2 Public Preview patch; schema v4 and automation journal v1 remain unchanged.
- Unresolved outcome-changing ambiguity: none.

## Allowed scope
- rigorbreeze/scripts/flow_parallel.py
- rigorbreeze/scripts/flow.py
- rigorbreeze/scripts/flow_state.py
- rigorbreeze/scripts/tests/test_flow_v3.py
- rigorbreeze/scripts/tests/test_flow_v4.py
- rigorbreeze/scripts/tests/test_skill_contract.py
- README.md
- README.zh-CN.md
- CHANGELOG.md
- CHANGELOG.zh-CN.md
- Skill演进与实践记录.md
- spec/changes/RB-MANAGED-CLEANUP-0102.md
- spec/evidence/RB-MANAGED-CLEANUP-0102.json
- spec/archive/RB-MANAGED-CLEANUP-0102.md

## Forbidden scope
- Product repositories and business source code
- New CLI commands, Spec file types, dependencies, or Git authority
- Automatic branch deletion or force cleanup

## Acceptance criteria
- REQ-001: After one managed worktree is safely removed, every registry task referencing that exact path is marked `worktreeRemoved=true` in the same registry update.
- REQ-002: A subsequent `status --all --json` and `doctor --all --json` succeeds without invoking Git inside the removed directory.
- REQ-003: Cleanup output remains backward compatible: the `removed` list names only the task that authorized the physical removal, and branches remain preserved.
- REQ-004: `doctor --all --repair --json` treats archived history and the current active task in one primary worktree as sequential records, and does not compare an archived task's historical branch with the current primary branch.

## Test seams
- Seam: create two archived registry records that share one managed worktree, integrate the branch, and run managed cleanup.
- Seam: rebuild a registry that contains archived tasks from removed branches plus one active task in the primary worktree.
- Independent oracle: the directory no longer exists, both cleanup records carry `worktreeRemoved=true`, the branch still exists, repair retains all tasks, and doctor returns `status=ok` without duplicate or branch-mismatch issues.

## Verification commands
- python3 -m unittest rigorbreeze.scripts.tests.test_flow_v3
- python3 -m unittest discover -s rigorbreeze/scripts/tests -p 'test_*.py'
- python3 tests/behavior/test_behavior.py
- ruff format --check rigorbreeze/scripts tests/behavior
- ruff check rigorbreeze/scripts tests/behavior
- python3 -m compileall -q rigorbreeze/scripts tests/behavior
- python3 /Users/songjincheng/.codex/skills/.system/skill-creator/scripts/quick_validate.py rigorbreeze
- git diff --check

## Conditional risks
- Runtime/UI: N/A unless applicable
- Security/migration/release: N/A unless applicable
- Stop conditions: scope or acceptance changes

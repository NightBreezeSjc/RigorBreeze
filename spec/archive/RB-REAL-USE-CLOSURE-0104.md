# RB-REAL-USE-CLOSURE-0104: Keep real-use workflow recovery actionable and visible

Risk: L1

Depends-On: RB-EVIDENCE-RETENTION-0103

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: Recent real tasks should recover from stale/missing workflow records without crashing, surface recorded evolution candidates, and prevent a new or high-risk task from silently bypassing RigorBreeze.
- Current behavior and evidence: In home-api/home-ui, `status --all --json` aborts when a registered active contract is missing while `doctor --all --json` reports no issue; a mini-app `workflow-bypass` candidate stayed buried in evidence; new L1/L2 work can be framed before installation/baseline drift is resolved; one production-release task continued with a manual card after workflow state failed; an intentional Xinyuan draft was later mistaken for disposable residue because its origin and waiting condition were not machine-visible.
- Business and architecture path: Add recovery projections and deterministic preflight policy to the existing runner; keep practice evidence and Git-private registry authoritative; extend the existing repository-only behavior suite instead of adding another workflow or state system.
- Invariants and source of truth: Task Markdown/evidence/Git/private registry remain authoritative; recovery never invents a contract, approval, RED, test, acceptance, integration or completion result; project environment and adapter failures stay outside the core.
- Requirement/design/API version: RigorBreeze v0.10.4 Public Preview; workflow schema v4 and automation journal v1 remain unchanged.
- Unresolved outcome-changing ambiguity: None. The user explicitly asked to implement the previously reported narrow core improvements.

## Allowed scope
- README.md
- README.zh-CN.md
- CHANGELOG.md
- CHANGELOG.zh-CN.md
- Skill演进与实践记录.md
- rigorbreeze/SKILL.md
- rigorbreeze/references/handbook.md
- rigorbreeze/references/handbook.zh-CN.md
- rigorbreeze/references/spec-tree.md
- rigorbreeze/references/spec-tree.zh-CN.md
- rigorbreeze/scripts/flow.py
- rigorbreeze/scripts/flow_parallel.py
- rigorbreeze/scripts/flow_policy.py
- rigorbreeze/scripts/flow_state.py
- rigorbreeze/scripts/tests/
- tests/behavior/
- spec/changes/RB-REAL-USE-CLOSURE-0104.md
- spec/evidence/RB-REAL-USE-CLOSURE-0104.json
- spec/archive/RB-REAL-USE-CLOSURE-0104.md
- spec/archive/RB-EVIDENCE-RETENTION-0103.md
- spec/evidence/RB-EVIDENCE-RETENTION-0103.json

## Forbidden scope
- Product repositories and their current tasks/worktrees
- New public CLI commands, Spec file types, state systems, third-party dependencies or deployment adapters
- Automatic deletion, repair, commit, push, merge, release or production operation
- Project-specific WeChat, Docker registry, Maven, browser or credential behavior

## Acceptance criteria
- REQ-001: `status --all --json` and `doctor --all --json` consistently represent a registered active task whose contract is missing as an `orphaned-record`, with a non-destructive repair action instead of one command aborting and the other reporting healthy.
- REQ-002: Existing task evidence with `evolutionCandidate: true` is projected by status and produces a visible, copyable `$rigorbreeze 汇总这个项目的演进候选` reminder without creating another practice log.
- REQ-003: Starting a new L1/L2 task fails before contract creation when the installed runner or real base-branch workflow baseline is not current; L0 remains lightweight and existing active tasks remain recoverable through the bundled runner.
- REQ-004: The Agent behavior contract rejects continuing high-risk product or deployment writes after workflow status/doctor failure unless the record is repaired or an explicit Emergency/break-glass path is established.
- REQ-005: New task contracts and status projections preserve compact task origin and waiting-condition facts so an intentional draft is not treated as accidental residue merely because it has no implementation.
- REQ-006: Existing v0.10.3 CLI, schema, evidence compaction, Git automation, parallel worktree and release behavior remain compatible.

## Test seams
- Seam: Runner CLI against temporary Git repositories, registry/evidence fixtures, and repository-only Agent behavior transcripts.
- Independent oracle: JSON lifecycle/next-action/evolution projections, filesystem non-mutation assertions, subprocess exit codes, and exact forbidden/required behavior markers.

## Verification commands
- python3 -m unittest discover -s rigorbreeze/scripts/tests -v
- python3 -m unittest tests.behavior.test_behavior -v
- python3 /Users/songjincheng/.codex/skills/.system/skill-creator/scripts/quick_validate.py rigorbreeze
- python3 -m compileall -q -f rigorbreeze/scripts tests/behavior
- git diff --check

## Conditional risks
- Runtime/UI: N/A unless applicable
- Security/migration/release: N/A unless applicable
- Stop conditions: scope or acceptance changes

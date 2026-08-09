# RB-RISK-ADAPTIVE-0110: Keep ordinary solo work light while preserving production gates

Risk: L1

Depends-On: RB-REAL-USE-CLOSURE-0104

Task-Origin: current-request

Waiting-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: RigorBreeze must stay heavy for production-risk work while ordinary solo development, read-only diagnosis, small edits, handoffs, and repeated task closure remain understandable and proportionate.
- Current behavior and evidence: Recent real delivery repeatedly stopped unsafe RSA, secret, image, migration, and candidate-container failures before production replacement, but read-only questions were sometimes treated as delivery work, infrastructure upgrades were mixed into ordinary releases, cross-task delegation was not visible enough, completed TDD evidence duplicated RED history, and the published Skill archive included maintainer tests and caches. Moving all task records into a new private storage system would reduce Git noise but would also add another path, migration, cleanup, and cross-worktree authority surface before that design is proven.
- Business and architecture path: Tighten request routing and release-scope rules in the existing Skill contract, add repository-only behavior scenarios, compact only redundant completed TDD history in the existing evidence JSON, and exclude maintainer-only assets from the existing ZIP build. Keep the current Spec Tree and Git-private state architecture unchanged.
- Invariants and source of truth: Risk follows consequence rather than code size; read-only work never needs a delivery task; L2 production writes retain preview, backup, rehearsal, stop, rollback, artifact, and real-acceptance gates; active/abandoned/reconciled evidence and regression tests are never compacted; Git and external runtime state remain authoritative for delivery claims.
- Requirement/design/API version: RigorBreeze v0.11.0 Public Preview; workflow schema v4, automation journal v1, public CLI, Spec file types, and runtime dependencies remain unchanged.
- Unresolved outcome-changing ambiguity: None. The user explicitly approved a risk-adaptive low-friction iteration based on recent real-project evidence.

## Allowed scope
- README.md
- README.zh-CN.md
- CHANGELOG.md
- CHANGELOG.zh-CN.md
- CONTRIBUTING.md
- CONTRIBUTING.zh-CN.md
- Skill演进与实践记录.md
- rigorbreeze.toml
- rigorbreeze/SKILL.md
- rigorbreeze/references/handbook.md
- rigorbreeze/references/handbook.zh-CN.md
- rigorbreeze/references/spec-tree.md
- rigorbreeze/references/spec-tree.zh-CN.md
- rigorbreeze/references/ci-gates.md
- rigorbreeze/references/ci-gates.zh-CN.md
- rigorbreeze/scripts/flow.py
- rigorbreeze/scripts/flow_state.py
- rigorbreeze/scripts/tests/
- tests/behavior/
- spec/changes/RB-RISK-ADAPTIVE-0110.md
- spec/evidence/RB-RISK-ADAPTIVE-0110.json
- spec/archive/RB-RISK-ADAPTIVE-0110.md

## Forbidden scope
- Product repositories, their active tasks, deployments, databases, credentials, worktrees, or remote branches
- New risk levels, public CLI commands, Spec file types, task databases, evidence stores, orchestration consoles, third-party dependencies, or deployment adapters
- Lowering L2 security, migration, payment, permission, release, backup, rollback, real-acceptance, or protected-delivery gates
- Deleting regression tests, failed evidence, active evidence, abandoned/reconciled history, branches, or user project records
- Automatically committing, pushing, merging, releasing, migrating, rolling back, or editing Git provider protection

## Acceptance criteria
- REQ-001: The Agent contract routes status questions, log explanations, screenshots, recommendations, and other no-write diagnosis through a no-task path; workflow drift may be reported but cannot block the read-only answer.
- REQ-002: Risk selection follows consequence: isolated non-behavioral work stays L0, ordinary observable behavior stays L1, and data, payment, permission, external integration, infrastructure, and production writes remain L2 even when the code diff is small.
- REQ-003: A deployment task freezes its approved operational scope; unrelated base-image, operating-system, database-engine, security-tool, or deployment-framework upgrades become separate tasks unless a newly discovered critical risk makes the current release unsafe, in which case the release stops rather than expanding silently.
- REQ-004: A cross-task handoff explicitly shows the destination task/window, observable result, allowed scope, forbidden scope, dependency or blocking reason, and ownership; the receiving task remains authoritative and no hidden command relationship is created.
- REQ-005: A normally completed archive retains the final valid GREEN chain and at most the latest useful earlier failed/invalidated chain per acceptance ID, records aggregate counts, and removes duplicated top-level RED history that is already represented by retained TDD chains. Active, abandoned, and reconciled histories remain byte-for-byte uncompressed by this policy.
- REQ-006: The published Skill ZIP contains runtime Skill files and references but excludes maintainer tests, `.ruff_cache`, `__pycache__`, bytecode, and other repository-only test caches; repository tests remain tracked and continue running in CI.
- REQ-007: Documentation explains that tracked task records remain the current auditable default, while raw logs and transient reports stay ignored or in CI artifacts; moving all records to a new private store is explicitly deferred until real use proves that the added authority and recovery complexity is worthwhile.
- REQ-008: Existing v0.10.4 CLI, schema-v4 upgrades, checks, TDD gates, Git automation, parallel worktrees, release behavior, and historical evidence remain compatible.

## Test seams
- Seam: Runner archive behavior in temporary Git repositories, repository ZIP inspection, Skill contract assertions, and synthetic Agent transcripts for read-only routing, release-scope freeze, and explicit handoff.
- Independent oracle: Exact retained evidence groups and aggregate counts, archive member names, no-mutation assertions, deterministic behavior markers/transcripts, existing CLI JSON, and full regression outcomes.

## Verification commands
- python3 -m unittest discover -s rigorbreeze/scripts/tests -v
- python3 -m unittest tests.behavior.test_behavior -v
- python3 /Users/songjincheng/.codex/skills/.system/skill-creator/scripts/quick_validate.py rigorbreeze
- python3 -m ruff format --check rigorbreeze/scripts tests/behavior
- python3 -m ruff check rigorbreeze/scripts tests/behavior
- python3 -m compileall -q -f rigorbreeze/scripts tests/behavior
- git diff --check

## Conditional risks
- Runtime/UI: N/A unless applicable
- Security/migration/release: The change alters Agent routing around release work but must only narrow unsolicited scope expansion; existing L2 blocking conditions remain unchanged.
- Stop conditions: scope or acceptance changes

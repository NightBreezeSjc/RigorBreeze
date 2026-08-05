# RB-LOW-FRICTION-091: Reduce verification friction without weakening delivery gates

Risk: L1

Depends-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: Make an explicitly requested Git commit fast and predictable while preserving RigorBreeze's scope, secret, dependency, migration, merge and release safety boundaries.
- Current behavior and evidence: v0.9.0 commit friction exposed a Python 3.14 bytes/str crash after a 120-second check timeout, duplicate execution of the same 113-test command under unit and acceptance, a false positive on synthetic redaction fixtures, and an unnecessary attempt to run live release-candidate Agent evaluations for an ordinary commit.
- Business and architecture path: Keep the existing affected/full profiles and commit/merge/release gates; repair subprocess normalization, reuse identical executions only inside one profile invocation, add a line-scoped synthetic-secret marker under configured test paths, and clarify maintainer-only release-candidate evaluation.
- Invariants and source of truth: Exact check argv/cwd/env/timeout define one process execution; each check still validates its own report and artifacts. A marked fixture never bypasses secret paths or the configured secret adapter. Ordinary commit accepts only current configured affected/full evidence; archive, integration-branch delivery, merge and release retain their stronger gates.
- Requirement/design/API version: User-approved RigorBreeze v0.9.1 low-friction closure plan; Evidence/State Schema v4 and Automation Journal v1 remain unchanged.
- Unresolved outcome-changing ambiguity: none; the user selected risk-minimal commit verification and same-line markers limited to configured test paths.

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
- tests/behavior/run.py
- tests/behavior/test_behavior.py
- spec/changes/RB-LOW-FRICTION-091.md
- spec/evidence/RB-LOW-FRICTION-091.json
- spec/archive/RB-LOW-FRICTION-091.md

## Forbidden scope
- New public CLI commands, profiles, Spec files, state systems, runtime dependencies or automation authority
- Relaxing secret-path checks, configured secret adapters, dependency/migration approval, full archive/merge gates or protected delivery
- Persisting cross-profile check caches or invoking live Codex behavior evaluations from commit, full or CI
- Product repositories, remote Git writes, tags, releases, deployments, migrations or real credentials

## Acceptance criteria
- REQ-001: A timed-out configured check normalizes bytes, text or missing stdout/stderr, records exit code 124 and a redacted timeout summary, and never raises a bytes/str TypeError.
- REQ-002: Within one profile invocation, checks with identical argv, resolved cwd, environment and timeout execute once while retaining separate check records; each reused check independently fails when its own report or artifact is invalid.
- REQ-003: Checks whose argv, cwd, environment or timeout differ execute independently, and no result is reused across profile invocations or project changes.
- REQ-004: The exact same-line marker `rigorbreeze: synthetic-secret` exempts only the matching content heuristic under configured test paths and reports only file/line metadata.
- REQ-005: Unmarked matches, matches outside configured test paths, other lines in the same file and secret-like paths remain blocked; configured secret checks still run and can fail.
- REQ-006: A normal commit requires current configured affected or full evidence; targeted, stale or failed evidence cannot satisfy the gate.
- REQ-007: L1/L2 archive, merge and direct integration-branch push retain full verification, acceptance and review requirements where currently applicable.
- REQ-008: Ordinary commit, configured full verification and CI never invoke live Codex behavior tests; six scenarios twice remain an explicit maintainer release-candidate action whose default result version matches v0.9.1.
- REQ-009: RigorBreeze's full profile runs the core unit suite once and the deterministic behavior suite once, with a 240-second core-suite timeout.
- REQ-010: English and Chinese public/maintainer documentation identify v0.9.1 consistently, SKILL.md remains at most 150 lines, and no command, schema version or dependency is added.

## Test seams
- Seam: configured profile subprocess execution; staged secret-content scan; commit gate freshness; Skill/documentation contract.
- Independent oracle: mocked TimeoutExpired payloads and subprocess invocation counters; staged Git fixtures with exact line/path variants plus a deliberately failing configured scanner; targeted versus configured verification records; exact documentation assertions and line-count limit.

## Verification commands
- python3 -B -m unittest discover -s rigorbreeze/scripts/tests -v
- python3 -B -m unittest discover -s tests/behavior -v
- python3 -B tests/behavior/run.py validate
- python3 -B /Users/songjincheng/.codex/skills/.system/skill-creator/scripts/quick_validate.py rigorbreeze
- python3 -B syntax compilation without bytecode output
- python3 -m ruff format --check rigorbreeze/scripts tests/behavior
- python3 -m ruff check rigorbreeze/scripts tests/behavior
- git diff --check

## Conditional risks
- Runtime/UI: no product runtime; reuse is process-local and keyed by the complete execution identity.
- Security/migration/release: marker exemptions are line-scoped test fixtures only and never replace the configured secret adapter; delivery gates remain unchanged.
- Stop conditions: any solution requires a public command/profile, persistent cache, schema bump, dependency, broad file-level secret waiver or weaker protected delivery gate.

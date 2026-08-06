# RB-CI-WINDOWS-PROCESS-CHECK: Keep window ownership checks side-effect free on Windows

Risk: L1

Depends-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: publish the repository with its first remote CI run passing on every declared platform.
- Current behavior and evidence: GitHub Actions job 92551287598 is interrupted in `test_window_claim_blocks_a_second_live_session` when `process_alive()` calls `os.kill(pid, 0)` on Windows.
- Business and architecture path: `flow_parallel.process_alive` guards exclusive worktree ownership; the probe must remain read-only on every platform.
- Invariants and source of truth: a live owner blocks a second session, a dead owner may be reclaimed, and the liveness probe must never signal or terminate the owner.
- Requirement/design/API version: RigorBreeze 0.9.2, state schema v4, automation journal v1.
- Unresolved outcome-changing ambiguity: none.

## Allowed scope
- rigorbreeze/scripts/flow_parallel.py
- rigorbreeze/scripts/flow_policy.py
- rigorbreeze/scripts/tests/test_flow_graph.py
- rigorbreeze/scripts/tests/test_flow_v2.py
- CHANGELOG.md
- CHANGELOG.zh-CN.md

## Forbidden scope
- Public CLI, Spec Tree, schema, automation authority, and unrelated workflow behavior.

## Acceptance criteria
- REQ-001: Windows process liveness uses a side-effect-free native query and never calls `os.kill(pid, 0)`.
- REQ-002: POSIX process liveness retains the existing signal-zero behavior.
- REQ-003: The full local suite and the GitHub Actions Windows, macOS, Linux matrix pass.
- REQ-004: Re-observing RED for the same acceptance ID preserves history but only the latest current chain participates in closure gates.

## Test seams
- Seam: platform-specific process-liveness dispatch and the existing two-window claim integration test.
- Independent oracle: mocked call routing plus the real Windows GitHub Actions runner.

## Verification commands
- python3 -m unittest rigorbreeze.scripts.tests.test_flow_graph -v
- python3 -m unittest discover -s rigorbreeze/scripts/tests -v
- python3 tests/behavior/run.py validate
- python3 -m unittest discover -s tests/behavior -v

## Conditional risks
- Runtime/UI: process ownership only; no product runtime or UI change.
- Security/migration/release: no security policy, migration, or release authority change.
- Stop conditions: scope or acceptance changes

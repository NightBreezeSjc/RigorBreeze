# RB-LEGACY-STATE-RETIREMENT: Retire the tracked legacy state cache

Risk: L0

Depends-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: Remove the non-blocking Doctor warning caused by the obsolete tracked state cache without losing current workflow history.
- Current behavior and evidence: `spec/state.json` is a tracked 372-byte empty baseline from 2026-07-22, while `.git/rigorbreeze/state.json` is the current 7429-byte schema-v4 state containing the latest closed task and verification summary; Doctor retains the divergent tracked legacy file by policy and warns.
- Business and architecture path: Keep Git-private worktree state as the sole machine state, retire the obsolete tracked cache, and prevent it from being added again.
- Invariants and source of truth: `.git/rigorbreeze/state.json`, archived contracts, task evidence, and the common registry remain unchanged; no runner, task lifecycle, branch, tag, release, or product behavior changes.
- Requirement/design/API version: RigorBreeze v0.10.2 repository housekeeping; state/evidence schema v4 and automation journal v1 remain unchanged.
- Unresolved outcome-changing ambiguity: none.

## Allowed scope
- .gitignore
- spec/state.json
- spec/changes/RB-LEGACY-STATE-RETIREMENT.md
- spec/evidence/RB-LEGACY-STATE-RETIREMENT.json
- spec/archive/RB-LEGACY-STATE-RETIREMENT.md

## Forbidden scope
- RigorBreeze runner, policy, CLI, documentation, tests, historical contracts/evidence, Git branches/tags/releases, and product code.

## Acceptance criteria
- REQ-001: `spec/state.json` is absent from both the working tree and Git index while `.git/rigorbreeze/state.json` still reports schema v4 and the current `lastClosed` history.
- REQ-002: `/spec/state.json` is ignored against accidental reintroduction and `doctor --all --json` reports `status=ok` with no legacy-state warning.

## Test seams
- Seam: Git index/ignore behavior and RigorBreeze Doctor projection.
- Independent oracle: exact Git path queries plus parsed Doctor JSON and before/after private-state digest.

## Verification commands
- `python3 scripts/rigorbreeze.py doctor --all --json`
- `git ls-files spec/state.json`
- `git check-ignore -v --no-index spec/state.json`
- configured `affected` profile

## Conditional risks
- Runtime/UI: N/A unless applicable
- Security/migration/release: N/A unless applicable
- Stop conditions: scope or acceptance changes

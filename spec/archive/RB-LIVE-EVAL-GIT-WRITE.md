# RB-LIVE-EVAL-GIT-WRITE: Let synthetic live evaluations create Git-private workflow state

Risk: L1

Depends-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: complete the v0.9.2 Public Preview release with trustworthy live Agent behavior evidence.
- Current behavior and evidence: context-semantics run 1 stopped before product changes because child Codex workspace-write denied creation of `.git/rigorbreeze/flow.lock` in the synthetic repository.
- Business and architecture path: maintainer-only `tests/behavior/run.py` Codex invocation and its deterministic unit contract.
- Invariants and source of truth: live evaluations use only generated synthetic repositories; workspace source remains constrained; only that fixture's `.git` directory gains write access; ordinary projects and installed Skill behavior do not change.
- Requirement/design/API version: local `codex exec` 0.147.0 supports `--add-dir` for an additional writable directory.
- Unresolved outcome-changing ambiguity: none.

## Allowed scope
- tests/behavior/run.py
- tests/behavior/test_behavior.py
- CHANGELOG.md
- CHANGELOG.zh-CN.md
- spec/changes/RB-LIVE-EVAL-GIT-WRITE.md
- spec/evidence/RB-LIVE-EVAL-GIT-WRITE.json

## Forbidden scope
- rigorbreeze/**
- scripts/**
- README.md
- README.zh-CN.md
- .github/**

## Acceptance criteria
- REQ-001: The live Codex argv keeps `workspace-write` and explicitly adds only the generated fixture `.git` directory as writable.
- REQ-002: A real context-semantics evaluation can create and operate RigorBreeze Git-private state instead of stopping on `flow.lock` permissions.
- REQ-003: Offline behavior contracts, Skill contracts, and repository CI remain unchanged.

## Test seams
- Seam: live-evaluation child process argv.
- Independent oracle: a unit test captures the constructed argv, followed by one real context-semantics run in a generated repository.

## Verification commands
- python3 -B -m unittest discover -s tests/behavior -v
- python3 -B rigorbreeze/scripts/tests/test_skill_contract.py
- python3 -B tests/behavior/run.py run --version 0.9.2 --repetitions 1 --case context-semantics
- git diff --check

## Conditional risks
- Runtime/UI: N/A unless applicable
- Security/migration/release: N/A unless applicable
- Stop conditions: any proposal to use unrestricted filesystem access or a non-synthetic repository.

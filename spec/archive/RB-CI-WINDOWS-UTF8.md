# RB-CI-WINDOWS-UTF8: Keep CLI guidance printable on Windows

Risk: L1

Depends-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: complete the first public GitHub CI matrix without removing bilingual user guidance.
- Current behavior and evidence: Windows 3.11 and 3.13 jobs in run 31092055950 fail with `UnicodeEncodeError` when `retro` prints the Chinese evolution command through a cp1252 stdout.
- Business and architecture path: every CLI command exits through `flow.py`; stream encoding must be normalized once at the process boundary.
- Invariants and source of truth: stdout/stderr remain text streams, Chinese guidance is preserved, and redirected/test streams without `reconfigure` remain supported.
- Requirement/design/API version: RigorBreeze 0.9.2, state schema v4, automation journal v1.
- Unresolved outcome-changing ambiguity: none.

## Allowed scope
- rigorbreeze/scripts/flow.py
- rigorbreeze/scripts/tests/test_flow_simplified.py
- CHANGELOG.md
- CHANGELOG.zh-CN.md

## Forbidden scope
- Workflow semantics, public CLI arguments, schema, CI-only encoding overrides, and removal of Chinese guidance.

## Acceptance criteria
- REQ-001: CLI stdout and stderr use UTF-8 with safe replacement when the stream supports reconfiguration.
- REQ-002: The evolution reminder prints successfully even when the inherited `PYTHONIOENCODING` is cp1252.
- REQ-003: The full local suite and GitHub Windows, macOS, Linux matrix pass.

## Test seams
- Seam: the existing negative retrospective subprocess test with a forced cp1252 inherited encoding.
- Independent oracle: exact Unicode reminder text and both real GitHub-hosted Windows Python versions.

## Verification commands
- python3 -m unittest discover -s rigorbreeze/scripts/tests -p test_flow_simplified.py -v
- python3 scripts/rigorbreeze.py --root . --mode enforced verify --profile full

## Conditional risks
- Runtime/UI: CLI text encoding only; no product runtime or UI behavior.
- Security/migration/release: no security, migration, or delivery authority change.
- Stop conditions: scope or acceptance changes

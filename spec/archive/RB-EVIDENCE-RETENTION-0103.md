# RB-EVIDENCE-RETENTION-0103: Compact completed-task verification history without losing audit truth

Risk: L1

Depends-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: Keep regression protection and final delivery proof without allowing repeated successful profile runs or separate review notes to make long-lived repositories increasingly noisy.
- Current behavior and evidence: A real UI slice produced a 34,681-byte, 573-line evidence file; 18,627 compact bytes came from 15 check records, where the same five full-profile checks were appended three times. The paired API/UI task added about 220 useful regression-test lines and about 53 KiB of machine JSON. Tests remain valuable, while repeated successful check records and a separate 13-line review Markdown are avoidable archive noise.
- Business and architecture path: Preserve all evidence while a task is active. On a normally completed archive, compact only `checkRuns`: retain the latest record for each `(profile, checkId)` and the latest earlier failure when it differs, then write a machine summary of total, retained, omitted, pass and failure counts. Keep RED/GREEN, verifications, acceptance, artifacts, practice, closure and non-completed histories unchanged. Guide Codex to store ordinary review facts directly in structured evidence and create an external report only when independently inspectable findings require one.
- Invariants and source of truth: Regression tests are durable product assets and are never removed by evidence retention. Compaction must not change gate decisions before archive, must not fabricate or erase a failure summary, must preserve the final full-profile record, and must not alter abandoned or reconciled evidence. Existing schema-v4 files remain readable; the new summary is additive.
- Requirement/design/API version: RigorBreeze v0.10.3 Public Preview; evidence/state schema remains v4 and automation journal remains v1.
- Unresolved outcome-changing ambiguity: none; the user explicitly approved optimizing RigorBreeze and committing the result.

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
- rigorbreeze/scripts/flow_state.py
- rigorbreeze/scripts/tests/test_flow_v4.py
- rigorbreeze/scripts/tests/test_skill_contract.py
- spec/changes/RB-EVIDENCE-RETENTION-0103.md
- spec/evidence/RB-EVIDENCE-RETENTION-0103.json
- spec/archive/RB-EVIDENCE-RETENTION-0103.md

## Forbidden scope
- Business repositories, their regression tests, existing archived evidence and Git history
- New public commands, new Spec file types, third-party dependencies or telemetry
- Automatic deletion of tests, task contracts, evidence, branches, reports or worktrees
- Evidence compaction before normal completed archive

## Acceptance criteria
- REQ-001: A normally completed archive with repeated successful checks retains one latest record per `(profile, checkId)` and records accurate total, retained and omitted counts.
- REQ-002: When a check previously failed and later passed, the archive retains both the latest failure and latest final record and summarizes pass/failure counts without full-log duplication.
- REQ-003: Abandoned and reconciled archives preserve their complete `checkRuns` history and do not claim compaction.
- REQ-004: Current verification, TDD chains, acceptance, artifacts, practice and closure semantics remain unchanged, and existing schema-v4 evidence without a retention summary remains compatible.
- REQ-005: Skill and bilingual documentation state that regression tests remain durable, ordinary review facts should live in structured evidence, raw/transient reports should use ignored or time-limited artifact storage, and completed evidence is compacted rather than deleted.
- REQ-006: Version surfaces consistently report v0.10.3 without changing schema v4, public CLI or Spec Tree.

## Test seams
- Seam: `command_archive` operating on synthetic schema-v4 task evidence through the public CLI, plus Skill contract/version tests.
- Independent oracle: inspect the archived JSON and assert retained record identities, aggregate counts, untouched non-check sections and outcome-specific behavior independently of the compaction implementation.

## Verification commands
- `python3 -B -m unittest rigorbreeze.scripts.tests.test_flow_v4 -v`
- `python3 -B -m unittest discover -s rigorbreeze/scripts/tests -v`
- `python3 -B -m unittest discover -s tests/behavior -v`
- `python3 -m ruff format --check rigorbreeze/scripts tests/behavior`
- `python3 -m ruff check rigorbreeze/scripts tests/behavior`
- `python3 -m py_compile rigorbreeze/scripts/flow.py rigorbreeze/scripts/flow_state.py`
- `python3 rigorbreeze/scripts/flow.py --root . verify --profile full --mode enforced`
- `git diff --check`

## Conditional risks
- Runtime/UI: N/A - workflow evidence retention only
- Security/migration/release: N/A - no credential, migration, provider or release behavior changes
- Stop conditions: any need to delete regression tests, change pre-archive gates, alter schema version, or introduce a second evidence store

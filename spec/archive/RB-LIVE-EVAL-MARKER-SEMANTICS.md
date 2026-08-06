# RB-LIVE-EVAL-MARKER-SEMANTICS: Distinguish partial product delivery from incomplete workflow closure

Risk: L1

Depends-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: finish the v0.9.2 publication only after the live Agent behavior gate measures real requirement coverage without false failures.
- Current behavior and evidence: `context-semantics` repetition 2 implemented REQ-001 through REQ-005 and passed all three product tests, but its final result selected `partial-request-implemented` because the synthetic project had no configured full-profile commands. The evaluator therefore rejected complete product behavior for incomplete workflow closure.
- Business and architecture path: clarify the existing live prompt's marker contract and protect it with the existing deterministic behavior-suite test; do not change the scorer, Skill rules, scenario requirements, sandbox, timeout, or public workflow.
- Invariants and source of truth: a forbidden marker remains a hard failure. `partial-request-implemented` means at least one declared user-visible requirement atom was omitted, not that optional or unavailable project workflow evidence remains open. The final acceptance atoms and fresh product verification remain authoritative.
- Requirement/design/API version: RigorBreeze v0.9.2 Public Preview behavior contract on main `0ad9e5a`; no CLI, Schema, Spec Tree, or runtime API change.
- Unresolved outcome-changing ambiguity: none.

## Allowed scope
- tests/behavior/run.py
- tests/behavior/test_behavior.py
- CHANGELOG.md
- CHANGELOG.zh-CN.md
- spec/changes/RB-LIVE-EVAL-MARKER-SEMANTICS.md
- spec/evidence/RB-LIVE-EVAL-MARKER-SEMANTICS.json

## Forbidden scope
- RigorBreeze Skill and runner behavior, public CLI, schemas, scenario scoring rules, sandbox authority, release threshold, README, CI, dependencies, and unrelated tests.

## Acceptance criteria
- REQ-001: the live prompt defines `partial-request-implemented` as omission of one or more declared user-visible requirement atoms.
- REQ-002: the live prompt explicitly says incomplete workflow/profile closure alone does not qualify when all product atoms are implemented and freshly verified.
- REQ-003: the existing exact case ID and ambiguous-negation marker guidance remain intact, while actual partial product delivery continues to be a forbidden scored marker.

## Test seams
- Seam: call the behavior harness's `_live_prompt` helper and inspect the generated evaluator contract.
- Independent oracle: explicit product-atom versus workflow-closure language, without invoking the model or copying implementation logic into the assertion.

## Verification commands
- python3 -B tests/behavior/test_behavior.py BehaviorSuiteTests.test_live_prompt_names_the_exact_result_case_id -v
- python3 scripts/rigorbreeze.py --root . verify --profile full

## Conditional risks
- Runtime/UI: evaluator wording only; verify it does not instruct the Agent to hide genuine partial delivery.
- Security/migration/release: no sandbox, Git, release, or product runtime change.
- Stop conditions: any need to change the scorer, scenario requirements, Skill behavior, or public workflow.

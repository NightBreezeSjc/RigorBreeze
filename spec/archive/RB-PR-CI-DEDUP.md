# RB-PR-CI-DEDUP: Run one CI matrix for each pull request update

Risk: L0

Depends-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: make the new pull-request workflow mature without paying for duplicate CI matrices.
- Current behavior and evidence: PR #1 started one matrix for the branch push and another for the pull_request event because `push` currently matches every branch.
- Business and architecture path: GitHub Actions trigger configuration only; jobs, platforms, Python versions, and required check names remain unchanged.
- Invariants and source of truth: pull requests run the complete matrix once; main runs it once again after integration; required checks keep their existing names.
- Requirement/design/API version: GitHub Actions event filtering as of 2026-08-06.
- Unresolved outcome-changing ambiguity: none.

## Allowed scope
- .github/workflows/ci.yml
- README.md
- README.zh-CN.md
- CONTRIBUTING.md
- CONTRIBUTING.zh-CN.md
- spec/archive/RB-OPEN-SOURCE-GOVERNANCE.md
- spec/evidence/RB-OPEN-SOURCE-GOVERNANCE.json
- spec/changes/RB-PR-CI-DEDUP.md
- spec/evidence/RB-PR-CI-DEDUP.json

## Forbidden scope
- rigorbreeze/**
- scripts/**
- tests/**

## Acceptance criteria
- REQ-001: A pull request branch update starts the Skill CI workflow only through pull_request, while integration into main still starts it through push.
- REQ-002: Existing job names, matrix coverage, permissions, and commands remain unchanged so main protection continues to recognize all seven required checks.

## Test seams
- Seam: GitHub Actions event filter.
- Independent oracle: YAML source inspection plus the next PR synchronize event and GitHub check-run list.

## Verification commands
- python3 -B rigorbreeze/scripts/tests/test_skill_contract.py
- git diff --check
- gh pr checks 1 --repo NightBreezeSjc/RigorBreeze

## Conditional risks
- Runtime/UI: N/A unless applicable
- Security/migration/release: N/A unless applicable
- Stop conditions: any job-name or matrix change that would invalidate required checks.

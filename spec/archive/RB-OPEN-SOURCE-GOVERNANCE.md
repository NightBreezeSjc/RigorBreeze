# RB-OPEN-SOURCE-GOVERNANCE: Make the public contribution flow clear and protected

Risk: L0

Depends-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: adopt a mature open-source branch workflow and make the public README easier for contributors to follow.
- Current behavior and evidence: the GitHub repository has only an unprotected main branch; the bilingual README explains the product but not the repository workflow.
- Business and architecture path: repository-facing documentation and GitHub repository settings only; the installable Skill and runtime behavior remain unchanged.
- Invariants and source of truth: main remains the only long-lived branch; each unrelated change uses one short-lived branch and pull request; CI and maintainer merge authority protect integration.
- Requirement/design/API version: GitHub Flow and GitHub protected-branch guidance as of 2026-08-06.
- Unresolved outcome-changing ambiguity: none; avoid Git Flow because permanent develop/hotfix/release branches add overhead without a current integration need.

## Allowed scope
- README.md
- README.zh-CN.md
- CONTRIBUTING.md
- CONTRIBUTING.zh-CN.md
- spec/changes/RB-OPEN-SOURCE-GOVERNANCE.md
- spec/evidence/RB-OPEN-SOURCE-GOVERNANCE.json

## Forbidden scope
- rigorbreeze/**
- scripts/**
- tests/**
- CHANGELOG.md
- CHANGELOG.zh-CN.md

## Acceptance criteria
- REQ-001: The English and Chinese README explain the same lightweight GitHub Flow, branch prefixes, PR target, CI expectation, maintainer decision, and post-merge cleanup.
- REQ-002: The English and Chinese contribution guides provide copyable branch commands and define one outcome per branch and pull request.
- REQ-003: The documentation explicitly explains why the project does not keep permanent develop, hotfix, or empty release branches.
- REQ-004: GitHub main rejects force-push and deletion, required CI protects integration, merged topic branches are deleted automatically, and merge methods favor a readable history.

## Test seams
- Seam: repository documentation contracts and GitHub repository settings.
- Independent oracle: Markdown link/Skill contract tests plus GitHub API inspection of branches, merge methods, and main protection.

## Verification commands
- python3 -B tests/test_skill_contract.py
- python3 -B -m unittest discover -s tests/behavior -v
- git diff --check
- gh api repos/NightBreezeSjc/RigorBreeze/branches/main/protection

## Conditional risks
- Runtime/UI: N/A unless applicable
- Security/migration/release: N/A unless applicable
- Stop conditions: any proposal to add a permanent branch without a demonstrated release or integration need.

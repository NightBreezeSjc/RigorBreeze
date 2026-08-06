# RB-LEAN-IMPLEMENTATION-GUARDRAILS: Adopt evidence-based lean implementation guardrails

Risk: L1

Depends-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User outcome: Absorb the useful parts of a widely shared eight-rule AGENTS.md article into RigorBreeze without importing its unsafe side-project compatibility rule or bloating the Skill.
- Current behavior and evidence: RigorBreeze already requires tracer bullets, minimum GREEN, simplicity review, YAGNI, and no speculative abstraction, but it does not explicitly require checking the standard library/framework/current dependency set before adding code or packages. The first-party source located is vercel/eve's AGENTS.md; its breaking-change rule is explicitly scoped to pre-1.0 eve, while the article's Next.js/60B-token attribution is not independently verified.
- Business and architecture path: Tighten the existing implementation protocol and bilingual handbook, then protect the concise behavior contract with the existing Skill contract test. Record the change under Unreleased rather than adding a command, schema field, document type, or dependency.
- Invariants and source of truth: The repository and official Vercel source are authoritative. Production APIs, persisted data, upgrade paths, and migrations retain RigorBreeze's evidence, compatibility, rehearsal, and rollback controls. SKILL.md remains at most 150 lines.
- Requirement/design/API version: RigorBreeze v0.9.2 Public Preview, schema v4, automation journal v1; policy clarification remains Unreleased.
- Unresolved outcome-changing ambiguity: none; the user explicitly approved the previously summarized minimal adoption after the prior closure commit.

## Allowed scope
- rigorbreeze/SKILL.md
- rigorbreeze/references/handbook.md
- rigorbreeze/references/handbook.zh-CN.md
- rigorbreeze/scripts/tests/test_skill_contract.py
- CHANGELOG.md
- CHANGELOG.zh-CN.md
- Skill演进与实践记录.md
- spec/changes/RB-LEAN-IMPLEMENTATION-GUARDRAILS.md
- spec/evidence/RB-LEAN-IMPLEMENTATION-GUARDRAILS.json

## Forbidden scope
- Public CLI, state/evidence schema, automation journal, Spec Tree, risk lanes, Git authority, CI profiles, runtime dependencies, and existing project files outside this repository.
- Any unconditional instruction to delete compatibility code, skip migrations, or break production data/API contracts.
- Any claim that the unverified Next.js-team or 60B-token attribution is established fact.

## Acceptance criteria
- REQ-001: Before adding a custom mechanism or dependency, the Skill explicitly requires inspection of the standard library, framework, and current dependency set.
- REQ-002: A new dependency, abstraction, helper, or configuration layer must be justified by current acceptance or a durable invariant; implementation starts with the smallest working vertical path and extracts boundaries only for independent change or safety.
- REQ-003: Compatibility is risk-adaptive: code with no declared compatibility promise may remove proven-dead paths, while public APIs, persisted data, upgrade paths, and production migrations require an explicit transition, verification, and rollback strategy.
- REQ-004: The bilingual handbook explains why the viral rule is not a production default, and the maintainer record distinguishes verified first-party evidence from unverified attribution.
- REQ-005: Existing Skill contract tests enforce the new rules while SKILL.md remains at most 150 lines and no public interface expands.

## Test seams
- Seam: Installable SKILL.md plus bilingual handbook and repository-level Skill contract test.
- Independent oracle: First-party vercel/eve AGENTS.md scope, exact phrase assertions in test_skill_contract.py, line-count constraint, and the existing full verification profile.

## Verification commands
- python3 -B -m unittest rigorbreeze.scripts.tests.test_skill_contract -v
- python3 rigorbreeze/scripts/flow.py --root . verify --profile full
- python3 /Users/songjincheng/.codex/skills/.system/skill-creator/scripts/quick_validate.py rigorbreeze
- git diff --check

## Conditional risks
- Runtime/UI: N/A unless applicable
- Security/migration/release: Do not weaken existing compatibility, migration, dependency, license, SBOM, or rollback gates.
- Stop conditions: A rule requires a new CLI/schema surface, duplicates an existing protocol, exceeds the 150-line Skill limit, or treats an unverified social-media attribution as fact.

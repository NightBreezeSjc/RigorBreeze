---
name: codex-production-flow
description: Initialize and operate an auditable, production-grade development workflow for Codex projects using one active task spec, approval digests, observed RED-GREEN-REFACTOR evidence, runtime and review attestations, Git gates, release checks, and a minimal spec tree. Use when Codex needs to initialize a repository workflow, take over an existing project, create or resume a change, implement features or fixes under SDD/TDD, prepare CI gates, verify release readiness, or archive completed work across sessions.
---

# Codex Production Flow

Turn requirements, design, implementation, tests, runtime acceptance, and release evidence into one traceable delivery loop. Keep one human-authored Markdown file per active task; keep state and evidence machine-generated.

## Start every task

1. Resolve the target project root.
2. Run `python <skill-dir>/scripts/flow.py --root <project> status`.
3. If uninitialized, run `init`, then run `doctor`.
4. Read `spec/index.md`, `spec/state.json`, and the active `spec/changes/<TASK-ID>.md` when present.
5. Read only the authoritative requirement, design, API, data, security, and operations sources linked by the task.
6. Read [handbook.md](references/handbook.md) before initializing a project, changing workflow policy, or handling L2/Emergency work.

Do not use conversation memory as the source of truth. Do not create parallel planning documents that repeat the active task.

## Choose the risk lane

- `L0`: documentation, non-behavioral copy, isolated visual adjustment.
- `L1`: normal feature, fix, or end-to-end user flow.
- `L2`: permissions, sensitive data, migrations, payments, external integration, architecture, or production release.
- `Emergency`: smallest safe production hotfix, followed by evidence completion and incident review.

Escalate immediately when scope expands. Never downgrade risk merely to bypass a gate.

## Run the workflow

### 1. Establish the baseline

For an existing project, inspect the current build, public behavior, interfaces, permissions, data boundaries, tests, known failures, secrets/configuration, deployment, and debt before changing behavior. Record facts in existing authoritative sources or the active task; do not generate a baseline document pack.

### 2. Create one change

Run:

```bash
python scripts/codex-flow.py new TASK-001 --title "Observable user outcome" --risk L1
```

Complete `spec/changes/TASK-001.md`. Link sources by path, URL, version, section, or image; do not copy entire documents. Define allowed scope, forbidden scope, verifiable acceptance IDs, exact commands, runtime evidence, migration/rollback, release controls, and stop conditions.

### 3. Freeze the contract

Ask the user to approve the task when product scope, design, acceptance criteria, plan, and test shape are stable. Only then run:

```bash
python scripts/codex-flow.py approve task
```

The digest is the contract. Any task change invalidates approval, RED, verification, and attestations. Record dependency or migration approval separately:

```bash
python scripts/codex-flow.py approve dependency --name package-or-lockfile
python scripts/codex-flow.py approve migration --name migration-set
```

### 4. Prove RED before implementation

Write the smallest behavior test first. Run it through the gate with a pattern that proves the expected failure:

```bash
python scripts/codex-flow.py red \
  --requirement REQ-001 \
  --expect-pattern "expected missing behavior" \
  -- python -m pytest tests/test_feature.py -q
```

A passing test, import failure, tool failure, unrelated historical failure, or unmatched output is not RED. Run `check implement` before writing business implementation.

### 5. Implement the minimum and verify

Implement only the approved slice. Reach GREEN, refactor only while green, then run the narrow and affected suites. Record a fresh verification:

```bash
python scripts/codex-flow.py verify --scope affected -- <project verification command>
```

The verification fingerprint binds the approved task, project content, command, exit code, Git HEAD, and timestamp. Any project change makes it stale.

### 6. Validate the real product

Follow the acceptance dimensions in [handbook.md](references/handbook.md): function, design, integration, security/privacy, migration, and release operations. For UI work, use real runtime screenshots and visual comparison. For mini-app work, include developer-tool automation and real-device evidence. AI cannot approve its own visual baseline, security exception, legal conclusion, or production release.

Record evidence references only after inspecting the underlying artifact:

```bash
python scripts/codex-flow.py attest runtime --evidence artifacts/runtime/TASK-001.png
python scripts/codex-flow.py attest review --evidence "independent review result or URL"
```

L2 additionally requires `security`, `migration`, and `second-human`; Emergency requires `incident`.

### 7. Pass Git and release gates

Stage intended files, then run:

```bash
python scripts/codex-flow.py check commit
python scripts/codex-flow.py check release
python scripts/codex-flow.py archive
```

The commit gate blocks secret paths, secret-like staged content, unapproved dependency manifests, unapproved migrations, and stale verification. Archive moves the task to `spec/archive/`; it never copies the task.

Push, MR/PR creation, merge, tags, releases, branch deletion, and force push are separate external actions. Obtain explicit authorization for each.

## CI integration

Use the same repository-owned `scripts/codex-flow.py` locally and in CI. Never reimplement policy only in YAML. Read [ci-gates.md](references/ci-gates.md) and adapt the templates under `assets/ci/` to the project stack.

CI must run static/type checks, unit/integration/E2E, interface/permission contracts, secret and dependency scanning, SBOM/license checks, migration rehearsal, production build, artifact digesting, and release checks appropriate to risk. Test, UAT, and deployment must point to the same Git SHA and artifact.

## Spec tree contract

Read [spec-tree.md](references/spec-tree.md) before changing the tree, state schema, digest rules, or archive behavior. Keep these invariants:

- one active task;
- one human-authored Markdown per task;
- state and evidence are generated JSON;
- approval and evidence become invalid after relevant content changes;
- archive moves rather than copies;
- authoritative requirements and designs stay at their source;
- state can be reconstructed from the task, Git, and evidence.

## Completion rule

Do not say complete because code exists or tests passed once. Completion requires the risk-appropriate `check release`, current runtime/review evidence, a closed traceability chain, documented remaining risks, and fresh verification output.


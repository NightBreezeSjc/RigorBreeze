# Minimal Spec Tree Contract

## Contents

1. Purpose
2. Tree
3. Authority and lifecycle
4. State and evidence
5. Invalidation
6. Extension rules

## Purpose

The tree preserves cross-session state and auditability without copying the same requirement into proposal, design, plan, test-plan, and verification documents. Each change has one human-authored task file.

## Tree

```text
spec/
├── index.md
├── state.json
├── changes/
│   └── TASK-001.md
├── evidence/
│   └── TASK-001.json
└── archive/
    └── TASK-000.md
```

- `index.md`: authority order and navigation only.
- `state.json`: current phase, active task, approvals, latest RED/verification, attestations, and last close.
- `changes/<TASK-ID>.md`: the only human-authored change contract.
- `evidence/<TASK-ID>.json`: commands, exit codes, summaries, fingerprints, Git HEAD, and evidence references.
- `archive/<TASK-ID>.md`: the same task moved after release readiness; never a duplicate.

## Authority and lifecycle

Authority order:

```text
approved business/design source
→ active task contract
→ API/data/security/operations contract
→ tests and runtime evidence
→ code and artifact
→ archive history
```

Lifecycle:

```text
baseline → drafting → approved → red → implementing → green → refactoring
→ verifying → runtime acceptance → review → ready to release → observing → closed
```

Only one task may be active. Finish, archive, or explicitly abandon it before creating another. Parallel work requires separate worktrees and a future multi-task extension with conflict controls; do not silently weaken the invariant.

## State and evidence

`state.json` is a machine cache and gate input, not a product requirement source. It must remain replaceable from the task, Git, and evidence. Do not manually edit it to bypass a gate.

Evidence JSON may store:

- requirement ID;
- exact argument-vector command, not a shell string;
- exit code and redacted output summary;
- task digest and project fingerprint;
- Git HEAD and timestamp;
- runtime, review, security, migration, second-human, and incident evidence references.

Do not store credentials, production data, full logs containing personal data, or unverifiable claims.

## Invalidation

Changing the approved task invalidates task approval and all downstream evidence. Changing project content after verification invalidates verification and attestations. Evidence is current only when both the task digest and project fingerprint match.

Dependency and migration approvals are explicit because they change supply-chain and data risk. They do not replace vulnerability scanning, license checks, migration rehearsal, backup, restore, or rollback evidence.

## Extension rules

Add a field or file only when two real vertical slices demonstrate a repeated need. Prefer generated JSON or CI artifacts over another human document. Never add a new source of truth merely to make the tree look comprehensive.


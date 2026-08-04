# Minimal Spec Tree Contract

English · [简体中文](spec-tree.zh-CN.md)

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
├── changes/
│   └── TASK-001.md
├── evidence/
│   └── TASK-001.json
└── archive/
    └── TASK-000.md

rigorbreeze.toml
scripts/rigorbreeze.py
scripts/flow_state.py
scripts/flow_policy.py
scripts/flow_parallel.py
scripts/flow_automation.py

.git/rigorbreeze/registry.json                 # primary/common, not committed
.git/rigorbreeze/automation.json               # external-action journal
.git/worktrees/<name>/rigorbreeze/state.json   # linked-worktree private
```

- `index.md`: authority order and navigation only.
- Git-private `state.json`: schema-v4 phase, active task, approvals, latest
  RED/verification, warnings, and last close. Existing primary-worktree
  `spec/state.json` remains readable during compatibility migration.
- `changes/<TASK-ID>.md`: the only human-authored change contract.
- `evidence/<TASK-ID>.json`: baseline, check runs, TDD chain, verification,
  artifact digests, acceptance, release, and the prefilled practice summary.
- `archive/<TASK-ID>.md`: the same task moved after its risk-appropriate close gate; never a duplicate.
- `rigorbreeze.toml`: standard checks, profiles, commands, reports, artifacts,
  timeouts, and risk applicability.
- `scripts/rigorbreeze.py`: the stable project entry used locally and in CI.
- `scripts/flow_state.py`: configuration, templates, schema upgrades, state/evidence, digests, and atomic I/O.
- `scripts/flow_policy.py`: task contract, scope, TDD, freshness, risk, and delivery gates.
- Git-common `registry.json`: disposable cross-worktree index. It is rebuilt
  from worktrees and private state, never a requirement or evidence source.
- Git-common `automation.json`: private commit/push/provider action journal,
  keyed by immutable inputs. It records standing versus one-time authorization,
  supports recovery and idempotency, and never rewrites tracked task evidence
  after an external action.

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
draft → approved → red → implementing → verified → accepted
→ archived

accepted → release-ready → protected release gate
```

Completed and abandoned tasks both move the same contract to `archive/`; `closure.outcome` distinguishes success from cancellation without inventing verification. `release-ready` is an optional production-release branch, not a prerequisite
for closing every task.

Only one task may be active in one worktree. One project may have many active
worktrees. Every writing task uses its own `rigorbreeze/<task-id>` branch and linked
worktree; two writing windows never share one physical worktree.

`Depends-On` in each task contract is the only DAG representation. Independent
tasks have `Depends-On: none`. The runner derives topological order, cycles,
missing dependencies, readiness, and scope conflicts; no second DAG document
or task database is introduced.

## State and evidence

Private `state.json` and the common registry are machine caches and gate inputs,
not product requirement sources. Do not commit linked-worktree state or edit it
to bypass a gate. `doctor --all --repair` may rebuild the registry explicitly.

`status --json` includes `installation` and `scope` projections. Installation
compares the bundled Skill with the project runner and reports `current`,
`outdated`, `missing`, or `unmanaged` plus upgrade safety. Scope is `current`,
`violated`, or `not-applicable`, and evaluates committed changes from the
approval baseline through `HEAD` together with current working-tree changes.

`status --all --json` also includes runtime claims/conflicts and a `cleanup` projection. It lists
managed integrated worktrees that are removable, entries retained with a safety
reason, unregistered Git worktrees, and local task branches preserved by policy.
This is advisory state derived from Git and the registry, not another task or
evidence source.

Evidence JSON may store:

- requirement ID;
- exact argument-vector command, not a shell string;
- exit code and redacted output summary;
- task digest and project fingerprint;
- Git HEAD and timestamp;
- runtime, review, security, migration, second-human, and incident evidence references.

Stable schema-v4 sections are `baseline`, `checkRuns`, `tddChain`,
`artifacts`, `acceptance`, `release`, `automation`, `practice`, `red`, and
`verifications`, plus `closure` for completed or abandoned outcomes. Release
may contain validated `operation-plan` and `operation-result` snapshots;
practice may contain deduplicated machine events. Existing evidence `automation` entries remain readable, but
new external-action outcomes are written only to the Git-private journal.
The practice confirmation sets `evolutionCandidate` only for negative workflow
signals; review candidates from this evidence instead of creating another log.
Legacy attestations remain readable during schema upgrade but are not part of
the current command surface. Reading schema v1/v2/v3 upgrades it without deleting
RED, verification, acceptance, release, or practice history.

Do not store credentials, production data, full logs containing personal data, or unverifiable claims.

## Invalidation

Changing the approved task invalidates task approval and all downstream
evidence. Changing source, tests, dependency files, configuration, migrations,
or `rigorbreeze.toml` invalidates verification, acceptance, artifacts, and
release evidence. Generated state, evidence, configured reports, and configured
artifacts are excluded from the source fingerprint so proof does not invalidate
itself. Evidence is current only when task digest, project fingerprint, and
configuration digest match as applicable.

After production implementation changes, the contract cannot be reapproved to
create a new baseline. Restore the approved contract and finish, or revert the
production changes before amending and reapproving the same observable outcome.
A new user outcome or acceptance condition becomes a dependent task. Every
current RED chain must retain its test digest and bind GREEN to the current full
verification before merge or archive.

Scope globs are path-aware: `*` does not cross `/`, while a complete `**` path
segment matches zero or more directories. Task contracts and corresponding
machine evidence are task-owned; policy, configuration, runner, and unrelated
Spec files require explicit scope.

The approved baseline branch SHA is also part of freshness. When another task
changes the baseline, affected active tasks must incorporate that baseline and
rerun affected/full plus applicable acceptance. A registry update alone never
invalidates evidence; the changed Git baseline does.

Dependency and migration approvals are explicit because they change supply-chain and data risk. They do not replace vulnerability scanning, license checks, migration rehearsal, backup, restore, or rollback evidence.

## Extension rules

Add a field or file only when real vertical slices demonstrate a repeated need. Prefer generated JSON or CI artifacts over another human document. Never add a new source of truth merely to make the tree look comprehensive. Checks absent from a project profile need no N/A record.

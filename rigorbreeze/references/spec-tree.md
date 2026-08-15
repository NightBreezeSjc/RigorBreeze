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

The record model preserves cross-session state and risk-appropriate auditability without copying requirements across documents. Direct changes create no task record. Task-based changes have one contract and one evidence record, private by default in schema v5.

## Tree

```text
spec/
├── index.md
├── evidence/
│   └── TASK-002.audit.json   # optional sanitized L2/Emergency summary
└── archive/                  # legacy tracked mode only

rigorbreeze.toml
scripts/rigorbreeze.py
scripts/flow_state.py
scripts/flow_policy.py
scripts/flow_parallel.py
scripts/flow_automation.py

.git/rigorbreeze/registry.json                 # primary/common, not committed
.git/rigorbreeze/automation.json               # external-action journal
.git/rigorbreeze/state.json                    # primary-worktree private state
.git/rigorbreeze/records/{changes,evidence,archive,history}/
.git/worktrees/<name>/rigorbreeze/state.json   # linked-worktree private
```

- `index.md`: authority order and navigation only.
- Git-private `state.json`: schema-v5 phase, active task, approvals, latest
  RED/verification, warnings, and last close for both primary and linked
  worktrees. Existing `spec/state.json` is copied on first read; `init` or
  explicit repair removes it only when it is untracked and identical. A tracked
  or divergent legacy file is retained and reported.
- private `records/changes/<TASK-ID>.md`: the only human-authored change contract. New contracts
  carry compact `Task-Origin` and `Waiting-On` lines; they are lifecycle facts,
  not another planning document or evidence schema.
- private `records/evidence/<TASK-ID>.json`: baseline, check runs, TDD chain, verification,
  artifact digests, acceptance, release, and the prefilled practice summary.
- private `records/archive/<TASK-ID>.md`: the same task moved after its risk-appropriate close gate; never a duplicate.
- private `records/history/<TASK-ID>.json`: a path-free compact L1 history after proven integration.
- tracked `spec/evidence/<TASK-ID>.audit.json`: optional sanitized L2/Emergency audit proof, capped at 32 KiB. It excludes absolute paths, raw output, credentials, and production data.
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
  after an external action. Version 2-4 projects retain tracked paths until an
  explicit idle, clean `doctor --all --repair --migrate-records private`.

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

Completed, abandoned, and reconciled tasks move the same contract to `archive/`; `closure.outcome` distinguishes success, cancellation, and an externally integrated historical close without inventing verification. A normal close preserves a read-only `lastClosed` snapshot for guarded commit/push/merge after archive. `release-ready` is an optional production-release branch, not a prerequisite
for closing every task.

Only one task may be active in one worktree. One project may have many active
worktrees. Every writing task uses its own `rigorbreeze/<task-id>` branch and linked
worktree; two writing windows never share one physical worktree.

`Depends-On` in each task contract is the only DAG representation. Independent
tasks have `Depends-On: none`. The runner derives topological order, cycles,
missing dependencies, readiness, and scope conflicts; no second DAG document
or task database is introduced.

## State and evidence

Private `state.json`, records, and the common registry are machine gate inputs,
not product requirement sources. Do not commit linked-worktree state or edit it
to bypass a gate. `doctor --all --repair` may rebuild the registry explicitly.

`status --json` includes `installation`, `workflowBaseline`, `workflowBypass`, lifecycle, `scope`, compact `evolution`, and `interaction` projections. The text view is limited to completed, current, and the one genuine user action; `actor=codex` work stays internal. Installation
compares the bundled Skill with the project runner and reports `current`,
`outdated`, `missing`, or `unmanaged`, missing/modified components, and upgrade safety. `workflowBaseline` proves managed files on the real base branch and reports `current`, `missing`, `partial`, `modified`, or `blocked`. Lifecycle prioritizes `integrated-unclosed` and `closure-pending` over stale-baseline advice. Scope is `current`,
`violated`, or `not-applicable`, and evaluates committed changes from the
approval baseline through `HEAD` together with current working-tree changes.
`workflowBypass` is `detected` only when an active unapproved task already has
non-workflow delivery changes. That observation records one deduplicated
practice event as an immediate evolution candidate; it never creates approval,
RED, GREEN, acceptance, or a replacement baseline.

If an active contract is missing, current and aggregate status project
`lifecycle=orphaned-record`, block readiness, and identify the exact contract to
restore. Existing evidence candidates are summarized by task ID with the
copyable `$rigorbreeze 汇总这个项目的演进候选` instruction; status never mutates
that evidence while projecting the reminder.

`status --all --compact --json` is the normal machine handoff for parallel work. It keeps active task ownership, dependencies, blockers, next actions, and aggregate cleanup counts while omitting closed-task detail. The complete `status --all --json` also includes runtime claims/conflicts and a detailed `cleanup` projection. It lists
managed integrated worktrees that are removable, entries retained with a safety
reason, unregistered Git worktrees, and local task branches preserved by policy.
Candidates include cleanliness, integration proof, expected HEAD, and whether one-time confirmation is required. Unmanaged removal never deletes its branch.
This is advisory state derived from Git and the registry, not another task or
evidence source.
The compatible `tasks` list remains available, while `worktrees` groups those
records by physical path and reports the executing bundled runner separately
from each project's installed runner. Cleanup candidates likewise appear once
per physical path with all related `taskIds`.

Evidence JSON may store:

- requirement ID;
- exact argument-vector command, not a shell string;
- exit code and redacted output summary;
- task digest and project fingerprint;
- Git HEAD and timestamp;
- runtime, review, security, migration, second-human, and incident evidence references.

Within one profile invocation, `checkRuns[*].reusedFromCheckId` may identify the earlier check whose identical process result was reused. It is execution provenance only: the later check retains its own pass/fail, report, artifacts, category, and timestamp. Its absence preserves compatibility with existing schema-v4 evidence.

On a normally completed archive, repeated details are compacted without changing gate truth. Check runs keep the latest record for each `(profile, checkId)`, the latest earlier failure when present, and aggregate counts in optional `checkRunSummary`. TDD keeps the final valid GREEN chain and the latest useful earlier failed or invalidated chain for each acceptance ID, with aggregate counts in optional `tddSummary`; duplicated top-level RED detail is reduced to the fields required to prove the final chain. Profile-level `verifications`, acceptance, artifacts, practice, and closure remain unchanged. Active, abandoned, and reconciled histories are never compacted. Evidence created before either summary field remains valid.

The repository keeps regression tests, one compact task contract, and its compact evidence as versioned engineering records. Raw logs, generated reports, caches, and behavior-evaluation transcripts stay ignored or in CI/Git-private artifacts. The distributable Skill archive excludes maintainer tests and caches, but the source repository does not delete them. A second local-only evidence store is intentionally deferred: it would create another authority, migration path, and cleanup policy before repeated real use proves that cost worthwhile.

Stable schema-v4 sections are `baseline`, `checkRuns`, `tddChain`,
`artifacts`, `acceptance`, `release`, `automation`, `practice`, `red`, and
`verifications`, plus `closure` for completed, abandoned, or reconciled outcomes. Release
may contain validated `operation-plan` and `operation-result` snapshots;
practice may contain deduplicated machine events. Existing evidence `automation` entries remain readable, but
new external-action outcomes are written only to the Git-private journal.
The practice confirmation sets `evolutionCandidate` only for negative workflow
signals; review candidates from this evidence instead of creating another log.
Legacy attestations remain readable during schema upgrade but are not part of
the current command surface. Reading schema v1/v2/v3 upgrades it without deleting
RED, verification, acceptance, release, or practice history.

When an approved acceptance result is unchanged but its test is strengthened
after implementation begins, a new RED may contain `baselineReplay`. The runner
creates a temporary detached worktree at the recorded approval SHA, overlays
only current Allowed-Scope test files, and reruns the same RED command. The
field binds the replay SHA, previous RED time, and current test digests. It never
permits production, dependency, configuration, or migration overlays.

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

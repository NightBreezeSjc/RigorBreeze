# Changelog

English · [简体中文](CHANGELOG.zh-CN.md)

All notable changes to RigorBreeze will be documented in this file.

The project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). During Public Preview, minor releases may change workflow interfaces when real-project evidence shows that the current contract is unsafe or unnecessarily costly.

## [Unreleased]

### Changed

- Renamed the project, Skill ID, invocation, runner, configuration, Git-private state, and task-branch prefix from Codex Production Flow to RigorBreeze before the first public release. No legacy alias is retained.

### Documentation

- Reframed the repository for first-time adopters with bilingual onboarding, explicit safety boundaries, and a complete first-task walkthrough.
- Added concise contribution and security policies plus an MIT license.

## [0.7.0] - Real-delivery closure

### Added

- Project installation status reports the bundled Skill version, project runner version, drift state, and whether an upgrade is safe; active implementation tasks prevent silent runner replacement.
- `archive --outcome abandoned --reason ...` safely closes cancelled or superseded tasks without inventing successful verification and without deleting branches, worktrees, or commits.
- Task contracts can declare exclusive ports, processes, services, applications, and environments through `Runtime-Claims`; conflicts are enforced across active worktrees.
- L2 conditional integrations bind enabled, disabled, and dependency-unavailable behavior to acceptance IDs through `Operational-Modes`.
- Machine JSON `operation-plan` and `operation-result` release evidence records ordered stages, stop conditions, safe recovery state, and a single resume action.
- Runner drift, occupied task slots, runtime conflicts, missing release plans, and gate failures are deduplicated into task-local practice events for the existing retrospective.

### Changed

- Evidence and state schema advance from v3 to v4 while retaining historical RED, verification, acceptance, release, automation, and practice records.
- Enforced L1/L2 approval requires the runner, configuration, helper modules, and Spec index to exist in the Git baseline.
- The Skill protocol requires a bundled-runner status check, an approved task contract, and a successful window claim before product-code writes.

### Safety

- RigorBreeze does not kill processes, seize ports, overwrite an active task's runner, delete abandoned-task Git references, or turn operation snapshots into a resident deployment engine.

## [0.6.1] - Bounded worktree lifecycle

### Changed

- Recognize a task as integrated when every task commit since its recorded baseline has a patch-equivalent commit on the baseline branch, covering safe cherry-pick flows without treating partial integration as complete.
- Add a backward-compatible `cleanup` projection to `status --all --json`, separating removable, retained, and unregistered worktrees plus retained local task branches.
- Surface cleanup counts in human-readable project status so Codex can reconcile completed managed worktrees without relying on user memory.

### Safety

- Cleanup still requires RigorBreeze provenance, an exact creation path, a clean non-current worktree, and proven integration.
- Successfully created or integrated task branches remain preserved; lifecycle cleanup never deletes local or remote refs. Atomic rollback may still remove the just-created branch when worktree initialization itself fails.

## [0.6.0] - Core boundaries and on-request delivery

### Changed

- Split the policy runner into one stable CLI entry plus dedicated state, policy, parallel-work, and automation modules without changing the CLI, schema-v3 evidence model, or Spec Tree.
- Redefined `manual` as no standing unattended authority. An explicit current-message request may authorize one guarded commit or push without changing project configuration.
- Added one-time commit/push options to the existing `automate` command. One-time push requires an explicit remote, current branch, exact expected HEAD, a fast-forward remote, and post-push SHA verification; it never rebases or force-pushes.
- Require current full verification, structured acceptance, and review before a one-time direct push to an integration branch.

### Fixed

- Preserve verification across an automated commit when the journaled parent, tree, task, evidence, verification, and project fingerprint still identify the same immutable result.
- Allow a task executed on its physical baseline branch to advance from its recorded base SHA while the complete task change set and Allowed Scope remain valid.

### Compatibility

- Evidence schema remains v3 and the automation journal remains v1. New journal records add the backward-compatible `authorizationMode` projection.
- No new public command, Spec file type, state system, runtime dependency, or persistent permission was added.

## [0.5.2] - Real-use safety closure

### Changed

- Require unique machine-readable acceptance IDs and repository-relative path, prefix, or glob entries in Allowed Scope.
- Prevent first approval or reapproval from absorbing production implementation changes into a new RED baseline. The same outcome may be amended only after reverting production changes; a new outcome or acceptance condition becomes a dependent slice.
- Require real test files for L1/L2 RED, bind RED to declared acceptance IDs, and close every current TDD chain with the current full verification.
- Evaluate committed and uncommitted task changes for scope drift before verification, merge, archive, or optional Git automation.
- Use path-aware scope globs, NUL-safe Git status parsing, explicit scope for workflow policy files, and complete committed change types.
- Derive mandatory L2 full checks from risk and actual dependency or migration changes.

### Fixed

- Disable Python bytecode generation before loading bundled modules so first-run commands do not add `__pycache__` noise to projects.
- Warn L1/L2 users when the workflow baseline has not yet been captured in Git.

### Compatibility

- Evidence schema remains v3. `status --json` adds a backward-compatible `scope` projection.
- Historical evidence remains readable, but verification produced by an older runner is stale for v0.5.2 gates.

## [0.5.1] - Public Preview baseline

### Added

- Minimal SDD task contracts with machine-bound TDD, verification, acceptance, artifact, and retrospective evidence.
- Project-declared advisory/enforced check profiles and GitHub/GitLab CI templates.
- Isolated parallel worktrees, optional dependency DAGs, scope-conflict detection, and cross-window status recovery.
- Manual-by-default commit, push, protected merge, and release adapters with Git-private idempotency records.
- Provenance-safe worktree reconciliation and schema-v1/v2-to-v3 evidence migration.

### Maturity

- This is the first public-preview baseline, not a claim of production readiness.
- v1.0 remains gated on real L1/L2 slices, parallel and DAG use, remote CI, and protected delivery exercises.

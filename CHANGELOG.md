# Changelog

English · [简体中文](CHANGELOG.zh-CN.md)

All notable changes to RigorBreeze will be documented in this file.

The project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). During Public Preview, minor releases may change workflow interfaces when real-project evidence shows that the current contract is unsafe or unnecessarily costly.

## [Unreleased]

### Changed

- Renamed the project, Skill ID, invocation, runner, configuration, Git-private state, and task-branch prefix from Codex Production Flow to RigorBreeze before the first public release. No legacy alias is retained.
- Require inspection of the standard library, framework, and current dependency set before adding custom code or packages; new dependencies and abstractions need current acceptance or a durable invariant.
- Keep compatibility risk-adaptive: proven-dead private preview paths may be removed, while public APIs, persisted data, upgrade paths, and production migrations retain explicit transition, verification, and rollback requirements.

### Fixed

- Use a side-effect-free native Windows process query for worktree ownership checks instead of the POSIX-only `os.kill(pid, 0)` probe.
- Preserve repeated RED observations for audit while evaluating only the latest current chain per acceptance ID at closure gates.
- Configure CLI stdout and stderr as UTF-8 when supported so bilingual guidance remains printable on Windows legacy code pages.

### Documentation

- Reframed the repository for first-time adopters with bilingual onboarding, explicit safety boundaries, and a complete first-task walkthrough.
- Added concise contribution and security policies plus an MIT license.

## [0.10.2] - Shared worktree repair consistency

### Fixed

- Mark every registry record that references an exactly matched managed worktree as removed after Git confirms the physical cleanup, preventing later projections from entering a deleted directory.
- Treat archived records and the current active task in one primary worktree as sequential history rather than duplicate active ownership.
- Skip current-branch mismatch checks for archived historical records reconstructed after their original worktree was removed; duplicate active tasks remain blocked.

### Compatibility

- Public CLI, schema v4, automation journal v1, Spec Tree, dependencies, branch-retention policy, and Git authority are unchanged.

## [0.10.1] - Lossless historical repair

### Fixed

- Use the same registered integration proof for `integrated-unclosed` status and `archive --outcome reconciled`, so the suggested safe closure is executable when only allowlisted workflow commits remain.
- Rebuild the Git-private registry from every archived contract and evidence record, preserving multiple closed tasks that legitimately shared one historical worktree.
- Allow multiple closed task records to reference one preserved worktree while continuing to block duplicate active ownership.
- Emit a machine-readable registry repair plan on JSON doctor failures before `doctor --all --repair --json` mutates the disposable index.

### Compatibility

- Public CLI, schema v4, automation journal v1, Spec Tree, dependencies, and Git authority are unchanged.

## [0.10.0] - Initiative shaping and lifecycle truth

### Added

- Add an optional initiative-shaping pass for a new product, new business domain, broad legacy migration, or other idea that is not yet stable enough for one delivery contract. It compares viable approaches and closes product-risk ambiguity before only the first vertical slice enters the existing Spec Tree.
- Project `workflowBypass` in current and all-worktree status when an unapproved task already contains delivery changes, and persist one deduplicated machine practice event as an immediate evolution candidate.

### Fixed

- Recognize a registered task as `integrated-unclosed` when at least one product patch is already patch-equivalent on the base and every remaining positive commit contains only narrowly allowlisted workflow metadata.
- Keep mixed or unmatched product changes active and preserve the original conservative proof for unmanaged worktrees.

### Compatibility

- Public CLI, state/evidence schema v4, automation journal v1, Spec Tree, runtime dependencies, and Git authority are unchanged.

## [0.9.2] - Requirement interpretation reliability

### Changed

- Translate compound requests into observable `ADD`, `REMOVE`, `MOVE`, `RETAIN`, and `REPLACE` atoms before approval, with every atom mapped to an acceptance ID or an explicit out-of-scope reason.
- Resolve whether negated wording describes the current defect or desired result from project evidence; ask one short outcome question only when the direction remains materially ambiguous.
- Require UI final-state coverage for presence, absence, order/location, and retained behavior without adding a document, field, command, or user form.
- Classify user interpretation corrections through existing retrospective evidence as missing atoms, reversed intent, wrong source, or scope change without retaining chat transcripts.

### Tests

- Replaced the original semantics pressure fixture with a compound UI scenario that rejects partial capture of move/remove/retain operations and ambiguous negation while preserving the six-case suite.
- Allow live evaluations to write only their generated fixture's Git-private workflow state, and bind structured results to the exact scenario ID so valid Agent behavior is not reported as a harness failure.
- Define partial delivery in live evaluation as an omitted user-visible requirement atom, preventing incomplete optional workflow closure from being misreported as partial product implementation.

### Compatibility

- Public CLI, state/evidence schema v4, automation journal v1, Spec Tree, runtime dependencies, and Git authority are unchanged.

## [0.9.1] - Low-friction verification closure

### Changed

- Reuse an identical `argv + cwd + env + timeout` process result only inside one profile invocation while preserving separate check, report, and artifact records.
- Accept current configured `affected` or `full` evidence for an ordinary commit; targeted commands remain exploratory, while archive, merge, and direct integration-branch delivery retain full-quality gates.
- Run the core runner suite once with a 240-second timeout and use the deterministic behavior contract suite as the separate acceptance check. Live Codex behavior runs remain an explicit maintainer release-candidate action and are never launched by commit, full, or CI.

### Fixed

- Normalize timeout stdout/stderr from bytes, text, or missing values and always record exit code 124 with the preserved redacted output and timeout reason.
- Permit an explicitly marked synthetic secret only on the same physical line under configured test paths; secret paths, unmarked lines, and configured secret adapters remain enforced.

### Compatibility

- Public CLI, state/evidence schema v4, automation journal v1, Spec Tree, dependencies, and delivery authority are unchanged.

## [0.9.0] - Agent behavior reliability

### Added

- Added six repository-only synthetic pressure scenarios plus a standard-library scorer and an opt-in `codex exec --ephemeral --json` maintainer runner. Live redacted results stay under Git-private storage; CI uses deterministic fake transcripts and never calls a model.
- Added compact execution rules for semantic self-review before approval, fresh command/exit/scope evidence before completion claims, evidence-based review feedback handling, and an architecture stop after three failed hypotheses.

### Fixed

- Closed task projections discard stale retrospective `nextAction` values instead of suggesting work after archive.

### Compatibility

- Public CLI, state/evidence schema v4, automation journal v1, Spec Tree, risk lanes, runtime dependencies, and normal project operation are unchanged.

## [0.8.1] - Evidence-backed context intake

### Changed

- Incomplete prompts are completed from authoritative requirements, code, tests, Git and runtime evidence inside the existing task contract; Codex asks only for outcome-changing intent that cannot be recovered.
- Follow-up writes after compaction or while debugging/review skills are active must re-enter RigorBreeze state and ownership checks.
- External Git, deployment, developer-tool and platform writes first report observed current state, already completed work, immutable identifiers, the remaining action and stop conditions.
- Configured test paths nested below a source path are no longer misclassified as production changes before RED.

### Compatibility

- CLI, state/evidence schema v4, automation journal v1, Spec file types and runtime dependencies are unchanged.

## [0.8.0] - State closure and low-friction adoption

### Added

- `workflowBaseline` proves the managed installation on the real base branch and provides one exact, user-authorized baseline commit path.
- `archive --outcome reconciled` honestly closes externally integrated historical tasks without fabricating verification or acceptance.
- Normal archive retains an immutable `lastClosed` delivery context so guarded commit, push, and protected merge can finish after task closure.
- Explicit unmanaged-worktree cleanup requires an absolute path, base branch, exact HEAD, a clean inactive worktree, and complete integration proof while preserving the branch.

### Changed

- Primary and linked worktree state now lives only in Git-private directories; compatible legacy state is migrated conservatively.
- Installation status identifies missing and modified runner components, while lifecycle status prioritizes integrated or pending closure over stale-baseline advice.
- Enforced L1/L2 approval no longer accepts a workflow baseline committed only on a task branch.
- L2 guidance now favors sanitized real/provider-sandbox fixtures and explicit serialization, encoding, database-dialect, and business-precondition checks.

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

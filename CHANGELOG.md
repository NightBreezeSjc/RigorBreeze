# Changelog

English · [简体中文](CHANGELOG.zh-CN.md)

All notable changes to RigorBreeze will be documented in this file.

The project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). During Public Preview, minor releases may change workflow interfaces when real-project evidence shows that the current contract is unsafe or unnecessarily costly.

## [Unreleased]

### Changed

- Keep RigorBreeze-maintainer task contracts, evidence, and archives local to the source checkout; public release proof now stays in commits, the changelog, regression tests, and CI without changing initialized projects' evidence behavior.
- Renamed the project, Skill ID, invocation, runner, configuration, Git-private state, and task-branch prefix from Codex Production Flow to RigorBreeze before the first public release. No legacy alias is retained.
- Require inspection of the standard library, framework, and current dependency set before adding custom code or packages; new dependencies and abstractions need current acceptance or a durable invariant.
- Keep compatibility risk-adaptive: proven-dead private preview paths may be removed, while public APIs, persisted data, upgrade paths, and production migrations retain explicit transition, verification, and rollback requirements.

### Fixed

- Freeze current-worktree tasks against the configured sequential integration branch and its resolved Git SHA; fail before writing task records when that baseline is missing.
- Use a side-effect-free native Windows process query for worktree ownership checks instead of the POSIX-only `os.kill(pid, 0)` probe.
- Preserve repeated RED observations for audit while evaluating only the latest current chain per acceptance ID at closure gates.
- Configure CLI stdout and stderr as UTF-8 when supported so bilingual guidance remains printable on Windows legacy code pages.

### Documentation

- Added a bilingual architecture guide with GitHub-native diagrams for the system layers, risk-adaptive workflow, evidence boundaries, parallel worktrees, DAGs, and protected delivery; the README now links to a compact architecture overview without duplicating the handbook.
- Reframed the repository for first-time adopters with bilingual onboarding, explicit safety boundaries, and a complete first-task walkthrough.
- Added concise contribution and security policies plus an MIT license.

## [0.19.0] - Separate kernel responsibilities without changing behavior

### Changed

- Reduce `flow.py` from 3,875 lines to a thin 1,200-1,500 line orchestration entrypoint.
- Move evidence/retrospective/archive lifecycle into `flow_records.py`, environment/TDD/profile execution into `flow_verification.py`, and installation/status/doctor projections into `flow_diagnostics.py`.
- Use one helper manifest for initialization, installation integrity, workflow baseline tracking, and installed-runner upgrades.
- Compile every kernel module in CI while keeping the public CLI, state schema v5, evidence schema v4, automation journal v1, and all risk/delivery gates unchanged.

### Compatibility

- Existing active tasks keep their installed runner frozen. Idle projects may run `init` to install the three new helpers; no task, evidence, config, or command migration is required.

## [0.18.0] - Stop mixed work before approval and keep large features sliced

### Changed

- Require a clean task worktree before every L1/L2 approval; task-owned records and Git-private state remain valid, while foreign delivery changes and unignored caches block before baseline creation.
- Extend scope status with compatible `preexisting-dirt`, `cause`, and `dirtyPaths` details so cache hygiene, foreign work, and new out-of-scope writes produce one specific repair action.
- Separate product feature, RigorBreeze task, integration worktree/branch, and final pull request: one feature may close several independently verified sequential tasks and still ship through one PR.
- Require UAT, visual/runtime review, and follow-up feedback to re-enter current status and scope before another product write; forbidden paths, active owners, and new outcomes become successor tasks or visible handoffs.
- Expand deterministic Agent behavior coverage to nineteen scenarios, including invalid-approval re-entry and one-PR/multiple-slice delivery.

### Compatibility

- Public CLI, config/state schema v5, evidence schema v4, and automation journal v1 remain unchanged. Direct, L0, Emergency, and all existing L2 security/migration/release gates retain their behavior.

## [0.17.0] - Close real workflow friction without weakening proof

### Changed

- Route deterministic single-repository ordering/presentation corrections through Direct even when they touch backend code and add a regression test; path-bounded writer queries replace global status enumeration.
- Keep aggregate status alive when historical worktrees disappear, ignore proven integrated history during overlap checks, and retain integrated worktrees with uncommitted same-path changes as active writers.
- Preflight RED/build environments through built-in Node/Maven checks plus an optional project `environment` adapter; tooling and fixture failures no longer become business RED.
- Allow approved read-only authoritative observations to remain pending until matching verification, while review, artifacts, release, and writes stay gated.
- Reuse unchanged affected/full results unless `--force` is explicit, and provide a build-only temporary RSA adapter that never exposes or persists keys.

### Compatibility

- State/config remains schema v5, evidence remains schema v4, and automation journal remains v1. Existing projects need no new preflight configuration.
- Direct still excludes API/data/auth/permission/payment/lock/migration/dependency/production/external-state boundaries; every L2 gate remains unchanged.

## [0.16.0] - Bound solution and workflow cost without relaxing risk gates

### Changed

- Replace scattered YAGNI and dependency advice with one ordered ladder: no implementation, project reuse, standard/framework/platform-native capability, an installed maintained dependency, then the smallest clear new implementation.
- Batch one cross-repository user result into one combined approval, one end-to-end acceptance, and at most one retrospective while every repository retains its own scope, SHA, RED/GREEN, checks, and private record.
- Reuse current status through an unchanged phase and keep successful command output to command, exit code, scope, and digest; raw tails remain available for failures.
- Compact repeated check and verification results online by profile, task digest, and project fingerprint. Keep current truth, the latest useful failure, counts, and cumulative duration instead of linear duplicate success history.
- Extend the maintainer behavior harness to seventeen deterministic scenarios and record cached/uncached Token usage, workflow-only runner calls, evidence bytes, and product/test line deltas in Git-private results.

### Boundaries

- Keep schema v5, evidence schema v4, automation journal v1, the public CLI, and all L2 safety gates unchanged.
- Do not install Ponytail or adopt its modes, hooks, debt comments, or runtime dependency; only its minimum-solution and honest-measurement ideas influence this release.

## [0.15.1] - Reduce context cost without relaxing proof

### Changed

- Make current-worktree `status --json` the normal write-entry check; reserve all-project status for actual parallel coordination, repair, cleanup, and evolution work.
- Add the backward-compatible `status --all --compact --json` projection. It preserves active tasks, blockers, dependencies, worktree ownership, and next actions while replacing historical cleanup detail with counts; the original full response is unchanged.
- Reduce the activated `SKILL.md` entrypoint from 3,436 to 1,811 words through progressive disclosure into the existing handbook, Spec Tree, and CI references.
- Reduce the RigorBreeze-managed project `AGENTS.md` block from 804 to 438 words while preserving its trigger, risk, ownership, verification, and production-safety boundaries.
- Reuse an unchanged current-status snapshot within one uninterrupted write phase and summarize successful checks by command, exit, scope, and digest; raw output remains available for bounded failure diagnosis.

### Validation

- Lock the activated entrypoint to 2,000 words or fewer and the managed persistent policy to 600 words or fewer; require both current and compact-all status routes in the Skill contract.
- Verify compact and full status share the same task next action and overview; full output remains available for exact historical diagnosis.

### Compatibility

- State/config remains schema v5, evidence remains schema v4, automation journal remains v1, and no third-party dependency or public command is added. Existing `status --all --json` consumers keep their complete payload.

## [0.15.0] - Tighten Agent behavior without expanding the workflow surface

### Changed

- Re-observe strengthened tests against the immutable approval baseline when the contract and acceptance result are unchanged, while rejecting production-file overlays and unrelated environment failures.
- Group `status --all` and cleanup projections by physical worktree, retain compatible representative task IDs, and expose the executing bundled runner separately from installed project runners.
- Carry explicit `actor` and `kind` in next actions so wording such as "Implement the approved slice" remains Codex work rather than a false user-approval handoff.
- Require the Agent to prove whether a defect is wrong or missing data, wrong config, or a missing capability before widening scope, and keep the minimal correction separate from optional prevention.
- Treat unproven root causes as hypotheses until discriminating runtime evidence exists, instead of converting review guesses or repeated failures into confirmed diagnoses.
- Verify the real route, menu, role, account, and device entry before assigning manual acceptance; where one affordance is unavailable, report honest `N/A` and substitute equivalent runtime/API evidence.
- After two identical login, token, browser, or channel failures, stop repeating the same path, preserve a safe state, and switch diagnostic methods.
- Require one visual tracer before fanning out across three or more related screens or a new visual language, unless the change is an exact reuse of an already approved component.

### Validation

- Expand the deterministic Agent-behavior contract from fourteen to sixteen scenarios by extending the existing context/diagnosis cases and adding runtime-affordance-before-handoff plus visual-tracer-before-fanout.
- Score observable commands, changed paths, fresh verification, and a required user-facing result summary instead of trusting self-declared behavior markers; loaded rule text and command output cannot satisfy an Agent-action assertion.
- Keep a confirmed retrospective current across additional all-green verification reruns; only changed task/code facts, failures, acceptance, bypasses, or practice events require the human judgment again.

### Compatibility

- Public CLI, Spec Tree, state/config schema v5, evidence schema v4, automation journal v1, and dependencies remain unchanged. The bundled runner is now v0.15.0; active project tasks keep their installed runner frozen until closure.

## [0.14.0] - Make rigor proportional to consequence

### Added

- Add a no-task Direct lane for one unambiguous, low-consequence change proven by one targeted check.
- Add schema-v5 Git-common private records, explicit legacy migration, compact L1 history, and bounded sanitized L2/Emergency audit summaries.
- Project completed/current/one-next-action interaction state, plus stateless enforced full checks for clean CI checkouts.

### Changed

- Separate allocation concerns: risk selects gates, non-Direct independent outcomes use short-lived branches, and only concurrent writers or disposable risky experiments receive extra worktrees; sequential independent tasks reuse the checkout but not the predecessor branch.
- Let clear L1 requests supply approval, auto-close clean first-pass L1 work, and retain human review for friction and all L2/Emergency tasks.
- Reconcile integrated work automatically and safely delete only contained managed worktrees and local branches without remote uncertainty.
- Keep complete evidence schema v4 and automation journal v1; no public command, Spec file type, dependency, or production gate was added.

## [0.13.0] - Isolate reusable workflow repairs from business delivery

### Fixed

- Evaluate destructive-migration policy only against the active task's committed and working-tree change set, so an unchanged historical SQL file cannot block unrelated work while a newly changed destructive migration still fails.

### Changed

- When business work exposes a reusable RigorBreeze defect, preserve the business contract and record the blocker or evolution candidate, then fix the workflow in a separate Skill task instead of widening the product task or patching its private Runner.
- Reuse a designated integration worktree for sequential initiative slices; create another worktree only for a genuinely concurrent writer or a disposable risky experiment.

### Validation

- Expand the deterministic Agent-behavior contract from eleven to thirteen scenarios with business-task/workflow-defect separation and sequential-initiative worktree-reuse cases.

### Compatibility

- Public CLI, Spec Tree, state/evidence schema v4, automation journal v1, dependencies, default Git authority, and ordinary L0/L1 interaction remain unchanged.

## [0.12.0] - Improve Agent decisions without adding workflow weight

### Changed

- Bound initiative shaping and genuinely branching L2 ambiguity to a decision frontier: recover facts first, ask at most three currently answerable outcome-changing questions per round, and include a recommendation, rationale, and result impact.
- Treat a prototype as one disposable artifact answering one decision question; preserve its reference, observation, and verdict without treating it as production implementation or acceptance.
- Apply an abstraction deletion test before retaining helpers, adapters, wrappers, configuration layers, or shared abstractions; remove layers whose complexity disappears and retain boundaries that localize proven caller or safety complexity.
- Require every new always-loaded Skill instruction to identify its trigger, completion criterion, and behavior-evaluation delta; remove no-op wording or move detail to an existing reference.
- Separate stable released installations from contributor symlinks and defer project Runner upgrades until status reports `outdated` with `upgradeSafe=true` after active tasks close.

### Validation

- Expand the deterministic behavior contract from nine to eleven scenarios with decision-frontier and one-question-prototype cases, and add the deletion test to review skepticism.
- Require two manual live Codex runs per scenario for a release candidate; ordinary commits, configured profiles, and CI still never invoke a model.

### Compatibility

- Public CLI, Spec Tree, state/evidence schema v4, automation journal v1, dependencies, default Git authority, and ordinary L0/L1 interaction remain unchanged.

## [0.11.0] - Keep routine solo work light without weakening production gates

### Changed

- Route status questions, log explanations, screenshot analysis, recommendations, and other no-write diagnosis through a no-task path; stale workflow state is reported but does not block the read-only answer.
- Select L0/L1/L2 from consequence rather than diff size or urgency, and remove unrelated ceremony when an isolated L0 preparation would cost more than its implementation.
- Freeze an approved release scope before remote writes; critical findings stop the release while unrelated image, operating-system, database, scanner, framework, or platform upgrades become separate governance tasks.
- Require visible cross-task handoffs that name the destination, result, allowed and forbidden scope, dependency or blocker, and owner.

### Fixed

- Compact normally completed TDD history to the final valid GREEN and latest useful earlier failed or invalidated chain per acceptance ID, with aggregate counts; active, abandoned, and reconciled histories remain intact.
- Exclude maintainer tests, bytecode, and caches from the distributable Skill ZIP without deleting regression tests from source control.

### Compatibility

- Public CLI commands, state/evidence schema v4, automation journal v1, Spec Tree, dependencies, Git authority, and project adapter boundaries are unchanged.
- Compact tracked task/evidence records remain the audit model; a second local-only evidence store is deliberately deferred.

## [0.10.4] - Recover stale workflow records before risky work

### Fixed

- Keep `status` and `doctor` consistent when an active contract is missing: project an `orphaned-record`, block inferred completion, and provide a non-destructive restore action instead of aborting one command while another appears healthy.
- Surface existing evolution candidates through status with one copyable review instruction, without copying or mutating task evidence.
- Preflight the installed runner and real base-branch workflow baseline before creating a new Git-backed L1/L2 task; L0 and existing-task recovery remain lightweight.
- Preserve compact `Task-Origin` and `Waiting-On` facts for intentional prepared drafts so absence of implementation is not mistaken for permission to discard them.
- Add a seventh repository-only Agent pressure case that rejects replacing a broken high-risk workflow with an informal task card.

### Compatibility

- Public CLI commands, evidence/state schema v4, automation journal v1, Spec Tree, dependencies, Git authority, and project-specific adapter boundaries are unchanged.

## [0.10.3] - Compact completed verification evidence

### Changed

- Compact repeated `checkRuns` only when a task is normally completed: retain the latest record for every profile/check pair, the latest earlier failure, and aggregate pass/failure/omission counts.
- Keep regression tests, profile-level verification history, RED/GREEN, acceptance, artifacts, practice, closure, and abandoned/reconciled histories unchanged.
- Prefer structured review evidence over a second task-specific Markdown report; keep transient full logs in ignored or time-limited CI artifact storage.

### Compatibility

- Public CLI, schema v4, automation journal v1, Spec Tree, dependencies, Git authority, and pre-archive gate behavior are unchanged. Existing evidence without `checkRunSummary` remains valid.

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

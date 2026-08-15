# Solo Production Delivery Handbook

English · [简体中文](handbook.zh-CN.md)

> Use the least ceremony that still proves the user outcome. Codex performs the mechanics; the developer owns intent, real acceptance, and consequential decisions.

## Contents

1. [Operating principles](#1-operating-principles)
2. [Risk lanes](#2-risk-lanes)
3. [Run one vertical slice](#3-run-one-vertical-slice)
4. [Quality policy](#4-quality-policy)
5. [Real acceptance and release](#5-real-acceptance-and-release)
6. [Human decisions](#6-human-decisions)
7. [Parallel delivery](#7-parallel-delivery)
8. [Complexity limits](#8-complexity-limits)

## 1. Operating principles

### Deliver one observable outcome

Split work through a complete user path:

```text
user outcome
→ smallest interface, data, and UI change
→ automated behavioral proof
→ real-runtime acceptance
```

Do not split a feature into all database work, then all APIs, then all pages. Each task must produce a result that a user or independent oracle can observe.

### Treat one task as the active contract

Each change has one human-authored Markdown contract containing:

- authoritative requirement or design sources;
- allowed, forbidden, and out-of-scope work;
- observable acceptance IDs;
- public test seams and independent expected results;
- exact project verification commands;
- only the UI, security, migration, or release controls that apply.

`Task-Origin` stores one compact, resolvable source such as the current request,
an approved initiative brief, or a predecessor task. `Waiting-On` is `none` for
ready work and names the unresolved decision or upstream event for an
intentional prepared draft. A waiting draft cannot be approved, and lack of
implementation is not evidence that the draft is accidental or disposable.

`Runtime-Claims` names only exclusive resources actually used by the task: `port`, `service`, `process`, `app`, or `environment`; use `none` otherwise. Worktree isolation does not isolate these resources, so active claim conflicts block approval and window ownership. RigorBreeze reports conflicts but never kills processes, closes tools, or takes ports.

For conditional L2 integrations, `Operational-Modes` maps `enabled`, `disabled`, and `unavailable` to declared acceptance IDs. Each mapped behavior must close through current RED/GREEN or requirement-bound real-runtime evidence. Use `N/A - <reason>` when no conditional runtime behavior exists.

Allowed Scope entries must be repository-relative paths, directory prefixes, or globs. `*` matches one path segment; `**` crosses directories. Paths containing spaces remain valid. Acceptance criteria must contain unique machine-readable IDs. Approval freezes a digest of that contract. Never reapprove over production implementation changes. Restore the approved contract and finish, or revert production changes before correcting and reapproving the same observable outcome. A new user outcome or acceptance condition becomes a dependent slice. Git SHAs, artifact digests, reports, and completion results belong in machine evidence, not in fields the developer must predict before implementation.

### Keep the user out of internal mechanics

Codex runs `new`, approval, RED, verification, evidence, gate, and archive commands. The developer normally:

1. resolves only outcome-changing ambiguity;
2. accepts the result in the real product environment when applicable;
3. judges workflow friction for non-clean L1 and every L2/Emergency task.

Git and release automation remain `manual` unless the project explicitly selects a higher standing level. `manual` grants no unattended authority, but a user's explicit current-message request may authorize one guarded commit or push. Skill upgrades never increase authority.

## 2. Risk lanes

| Lane | Examples | Minimum close gate |
|---|---|---|
| Direct | One unambiguous low-consequence result with no protected boundary | One targeted check; no task, worktree, Spec, or evidence |
| L0 | Low-risk multi-file change needing coordination or audit | Configured affected verification |
| L1 | Feature, bug fix, end-to-end user flow | RED, full verification, real acceptance, two review passes, retrospective |
| L2 | Authorization, sensitive data, migration, payment, external integration, architecture, production release | L1 plus applicable security, migration, artifact, and release controls |
| Emergency | Smallest safe production repair | Reproduction, critical regression, rollback, monitoring, later evidence repair |

Do not lower risk to bypass a gate. Raise it when scope or consequences expand. A second human is required only by project policy or a real consequential decision; an AI reviewer never impersonates human approval.

Risk follows consequence, not diff size, duration, urgency, or ceremony already spent. Read-only diagnosis creates no task. Direct applies only to one repository, one observable result, no outcome ambiguity or competing writer, one targeted proof, and no API/data shape, auth, permission, payment, lock, migration, dependency, production configuration, or release impact. If preparation cost exceeds a genuinely isolated safe edit, choose Direct; if any protected boundary appears, stop and create L1/L2. Never downgrade L2 to recover speed. L0 remains for low-risk work that genuinely needs coordination or audit.

If an L2/release task cannot load its contract or authoritative workflow state,
stop before product, deployment, migration, or production writes. Restore the
record from Git/the originating worktree, or deliberately establish the
existing Emergency path. An informal task card is not a substitute for a
failed safety gate.

## 3. Run one vertical slice

### Shape an initiative before the first task

Use a short shaping pass only when the request is a new product, a new business
domain, a broad legacy migration, or a collection of outcomes that cannot yet
be approved as one vertical slice. A normal bounded feature or fix skips this
pass.

Read project and reference evidence before questioning the developer. Reuse an
existing versioned product/design source or create one compact initiative brief
outside the Spec Tree. It contains only:

- problem, target user, critical journey, desired outcome, and success measure;
- confirmed evidence, assumptions, unknowns, and their sources;
- two or three viable approaches with a recommendation and trade-offs;
- value, usability, feasibility, and viability risks;
- appetite, rabbit holes, no-gos, and the smallest useful first slice.

After recovering facts, expose only the current decision frontier: choices that
are outcome-changing, currently answerable, and not blocked by another unknown.
Ask at most three questions in one round. For each, recommend an answer, explain
why, and state how another answer changes the result, scope, or responsibility.
Recompute the frontier after the answers. Do not ask a question merely to show
process when evidence already establishes the result. The brief is ready only
when no outcome-changing decision remains, assumptions are explicit, and the
developer approves it.

For an uncertain experience, a disposable prototype may answer exactly one
decision question. Before running it, name that question. Record the prototype
reference, observed result, and keep/adjust/reject verdict in the existing
brief (or the task's Authoritative inputs when the task is already bounded).
Prefer a temporary directory or disposable branch; retain the artifact only
when requested or independently useful. A prototype never proves production
implementation, acceptance, or operational readiness. For uncertain value or
operations, use real user, operator, contract, analytics, or business evidence.
Reference code proves what an older system did, not what the new product should
do. A role prompt can challenge the brief but cannot supply missing intent or
approve it.

The developer approves the brief before task creation. Then cite its exact
version in the first RigorBreeze contract and continue through the normal
vertical-slice flow. Do not turn the roadmap into a task DAG, copy every open
question into every task, or create proposal/design/task directories in
parallel with the minimal Spec Tree. Later discoveries update the authoritative
product source and only the affected future task.

### Frame the task

Read the current requirements, design, code, interfaces, permissions, data, and tests before changing behavior. Propose the smallest observable task. Stop for unresolved business ambiguity, unapproved dependencies, unexpected migration risk, or scope expansion.

Do not require a perfect user prompt. Build a compact context intake inside Authoritative inputs:

- recover project facts from authoritative documents, current behavior, code, tests, Git and runtime evidence;
- trace the affected user flow through its business rule, interface, data, permission and failure boundaries rather than rereading the whole repository;
- record user outcome, current behavior evidence, architecture path, invariants/source of truth, freshness and fallback semantics, and the governing requirement/design/API version;
- ask only for outcome-changing intent that evidence cannot determine, and state any safe default explicitly.

For a compound request, preserve a short exact user phrase or a resolvable authoritative source and translate the request into observable `ADD`, `REMOVE`, `MOVE`, `RETAIN`, or `REPLACE` atoms. State each atom as a final product condition and map it to one acceptance ID or an explicit out-of-scope reason. This mapping lives in the existing Authoritative inputs and Acceptance criteria; it is not another requirements document.

Before widening the fix, prove whether the defect is wrong/missing data, wrong config, or a missing capability. Keep the minimal correction separate from optional prevention work; if prevention is not already accepted, record it as a follow-up instead of silently expanding the slice.

Negative phrases such as “not shown”, “missing”, “cannot”, or “not changed” can describe either the current defect or the desired result. Resolve that direction from requirements, prototype, current UI, tests and follow-up context. If evidence cannot decide and the two readings produce different results, ask one short binary outcome question. Do not silently choose a direction.

Role prompts such as “act as a CTO” may encourage a perspective but never replace project evidence, acceptance criteria, or human authority. After compaction or a follow-up write request, re-run RigorBreeze status and ownership checks even when a debugging or review skill is also active.

Before approval, agree on:

- the public interface or business boundary the test observes;
- the independent oracle that defines success;
- production paths that may change;
- the requirement or design version used for acceptance.

Then perform one semantic self-review. Reject unresolved placeholders and internal contradictions, split an oversized outcome, and make source-of-truth, freshness, fallback, and failure behavior unambiguous. Treat any unproven root cause as a hypothesis until runtime evidence distinguishes it. For UI changes, acceptance covers four applicable dimensions: what must exist, what must be absent, order/location, and behavior that must remain. When three or more related screens change together, or a new visual language is introduced, trace one representative screen first unless the work is an exact reuse of an already approved component. Present a compact final-state checklist before approval and confirm that every observable atom is covered. Correct facts recoverable from the repository directly; ask the developer only when different answers produce materially different outcomes.

The Skill first calls its bundled runner and inspects the `installation` projection. It must not begin product-code writes until the task exists, approval is valid, the current window owns the worktree, and the runner/configuration/baseline are usable. An active task freezes project-runner upgrades; finish or safely abandon that task with the bundled runner before `init` replaces managed files.

### Observe RED

L1, L2, and Emergency tasks require a real failure before production implementation:

- bind the failure to an acceptance ID;
- execute the relevant test through a public seam;
- record the command, exit code, expected failure, baseline SHA, and test digests;
- reject import errors, missing tools, unrelated historical failures, or a test that already passes;
- never derive the expected result by calling or copying the implementation under test.

L1 and L2 RED must name at least one real test file. Emergency may instead use a deterministic incident reproduction. A source-string search may prove a static contract such as an export or configuration key, but it cannot by itself prove user behavior or business logic.

For bugs, first build a deterministic, fast, agent-runnable reproduction. Rank falsifiable hypotheses, instrument only to distinguish them, remove temporary probes, and retain the regression. If three hypotheses for the same defect fail, stop patching. Preserve the attempts and reopen the architecture question around boundaries, shared state, ownership, and invalid assumptions before a fourth change.

### Implement as tracer bullets

Repeat:

```text
one failing behavior
→ minimum GREEN implementation
→ refactor while green
→ affected profile
→ next behavior
```

Do not batch every test before every implementation. Do not include drive-by refactors or speculative abstractions.

### Keep implementation lean without breaking production

After confirming the requirement and real call path, move through one ladder in order: no implementation, reuse project capability, use a standard-library/framework/platform-native capability, use an installed maintained dependency, then write the smallest clear new implementation. Stop at the first option that satisfies the contract. The ladder reduces solution surface, not requirement analysis or root-cause proof; it never removes security, permissions, data protection, migration, rollback, accessibility, or declared compatibility.

Preserve the smallest working vertical path, then extract a cohesive boundary only when separate change pressure, a public contract, or safety requires it. Standards Review classifies avoidable complexity as `delete`, `reuse`, `stdlib`, `native`, `yagni`, or `shrink`. Apply the deletion test before retaining a helper, adapter, wrapper, configuration layer, or shared abstraction: if deleting it removes complexity, delete it; if proven complexity merely spreads across callers or weakens safety, keep it. This is contextual, not a universal “two implementations” rule. Record intentionally accepted capacity limits and re-evaluation triggers in Lore `Directive`, not a new debt system.

Compatibility is a product property, not a universal yes/no rule. Code with no declared compatibility promise may remove a proven-dead path when callers, data, and Git history support that conclusion. Public APIs, persisted data, upgrade paths, and production migrations require an explicit transition, verification, and rollback or forward-fix strategy. A pre-1.0 version by itself does not authorize destructive changes when real users or data exist.

### Verify and close

- `affected` is the fast development feedback profile.
- `full` is the configured L1/L2 merge-quality profile.
- `archive` closes a completed task; it is not a production release.
- `archive --outcome abandoned --reason <reason>` closes a cancelled or superseded task without claiming success. Task-owned uncommitted changes, running automation, or unknown external outcomes block abandonment; unrelated changes are reported. Branches, worktrees, and commits are preserved.
- `archive --outcome reconciled --reason <reason> --expected-head <sha>` closes a historical task whose code is already integrated. It requires exact HEAD plus ancestry or complete patch-equivalence (or explicit same-base-branch confirmation with no product changes), records the original phase and missing verification honestly, and never fabricates GREEN, acceptance, or release success.
- `release` is evaluated only after an explicit release request.

The normal delivery order is verify/full → acceptance → two-pass review → retrospective → archive → guarded commit/push/merge → reconcile → cleanup. A clear L1 request is sufficient approval once its compact contract is complete. A clean first-pass L1 records a machine retrospective and closes automatically; failures, bypass, rework, unreasonable blocks, and every L2/Emergency retain human review. Release authority is never inherited from ordinary archive.

L0 may archive after configured verification. L1/L2 retain current full verification, applicable acceptance, and two review passes; only the retrospective interaction is conditional for a clean L1.

Schema-v5 projects keep contracts and full evidence in Git-common `.git/rigorbreeze/records/` by default. After proven integration, L1 detail becomes a path-free local history summary. L2/Emergency keeps full private evidence and may publish only a sanitized audit summary capped at 32 KiB. Legacy tracked projects move only through an explicit idle, clean migration; Runner upgrades never move records silently.

An ordinary commit requires a current configured `affected` or `full` result; a targeted exploration never satisfies the gate, and a fresh configured result is reused instead of rerun. Archive, merge, and direct integration-branch delivery remain full-quality operations. Live Codex behavior evaluation is a separate maintainer release-candidate action and is never launched by commit, configured full, or CI.

Verification, merge, archive, and optional Git automation evaluate the complete task change set: committed paths from the approved baseline through `HEAD` plus current working-tree changes. A scope violation takes priority in `status` and must be corrected or split before verification continues. Every current RED chain must have an unchanged test digest and GREEN bound to the current full verification before merge or archive.

Run review in two passes:

1. standards: correctness, simplicity, project conventions, security, maintainability, tests, scope;
2. spec: every acceptance ID, design state, interface, data, permission, and forbidden boundary.

A solo developer may perform both with fresh context at different times.

Review feedback is evidence to investigate, not authority to obey. Compare it with the accepted outcome, real code use, compatibility constraints, tests, and YAGNI. Reject an irrelevant redesign or unused capability with evidence instead of expanding scope.

Before commit, archive, or a claim that work is fixed, passed, or complete, cite verification actually run in the current turn: exact command, exit status, and covered scope. A historical report, a partial check, or another Agent's statement cannot substitute for fresh evidence.

## 4. Quality policy

`rigorbreeze.toml` declares only the checks the project actually uses. Every check listed in the selected profile must be configured, must produce its required report, and must pass in enforced mode. Capabilities outside the profile need no `N/A` record.

Common optional check IDs include:

- format, lint, and typecheck;
- unit, integration, E2E, and contract;
- secret, dependency, license, and SBOM;
- migration, build, Playwright, and acceptance.

One-off exploration and debugging commands may run directly but do not satisfy workflow gates. The configured profile is the contract shared by local development and CI.

Within one profile invocation, checks with identical argv, resolved cwd, effective environment, and timeout share one process result. Each check still validates its own report and artifacts and records `reusedFromCheckId`; no result is cached across profiles, sessions, or project changes.

Keep regression tests as durable product assets. After every profile, compact identical-fingerprint repeats online to current truth plus the latest useful failure; `checkRunSummary` and `verificationSummary` preserve pass/failure counts and cumulative duration. A changed task or project fingerprint remains distinct. TDD keeps current RED/GREEN plus the latest replaced or failed chain; acceptance, migration, release, rollback, and evolution candidates remain intact. Record ordinary review facts in structured evidence with `standards`, `spec`, and a non-empty `findings` summary. Raw logs belong in ignored local output or time-limited CI artifacts, not tracked evidence.

L2 `full` derives a non-negotiable minimum from risk and actual changes: secret scanning, build, at least one static-quality check, and at least one behavioral check. Dependency-manifest changes additionally require dependency, license, and SBOM checks with non-empty reports. Migration changes require the configured migration adapter and report. L0/L1 remain project-declared and do not inherit unrelated enterprise tooling.

Always preserve these boundaries:

- staged files stay within the approved task scope;
- workflow policy and runner files require explicit Allowed Scope just like product files;
- secrets and sensitive files never enter a commit or evidence record;
- dependency and migration changes are detected and explicitly reviewed;
- changing source, tests, dependencies, configuration, migrations, or the task invalidates stale proof;
- tests, UAT, artifacts, and release refer to the same Git SHA and immutable artifact digest when release applies.

Synthetic redaction fixtures may annotate a secret-shaped value with `rigorbreeze: synthetic-secret` on the same physical line, but only under configured test paths. The exemption applies only to the built-in content heuristic for that line: secret-like paths, other lines, and the project's configured secret adapter still block normally, and output reports only file/line metadata.

Local advisory mode helps iteration. Remote required checks and protected environments are the non-bypassable merge and release authority.

## 5. Real acceptance and release

Accept the capability that actually changed:

- UI: real runtime, key loading/empty/error/permission states, screenshots, accessibility, and applicable Playwright evidence;
- mini-app: production build, developer-tool automation, real AppID/HTTPS environment, and device evidence;
- authorization: role, tenant, ownership, data scope, and forbidden access;
- migration: cloned-data rehearsal, before/after assertions, backup/restore or forward-fix proof;
- external integration: prefer sanitized real responses or provider-sandbox fixtures; cover enabled, disabled, and unavailable modes plus failure behavior. Verify wire serialization, text-form JSON, URL-encoding count, database-dialect semantics, and order-creation or other business preconditions where applicable. Mock or temporary credentials prove only a local contract/build, never real acceptance.

Before assigning manual acceptance, confirm the actual route, menu, role, account, and device entry that will be used. If one of those affordances is unavailable, say so honestly as `N/A - <reason>` and substitute equivalent runtime/API evidence instead of pretending a human can click a path that does not exist.

Humans approve visual baselines. Never update screenshots only to remove a failure.

Only an explicit production release requires:

- one immutable artifact and Git SHA across tests, UAT, and deployment;
- feature flag and staged rollout scope;
- observation window, SLI/SLO, and alert owner;
- executable rollback or forward-fix command;
- applicable business metric and user-feedback evidence.

Freeze the approved operation scope before the first remote write. A newly discovered critical risk stops the release. An unrelated base-image, operating-system, database-engine, scanner, framework, or platform upgrade becomes a separate governance task instead of silently expanding the business deployment. Ordinary release work must not absorb a security modernization program simply because both touch the same image or server.

An L2 release also requires a machine JSON `operation-plan` bound to the current Git SHA and artifact digest. It lists ordered backup, configuration-freeze, migration, deployment, acceptance, traffic-switch, and observation stages; every step has a success condition, plus stop conditions, safe recovery points, and rollback limitations. Show the full plan and identify the single step about to run before any remote write.

Before any external Git, deployment, developer-tool, or platform write, inspect the external system rather than trusting an old plan or chat summary. Present the observed current state, what is already completed, current immutable identifiers, the one remaining action, and stop conditions. Do not rebuild, upload, migrate, deploy, or promote a version again merely because that step still appears in an earlier checklist.

Record `operation-result` after execution. `paused` and `failed` results state completed steps, the current safe state, and exactly one resume action. For example, when migration succeeded but the candidate failed and the old instance remains healthy, resume from candidate deployment instead of repeating migration or the whole release. These snapshots do not create a resident deployment scheduler.

AI may organize the evidence but cannot provide its own security exception, legal judgment, or production approval.

Temporary or synthetic credentials can prove that a project builds. They cannot prove a real environment, authorize deployment, or satisfy acceptance or release evidence.

## 6. Human decisions

Machine facts stay in `spec/evidence/<TASK-ID>.json`: approval baseline, RED, checks, duration, invalidation, reports, file digests, Git SHA, artifacts, and acceptance.

Before L1/L2/Emergency archive, Codex displays the prefilled `retro --json` summary. Ask the developer only:

1. What primarily caused rework, if any?
2. Was any block, bypass, or `nextAction` unreasonable?
3. Did the workflow help, remain neutral, or hurt?

The confirmation binds to the current task and project fingerprint. L0 has no mandatory retrospective. Runner drift, occupied task slots, runtime conflicts, missing operation plans, and gate failures are captured and deduplicated automatically as practice events. If the user corrects the interpretation with language such as “I meant”, “you missed”, or “understood it backwards”, record the existing retrospective exception as `requirement-interpretation-correction` and classify it as `missing-atom`, `reversed-intent`, `wrong-source`, or `scope-change`. Correct blocks remain statistics; only human-confirmed misblocks, unreasonable next actions, bypasses, workflow-caused rework, or `hurt` impact become evolution candidates. Do not create a second practice log or retain chat transcripts.

Ordinary candidates are observed once and reviewed after the second comparable occurrence. Review immediately when the workflow incorrectly permits a secret, privilege bypass, destructive migration, stale evidence, unauthorized external action, or wrong release.

If an active business task reveals a reusable RigorBreeze defect, preserve the
approved business contract and evidence. Record the failed gate as a blocker or
evolution candidate, then create a separate Skill task in the RigorBreeze
repository. Do not add runner internals to the business Allowed Scope, patch a
project-private runner, or reapprove over implementation changes merely to keep
the task moving.

## 7. Parallel delivery

Parallel writing uses this invariant:

```text
one project entry
→ one short-lived branch per independent outcome
→ one physical worktree per concurrent writer or designated integration stream
→ one active task per worktree
→ one rebuildable registry in the Git common directory
```

Keep a stable `RIGORBREEZE_SESSION_ID` per Codex window. A second live session cannot claim the same worktree. Routine writes use current-worktree `status --json`; concurrent windows and optional orchestrators use `status --all --compact --json`. Load the full `status --all --json` only when exact historical repair, cleanup, or evolution detail is required.

Sequential initiative work reuses one designated integration worktree per
repository. Create another worktree only for a genuinely concurrent writer or
an explicitly disposable risky experiment. A planned future task is not
concurrency, and closing one slice does not require replacing the initiative's
worktree before the next sequential slice.

Treat branch and worktree allocation as separate decisions. Consequence selects
the quality lane; outside Direct, an independent outcome selects a short-lived task branch;
concurrent writers select additional worktrees; real ordering selects
`Depends-On`. After an independent task is closed and integrated, the same
window reuses its clean physical worktree by returning to the current base and
creating a fresh task branch. Reuse the existing branch only for explicitly
related sequential slices on a designated integration branch, after the prior
slice is closed, committed, and clean. Never stack unrelated work on a previous
task branch. A high-risk task with one writer uses stricter gates, not an extra
worktree merely because it is important.

Before one task asks another task or window to act, show a visible handoff: destination task, observable result, allowed scope, forbidden scope, dependency or blocker, and owner. This notice improves user understanding but does not create another authority; the receiving task contract remains controlling.

After two identical login, token, browser, or channel failures, stop repeating the same path. Preserve a safe state, switch to a different diagnostic method or runtime surface, and keep the root cause labeled as a hypothesis until the new evidence discriminates it.

All worktree state is Git-private. `status --json` projects the workflow baseline from the real base branch and distinguishes missing, partial, modified, current, and blocked states. A one-time baseline commit is allowed only on that branch, at the expected HEAD, with no active task or mixed product changes.

Do not create a DAG for independent tasks. When ordering is real, store it only in each task's `Depends-On`. The runner derives readiness, cycles, missing dependencies, and topological order. Unrelated active tasks may not have overlapping allowed scopes; split them, order them, or isolate a shared integration task.

`Depends-On` represents only tasks in the same repository. For cross-repository delivery, each repository keeps its own contract and evidence; Authoritative inputs link the counterpart task and shared API/data contract. A consumer cannot complete real acceptance until the provider interface is integrated and verified.

Treat one user-visible cross-repository result as a single interaction: read each repository status once, ask for one combined approval at the highest risk, collect one end-to-end acceptance, and ask for at most one retrospective. Each repository still owns its task ID, allowed scope, Git SHA, RED/GREEN, checks, and local record. Reuse the acceptance reference and concise summary instead of copying product background, screenshots, logs, or reports.

Automation levels are cumulative but explicit:

| Level | Permitted action | Required boundary |
|---|---|---|
| manual | Validate by default; one requested commit/push | No unattended writes; one-time authority does not persist |
| commit | Commit approved task files | Current gates, no unrelated changes |
| push | Push `rigorbreeze/<task-id>` | No protected target or force push |
| merge | Request provider auto-merge | Current Required Checks and baseline |
| release | Invoke configured release adapter | One SHA/artifact and complete governance |

Provider results stay in the Git-private automation journal so external actions do not dirty evidence. `status --all --json` projects removable and retained worktrees/branches with cleanliness, integration status, expected HEAD, and confirmation requirements. Managed cleanup requires exact Flow-created provenance and may delete only a contained local branch through safe `git branch -d` when no remote uncertainty exists. Patch-equivalent, uncontained, unmanaged, current, dirty, or remotely uncertain branches/worktrees remain with reasons; remote branches are never deleted automatically.

For an explicit current-task request, Codex may run `automate commit --once` or `automate push --once --remote <name> --branch <current> --expected-head <sha>` without changing `rigorbreeze.toml`. Push never commits implicitly, fetches before writing, permits only a fast-forward update, never rebases or force-pushes, and verifies the remote SHA. Direct integration-branch push additionally requires current full verification, structured acceptance, and review. One-time authority never applies to merge, release, production migration, or rollback.

## 8. Complexity limits

- Do not create one human document for every evidence category.
- Do not make every project declare every standard check.
- Do not duplicate evidence, attestations, or practice logs.
- Do not bind ordinary archive to production artifact and rollout fields.
- Do not create a worktree, DAG, code graph, vector index, or agent console for a simple task.
- Do not perform unsolicited Git or production actions while automation is `manual`; an explicit one-time commit/push is the only exception.
- Do not make workflow metrics a delivery goal of their own.
- Do not add a permanent abstraction for a one-off problem.

Change the shared Skill only after real use establishes the need. Prefer project configuration, an optional adapter, or a better prompt when those solve the problem without raising the fixed cost for every user.

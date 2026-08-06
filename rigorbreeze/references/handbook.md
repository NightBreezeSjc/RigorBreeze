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

`Runtime-Claims` names only exclusive resources actually used by the task: `port`, `service`, `process`, `app`, or `environment`; use `none` otherwise. Worktree isolation does not isolate these resources, so active claim conflicts block approval and window ownership. RigorBreeze reports conflicts but never kills processes, closes tools, or takes ports.

For conditional L2 integrations, `Operational-Modes` maps `enabled`, `disabled`, and `unavailable` to declared acceptance IDs. Each mapped behavior must close through current RED/GREEN or requirement-bound real-runtime evidence. Use `N/A - <reason>` when no conditional runtime behavior exists.

Allowed Scope entries must be repository-relative paths, directory prefixes, or globs. `*` matches one path segment; `**` crosses directories. Paths containing spaces remain valid. Acceptance criteria must contain unique machine-readable IDs. Approval freezes a digest of that contract. Never reapprove over production implementation changes. Restore the approved contract and finish, or revert production changes before correcting and reapproving the same observable outcome. A new user outcome or acceptance condition becomes a dependent slice. Git SHAs, artifact digests, reports, and completion results belong in machine evidence, not in fields the developer must predict before implementation.

### Keep the user out of internal mechanics

Codex runs `new`, approval, RED, verification, evidence, gate, and archive commands. The developer normally:

1. approves the intended outcome, scope, and acceptance boundary;
2. accepts the result in the real product environment;
3. confirms the prefilled retrospective for non-L0 work.

Git and release automation remain `manual` unless the project explicitly selects a higher standing level. `manual` grants no unattended authority, but a user's explicit current-message request may authorize one guarded commit or push. Skill upgrades never increase authority.

## 2. Risk lanes

| Lane | Examples | Minimum close gate |
|---|---|---|
| L0 | Documentation, non-behavioral copy, isolated styling | Configured affected verification |
| L1 | Feature, bug fix, end-to-end user flow | RED, full verification, real acceptance, two review passes, retrospective |
| L2 | Authorization, sensitive data, migration, payment, external integration, architecture, production release | L1 plus applicable security, migration, artifact, and release controls |
| Emergency | Smallest safe production repair | Reproduction, critical regression, rollback, monitoring, later evidence repair |

Do not lower risk to bypass a gate. Raise it when scope or consequences expand. A second human is required only by project policy or a real consequential decision; an AI reviewer never impersonates human approval.

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

Ask only the few outcome-changing questions that evidence cannot answer. For
an uncertain experience, validate a rough flow or prototype; for uncertain
value or operations, use real user, operator, contract, analytics, or business
evidence. Reference code proves what an older system did, not what the new
product should do. A role prompt can challenge the brief but cannot supply
missing intent or approve it.

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

Negative phrases such as “not shown”, “missing”, “cannot”, or “not changed” can describe either the current defect or the desired result. Resolve that direction from requirements, prototype, current UI, tests and follow-up context. If evidence cannot decide and the two readings produce different results, ask one short binary outcome question. Do not silently choose a direction.

Role prompts such as “act as a CTO” may encourage a perspective but never replace project evidence, acceptance criteria, or human authority. After compaction or a follow-up write request, re-run RigorBreeze status and ownership checks even when a debugging or review skill is also active.

Before approval, agree on:

- the public interface or business boundary the test observes;
- the independent oracle that defines success;
- production paths that may change;
- the requirement or design version used for acceptance.

Then perform one semantic self-review. Reject unresolved placeholders and internal contradictions, split an oversized outcome, and make source-of-truth, freshness, fallback, and failure behavior unambiguous. For UI changes, acceptance covers four applicable dimensions: what must exist, what must be absent, order/location, and behavior that must remain. Present a compact final-state checklist before approval and confirm that every observable atom is covered. Correct facts recoverable from the repository directly; ask the developer only when different answers produce materially different outcomes.

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

Before creating a helper, subsystem, configuration layer, or dependency, inspect the standard library, framework, and dependency set already present in the repository. Prefer the smallest maintained existing capability that satisfies the approved contract. Add something new only when current acceptance or a durable invariant justifies its ownership, supply-chain cost, and maintenance surface.

Preserve the smallest working vertical path, then extract a cohesive boundary only when separate change pressure, a public contract, or safety requires it. Modularity means explicit ownership and narrow responsibilities; it does not mean manufacturing layers, adapters, or extension points for hypothetical reuse. A time-boxed experiment may be disposable, but it stays outside the durable production path and cannot become an undocumented “replace later” architecture.

Compatibility is a product property, not a universal yes/no rule. Code with no declared compatibility promise may remove a proven-dead path when callers, data, and Git history support that conclusion. Public APIs, persisted data, upgrade paths, and production migrations require an explicit transition, verification, and rollback or forward-fix strategy. A pre-1.0 version by itself does not authorize destructive changes when real users or data exist.

### Verify and close

- `affected` is the fast development feedback profile.
- `full` is the configured L1/L2 merge-quality profile.
- `archive` closes a completed task; it is not a production release.
- `archive --outcome abandoned --reason <reason>` closes a cancelled or superseded task without claiming success. Task-owned uncommitted changes, running automation, or unknown external outcomes block abandonment; unrelated changes are reported. Branches, worktrees, and commits are preserved.
- `archive --outcome reconciled --reason <reason> --expected-head <sha>` closes a historical task whose code is already integrated. It requires exact HEAD plus ancestry or complete patch-equivalence (or explicit same-base-branch confirmation with no product changes), records the original phase and missing verification honestly, and never fabricates GREEN, acceptance, or release success.
- `release` is evaluated only after an explicit release request.

The normal delivery order is verify/full → acceptance → two-pass review → retrospective → archive → guarded commit/push/merge → reconcile → cleanup. Archive stores a read-only `lastClosed` snapshot so task-owned product changes, the moved contract, and its evidence can still be committed and delivered safely. A pending closure blocks another task in the same worktree. Release authority is never inherited from ordinary archive.

L0 may archive after its configured verification. L1/L2 require current full verification, applicable acceptance, two separate review passes, and the prefilled retrospective confirmation.

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

Humans approve visual baselines. Never update screenshots only to remove a failure.

Only an explicit production release requires:

- one immutable artifact and Git SHA across tests, UAT, and deployment;
- feature flag and staged rollout scope;
- observation window, SLI/SLO, and alert owner;
- executable rollback or forward-fix command;
- applicable business metric and user-feedback evidence.

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

## 7. Parallel delivery

Parallel writing uses this invariant:

```text
one project entry
→ one rigorbreeze/<task-id> branch and isolated worktree per writing task
→ one active task per worktree
→ one rebuildable registry in the Git common directory
```

Keep a stable `RIGORBREEZE_SESSION_ID` per Codex window. A second live session cannot claim the same worktree. `status --all --json` is the read-only interface for every window and optional external orchestrator.

All worktree state is Git-private. `status --json` projects the workflow baseline from the real base branch and distinguishes missing, partial, modified, current, and blocked states. A one-time baseline commit is allowed only on that branch, at the expected HEAD, with no active task or mixed product changes.

Do not create a DAG for independent tasks. When ordering is real, store it only in each task's `Depends-On`. The runner derives readiness, cycles, missing dependencies, and topological order. Unrelated active tasks may not have overlapping allowed scopes; split them, order them, or isolate a shared integration task.

`Depends-On` represents only tasks in the same repository. For cross-repository delivery, each repository keeps its own contract and evidence; Authoritative inputs link the counterpart task and shared API/data contract. A consumer cannot complete real acceptance until the provider interface is integrated and verified.

Automation levels are cumulative but explicit:

| Level | Permitted action | Required boundary |
|---|---|---|
| manual | Validate by default; one requested commit/push | No unattended writes; one-time authority does not persist |
| commit | Commit approved task files | Current gates, no unrelated changes |
| push | Push `rigorbreeze/<task-id>` | No protected target or force push |
| merge | Request provider auto-merge | Current Required Checks and baseline |
| release | Invoke configured release adapter | One SHA/artifact and complete governance |

Provider results stay in the Git-private automation journal so an external action does not dirty tracked evidence. `status --all --json` projects removable, retained, and unregistered worktrees plus retained task branches, with cleanliness, integration status, expected HEAD, and confirmation requirements. Integration is proven by ancestry or complete patch equivalence. For a registered task, positive commits left after `git cherry` may be ignored only when at least one product patch is negative/equivalent and every positive commit contains only the task's allowlisted workflow metadata; any mixed or unmatched product path remains active. Unmanaged proof stays unchanged and conservative. Managed cleanup requires exact Flow-created provenance. Unmanaged cleanup additionally requires a one-time explicit absolute path, base, expected HEAD, clean inactive state, and complete integration proof. Local branches are always preserved.

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

---
name: rigorbreeze
description: Operate and evolve RigorBreeze, an evidence-backed and risk-adaptive idea-to-delivery workflow for a solo developer using Codex. Use when shaping an unbounded initiative; initializing or resuming a project; implementing a non-trivial feature or fix; coordinating worktrees or a dependency DAG; collecting SDD/TDD and real-runtime evidence; enforcing quality gates; proving delivery readiness; or reviewing workflow friction.
---

# RigorBreeze

Deliver one observable user outcome per task. Keep human interaction proportional to risk; keep state and evidence machine-generated. One physical worktree has one writing owner. Git automation defaults to `manual`.

## Enter with the smallest sufficient context

1. Resolve the project root. Route status questions, log explanations, screenshot analysis, and recommendations through the **no-task path**; give the read-only answer even if workflow state is stale.
2. Before writing—including **after compaction**—run the bundled `status --json` for the current worktree. Reuse that snapshot during one uninterrupted write phase only while Git, task, worktree, and external state remain unchanged. Use `status --all --compact --json` only for concurrent writers, dependencies, cross-task handoff, or project-wide drift. Load the full `status --all --json` only for cleanup, detailed repair, or evolution review. Continue `interaction.next.actor=codex` yourself; show the user only real approval, safety-stop, or external action.
3. If uninitialized, run `init`, configure `rigorbreeze.toml`, then run `doctor --json`. Never replace an outdated project runner while a task is active. State belongs under the Git directory; migrate legacy state only through the runner.
4. Read the configuration, index, current contract, and only linked or affected authoritative sources. Before product writes, require an approved contract and a successful worktree claim. If an L2/Emergency record is missing or unreadable, **restore the authoritative record** or establish an **explicit Emergency** contract; never substitute an **informal task card**.

Read [handbook.md](references/handbook.md) for initialization, initiative shaping, L2/Emergency, parallel/DAG, automation, release, or evolution work. Read [spec-tree.md](references/spec-tree.md) before changing state, evidence, digest, archive, or retention behavior. Read [ci-gates.md](references/ci-gates.md) for enforced profiles, CI, or release gates. Use runner `--help` for syntax.

## Recover intent before creating work

Recover **recoverable project facts** from requirements, current code, tests, Git, interfaces, data, permissions, and runtime evidence. **Read every authoritative requirement, prototype, design, API, or runtime source** applicable to the slice; ask only for **outcome-changing intent** that evidence cannot establish. A persona such as “CTO” is a perspective, not evidence or approval. Trace the affected vertical slice, not the entire repository.

Use **initiative shaping** only for a **new product, new business domain, broad legacy migration**, or another unshaped initiative without one stable outcome. **Do not create a delivery task** while shaping. Recover facts, then maintain a **decision frontier**: ask no more than **three questions** per round, each with a recommendation, reason, and result impact; stop asking when evidence decides. Compare **two or three viable approaches** and keep one compact brief covering the problem, user journey, outcome and measure, evidence versus assumptions, **value, usability, feasibility, and viability**, appetite, no-gos, and recommended **first vertical slice**. A prototype answers **one decision question**; record observation and verdict, keep it disposable, and never treat it as production acceptance. Approve the brief only after result-level uncertainty is resolved. **Ordinary bounded work** skips shaping.

For an ordinary request, record outcome, current behavior and evidence, source of truth including freshness/fallback, design/API version, and unresolved result ambiguity. Classify a defect as **wrong/missing data, config, or missing capability** before writing. Translate compound requests into **observable atoms** (`ADD`, `REMOVE`, `MOVE`, `RETAIN`, `REPLACE`) and map each to an acceptance ID or explicit exclusion. Separate the minimal correction from **optional prevention**.

## Choose the risk lane and isolation

**Risk follows consequence**, not diff size:

- `Direct`: one low-consequence result in one repository; no ambiguity, competing writer, API/data shape, auth, permission, payment, lock, migration, dependency, production config, or release. Read current status, reproduce, make the smallest edit, run one targeted check, and report command/exit/scope. Create no task or evidence; **do not promote merely because configured profiles are absent or incomplete**.
- `L0`: coordinated documentation or isolated non-behavioral/visual change.
- `L1`: normal feature, fix, or user flow.
- `L2`: sensitive data, permissions, migration, payment, external integration, architecture, or production release.
- `Emergency`: smallest safe hotfix, followed by evidence repair and incident review.

Except Direct, create one observable task. A clear L1 request supplies approval after the contract is completed; ask again only for result ambiguity. Git isolation has distinct causes: **consequence sets gates**; each **independent outcome gets one short-lived task branch**; **concurrent writers—not importance—get extra worktrees**. A sole writer reuses a clean base worktree on a fresh task branch after prior closure. **Sequential initiative work** may reuse its integration worktree only when the prior slice is closed, committed, clean, and related. Never stack unrelated work or share one physical worktree between writers.

Ordinary tasks have no DAG. For real ordering constraints, show one compact proposal of outcomes, `Depends-On`, scope, acceptance, and parallel-ready nodes; create tasks after one approval. Task contracts remain the DAG. Cross-repository dependencies are references under authoritative inputs, not a global state system.

Contracts declare allowed/forbidden scope, unique acceptance IDs, public test seam, independent oracle, commands, and applicable risks. Use repository-relative paths/globs. Declare exclusive runtime resources or `none`; active conflicts block. Conditional L2 integrations map enabled, disabled, and unavailable modes to acceptance IDs.

Before approval, perform one **semantic self-review** for placeholders, contradictions, oversized scope, ambiguous outcome/source/fallback, and any **root cause as a hypothesis** until discriminating evidence exists. Distinguish a **current defect** from the **desired result**. For UI, cover existence, absence, order/location, and retained behavior. Show one compact **final-state checklist**. Approval freezes contract digest; do not rebaseline over implementation. Amend only after reverting implementation for the same outcome, or create a dependent task for a new outcome.

For enforced L1/L2, require a current workflow baseline on the real base branch. A user-authorized baseline commit may contain only managed workflow files, never product changes.

## Implement and prove

Follow configured record storage. Private v5 records stay in `.git/rigorbreeze/records`; explicit tracked mode remains compatible. Never silently move legacy records. L1 detail compacts after integration; L2/Emergency retains full private proof and publishes only a bounded sanitized audit summary when configured.

For L1/L2/Emergency, observe RED before production implementation. Bind a real acceptance ID, independent expected failure, command, **exit status**, approved baseline, and test digest. Tool/import/unrelated failures and already-green tests are not RED. Source searches prove static contracts only. Then iterate one behavior at a time: failing test, minimum GREEN through a public seam, refactor while green, affected checks.

Keep command output proportional to the decision: on success retain the command, return code, covered scope, and report digest; load raw output or a bounded failure tail only when diagnosing. Never hide a failed check or omit the artifact/report that a gate requires.

If only test implementation evolves while contract and acceptance stay unchanged, use the runner's approved-baseline replay; it may overlay test paths only and must clean its temporary worktree. A changed outcome, production file, dependency, config, migration, or failure mode requires a contract change or successor task.

For debugging, build a deterministic tight loop, minimize reproduction, rank falsifiable hypotheses, instrument only to distinguish them, remove probes, and keep a regression test. After **three failed hypotheses**, make an **architecture stop** and re-examine boundaries, shared state, and assumptions.

Before adding code or dependencies, inspect the **standard library, framework, and current dependencies**. Prefer the smallest maintained capability. A helper, wrapper, abstraction, dependency, or config layer needs **current acceptance or a durable invariant**. Apply a **deletion test**: remove or inline it if complexity disappears; retain it only when deletion redistributes proven independent-change or safety complexity. Compatibility is explicit: dead internal paths may be removed, while **public APIs, persisted data, upgrade paths, and production migrations** need an approved transition and rollback.

## Review, accept, and deliver

Run separate standards and spec passes. Standards checks correctness, simplicity, conventions, security, maintainability, tests, and scope. Spec checks each acceptance result, interface/data/permission contract, and exclusions. Treat **review feedback** as a hypothesis; verify it against actual use, compatibility, tests, and YAGNI.

Validate the real product. Before manual handoff, prove the real **route/menu/role/account/device** entry. If unavailable, record N/A, the **replacement method actually used**, and the remaining gap; use equivalent runtime/API proof. After **two identical login/token/browser/channel failures**, preserve a safe state and switch methods rather than repeating the instruction. A new visual language or three-plus related screens needs one representative **visual tracer** and approval before fan-out unless an approved component is reused exactly.

For migration, require rehearsal, assertions, backup/recovery or forward-fix proof. For release, use one SHA/artifact across tests and UAT, **freeze the approved operation scope**, show all stages and the current stage, and record one resume action after pause/failure. Unrelated infrastructure work becomes a **separate governance task**. AI cannot approve its own visual baseline, security exception, legal conclusion, or production release.

Before external Git, deployment, developer-tool, or platform writes, reconstruct the **observed current state** from the system: completed steps, immutable identifiers, one remaining action, and stop conditions. Never repeat an already completed action from an old plan. Synthetic credentials prove buildability only.

## Parallel handoff and Git authority

For concurrent work, use compact project status. Use detailed all-project status only when exact historical cleanup or repair evidence is needed. External agent tools may consume status but never replace task evidence, Git, and the runner. Before cross-task work, give one **visible handoff** naming destination, outcome, allowed and forbidden scope, dependency, and owner; prefer a **self-contained inline handoff** over another file or task.

Read `[automation].level`: `manual` has no standing write authority; `commit`, `push`, `merge`, and `release` progressively enable only configured guarded actions. A current-message `--once` may authorize commit or push, never merge/release. Never raise the level during setup. Push must fetch, remain fast-forward, never force/rebase, and verify remote SHA. Commit authority never grants migration or rollback authority.

After delivery, reconcile from the base worktree. Automatically remove only clean, non-current, managed worktrees proven contained in base, and only safe-delete local branches without remote uncertainty. Keep dirty, unregistered, patch-equivalent, uncontained, current, or remotely uncertain items with a reason. Never delete remote branches automatically.

## Learn and complete

Clean first-pass L1 may archive with a machine retrospective; L1 with friction and every L2/Emergency needs a prefilled human review. Record interpreted-request corrections without chat transcripts. A reusable workflow defect becomes a **separate Skill task** with a **self-contained inline handoff**, never a business-task expansion. Only judged workflow rework, unreasonable block/action, bypass, or harm becomes an evolution candidate; correct safety stops remain statistics. For evolution review, scan compact/private records for candidates and use `$rigorbreeze 汇总这个项目的演进候选`; do not create another log or silently relax a gate.

- UI: real runtime, key states, screenshots, accessibility, and Playwright visual evidence.
- Mini-app: formal build, developer-tool automation, real AppID/HTTPS environment, and device evidence.
- Migration: cloned-data rehearsal, assertions, backup/restore or forward-fix proof.
- Release, only when requested: one SHA/artifact across tests and UAT plus applicable governance. Freeze the approved operation scope before remote writes. A newly discovered critical risk stops the release; unrelated image, OS, database-engine, scanner, or deployment-framework work becomes a separate governance task instead of silently expanding the current release. Show the complete operation-plan stages and the one stage being executed; after pause/failure record the safe state and single resume action.

Before any external Git, deployment, developer-tool, or platform write, reconstruct the **observed current state** from the system itself. Summarize already completed steps, current immutable identifiers, the one remaining action, and stop conditions; never repeat a completed step from an old plan or chat summary.

Temporary or synthetic credentials prove buildability only; they cannot satisfy real-environment acceptance, deployment, or release evidence.

AI cannot approve its own visual baseline, security exception, legal conclusion, or production release.

## Parallel context and optional adapters

Use compact outputs and read only the next needed source. `status --all --json` is the project handoff: worktree, branch, phase, dependencies, readiness, scope, freshness, and deterministic next action. `doctor --all --json` diagnoses drift; use `doctor --all --repair --json` only to explicitly rebuild the disposable Git-common registry and clear stale locks.

For a large repository, an installed code-graph tool may help locate impact radius and affected tests only when its index reports the current Git SHA. Treat graph risk scores as hints, never as correctness gates or sources of truth.

External multi-agent tools may consume `status --all --json`, but they never become a second source of truth. Before cross-task work, show one **visible handoff** naming destination, observable result, allowed scope, forbidden scope, dependency/blocker, and owner; when that is enough to route the work, emit the self-contained handoff inline instead of asking for a non-outcome delivery channel or creating a handoff file/task. The receiving task stays authoritative. The task Markdown, task evidence, Git, and the runner remain authoritative.

`Depends-On` is repository-local. For cross-repository delivery, link the counterpart task and API/data contract under Authoritative inputs; do not complete consumer acceptance before the provider is integrated and verified.

## Optional Git automation

Read `[automation].level` before any Git action:

- `manual`: no unattended Git write; an explicit current-message request may authorize one guarded commit or push.
- `commit`: after enforced commit gates, stage and commit only allowed task files.
- `push`: additionally push only `rigorbreeze/<task-id>` without force.
- `merge`: additionally invoke configured GitHub/GitLab required-check and auto-merge argv adapters; never merge locally around protection.
- `release`: additionally invoke configured release-check and release argv adapters for one immutable SHA/artifact.

Never raise the configured level during initialization or upgrade. Before an automated action, summarize the exact action and target to the user; their project configuration is standing authorization only for that level. Tokens remain in Git/provider/CI credential stores. Commit/push authority never grants production migration or rollback authority. AI still cannot approve visual, security, legal, or production conclusions.

Use `automate commit --once` or `automate push --once --remote <name> --branch <current> --expected-head <sha>` only when the user explicitly requested that action in the current message. One-time authority never persists or covers merge/release. An ordinary commit requires current configured `affected` or `full` evidence—never targeted—and reuses it without rerunning; archive, merge, and integration-branch delivery still require current full evidence and applicable acceptance/review. Push fetches first, requires a fast-forward target, never rebases or force-pushes, and verifies the remote SHA.

After delivery or protected integration, run `reconcile --cleanup` from the base worktree. It may remove only clean, non-current, RigorBreeze-managed worktrees proven contained in the base and may delete their local branches only with safe `git branch -d` and no remote uncertainty. Retain patch-equivalent, uncontained, unregistered, current, dirty, or remotely uncertain branches/worktrees with a reason. Unregistered worktrees remain report-only unless the current user message explicitly authorizes their exact path, base, HEAD, and `--allow-unmanaged`.

Automation outcomes live in Git-private `.git/rigorbreeze/automation.json`, keyed by immutable inputs. They are projected by JSON status, validated by `doctor`, and never rewrite task evidence after the external action.

## Evolve from real use

At close, let a clean first-pass L1 record an automatic machine retrospective and archive without another questionnaire; if it had failure, bypass, rework, or an unreasonable block, show one prefilled review. Additional all-green verification refreshes machine statistics without repeating an unchanged human judgment; changed task/code facts, failures, acceptance, bypasses, or practice events invalidate it. L2/Emergency always require human retrospective and real acceptance. Runner drift, occupied tasks, resource conflicts, missing operation plans, and gate failures are deduplicated as practice events. When the user corrects an interpretation, classify it as `requirement-interpretation-correction` with `missing-atom`, `reversed-intent`, `wrong-source`, or `scope-change`; never retain chat transcripts. A reusable workflow defect must end with a self-contained inline handoff naming the separate Skill task in the Skill repository, evidence, allowed fix scope, and forbidden business scope—never create or amend a business task to carry it, even when old state cannot be reconstructed. Only judged workflow rework, unreasonable block/next action, bypass, or `hurt` becomes an evolution candidate; correct blocks remain statistics.

When a candidate is emitted:

- tell the user it was recorded in the task evidence;
- show the copyable instruction `$rigorbreeze 汇总这个项目的演进候选`;
- observe the first ordinary occurrence; review the Skill after a second similar occurrence;
- review immediately if a gate incorrectly permits secrets, privilege bypass, destructive migration, stale evidence, or a wrong release;
- classify the cause as core, project configuration, adapter, environment, usage, or a correctly detected risk;
- for a confirmed core problem, write a failing regression, make the smallest change in the Skill repository, and validate it in the next real slice.

When asked to review evolution, scan the configured private/tracked evidence and compact history for `evolutionCandidate: true`; do not create another practice log. Project evidence stays local. Never silently rewrite the installed Skill or relax a gate from one ordinary occurrence.

## Completion

Keep human interaction small: ask only for unresolved outcome-changing approval, applicable real acceptance, and the prefilled retrospective when L1 friction exists or the task is L2/Emergency. Clean L1 closes automatically with `workflowImpact=unreviewed`.

Codex runs the CLI and records evidence; do not make the user operate each internal command. Close in this order: verify, accept, review, confirm retrospective, archive, then guarded commit/push/merge and worktree reconciliation. Normal completion compacts repeated check and TDD details while retaining final proof, the latest useful earlier failure, and aggregate counts; it never deletes regression tests, and non-completed histories stay intact. L0 needs only configured affected verification; L1/L2 need full verification, applicable acceptance, review, and retrospective. Use `abandoned` for a clean cancellation. If code was already externally integrated but the task remained open, use `archive --outcome reconciled --reason <reason> --expected-head <sha>` only after integration and external outcomes are proven; never invent GREEN, acceptance, or release success. Production release still requires an active `release-ready` task. Before commit, archive, or any “fixed/passed/complete” claim, cite **fresh verification** run in this turn: the exact command, **exit status**, and covered scope. Historical reports, partial checks, or another Agent's success claim cannot substitute.

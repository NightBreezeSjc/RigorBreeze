---
name: rigorbreeze
description: Operate and evolve RigorBreeze, an evidence-backed and risk-adaptive idea-to-delivery workflow for a solo developer using Codex. Use when shaping an unbounded initiative; initializing or resuming a project; implementing a non-trivial feature or fix; coordinating worktrees or a dependency DAG; collecting SDD/TDD and real-runtime evidence; enforcing quality gates; proving delivery readiness; or reviewing workflow friction.
---

# RigorBreeze

Deliver one observable outcome per task. Match interaction to risk; machine-generate state/evidence. One worktree has one writer. Git automation defaults to `manual`.

## Enter with the smallest sufficient context

1. Resolve the root. Route status, logs, screenshot analysis, and recommendations through the **no-task path**; give the read-only answer despite stale workflow state.
2. Before writing—including **after compaction**—run bundled `status --json`. Reuse it through one uninterrupted write phase until HEAD, worktree, contract digest, ownership, external state, or a runner action changes. Use `status --all --compact --json` only for concurrency, dependencies, handoff, or drift; use full `status --all --json` only for exact cleanup, repair, or evolution. Continue `interaction.next.actor=codex`; surface only approval, safety-stop, or external action.
3. If uninitialized, run `init`, configure `rigorbreeze.toml`, then `doctor --json`. Never replace a runner during an active task. State belongs under Git; migrate it only through the runner.
4. Read configuration, index, contract, and affected authoritative sources. Product writes require approval and a worktree claim. For missing/unreadable L2/Emergency records, **restore the authoritative record** or create an **explicit Emergency** contract; never use an **informal task card**.

Read [handbook.md](references/handbook.md) for shaping, L2/Emergency, parallel/DAG, automation, release, or evolution; [spec-tree.md](references/spec-tree.md) for records/digests/retention; [ci-gates.md](references/ci-gates.md) for enforced CI/release. Use runner `--help` for syntax.

## Recover intent before creating work

Recover **recoverable project facts** from requirements, code, tests, Git, interfaces, data, permissions, and runtime. **Read every authoritative requirement, prototype, design, API, or runtime source** for the slice; ask only for unprovable **outcome-changing intent**. A “CTO” persona is perspective, not evidence. Trace the slice, not the repository.

Use **initiative shaping** only for a **new product, new business domain, broad legacy migration**, or another unshaped initiative. **Do not create a delivery task** while shaping. Maintain a **decision frontier**: at most **three questions** per round, each with recommendation, reason, and result impact. Compare **two or three viable approaches** in one brief: problem, journey, measured outcome, evidence/assumptions, **value, usability, feasibility, and viability**, appetite, no-gos, and **first vertical slice**. A prototype answers **one decision question**; record observation/verdict and never call it production acceptance. Approve after result uncertainty clears. **Ordinary bounded work** skips shaping.

For ordinary work, record outcome, evidence, source freshness/fallback, version, and result ambiguity. Classify defects as **wrong/missing data, config, or missing capability**. Map compound **observable atoms** (`ADD`, `REMOVE`, `MOVE`, `RETAIN`, `REPLACE`) to acceptance or exclusion. Separate correction from **optional prevention**.

## Choose the risk lane and isolation

**Risk follows consequence**, not diff size:

- `Direct`: one low-consequence result in one repository; no ambiguity, competing writer, API/data shape, auth, permission, payment, lock, migration, dependency, production config, or release. Read current status, reproduce, make the smallest edit, run one targeted check, and report command/exit/scope. Create no task or evidence; **do not promote merely because configured profiles are absent or incomplete**.
- `L0`: coordinated documentation or isolated non-behavioral/visual change.
- `L1`: normal feature, fix, or user flow.
- `L2`: sensitive data, permissions, migration, payment, external integration, architecture, or production release.
- `Emergency`: smallest safe hotfix, followed by evidence repair and incident review.

Except Direct, create one observable task. A clear L1 request supplies approval after the contract is completed; ask again only for result ambiguity. Git isolation has distinct causes: **consequence sets gates**; each **independent outcome gets one short-lived task branch**; **concurrent writers—not importance—get extra worktrees**. A sole writer reuses a clean base worktree on a fresh task branch after prior closure. **Sequential initiative work** may reuse its integration worktree only when the prior slice is closed, committed, clean, and related. Never stack unrelated work or share one physical worktree between writers.

Ordinary tasks have no DAG. For real ordering constraints, show one compact proposal of outcomes, `Depends-On`, scope, acceptance, and parallel-ready nodes; create tasks after one approval. Contracts remain the DAG. Cross-repository dependencies are authoritative-input references, not global state.

For one result spanning repositories, keep repository-local scope, SHA, RED, and checks, but batch human interaction: one combined approval at the highest risk, one end-to-end acceptance reference, and one retrospective projected only to repositories that require it. Read each repository status once; a changed repository alone repeats approval or verification. Never duplicate product background, screenshots, logs, or raw reports.

Contracts declare scope, unique acceptance IDs, public seam, independent oracle, commands, and risks using relative paths/globs. Declare exclusive runtime resources or `none`; conflicts block. Conditional L2 integrations map enabled/disabled/unavailable modes to acceptance.

Before approval, perform one **semantic self-review** for placeholders, contradictions, oversized scope, ambiguous outcome/source/fallback, and any **root cause as a hypothesis** until discriminating evidence exists. Distinguish a **current defect** from the **desired result**. For UI, cover existence, absence, order/location, and retained behavior. Show one compact **final-state checklist**. Approval freezes contract digest; do not rebaseline over implementation. Amend only after reverting implementation for the same outcome, or create a dependent task for a new outcome.

For enforced L1/L2, require a current workflow baseline on the real base branch. A user-authorized baseline commit may contain only managed workflow files, never product changes.

## Implement and prove

Follow configured record storage. Private v5 records stay in `.git/rigorbreeze/records`; explicit tracked mode remains compatible. Never silently move legacy records. L1 detail compacts after integration; L2/Emergency retains full private proof and publishes only a bounded sanitized audit summary when configured.

For L1/L2/Emergency, observe RED before production implementation. Bind a real acceptance ID, independent expected failure, command, **exit status**, approved baseline, and test digest. Tool/import/unrelated failures and already-green tests are not RED. Source searches prove static contracts only. Then iterate one behavior at a time: failing test, minimum GREEN through a public seam, refactor while green, affected checks.

Keep output proportional: on success retain command, return code, scope, and report digest; read raw output or a bounded failure tail only for diagnosis. Never hide failure or a required artifact/report. Batch machine phases without commentary; return only for failure, safety-stop, or real judgment.

If only test implementation evolves while contract and acceptance stay unchanged, use the runner's approved-baseline replay; it may overlay test paths only and must clean its temporary worktree. A changed outcome, production file, dependency, config, migration, or failure mode requires a contract change or successor task.

For debugging, build a deterministic tight loop, minimize reproduction, rank falsifiable hypotheses, instrument only to distinguish them, remove probes, and keep a regression test. After **three failed hypotheses**, make an **architecture stop** and re-examine boundaries, shared state, and assumptions.

After inspecting the **standard library, framework, and current dependencies**, use one solution ladder: **no implementation** → **existing project capability** → **standard library, framework, or platform-native capability** → **installed and maintained dependency** → **smallest clear new implementation**. It shortens solutions, not understanding. Standards Review tags removable complexity `delete`, `reuse`, `stdlib`, `native`, `yagni`, or `shrink`; a **deletion test** retains an abstraction only for **current acceptance or a durable invariant**. Put intentional limits and re-evaluation triggers in Lore `Directive`. Never shrink **permission**, **security**, **data protection**, **migration**, **rollback**, **accessibility**, or explicit **compatibility**. **public APIs, persisted data, upgrade paths, and production migrations** need transition and rollback.

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

Clean first-pass L1 may archive with a machine retrospective; L1 with friction and every L2/Emergency needs a prefilled human review. Additional all-green verification updates machine statistics without repeating an unchanged human judgment; changed task/code facts, failures, acceptance, bypasses, or practice events invalidate it. Record interpreted-request corrections without chat transcripts. A reusable workflow defect becomes a **separate Skill task** with a **self-contained inline handoff**, never a business-task expansion. Only judged workflow rework, unreasonable block/action, bypass, or harm becomes an evolution candidate; correct safety stops remain statistics. For evolution review, scan compact/private records for candidates and use `$rigorbreeze 汇总这个项目的演进候选`; do not create another log or silently relax a gate.

Codex runs internal commands. Close in order: verify, accept, review, retrospective, archive, guarded delivery, reconcile. L0 requires affected; L1/L2 require full plus applicable acceptance/review. Use `abandoned` for clean cancellation and `reconciled` only for proven external integration; never invent success. Release requires an active release-ready task. Before commit, archive, or fixed/passed/complete claims, cite **fresh verification**: command, status, scope. History or another Agent cannot substitute. After L2, cross-repository work, or context compaction, give one short handoff prompt recommending a new Codex task for the next independent feature; never block continuation.

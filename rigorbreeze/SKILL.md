---
name: rigorbreeze
description: Run RigorBreeze, a risk-adaptive idea-to-delivery workflow for solo Codex development. Use for initiative shaping, non-trivial implementation, worktree/DAG coordination, SDD/TDD/runtime evidence, delivery gates, or workflow evolution.
---

# RigorBreeze

Deliver one observable outcome per task. Match interaction to risk and machine-generate evidence. One worktree has one writer; Git automation defaults to `manual`.

## Enter with the smallest sufficient context

1. Resolve root. Use the **no-task path** for status/logs/screenshots/recommendations; give the read-only answer despite stale state.
2. Before writing—including **after compaction**—run bundled status. Direct locates targets read-only, then runs `python3 scripts/rigorbreeze.py status --json --path <target>`; never `--path .` or global status. Reuse for one write phase until HEAD, contract, ownership, external state, or runner changes. Reserve `status --all --compact --json` for concurrency/dependencies/handoff and full global detail for repair/cleanup/evolution.
3. If uninitialized, `init`, configure `rigorbreeze.toml`, then `doctor --json`. Never replace a runner mid-task; migrate Git state only through it.
4. Read configuration, contract, index, and affected sources. Writes need approval and a worktree claim. For missing L2/Emergency records, restore the authoritative record or create an explicit Emergency contract; never use an informal task card. Neither supplies missing product intent; stop product writes and ask.

Read [handbook.md](references/handbook.md) for advanced flows, [spec-tree.md](references/spec-tree.md) for record contracts, and [ci-gates.md](references/ci-gates.md) for enforced delivery. Use `--help` for omitted command forms.

## Recover intent before creating work

Recover **recoverable project facts** from code, tests, Git, interfaces, data, permissions, and runtime. **Read every authoritative requirement, prototype, design, API, or runtime source** for the slice; ask only unprovable **outcome-changing intent**. Personas are not evidence; trace the slice, not the repository.

Use initiative shaping only for a new product, new business domain, broad legacy migration, or unshaped initiative; ordinary bounded work skips it. Do not create a delivery task while shaping. Keep a decision frontier of at most three questions, each with recommendation/impact. Compare two or three viable approaches by evidence, value, usability, feasibility, and viability, no-gos, then choose the first vertical slice. A prototype answers one decision question, never acceptance.

For ordinary work, preserve the exact user-stated outcome/source and label Agent-inferred options. Inference cannot add a repository, backend, database, payment, permission, or external boundary without outcome approval. Record freshness/fallback/version/ambiguity; classify wrong/missing data, config, or missing capability; map observable atoms to acceptance/exclusion and separate correction from optional prevention.

## Choose the risk lane and isolation

**Risk follows consequence**, not diff size:

- `Direct`: one deterministic low-consequence result in one repository; no ambiguity/writer or API/persisted-data/auth/permission/payment/lock/migration/dependency/production-config/external-state/release boundary. Backend location and a regression test do not raise risk. Extend the existing test seam unless unusable. Use focused proof/compile; no task/evidence/full. **Do not promote merely because configured profiles are absent or incomplete.** Unrelated dirt may use a short-lived clean worktree; remove only clean+contained.
- `L0`: coordinated documentation or isolated non-behavioral/visual change.
- `L1`: normal feature, fix, or user flow.
- `L2`: sensitive data, permissions, migration, payment, external integration, architecture, or production release.
- `Emergency`: smallest safe hotfix, followed by evidence repair and incident review.

Except Direct, one independently verifiable outcome is one task. **Consequence sets gates; each independent outcome gets one short-lived task branch. Only a genuinely concurrent writer may use `new --worktree auto`; sequential work stays in the current clean worktree.** One feature/PR may contain several tasks: **sequential initiative work** reuses a clean integration stream, closes/commits each task, batches human interaction, then opens one PR. Never compress verification frontiers, multiply worktree/PRs, stack unrelated work, or share writers.

Ordinary tasks have no DAG. For real ordering, propose outcomes, `Depends-On`, scope, acceptance, and parallel-ready nodes; create tasks after one approval. Contracts remain the DAG. Cross-repository dependencies are authoritative-input references, not global state.

For one cross-repository result, keep repository-local scope/SHA/RED/checks; promise one combined approval, one end-to-end acceptance, and one retrospective even when blocked. Read each status once; only changed repositories repeat work. Do not duplicate background/raw evidence.

Contracts declare relative scope, unique acceptance IDs, public seam, independent oracle, commands, and risks. Declare exclusive runtime resources or `none`; conflicts block. Conditional L2 modes map enabled/disabled/unavailable to acceptance.

Before approval, perform one **semantic self-review**: reject placeholders/contradictions/oversized scope/ambiguous outcome-source-fallback and keep each **root cause as a hypothesis** until distinguished. Separate current defect from desired result; UI covers presence/absence/order/retained behavior. Show a final-state checklist. Approval freezes the contract; never rebaseline implementation.

L1/L2 approval requires a clean task worktree: only task records/private state may differ; foreign work/cache blocks. Enforced mode also requires the real base's current workflow baseline. A baseline commit contains managed files only.

## Implement and prove

Use configured storage. Private v5 records stay in `.git/rigorbreeze/records`; tracked mode remains compatible. Never silently move legacy records. Integrated L1 compacts; L2/Emergency retains private proof and configured sanitized audit.

For L1/L2/Emergency, preflight tests/command/runtime/dependencies and optional `environment` adapter; tooling failures are not RED. Bind a real acceptance ID, independent failure, command, **exit status**, baseline, and test digest. Source searches prove static contracts only. Iterate failing test → minimum public-seam GREEN → refactor → affected. Run full once at the final fingerprint; reuse unless `--force` is explicit.

Keep output proportional: success retains command/code/scope/report digest; read raw output or a bounded failure tail only for diagnosis. Batch machine phases; return only for failure, safety-stop, or judgment.

Create a tracked `verification/` pack only through a separate task when live acceptance repeatedly bottlenecks work. Seed three to five critical features defining Launch, Doctor, Drive, Evidence, and Cleanup; ignore reports. Verification Report v1 cannot be replaced by compilation, source search, unit tests, cached screenshots, or Agent claims; require its live level, current SHA, mapped features, evidence, Doctor, and Cleanup. Direct/no-pack projects gain no step.

If only tests evolve while contract/acceptance stay unchanged, use approved-baseline replay: overlay test paths only and clean the temporary worktree. Changed outcome, production, dependency, config, migration, or failure mode requires contract change or successor.

For debugging, minimize reproduction, test hypotheses, remove probes, and keep a regression. After **three failed hypotheses**, make an **architecture stop** and re-examine boundaries/shared state/assumptions.

After inspecting the **standard library, framework, and current dependencies**, follow: **no implementation** → **existing project capability** → **standard library, framework, or platform-native capability** → **installed and maintained dependency** → **smallest clear new implementation**. Standards Review tags `delete`, `reuse`, `stdlib`, `native`, `yagni`, or `shrink`; a **deletion test** retains abstraction only for **current acceptance or a durable invariant**. Put limits/re-evaluation triggers in Lore `Directive`. Never shrink **permission**, **security**, **data protection**, **migration**, **rollback**, **accessibility**, or explicit **compatibility**. **public APIs, persisted data, upgrade paths, and production migrations** need transition/rollback.

## Review, accept, and deliver

Run separate standards and spec passes. Standards checks correctness, simplicity, conventions, security, maintainability, tests, and scope. Spec checks each acceptance result, interface/data/permission contract, and exclusions. Treat **review feedback** as a hypothesis; verify it against actual use, compatibility, tests, and YAGNI.

Validate the real product. After UAT/runtime/follow-up, writes rerun status and scope: same-result feedback invalidates proof; forbidden/new results become a successor or handoff. Pending observations grant no acceptance. Prove route/menu/role/account/device or record N/A plus the replacement method actually used. After two identical login/token/browser/channel failures, preserve safety and switch methods. New visual language or three-plus screens needs one visual tracer unless reusing an approved component. The writer runs a cheap check; use a read-only independent Verifier only for judgment-heavy, expensive, high-impact, or multi-page proof against current HEAD.

Migration requires rehearsal, assertions, and recovery/forward-fix proof. Release uses one SHA/artifact, must **freeze the approved operation scope**, show the current stage, and record one resume action. Unrelated infrastructure becomes a **separate governance task**. AI cannot approve visual, security, legal, or production conclusions.

Before external writes, reconstruct the **observed current state**: completed steps, immutable identifiers, one action, and stop conditions. Never repeat completed work from an old plan. Synthetic credentials prove buildability only.

## Parallel handoff and Git authority

For concurrent work, use compact project status. Use detailed all-project status only when exact historical cleanup or repair evidence is needed. External agent tools may consume status but never replace task evidence, Git, and the runner. Before cross-task work, give one **visible handoff** naming destination, outcome, allowed and forbidden scope, dependency, and owner; prefer a **self-contained inline handoff** over another file or task.

Read `[automation].level`: `manual` has no standing write authority; `commit`, `push`, `merge`, and `release` progressively enable only configured guarded actions. A current-message `--once` may authorize commit or push, never merge/release. Never raise the level during setup. Push must fetch, remain fast-forward, never force/rebase, and verify remote SHA. Commit authority never grants migration or rollback authority.

After delivery, reconcile from the base worktree. Missing historical worktrees and proven integrated records are warnings/cleanup candidates, never reasons for aggregate status to crash or demand overlap approval. A proven integrated HEAD still conflicts while its worktree has uncommitted changes in the queried path. Automatically remove only clean, non-current, managed worktrees proven contained in base; the same strict rule applies to taskless Direct worktrees. Keep dirty, untracked, patch-equivalent, uncontained, current, or remotely uncertain items with a reason. Never delete remote branches automatically.

## Learn and complete

Clean first-pass L1 may machine-retrospect; friction and every L2/Emergency need prefilled human review. Extra green runs do not repeat unchanged judgment; changed facts invalidate it. A reusable defect becomes a separate Skill task, never business expansion. Ordinary failures need two comparable occurrences; a high-risk escape needs one. Promote a rule only when the same fixture shows the candidate beats the prior Skill without regression. Review private candidates with `$rigorbreeze 汇总这个项目的演进候选`; create no second log or relaxed gate.

Codex runs internal commands. Close in order: verify, accept, review, retrospective, archive, guarded delivery, reconcile. L0 requires affected; L1/L2 require full plus applicable acceptance/review. Use `abandoned` for clean cancellation and `reconciled` only for proven external integration; never invent success. Release requires an active release-ready task. Before commit, archive, or fixed/passed/complete claims, cite **fresh verification**: command, status, scope. History or another Agent cannot substitute. After L2, cross-repository work, or context compaction, give one short handoff prompt recommending a new Codex task for the next independent feature; never block continuation.

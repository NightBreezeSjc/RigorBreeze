---
name: rigorbreeze
description: Operate and evolve RigorBreeze, an evidence-backed and risk-adaptive spec-to-delivery workflow for a solo developer using Codex. Use when initializing or resuming a project, completing an incomplete request from project evidence, implementing any non-trivial feature or follow-up fix in an initialized project, coordinating isolated parallel worktrees or an optional dependency DAG, collecting SDD/TDD and real-runtime acceptance evidence, running configured quality gates, proving merge or release readiness, or reviewing workflow friction from real delivery.
---

# RigorBreeze

Deliver one observable user outcome per task. Keep one human-authored Markdown contract per change; keep state, evidence, registry, and reports machine-generated. One worktree owns one writing task. Git automation defaults to `manual`, meaning no standing unattended authority.

## Start or resume

1. Resolve the project root.
2. Before every non-trivial writing request, including a follow-up after compaction or while debugging/review skills are active, run the bundled `python <skill-dir>/scripts/flow.py --root <project> status --all --json` in Git projects; fall back to `status --json` before initialization. Other skills supplement RigorBreeze but never replace its task state and ownership check.
3. If uninitialized, run `init`, configure `rigorbreeze.toml`, and run `doctor --json`. Report `installation.status`; never overwrite an outdated project runner while a task is active.
4. Read `rigorbreeze.toml`, `spec/index.md`, the current task, and only its linked authoritative sources. State for every Git worktree is private under its Git directory; migrate legacy `spec/state.json` through `init` or `doctor --all --repair`, never by editing it.
5. Follow `nextAction`; use the bundled runner's `--help` as the canonical command reference. Before product-code writes, require an approved contract and successfully claim the current worktree/window.

Read [handbook.md](references/handbook.md) before initialization, policy changes, or L2/Emergency work. Read [spec-tree.md](references/spec-tree.md) before changing state, evidence, digest, or archive behavior. Read [ci-gates.md](references/ci-gates.md) when configuring remote enforcement or releases.

Complete an imperfect prompt before creating the contract. Recover **recoverable project facts** from authoritative requirements, current code, tests, Git, interfaces, data, permissions and runtime evidence. Ask only for **outcome-changing intent** those sources cannot establish. State safe defaults and uncertainty explicitly; a persona such as “CTO” is a perspective, never evidence or approval. Trace only the affected vertical slice and its dependencies rather than rereading the whole repository.

Write the compact result into the existing Authoritative inputs: user outcome, current behavior and evidence, business and architecture path, invariants and source of truth (including freshness/fallback semantics), requirement/design/API version, and unresolved outcome-changing ambiguity. Preserve a short exact user phrase or resolvable source, then translate every compound request into **observable atoms** (`ADD`, `REMOVE`, `MOVE`, `RETAIN`, or `REPLACE`) stated as final product behavior. Map each atom to an acceptance ID or an explicit out-of-scope reason; do not create another context report or make the developer fill these fields.

## Frame one vertical slice

Choose the lane:

- `L0`: documentation or isolated non-behavioral/visual change.
- `L1`: normal feature, fix, or end-to-end user flow.
- `L2`: permissions, sensitive data, migration, payments, external integration, architecture, or production release.
- `Emergency`: smallest safe hotfix followed by evidence repair and incident review.

Create one task with an observable title. For a single task, stay in the current worktree. When another writing task must run concurrently, use `new ... --worktree auto`; never let two writing windows share one physical worktree.

For an ordinary independent task, do not create a DAG. If a complex requirement has real ordering constraints, first show one compact proposal containing task outcome, `Depends-On`, allowed scope, acceptance result, and parallel-ready nodes. After one user confirmation, create the isolated tasks with repeated `--depends-on`. The task contracts are the DAG; do not create a second planning tree.

Before mutating an existing task worktree, keep a stable `RIGORBREEZE_SESSION_ID` for the Codex window or pass `--session`. The runner blocks another live session from claiming the same worktree. Use `claim --release` only when handing that worktree to another window.

Complete the task's authoritative inputs, allowed and forbidden scope, acceptance IDs, test seams, commands, and only the conditional risks that apply. Allowed Scope uses repository-relative paths, prefixes, or globs; acceptance IDs are unique and machine-readable. Declare exclusive ports/services/processes/apps/environments in `Runtime-Claims` (`none` otherwise); conflicting active claims cannot be waived by scope approval. For conditional L2 integrations, map `enabled`, `disabled`, and `unavailable` in `Operational-Modes` to declared acceptance IDs. Split or order overlapping scopes; use overlap approval only for a reviewed file-scope exception.

Use existing domain glossaries and ADRs when they help decode terms or constrain a decision. Add a glossary entry or ADR only when a real term or durable decision has crystallized; never create a documentation tree speculatively.

Before approval, agree:

- which public interface or boundary the test exercises;
- which independent oracle proves the expected result;
- which production paths may change;
- which requirement/design version defines acceptance.

Before approval, perform one **semantic self-review** for placeholders, contradictions, oversized scope, and ambiguous outcome, source-of-truth, freshness, or fallback meaning. For negated wording such as “not shown”, “missing”, or “not changed”, distinguish a **current defect** from the **desired result** using project evidence; if evidence cannot decide, ask one short outcome question. For UI work, cover what must exist, must be absent, its order/location, and retained behavior. Show one compact **final-state checklist** before approval, repair recoverable facts directly, and ask only when ambiguity changes the result. Approve only after every atom is covered and scope, design, acceptance, plan, and test shape are stable. Its digest becomes the contract; changes invalidate downstream evidence. Do not reapprove over production implementation changes. Restore the approved contract and finish, or revert production changes before amending and reapproving the same outcome. Create a dependent task for a new user outcome or acceptance condition.

Before the first enforced L1/L2 approval, require `workflowBaseline.status=current` on the task's real base branch. If the user explicitly authorizes the isolated baseline commit shown by `nextAction`, use `automate commit --once --workflow-baseline --expected-head <sha>`; never mix product changes into it or treat a task-branch runner commit as the project baseline.

## Implement with evidence

For L1/L2/Emergency, observe RED before production implementation. L1/L2 require a real test file; Emergency may instead use a deterministic incident reproduction. RED must bind a declared acceptance ID, independent expected failure, command, exit code, baseline SHA, and file digests. Import errors, tool failures, unrelated failures, or a test that already passes are not RED. Source-string searches prove static contracts only, never user behavior or business logic.

Implement as tracer bullets:

1. one failing behavior;
2. minimum GREEN implementation through a public seam;
3. refactor while green;
4. run affected checks;
5. repeat for the next behavior.

Do not batch all tests, then all implementation. Do not derive the expected result by calling or duplicating the implementation under test.

For bugs, first build a tight feedback loop that is deterministic, fast, agent-runnable, and capable of turning red. Minimize the reproduction, rank falsifiable hypotheses, instrument only to distinguish them, remove temporary probes, then retain a regression test. After **three failed hypotheses** for the same defect, make an **architecture stop**: preserve evidence and re-examine boundaries, shared state, and assumptions before another patch.

Run one-off debugging or exploratory commands directly. Workflow validity comes only from configured profiles. A profile is the project's declared contract: every listed check must run, while unrelated capabilities stay outside the profile.

## Review and accept

Run two separate review passes so one does not mask the other:

1. **Standards pass:** correctness, simplicity, project conventions, security, maintainability, tests, and scope.
2. **Spec pass:** each acceptance ID, prototype state, API/data/permission contract, and forbidden scope.

A solo developer may perform both passes at different times with fresh context. Require a second human only when project policy or the real production risk calls for one. Treat **review feedback** as a hypothesis: verify it against the requirement, actual code use, compatibility constraints, tests, and YAGNI. Explain and reject advice that is wrong, excessive, or unused rather than implementing it because a reviewer proposed it.

Validate the real product, not only the build:

- UI: real runtime, key states, screenshots, accessibility, and Playwright visual evidence.
- Mini-app: formal build, developer-tool automation, real AppID/HTTPS environment, and device evidence.
- Migration: cloned-data rehearsal, assertions, backup/restore or forward-fix proof.
- Release, only when requested: one SHA/artifact across tests and UAT plus applicable governance. Before L2 remote writes, show the complete operation-plan stages and the one stage being executed; after pause/failure record the safe state and single resume action.

Before any external Git, deployment, developer-tool, or platform write, reconstruct the **observed current state** from the system itself. Summarize already completed steps, current immutable identifiers, the one remaining action, and stop conditions; never repeat a completed step from an old plan or chat summary.

Temporary or synthetic credentials prove buildability only; they cannot satisfy real-environment acceptance, deployment, or release evidence.

AI cannot approve its own visual baseline, security exception, legal conclusion, or production release.

## Parallel context and optional adapters

Use compact outputs and read only the next needed source. `status --all --json` is the project handoff: worktree, branch, phase, dependencies, readiness, scope, freshness, and deterministic next action. `doctor --all --json` diagnoses drift; use `doctor --all --repair --json` only to explicitly rebuild the disposable Git-common registry and clear stale locks.

For a large repository, an installed code-graph tool may help locate impact radius and affected tests only when its index reports the current Git SHA. Treat graph risk scores as hints, never as correctness gates or sources of truth.

External multi-agent tools may consume `status --all --json`, but they never become a second source of truth. The task Markdown, task evidence, Git, and the runner remain authoritative.

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

After refreshing the baseline, inspect the `cleanup` projection from `status --all --json`. Run `reconcile --cleanup` from a different worktree when managed entries are removable. Unregistered entries remain report-only unless the current user message explicitly authorizes the exact absolute path, base branch, expected HEAD, and `--allow-unmanaged`; require a clean non-current worktree with ancestry or complete patch-equivalence proof. Partial equivalence never qualifies, and local branches are always preserved.

Automation outcomes live in Git-private `.git/rigorbreeze/automation.json`, keyed
by immutable inputs. They are projected by JSON status, validated by `doctor`,
and never rewrite tracked task evidence after the external action.

## Evolve from real use

At every L1/L2/Emergency close, run the retrospective without asking the user to remember metrics. Runner drift, occupied tasks, resource conflicts, missing operation plans, and gate failures are deduplicated as task practice events. When the user corrects an interpretation (“I meant”, “you missed”, “understood it backwards”), classify the existing retrospective evidence as `requirement-interpretation-correction` with `missing-atom`, `reversed-intent`, `wrong-source`, or `scope-change`; never retain the chat transcript. Pass `none` when no human exception exists. Only a judged workflow rework, unreasonable block/next action, bypass, or `hurt` impact becomes an evolution candidate; correct blocks remain statistics.

When a candidate is emitted:

- tell the user it was recorded in the task evidence;
- show the copyable instruction `$rigorbreeze 汇总这个项目的演进候选`;
- observe the first ordinary occurrence; review the Skill after a second similar occurrence;
- review immediately if a gate incorrectly permits secrets, privilege bypass, destructive migration, stale evidence, or a wrong release;
- classify the cause as core, project configuration, adapter, environment, usage, or a correctly detected risk;
- for a confirmed core problem, write a failing regression, make the smallest change in the Skill repository, and validate it in the next real slice.

When asked to review evolution, scan `spec/evidence/*.json` for confirmations with `evolutionCandidate: true`; do not create another practice log. Project evidence stays local. Never silently rewrite the installed Skill or relax a gate from one ordinary occurrence.

## Completion

Keep the human interaction small:

1. ask for approval of the compact task contract;
2. ask for real acceptance when implementation is ready;
3. before L1/L2/Emergency archive, show the prefilled `retro --json` summary and ask only for rework reason, whether any block/next action was unreasonable, and whether the workflow helped.

Codex runs the CLI and records evidence; do not make the user operate each internal command. Close in this order: verify, accept, review, confirm retrospective, archive, then guarded commit/push/merge and worktree reconciliation. L0 needs only configured affected verification; L1/L2 need full verification, applicable acceptance, review, and retrospective. Use `abandoned` for a clean cancellation. If code was already externally integrated but the task remained open, use `archive --outcome reconciled --reason <reason> --expected-head <sha>` only after integration and external outcomes are proven; never invent GREEN, acceptance, or release success. Production release still requires an active `release-ready` task. Before commit, archive, or any “fixed/passed/complete” claim, cite **fresh verification** run in this turn: the exact command, **exit status**, and covered scope. Historical reports, partial checks, or another Agent's success claim cannot substitute.

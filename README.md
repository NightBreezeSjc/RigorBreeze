# RigorBreeze

**Production rigor, without process drag.**

An evidence-backed, risk-adaptive AI engineering workflow for solo developers using Codex.

[![Public Preview](https://img.shields.io/badge/status-Public%20Preview-f59e0b)](#public-preview-and-v10)
[![Skill CI](https://github.com/nightbreezesjc/rigorbreeze/actions/workflows/ci.yml/badge.svg)](https://github.com/nightbreezesjc/rigorbreeze/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776ab)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)

English · [简体中文](README.zh-CN.md)

RigorBreeze routes work by consequence: tiny safe edits go straight through a verified Direct lane, ordinary changes get compact private records, and production-risk work retains full evidence and public sanitized audit proof. It is deliberately smaller than a project-management system and keeps normal workflow mechanics out of product commits.

> **Public Preview:** v0.15.1 is usable today. It preserves the v0.15 reliability gates while reducing routine context load through a shorter Skill entrypoint, smaller managed project policy, and compact project-status projection. Active projects keep their installed runner frozen until the task closes.

## Why this exists

AI can produce code quickly while still building the wrong behavior, missing a design state, or passing tests that do not prove the user outcome. Chat history is also a weak source of truth across long projects and parallel Codex windows.

RigorBreeze moves human attention to the two places where it matters most:

```text
agree on the outcome and acceptance boundary
→ let Codex implement through observable feedback loops
→ accept the result in the real runtime
```

It adds auditable SDD, observed RED–GREEN–REFACTOR, project-declared checks, real acceptance, safe parallel worktrees, and optional protected Git automation without requiring a large Spec Tree.

## Is it for you?

Use it when you are:

- a solo developer using Codex App or Codex CLI;
- maintaining a product across multiple sessions or parallel Codex windows;
- shipping features where tests, design fidelity, permissions, migrations, or rollback matter;
- willing to approve a compact task contract and inspect the real result.

Skip it for:

- throwaway scripts and weekend prototypes where failure has little cost;
- teams looking for sprint planning, staffing, issue tracking, or an agent control plane;
- projects that cannot configure any real build, test, or acceptance command;
- workflows that expect AI to approve its own visual, security, legal, or production decisions.

Codex App and Codex CLI are the supported hosts. Other Agent Skills-compatible tools may load the Skill, but they are experimental until their installation and behavior are verified.

## 60-second install

Prerequisites: Git, Python 3.11 or newer, and Codex App or Codex CLI.

### Option A: Agent Skills installer

```bash
npx skills@latest add nightbreezesjc/rigorbreeze --skill rigorbreeze -g -a codex -y
```

The `skills` CLI is a third-party installer with its own telemetry policy. Set `DISABLE_TELEMETRY=1` for that command or use the manual method if you do not want installer telemetry.

Restart or reload Codex after installation.

### Option B: Git clone and copy

From the directory where you keep development tools:

```bash
git clone https://github.com/nightbreezesjc/rigorbreeze.git
mkdir -p ~/.codex/skills
cp -R rigorbreeze/rigorbreeze ~/.codex/skills/rigorbreeze
```

For local Skill development, use a symlink from a dedicated contributor checkout instead of the final copy command:

```bash
ln -s "$(pwd)/rigorbreeze/rigorbreeze" ~/.codex/skills/rigorbreeze
```

The outer directory is the repository; the inner directory is the installable Skill.

Treat installer-managed copies and a checkout pinned to a stable release as the normal user channel. A contributor checkout is intentionally live: do not pull updates into it when it has uncommitted changes or an active RigorBreeze task. Project Runner upgrades are separate from Skill installation; run them only when status reports `installation.status=outdated` and `upgradeSafe=true`. Active tasks keep their current Runner until they close.

### Verify the installation

Open a new Codex task in a Git project and enter:

```text
$rigorbreeze inspect this project and tell me whether the workflow is initialized
```

Codex should load the Skill, inspect the repository, and either report the current `nextAction` or offer to initialize the project.

## Shape an initiative before the first task

When an idea is a new product, a new business domain, a broad legacy migration,
or still contains several possible outcomes, ask RigorBreeze to shape it before
creating a delivery task:

```text
$rigorbreeze shape this initiative before creating a task. Recover project facts first; distinguish evidence, assumptions and unknowns; compare two or three viable approaches; cover the user journey, desired outcome, success measure, four product risks, appetite, rabbit holes and no-gos; recommend the first vertical slice and wait for my approval.
```

This is optional. A bounded feature or fix goes directly to the normal task
contract. Shaping reuses one versioned product/design source or creates one
compact initiative brief outside the Spec Tree. It does not manufacture a PRD
tree, implementation DAG, or product truth from a persona or reference code.
After recovering facts, RigorBreeze asks at most three current decision-frontier
questions per round, with a recommendation, reason, and result impact for each.
A disposable prototype answers one decision question and records its observation
and verdict; it is never production acceptance. After the frontier is resolved
and the brief is approved, only the first slice becomes a RigorBreeze task.

## Your first task

You normally interact with the Skill in Codex chat, not by operating every internal command yourself:

```text
$rigorbreeze initialize this project and develop a profile page where users can update their display name
```

Codex will:

1. inspect the current project and complete missing context from authoritative requirements, code, tests, Git and runtime evidence;
2. propose one observable task with scope, acceptance IDs, risk, and test seams;
3. use a clear current request as L1 approval, asking only when the intended result is still ambiguous;
4. observe RED for L1/L2 behavior, implement in small GREEN steps, and run configured checks;
5. show the real page, API, device, migration, or runtime evidence that applies;
6. ask for real acceptance where needed; clean first-pass L1 work closes automatically, while friction and L2/Emergency retain a human retrospective.

You judge only what cannot be automated safely: unresolved outcome choices, applicable real acceptance, and workflow friction or high-risk conclusions. Codex runs and records the internal mechanics.

RigorBreeze does not turn every conversation into a workflow task. Status questions, log explanations, screenshot analysis, recommendations, and other no-write diagnosis use the no-task path: answer first, report relevant drift separately, and never make workflow repair a prerequisite for a read-only result. When code must change, choose the lowest lane that still covers the consequence:

| Request | Default path |
|---|---|
| Explain state, logs, screenshots, or the next command | No task |
| Copy, isolated styling, simple display field, or low-consequence small bug | Direct: edit + targeted verification, no task |
| Low-risk multi-file change that still needs coordination or audit | L0 |
| Normal feature, fix, or observable behavior | L1 |
| Data, payment, permission, external integration, infrastructure, or production write | L2 |

Risk follows consequence, not line count, elapsed time, or how urgent the request sounds. If workflow preparation would cost more than a genuinely isolated L0 edit, Codex removes unrelated ceremony; it never downgrades an L2 consequence to save time.

You do not need to write a perfect prompt or prepend a persona such as “act as a unicorn CTO.” RigorBreeze recovers project facts, current behavior, architecture paths, invariants and data-freshness/fallback semantics itself. It asks only when evidence cannot determine an intent that would materially change the result. For external Git, deployment, developer-tool or platform writes, it first reports what is already completed, the current immutable identifiers, the one remaining action and stop conditions so an old checklist is not replayed.

Before approval, RigorBreeze checks the task for placeholders, contradictions, an oversized slice, and ambiguous outcome/source/fallback semantics. Compound requests become observable ADD/REMOVE/MOVE/RETAIN/REPLACE atoms, each mapped to acceptance or explicit exclusion. Before widening scope, it proves whether the defect is wrong/missing data, wrong config, or a missing capability, and keeps the minimal correction separate from optional prevention. For UI changes, the final-state checklist covers presence, absence, order/location, and retained behavior; negative wording is resolved as either a current defect or desired result from evidence, with one short question only when the direction remains outcome-changing. Unproven root cause stays labeled as a hypothesis until runtime evidence distinguishes it. Manual acceptance must name the real route/menu/role/account/device entry or say `N/A` with equivalent runtime/API evidence. After two identical login/token/browser/channel failures, the Skill stops repeating the same path, preserves a safe state, and switches method. When three or more related screens or a new visual language are involved, one visual tracer comes before fanout unless an approved component is reused exactly. Completion claims must name a fresh command, exit status, and covered scope. Review suggestions are checked against repository reality and YAGNI; speculative layers face a deletion test, while three failed hypotheses for the same defect trigger an architecture stop instead of a fourth patch. Maintainers validate these rules with sixteen synthetic Agent-pressure scenarios; the suite is not installed into user projects and never calls a model from CI.

Allowed Scope entries are repository-relative paths, directory prefixes, or globs; `*` matches one path segment and `**` crosses directories. Acceptance criteria use unique machine-readable IDs. A contract cannot be reapproved over production changes: restore the approved contract and finish, or revert those changes before amending the same outcome. A new user outcome or acceptance condition becomes a dependent slice.

After initialization and project-check configuration, establish a human-controlled Git baseline before creating a new L1/L2 task. `status --json` reports the exact base-branch state under `workflowBaseline`; Direct and L0 remain lightweight. When explicitly authorized, Codex may create the isolated baseline commit without mixing product changes or persisting Git authority. The installed Skill checks through its bundled v0.15.1 runner, reports missing or modified components separately, and does not overwrite it during implementation. A missing high-risk contract must be restored or replaced by an explicit Emergency contract, never an informal bypass.

After initialization, the project contains:

```text
spec/
├── index.md
└── evidence/TASK-002.audit.json  # sanitized L2/Emergency audit only

rigorbreeze.toml               # project checks and policy
scripts/rigorbreeze.py         # the same runner used locally and in CI
.git/rigorbreeze/state.json    # private state; never committed
.git/rigorbreeze/records/      # private contracts, evidence, archives, history
```

The expected next-action check is:

```bash
python3 scripts/rigorbreeze.py status --json
```

That command is primarily for Codex, CI, and troubleshooting. Run `python3 scripts/rigorbreeze.py --help` for the canonical CLI reference.

## How the workflow works

```text
classify read-only / Direct / L0 / L1 / L2 / Emergency
→ optionally shape an initiative whose outcome is not yet stable
→ frame one vertical slice
→ approve the task digest
→ observe RED
→ implement GREEN and refactor
→ run affected/full profiles
→ inspect the real runtime
→ review against standards and the spec
→ auto-close a clean L1 or confirm the applicable retrospective
→ archive
→ guarded commit/push/merge when requested
→ reconcile and clean integrated worktrees
```

Risk controls scale with the task:

| Lane | Typical change | Close requirement |
|---|---|---|
| Direct | One unambiguous low-consequence result | One targeted check; no task or evidence |
| L0 | Low-risk change needing coordination or audit | Configured affected checks |
| L1 | Normal feature, fix, or user flow | RED, full verification, acceptance, review, retrospective |
| L2 | Permissions, sensitive data, migration, payment, integration, release | L1 plus applicable security, migration, and release controls |
| Emergency | Smallest safe production hotfix | Reproduction, critical regression, rollback, evidence repair |

Archiving a completed task is not the same as releasing it. Artifact identity, canary, SLO, alerting, and rollback evidence are required only when a production release is actually requested.

Once a release starts, its approved operation scope is frozen. A newly discovered critical risk stops that release; an unrelated base-image, operating-system, database-engine, scanner, framework, or platform upgrade becomes a separate governance task. It is not silently inserted into a routine business deployment. Cross-task work is shown before execution with the destination task, observable result, allowed and forbidden scope, dependency or blocker, and owner.

For conditional L2 integrations, `Operational-Modes` binds enabled, disabled, and dependency-unavailable behavior to real acceptance IDs. Before an L2 release writes remotely, a machine JSON operation plan must identify the exact SHA/artifact, ordered backup/config/migration/deploy/accept/switch/observe stages, success and stop conditions, safe recovery points, and rollback limits. A paused or failed result records one safe state and one resume action instead of rerunning the whole release blindly.

## Minimal Spec Tree

Direct changes create no workflow files. Task-based work has at most one human-authored contract and one machine evidence record; requirements are linked rather than copied into a document maze.

The task contract records the current sources, machine-checkable allowed and forbidden scope, acceptance IDs, test seams, exclusive `Runtime-Claims`, conditional `Operational-Modes`, and applicable risks. The evidence JSON records approval digests, RED, checks, reports, acceptance, artifact identity, release-operation snapshots, and retrospective facts. Changes to relevant source, tests, configuration, dependencies, migrations, or the task digest invalidate stale proof automatically. Additional all-green verification refreshes machine statistics without asking for the same retrospective judgment again; changed task/code facts, failures, acceptance, bypasses, or practice events still invalidate that judgment. `status --json` also projects installation and scope drift, so an old runner or a change outside the contract cannot be hidden by a passing verification.

Version-5 projects default to Git-common private records under `.git/rigorbreeze/records/`, readable from every worktree but absent from product commits. Integrated L1 detail is reduced to a path-free local history summary. L2/Emergency keeps full private proof and, when configured, publishes a sanitized `.audit.json` capped at 32 KiB with task/risk, acceptance IDs, immutable digests, conclusions, and honest `Tested`/`Not-tested`—never absolute paths, raw output, credentials, or production data. Explicit `tracked` mode remains available for teams and cross-machine evidence.

Legacy v2-v4 projects keep tracked behavior until an explicit, idle, clean migration runs: `doctor --all --repair --migrate-records private`. Upgrading the Runner never silently moves or deletes historical evidence.

See the installable Skill's [Spec Tree contract](rigorbreeze/references/spec-tree.md) for authority and invalidation rules.

## Safety and privacy defaults

- Local checks default to advisory; CI, L2, merge, and release use enforced policy.
- Git automation defaults to `manual`: no unattended Git write is allowed, while an explicit current-task request may authorize one safe commit or push without changing the project level. Upgrades never increase standing authority.
- No force push or local merge is used to bypass protected branches.
- Managed cleanup requires provenance, exact path, integration, and cleanliness. It may safely remove a contained local task branch with `git branch -d` only when no remote uncertainty exists; every other branch/worktree is retained with a reason. Remote branches are never deleted automatically.
- A cancelled or superseded task may be archived as `abandoned` only when its task-owned working tree is clean and no external action has an unknown outcome; this releases its task and runtime claims without deleting its branch or worktree.
- Workflow policy files such as `AGENTS.md`, `rigorbreeze.toml`, and the runner must be explicitly included in Allowed Scope when a task changes them.
- External-action recovery data stays in Git-private `.git/rigorbreeze/automation.json`.
- Private records stay in the project's Git common directory. The Skill has no telemetry and does not upload source, prompts, evidence, or metrics.
- Secrets, credentials, production data, and sensitive full logs must never be stored in task evidence.
- Temporary or synthetic credentials may prove buildability only; they cannot satisfy real-environment acceptance, deployment, or release evidence.
- AI cannot approve its own visual baseline, security exception, legal conclusion, or production release.

The Skill coordinates external security, migration, CI, browser, device, and observability tools through project configuration; it does not pretend that an internal placeholder check is equivalent to those tools.

## Parallel work and optional automation

One physical worktree may have only one active writing task. Risk chooses the gates, each non-Direct independent outcome gets a short-lived branch, and only a concurrent writer or disposable risky experiment gets another worktree. After one task is closed and integrated, the same window reuses its clean checkout by returning to the current base and starting a fresh task branch; only explicitly related sequential slices reuse a designated integration branch. When another Codex window must write concurrently, the Skill creates an isolated `rigorbreeze/<task-id>` branch and worktree. File isolation does not make ports, watchers, local services, environments, or developer tools independent: tasks declare only the exclusive resources they use through `Runtime-Claims`, and conflicting active claims are blocked.

Routine work reads only current-worktree `status --json` and may reuse that snapshot during one uninterrupted write phase while repository and external state stay unchanged. Parallel coordination uses `status --all --compact --json`, which retains active tasks, blockers, dependencies, worktree ownership, and deterministic next actions while replacing historical cleanup detail with counts. Successful checks are summarized by command, exit status, covered scope, and report digest; raw output is loaded only for bounded failure diagnosis. The original `status --all --json` remains unchanged for exact repair, cleanup, and evolution review, so the context optimization does not weaken machine checks or remove evidence.

The same status payload exposes removable, retained, and unregistered worktrees with cleanliness, integration proof, expected HEAD, and confirmation requirements. RigorBreeze recognizes ancestor merges and complete patch-equivalent cherry-picks. For a registered task, extra commits qualify only when they contain a narrow allowlist of workflow metadata and at least one product patch is already equivalent on the base; mixed or unmatched product changes remain active. Cleanup normally removes only clean worktrees with intact creation provenance. A precisely authorized unmanaged cleanup uses the original conservative proof and preserves the local branch.

Independent tasks do not get a DAG. When real ordering exists, Codex proposes a compact dependency graph once and stores it only through each task's `Depends-On` field. That field is repository-local; cross-repository tasks link their counterpart contract and API/data contract under Authoritative inputs, and a consumer cannot complete real acceptance before the provider is integrated and verified. Cycles, missing dependencies, overlapping allowed scopes, stale baselines, and duplicate live claims are blocked.

Projects may explicitly raise `[automation].level` through:

```text
manual → commit → push → merge → release
```

Each level includes the earlier one, remains task-scoped, and must pass its configured gates. Merge and release use protected provider adapters; production migration and rollback always require separate authority.

`manual` is not a ban on a user's explicit delivery request. When the user clearly asks to commit or push the current task, Codex may use one-time authorization after showing the exact repository, remote, branch, and HEAD. A one-time push fetches first, requires an unchanged expected HEAD, permits only a fast-forward update, never force-pushes, verifies the remote SHA afterward, and does not persist authority. Direct integration-branch delivery additionally requires current full verification, acceptance, and review. Merge, release, production migration, and rollback never inherit this one-time authority.

## Configure checks and CI

Start with one bundled adapter:

- `rigorbreeze/assets/config/generic.toml`;
- `rigorbreeze/assets/config/java-vue-uniapp.toml`.

Copy the GitHub Actions or GitLab CI template from `rigorbreeze/assets/ci/`, then configure the commands your project actually uses in `rigorbreeze.toml`. A declared profile item must exist and pass in enforced mode; unrelated capabilities do not require `N/A` paperwork. For L2, `full` always derives a minimum of secrets, build, one static-quality check, and one behavioral check. Dependency changes additionally require dependency, license, and SBOM reports; migration changes require the migration adapter and report.

The remote required pipeline—not a local hook—is the merge authority. On a clean CI checkout, enforced `verify --profile full` can run configured checks without private task records; that stateless result is a Required Check only and cannot impersonate task acceptance, archive, merge evidence, or a production release.

## Update and uninstall

Installer-managed copies can be refreshed with the installer:

```bash
npx skills@latest update rigorbreeze -g -y
```

For a manual copy, pull the repository and replace only the installed `~/.codex/skills/rigorbreeze` directory with the updated inner Skill. Symlink installations update with the repository checkout.

To uninstall an installer-managed copy:

```bash
npx skills@latest remove rigorbreeze -g -a codex -y
```

For a manual install, remove only the `rigorbreeze` directory or symlink from your Codex skills directory. Existing project configuration, runner, private records, and audit summaries are intentionally left untouched.

## Public Preview and v1.0

v0.15.1 keeps every v0.15.0 consequence, TDD, acceptance, and delivery gate. It changes only context routing: the activated Skill entrypoint is shorter, current-task status is the default, and parallel coordination can request a compact backward-compatible projection without changing the full status response. Public CLI command count and third-party dependencies do not change; state/config remains schema v5 while full evidence remains schema v4.

The v0.12.0 decision-frontier, one-question prototype, and abstraction-deletion contracts remain part of this release.

Before v1.0, the workflow must complete and learn from:

- one normal L1 vertical slice;
- one high-risk L2 slice involving permissions, migration, or release governance;
- one real two-worktree parallel delivery;
- one real dependency DAG with at least three nodes;
- remote required CI and protected delivery exercises;
- one applicable canary, monitoring, and rollback exercise.

The evidence must show that `nextAction`, affected/full selection, invalidation, gates, and retrospective capture reduce rework and escaped risk without turning development into form filling. See [the Chinese maintainer evolution guide](Skill演进与实践记录.md) for the current evidence protocol.

## Repository workflow

RigorBreeze uses [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow), not a permanent Git Flow hierarchy:

```text
up-to-date main
→ one short-lived branch for one outcome
→ focused commits
→ pull request to main
→ required CI and maintainer decision
→ squash or rebase merge
→ delete the merged branch
```

Use a descriptive prefix such as `feat/`, `fix/`, `docs/`, `refactor/`, or `test/`; for example, `docs/clarify-installation`. A `release/vX.Y.Z` branch is created only while a real release candidate needs stabilization. The project does not keep empty `develop`, `hotfix`, or release branches: `main` is the only long-lived source of truth, while topic branches are cheap, isolated, and disposable.

External contributors fork the repository and open a pull request against `main`. The maintainer decides whether and when it is merged; passing CI is necessary but does not merge or publish a change by itself. See [CONTRIBUTING.md](CONTRIBUTING.md) for the copyable workflow and verification contract.

## Contributing and security

Read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing workflow behavior. Ordinary friction must repeat in real slices before entering the core; a gate that incorrectly permits a secret, privilege bypass, destructive migration, stale proof, or wrong release is reviewed immediately.

Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md). Do not place secrets or exploit details in public issues.

Changes are recorded in [CHANGELOG.md](CHANGELOG.md). The project is available under the [MIT License](LICENSE).

## Design influences

RigorBreeze is an independent project informed by:

- [GitHub Spec Kit](https://github.com/github/spec-kit) for spec-driven alignment;
- [OpenSpec](https://github.com/Fission-AI/OpenSpec) for lightweight change-oriented SDD;
- [Superpowers](https://github.com/obra/superpowers) for composable engineering disciplines and evidence before completion;
- [mattpocock/skills](https://github.com/mattpocock/skills) for small, adaptable skills and explicit feedback loops;
- [Wu5 Dev Flow](https://github.com/WenOwen/wu5-dev-flow) for auditable task state, TDD evidence, and Git gates.

Ideas were adapted to a solo Codex workflow with a minimal Spec Tree, project-declared enforcement, real-runtime acceptance, isolated parallel worktrees, and manual-by-default delivery. This project is not affiliated with or a drop-in replacement for any project above.

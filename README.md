# RigorBreeze

**Production rigor, without process drag.**

An evidence-backed, risk-adaptive AI engineering workflow for solo developers using Codex.

[![Public Preview](https://img.shields.io/badge/status-Public%20Preview-f59e0b)](#public-preview-and-v10)
[![Skill CI](https://github.com/nightbreezesjc/rigorbreeze/actions/workflows/ci.yml/badge.svg)](https://github.com/nightbreezesjc/rigorbreeze/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776ab)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-22c55e)](LICENSE)

English · [简体中文](README.zh-CN.md)

RigorBreeze turns a conversation into one approved task contract, observed TDD evidence, configured quality checks, real-runtime acceptance, and a recoverable delivery record. It is deliberately smaller than a full project-management system: one task Markdown, one machine evidence file, and no document maze.

> **Public Preview:** v0.8.0 is usable today and closes real-delivery gaps around workflow baselines, stale integrated tasks, post-archive delivery, and safe review of unmanaged worktrees. It has not yet completed the validation required for v1.0, so interfaces may still change in response to further delivery evidence.

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

For local Skill development, use a symlink instead of the final copy command:

```bash
ln -s "$(pwd)/rigorbreeze/rigorbreeze" ~/.codex/skills/rigorbreeze
```

The outer directory is the repository; the inner directory is the installable Skill.

### Verify the installation

Open a new Codex task in a Git project and enter:

```text
$rigorbreeze inspect this project and tell me whether the workflow is initialized
```

Codex should load the Skill, inspect the repository, and either report the current `nextAction` or offer to initialize the project.

## Your first task

You normally interact with the Skill in Codex chat, not by operating every internal command yourself:

```text
$rigorbreeze initialize this project and develop a profile page where users can update their display name
```

Codex will:

1. inspect the current project and its authoritative requirements;
2. propose one observable task with scope, acceptance IDs, risk, and test seams;
3. ask you to approve that compact contract;
4. observe RED for L1/L2 behavior, implement in small GREEN steps, and run configured checks;
5. show the real page, API, device, migration, or runtime evidence that applies;
6. ask you to accept the result and confirm one prefilled retrospective before archive.

You make three kinds of judgment: approve the intended outcome, accept the real result, and confirm whether the workflow helped. Codex runs and records the internal workflow commands.

Allowed Scope entries are repository-relative paths, directory prefixes, or globs; `*` matches one path segment and `**` crosses directories. Acceptance criteria use unique machine-readable IDs. A contract cannot be reapproved over production changes: restore the approved contract and finish, or revert those changes before amending the same outcome. A new user outcome or acceptance condition becomes a dependent slice.

After initialization and project-check configuration, establish a human-controlled Git baseline before the first enforced L1/L2 approval. `status --json` reports the exact base-branch state under `workflowBaseline`. When the user explicitly authorizes it, Codex may run `automate commit --once --workflow-baseline --expected-head <SHA>`; it stages only managed workflow files, rejects mixed product changes and secrets, and does not persist Git authority. The installed Skill always checks through its bundled v0.8.0 runner, reports missing or modified components separately, and does not overwrite it while an implementation task is active.

After initialization, the project contains:

```text
spec/
├── index.md
├── changes/TASK-001.md       # the only human-authored task contract
├── evidence/TASK-001.json    # machine evidence and freshness
└── archive/

rigorbreeze.toml               # project checks and policy
scripts/rigorbreeze.py         # the same runner used locally and in CI
.git/rigorbreeze/state.json    # private state; never committed
```

The expected next-action check is:

```bash
python3 scripts/rigorbreeze.py status --json
```

That command is primarily for Codex, CI, and troubleshooting. Run `python3 scripts/rigorbreeze.py --help` for the canonical CLI reference.

## How the workflow works

```text
frame one vertical slice
→ approve the task digest
→ observe RED
→ implement GREEN and refactor
→ run affected/full profiles
→ inspect the real runtime
→ review against standards and the spec
→ confirm the prefilled retrospective
→ archive
→ guarded commit/push/merge when requested
→ reconcile and clean integrated worktrees
```

Risk controls scale with the task:

| Lane | Typical change | Close requirement |
|---|---|---|
| L0 | Documentation or isolated non-behavioral change | Configured affected checks |
| L1 | Normal feature, fix, or user flow | RED, full verification, acceptance, review, retrospective |
| L2 | Permissions, sensitive data, migration, payment, integration, release | L1 plus applicable security, migration, and release controls |
| Emergency | Smallest safe production hotfix | Reproduction, critical regression, rollback, evidence repair |

Archiving a completed task is not the same as releasing it. Artifact identity, canary, SLO, alerting, and rollback evidence are required only when a production release is actually requested.

For conditional L2 integrations, `Operational-Modes` binds enabled, disabled, and dependency-unavailable behavior to real acceptance IDs. Before an L2 release writes remotely, a machine JSON operation plan must identify the exact SHA/artifact, ordered backup/config/migration/deploy/accept/switch/observe stages, success and stop conditions, safe recovery points, and rollback limits. A paused or failed result records one safe state and one resume action instead of rerunning the whole release blindly.

## Minimal Spec Tree

Each change has one human-authored Markdown contract and one machine JSON evidence file. Requirements are linked, not copied into proposal, design, plan, test-plan, and report documents.

The task contract records the current sources, machine-checkable allowed and forbidden scope, acceptance IDs, test seams, exclusive `Runtime-Claims`, conditional `Operational-Modes`, and applicable risks. The evidence JSON records approval digests, RED, checks, reports, acceptance, artifact identity, release-operation snapshots, and retrospective facts. Changes to relevant source, tests, configuration, dependencies, migrations, or the task digest invalidate stale proof automatically. `status --json` also projects installation and scope drift, so an old runner or a change outside the contract cannot be hidden by a passing verification.

See the installable Skill's [Spec Tree contract](rigorbreeze/references/spec-tree.md) for authority and invalidation rules.

## Safety and privacy defaults

- Local checks default to advisory; CI, L2, merge, and release use enforced policy.
- Git automation defaults to `manual`: no unattended Git write is allowed, while an explicit current-task request may authorize one safe commit or push without changing the project level. Upgrades never increase standing authority.
- No force push or local merge is used to bypass protected branches.
- Managed worktree cleanup requires creation provenance, exact path, integration, and cleanliness. An unmanaged worktree remains report-only unless the user explicitly supplies its absolute path, base branch, expected HEAD, and one-time `--allow-unmanaged`; the branch is always preserved.
- A cancelled or superseded task may be archived as `abandoned` only when its task-owned working tree is clean and no external action has an unknown outcome; this releases its task and runtime claims without deleting its branch or worktree.
- Workflow policy files such as `AGENTS.md`, `rigorbreeze.toml`, and the runner must be explicitly included in Allowed Scope when a task changes them.
- External-action recovery data stays in Git-private `.git/rigorbreeze/automation.json`.
- Project evidence stays in the project. The Skill has no telemetry and does not upload source, prompts, evidence, or metrics.
- Secrets, credentials, production data, and sensitive full logs must never be stored in task evidence.
- Temporary or synthetic credentials may prove buildability only; they cannot satisfy real-environment acceptance, deployment, or release evidence.
- AI cannot approve its own visual baseline, security exception, legal conclusion, or production release.

The Skill coordinates external security, migration, CI, browser, device, and observability tools through project configuration; it does not pretend that an internal placeholder check is equivalent to those tools.

## Parallel work and optional automation

One physical worktree may have only one active writing task. When another Codex window must write concurrently, the Skill creates an isolated `rigorbreeze/<task-id>` branch and worktree. File isolation does not make ports, watchers, local services, environments, or developer tools independent: tasks declare only the exclusive resources they use through `Runtime-Claims`, and conflicting active claims are blocked. `status --all --json` is the shared read-only project view.

The same status payload exposes removable, retained, and unregistered worktrees with cleanliness, integration proof, expected HEAD, and confirmation requirements. RigorBreeze recognizes both ancestor merges and complete patch-equivalent cherry-picks, never treats a partial patch set as integrated, and normally removes only clean worktrees with intact creation provenance. A precisely authorized unmanaged cleanup uses the same proof and preserves the local branch.

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

The remote required pipeline—not a local hook—is the merge authority. The repository's own workflow tests the Skill across its declared Python and operating-system matrix once GitHub Actions runs on the public repository.

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

For a manual install, remove only the `rigorbreeze` directory or symlink from your Codex skills directory. Existing project `spec/`, runner, evidence, and configuration are intentionally left untouched.

## Public Preview and v1.0

v0.8.0 keeps the minimal Spec Tree and existing command surface while moving all worktree state into Git-private storage, proving the workflow baseline on the real base branch, prioritizing `integrated-unclosed` and `closure-pending` lifecycles, and permitting guarded delivery after archive. Historical reconciliation records missing proof honestly; it never fabricates GREEN, acceptance, or release success. Maturity beyond preview must still come from repeated real use rather than more features.

Before v1.0, the workflow must complete and learn from:

- one normal L1 vertical slice;
- one high-risk L2 slice involving permissions, migration, or release governance;
- one real two-worktree parallel delivery;
- one real dependency DAG with at least three nodes;
- remote required CI and protected delivery exercises;
- one applicable canary, monitoring, and rollback exercise.

The evidence must show that `nextAction`, affected/full selection, invalidation, gates, and retrospective capture reduce rework and escaped risk without turning development into form filling. See [the Chinese maintainer evolution guide](Skill演进与实践记录.md) for the current evidence protocol.

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

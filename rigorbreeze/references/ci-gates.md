# CI Gate Integration

English · [简体中文](ci-gates.zh-CN.md)

## Contents

- [Principle](#principle)
- [Minimum pipeline](#minimum-pipeline)
- [GitLab](#gitlab)
- [GitHub Actions](#github-actions)
- [Artifact identity](#artifact-identity)
- [Enforcement boundary](#enforcement-boundary)

## Principle

Keep policy in `scripts/rigorbreeze.py` plus `rigorbreeze.toml` and call the same
runner locally and in CI. CI configuration orchestrates jobs; it must not become
a second workflow specification.

## Minimum pipeline

```text
doctor
→ optional `profiles.preflight = ["environment"]`
→ `--mode enforced verify --profile full`
  → project-declared static and behavior checks
  → applicable security/supply-chain checks
  → applicable migration checks
  → configured build/runtime checks
→ `check merge` or protected `check release`
```

An enforced profile contains the checks the project declares for that profile,
and every declared check must be configured and pass. L0/L1 remain
project-declared. L2 `full` derives a minimum of `secret`, `build`, at least one
static-quality check, and at least one behavioral check. Dependency-manifest
changes additionally require `dependency`, `license`, and `sbom` with non-empty
reports; migration changes require `migration` with its report. Destructive-migration
policy scans only migration files in the active task change set, never unchanged
historical SQL. Browser UI and
other unrelated capabilities remain conditional and require no N/A paperwork.
Required failures block merge and release.

An ordinary task commit is a narrower checkpoint: it requires current configured `affected` or `full` evidence, and never accepts targeted exploration. On a clean CI checkout without Git-private task records, enforced `verify --profile full` runs the configured checks statelessly. That result is a Required Check only: it cannot satisfy local task acceptance, archive, merge evidence, or release governance. Maintainer live Agent behavior runs are release-candidate evidence only and are never invoked by commit, configured `full`, or CI.

Inside one profile invocation only, an identical argv, resolved cwd, effective environment, and timeout executes once. Reusing the process does not reuse policy: each check independently validates its report and artifacts and records `reusedFromCheckId`.

Once a successful `full` result is bound to the unchanged task digest, project fingerprint, configuration digest, and HEAD, later `verify`, archive, commit, and merge gates reuse it. An explicit `verify --force` is the only unchanged-fingerprint rerun. A workflow phase transition alone never reruns `full`; code, contract, ownership, configuration, or external-state change invalidates the snapshot and only the affected repository repeats verification. Environment preflight failures are tooling facts, not RED or business rework.

## GitLab

Adapt `assets/ci/gitlab-ci.yml` into the existing `.gitlab-ci.yml`. Configure
the actual project commands in `rigorbreeze.toml`; the YAML calls the policy
runner directly and contains no second command registry. Preserve evidence, reports, screenshots, migration
logs, SBOM, artifact digests, and sanitized high-risk audit summaries when the project publishes them. Do not upload Git-private records.

Use protected branches/environments, required pipelines, environment-scoped secrets, and manual production approval. Do not place credentials in YAML.

## GitHub Actions

Adapt `assets/ci/github-actions.yml` into
`.github/workflows/production-flow.yml`. Require the named full-profile job,
block direct pushes to main, and protect production with manual approval. Use
OIDC or repository/environment secrets; do not embed tokens.

## Artifact identity

Build once and promote the same immutable artifact. Structured acceptance and
release records automatically bind the current artifact SHA-256. Record Git
SHA, dependency lock digest, configuration version, migration set,
image/package digest, CI run, and release observation. Rebuilding separately
for production breaks the evidence chain.

For L2 remote delivery, `check release` also requires a current machine JSON
`operation-plan`. It binds the target environment, Git SHA, artifact digests,
ordered backup/config-freeze/migration/deploy/acceptance/switch/observe stages,
per-step success conditions, stop conditions, safe recovery points, and
rollback limitations. After execution, store an `operation-result`; paused or
failed work has one safe-state description and one resume action. CI remains a
gate and artifact carrier, not a resident deployment state machine.

The approved release profile and operation scope are frozen before remote writes. A newly discovered critical risk stops the candidate. Unrelated base-image, operating-system, database-engine, scanner, framework, or platform upgrades require a separate governance task and their own verification; a routine business release must not silently grow new security or infrastructure work while running.

## Enforcement boundary

Local mode defaults to advisory. Local hooks can remind but are not the
authority. Remote required checks and protected environments are the
non-bypassable merge/release boundary.

The built-in staged-content heuristic may ignore a same-line `rigorbreeze: synthetic-secret` marker only below configured test paths. This never exempts secret-like file paths or project-configured Gitleaks/secret adapters, which remain authoritative. The optional temporary-RSA adapter may satisfy a configured build command with a disposable matched key pair, but its `synthetic-build-only` result is not runtime, acceptance, deployment, or release authority.

Before the first enforced L1/L2 approval, `workflowBaseline.status` must be
`current` on the configured base branch. A task-branch runner commit is not a
substitute. With explicit one-time user authorization,
`automate commit --once --workflow-baseline --expected-head <sha>` may establish
or update that baseline only when the base worktree contains no active task,
unrelated changes, cache, or secret material.

Every L1/L2 approval, advisory or enforced, also requires a clean task
worktree. Only task-owned records and Git-private state are exempt. Unignored
caches and foreign product changes block before baseline creation; CI cannot
repair or reinterpret a mixed local task after the fact.

`[automation].level` is an explicit project authorization boundary:

- `manual` grants no unattended Git write; an explicit current-message request may authorize one guarded commit or push without changing the level;
- `commit` and `push` are limited to the task scope and `rigorbreeze/<task-id>`;
- `merge` must run configured provider required-check and auto-merge adapters;
- `release` must run configured provider/environment check and release adapters.

The core never performs a local merge around branch protection, force-pushes,
stores provider credentials, or treats commit/push authority as permission for
production migration or rollback. Provider and release adapters use argv arrays
and inherit credentials from Git, CI, OIDC, or the platform environment.

A one-time push requires an explicit remote, the current branch, and the exact
expected HEAD. It fetches the target, rejects a remote-ahead or diverged history,
and verifies the resulting remote SHA. Direct integration-branch push also
requires current full verification, structured acceptance, and review. One-time
authority never extends to merge, release, migration, or rollback.

Optional advisory hooks are under `assets/hooks/`. Copy them to a project-owned
hooks directory and enable that directory deliberately; initialization does not
change Git configuration.

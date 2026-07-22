# Codex Production Flow

A production-oriented Codex Skill that connects one active specification, observed TDD evidence, real runtime acceptance, Git gates, CI, release operations, and cross-session state without creating a document maze.

## What it adds

- one human-authored task specification per change;
- approval digests that invalidate after scope or acceptance changes;
- recorded RED with expected-failure matching;
- verification fingerprints bound to project content and Git;
- secret, dependency, migration, commit, and release gates;
- runtime, independent review, security, migration, second-human, and incident evidence;
- a minimal, archivable Spec Tree;
- GitLab CI and GitHub Actions starting templates.

It does not replace product judgment, design approval, security/legal review, real-device testing, production approval, monitoring, or incident response.

## Repository layout

```text
codex-production-flow/
├── README.md
└── codex-production-flow/
    ├── SKILL.md
    ├── agents/openai.yaml
    ├── scripts/flow.py
    ├── scripts/tests/test_flow.py
    ├── references/
    │   ├── handbook.md
    │   ├── spec-tree.md
    │   └── ci-gates.md
    └── assets/ci/
```

The inner `codex-production-flow/` directory is the installable Skill. The outer directory is the GitHub repository.

## Install locally

Clone the repository, then copy or symlink the inner Skill directory into the Codex skills directory:

```bash
cp -R codex-production-flow/codex-production-flow ~/.codex/skills/
```

Restart or reload Codex, then invoke:

```text
$codex-production-flow initialize this project and create its first production task
```

## Generated project structure

Initialization creates:

```text
spec/
├── index.md
├── state.json
├── changes/TASK-001.md
├── evidence/TASK-001.json
└── archive/

scripts/codex-flow.py
```

The repository-owned runner allows local development and CI to use the same policy implementation.

## Core commands

```bash
python3 scripts/codex-flow.py init
python3 scripts/codex-flow.py doctor
python3 scripts/codex-flow.py new TASK-001 --title "User outcome" --risk L1
python3 scripts/codex-flow.py approve task
python3 scripts/codex-flow.py red --requirement REQ-001 --expect-pattern "expected failure" -- <test command>
python3 scripts/codex-flow.py check implement
python3 scripts/codex-flow.py verify --scope affected -- <verification command>
python3 scripts/codex-flow.py attest runtime --evidence <artifact-or-reference>
python3 scripts/codex-flow.py attest review --evidence <artifact-or-reference>
python3 scripts/codex-flow.py check commit
python3 scripts/codex-flow.py check release
python3 scripts/codex-flow.py archive
```

## Validate the Skill

```bash
python3 -m unittest discover -s codex-production-flow/scripts/tests -v
python3 <skill-creator>/scripts/quick_validate.py codex-production-flow
```

Before publishing publicly, choose the repository visibility and an explicit software license. Absence of a license does not grant open-source reuse rights.

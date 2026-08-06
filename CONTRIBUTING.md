# Contributing

English · [简体中文](CONTRIBUTING.zh-CN.md)

Thank you for helping make RigorBreeze safer, smaller, and easier to use.

## Before proposing a change

- Open a focused issue or discussion describing the observed failure, affected task, and user cost.
- Prefer fixing project configuration or a stack adapter when the core workflow is behaving correctly.
- Do not add a permanent core capability for a hypothetical use case.
- Keep public behavior compatible unless the safety or friction evidence justifies a change.

Ordinary workflow friction should appear in at least two real vertical slices before it changes the core. One occurrence is enough when a gate incorrectly permits secrets, privilege bypass, destructive migration, stale evidence, an unauthorized Git action, or a wrong release.

## Development setup

Requirements: Git and Python 3.11 or newer. Runtime code uses the Python standard library; repository quality checks may also use Ruff.

Run the regression suite:

```bash
python3 -m unittest discover -s rigorbreeze/scripts/tests -v
```

Run the repository's configured static checks when Ruff is available:

```bash
python3 -m ruff format --check rigorbreeze/scripts
python3 -m ruff check rigorbreeze/scripts
python3 -m py_compile rigorbreeze/scripts/flow.py
```

Validate the installable Skill with Codex's `skill-creator` validator:

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py rigorbreeze
```

Validate the offline Agent-behavior contract and scorer:

```bash
python3 -B tests/behavior/run.py validate
python3 -B -m unittest discover -s tests/behavior -v
```

Before a release candidate, run every synthetic scenario twice with a locally installed Codex. This is an explicit maintainer action; ordinary commits, configured `full`, and CI never invoke it:

```bash
python3 -B tests/behavior/run.py run --version 0.9.2 --repetitions 2
```

Any hard-rule failure blocks the candidate. Inspect only the redacted Git-private results under `.git/rigorbreeze/behavior-evals/0.9.2/`; do not commit them or use real credentials and services in a fixture.

## Change rules

1. Add or identify a failing regression that represents the real problem.
2. Make the smallest change that fixes that failure.
3. Preserve one task Markdown plus one evidence JSON as the task source of truth.
4. Do not add dependencies, public CLI commands, Spec file types, or default automation levels without evidence and explicit design review.
5. Keep `SKILL.md` compact and move detailed policy into an existing reference.
6. Verify the full suite and a clean temporary-project flow before submitting.

Documentation changes should keep the English and Chinese onboarding contracts aligned. Do not copy repository-facing README, changelog, contribution, license, or security files into the installable Skill folder.

## Pull requests

RigorBreeze has one long-lived branch: `main`. Start each unrelated outcome from an up-to-date `main` and use a short-lived branch:

```bash
git switch main
git pull --ff-only
git switch -c docs/clarify-installation
```

Use `feat/`, `fix/`, `docs/`, `refactor/`, or `test/` followed by a short kebab-case description. Maintainers may open `release/vX.Y.Z` while stabilizing a real release candidate. Do not create permanent `develop`, `hotfix`, or empty release branches.

Keep one branch and pull request focused on one observable outcome. Push the branch, then open a pull request against `main`:

```bash
git push -u origin docs/clarify-installation
gh pr create --base main --head docs/clarify-installation
```

Explain the problem, evidence, chosen boundary, rejected alternative, compatibility impact, and exact verification run. Resolve review conversations and keep required CI green. Passing checks does not grant merge or release authority; the maintainer makes the final decision. After merge, delete the topic branch rather than reusing it for unrelated work.

AI-generated contributions are welcome when the submitter has reviewed and tested them; name the agent and model in the pull request description.

By contributing, you agree that your contribution is licensed under the repository's [MIT License](LICENSE).

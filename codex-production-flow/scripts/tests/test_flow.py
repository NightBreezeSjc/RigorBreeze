from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


FLOW = Path(__file__).resolve().parents[1] / "flow.py"


class FlowCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_flow(self, *args: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            self.flow_command(*args),
            text=True,
            encoding="utf-8",
            capture_output=True,
        )
        if result.returncode != expected:
            self.fail(
                f"flow command returned {result.returncode}, expected {expected}\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def flow_command(self, *args: str) -> list[str]:
        return [sys.executable, str(FLOW), "--root", str(self.root), *args]

    def init_git(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Flow Tests"], cwd=self.root, check=True)
        (self.root / "README.md").write_text("fixture\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.root, check=True)

    def complete_task(self, task_id: str = "TASK-001") -> Path:
        task = self.root / "spec" / "changes" / f"{task_id}.md"
        task.write_text(
            f"""# {task_id}: Deliver one observable outcome

Risk: L1

## Authoritative inputs
- Requirement: fixture requirement v1
- Design: fixture design v1

## Allowed scope
- app.py
- tests/

## Forbidden scope
- production credentials

## Acceptance criteria
- REQ-001: command returns the expected result

## Verification commands
- python -m unittest

## Runtime and release
- Runtime evidence: local fixture
- Rollback: revert the atomic commit
""",
            encoding="utf-8",
        )
        return task

    def test_init_creates_minimal_spec_tree_and_is_idempotent(self) -> None:
        self.run_flow("init")
        self.run_flow("init")

        self.assertTrue((self.root / "spec" / "index.md").is_file())
        self.assertTrue((self.root / "spec" / "state.json").is_file())
        self.assertTrue((self.root / "spec" / "changes").is_dir())
        self.assertTrue((self.root / "spec" / "evidence").is_dir())
        self.assertTrue((self.root / "spec" / "archive").is_dir())
        self.assertTrue((self.root / "scripts" / "codex-flow.py").is_file())

        state = json.loads((self.root / "spec" / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["phase"], "baseline")
        self.assertIsNone(state["activeTask"])

    def test_init_updates_an_existing_managed_runner(self) -> None:
        self.run_flow("init")
        runner = self.root / "scripts" / "codex-flow.py"
        runner.write_text(
            '#!/usr/bin/env python3\n"""Deterministic gates for Codex Production Flow."""\n# old\n',
            encoding="utf-8",
        )

        self.run_flow("init")

        self.assertEqual(runner.read_text(encoding="utf-8"), FLOW.read_text(encoding="utf-8"))

    def test_init_preserves_the_skill_repository_wrapper(self) -> None:
        bundled = self.root / "codex-production-flow" / "scripts" / "flow.py"
        bundled.parent.mkdir(parents=True)
        bundled.write_text(FLOW.read_text(encoding="utf-8"), encoding="utf-8")
        runner = self.root / "scripts" / "codex-flow.py"
        runner.parent.mkdir(parents=True)
        wrapper = (
            '#!/usr/bin/env python3\n'
            '"""Repository-local entry point for the bundled Production Flow Skill."""\n'
        )
        runner.write_text(wrapper, encoding="utf-8")

        self.run_flow("init")

        self.assertEqual(runner.read_text(encoding="utf-8"), wrapper)

    def test_new_allows_only_one_active_task(self) -> None:
        self.run_flow("init")
        self.run_flow("new", "TASK-001", "--title", "First slice", "--risk", "L1")

        blocked = self.run_flow(
            "new", "TASK-002", "--title", "Second slice", "--risk", "L1", expected=2
        )
        self.assertIn("active task", blocked.stderr.lower())
        self.assertTrue((self.root / "spec" / "changes" / "TASK-001.md").is_file())
        self.assertFalse((self.root / "spec" / "changes" / "TASK-002.md").exists())

    def test_approval_rejects_placeholders_and_invalidates_after_change(self) -> None:
        self.run_flow("init")
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L1")
        rejected = self.run_flow("approve", "task", expected=2)
        self.assertIn("placeholder", rejected.stderr.lower())

        task = self.complete_task()
        self.run_flow("approve", "task")
        task.write_text(task.read_text(encoding="utf-8") + "\nChanged after approval.\n", encoding="utf-8")

        status = self.run_flow("status")
        self.assertIn("approval: invalid", status.stdout.lower())
        state = json.loads((self.root / "spec" / "state.json").read_text(encoding="utf-8"))
        self.assertFalse(state["approvals"]["task"]["valid"])

    def test_l1_implementation_requires_observed_red_with_expected_failure(self) -> None:
        self.run_flow("init")
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L1")
        self.complete_task()
        self.run_flow("approve", "task")
        self.run_flow("check", "implement", expected=2)

        self.run_flow(
            "red",
            "--requirement",
            "REQ-001",
            "--expect-pattern",
            "behavior missing",
            "--",
            sys.executable,
            "-c",
            "import sys; print('behavior missing'); sys.exit(1)",
        )
        self.run_flow("check", "implement")

    def test_green_verification_becomes_stale_after_project_change(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L0")
        self.complete_task()
        self.run_flow("approve", "task")
        (self.root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")

        self.run_flow(
            "verify",
            "--scope",
            "targeted",
            "--",
            sys.executable,
            "-c",
            "print('green')",
        )
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        self.run_flow("check", "commit")

        (self.root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=self.root, check=True)
        stale = self.run_flow("check", "commit", expected=2)
        self.assertIn("stale", stale.stderr.lower())

    def test_commit_gate_blocks_secret_paths_and_unapproved_migrations(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L0")
        self.complete_task()
        self.run_flow("approve", "task")
        (self.root / ".env.production").write_text("TOKEN=not-a-real-token\n", encoding="utf-8")
        subprocess.run(["git", "add", "-f", ".env.production"], cwd=self.root, check=True)
        blocked_secret = self.run_flow("check", "commit", expected=2)
        self.assertIn("secret", blocked_secret.stderr.lower())

        subprocess.run(["git", "reset", "-q", "HEAD", ".env.production"], cwd=self.root, check=True)
        (self.root / "db" / "migrations").mkdir(parents=True)
        migration = self.root / "db" / "migrations" / "001.sql"
        migration.write_text("select 1;\n", encoding="utf-8")
        subprocess.run(["git", "add", "db/migrations/001.sql"], cwd=self.root, check=True)
        blocked_migration = self.run_flow("check", "commit", expected=2)
        self.assertIn("migration approval", blocked_migration.stderr.lower())

        self.run_flow("approve", "migration", "--name", "001")
        self.run_flow(
            "verify",
            "--scope",
            "affected",
            "--",
            sys.executable,
            "-c",
            "print('green')",
        )
        self.run_flow("check", "commit")

    def test_commit_gate_blocks_secret_like_content(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L0")
        self.complete_task()
        self.run_flow("approve", "task")
        source = self.root / "config.py"
        source.write_text("API_KEY = 'fixture-secret-value-12345'\n", encoding="utf-8")
        self.run_flow(
            "verify",
            "--scope",
            "affected",
            "--",
            sys.executable,
            "-c",
            "print('green')",
        )
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)

        blocked = self.run_flow("check", "commit", expected=2)
        self.assertIn("secret-like content", blocked.stderr.lower())

    def test_archive_moves_the_single_task_without_copying_it(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L0")
        self.complete_task()
        self.run_flow("approve", "task")
        self.run_flow(
            "verify",
            "--scope",
            "full",
            "--",
            sys.executable,
            "-c",
            "print('green')",
        )
        self.run_flow("archive")

        self.assertFalse((self.root / "spec" / "changes" / "TASK-001.md").exists())
        self.assertTrue((self.root / "spec" / "archive" / "TASK-001.md").is_file())
        state = json.loads((self.root / "spec" / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["phase"], "closed")
        self.assertIsNone(state["activeTask"])
        status = self.run_flow("status")
        self.assertIn("active task: none", status.stdout.lower())

    def test_l1_release_requires_runtime_and_independent_review_evidence(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L1")
        self.complete_task()
        self.run_flow("approve", "task")
        self.run_flow(
            "red",
            "--requirement",
            "REQ-001",
            "--expect-pattern",
            "behavior missing",
            "--",
            sys.executable,
            "-c",
            "import sys; print('behavior missing'); sys.exit(1)",
        )
        self.run_flow(
            "verify",
            "--scope",
            "full",
            "--",
            sys.executable,
            "-c",
            "print('green')",
        )

        blocked = self.run_flow("check", "release", expected=2)
        self.assertIn("runtime", blocked.stderr.lower())
        self.run_flow("attest", "runtime", "--evidence", "artifacts/runtime.png")
        self.run_flow("attest", "review", "--evidence", "review: independent pass")
        self.run_flow("check", "release")

    def test_doctor_reports_consistent_initialized_project(self) -> None:
        self.init_git()
        self.run_flow("init")
        result = self.run_flow("doctor")
        self.assertIn("doctor: ok", result.stdout.lower())

    def test_concurrent_attestations_do_not_lose_state_or_evidence(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L1")
        self.complete_task()
        self.run_flow("approve", "task")
        self.run_flow(
            "red",
            "--requirement",
            "REQ-001",
            "--expect-pattern",
            "behavior missing",
            "--",
            sys.executable,
            "-c",
            "import sys; print('behavior missing'); sys.exit(1)",
        )
        self.run_flow(
            "verify",
            "--scope",
            "full",
            "--",
            sys.executable,
            "-c",
            "print('green')",
        )

        processes = [
            subprocess.Popen(
                self.flow_command("attest", kind, "--evidence", f"{kind}-evidence"),
                text=True,
                encoding="utf-8",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            for kind in ("runtime", "review")
        ]
        results = [process.communicate(timeout=10) + (process.returncode,) for process in processes]
        self.assertEqual([result[2] for result in results], [0, 0], results)

        state = json.loads((self.root / "spec" / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(set(state["attestations"]), {"runtime", "review"})
        evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-001.json").read_text(encoding="utf-8")
        )
        self.assertEqual({item["kind"] for item in evidence["attestations"]}, {"runtime", "review"})


if __name__ == "__main__":
    unittest.main()

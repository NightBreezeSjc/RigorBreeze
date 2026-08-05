from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from flow_test_support import FLOW, FlowTestCase

STANDARD_CHECKS = (
    "format",
    "lint",
    "typecheck",
    "unit",
    "integration",
    "e2e",
    "contract",
    "secret",
    "dependency",
    "license",
    "sbom",
    "migration",
    "build",
    "playwright",
    "acceptance",
)


class FlowCliTests(FlowTestCase):
    def write_full_config(self) -> None:
        checks: list[str] = []
        for check_id in STANDARD_CHECKS:
            if check_id == "build":
                command = [
                    sys.executable,
                    "-c",
                    (
                        "import pathlib;"
                        "p=pathlib.Path('artifacts/app.bin');"
                        "p.parent.mkdir(parents=True,exist_ok=True);"
                        "p.write_bytes(b'artifact')"
                    ),
                ]
                artifact = 'artifacts = ["artifacts/app.bin"]\n'
            else:
                command = [sys.executable, "-c", "print('passed')"]
                artifact = ""
            checks.append(
                "[[checks]]\n"
                f"id = {json.dumps(check_id)}\n"
                f"command = {json.dumps(command)}\n"
                "timeout = 30\n"
                'risks = ["L0", "L1", "L2", "Emergency"]\n'
                f"{artifact}"
            )
        config = (
            "version = 2\n\n"
            "[policy]\n"
            'local_mode = "advisory"\n'
            'test_paths = ["tests"]\n'
            'source_paths = ["src", "app.py"]\n\n'
            "[profiles]\n"
            'affected = ["unit", "secret"]\n'
            f"full = {json.dumps(list(STANDARD_CHECKS))}\n\n" + "\n".join(checks)
        )
        (self.root / "rigorbreeze.toml").write_text(config, encoding="utf-8")
        if self.is_git_repo():
            self.commit_all()

    def record_release_governance(self) -> None:
        command = [
            "evidence",
            "add",
            "--section",
            "release",
            "--kind",
            "governance",
        ]
        for field in (
            "featureFlag=not-required",
            "canary=single-instance",
            "observationWindow=30m",
            "slo=availability>=99.9%",
            "alertOwner=maintainer",
            "rollback=revert artifact",
            "businessMetrics=no-regression",
        ):
            command.extend(("--field", field))
        self.run_flow(*command)

    def complete_task(self, task_id: str = "TASK-001") -> Path:
        task = self.root / "spec" / "changes" / f"{task_id}.md"
        task.write_text(
            f"""# {task_id}: Deliver one observable outcome

Risk: L1

## Authoritative inputs
- Requirement: fixture requirement v1
- Design: fixture design v1
- Domain glossary/ADRs: N/A for this fixture

## Allowed scope
- app.py
- tests/
- db/migrations/

## Forbidden scope
- production credentials

## Acceptance criteria
- REQ-001: command returns the expected result

## Test seams
- Seam: public CLI behavior
- Independent oracle: literal expected output from the requirement

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
        self.init_git()
        self.run_flow("init")
        self.run_flow("init")

        self.assertTrue((self.root / "spec" / "index.md").is_file())
        self.assertTrue(self.state_path().is_file())
        self.assertFalse((self.root / "spec" / "state.json").exists())
        self.assertTrue((self.root / "spec" / "changes").is_dir())
        self.assertTrue((self.root / "spec" / "evidence").is_dir())
        self.assertTrue((self.root / "spec" / "archive").is_dir())
        self.assertTrue((self.root / "scripts" / "rigorbreeze.py").is_file())
        for helper in (
            "flow_state.py",
            "flow_policy.py",
            "flow_parallel.py",
            "flow_automation.py",
        ):
            self.assertTrue((self.root / "scripts" / helper).is_file())

        task = self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L1")
        self.assertIn("created TASK-001", task.stdout)
        task_text = (self.root / "spec" / "changes" / "TASK-001.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## Test seams", task_text)
        self.assertIn("## Conditional risks", task_text)
        for context_field in (
            "- User outcome: TODO",
            "- Current behavior and evidence: TODO",
            "- Business and architecture path: TODO",
            "- Invariants and source of truth: TODO",
            "- Requirement/design/API version: TODO",
            "- Unresolved outcome-changing ambiguity: TODO",
        ):
            self.assertIn(context_field, task_text)

        state = json.loads(self.state_path().read_text(encoding="utf-8"))
        self.assertEqual(state["phase"], "draft")
        self.assertEqual(state["activeTask"]["id"], "TASK-001")

    def test_init_updates_an_existing_managed_runner(self) -> None:
        self.run_flow("init")
        runner = self.root / "scripts" / "rigorbreeze.py"
        runner.write_text(
            '#!/usr/bin/env python3\n"""Deterministic gates for RigorBreeze."""\n# old\n',
            encoding="utf-8",
        )

        self.run_flow("init")

        self.assertEqual(
            runner.read_text(encoding="utf-8"), FLOW.read_text(encoding="utf-8")
        )

    def test_init_preserves_the_skill_repository_wrapper(self) -> None:
        bundled = self.root / "rigorbreeze" / "scripts" / "flow.py"
        bundled.parent.mkdir(parents=True)
        bundled.write_text(FLOW.read_text(encoding="utf-8"), encoding="utf-8")
        runner = self.root / "scripts" / "rigorbreeze.py"
        runner.parent.mkdir(parents=True)
        wrapper = (
            "#!/usr/bin/env python3\n"
            '"""Repository-local entry point for the bundled RigorBreeze Skill."""\n'
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
        task.write_text(
            task.read_text(encoding="utf-8") + "\nChanged after approval.\n",
            encoding="utf-8",
        )

        status = self.run_flow("status")
        self.assertIn("approval: invalid", status.stdout.lower())
        state = json.loads(self.state_path().read_text(encoding="utf-8"))
        self.assertTrue(
            state["approvals"]["task"]["valid"],
            "status must report derived invalidity without mutating persisted state",
        )

    def test_status_json_reports_next_action_without_mutating_state(self) -> None:
        self.init_git()
        self.run_flow("init")
        state_path = self.state_path()
        before = state_path.read_bytes()
        lock_path = self.root / "spec" / ".rigorbreeze.lock"
        lock_path.mkdir()

        result = self.run_flow("status", "--json")
        doctor = self.run_flow("doctor", "--json")

        payload = json.loads(result.stdout)
        self.assertEqual(payload["phase"], "baseline")
        self.assertEqual(payload["activeTask"], None)
        self.assertIn("new", payload["nextAction"]["command"])
        self.assertEqual(json.loads(doctor.stdout)["status"], "ok")
        self.assertTrue(
            lock_path.is_dir(), "read-only commands must not touch the lock"
        )
        self.assertEqual(state_path.read_bytes(), before)

    def test_l1_implementation_requires_observed_red_with_expected_failure(
        self,
    ) -> None:
        self.run_flow("init")
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L1")
        self.complete_task()
        test_file = self.root / "tests" / "test_feature.py"
        test_file.parent.mkdir()
        test_file.write_text(
            "raise AssertionError('behavior missing')\n", encoding="utf-8"
        )
        self.run_flow("approve", "task")
        self.run_flow(
            "--mode", "enforced", "verify", "--profile", "affected", expected=2
        )

        self.run_flow(
            "red",
            "--requirement",
            "REQ-001",
            "--test",
            "tests/test_feature.py",
            "--expect-pattern",
            "behavior missing",
            "--",
            sys.executable,
            "tests/test_feature.py",
        )
        status = json.loads(self.run_flow("status", "--json").stdout)
        self.assertEqual(status["phase"], "red")

    def test_green_verification_becomes_stale_after_project_change(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_full_config()
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L0")
        self.complete_task()
        self.run_flow("approve", "task")
        (self.root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")

        self.run_flow(
            "verify",
            "--profile",
            "affected",
        )
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        self.run_flow("check", "commit")

        (self.root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "app.py"], cwd=self.root, check=True)
        stale = self.run_flow("--mode", "enforced", "check", "commit", expected=2)
        self.assertIn("stale", stale.stderr.lower())

    def test_commit_gate_blocks_secret_paths_and_unapproved_migrations(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_full_config()
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L0")
        self.complete_task()
        self.run_flow("approve", "task")
        (self.root / ".env.production").write_text(
            "TOKEN=not-a-real-token\n", encoding="utf-8"
        )
        subprocess.run(
            ["git", "add", "-f", ".env.production"], cwd=self.root, check=True
        )
        blocked_secret = self.run_flow(
            "--mode", "enforced", "check", "commit", expected=2
        )
        self.assertIn("secret", blocked_secret.stderr.lower())

        subprocess.run(
            ["git", "reset", "-q", "HEAD", ".env.production"], cwd=self.root, check=True
        )
        (self.root / ".env.production").unlink()
        (self.root / "db" / "migrations").mkdir(parents=True)
        migration = self.root / "db" / "migrations" / "001.sql"
        migration.write_text("select 1;\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "db/migrations/001.sql"], cwd=self.root, check=True
        )
        blocked_migration = self.run_flow(
            "--mode", "enforced", "check", "commit", expected=2
        )
        self.assertIn("migration approval", blocked_migration.stderr.lower())

        self.run_flow("approve", "migration", "--name", "001")
        self.run_flow(
            "verify",
            "--profile",
            "affected",
        )
        self.run_flow("check", "commit")

    def test_commit_gate_blocks_secret_like_content(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_full_config()
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L0")
        self.complete_task()
        self.run_flow("approve", "task")
        source = self.root / "config.py"
        source.write_text("API_KEY = 'fixture-secret-value-12345'\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)

        blocked = self.run_flow("--mode", "enforced", "check", "commit", expected=2)
        self.assertIn("secret-like content", blocked.stderr.lower())

    def test_commit_gate_allows_only_same_line_marked_synthetic_test_secret(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_full_config()
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L0")
        self.complete_task()
        self.run_flow("approve", "task")
        fixture = self.root / "tests" / "test_redaction.py"
        fixture.parent.mkdir()
        fixture.write_text(
            "API_KEY = 'fixture-secret-value-12345'  # rigorbreeze: synthetic-secret\n",
            encoding="utf-8",
        )
        self.run_flow("--mode", "enforced", "verify", "--profile", "affected")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)

        allowed = self.run_flow("--mode", "enforced", "check", "commit")
        self.assertIn("tests/test_redaction.py:1", allowed.stdout)
        self.assertNotIn("fixture-secret-value", allowed.stdout)

        fixture.write_text(
            "API_KEY = 'fixture-secret-value-12345'  # rigorbreeze: synthetic-secret\n"
            "PASSWORD = 'another-unmarked-secret-12345'\n",
            encoding="utf-8",
        )
        self.run_flow("--mode", "enforced", "verify", "--profile", "affected")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        unmarked = self.run_flow("--mode", "enforced", "check", "commit", expected=2)
        self.assertIn("secret-like content", unmarked.stderr.lower())

    def test_synthetic_secret_marker_cannot_escape_test_or_secret_path_boundaries(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_full_config()
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L0")
        self.complete_task()
        self.run_flow("approve", "task")
        outside = self.root / "app.py"
        outside.write_text(
            "API_KEY = 'fixture-secret-value-12345'  # rigorbreeze: synthetic-secret\n",
            encoding="utf-8",
        )
        self.run_flow("--mode", "enforced", "verify", "--profile", "affected")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        blocked_outside = self.run_flow(
            "--mode", "enforced", "check", "commit", expected=2
        )
        self.assertIn("secret-like content", blocked_outside.stderr.lower())

        subprocess.run(
            ["git", "reset", "-q", "HEAD", "app.py"], cwd=self.root, check=True
        )
        outside.unlink()
        secret_path = self.root / "tests" / "secrets" / "fixture.py"
        secret_path.parent.mkdir(parents=True)
        secret_path.write_text(
            "API_KEY = 'fixture-secret-value-12345'  # rigorbreeze: synthetic-secret\n",
            encoding="utf-8",
        )
        self.run_flow("--mode", "enforced", "verify", "--profile", "affected")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        blocked_path = self.run_flow(
            "--mode", "enforced", "check", "commit", expected=2
        )
        self.assertIn("secret paths are forbidden", blocked_path.stderr.lower())

    def test_synthetic_secret_marker_does_not_bypass_configured_secret_check(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_full_config()
        config = self.root / "rigorbreeze.toml"
        passing = 'id = "secret"\ncommand = ' + json.dumps(
            [sys.executable, "-c", "print('passed')"]
        )
        failing = 'id = "secret"\ncommand = ' + json.dumps(
            [
                sys.executable,
                "-c",
                "raise SystemExit('configured secret scanner failed')",
            ]
        )
        config_text = config.read_text(encoding="utf-8")
        self.assertIn(passing, config_text)
        config.write_text(
            config_text.replace(passing, failing, 1),
            encoding="utf-8",
        )
        self.commit_all("configure failing secret scanner")
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L0")
        self.complete_task()
        self.run_flow("approve", "task")
        fixture = self.root / "tests" / "test_redaction.py"
        fixture.parent.mkdir()
        fixture.write_text(
            "API_KEY = 'fixture-secret-value-12345'  # rigorbreeze: synthetic-secret\n",
            encoding="utf-8",
        )

        result = self.run_flow(
            "--mode", "enforced", "verify", "--profile", "affected", expected=1
        )

        self.assertIn("failed", result.stdout.lower())

    def test_commit_gate_requires_configured_profile_verification(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_full_config()
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L0")
        self.complete_task()
        self.run_flow("approve", "task")
        (self.root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        self.run_flow("--mode", "enforced", "verify", "--profile", "affected")
        state_path = self.state_path()
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["verification"]["configured"] = False
        state["verification"]["profile"] = "targeted"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)

        blocked = self.run_flow("--mode", "enforced", "check", "commit", expected=2)
        self.assertIn("configured", blocked.stderr.lower())

    def test_archive_moves_the_single_task_without_copying_it(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_full_config()
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L0")
        self.complete_task()
        self.run_flow("approve", "task")
        self.run_flow("--mode", "enforced", "verify", "--profile", "full")
        self.record_release_governance()
        self.run_flow("archive")

        self.assertFalse((self.root / "spec" / "changes" / "TASK-001.md").exists())
        self.assertTrue((self.root / "spec" / "archive" / "TASK-001.md").is_file())
        state = json.loads(self.state_path().read_text(encoding="utf-8"))
        self.assertEqual(state["phase"], "archived")
        self.assertIsNone(state["activeTask"])
        status = self.run_flow("status")
        self.assertIn("active task: none", status.stdout.lower())

    def test_l1_release_requires_runtime_and_independent_review_evidence(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_full_config()
        self.run_flow("new", "TASK-001", "--title", "One slice", "--risk", "L1")
        self.complete_task()
        test_file = self.root / "tests" / "test_feature.py"
        test_file.parent.mkdir()
        test_file.write_text(
            "raise AssertionError('behavior missing')\n", encoding="utf-8"
        )
        self.run_flow("approve", "task")
        self.run_flow(
            "red",
            "--requirement",
            "REQ-001",
            "--test",
            "tests/test_feature.py",
            "--expect-pattern",
            "behavior missing",
            "--",
            sys.executable,
            "tests/test_feature.py",
        )
        self.run_flow("--mode", "enforced", "verify", "--profile", "full")
        self.record_release_governance()

        missing_acceptance = self.run_flow("check", "release", expected=2)
        self.assertIn("structured acceptance", missing_acceptance.stderr.lower())
        runtime = self.root / "reports" / "runtime.json"
        runtime.parent.mkdir(exist_ok=True)
        runtime.write_text('{"status":"passed"}\n', encoding="utf-8")
        self.run_flow(
            "evidence",
            "add",
            "--section",
            "acceptance",
            "--kind",
            "runtime",
            "--file",
            "reports/runtime.json",
            "--field",
            "status=passed",
            "--field",
            "environment=test",
        )
        blocked = self.run_flow("check", "release", expected=2)
        self.assertIn("review", blocked.stderr.lower())
        review = self.root / "reports" / "review.txt"
        review.write_text("independent pass\n", encoding="utf-8")
        self.run_flow(
            "evidence",
            "add",
            "--section",
            "acceptance",
            "--kind",
            "review",
            "--file",
            "reports/review.txt",
            "--field",
            "status=passed",
            "--field",
            "reviewer=independent-pass",
        )
        self.run_flow("check", "release")

    def test_doctor_reports_consistent_initialized_project(self) -> None:
        self.init_git()
        self.run_flow("init")
        result = self.run_flow("doctor")
        self.assertIn("doctor: ok", result.stdout.lower())

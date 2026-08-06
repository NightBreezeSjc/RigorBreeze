from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch

from flow_test_support import FlowTestCase


class SimplifiedFlowTests(FlowTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.run_flow("init")
        self.init_git()

    def write_config(
        self,
        *,
        affected: tuple[str, ...] = ("unit",),
        full: tuple[str, ...] = ("unit", "secret"),
        artifact: bool = False,
    ) -> None:
        checks: list[str] = []
        for check_id in sorted(set(affected + full)):
            script = "print('passed')"
            artifact_line = ""
            if check_id == "build" and artifact:
                script = (
                    "import pathlib;"
                    "p=pathlib.Path('artifacts/app.bin');"
                    "p.parent.mkdir(parents=True,exist_ok=True);"
                    "p.write_bytes(b'artifact')"
                )
                artifact_line = 'artifacts = ["artifacts/app.bin"]\n'
            checks.append(
                "[[checks]]\n"
                f'id = "{check_id}"\n'
                f"command = {json.dumps([sys.executable, '-c', script])}\n"
                "timeout = 30\n"
                f"{artifact_line}"
            )
        (self.root / "rigorbreeze.toml").write_text(
            "version = 2\n\n"
            "[policy]\n"
            'local_mode = "advisory"\n'
            'test_paths = ["tests"]\n'
            'source_paths = ["src"]\n'
            'migration_paths = ["migrations"]\n\n'
            "[profiles]\n"
            f"affected = {json.dumps(list(affected))}\n"
            f"full = {json.dumps(list(full))}\n\n" + "\n".join(checks),
            encoding="utf-8",
        )
        self.commit_all()

    def create_task(self, *, risk: str) -> None:
        self.run_flow(
            "new", "TASK-001", "--title", "Observable outcome", "--risk", risk
        )
        task = self.root / "spec" / "changes" / "TASK-001.md"
        task.write_text(
            f"""# TASK-001: Observable outcome

Risk: {risk}

## Authoritative inputs
- Requirement: fixture requirement

## Allowed scope
- src/
- tests/

## Forbidden scope
- production credentials

## Acceptance criteria
- REQ-001: observable behavior passes

## Test seams
- Seam: public behavior
- Independent oracle: literal expected value

## Verification commands
- configured profiles

## Conditional risks
- Runtime/UI: N/A
- Security/migration/release: N/A
""",
            encoding="utf-8",
        )

    def approve_with_red(self) -> None:
        self.create_task(risk="L1")
        tests = self.root / "tests"
        tests.mkdir()
        test_file = tests / "test_feature.py"
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

    def add_runtime_acceptance(self) -> None:
        report = self.root / "reports" / "runtime.txt"
        report.parent.mkdir()
        report.write_text("passed\n", encoding="utf-8")
        self.run_flow(
            "evidence",
            "add",
            "--section",
            "acceptance",
            "--kind",
            "runtime",
            "--file",
            "reports/runtime.txt",
            "--field",
            "status=passed",
            "--field",
            "environment=test",
        )
        review = self.root / "reports" / "review.txt"
        review.write_text("independent review passed\n", encoding="utf-8")
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

    def confirm_retro(self):
        return self.run_flow(
            "retro",
            "--confirm",
            "--rework-reason",
            "none",
            "--exceptions",
            "none",
            "--workflow-impact",
            "helped",
        )

    def test_generated_task_does_not_require_completion_or_release_data_to_approve(
        self,
    ) -> None:
        self.run_flow(
            "new", "TASK-001", "--title", "Observable outcome", "--risk", "L0"
        )
        task = self.root / "spec" / "changes" / "TASK-001.md"
        content = task.read_text(encoding="utf-8")
        self.assertNotIn("## Completion report", content)
        self.assertIn("## Conditional risks", content)

    def test_new_v2_state_does_not_emit_legacy_attestations(self) -> None:
        # Initializing Git after an existing non-Git workflow is a supported
        # legacy-state migration path. The first runner read performs the copy.
        self.run_flow("status", "--json")
        state = json.loads(self.state_path().read_text(encoding="utf-8"))
        self.assertNotIn("attestations", state)

        self.run_flow(
            "new", "TASK-001", "--title", "Observable outcome", "--risk", "L0"
        )
        evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-001.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertNotIn("attestations", evidence)

    def test_enforced_full_accepts_only_the_checks_declared_by_the_project(
        self,
    ) -> None:
        self.write_config()
        self.create_task(risk="L0")
        self.run_flow("approve", "task")

        result = self.run_flow("--mode", "enforced", "verify", "--profile", "full")

        self.assertIn("full profile passed", result.stdout)

    def test_l0_can_archive_after_affected_without_release_governance(self) -> None:
        self.write_config()
        self.create_task(risk="L0")
        self.run_flow("approve", "task")
        self.run_flow("verify", "--profile", "affected")

        self.run_flow("archive")

        self.assertTrue((self.root / "spec" / "archive" / "TASK-001.md").is_file())

    def test_l1_archive_needs_one_prefilled_retro_confirmation_not_release(
        self,
    ) -> None:
        self.write_config()
        self.approve_with_red()
        self.run_flow("--mode", "enforced", "verify", "--profile", "full")
        self.add_runtime_acceptance()

        blocked = self.run_flow("archive", expected=2)
        self.assertIn("retro", blocked.stderr.lower())
        self.assertIn("prefilled summary", blocked.stderr.lower())
        self.assertIn("failureCategories", blocked.stderr)

        summary = json.loads(self.run_flow("retro", "--json").stdout)
        self.assertEqual(summary["taskId"], "TASK-001")
        self.assertIn("verificationRuns", summary)
        self.assertIn("checkRuns", summary)

        confirmation = self.confirm_retro()
        self.assertNotIn("evolution candidate", confirmation.stdout.lower())
        self.run_flow("archive")

        state = json.loads(self.state_path().read_text(encoding="utf-8"))
        evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-001.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(state["phase"], "archived")
        self.assertEqual(evidence["practice"]["summary"]["taskId"], "TASK-001")
        self.assertIn("failureCategories", evidence["practice"]["summary"])
        self.assertFalse(evidence["practice"]["confirmation"]["evolutionCandidate"])

    def test_negative_retro_records_and_prompts_an_evolution_candidate(self) -> None:
        self.write_config()
        self.approve_with_red()
        self.run_flow("--mode", "enforced", "verify", "--profile", "full")
        self.add_runtime_acceptance()

        with patch.dict(os.environ, {"PYTHONIOENCODING": "cp1252"}):
            result = self.run_flow(
                "retro",
                "--confirm",
                "--rework-reason",
                "workflow",
                "--exceptions",
                "nextAction suggested full too early",
                "--workflow-impact",
                "hurt",
            )

        self.assertIn("evolution candidate", result.stdout.lower())
        self.assertIn(
            "$rigorbreeze 汇总这个项目的演进候选",
            result.stdout,
        )
        evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-001.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(evidence["practice"]["confirmation"]["evolutionCandidate"])

    def test_redundant_command_surface_is_removed(self) -> None:
        help_text = self.run_flow("--help").stdout

        self.assertNotIn("attest", help_text)
        for command in ("start", "implement", "push"):
            result = self.run_flow("check", command, expected=2)
            self.assertIn("invalid choice", result.stderr)

    def test_status_never_recommends_a_removed_gate(self) -> None:
        self.write_config()
        self.approve_with_red()

        payload = json.loads(self.run_flow("status", "--json").stdout)

        self.assertNotIn("check implement", payload["nextAction"]["command"])
        self.assertIn("verify --profile affected", payload["nextAction"]["command"])

    def test_failed_checks_are_classified_without_a_second_event_log(self) -> None:
        self.write_config(affected=("lint",), full=("lint",))
        config = self.root / "rigorbreeze.toml"
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                "print('passed')", "raise SystemExit(1)", 1
            ),
            encoding="utf-8",
        )
        self.create_task(risk="L0")
        task = self.root / "spec" / "changes" / "TASK-001.md"
        task.write_text(
            task.read_text(encoding="utf-8").replace(
                "- src/", "- src/\n- rigorbreeze.toml"
            ),
            encoding="utf-8",
        )
        self.run_flow("approve", "task")
        self.run_flow("verify", "--profile", "affected")

        evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-001.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(evidence["checkRuns"][-1]["category"], "static-quality")

        config.write_text(
            config.read_text(encoding="utf-8").replace(
                "raise SystemExit(1)", "print('passed')", 1
            ),
            encoding="utf-8",
        )
        self.run_flow("approve", "task")
        self.run_flow("verify", "--profile", "affected")
        summary = json.loads(self.run_flow("retro", "--json").stdout)
        self.assertEqual(summary["failureCategories"], ["static-quality"])

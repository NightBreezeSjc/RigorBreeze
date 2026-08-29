from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from flow_test_support import FlowTestCase

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import flow_state  # noqa: E402


class FlowV5Tests(FlowTestCase):
    def git_output(self, *args: str) -> str:
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
        ).stdout.strip()

    def initialize_versioned_project(self) -> None:
        self.init_git()
        self.git_output("branch", "-M", "main")
        self.run_flow("init")
        self.commit_all("install workflow")

    def configure_base(self, base: str) -> None:
        config = self.root / "rigorbreeze.toml"
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                'base_branch = ""', f'base_branch = "{base}"'
            ),
            encoding="utf-8",
        )

    def private_records(self):
        common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=self.root,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
        ).stdout.strip()
        return (self.root / common / "rigorbreeze" / "records").resolve()

    def prepare_red_replay_task(
        self, task_id: str
    ) -> tuple[Path, Path, tuple[str, ...]]:
        self.initialize_versioned_project()
        self.run_flow("new", task_id, "--title", "Replay RED", "--risk", "L1")
        task = self.task_file(task_id)
        task.write_text(
            f"""# {task_id}: Replay RED

Risk: L1

Depends-On: none
Task-Origin: current-request
Waiting-On: none
Runtime-Claims: none
Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- Requirement: return a stable value

## Allowed scope
- app/
- tests/

## Forbidden scope
- production configuration

## Acceptance criteria
- REQ-001: public behavior returns the stable value

## Test seams
- Seam: public file behavior
- Independent oracle: literal expected value

## Verification commands
- configured profile
""",
            encoding="utf-8",
        )
        self.run_flow("approve", "task")
        tests = self.root / "tests"
        tests.mkdir()
        test_file = tests / "test_feature.py"
        test_file.write_text("raise AssertionError('missing')\n", encoding="utf-8")
        command = (
            "red",
            "--requirement",
            "REQ-001",
            "--test",
            "tests/test_feature.py",
            "--expect-pattern",
            "missing",
            "--",
            sys.executable,
            "tests/test_feature.py",
        )
        self.run_flow(*command)
        source = self.root / "app"
        source.mkdir()
        (source / "feature.py").write_text("VALUE = 1\n", encoding="utf-8")
        return task, test_file, command

    def test_contract_detail_tracks_risk_instead_of_loading_every_task(self) -> None:
        l1 = flow_state.task_template("TASK-500", "Compact", "L1")
        l2 = flow_state.task_template("TASK-500A", "Full", "L2")

        self.assertIn("- User-stated result and basis: TODO", l1)
        self.assertIn("- Agent-inferred options: none", l1)
        self.assertNotIn("Business and architecture path", l1)
        self.assertIn("Business and architecture path", l2)
        self.assertIn("Invariants and source of truth", l2)

    def test_new_projects_keep_task_records_in_git_private_storage(self) -> None:
        self.init_git()
        self.run_flow("init")

        config = (self.root / "rigorbreeze.toml").read_text(encoding="utf-8")
        self.assertIn("version = 5", config)
        self.assertIn('[records]\nstorage = "private"', config)

        self.commit_all()
        self.run_flow("new", "TASK-501", "--title", "Private records", "--risk", "L0")

        records = self.private_records()
        self.assertTrue((records / "changes" / "TASK-501.md").is_file())
        evidence = json.loads(
            (records / "evidence" / "TASK-501.json").read_text(encoding="utf-8")
        )
        self.assertEqual(evidence["workflowVersion"], 4)
        self.assertFalse((self.root / "spec/changes/TASK-501.md").exists())
        self.assertFalse((self.root / "spec/evidence/TASK-501.json").exists())

    def test_legacy_v4_configuration_keeps_tracked_record_paths(self) -> None:
        self.init_git()
        self.run_flow("init")
        config = (self.root / "rigorbreeze.toml").read_text(encoding="utf-8")
        (self.root / "rigorbreeze.toml").write_text(
            config.replace("version = 5", "version = 4").replace(
                '[records]\nstorage = "private"\npublish_high_risk_summary = true\n\n',
                "",
            ),
            encoding="utf-8",
        )
        self.commit_all()

        self.run_flow("new", "TASK-502", "--title", "Legacy tracked", "--risk", "L0")

        self.assertTrue((self.root / "spec/changes/TASK-502.md").is_file())
        self.assertTrue((self.root / "spec/evidence/TASK-502.json").is_file())

    def test_status_exposes_one_user_facing_interaction(self) -> None:
        self.init_git()
        self.run_flow("init")
        payload = json.loads(self.run_flow("status", "--json").stdout)

        self.assertIn("interaction", payload)
        self.assertEqual(set(payload["interaction"]), {"completed", "current", "next"})
        self.assertIn(
            payload["interaction"]["next"]["actor"], {"codex", "user", "none"}
        )
        text = self.run_flow("status").stdout
        self.assertIn("已完成：", text)
        self.assertIn("当前：", text)
        self.assertIn("需要你操作：", text)
        self.assertNotIn("next action:", text)

    def test_explicit_record_migration_keeps_high_risk_details_private(self) -> None:
        self.init_git()
        self.run_flow("init")
        config_path = self.root / "rigorbreeze.toml"
        config_path.write_text(
            config_path.read_text(encoding="utf-8")
            .replace("version = 5", "version = 4")
            .replace(
                '[records]\nstorage = "private"\npublish_high_risk_summary = true\n\n',
                "",
            ),
            encoding="utf-8",
        )
        (self.root / "spec/changes").mkdir(parents=True, exist_ok=True)
        (self.root / "spec/evidence").mkdir(parents=True, exist_ok=True)
        (self.root / "spec/archive").mkdir(parents=True, exist_ok=True)
        (self.root / "spec/archive/TASK-503.md").write_text(
            "# TASK-503: release\n\nRisk: L2\n", encoding="utf-8"
        )
        (self.root / "spec/evidence/TASK-503.json").write_text(
            json.dumps(
                {
                    "workflowVersion": 4,
                    "taskId": "TASK-503",
                    "baseline": {"head": "abc", "path": "/private/project"},
                    "checkRuns": [
                        {
                            "checkId": "unit",
                            "exitCode": 0,
                            "command": ["python", "secret.py"],
                            "summary": "raw output password=not-for-public rigorbreeze: synthetic-secret",
                        }
                    ],
                    "artifacts": [
                        {
                            "kind": "image",
                            "sha256": "a" * 64,
                            "gitSha": "abc",
                            "path": "/private/build/image.tar",
                        }
                    ],
                    "acceptance": [],
                    "release": [{"kind": "rollback", "status": "ready"}],
                    "practice": {"confirmation": None, "events": []},
                    "closure": {"outcome": "completed", "head": "abc"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self.commit_all("legacy tracked records")

        result = self.run_flow(
            "doctor", "--all", "--repair", "--migrate-records", "private"
        )

        self.assertIn("migrated records to private storage", result.stdout)
        self.assertFalse((self.root / "spec/archive/TASK-503.md").exists())
        self.assertFalse((self.root / "spec/evidence/TASK-503.json").exists())
        audit = self.root / "spec/evidence/TASK-503.audit.json"
        self.assertTrue(audit.is_file())
        audit_text = audit.read_text(encoding="utf-8")
        self.assertLessEqual(len(audit_text.encode()), 32 * 1024)
        self.assertNotIn("/private/project", audit_text)
        self.assertNotIn("password=", audit_text)
        self.assertNotIn('"command"', audit_text)
        self.assertNotIn("/private/build", audit_text)
        self.assertEqual(json.loads(audit_text)["artifacts"][0]["sha256"], "a" * 64)
        self.assertIn('[records]\nstorage = "private"', config_path.read_text())

    def test_record_migration_refuses_active_tasks(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all()
        self.run_flow("new", "TASK-504", "--title", "Active task", "--risk", "L0")

        result = self.run_flow(
            "doctor",
            "--all",
            "--repair",
            "--migrate-records",
            "private",
            expected=2,
        )
        self.assertIn("active task", result.stderr)

    def test_clean_l1_auto_closes_and_compacts_after_integration(self) -> None:
        self.init_git()
        self.git_output("branch", "-M", "main")
        self.run_flow("init")
        (self.root / "rigorbreeze.toml").write_text(
            "version = 5\n\n"
            '[policy]\nlocal_mode = "advisory"\n'
            'test_paths = ["tests"]\nsource_paths = ["src"]\n'
            'migration_paths = ["migrations"]\n\n'
            '[profiles]\naffected = ["unit"]\nfull = ["unit"]\n\n'
            '[parallel]\nbase_branch = "main"\nworktree_root = ""\n\n'
            '[automation]\nlevel = "manual"\nremote = "origin"\n'
            'protected_branches = ["main"]\ncommit_message = "{task_id}: {title}"\n\n'
            '[records]\nstorage = "private"\n'
            "publish_high_risk_summary = true\n\n"
            '[[checks]]\nid = "unit"\n'
            f"command = {json.dumps([sys.executable, 'tests/test_feature.py'])}\n",
            encoding="utf-8",
        )
        self.commit_all()
        self.run_flow("new", "TASK-505", "--title", "Clean L1", "--risk", "L1")
        records = self.private_records()
        task = records / "changes/TASK-505.md"
        task.write_text(
            """# TASK-505: Clean L1

Risk: L1

Depends-On: none
Task-Origin: current-request
Waiting-On: none
Runtime-Claims: none
Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- Requirement: return the expected value

## Allowed scope
- src/
- tests/

## Forbidden scope
- production configuration

## Acceptance criteria
- REQ-001: public behavior passes

## Test seams
- Seam: public behavior
- Independent oracle: literal expected value

## Verification commands
- configured unit profile
""",
            encoding="utf-8",
        )
        self.run_flow("approve", "task")
        (self.root / "tests").mkdir()
        test_file = self.root / "tests/test_feature.py"
        test_file.write_text(
            "from pathlib import Path\n"
            "assert Path('src/feature.py').exists(), 'missing'\n",
            encoding="utf-8",
        )
        self.run_flow(
            "red",
            "--requirement",
            "REQ-001",
            "--test",
            "tests/test_feature.py",
            "--expect-pattern",
            "missing",
            "--",
            sys.executable,
            "tests/test_feature.py",
        )
        (self.root / "src").mkdir()
        (self.root / "src/feature.py").write_text("VALUE = 1\n", encoding="utf-8")
        self.run_flow("--mode", "enforced", "verify", "--profile", "full")
        for kind in ("runtime", "review"):
            report = self.root / "reports" / f"{kind}.txt"
            report.parent.mkdir(exist_ok=True)
            report.write_text("passed\n", encoding="utf-8")
            fields = ["status=passed", "environment=test"]
            if kind == "review":
                fields.append("reviewer=independent-pass")
            args = [
                "evidence",
                "add",
                "--section",
                "acceptance",
                "--kind",
                kind,
                "--file",
                f"reports/{report.name}",
            ]
            for field in fields:
                args.extend(["--field", field])
            self.run_flow(*args)

        self.run_flow("archive")
        evidence = json.loads(
            (records / "evidence/TASK-505.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            evidence["practice"]["confirmation"]["workflowImpact"], "unreviewed"
        )
        self.commit_all("integrate clean L1")
        result = json.loads(self.run_flow("reconcile", "--cleanup").stdout)
        self.assertIn("TASK-505", result["compactedRecords"])
        self.assertTrue((records / "history/TASK-505.json").is_file())
        self.assertFalse((records / "evidence/TASK-505.json").exists())

    def test_enforced_full_can_run_stateless_without_satisfying_task_gates(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        config = self.root / "rigorbreeze.toml"
        unit_command = json.dumps([sys.executable, "-c", "print('ok')"])
        config.write_text(
            config.read_text(encoding="utf-8")
            .replace('affected = ["lint", "unit", "secret"]', 'affected = ["unit"]')
            .replace('full = ["lint", "unit", "secret", "build"]', 'full = ["unit"]')
            + '\n[[checks]]\nid = "unit"\n'
            + f"command = {unit_command}\n",
            encoding="utf-8",
        )

        result = self.run_flow("--mode", "enforced", "verify", "--profile", "full")

        self.assertIn("stateless full profile passed", result.stdout)
        state = json.loads(self.state_path().read_text(encoding="utf-8"))
        self.assertIsNone(state["verification"])
        blocked = self.run_flow("check", "merge", expected=2)
        self.assertIn("active task", blocked.stderr)

    def test_current_worktree_uses_configured_integration_baseline(self) -> None:
        self.initialize_versioned_project()
        self.git_output("switch", "-c", "integration/initiative")
        (self.root / "historical.txt").write_text(
            "prior initiative slices\n", encoding="utf-8"
        )
        self.git_output("add", "historical.txt")
        self.git_output("commit", "-m", "historical integration work")
        self.configure_base("integration/initiative")
        self.git_output("add", "rigorbreeze.toml")
        self.git_output("commit", "-m", "designate sequential baseline")
        expected_sha = self.git_output("rev-parse", "integration/initiative")

        self.run_flow(
            "new",
            "TASK-506",
            "--title",
            "Configured baseline",
            "--risk",
            "L0",
        )

        state = json.loads(self.state_path().read_text(encoding="utf-8"))
        self.assertEqual(state["activeTask"]["baseBranch"], "integration/initiative")
        self.assertEqual(state["activeTask"]["baseSha"], expected_sha)

    def test_sequential_task_scope_starts_at_its_creation_head(self) -> None:
        self.initialize_versioned_project()
        base_sha = self.git_output("rev-parse", "main")
        self.git_output("switch", "-c", "feature/multiple-slices")
        (self.root / "prior.txt").write_text("closed slice\n", encoding="utf-8")
        self.git_output("add", "prior.txt")
        self.git_output("commit", "-m", "close prior slice")
        start_sha = self.git_output("rev-parse", "HEAD")

        self.run_flow("new", "TASK-509", "--title", "Next slice", "--risk", "L0")
        state = json.loads(self.state_path().read_text(encoding="utf-8"))
        self.assertEqual(state["activeTask"]["baseSha"], base_sha)
        self.assertEqual(state["activeTask"]["startSha"], start_sha)
        task = self.task_file("TASK-509")
        task.write_text(
            """# TASK-509: Next slice

Risk: L0
Depends-On: none
Task-Origin: current-request
Waiting-On: none
Runtime-Claims: none
Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- User-stated result and basis: add the next isolated file
- Agent-inferred options: none
- Unresolved outcome-changing ambiguity: none

## Allowed scope
- next.txt

## Forbidden scope
- prior.txt

## Acceptance criteria
- REQ-001: next file is isolated from the prior slice

## Test seams
- Seam: Git change set
- Independent oracle: task creation HEAD

## Verification commands
- focused fixture check

## Conditional risks
- Runtime/UI: N/A
- Security/migration/release: N/A
- Stop conditions: scope changes
""",
            encoding="utf-8",
        )
        self.run_flow("approve", "task")
        self.assertEqual(
            json.loads(self.run_flow("status", "--json").stdout)["scope"]["status"],
            "current",
        )

        (self.root / "next.txt").write_text("current slice\n", encoding="utf-8")
        self.git_output("add", "next.txt")
        self.git_output("commit", "-m", "implement next slice")
        self.assertEqual(
            json.loads(self.run_flow("status", "--json").stdout)["scope"]["status"],
            "current",
        )
        (self.root / "outside.txt").write_text("escape\n", encoding="utf-8")
        scope = json.loads(self.run_flow("status", "--json").stdout)["scope"]
        self.assertEqual(scope["status"], "violated")
        self.assertEqual(scope["outOfScope"], ["outside.txt"])

    def test_historical_active_task_uses_base_sha_as_start_fallback(self) -> None:
        state = flow_state.initial_state()
        state["activeTask"] = {"id": "LEGACY", "baseSha": "legacy-base"}

        upgraded = flow_state.upgrade_state(state)

        self.assertEqual(upgraded["activeTask"]["startSha"], "legacy-base")

    def test_empty_base_configuration_keeps_default_branch_and_sha(self) -> None:
        self.initialize_versioned_project()
        expected_sha = self.git_output("rev-parse", "main")

        self.run_flow(
            "new",
            "TASK-507",
            "--title",
            "Default baseline",
            "--risk",
            "L0",
        )

        state = json.loads(self.state_path().read_text(encoding="utf-8"))
        self.assertEqual(state["activeTask"]["baseBranch"], "main")
        self.assertEqual(state["activeTask"]["baseSha"], expected_sha)

    def test_missing_configured_base_fails_before_writing_task_records(self) -> None:
        self.initialize_versioned_project()
        self.configure_base("integration/missing")
        self.git_output("add", "rigorbreeze.toml")
        self.git_output("commit", "-m", "configure missing baseline")

        failed = self.run_flow(
            "new",
            "TASK-508",
            "--title",
            "Missing baseline",
            "--risk",
            "L0",
            expected=2,
        )

        self.assertIn("baseline branch is missing: integration/missing", failed.stderr)
        self.assertFalse(self.task_file("TASK-508").exists())
        self.assertFalse(self.evidence_file("TASK-508").exists())
        state = json.loads(self.state_path().read_text(encoding="utf-8"))
        self.assertIsNone(state["activeTask"])

    def test_changed_test_can_reobserve_red_against_the_approved_baseline(self) -> None:
        _, test_file, red_command = self.prepare_red_replay_task("TASK-509")
        test_file.write_text(
            "raise AssertionError('missing again')\n", encoding="utf-8"
        )

        replayed = self.run_flow(*red_command)

        self.assertIn("approved baseline", replayed.stdout)
        self.assertTrue((self.root / "app/feature.py").is_file())
        evidence = json.loads(self.evidence_file("TASK-509").read_text())
        latest = evidence["tddChain"][-1]["red"]
        self.assertEqual(
            latest["baselineReplay"]["baselineSha"], evidence["baseline"]["head"]
        )
        self.assertEqual(
            latest["baselineReplay"]["previousRedObservedAt"],
            evidence["tddChain"][-2]["red"]["observedAt"],
        )
        status = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=self.root,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
        ).stdout
        self.assertNotIn("rigorbreeze-red-", status)

    def test_baseline_red_replay_rejects_contract_change_and_production_tests(
        self,
    ) -> None:
        task, test_file, command = self.prepare_red_replay_task("TASK-510")
        test_file.write_text(
            "raise AssertionError('missing again')\n", encoding="utf-8"
        )
        production_overlay = (
            *command[:-2],
            sys.executable,
            str(self.root / "app/feature.py"),
        )
        unsafe = self.run_flow(*production_overlay, expected=2)
        self.assertIn("must execute every declared --test file", unsafe.stderr)

        task.write_text(
            task.read_text(encoding="utf-8") + "\nChanged outcome.\n", encoding="utf-8"
        )

        blocked = self.run_flow(*command, expected=2)

        self.assertIn("approval", blocked.stderr.lower())

    def test_baseline_red_replay_cleans_temporary_worktree_after_mismatch(self) -> None:
        _, test_file, original = self.prepare_red_replay_task("TASK-511")
        test_file.write_text("raise AssertionError('different')\n", encoding="utf-8")

        self.run_flow(*original, expected=2)

        listed = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=self.root,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
        ).stdout
        self.assertNotIn("rigorbreeze-red-", listed)

    def test_baseline_red_replay_rejects_missing_baseline_and_environment_failure(
        self,
    ) -> None:
        _, test_file, command = self.prepare_red_replay_task("TASK-512")
        evidence_path = self.evidence_file("TASK-512")
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        valid_baseline = evidence["baseline"]["head"]
        evidence["baseline"]["head"] = "0" * 40
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        test_file.write_text(
            "raise AssertionError('missing again')\n", encoding="utf-8"
        )

        missing = self.run_flow(*command, expected=2)
        self.assertIn("baseline replay commit is missing", missing.stderr)

        evidence["baseline"]["head"] = valid_baseline
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        test_file.write_text("import package_that_does_not_exist\n", encoding="utf-8")
        environment = self.run_flow(*command, expected=2)
        self.assertIn("tooling or environment", environment.stderr)

        listed = self.git_output("worktree", "list", "--porcelain")
        self.assertNotIn("rigorbreeze-red-", listed)


if __name__ == "__main__":
    import unittest

    unittest.main()

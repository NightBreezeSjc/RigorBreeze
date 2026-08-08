from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from flow_test_support import FlowTestCase

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


class FlowV4Tests(FlowTestCase):
    def write_task(
        self,
        task_id: str,
        *,
        root: Path | None = None,
        risk: str = "L0",
        scope: str = "src/",
        runtime_claims: str = "none",
        operational_modes: str = "N/A - no conditional runtime behavior",
    ) -> Path:
        project = root or self.root
        path = project / "spec" / "changes" / f"{task_id}.md"
        path.write_text(
            f"""# {task_id}: fixture

Risk: {risk}

Depends-On: none

Runtime-Claims: {runtime_claims}

Operational-Modes: {operational_modes}

## Authoritative inputs
- Requirement: fixture

## Allowed scope
- {scope}

## Forbidden scope
- unrelated files

## Acceptance criteria
- REQ-001: fixture passes
- REQ-002: disabled mode passes
- REQ-003: unavailable mode passes

## Test seams
- Seam: CLI
- Independent oracle: exit code

## Verification commands
- configured profiles

## Conditional risks
- Runtime/UI: N/A
- Security/migration/release: N/A
- Stop conditions: scope changes
""",
            encoding="utf-8",
        )
        return path

    def run_at(
        self, root: Path, *args: str, expected: int = 0
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                *self.flow_command(*args)[:3],
                str(root),
                *self.flow_command(*args)[4:],
            ],
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

    def registry_path(self) -> Path:
        common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        common_path = Path(common)
        if not common_path.is_absolute():
            common_path = self.root / common_path
        return common_path.resolve() / "rigorbreeze" / "registry.json"

    def prepare_release_evidence_task(self, task_id: str) -> None:
        self.init_git()
        self.run_flow("init")
        (self.root / "rigorbreeze.toml").write_text(
            f"""version = 4

[policy]
local_mode = "advisory"
test_paths = ["tests"]
source_paths = ["src"]
migration_paths = ["migrations"]

[profiles]
affected = ["unit"]
full = ["unit", "build"]

[automation]
level = "manual"

[[checks]]
id = "unit"
command = {json.dumps([sys.executable, "-c", "print('passed')"])}

[[checks]]
id = "build"
command = {json.dumps([sys.executable, "-c", "import pathlib; p=pathlib.Path('artifacts/app.bin'); p.parent.mkdir(exist_ok=True); p.write_bytes(b'artifact')"])}
artifacts = ["artifacts/app.bin"]
""",
            encoding="utf-8",
        )
        self.commit_all("install workflow")
        self.run_flow("new", task_id, "--title", "release", "--risk", "L0")
        self.write_task(task_id)
        self.run_flow("approve", "task")
        self.run_flow("--mode", "enforced", "verify", "--profile", "full")

    def test_status_reports_runner_drift_and_init_does_not_upgrade_active_task(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install workflow")
        self.run_flow("new", "TASK-701", "--title", "drift", "--risk", "L0")
        runner = self.root / "scripts" / "flow_state.py"
        runner.write_text(
            runner.read_text(encoding="utf-8").replace(
                'TOOL_VERSION = "0.10.3"', 'TOOL_VERSION = "0.5.1"'
            ),
            encoding="utf-8",
        )

        status = json.loads(self.run_flow("status", "--json").stdout)
        self.assertEqual(
            status["installation"],
            {
                "runnerVersion": "0.5.1",
                "skillVersion": "0.10.3",
                "status": "outdated",
                "upgradeSafe": False,
                "missingComponents": [],
                "modifiedComponents": ["scripts/flow_state.py"],
            },
        )
        blocked = self.run_flow("init", expected=2)
        self.assertIn("active task", blocked.stderr)
        self.assertIn('TOOL_VERSION = "0.5.1"', runner.read_text(encoding="utf-8"))

    def test_status_reports_missing_runner_and_init_repairs_when_idle(self) -> None:
        self.init_git()
        self.run_flow("init")
        runner = self.root / "scripts" / "rigorbreeze.py"
        runner.unlink()

        status = json.loads(self.run_flow("status", "--json").stdout)
        self.assertEqual(status["installation"]["status"], "missing")
        self.assertTrue(status["installation"]["upgradeSafe"])
        self.run_flow("init")
        self.assertTrue(runner.is_file())
        self.assertIn(
            'TOOL_VERSION = "0.10.3"',
            (self.root / "scripts" / "flow_state.py").read_text(encoding="utf-8"),
        )

    def test_l2_approval_requires_a_tracked_workflow_baseline(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.run_flow("new", "TASK-702", "--title", "baseline", "--risk", "L2")
        self.write_task("TASK-702", risk="L2")

        blocked = self.run_flow("approve", "task", expected=2)
        self.assertIn("workflow baseline branch is not current", blocked.stderr)
        self.assertIn("baseline=missing", blocked.stderr)

        self.commit_all("track workflow baseline")
        self.run_flow("approve", "task")

    def test_nested_test_path_is_not_treated_as_production_before_red(self) -> None:
        self.init_git()
        self.run_flow("init")
        config = self.root / "rigorbreeze.toml"
        config.write_text(
            config.read_text(encoding="utf-8")
            .replace(
                'test_paths = ["tests", "test", "__tests__", "src/test"]',
                'test_paths = ["src/tests"]',
            )
            .replace('source_paths = ["src", "app", "lib"]', 'source_paths = ["src"]'),
            encoding="utf-8",
        )
        self.commit_all("install nested-test workflow")
        self.run_flow("new", "TASK-716", "--title", "nested tests", "--risk", "L1")
        self.write_task("TASK-716", risk="L1", scope="src/")
        self.run_flow("approve", "task")

        test_file = self.root / "src" / "tests" / "test_feature.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text(
            "raise AssertionError('expected behavior missing')\n", encoding="utf-8"
        )
        observed = self.run_flow(
            "red",
            "--requirement",
            "REQ-001",
            "--test",
            "src/tests/test_feature.py",
            "--expect-pattern",
            "expected behavior missing",
            "--",
            sys.executable,
            "src/tests/test_feature.py",
        )
        self.assertIn("RED observed", observed.stdout)

    def test_abandoned_archive_records_outcome_and_releases_the_task_slot(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install workflow")
        self.run_flow("new", "TASK-703", "--title", "obsolete", "--risk", "L0")
        self.write_task("TASK-703")
        (self.root / "notes.txt").write_text("unrelated\n", encoding="utf-8")

        result = self.run_flow(
            "archive",
            "--outcome",
            "abandoned",
            "--reason",
            "requirement was withdrawn",
        )
        self.assertIn("abandoned TASK-703", result.stdout)
        state = json.loads(self.state_path().read_text())
        evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-703.json").read_text()
        )
        self.assertIsNone(state["activeTask"])
        self.assertEqual(state["lastClosed"]["outcome"], "abandoned")
        self.assertEqual(evidence["closure"]["outcome"], "abandoned")
        self.assertIn("notes.txt", evidence["closure"]["unrelatedChanges"])
        self.assertTrue((self.root / "spec" / "archive" / "TASK-703.md").is_file())
        self.run_flow("new", "TASK-704", "--title", "replacement", "--risk", "L0")

    def test_abandoned_archive_blocks_task_owned_uncommitted_changes(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install workflow")
        self.run_flow("new", "TASK-705", "--title", "dirty", "--risk", "L0")
        self.write_task("TASK-705")
        (self.root / "src").mkdir()
        (self.root / "src" / "value.txt").write_text("unfinished\n", encoding="utf-8")

        blocked = self.run_flow(
            "archive",
            "--outcome",
            "abandoned",
            "--reason",
            "no longer needed",
            expected=2,
        )
        self.assertIn("task-owned uncommitted changes", blocked.stderr)

    def test_parallel_runtime_claims_block_shared_resources_but_allow_distinct_ones(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install workflow")
        main = self.root
        for task_id in ("TASK-706", "TASK-707"):
            self.run_flow(
                "new",
                task_id,
                "--title",
                task_id,
                "--risk",
                "L0",
                "--worktree",
                "auto",
            )
        tasks = {
            item["taskId"]: Path(item["worktree"])
            for item in json.loads(self.run_flow("status", "--all", "--json").stdout)[
                "tasks"
            ]
        }
        first = tasks["TASK-706"]
        second = tasks["TASK-707"]
        shared = "port:8080, process:uniapp-watcher, app:wechat-devtools"
        self.write_task(
            "TASK-706", root=first, scope="src/first/", runtime_claims=shared
        )
        self.write_task(
            "TASK-707", root=second, scope="src/second/", runtime_claims=shared
        )
        self.run_at(first, "approve", "task")

        blocked = self.run_at(second, "approve", "task", expected=2)
        self.assertIn("runtime claim", blocked.stderr)
        payload = json.loads(self.run_at(main, "status", "--all", "--json").stdout)
        second_status = next(
            item for item in payload["tasks"] if item["taskId"] == "TASK-707"
        )
        self.assertEqual(second_status["runtimeClaims"], sorted(shared.split(", ")))
        self.assertEqual(
            {item["claim"] for item in second_status["runtimeConflicts"]},
            set(shared.split(", ")),
        )

        self.write_task(
            "TASK-707",
            root=second,
            scope="src/second/",
            runtime_claims="port:8081, process:other-watcher, app:other-tool",
        )
        self.run_at(second, "approve", "task")

    def test_l2_operational_modes_require_declared_acceptance_and_full_matrix(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install workflow")
        self.run_flow("new", "TASK-708", "--title", "modes", "--risk", "L2")
        self.write_task(
            "TASK-708",
            risk="L2",
            operational_modes=(
                "enabled=REQ-001, disabled=REQ-999, unavailable=REQ-003"
            ),
        )

        undeclared = self.run_flow("approve", "task", expected=2)
        self.assertIn("undeclared acceptance", undeclared.stderr)

        self.write_task(
            "TASK-708",
            risk="L2",
            operational_modes="enabled=REQ-001",
        )
        incomplete = self.run_flow("approve", "task", expected=2)
        self.assertIn("disabled", incomplete.stderr)
        self.assertIn("unavailable", incomplete.stderr)

        self.write_task(
            "TASK-708",
            risk="L2",
            operational_modes=(
                "enabled=REQ-001, disabled=REQ-002, unavailable=REQ-003"
            ),
        )
        self.run_flow("approve", "task")

    def test_v3_state_upgrade_preserves_history_and_adds_v4_closure(self) -> None:
        self.run_flow("init")
        state_path = self.state_path()
        state = json.loads(state_path.read_text())
        state["workflowVersion"] = 3
        state["lastClosed"] = {
            "id": "TASK-OLD",
            "practice": {"confirmation": {"workflowImpact": "helped"}},
        }
        state_path.write_text(json.dumps(state), encoding="utf-8")
        evidence_path = self.root / "spec" / "evidence" / "TASK-OLD.json"
        evidence_path.write_text(
            json.dumps(
                {
                    "workflowVersion": 3,
                    "taskId": "TASK-OLD",
                    "red": [{"requirement": "REQ-OLD"}],
                    "verifications": [{"profile": "full"}],
                    "automation": [{"action": "push"}],
                    "practice": {"confirmation": {"workflowImpact": "helped"}},
                }
            ),
            encoding="utf-8",
        )

        self.run_flow("init")

        upgraded_state = json.loads(state_path.read_text())
        upgraded_evidence = json.loads(evidence_path.read_text())
        self.assertEqual(upgraded_state["workflowVersion"], 4)
        self.assertEqual(upgraded_evidence["workflowVersion"], 4)
        self.assertEqual(upgraded_evidence["red"][0]["requirement"], "REQ-OLD")
        self.assertEqual(upgraded_evidence["automation"][0]["action"], "push")
        self.assertIsNone(upgraded_evidence["closure"])

    def test_operation_plan_and_paused_result_are_validated_and_recorded(self) -> None:
        self.prepare_release_evidence_task("TASK-709")
        evidence_path = self.root / "spec" / "evidence" / "TASK-709.json"
        evidence = json.loads(evidence_path.read_text())
        artifact_digest = evidence["artifacts"][0]["sha256"]
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        reports = self.root / "reports"
        reports.mkdir(exist_ok=True)
        plan_path = reports / "operation-plan.json"
        plan = {
            "status": "passed",
            "targetEnvironment": "staging",
            "gitSha": head,
            "artifactDigests": [artifact_digest],
            "steps": [
                {"name": stage, "successCondition": f"{stage} complete"}
                for stage in (
                    "backup",
                    "config-freeze",
                    "migration",
                    "deploy",
                    "acceptance",
                    "switch",
                    "observe",
                )
            ],
            "stopConditions": ["candidate unhealthy"],
            "safeRecoveryPoints": ["old instance remains healthy"],
            "rollbackLimitations": ["migration uses forward-fix"],
        }
        plan_path.write_text(json.dumps({**plan, "stopConditions": []}))

        invalid = self.run_flow(
            "evidence",
            "add",
            "--section",
            "release",
            "--kind",
            "operation-plan",
            "--file",
            "reports/operation-plan.json",
            expected=2,
        )
        self.assertIn("stopConditions", invalid.stderr)

        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        self.run_flow(
            "evidence",
            "add",
            "--section",
            "release",
            "--kind",
            "operation-plan",
            "--file",
            "reports/operation-plan.json",
        )
        result_path = reports / "operation-result.json"
        result_path.write_text(
            json.dumps(
                {
                    "status": "paused",
                    "gitSha": head,
                    "artifactDigests": [artifact_digest],
                    "completedSteps": ["backup", "config-freeze", "migration"],
                    "safeState": "migration complete; old instance remains healthy",
                    "resumeAction": "continue from candidate deployment",
                }
            ),
            encoding="utf-8",
        )
        self.run_flow(
            "evidence",
            "add",
            "--section",
            "release",
            "--kind",
            "operation-result",
            "--file",
            "reports/operation-result.json",
        )

        recorded = json.loads(evidence_path.read_text())["release"]
        self.assertEqual(recorded[-2]["kind"], "operation-plan")
        self.assertEqual(recorded[-1]["operation"]["status"], "paused")
        self.assertEqual(
            recorded[-1]["operation"]["resumeAction"],
            "continue from candidate deployment",
        )

    def test_gate_friction_is_deduplicated_into_practice_events(self) -> None:
        self.prepare_release_evidence_task("TASK-710")

        for _ in range(2):
            blocked = self.run_flow("check", "release", expected=2)
            self.assertIn("governance", blocked.stderr)

        evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-710.json").read_text()
        )
        events = evidence["practice"]["events"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "gate-failure")
        self.assertEqual(events[0]["count"], 2)
        summary = json.loads(self.run_flow("retro", "--json").stdout)
        self.assertEqual(summary["practiceEvents"][0]["count"], 2)

    def test_status_records_unapproved_delivery_changes_as_workflow_bypass(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install workflow")
        self.run_flow("new", "TASK-711", "--title", "bypass", "--risk", "L1")
        self.write_task("TASK-711", risk="L1")
        (self.root / "src").mkdir()
        (self.root / "src" / "value.py").write_text("VALUE = 1\n", encoding="utf-8")

        current = json.loads(self.run_flow("status", "--json").stdout)
        self.assertEqual(current["workflowBypass"]["status"], "detected")
        self.assertEqual(current["workflowBypass"]["paths"], ["src/value.py"])
        self.assertTrue(current["workflowBypass"]["evolutionCandidate"])
        self.assertIn("do not fabricate RED", current["nextAction"]["reason"])

        aggregate = json.loads(self.run_flow("status", "--all", "--json").stdout)
        task = next(item for item in aggregate["tasks"] if item["taskId"] == "TASK-711")
        self.assertEqual(task["workflowBypass"]["status"], "detected")
        self.assertEqual(task["workflowBypass"]["paths"], ["src/value.py"])

        evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-711.json").read_text()
        )
        events = evidence["practice"]["events"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "workflow-bypass")
        self.assertTrue(events[0]["evolutionCandidate"])
        self.assertEqual(events[0]["count"], 2)

    def test_status_does_not_treat_workflow_metadata_as_delivery_bypass(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install workflow")
        self.run_flow("new", "TASK-712", "--title", "draft", "--risk", "L1")
        self.write_task("TASK-712", risk="L1")

        status = json.loads(self.run_flow("status", "--json").stdout)
        self.assertEqual(status["workflowBypass"]["status"], "clear")
        evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-712.json").read_text()
        )
        self.assertEqual(evidence.get("practice", {}).get("events", []), [])

    def test_l2_operational_modes_must_close_before_archive(self) -> None:
        self.run_flow("init")
        checks = []
        for check_id in ("format", "unit", "secret", "build"):
            command = [sys.executable, "-c", "print('passed')"]
            artifact = ""
            if check_id == "build":
                command = [
                    sys.executable,
                    "-c",
                    "import pathlib; p=pathlib.Path('artifacts/app.bin'); p.parent.mkdir(exist_ok=True); p.write_bytes(b'artifact')",
                ]
                artifact = 'artifacts = ["artifacts/app.bin"]\n'
            checks.append(
                "[[checks]]\n"
                f'id = "{check_id}"\n'
                f"command = {json.dumps(command)}\n"
                f"{artifact}"
            )
        (self.root / "rigorbreeze.toml").write_text(
            """version = 4
[policy]
local_mode = "advisory"
test_paths = ["tests"]
source_paths = ["src"]
migration_paths = ["migrations"]
[profiles]
affected = ["unit"]
full = ["format", "unit", "secret", "build"]
[automation]
level = "manual"
"""
            + "\n".join(checks),
            encoding="utf-8",
        )
        self.run_flow("new", "TASK-711", "--title", "modes", "--risk", "L2")
        self.write_task(
            "TASK-711",
            risk="L2",
            operational_modes=(
                "enabled=REQ-001, disabled=REQ-002, unavailable=REQ-003"
            ),
        )
        test_file = self.root / "tests" / "test_modes.py"
        test_file.parent.mkdir()
        test_file.write_text("raise AssertionError('mode missing')\n")
        self.run_flow("approve", "task")
        self.run_flow(
            "red",
            "--requirement",
            "REQ-001",
            "--test",
            "tests/test_modes.py",
            "--expect-pattern",
            "mode missing",
            "--",
            sys.executable,
            "tests/test_modes.py",
        )
        self.run_flow("--mode", "enforced", "verify", "--profile", "full")
        reports = self.root / "reports"
        reports.mkdir(exist_ok=True)
        (reports / "runtime.json").write_text('{"status":"passed"}')
        (reports / "review.txt").write_text("review passed\n")
        for kind, file, fields in (
            ("runtime", "runtime.json", ("status=passed", "environment=test")),
            ("review", "review.txt", ("status=passed", "reviewer=independent")),
        ):
            command = [
                "evidence",
                "add",
                "--section",
                "acceptance",
                "--kind",
                kind,
                "--file",
                f"reports/{file}",
            ]
            for field in fields:
                command.extend(("--field", field))
            self.run_flow(*command)

        blocked = self.run_flow("archive", expected=2)
        self.assertIn("REQ-002", blocked.stderr)
        self.assertIn("REQ-003", blocked.stderr)

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
            "--field",
            "requirement=REQ-002,REQ-003",
        )
        retro_only = self.run_flow("archive", expected=2)
        self.assertIn("retrospective", retro_only.stderr)

    def test_primary_worktree_state_migrates_to_git_private_storage(self) -> None:
        self.run_flow("init")
        legacy = self.root / "spec" / "state.json"
        legacy_state = json.loads(legacy.read_text())
        legacy_state["warnings"] = ["preserve-me"]
        legacy.write_text(json.dumps(legacy_state), encoding="utf-8")
        self.init_git()

        projected = json.loads(self.run_flow("status", "--all", "--json").stdout)
        self.assertIsNotNone(projected["workflowBaseline"])
        self.assertTrue(self.state_path().is_file())
        self.assertTrue(legacy.is_file())
        self.run_flow("init")

        private = self.state_path()
        self.assertTrue(private.is_file())
        self.assertEqual(json.loads(private.read_text())["warnings"], ["preserve-me"])
        self.assertFalse(legacy.exists())
        self.assertNotIn("spec/state.json", self.run_flow("status", "--json").stdout)

    def test_workflow_baseline_is_proven_on_the_base_branch(self) -> None:
        self.init_git()
        base = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "checkout", "-qb", "rigorbreeze/task-branch"],
            cwd=self.root,
            check=True,
        )
        self.run_flow("init")
        self.commit_all("workflow exists only on task branch")
        self.run_flow("new", "TASK-712", "--title", "baseline branch", "--risk", "L2")
        self.write_task("TASK-712", risk="L2")

        status = json.loads(self.run_flow("status", "--json").stdout)
        self.assertEqual(status["workflowBaseline"]["baseBranch"], base)
        self.assertEqual(status["workflowBaseline"]["status"], "missing")
        blocked = self.run_flow("--mode", "enforced", "approve", "task", expected=2)
        self.assertIn("baseline branch", blocked.stderr)

    def test_completed_archive_can_be_committed_from_last_closed_context(self) -> None:
        import flow_parallel

        self.init_git()
        self.run_flow("init")
        (self.root / "rigorbreeze.toml").write_text(
            f"""version = 4
[policy]
local_mode = "advisory"
test_paths = ["tests"]
source_paths = ["src"]
migration_paths = ["migrations"]
[profiles]
affected = ["unit"]
full = ["unit"]
[automation]
level = "manual"
[[checks]]
id = "unit"
command = {json.dumps([sys.executable, "-c", "print('passed')"])}
""",
            encoding="utf-8",
        )
        self.commit_all("install workflow")
        self.run_flow("new", "TASK-713", "--title", "close then commit", "--risk", "L0")
        self.write_task("TASK-713", scope="src/")
        self.run_flow("approve", "task")
        self.commit_all("track approved task contract")
        self.assertEqual(
            subprocess.run(
                ["git", "ls-files", "--error-unmatch", "spec/changes/TASK-713.md"],
                cwd=self.root,
                capture_output=True,
            ).returncode,
            0,
        )
        source = self.root / "src" / "value.txt"
        source.parent.mkdir()
        source.write_text("done\n", encoding="utf-8")
        self.run_flow("verify", "--profile", "affected")
        self.run_flow("archive")

        pending = json.loads(self.run_flow("status", "--json").stdout)
        self.assertEqual(pending["lifecycle"], "closure-pending")
        self.assertIn("automate commit --once", pending["nextAction"]["command"])
        registry = json.loads(self.registry_path().read_text(encoding="utf-8"))
        registry["tasks"]["TASK-713"]["nextAction"] = {
            "reason": "stale retrospective advice",
            "command": "repeat an already closed action",
        }
        self.registry_path().write_text(json.dumps(registry), encoding="utf-8")
        aggregate = flow_parallel.aggregate(self.root)
        archived = next(
            task for task in aggregate["tasks"] if task["taskId"] == "TASK-713"
        )
        self.assertEqual(archived["lifecycle"], "closed")
        self.assertNotIn("nextAction", archived)
        pending_evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-713.json").read_text()
        )
        self.assertIn(
            "closure-pending-commit", pending_evidence["closure"]["practiceEvents"]
        )
        blocked_new = self.run_flow(
            "new",
            "TASK-713-NEXT",
            "--title",
            "must wait",
            "--risk",
            "L0",
            expected=2,
        )
        self.assertIn("closure-pending", blocked_new.stderr)
        self.run_flow("automate", "commit", "--once")

        self.assertEqual(
            subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=True,
            ).stdout,
            "",
        )
        committed = subprocess.run(
            ["git", "show", "--pretty=format:", "--name-only", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout
        self.assertIn("src/value.txt", committed)
        self.assertIn("spec/archive/TASK-713.md", committed)
        self.assertIn("spec/evidence/TASK-713.json", committed)
        self.assertNotEqual(
            subprocess.run(
                ["git", "cat-file", "-e", "HEAD:spec/changes/TASK-713.md"],
                cwd=self.root,
                capture_output=True,
            ).returncode,
            0,
        )

    def test_completed_archive_compacts_repeated_successful_check_runs(self) -> None:
        self.init_git()
        self.run_flow("init")
        (self.root / "rigorbreeze.toml").write_text(
            f"""version = 4
[policy]
local_mode = "advisory"
test_paths = ["tests"]
source_paths = ["src"]
migration_paths = ["migrations"]
[profiles]
affected = ["lint", "unit"]
full = ["lint", "unit"]
[automation]
level = "manual"
[[checks]]
id = "lint"
command = {json.dumps([sys.executable, "-c", "print('lint passed')"])}
[[checks]]
id = "unit"
command = {json.dumps([sys.executable, "-c", "print('unit passed')"])}
""",
            encoding="utf-8",
        )
        self.commit_all("install workflow")
        self.run_flow("new", "TASK-713A", "--title", "compact checks", "--risk", "L0")
        self.write_task("TASK-713A", scope="src/")
        self.run_flow("approve", "task")

        for _ in range(3):
            self.run_flow("verify", "--profile", "affected")
        before = json.loads(
            (self.root / "spec" / "evidence" / "TASK-713A.json").read_text()
        )
        self.assertEqual(len(before["checkRuns"]), 6)

        self.run_flow("archive")

        after = json.loads(
            (self.root / "spec" / "evidence" / "TASK-713A.json").read_text()
        )
        self.assertEqual(
            [(run["profile"], run["checkId"]) for run in after["checkRuns"]],
            [("affected", "lint"), ("affected", "unit")],
        )
        self.assertEqual(
            after["checkRunSummary"],
            {
                "policy": "latest-per-profile-check-plus-latest-failure",
                "total": 6,
                "retained": 2,
                "omitted": 4,
                "groups": [
                    {
                        "profile": "affected",
                        "checkId": "lint",
                        "total": 3,
                        "passed": 3,
                        "failed": 0,
                        "retained": 1,
                    },
                    {
                        "profile": "affected",
                        "checkId": "unit",
                        "total": 3,
                        "passed": 3,
                        "failed": 0,
                        "retained": 1,
                    },
                ],
            },
        )
        self.assertEqual(after["closure"]["outcome"], "completed")
        self.assertEqual(len(after["verifications"]), 3)

    def test_completed_archive_keeps_latest_failure_and_final_check(self) -> None:
        self.init_git()
        self.run_flow("init")
        check = (
            "import pathlib,sys; "
            "sys.exit(0 if pathlib.Path('src/pass').exists() else 1)"
        )
        (self.root / "rigorbreeze.toml").write_text(
            f"""version = 4
[policy]
local_mode = "advisory"
test_paths = ["tests"]
source_paths = ["src"]
migration_paths = ["migrations"]
[profiles]
affected = ["unit"]
full = ["unit"]
[automation]
level = "manual"
[[checks]]
id = "unit"
command = {json.dumps([sys.executable, "-c", check])}
""",
            encoding="utf-8",
        )
        self.commit_all("install workflow")
        self.run_flow("new", "TASK-713B", "--title", "retain failure", "--risk", "L0")
        self.write_task("TASK-713B", scope="src/")
        self.run_flow("approve", "task")

        self.run_flow("verify", "--profile", "affected")
        marker = self.root / "src" / "pass"
        marker.parent.mkdir()
        marker.write_text("passed\n", encoding="utf-8")
        self.run_flow("verify", "--profile", "affected")
        self.run_flow("verify", "--profile", "affected")
        self.run_flow("archive")

        evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-713B.json").read_text()
        )
        self.assertEqual(
            [run["passed"] for run in evidence["checkRuns"]], [False, True]
        )
        self.assertEqual(evidence["checkRunSummary"]["total"], 3)
        self.assertEqual(evidence["checkRunSummary"]["retained"], 2)
        self.assertEqual(evidence["checkRunSummary"]["omitted"], 1)
        self.assertEqual(
            evidence["checkRunSummary"]["groups"][0],
            {
                "profile": "affected",
                "checkId": "unit",
                "total": 3,
                "passed": 2,
                "failed": 1,
                "retained": 2,
            },
        )

    def test_non_completed_archive_preserves_check_run_history(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install workflow")
        self.run_flow("new", "TASK-713C", "--title", "preserve history", "--risk", "L0")
        self.write_task("TASK-713C", scope="src/")
        self.run_flow("approve", "task")
        evidence_path = self.root / "spec" / "evidence" / "TASK-713C.json"
        evidence = json.loads(evidence_path.read_text())
        evidence["checkRuns"] = [
            {"profile": "affected", "checkId": "unit", "passed": False},
            {"profile": "affected", "checkId": "unit", "passed": True},
            {"profile": "affected", "checkId": "unit", "passed": True},
        ]
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

        self.run_flow("archive", "--outcome", "abandoned", "--reason", "cancelled")

        preserved = json.loads(evidence_path.read_text())
        self.assertEqual(len(preserved["checkRuns"]), 3)
        self.assertNotIn("checkRunSummary", preserved)

    def test_reconciled_archive_preserves_check_run_history(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install workflow")
        self.run_flow(
            "new", "TASK-713D", "--title", "reconcile history", "--risk", "L0"
        )
        self.write_task("TASK-713D", scope="src/")
        self.run_flow("approve", "task")
        evidence_path = self.root / "spec" / "evidence" / "TASK-713D.json"
        evidence = json.loads(evidence_path.read_text())
        evidence["checkRuns"] = [
            {"profile": "affected", "checkId": "unit", "passed": False},
            {"profile": "affected", "checkId": "unit", "passed": True},
            {"profile": "affected", "checkId": "unit", "passed": True},
        ]
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        self.commit_all("externally integrated task record")
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()

        self.run_flow(
            "archive",
            "--outcome",
            "reconciled",
            "--reason",
            "external workflow closure",
            "--expected-head",
            head,
        )

        preserved = json.loads(evidence_path.read_text())
        self.assertEqual(len(preserved["checkRuns"]), 3)
        self.assertNotIn("checkRunSummary", preserved)

    def test_review_can_be_recorded_without_a_duplicate_report_file(self) -> None:
        self.prepare_release_evidence_task("TASK-713E")

        self.run_flow(
            "evidence",
            "add",
            "--section",
            "acceptance",
            "--kind",
            "review",
            "--field",
            "status=passed",
            "--field",
            "reviewer=independent-fresh-context",
            "--field",
            "standards=passed",
            "--field",
            "spec=passed",
            "--field",
            "findings=none",
        )

        evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-713E.json").read_text()
        )
        review = evidence["acceptance"][-1]
        self.assertEqual(review["kind"], "review")
        self.assertNotIn("path", review)
        self.assertEqual(review["fields"]["standards"], "passed")
        self.assertEqual(review["fields"]["spec"], "passed")

    def test_reconciled_archive_is_honest_and_releases_the_task_slot(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install workflow")
        self.run_flow("new", "TASK-714", "--title", "historical", "--risk", "L1")
        self.write_task("TASK-714", risk="L1")
        self.run_flow("approve", "task")
        self.commit_all("externally integrated task record")
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()

        self.run_flow(
            "archive",
            "--outcome",
            "reconciled",
            "--reason",
            "code was integrated before workflow closure",
            "--expected-head",
            head,
        )

        evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-714.json").read_text()
        )
        state = json.loads(self.state_path().read_text())
        self.assertEqual(evidence["closure"]["outcome"], "reconciled")
        self.assertEqual(evidence["closure"]["originalPhase"], "approved")
        self.assertEqual(evidence["closure"]["verificationStatus"], "missing/stale")
        self.assertIn("integrated-unclosed", evidence["closure"]["practiceEvents"])
        self.assertEqual(evidence["tddChain"], [])
        self.assertIsNone(state["activeTask"])
        self.assertEqual(state["lastClosed"]["outcome"], "reconciled")

    def test_one_time_workflow_baseline_commit_is_exact_and_becomes_current(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()

        before = json.loads(self.run_flow("status", "--json").stdout)
        self.assertTrue(before["workflowBaseline"]["safeToCommit"])
        self.run_flow(
            "automate",
            "commit",
            "--once",
            "--workflow-baseline",
            "--expected-head",
            head,
        )

        after = json.loads(self.run_flow("status", "--json").stdout)
        self.assertEqual(after["workflowBaseline"]["status"], "current")
        committed = subprocess.run(
            ["git", "show", "--pretty=format:", "--name-only", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines()
        self.assertIn("AGENTS.md", committed)
        self.assertIn("scripts/rigorbreeze.py", committed)
        self.assertIn("spec/index.md", committed)
        self.assertNotIn("spec/state.json", committed)

    def test_integrated_task_is_reported_unclosed_before_baseline_staleness(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install workflow")
        base = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        created = self.run_flow(
            "new",
            "TASK-715",
            "--title",
            "integrated history",
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
        worktree = Path(created.stdout.split("worktree: ", 1)[1].splitlines()[0])
        self.write_task("TASK-715", root=worktree, scope="src/")
        self.run_at(worktree, "approve", "task")
        source = worktree / "src" / "value.txt"
        source.parent.mkdir()
        source.write_text("integrated\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=worktree, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "integrate historical task"],
            cwd=worktree,
            check=True,
        )
        subprocess.run(
            ["git", "merge", "--ff-only", "rigorbreeze/task-715"],
            cwd=self.root,
            check=True,
        )

        payload = json.loads(self.run_flow("status", "--all", "--json").stdout)
        task = next(item for item in payload["tasks"] if item["taskId"] == "TASK-715")
        task_head = subprocess.run(
            ["git", "rev-parse", "rigorbreeze/task-715"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(task["lifecycle"], "integrated-unclosed")
        self.assertFalse(task["baselineStale"])
        self.assertIn("--outcome reconciled", task["nextAction"]["command"])
        self.assertIn(task_head, task["nextAction"]["command"])
        self.assertEqual(task["baseBranch"], base)

    def test_explicit_unmanaged_cleanup_removes_only_proven_integrated_worktree(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install workflow")
        base = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        target = self.root.parent / f"{self.root.name}-unmanaged"
        subprocess.run(
            ["git", "worktree", "add", "-qb", "historical-cleanup", str(target), base],
            cwd=self.root,
            check=True,
        )
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=target,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()

        projected = json.loads(self.run_flow("status", "--all", "--json").stdout)
        candidate = next(
            item
            for item in projected["cleanup"]["retainedWorktrees"]
            if item["worktree"] == str(target.resolve())
        )
        self.assertTrue(candidate["clean"])
        self.assertEqual(candidate["integrationStatus"], "contained")
        self.assertTrue(candidate["requiresConfirmation"])
        self.run_flow(
            "reconcile",
            "--cleanup",
            "--worktree",
            str(target),
            "--base",
            base,
            "--expected-head",
            head,
            "--allow-unmanaged",
        )
        self.assertFalse(target.exists())
        self.assertEqual(
            subprocess.run(
                ["git", "show-ref", "--verify", "refs/heads/historical-cleanup"],
                cwd=self.root,
                capture_output=True,
            ).returncode,
            0,
        )

    def test_doctor_repair_preserves_multiple_closed_tasks_from_one_worktree(
        self,
    ) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.commit_all("install workflow")
        created = self.run_flow(
            "new",
            "TASK-718",
            "--title",
            "first closed task",
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
        worktree = Path(created.stdout.split("worktree: ", 1)[1].splitlines()[0])
        self.write_task("TASK-718", root=worktree)
        self.run_at(
            worktree,
            "archive",
            "--outcome",
            "abandoned",
            "--reason",
            "fixture task ended before implementation",
        )
        subprocess.run(["git", "add", "spec"], cwd=worktree, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "close first fixture"],
            cwd=worktree,
            check=True,
        )

        self.run_at(
            worktree,
            "new",
            "TASK-719",
            "--title",
            "second closed task",
            "--risk",
            "L0",
        )
        self.write_task("TASK-719", root=worktree)
        self.run_at(
            worktree,
            "archive",
            "--outcome",
            "abandoned",
            "--reason",
            "second fixture task ended before implementation",
        )
        subprocess.run(["git", "add", "spec"], cwd=worktree, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "close second fixture"],
            cwd=worktree,
            check=True,
        )

        self.registry_path().write_text("{broken", encoding="utf-8")
        repaired = json.loads(
            self.run_flow("doctor", "--all", "--repair", "--json").stdout
        )
        tasks = {item["taskId"]: item for item in repaired["tasks"]}
        self.assertEqual(set(tasks), {"TASK-718", "TASK-719"})
        self.assertTrue(tasks["TASK-718"]["archived"])
        self.assertTrue(tasks["TASK-719"]["archived"])
        self.assertEqual(tasks["TASK-718"]["worktree"], tasks["TASK-719"]["worktree"])

    def test_doctor_repair_allows_archived_branch_history_with_active_primary_task(
        self,
    ) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.commit_all("install workflow")
        created = self.run_flow(
            "new",
            "TASK-718A",
            "--title",
            "closed branch history",
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
        worktree = Path(created.stdout.split("worktree: ", 1)[1].splitlines()[0])
        self.write_task("TASK-718A", root=worktree)
        self.run_at(
            worktree,
            "archive",
            "--outcome",
            "abandoned",
            "--reason",
            "fixture task ended before implementation",
        )
        subprocess.run(["git", "add", "spec"], cwd=worktree, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "close branch fixture"],
            cwd=worktree,
            check=True,
        )
        subprocess.run(
            ["git", "merge", "--ff-only", "rigorbreeze/task-718a"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "worktree", "remove", str(worktree)],
            cwd=self.root,
            check=True,
            capture_output=True,
        )

        self.run_flow(
            "new",
            "TASK-718B",
            "--title",
            "active primary task",
            "--risk",
            "L0",
        )
        self.write_task("TASK-718B")
        self.registry_path().write_text("{broken", encoding="utf-8")

        repaired = json.loads(
            self.run_flow("doctor", "--all", "--repair", "--json").stdout
        )
        tasks = {item["taskId"]: item for item in repaired["tasks"]}
        self.assertEqual(set(tasks), {"TASK-718A", "TASK-718B"})
        self.assertTrue(tasks["TASK-718A"]["archived"])
        self.assertFalse(tasks["TASK-718B"]["archived"])
        self.assertEqual(tasks["TASK-718A"]["worktree"], tasks["TASK-718B"]["worktree"])

    def test_doctor_json_previews_registry_repair_before_mutation(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.commit_all("install workflow")
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        duplicate = {
            "version": 1,
            "tasks": {
                task_id: {
                    "taskId": task_id,
                    "phase": "draft",
                    "worktree": str(self.root.resolve()),
                    "branch": "main",
                    "baseBranch": "main",
                    "baseSha": head,
                    "dependsOn": [],
                    "allowedScope": [],
                    "runtimeClaims": [],
                    "managedByFlow": False,
                }
                for task_id in ("TASK-720", "TASK-721")
            },
        }
        self.registry_path().write_text(json.dumps(duplicate), encoding="utf-8")

        result = self.run_flow("doctor", "--all", "--json", expected=2)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "error")
        self.assertIn("duplicate worktree registration", " ".join(payload["issues"]))
        self.assertEqual(
            payload["repairPlan"]["command"],
            "python scripts/rigorbreeze.py doctor --all --repair --json",
        )
        self.assertTrue(payload["repairPlan"]["willWriteRegistry"])

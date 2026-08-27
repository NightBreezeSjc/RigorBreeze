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


class FlowV4Tests(FlowTestCase):
    def use_tracked_records(self) -> None:
        path = self.root / "rigorbreeze.toml"
        content = path.read_text(encoding="utf-8")
        content = content.replace("version = 5", "version = 4")
        content = content.replace(
            '[records]\nstorage = "private"\npublish_high_risk_summary = true\n\n',
            "",
        )
        path.write_text(content, encoding="utf-8")

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
        path = self.task_file(task_id, project)
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
                'TOOL_VERSION = "0.18.0"', 'TOOL_VERSION = "0.5.1"'
            ),
            encoding="utf-8",
        )

        status = json.loads(self.run_flow("status", "--json").stdout)
        self.assertEqual(
            status["installation"],
            {
                "runnerVersion": "0.5.1",
                "skillVersion": "0.18.0",
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
            'TOOL_VERSION = "0.18.0"',
            (self.root / "scripts" / "flow_state.py").read_text(encoding="utf-8"),
        )

    def test_l2_approval_requires_a_tracked_workflow_baseline(self) -> None:
        self.init_git()
        self.run_flow("init")
        blocked = self.run_flow(
            "new", "TASK-702", "--title", "baseline", "--risk", "L2", expected=2
        )
        self.assertIn("workflow baseline and runner must be current", blocked.stderr)
        self.assertIn("baseline=missing", blocked.stderr)
        self.assertFalse(self.task_file("TASK-702").exists())

        self.commit_all("track workflow baseline")
        self.run_flow("new", "TASK-702", "--title", "baseline", "--risk", "L2")
        self.write_task("TASK-702", risk="L2")
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
        evidence = json.loads(self.evidence_file("TASK-703").read_text())
        self.assertIsNone(state["activeTask"])
        self.assertEqual(state["lastClosed"]["outcome"], "abandoned")
        self.assertEqual(evidence["closure"]["outcome"], "abandoned")
        self.assertIn("notes.txt", evidence["closure"]["unrelatedChanges"])
        self.assertTrue(self.archive_file("TASK-703").is_file())
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
        evidence_path = self.evidence_file("TASK-OLD")
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
        self.assertEqual(upgraded_state["workflowVersion"], 5)
        self.assertEqual(upgraded_evidence["workflowVersion"], 4)
        self.assertEqual(upgraded_evidence["red"][0]["requirement"], "REQ-OLD")
        self.assertEqual(upgraded_evidence["automation"][0]["action"], "push")
        self.assertIsNone(upgraded_evidence["closure"])

    def test_operation_plan_and_paused_result_are_validated_and_recorded(self) -> None:
        self.prepare_release_evidence_task("TASK-709")
        evidence_path = self.evidence_file("TASK-709")
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

        evidence = json.loads(self.evidence_file("TASK-710").read_text())
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

        evidence = json.loads(self.evidence_file("TASK-711").read_text())
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
        evidence = json.loads(self.evidence_file("TASK-712").read_text())
        self.assertEqual(evidence.get("practice", {}).get("events", []), [])

    def test_missing_active_contract_is_a_recoverable_orphan_in_status_and_doctor(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install workflow")
        self.run_flow("new", "TASK-716", "--title", "orphan", "--risk", "L0")
        contract = self.task_file("TASK-716")
        contract.unlink()

        current = json.loads(self.run_flow("status", "--json").stdout)
        self.assertEqual(current["lifecycle"], "orphaned-record")
        self.assertIn("restore", current["nextAction"]["command"])

        aggregate = json.loads(self.run_flow("status", "--all", "--json").stdout)
        task = next(item for item in aggregate["tasks"] if item["taskId"] == "TASK-716")
        self.assertEqual(task["lifecycle"], "orphaned-record")
        self.assertEqual(task["readiness"], "blocked")
        self.assertTrue(any("TASK-716" in issue for issue in aggregate["issues"]))

        doctor = self.run_flow("doctor", "--all", "--json", expected=2)
        diagnosis = json.loads(doctor.stdout)
        diagnosed = next(
            item for item in diagnosis["tasks"] if item["taskId"] == "TASK-716"
        )
        self.assertEqual(diagnosed["lifecycle"], "orphaned-record")
        self.assertTrue(any("TASK-716" in issue for issue in diagnosis["issues"]))

    def test_status_surfaces_existing_evolution_candidates_without_new_log(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install workflow")
        self.run_flow("new", "TASK-717", "--title", "candidate", "--risk", "L0")
        evidence_path = self.evidence_file("TASK-717")
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["practice"] = {
            "events": [
                {
                    "type": "workflow-bypass",
                    "evolutionCandidate": True,
                    "count": 2,
                }
            ]
        }
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        before = evidence_path.read_bytes()

        current = json.loads(self.run_flow("status", "--json").stdout)
        self.assertEqual(current["evolution"]["candidateCount"], 1)
        self.assertEqual(current["evolution"]["taskIds"], ["TASK-717"])
        self.assertEqual(
            current["evolution"]["command"],
            "$rigorbreeze 汇总这个项目的演进候选",
        )
        aggregate = json.loads(self.run_flow("status", "--all", "--json").stdout)
        self.assertEqual(aggregate["evolution"]["candidateCount"], 1)
        self.assertEqual(evidence_path.read_bytes(), before)

    def test_new_l1_preflights_installation_and_baseline_before_creating_files(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")

        blocked = self.run_flow(
            "new", "TASK-718", "--title", "preflight", "--risk", "L1", expected=2
        )
        self.assertIn("workflow baseline", blocked.stderr)
        self.assertFalse(self.task_file("TASK-718").exists())
        self.assertFalse(self.evidence_file("TASK-718").exists())
        state = json.loads(self.state_path().read_text(encoding="utf-8"))
        self.assertIsNone(state["activeTask"])

        self.run_flow("new", "TASK-719", "--title", "lightweight", "--risk", "L0")
        self.assertTrue(self.task_file("TASK-719").is_file())

    def test_task_origin_and_waiting_condition_are_projected_from_the_contract(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install workflow")
        self.run_flow("new", "TASK-720", "--title", "prepared draft", "--risk", "L0")
        contract = self.task_file("TASK-720")
        content = contract.read_text(encoding="utf-8")
        self.assertIn("Task-Origin: current-request", content)
        self.assertIn("Waiting-On: none", content)
        self.write_task("TASK-720")
        content = contract.read_text(encoding="utf-8").replace(
            "Depends-On: none\n",
            "Depends-On: none\n\nTask-Origin: current-request\n\nWaiting-On: none\n",
        )
        contract.write_text(
            content.replace(
                "Task-Origin: current-request",
                "Task-Origin: initiative:DOMAIN-BRIEF-v1",
            ).replace("Waiting-On: none", "Waiting-On: product-approval"),
            encoding="utf-8",
        )

        aggregate = json.loads(self.run_flow("status", "--all", "--json").stdout)
        task = next(item for item in aggregate["tasks"] if item["taskId"] == "TASK-720")
        self.assertEqual(task["taskOrigin"], "initiative:DOMAIN-BRIEF-v1")
        self.assertEqual(task["waitingOn"], "product-approval")
        self.assertEqual(task["readiness"], "waiting")
        self.assertIn("product-approval", task["nextAction"]["reason"])
        blocked = self.run_flow("approve", "task", expected=2)
        self.assertIn("resolve Waiting-On", blocked.stderr)

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
        self.assertTrue(base)
        subprocess.run(
            ["git", "checkout", "-qb", "rigorbreeze/task-branch"],
            cwd=self.root,
            check=True,
        )
        self.run_flow("init")
        self.commit_all("workflow exists only on task branch")
        blocked = self.run_flow(
            "new",
            "TASK-712",
            "--title",
            "baseline branch",
            "--risk",
            "L2",
            expected=2,
        )
        self.assertIn("baseline=missing", blocked.stderr)
        self.assertFalse(self.task_file("TASK-712").exists())

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
        pending_evidence = json.loads(self.evidence_file("TASK-713").read_text())
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
            self.run_flow("verify", "--profile", "affected", "--force")
        before = json.loads(self.evidence_file("TASK-713A").read_text())
        self.assertEqual(len(before["checkRuns"]), 2)
        self.assertEqual(before["checkRunSummary"]["total"], 6)

        self.run_flow("archive")

        after = json.loads(self.evidence_file("TASK-713A").read_text())
        self.assertEqual(
            [(run["profile"], run["checkId"]) for run in after["checkRuns"]],
            [("affected", "lint"), ("affected", "unit")],
        )
        summary = after["checkRunSummary"]
        self.assertEqual(
            summary["policy"], "current-per-fingerprint-plus-latest-failure"
        )
        self.assertEqual(summary["total"], 6)
        self.assertEqual(summary["passed"], 6)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["retained"], 2)
        self.assertEqual(summary["omitted"], 4)
        self.assertGreaterEqual(summary["durationMs"], 0)
        self.assertEqual(
            [
                (group["checkId"], group["total"], group["passed"])
                for group in summary["groups"]
            ],
            [("lint", 3, 3), ("unit", 3, 3)],
        )
        self.assertEqual(after["closure"]["outcome"], "completed")
        self.assertEqual(len(after["verifications"]), 1)
        self.assertEqual(after["verificationSummary"]["total"], 3)

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
        self.run_flow("verify", "--profile", "affected", "--force")
        self.run_flow("archive")

        evidence = json.loads(self.evidence_file("TASK-713B").read_text())
        self.assertEqual(
            [run["passed"] for run in evidence["checkRuns"]], [False, True]
        )
        self.assertEqual(evidence["checkRunSummary"]["total"], 3)
        self.assertEqual(evidence["checkRunSummary"]["retained"], 2)
        self.assertEqual(evidence["checkRunSummary"]["omitted"], 1)
        groups = evidence["checkRunSummary"]["groups"]
        self.assertEqual(sum(group["total"] for group in groups), 3)
        self.assertEqual(sum(group["passed"] for group in groups), 2)
        self.assertEqual(sum(group["failed"] for group in groups), 1)
        self.assertEqual(sum(group["retained"] for group in groups), 2)

    def test_check_run_compaction_is_online_bounded_and_cumulative(self) -> None:
        def run(*, passed: bool, duration: int, fingerprint: str = "fp") -> dict:
            return {
                "profile": "full",
                "checkId": "unit",
                "passed": passed,
                "durationMs": duration,
                "taskDigest": "task",
                "projectFingerprint": fingerprint,
            }

        evidence = {
            "checkRuns": [
                run(passed=False, duration=10),
                run(passed=True, duration=20),
                run(passed=True, duration=30),
            ]
        }
        flow_state.compact_completed_check_runs(evidence)
        evidence["checkRuns"].append(run(passed=True, duration=40))
        flow_state.compact_completed_check_runs(evidence)

        self.assertEqual(
            [record["passed"] for record in evidence["checkRuns"]], [False, True]
        )
        self.assertEqual(evidence["checkRunSummary"]["total"], 4)
        self.assertEqual(evidence["checkRunSummary"]["passed"], 3)
        self.assertEqual(evidence["checkRunSummary"]["failed"], 1)
        self.assertEqual(evidence["checkRunSummary"]["durationMs"], 100)
        self.assertEqual(evidence["checkRunSummary"]["retained"], 2)

    def test_check_run_compaction_does_not_merge_changed_fingerprints(self) -> None:
        evidence = {
            "checkRuns": [
                {
                    "profile": "full",
                    "checkId": "unit",
                    "passed": True,
                    "durationMs": 10,
                    "taskDigest": "task",
                    "projectFingerprint": "before",
                },
                {
                    "profile": "full",
                    "checkId": "unit",
                    "passed": True,
                    "durationMs": 20,
                    "taskDigest": "task",
                    "projectFingerprint": "after",
                },
            ]
        }

        flow_state.compact_completed_check_runs(evidence)

        self.assertEqual(len(evidence["checkRuns"]), 2)
        self.assertNotIn("checkRunSummary", evidence)

    def test_verification_history_compacts_online_without_losing_latest_failure(
        self,
    ) -> None:
        def verification(*, passed: bool, fingerprint: str = "fp") -> dict:
            return {
                "profile": "full",
                "passed": passed,
                "taskDigest": "task",
                "projectFingerprint": fingerprint,
                "configDigest": "config",
            }

        evidence = {
            "verifications": [
                verification(passed=False),
                verification(passed=True),
                verification(passed=True),
            ]
        }
        flow_state.compact_verification_history(evidence)
        evidence["verifications"].append(verification(passed=True))
        flow_state.compact_verification_history(evidence)

        self.assertEqual(
            [record["passed"] for record in evidence["verifications"]],
            [False, True],
        )
        self.assertEqual(
            evidence["verificationSummary"],
            {
                "policy": "current-per-fingerprint-plus-latest-failure",
                "total": 4,
                "passed": 3,
                "failed": 1,
                "retained": 2,
                "omitted": 2,
            },
        )

    def test_completed_tdd_history_keeps_final_green_and_latest_failed_chain(
        self,
    ) -> None:
        def red(requirement: str, label: str) -> dict[str, object]:
            return {
                "requirement": requirement,
                "command": [sys.executable, f"tests/{label}.py"],
                "exitCode": 1,
                "expectedPattern": label,
                "testDigests": {f"tests/{label}.py": label},
                "summary": f"full failure output for {label}",
                "taskDigest": "task-digest",
                "projectFingerprint": f"fingerprint-{label}",
                "head": f"head-{label}",
                "observedAt": f"2026-08-09T00:00:0{label[-1]}Z",
            }

        final_green = {"profile": "full", "passed": True, "verifiedAt": "now"}
        chains = [
            {
                "requirement": "REQ-001",
                "red": red("REQ-001", "attempt1"),
                "green": None,
            },
            {
                "requirement": "REQ-001",
                "red": red("REQ-001", "attempt2"),
                "green": None,
            },
            {
                "requirement": "REQ-001",
                "red": red("REQ-001", "attempt3"),
                "green": final_green,
            },
            {
                "requirement": "REQ-002",
                "red": red("REQ-002", "attempt4"),
                "green": final_green,
            },
        ]
        evidence = {
            "tddChain": chains.copy(),
            "red": [chain["red"] for chain in chains],
        }

        flow_state.compact_completed_tdd_history(evidence)

        self.assertEqual(
            [chain["red"]["expectedPattern"] for chain in evidence["tddChain"]],
            ["attempt2", "attempt3", "attempt4"],
        )
        self.assertEqual(evidence["tddSummary"]["total"], 4)
        self.assertEqual(evidence["tddSummary"]["retained"], 3)
        self.assertEqual(evidence["tddSummary"]["omitted"], 1)
        self.assertEqual(len(evidence["red"]), 3)
        self.assertNotIn("summary", evidence["red"][0])
        self.assertNotIn("command", evidence["red"][0])
        self.assertEqual(evidence["red"][0]["expectedPattern"], "attempt2")

    def test_completed_tdd_history_does_not_change_single_or_empty_history(
        self,
    ) -> None:
        empty = {"tddChain": [], "red": []}
        single = {
            "tddChain": [
                {
                    "requirement": "REQ-001",
                    "red": {"requirement": "REQ-001", "summary": "keep"},
                    "green": {"profile": "full", "passed": True},
                }
            ],
            "red": [{"requirement": "REQ-001", "summary": "keep"}],
        }

        flow_state.compact_completed_tdd_history(empty)
        flow_state.compact_completed_tdd_history(single)

        self.assertEqual(empty, {"tddChain": [], "red": []})
        self.assertEqual(single["red"][0]["summary"], "keep")
        self.assertNotIn("tddSummary", single)

    def test_tdd_compaction_accumulates_replaced_chain_counts_online(self) -> None:
        def chain(label: str, *, green: bool) -> dict:
            return {
                "requirement": "REQ-001",
                "red": {
                    "requirement": "REQ-001",
                    "expectedPattern": label,
                    "taskDigest": "task",
                },
                "green": {"passed": True} if green else None,
            }

        evidence = {
            "tddChain": [chain("first", green=False), chain("second", green=True)],
            "red": [],
        }
        flow_state.compact_completed_tdd_history(evidence)
        evidence["tddChain"].append(chain("third", green=True))
        flow_state.compact_completed_tdd_history(evidence)

        self.assertEqual(evidence["tddSummary"]["total"], 3)
        self.assertEqual(evidence["tddSummary"]["green"], 2)
        self.assertEqual(evidence["tddSummary"]["failedOrInvalidated"], 1)
        self.assertEqual(evidence["tddSummary"]["retained"], 2)
        self.assertEqual(
            [item["red"]["expectedPattern"] for item in evidence["tddChain"]],
            ["first", "third"],
        )

    def test_non_completed_archive_preserves_check_run_history(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install workflow")
        self.run_flow("new", "TASK-713C", "--title", "preserve history", "--risk", "L0")
        self.write_task("TASK-713C", scope="src/")
        self.run_flow("approve", "task")
        evidence_path = self.evidence_file("TASK-713C")
        evidence = json.loads(evidence_path.read_text())
        evidence["checkRuns"] = [
            {"profile": "affected", "checkId": "unit", "passed": False},
            {"profile": "affected", "checkId": "unit", "passed": True},
            {"profile": "affected", "checkId": "unit", "passed": True},
        ]
        evidence["tddChain"] = [
            {"requirement": "REQ-001", "red": {"summary": "first"}, "green": None},
            {"requirement": "REQ-001", "red": {"summary": "second"}, "green": None},
        ]
        evidence["red"] = [chain["red"] for chain in evidence["tddChain"]]
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

        self.run_flow("archive", "--outcome", "abandoned", "--reason", "cancelled")

        preserved = json.loads(evidence_path.read_text())
        self.assertEqual(len(preserved["checkRuns"]), 3)
        self.assertEqual(len(preserved["tddChain"]), 2)
        self.assertEqual(len(preserved["red"]), 2)
        self.assertNotIn("checkRunSummary", preserved)
        self.assertNotIn("tddSummary", preserved)

    def test_reconciled_archive_preserves_check_run_history(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install workflow")
        self.run_flow(
            "new", "TASK-713D", "--title", "reconcile history", "--risk", "L0"
        )
        self.write_task("TASK-713D", scope="src/")
        self.run_flow("approve", "task")
        evidence_path = self.evidence_file("TASK-713D")
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

        evidence = json.loads(self.evidence_file("TASK-713E").read_text())
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

        evidence = json.loads(self.evidence_file("TASK-714").read_text())
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
        self.use_tracked_records()
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
        self.use_tracked_records()
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

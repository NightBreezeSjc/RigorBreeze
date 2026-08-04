from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from flow_test_support import FlowTestCase

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


class FlowV2Tests(FlowTestCase):
    def record_operation_plan(self, task_id: str = "TASK-001") -> None:
        evidence = json.loads(
            (self.root / "spec" / "evidence" / f"{task_id}.json").read_text()
        )
        artifact_digests = [item["sha256"] for item in evidence["artifacts"]]
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        report = self.root / "reports" / "operation-plan.json"
        report.parent.mkdir(exist_ok=True)
        report.write_text(
            json.dumps(
                {
                    "status": "passed",
                    "targetEnvironment": "staging",
                    "gitSha": head,
                    "artifactDigests": artifact_digests,
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
            ),
            encoding="utf-8",
        )
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

    def write_config(
        self,
        *,
        full: tuple[str, ...] = STANDARD_CHECKS,
        affected: tuple[str, ...] = ("unit", "secret"),
        failing: tuple[str, ...] = (),
        artifact: bool = True,
    ) -> None:
        checks: list[str] = []
        for check_id in sorted(set(full + affected)):
            exit_code = 1 if check_id in failing else 0
            report = self.root / "reports" / f"{check_id}.json"
            script = (
                "import json,pathlib,sys;"
                f"p=pathlib.Path({str(report)!r});p.parent.mkdir(parents=True,exist_ok=True);"
                f"p.write_text(json.dumps({{'status':'passed' if {exit_code} == 0 else 'failed'}}));"
                f"sys.exit({exit_code})"
            )
            artifact_line = ""
            if check_id == "build" and artifact:
                artifact_path = self.root / "artifacts" / "app.bin"
                script = (
                    "import json,pathlib;"
                    f"a=pathlib.Path({str(artifact_path)!r});a.parent.mkdir(parents=True,exist_ok=True);"
                    "a.write_bytes(b'immutable-artifact');"
                    f"p=pathlib.Path({str(report)!r});p.parent.mkdir(parents=True,exist_ok=True);"
                    "p.write_text(json.dumps({'status':'passed'}))"
                )
                artifact_line = f"artifacts = [{json.dumps(str(artifact_path.relative_to(self.root)))}]\n"
            command = json.dumps([sys.executable, "-c", script])
            checks.append(
                "[[checks]]\n"
                f"id = {json.dumps(check_id)}\n"
                f"command = {command}\n"
                "timeout = 30\n"
                'risks = ["L0", "L1", "L2", "Emergency"]\n'
                f"report = {json.dumps(str(report.relative_to(self.root)))}\n"
                f"{artifact_line}"
            )
        config = (
            "version = 2\n\n"
            "[policy]\n"
            'local_mode = "advisory"\n'
            'test_paths = ["tests"]\n'
            'source_paths = ["src", "app.py"]\n\n'
            "[profiles]\n"
            f"affected = {json.dumps(list(affected))}\n"
            f"full = {json.dumps(list(full))}\n\n" + "\n".join(checks)
        )
        (self.root / "rigorbreeze.toml").write_text(config, encoding="utf-8")

    def create_task(self, *, risk: str = "L1", commit_baseline: bool = True) -> Path:
        if commit_baseline and self.is_git_repo():
            self.commit_all()
        self.run_flow(
            "new", "TASK-001", "--title", "One observable outcome", "--risk", risk
        )
        task = self.root / "spec" / "changes" / "TASK-001.md"
        task.write_text(
            f"""# TASK-001: One observable outcome

Risk: {risk}

## Authoritative inputs
- Requirement: fixture requirement v2
- Design/prototype: fixture design v2
- API/data/permission: fixture contract v2
- Domain glossary/ADRs: N/A for this fixture

## Allowed scope
- src/
- tests/
- app.py

## Forbidden scope
- production credentials

## Acceptance criteria
- REQ-001: returns the expected result
- UX-001: N/A because this fixture has no UI
- API/DATA/SEC/OPS-001: fixture quality profiles pass

## Test seams
- Seam: public CLI behavior
- Independent oracle: literal expected output from the requirement

## Verification commands
- configured affected and full profiles

## Runtime and release
- Runtime evidence: structured evidence
- Migration and rollback: no migration; revert the atomic commit
- Feature flag/canary/SLO: recorded before release
- Stop conditions: any enforced check fails

## Completion report
- Git SHA / CI run / artifact: generated evidence
- Remaining risks: none for fixture
""",
            encoding="utf-8",
        )
        return task

    def approve_with_red(self, *, risk: str = "L1") -> None:
        self.create_task(risk=risk)
        (self.root / "tests").mkdir()
        test_file = self.root / "tests" / "test_feature.py"
        test_file.write_text(
            "def test_missing_behavior():\n    assert False, 'behavior missing'\n"
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

    def test_init_creates_v2_config_and_structured_evidence(self) -> None:
        self.run_flow("init")
        self.assertTrue((self.root / "rigorbreeze.toml").is_file())
        state = json.loads(
            (self.root / "spec" / "state.json").read_text(encoding="utf-8")
        )
        self.assertEqual(state["workflowVersion"], 4)

        self.create_task(risk="L0")
        evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-001.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(evidence["workflowVersion"], 4)
        for key in (
            "baseline",
            "checkRuns",
            "tddChain",
            "artifacts",
            "acceptance",
            "release",
        ):
            self.assertIn(key, evidence)

    def test_doctor_is_read_only_and_init_upgrades_v1_without_losing_history(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        state_path = self.root / "spec" / "state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["workflowVersion"] = 1
        state["phase"] = "baseline"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        evidence_path = self.root / "spec" / "evidence" / "OLD-001.json"
        evidence_path.write_text(
            json.dumps(
                {
                    "workflowVersion": 1,
                    "taskId": "OLD-001",
                    "red": [{"requirement": "REQ-OLD"}],
                    "verifications": [{"passed": True}],
                    "attestations": [{"kind": "runtime"}],
                }
            ),
            encoding="utf-8",
        )

        before_state = state_path.read_bytes()
        before_evidence = evidence_path.read_bytes()
        doctor = self.run_flow("doctor", "--json")

        self.assertEqual(json.loads(doctor.stdout)["status"], "ok")
        self.assertEqual(state_path.read_bytes(), before_state)
        self.assertEqual(evidence_path.read_bytes(), before_evidence)

        self.run_flow("init")

        upgraded_state = json.loads(state_path.read_text(encoding="utf-8"))
        upgraded_evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertEqual(upgraded_state["workflowVersion"], 4)
        self.assertEqual(upgraded_evidence["workflowVersion"], 4)
        self.assertEqual(upgraded_evidence["red"][0]["requirement"], "REQ-OLD")
        self.assertIn("checkRuns", upgraded_evidence)

    def test_profile_validation_runs_configured_checks_and_records_artifact_digest(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config()
        self.create_task(risk="L0")
        self.run_flow("approve", "task")

        self.run_flow("--mode", "enforced", "verify", "--profile", "full")

        evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-001.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            {item["checkId"] for item in evidence["checkRuns"]},
            set(STANDARD_CHECKS),
        )
        self.assertEqual(len(evidence["artifacts"]), 1)
        self.assertEqual(len(evidence["artifacts"][0]["sha256"]), 64)
        self.assertEqual(evidence["verification"]["profile"], "full")

    def test_arbitrary_verify_scope_is_not_part_of_the_public_cli(self) -> None:
        self.run_flow("init")
        rejected = self.run_flow(
            "verify",
            "--scope",
            "targeted",
            expected=2,
        )

        self.assertIn("--profile", rejected.stderr.lower())

    def test_advisory_warns_but_enforced_blocks_failed_profile(self) -> None:
        self.run_flow("init")
        self.write_config(full=("unit",), affected=("unit",), failing=("unit",))
        self.create_task(risk="L0")
        self.run_flow("approve", "task")

        advisory = self.run_flow("verify", "--profile", "full")
        self.assertIn("advisory", advisory.stdout.lower())
        enforced = self.run_flow(
            "--mode", "enforced", "verify", "--profile", "full", expected=1
        )
        self.assertIn("failed", enforced.stdout.lower())

    def test_enforced_full_requires_only_project_declared_checks(self) -> None:
        self.run_flow("init")
        self.write_config(full=("unit",), affected=("unit",))
        self.create_task(risk="L0")
        self.run_flow("approve", "task")

        result = self.run_flow("--mode", "enforced", "verify", "--profile", "full")
        evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-001.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual({item["checkId"] for item in evidence["checkRuns"]}, {"unit"})
        self.assertIn("passed", result.stdout.lower())

    def test_red_blocks_production_changes_and_green_rejects_changed_test(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config(full=("unit",), affected=("unit",))
        self.create_task()
        (self.root / "tests").mkdir()
        test_file = self.root / "tests" / "test_feature.py"
        test_file.write_text("raise AssertionError('behavior missing')\n")
        self.run_flow("approve", "task")
        (self.root / "app.py").write_text("VALUE = 'implemented too early'\n")

        blocked = self.run_flow(
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
            expected=2,
        )
        self.assertIn("production", blocked.stderr.lower())

        (self.root / "app.py").unlink()
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
        test_file.write_text("print('changed after red')\n")
        stale = self.run_flow(
            "--mode", "enforced", "verify", "--profile", "affected", expected=2
        )
        self.assertIn("test changed", stale.stderr.lower())

    def test_scope_drift_blocks_before_commit_gate(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config()
        self.create_task(risk="L0")
        self.run_flow("approve", "task")
        (self.root / "outside.txt").write_text("scope creep\n", encoding="utf-8")
        blocked = self.run_flow("verify", "--profile", "affected", expected=2)
        self.assertIn("approved scope", blocked.stderr.lower())

    def test_destructive_migration_and_missing_rehearsal_block_enforced_profile(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config(full=("unit",), affected=("unit",))
        task = self.create_task(risk="L2")
        task.write_text(
            task.read_text(encoding="utf-8").replace(
                "- app.py", "- app.py\n- db/migrations/"
            ),
            encoding="utf-8",
        )
        migration = self.root / "db" / "migrations" / "001_drop.sql"
        migration.parent.mkdir(parents=True)
        migration.write_text("DROP TABLE tenant;\n", encoding="utf-8")
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

        blocked = self.run_flow(
            "--mode", "enforced", "verify", "--profile", "full", expected=2
        )
        self.assertIn("destructive migration", blocked.stderr.lower())

    def test_structured_acceptance_requires_real_file_and_metadata(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config()
        self.create_task(risk="L0")
        self.run_flow("approve", "task")
        self.run_flow("--mode", "enforced", "verify", "--profile", "full")

        missing = self.run_flow(
            "evidence",
            "add",
            "--section",
            "acceptance",
            "--kind",
            "playwright",
            "--file",
            "reports/missing.json",
            "--field",
            "status=passed",
            "--field",
            "environment=test",
            expected=2,
        )
        self.assertIn("missing evidence file", missing.stderr.lower())

        report = self.root / "reports" / "playwright.json"
        report.parent.mkdir(exist_ok=True)
        report.write_text('{"status":"passed"}\n', encoding="utf-8")
        self.run_flow(
            "evidence",
            "add",
            "--section",
            "acceptance",
            "--kind",
            "playwright",
            "--file",
            "reports/playwright.json",
            "--field",
            "status=passed",
            "--field",
            "environment=test",
        )
        evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-001.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(evidence["acceptance"][0]["sha256"]), 64)

    def test_l2_release_with_migration_requires_structured_migration_evidence(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config()
        task = self.create_task(risk="L2")
        task.write_text(
            task.read_text(encoding="utf-8").replace(
                "- app.py", "- app.py\n- db/migrations/"
            ),
            encoding="utf-8",
        )
        migration = self.root / "db" / "migrations" / "001_add.sql"
        migration.parent.mkdir(parents=True)
        migration.write_text(
            "CREATE TABLE fixture(id bigint primary key);\n", encoding="utf-8"
        )
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
        runtime_report = self.root / "reports" / "runtime.json"
        runtime_report.write_text('{"status":"passed"}\n', encoding="utf-8")
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
        review_report = self.root / "reports" / "review.txt"
        review_report.write_text("independent review passed\n", encoding="utf-8")
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
        governance = [
            "evidence",
            "add",
            "--section",
            "release",
            "--kind",
            "governance",
        ]
        for field in (
            "featureFlag=off",
            "canary=internal",
            "observationWindow=60m",
            "slo=success>=99%",
            "alertOwner=oncall",
            "rollback=forward-fix",
            "businessMetrics=no-regression",
        ):
            governance.extend(("--field", field))
        self.run_flow(*governance)
        security_evidence = [
            "evidence",
            "add",
            "--section",
            "release",
            "--kind",
            "security",
            "--file",
            "reports/security.json",
        ]
        (self.root / "reports" / "security.json").write_text(
            '{"status":"passed"}\n',
            encoding="utf-8",
        )
        for field in (
            "secretScan=passed",
            "sca=passed",
            "license=passed",
            "sbom=artifacts/sbom.json",
            "owner=security-owner",
        ):
            security_evidence.extend(("--field", field))
        self.run_flow(*security_evidence)
        self.record_operation_plan()

        blocked = self.run_flow("check", "release", expected=2)
        self.assertIn("structured migration", blocked.stderr.lower())
        migration_evidence = [
            "evidence",
            "add",
            "--section",
            "release",
            "--kind",
            "migration",
            "--file",
            "reports/migration-evidence.json",
        ]
        (self.root / "reports" / "migration-evidence.json").write_text(
            '{"status":"passed"}\n',
            encoding="utf-8",
        )
        for field in (
            "rehearsal=passed",
            "dataAssertions=passed",
            "backup=verified",
            "restore=verified",
            "strategy=forward-fix",
        ):
            migration_evidence.extend(("--field", field))
        self.run_flow(*migration_evidence)
        self.run_flow("check", "release")

    def test_release_requires_governance_without_a_push_gate(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config()
        self.create_task(risk="L0")
        self.run_flow("approve", "task")
        self.run_flow("--mode", "enforced", "verify", "--profile", "full")

        blocked = self.run_flow("check", "release", expected=2)
        self.assertIn("release governance", blocked.stderr.lower())
        fields = (
            "featureFlag=not-required",
            "canary=single-instance",
            "observationWindow=30m",
            "slo=availability>=99.9%",
            "alertOwner=maintainer",
            "rollback=revert artifact",
            "businessMetrics=no-regression",
        )
        command = [
            "evidence",
            "add",
            "--section",
            "release",
            "--kind",
            "governance",
        ]
        for field in fields:
            command.extend(("--field", field))
        self.run_flow(*command)
        self.run_flow("check", "release")

    def test_task_approval_rejects_non_machine_readable_scope_and_duplicate_ids(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        task = self.create_task(risk="L1")
        content = task.read_text(encoding="utf-8").replace(
            "## Allowed scope\n- src/\n- tests/\n- app.py",
            "## Allowed scope\n- Enterprise room allocation APIs and tests",
        )
        task.write_text(content, encoding="utf-8")

        invalid_scope = self.run_flow("approve", "task", expected=2)
        self.assertIn("machine-readable", invalid_scope.stderr.lower())

        task.write_text(
            content.replace(
                "- Enterprise room allocation APIs and tests",
                "- src/\n- tests/\n- app.py",
            ).replace(
                "- REQ-001: returns the expected result",
                "- REQ-001: returns the expected result\n- REQ-001: duplicate",
            ),
            encoding="utf-8",
        )
        duplicate = self.run_flow("approve", "task", expected=2)
        self.assertIn("duplicate acceptance", duplicate.stderr.lower())

    def test_approval_cannot_baseline_existing_or_reapproved_production_changes(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config(full=("unit",), affected=("unit",))
        self.commit_all()
        task = self.create_task(risk="L1")
        (self.root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")

        first = self.run_flow("approve", "task", expected=2)
        self.assertIn("production", first.stderr.lower())

        (self.root / "app.py").unlink()
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
        (self.root / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
        task.write_text(
            task.read_text(encoding="utf-8").replace("- src/", "- src/\n- shared/"),
            encoding="utf-8",
        )

        reapproval = self.run_flow("approve", "task", expected=2)
        self.assertIn("revert production changes", reapproval.stderr.lower())

        (self.root / "app.py").unlink()
        self.run_flow("approve", "task")

    def test_single_segment_scope_glob_does_not_cross_directories(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config(full=("unit",), affected=("unit",))
        self.commit_all()
        task = self.create_task(risk="L0")
        task.write_text(
            task.read_text(encoding="utf-8").replace("- src/", "- src/*.py"),
            encoding="utf-8",
        )
        self.run_flow("approve", "task")
        nested = self.root / "src" / "nested" / "value.py"
        nested.parent.mkdir(parents=True)
        nested.write_text("VALUE = 1\n", encoding="utf-8")

        payload = json.loads(self.run_flow("status", "--json").stdout)

        self.assertEqual(payload["scope"]["outOfScope"], ["src/nested/value.py"])

    def test_recursive_scope_glob_matches_nested_paths(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config(full=("unit",), affected=("unit",))
        self.commit_all()
        task = self.create_task(risk="L0")
        task.write_text(
            task.read_text(encoding="utf-8").replace("- src/", "- src/**/*.py"),
            encoding="utf-8",
        )
        self.run_flow("approve", "task")
        nested = self.root / "src" / "nested" / "value.py"
        nested.parent.mkdir(parents=True)
        nested.write_text("VALUE = 1\n", encoding="utf-8")

        payload = json.loads(self.run_flow("status", "--json").stdout)

        self.assertEqual(payload["scope"]["status"], "current")

    def test_new_scope_path_with_spaces_is_machine_checkable(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config(full=("unit",), affected=("unit",))
        self.commit_all()
        task = self.create_task(risk="L0")
        task.write_text(
            task.read_text(encoding="utf-8").replace("- src/", "- src/new file.py"),
            encoding="utf-8",
        )
        self.run_flow("approve", "task")
        source = self.root / "src" / "new file.py"
        source.parent.mkdir()
        source.write_text("VALUE = 1\n", encoding="utf-8")

        payload = json.loads(self.run_flow("status", "--json").stdout)

        self.assertEqual(payload["scope"]["status"], "current")

    def test_workflow_policy_file_requires_explicit_scope(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config(full=("unit",), affected=("unit",))
        self.commit_all()
        self.create_task(risk="L0")
        self.run_flow("approve", "task")
        config = self.root / "rigorbreeze.toml"
        config.write_text(
            config.read_text(encoding="utf-8") + "\n# task-local policy change\n",
            encoding="utf-8",
        )

        payload = json.loads(self.run_flow("status", "--json").stdout)

        self.assertEqual(payload["scope"]["outOfScope"], ["rigorbreeze.toml"])

    def test_committed_file_type_change_is_in_the_task_change_set(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config(full=("unit",), affected=("unit",))
        outside = self.root / "outside.txt"
        outside.write_text("original\n", encoding="utf-8")
        self.commit_all()
        self.create_task(risk="L0")
        self.run_flow("approve", "task")
        blob = subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            cwd=self.root,
            input="target\n",
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "update-index", "--cacheinfo", f"120000,{blob},outside.txt"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-qm", "change file type"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "checkout-index", "--force", "--", "outside.txt"],
            cwd=self.root,
            check=True,
        )

        state = json.loads(
            (self.root / "spec" / "state.json").read_text(encoding="utf-8")
        )
        changed = subprocess.run(
            [
                "git",
                "diff",
                "--name-only",
                f"{state['activeTask']['baseSha']}..HEAD",
            ],
            cwd=self.root,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
        ).stdout.splitlines()
        self.assertIn("outside.txt", changed)

        payload = json.loads(self.run_flow("status", "--json").stdout)

        self.assertEqual(payload["scope"]["outOfScope"], ["outside.txt"])

    def test_red_requires_declared_requirement_and_supports_glob_test_roots(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config(full=("unit",), affected=("unit",))
        config = self.root / "rigorbreeze.toml"
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                'test_paths = ["tests"]', 'test_paths = ["tests/**"]'
            ),
            encoding="utf-8",
        )
        self.create_task(risk="L1")
        test_file = self.root / "tests" / "unit" / "test_feature.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text(
            "raise AssertionError('behavior missing')\n", encoding="utf-8"
        )
        self.run_flow("approve", "task")

        unknown = self.run_flow(
            "red",
            "--requirement",
            "REQ-NOT-DECLARED",
            "--test",
            "tests/unit/test_feature.py",
            "--expect-pattern",
            "behavior missing",
            "--",
            sys.executable,
            "tests/unit/test_feature.py",
            expected=2,
        )
        self.assertIn("acceptance", unknown.stderr.lower())

        self.run_flow(
            "red",
            "--requirement",
            "REQ-001",
            "--test",
            "tests/unit/test_feature.py",
            "--expect-pattern",
            "behavior missing",
            "--",
            sys.executable,
            "tests/unit/test_feature.py",
        )

    def test_l1_red_requires_a_test_even_in_advisory_mode(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config(full=("unit",), affected=("unit",))
        self.create_task(risk="L1")
        self.run_flow("approve", "task")

        blocked = self.run_flow(
            "red",
            "--requirement",
            "REQ-001",
            "--expect-pattern",
            "behavior missing",
            "--",
            sys.executable,
            "-c",
            "raise AssertionError('behavior missing')",
            expected=2,
        )
        self.assertIn("test file", blocked.stderr.lower())

    def test_verify_blocks_scope_drift_and_status_reports_it(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config(full=("unit",), affected=("unit",))
        self.create_task(risk="L0")
        self.run_flow("approve", "task")
        (self.root / "outside.txt").write_text("scope drift\n", encoding="utf-8")

        payload = json.loads(self.run_flow("status", "--json").stdout)
        self.assertEqual(payload["scope"]["status"], "violated")
        self.assertEqual(payload["scope"]["outOfScope"], ["outside.txt"])
        self.assertIn("scope", payload["nextAction"]["reason"].lower())

        blocked = self.run_flow("verify", "--profile", "affected", expected=2)
        self.assertIn("approved scope", blocked.stderr.lower())

    def test_full_profile_greens_every_current_red_chain(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config(full=("unit", "secret"), affected=("unit",))
        task = self.create_task(risk="L1")
        task.write_text(
            task.read_text(encoding="utf-8").replace(
                "- REQ-001: returns the expected result",
                "- REQ-001: returns the expected result\n"
                "- REQ-002: preserves the second behavior",
            ),
            encoding="utf-8",
        )
        tests = self.root / "tests"
        tests.mkdir()
        for number in (1, 2):
            (tests / f"test_{number}.py").write_text(
                f"raise AssertionError('missing {number}')\n", encoding="utf-8"
            )
        self.run_flow("approve", "task")
        for number in (1, 2):
            self.run_flow(
                "red",
                "--requirement",
                f"REQ-00{number}",
                "--test",
                f"tests/test_{number}.py",
                "--expect-pattern",
                f"missing {number}",
                "--",
                sys.executable,
                f"tests/test_{number}.py",
            )

        self.run_flow("--mode", "enforced", "verify", "--profile", "full")
        evidence = json.loads(
            (self.root / "spec" / "evidence" / "TASK-001.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(all(chain.get("green") for chain in evidence["tddChain"]))

    def test_l2_full_derives_supply_chain_and_migration_checks_from_changes(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config(
            full=("format", "unit", "secret", "build"),
            affected=("unit", "secret"),
        )
        task = self.create_task(risk="L2")
        task.write_text(
            task.read_text(encoding="utf-8").replace(
                "- app.py", "- app.py\n- pom.xml\n- migrations/"
            ),
            encoding="utf-8",
        )
        (self.root / "pom.xml").write_text("<project/>\n", encoding="utf-8")
        migration = self.root / "migrations" / "001_add.sql"
        migration.parent.mkdir()
        migration.write_text("CREATE TABLE example(id INT);\n", encoding="utf-8")
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

        blocked = self.run_flow(
            "--mode", "enforced", "verify", "--profile", "full", expected=2
        )
        for check_id in ("dependency", "license", "sbom", "migration"):
            self.assertIn(check_id, blocked.stderr)

    def test_repository_runner_does_not_create_python_bytecode_cache(self) -> None:
        self.init_git()
        self.run_flow("init")
        runner = self.root / "scripts" / "rigorbreeze.py"
        commands = (
            ("status", "--json"),
            ("doctor", "--json"),
            ("new", "TASK-001", "--title", "Observable", "--risk", "L0"),
        )
        for arguments in commands:
            result = subprocess.run(
                [sys.executable, str(runner), "--root", str(self.root), *arguments],
                cwd=self.root,
                text=True,
                encoding="utf-8",
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

        self.assertFalse((self.root / "scripts" / "__pycache__").exists())

    def test_committed_scope_drift_is_still_detected_from_task_baseline(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config(full=("unit",), affected=("unit",))
        self.create_task(risk="L0")
        self.run_flow("approve", "task")
        (self.root / "outside.txt").write_text("committed drift\n", encoding="utf-8")
        subprocess.run(["git", "add", "outside.txt"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "outside task scope"],
            cwd=self.root,
            check=True,
        )

        payload = json.loads(self.run_flow("status", "--json").stdout)
        self.assertEqual(payload["scope"]["outOfScope"], ["outside.txt"])
        blocked = self.run_flow("verify", "--profile", "affected", expected=2)
        self.assertIn("approved scope", blocked.stderr.lower())

    def test_doctor_warns_when_high_risk_task_starts_before_workflow_baseline(
        self,
    ) -> None:
        self.init_git()
        self.run_flow("init")
        self.create_task(risk="L1", commit_baseline=False)

        payload = json.loads(self.run_flow("doctor", "--json").stdout)

        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["warnings"])
        self.assertIn("workflow baseline", payload["warnings"][0])

    def test_merge_blocks_a_dangling_current_tdd_chain(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_config(full=("unit", "secret"), affected=("unit",))
        task = self.create_task(risk="L1")
        task.write_text(
            task.read_text(encoding="utf-8").replace(
                "- REQ-001: returns the expected result",
                "- REQ-001: returns the expected result\n"
                "- REQ-002: preserves the second behavior",
            ),
            encoding="utf-8",
        )
        tests = self.root / "tests"
        tests.mkdir()
        for number in (1, 2):
            (tests / f"test_{number}.py").write_text(
                f"raise AssertionError('missing {number}')\n", encoding="utf-8"
            )
        self.run_flow("approve", "task")
        for number in (1, 2):
            self.run_flow(
                "red",
                "--requirement",
                f"REQ-00{number}",
                "--test",
                f"tests/test_{number}.py",
                "--expect-pattern",
                f"missing {number}",
                "--",
                sys.executable,
                f"tests/test_{number}.py",
            )
        self.run_flow("--mode", "enforced", "verify", "--profile", "full")
        evidence_path = self.root / "spec" / "evidence" / "TASK-001.json"
        evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        evidence["tddChain"][0]["green"] = None
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

        blocked = self.run_flow("check", "merge", expected=2)
        self.assertIn("tdd chains", blocked.stderr.lower())

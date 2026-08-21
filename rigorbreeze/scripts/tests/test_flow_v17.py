from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from flow_test_support import FlowTestCase


RSA_WRAPPER = Path(__file__).resolve().parents[1] / "with_temporary_rsa.py"


class FlowV17Tests(FlowTestCase):
    def registry_path(self) -> Path:
        common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=self.root,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
        ).stdout.strip()
        common_path = Path(common)
        if not common_path.is_absolute():
            common_path = self.root / common_path
        return common_path.resolve() / "rigorbreeze" / "registry.json"

    def write_task(
        self, root: Path, task_id: str, scope: str, risk: str = "L0"
    ) -> None:
        self.task_file(task_id, root).write_text(
            f"""# {task_id}: fixture

Risk: {risk}

Depends-On: none

Task-Origin: current-request

Waiting-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- Result: fixture
- Basis: fixture
- Unresolved outcome-changing ambiguity: none

## Allowed scope
- {scope}

## Forbidden scope
- unrelated files

## Acceptance criteria
- REQ-001: fixture passes

## Test seams
- Seam: CLI
- Independent oracle: JSON state

## Verification commands
- python3 -c "print('ok')"

## Conditional risks
- Runtime/UI: N/A
- Security/migration/release: N/A
- Stop conditions: scope changes
""",
            encoding="utf-8",
        )

    def setup_parallel_repo(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.commit_all("install flow")

    def setup_l1_unit_repo(self, task_id: str) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        (self.root / "rigorbreeze.toml").write_text(
            """version = 5

[records]
storage = "private"

[policy]
local_mode = "advisory"
test_paths = ["tests"]
source_paths = ["src"]
migration_paths = ["migrations"]

[profiles]
affected = ["unit"]
full = ["unit"]

[[checks]]
id = "unit"
command = ["python3", "-c", "print('unit ok')"]
""",
            encoding="utf-8",
        )
        self.commit_all("install flow")
        self.run_flow("new", task_id, "--title", task_id, "--risk", "L1")
        self.write_task(
            self.root,
            task_id,
            "src/value.txt\n- tests/feature_test.py\n- reports/permission-matrix.json",
            risk="L1",
        )
        (self.root / "tests").mkdir()
        (self.root / "tests/feature_test.py").write_text(
            "import pathlib,sys\n"
            "ok=pathlib.Path('src/value.txt').exists()\n"
            "print('present' if ok else 'missing behavior')\n"
            "sys.exit(0 if ok else 1)\n",
            encoding="utf-8",
        )
        self.run_flow("approve", "task")
        self.run_flow(
            "red",
            "--requirement",
            "REQ-001",
            "--expect-pattern",
            "missing behavior",
            "--test",
            "tests/feature_test.py",
            "--",
            "python3",
            "tests/feature_test.py",
        )
        (self.root / "src").mkdir()
        (self.root / "src/value.txt").write_text("green\n", encoding="utf-8")
        (self.root / "reports").mkdir()
        (self.root / "reports/permission-matrix.json").write_text(
            json.dumps({"status": "passed", "roles": ["auditor"]}),
            encoding="utf-8",
        )

    def create_worktree_task(self, task_id: str, scope: str) -> Path:
        created = self.run_flow(
            "new",
            task_id,
            "--title",
            task_id,
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
        worktree = Path(created.stdout.split("worktree: ", 1)[1].splitlines()[0])
        self.write_task(worktree, task_id, scope)
        return worktree

    def create_direct_worktree(self, suffix: str) -> tuple[Path, str]:
        branch = f"rigorbreeze/direct-{suffix}"
        worktree = self.root.parent / f"{self.root.name}-direct-{suffix}"
        subprocess.run(
            ["git", "worktree", "add", "-b", branch, str(worktree), "main"],
            cwd=self.root,
            capture_output=True,
            check=True,
        )
        return worktree, branch

    def commit_direct_change(self, worktree: Path, name: str) -> str:
        (worktree / "src").mkdir(exist_ok=True)
        (worktree / f"src/{name}.txt").write_text(f"{name}\n", encoding="utf-8")
        subprocess.run(["git", "add", f"src/{name}.txt"], cwd=worktree, check=True)
        subprocess.run(["git", "commit", "-qm", name], cwd=worktree, check=True)
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
        ).stdout.strip()

    def test_status_all_survives_a_missing_integrated_worktree(self) -> None:
        self.setup_parallel_repo()
        worktree = self.create_worktree_task("TASK-1701", "src/value.txt")
        registry = json.loads(self.registry_path().read_text(encoding="utf-8"))
        registry["tasks"]["TASK-1701"]["integrated"] = True
        self.registry_path().write_text(json.dumps(registry), encoding="utf-8")
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=self.root,
            check=True,
        )

        payload = json.loads(
            self.run_flow("status", "--all", "--compact", "--json").stdout
        )

        self.assertEqual(payload["issues"], [])
        self.assertEqual(payload["cleanup"]["staleRegistryEntries"], 1)

    def test_status_all_reports_one_issue_for_an_unknown_active_missing_worktree(
        self,
    ) -> None:
        self.setup_parallel_repo()
        worktree = self.create_worktree_task("TASK-1702", "src/value.txt")
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=self.root,
            check=True,
        )

        payload = json.loads(
            self.run_flow("status", "--all", "--compact", "--json").stdout
        )

        missing = [
            issue for issue in payload["issues"] if "worktree is missing" in issue
        ]
        self.assertEqual(len(missing), 1)

    def test_status_path_returns_only_relevant_active_writers(self) -> None:
        self.setup_parallel_repo()
        first = self.create_worktree_task("TASK-1703", "src/target.txt")
        self.create_worktree_task("TASK-1704", "docs/readme.md")

        payload = json.loads(
            self.run_flow("status", "--json", "--path", "src/target.txt").stdout
        )

        self.assertEqual(payload["paths"], ["src/target.txt"])
        self.assertEqual(
            [item["taskId"] for item in payload["activeWriters"]], ["TASK-1703"]
        )
        self.assertNotIn("tasks", payload)
        self.assertNotIn("worktrees", payload)
        self.assertEqual(payload["activeWriters"][0]["worktree"], str(first.resolve()))
        self.assertLess(len(json.dumps(payload)), 4096)

    def test_integrated_head_with_dirty_same_path_remains_a_writer(self) -> None:
        self.setup_parallel_repo()
        main = self.root
        worktree = self.create_worktree_task("TASK-1705", "src/shared.txt")
        (worktree / "src").mkdir()
        (worktree / "src/shared.txt").write_text("integrated\n", encoding="utf-8")
        subprocess.run(["git", "add", "src/shared.txt"], cwd=worktree, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "integrated change"], cwd=worktree, check=True
        )
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=worktree,
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "merge", "--ff-only", branch],
            cwd=main,
            capture_output=True,
            check=True,
        )
        (worktree / "src/shared.txt").write_text("uncommitted\n", encoding="utf-8")

        dirty = json.loads(
            self.run_flow("status", "--json", "--path", "src/shared.txt").stdout
        )
        self.assertEqual(
            [item["taskId"] for item in dirty["activeWriters"]], ["TASK-1705"]
        )
        self.assertEqual(dirty["activeWriters"][0]["reason"], "dirty-overlap")

        subprocess.run(["git", "restore", "src/shared.txt"], cwd=worktree, check=True)
        clean = json.loads(
            self.run_flow("status", "--json", "--path", "src/shared.txt").stdout
        )
        self.assertEqual(clean["activeWriters"], [])
        self.assertEqual(clean["ignoredHistorical"], 1)

    def test_red_preflight_rejects_a_missing_executable_without_recording_red(
        self,
    ) -> None:
        self.setup_parallel_repo()
        self.run_flow("new", "TASK-1710", "--title", "preflight", "--risk", "L1")
        self.write_task(
            self.root,
            "TASK-1710",
            "src/value.txt\n- tests/feature_test.py",
            risk="L1",
        )
        (self.root / "tests").mkdir()
        test_file = self.root / "tests/feature_test.py"
        test_file.write_text(
            "raise AssertionError('missing behavior')\n", encoding="utf-8"
        )
        self.run_flow("approve", "task")

        blocked = self.run_flow(
            "red",
            "--requirement",
            "REQ-001",
            "--expect-pattern",
            "missing behavior",
            "--test",
            "tests/feature_test.py",
            "--",
            "definitely-missing-rigorbreeze-tool",
            "tests/feature_test.py",
            expected=2,
        )

        self.assertIn("environment preflight", blocked.stderr.lower())
        evidence = json.loads(
            self.evidence_file("TASK-1710").read_text(encoding="utf-8")
        )
        self.assertEqual(evidence["tddChain"], [])

    def test_red_preflight_rejects_npm_without_installed_dependencies(self) -> None:
        self.setup_parallel_repo()
        self.run_flow("new", "TASK-1711", "--title", "npm preflight", "--risk", "L1")
        self.write_task(
            self.root,
            "TASK-1711",
            "src/value.ts\n- tests/order.test.js\n- package.json",
            risk="L1",
        )
        (self.root / "tests").mkdir()
        (self.root / "tests/order.test.js").write_text(
            "throw new Error('wrong order')\n", encoding="utf-8"
        )
        (self.root / "package.json").write_text(
            json.dumps(
                {
                    "scripts": {"test": "node tests/order.test.js"},
                    "devDependencies": {"vitest": "synthetic"},
                }
            ),
            encoding="utf-8",
        )
        self.run_flow("approve", "task")

        blocked = self.run_flow(
            "red",
            "--requirement",
            "REQ-001",
            "--expect-pattern",
            "wrong order",
            "--test",
            "tests/order.test.js",
            "--",
            "npm",
            "test",
            "--",
            "tests/order.test.js",
            expected=2,
        )

        self.assertIn("node_modules", blocked.stderr)

    def test_configured_environment_preflight_is_reused_for_red_and_full(
        self,
    ) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        (self.root / "rigorbreeze.toml").write_text(
            """version = 5

[records]
storage = "private"

[policy]
local_mode = "advisory"
test_paths = ["tests"]
source_paths = ["src"]
migration_paths = ["migrations"]

[profiles]
preflight = ["environment"]
affected = ["unit"]
full = ["unit"]

[[checks]]
id = "environment"
command = ["python3", "-c", "import pathlib; p=pathlib.Path('reports/preflight-count'); p.parent.mkdir(exist_ok=True); p.write_text(str(int(p.read_text())+1) if p.exists() else '1')"]

[[checks]]
id = "unit"
command = ["python3", "-c", "print('unit ok')"]
""",
            encoding="utf-8",
        )
        self.commit_all("install flow with preflight")
        self.run_flow("new", "TASK-1712", "--title", "preflight reuse", "--risk", "L1")
        self.write_task(
            self.root,
            "TASK-1712",
            "src/value.txt\n- tests/feature_test.py",
            risk="L1",
        )
        (self.root / "tests").mkdir()
        (self.root / "tests/feature_test.py").write_text(
            "import pathlib,sys\n"
            "ok=pathlib.Path('src/value.txt').exists()\n"
            "print('present' if ok else 'missing behavior')\n"
            "sys.exit(0 if ok else 1)\n",
            encoding="utf-8",
        )
        self.run_flow("approve", "task")
        self.run_flow(
            "red",
            "--requirement",
            "REQ-001",
            "--expect-pattern",
            "missing behavior",
            "--test",
            "tests/feature_test.py",
            "--",
            "python3",
            "tests/feature_test.py",
        )
        (self.root / "src").mkdir()
        (self.root / "src/value.txt").write_text("green\n", encoding="utf-8")

        self.run_flow("verify", "--profile", "full")

        self.assertEqual(
            (self.root / "reports/preflight-count").read_text(encoding="utf-8"), "1"
        )

    def test_read_only_authoritative_observation_can_wait_for_verification(
        self,
    ) -> None:
        self.setup_l1_unit_repo("TASK-1720")

        self.run_flow(
            "evidence",
            "add",
            "--section",
            "acceptance",
            "--kind",
            "authoritative-observation",
            "--file",
            "reports/permission-matrix.json",
            "--field",
            "status=passed",
            "--field",
            "environment=production-readonly",
            "--field",
            "requirement=REQ-001",
            "--field",
            "source=production-role-permission-matrix",
        )
        before = json.loads(self.evidence_file("TASK-1720").read_text(encoding="utf-8"))
        self.assertEqual(before["acceptance"][-1]["verificationBinding"], "pending")
        self.assertEqual(
            json.loads(self.run_flow("status", "--json").stdout)["phase"], "red"
        )

        self.run_flow("verify", "--profile", "full")

        after = json.loads(self.evidence_file("TASK-1720").read_text(encoding="utf-8"))
        self.assertEqual(after["acceptance"][-1]["verificationBinding"], "current")
        self.assertEqual(
            after["acceptance"][-1]["fields"]["source"],
            "production-role-permission-matrix",
        )

    def test_pending_observation_does_not_survive_a_project_change(self) -> None:
        self.setup_l1_unit_repo("TASK-1721")
        self.run_flow(
            "evidence",
            "add",
            "--section",
            "acceptance",
            "--kind",
            "authoritative-observation",
            "--file",
            "reports/permission-matrix.json",
            "--field",
            "status=passed",
            "--field",
            "environment=production-readonly",
            "--field",
            "requirement=REQ-001",
            "--field",
            "source=production-role-permission-matrix",
        )
        (self.root / "src/value.txt").write_text("changed again\n", encoding="utf-8")

        self.run_flow("verify", "--profile", "full")

        evidence = json.loads(
            self.evidence_file("TASK-1721").read_text(encoding="utf-8")
        )
        self.assertEqual(evidence["acceptance"][-1]["verificationBinding"], "pending")

    def test_review_evidence_still_requires_fresh_verification(self) -> None:
        self.setup_l1_unit_repo("TASK-1722")

        blocked = self.run_flow(
            "evidence",
            "add",
            "--section",
            "acceptance",
            "--kind",
            "review",
            "--field",
            "status=passed",
            "--field",
            "reviewer=independent-pass",
            "--field",
            "standards=passed",
            "--field",
            "spec=passed",
            "--field",
            "findings=none",
            expected=2,
        )

        self.assertIn("fresh verification", blocked.stderr)

    def test_verification_reuses_current_fingerprint_unless_forced(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        (self.root / "rigorbreeze.toml").write_text(
            """version = 5

[records]
storage = "private"

[policy]
local_mode = "advisory"
test_paths = ["tests"]
source_paths = ["src"]
migration_paths = ["migrations"]

[profiles]
affected = ["unit"]
full = ["unit"]

[[checks]]
id = "unit"
command = ["python3", "-c", "import pathlib; p=pathlib.Path('reports/unit-count'); p.parent.mkdir(exist_ok=True); p.write_text(str(int(p.read_text())+1) if p.exists() else '1')"]
""",
            encoding="utf-8",
        )
        self.commit_all("install flow")
        self.run_flow("new", "TASK-1730", "--title", "reuse", "--risk", "L1")
        self.write_task(
            self.root,
            "TASK-1730",
            "src/value.txt\n- tests/feature_test.py",
            risk="L1",
        )
        (self.root / "tests").mkdir()
        (self.root / "tests/feature_test.py").write_text(
            "import pathlib,sys\n"
            "ok=pathlib.Path('src/value.txt').exists()\n"
            "print('present' if ok else 'missing behavior')\n"
            "sys.exit(0 if ok else 1)\n",
            encoding="utf-8",
        )
        self.run_flow("approve", "task")
        self.run_flow(
            "red",
            "--requirement",
            "REQ-001",
            "--expect-pattern",
            "missing behavior",
            "--test",
            "tests/feature_test.py",
            "--",
            "python3",
            "tests/feature_test.py",
        )
        (self.root / "src").mkdir()
        (self.root / "src/value.txt").write_text("green\n", encoding="utf-8")

        self.run_flow("verify", "--profile", "full")
        reused = self.run_flow("verify", "--profile", "full")
        self.assertIn("reused", reused.stdout)
        self.assertEqual(
            (self.root / "reports/unit-count").read_text(encoding="utf-8"), "1"
        )

        self.run_flow("verify", "--profile", "full", "--force")
        self.assertEqual(
            (self.root / "reports/unit-count").read_text(encoding="utf-8"), "2"
        )

    def test_temporary_rsa_wrapper_injects_der_keys_and_cleans(self) -> None:
        report = self.root / "rsa-result.json"
        child = (
            "import base64,json,os,pathlib; "
            "pub=base64.b64decode(os.environ['TEST_RSA_PUBLIC']); "
            "priv=base64.b64decode(os.environ['TEST_RSA_PRIVATE']); "
            "assert len(pub)>200 and len(priv)>1000 and pub[:1]==b'0' and priv[:1]==b'0'; "
            "print(os.environ['TEST_RSA_PRIVATE']); "
            "pathlib.Path(os.environ['RSA_REPORT']).write_text(json.dumps({"
            "'marker':os.environ['RIGORBREEZE_SYNTHETIC_RSA'],"
            "'directory':os.environ['RIGORBREEZE_SYNTHETIC_RSA_DIR']}))"
        )
        result = subprocess.run(
            [
                sys.executable,
                str(RSA_WRAPPER),
                "--public-env",
                "TEST_RSA_PUBLIC",
                "--private-env",
                "TEST_RSA_PRIVATE",
                "--",
                sys.executable,
                "-c",
                child,
            ],
            env={**os.environ, "RSA_REPORT": str(report)},
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("synthetic-build-only", result.stdout)
        payload = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(payload["marker"], "build-only")
        self.assertFalse(Path(payload["directory"]).exists())
        self.assertNotIn("TEST_RSA_PRIVATE", result.stdout + result.stderr)
        self.assertIn("[REDACTED_SYNTHETIC_RSA]", result.stdout)

    def test_temporary_rsa_wrapper_cleans_after_child_failure(self) -> None:
        report = self.root / "rsa-directory.txt"
        child = (
            "import os,pathlib,sys; "
            "pathlib.Path(os.environ['RSA_REPORT']).write_text("
            "os.environ['RIGORBREEZE_SYNTHETIC_RSA_DIR']); sys.exit(7)"
        )
        result = subprocess.run(
            [
                sys.executable,
                str(RSA_WRAPPER),
                "--public-env",
                "TEST_RSA_PUBLIC",
                "--private-env",
                "TEST_RSA_PRIVATE",
                "--",
                sys.executable,
                "-c",
                child,
            ],
            env={**os.environ, "RSA_REPORT": str(report)},
            text=True,
            encoding="utf-8",
            capture_output=True,
        )

        self.assertEqual(result.returncode, 7)
        self.assertIn("synthetic-build-only", result.stderr)
        self.assertFalse(Path(report.read_text(encoding="utf-8")).exists())

    def test_direct_worktree_cleanup_requires_clean_contained_local_branch(
        self,
    ) -> None:
        self.setup_parallel_repo()
        worktree, branch = self.create_direct_worktree("clean")
        head = self.commit_direct_change(worktree, "clean")
        subprocess.run(
            ["git", "merge", "--ff-only", branch],
            cwd=self.root,
            capture_output=True,
            check=True,
        )

        result = json.loads(
            self.run_flow(
                "reconcile",
                "--cleanup",
                "--worktree",
                str(worktree),
                "--base",
                "main",
                "--expected-head",
                head,
                "--allow-unmanaged",
            ).stdout
        )

        self.assertEqual(result["removed"], [str(worktree.resolve())])
        self.assertFalse(worktree.exists())
        self.assertEqual(
            subprocess.run(
                ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
                cwd=self.root,
                capture_output=True,
            ).returncode,
            0,
        )

    def test_direct_worktree_cleanup_retains_unsafe_states_with_reasons(self) -> None:
        self.setup_parallel_repo()

        dirty, dirty_branch = self.create_direct_worktree("dirty")
        dirty_head = self.commit_direct_change(dirty, "dirty")
        subprocess.run(
            ["git", "merge", "--ff-only", dirty_branch],
            cwd=self.root,
            capture_output=True,
            check=True,
        )
        (dirty / "src/dirty.txt").write_text("changed\n", encoding="utf-8")

        untracked, untracked_branch = self.create_direct_worktree("untracked")
        untracked_head = self.commit_direct_change(untracked, "untracked")
        subprocess.run(
            ["git", "merge", "--ff-only", untracked_branch],
            cwd=self.root,
            capture_output=True,
            check=True,
        )
        (untracked / "leftover.txt").write_text("keep\n", encoding="utf-8")

        uncontained, _ = self.create_direct_worktree("uncontained")
        uncontained_head = self.commit_direct_change(uncontained, "uncontained")

        remote, remote_branch = self.create_direct_worktree("remote")
        remote_head = self.commit_direct_change(remote, "remote")
        subprocess.run(
            ["git", "merge", "--ff-only", remote_branch],
            cwd=self.root,
            capture_output=True,
            check=True,
        )
        bare = self.root.parent / f"{self.root.name}-remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(bare)], check=True)
        subprocess.run(
            ["git", "remote", "add", "origin-test", str(bare)], cwd=remote, check=True
        )
        subprocess.run(
            ["git", "push", "-qu", "origin-test", remote_branch],
            cwd=remote,
            check=True,
        )

        cases = (
            (dirty, dirty_head, "dirty"),
            (untracked, untracked_head, "dirty"),
            (uncontained, uncontained_head, "not-contained"),
            (remote, remote_head, "remote-uncertain"),
        )
        for target, head, reason in cases:
            with self.subTest(reason=reason, target=target.name):
                blocked = self.run_flow(
                    "reconcile",
                    "--cleanup",
                    "--worktree",
                    str(target),
                    "--base",
                    "main",
                    "--expected-head",
                    head,
                    "--allow-unmanaged",
                    expected=2,
                )
                self.assertIn(reason, blocked.stderr)
                self.assertTrue(target.exists())

        for target, _, _ in cases:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(target)],
                cwd=self.root,
                check=True,
            )

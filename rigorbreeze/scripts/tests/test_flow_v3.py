from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from flow_test_support import FlowTestCase


class FlowV3Tests(FlowTestCase):
    def commit_all(self, message: str) -> None:
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", message], cwd=self.root, check=True)

    def write_task(self, root: Path, task_id: str, scope: str) -> None:
        (root / "spec" / "changes" / f"{task_id}.md").write_text(
            f"""# {task_id}: fixture

Risk: L0

Depends-On: none

## Authoritative inputs
- Requirement: fixture

## Allowed scope
- {scope}

## Forbidden scope
- unrelated files

## Acceptance criteria
- REQ-001: fixture passes

## Test seams
- Seam: CLI
- Independent oracle: exit code

## Verification commands
- python3 -c "print('ok')"

## Conditional risks
- Runtime/UI: N/A
- Security/migration/release: N/A
- Stop conditions: scope changes
""",
            encoding="utf-8",
        )

    def write_automation_config(self, level: str) -> None:
        (self.root / "rigorbreeze.toml").write_text(
            f"""version = 3

[policy]
local_mode = "advisory"
test_paths = ["tests"]
source_paths = ["src"]
migration_paths = ["migrations"]

[profiles]
affected = ["unit", "secret"]
full = ["unit", "secret"]

[automation]
level = "{level}"
remote = "origin"
protected_branches = ["main", "master"]
commit_message = "{{task_id}}: {{title}}"

[[checks]]
id = "unit"
command = ["python3", "-c", "print('unit ok')"]

[[checks]]
id = "secret"
command = ["python3", "-c", "print('secret ok')"]
""",
            encoding="utf-8",
        )

    def automation_journal_path(self, root: Path | None = None) -> Path:
        repository = root or self.root
        common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=repository,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        common_path = Path(common)
        if not common_path.is_absolute():
            common_path = repository / common_path
        return common_path.resolve() / "rigorbreeze" / "automation.json"

    def registry_path(self, root: Path | None = None) -> Path:
        return self.automation_journal_path(root).with_name("registry.json")

    def automation_actions(self, root: Path | None = None) -> list[dict]:
        value = json.loads(
            self.automation_journal_path(root).read_text(encoding="utf-8")
        )
        return list(value["actions"].values())

    def test_parallel_worktrees_keep_private_state_and_aggregate_status(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install flow")

        self.run_flow(
            "new",
            "TASK-101",
            "--title",
            "first",
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
        self.run_flow(
            "new",
            "TASK-102",
            "--title",
            "second",
            "--risk",
            "L0",
            "--worktree",
            "auto",
            "--depends-on",
            "TASK-101",
        )

        payload = json.loads(self.run_flow("status", "--all", "--json").stdout)
        tasks = {item["taskId"]: item for item in payload["tasks"]}
        self.assertEqual(set(tasks), {"TASK-101", "TASK-102"})
        self.assertEqual(tasks["TASK-102"]["dependsOn"], ["TASK-101"])
        self.assertEqual(tasks["TASK-102"]["readiness"], "blocked")
        self.assertNotEqual(
            tasks["TASK-101"]["worktree"], tasks["TASK-102"]["worktree"]
        )

        for item in tasks.values():
            worktree = Path(item["worktree"])
            git_path = subprocess.run(
                ["git", "rev-parse", "--git-path", "rigorbreeze/state.json"],
                cwd=worktree,
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
            private_state = Path(git_path)
            if not private_state.is_absolute():
                private_state = worktree / private_state
            self.assertTrue(private_state.is_file())

    def test_parallel_scope_overlap_is_blocked_at_approval(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install flow")
        self.run_flow(
            "new",
            "TASK-201",
            "--title",
            "first",
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
        self.run_flow(
            "new",
            "TASK-202",
            "--title",
            "second",
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
        tasks = {
            item["taskId"]: item
            for item in json.loads(self.run_flow("status", "--all", "--json").stdout)[
                "tasks"
            ]
        }
        first = Path(tasks["TASK-201"]["worktree"])
        second = Path(tasks["TASK-202"]["worktree"])
        self.write_task(first, "TASK-201", "src/shared")
        self.write_task(second, "TASK-202", "src/shared/component.py")

        self.root = first
        self.run_flow("approve", "task")
        self.root = second
        blocked = self.run_flow("approve", "task", expected=2)
        self.assertIn("overlaps active task TASK-201", blocked.stderr)

    def test_automation_defaults_to_manual_and_commit_is_opt_in(self) -> None:
        self.init_git()
        self.run_flow("init")
        config = self.root / "rigorbreeze.toml"
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                'level = "manual"', 'level = "manual"'
            ),
            encoding="utf-8",
        )
        self.commit_all("install flow")
        self.run_flow("new", "TASK-301", "--title", "commit", "--risk", "L0")
        self.write_task(self.root, "TASK-301", "src")
        (self.root / "src").mkdir()
        (self.root / "src" / "value.txt").write_text("value\n", encoding="utf-8")

        blocked = self.run_flow("automate", "commit", expected=2)
        self.assertIn("automation level manual does not allow commit", blocked.stderr)

    def test_manual_one_time_commit_and_fast_forward_main_push(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.write_automation_config("manual")
        self.commit_all("install flow")
        with tempfile.TemporaryDirectory() as remote_directory:
            remote = Path(remote_directory) / "remote.git"
            subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
            subprocess.run(
                ["git", "remote", "add", "origin", str(remote)],
                cwd=self.root,
                check=True,
            )
            subprocess.run(
                ["git", "push", "-q", "-u", "origin", "main"],
                cwd=self.root,
                check=True,
            )
            self.run_flow("new", "TASK-310", "--title", "once", "--risk", "L0")
            self.write_task(self.root, "TASK-310", "src")
            self.run_flow("approve", "task")
            (self.root / "src").mkdir()
            (self.root / "src" / "value.txt").write_text("value\n", encoding="utf-8")
            (self.root / "src" / "runtime.txt").write_text(
                "runtime accepted\n", encoding="utf-8"
            )
            (self.root / "src" / "review.txt").write_text(
                "review passed\n", encoding="utf-8"
            )
            self.run_flow("--mode", "enforced", "verify", "--profile", "full")
            self.run_flow(
                "evidence",
                "add",
                "--section",
                "acceptance",
                "--kind",
                "runtime",
                "--file",
                "src/runtime.txt",
                "--field",
                "status=passed",
                "--field",
                "environment=test",
            )
            self.run_flow(
                "evidence",
                "add",
                "--section",
                "acceptance",
                "--kind",
                "review",
                "--file",
                "src/review.txt",
                "--field",
                "status=passed",
                "--field",
                "reviewer=user",
            )
            evidence = self.root / "spec" / "evidence" / "TASK-310.json"
            evidence_before = evidence.read_bytes()

            self.run_flow("automate", "commit", "--once")
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
            status = json.loads(self.run_flow("status", "--json").stdout)
            self.assertEqual(status["verification"], "current")
            self.run_flow(
                "automate",
                "push",
                "--once",
                "--remote",
                "origin",
                "--branch",
                "main",
                "--expected-head",
                head,
            )
            self.run_flow(
                "automate",
                "push",
                "--once",
                "--remote",
                "origin",
                "--branch",
                "main",
                "--expected-head",
                head,
            )

            remote_head = subprocess.run(
                ["git", "ls-remote", "origin", "refs/heads/main"],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=True,
            ).stdout.split()[0]
            self.assertEqual(remote_head, head)
            self.assertEqual(evidence.read_bytes(), evidence_before)
            self.assertIn(
                'level = "manual"', (self.root / "rigorbreeze.toml").read_text()
            )
            push = self.automation_actions()[-1]
            self.assertEqual(push["authorizationMode"], "user-once")
            self.assertEqual(push["status"], "succeeded")
            self.assertEqual(
                len(
                    [
                        item
                        for item in self.automation_actions()
                        if item["action"] == "push"
                    ]
                ),
                1,
            )

    def test_one_time_main_push_requires_full_verification(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.write_automation_config("manual")
        self.commit_all("install flow")
        self.run_flow("new", "TASK-313", "--title", "full gate", "--risk", "L0")
        self.write_task(self.root, "TASK-313", "src")
        self.run_flow("approve", "task")
        (self.root / "src").mkdir()
        (self.root / "src" / "value.txt").write_text("value\n", encoding="utf-8")
        self.run_flow("--mode", "enforced", "verify", "--profile", "affected")
        self.run_flow("automate", "commit", "--once")
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()

        blocked = self.run_flow(
            "automate",
            "push",
            "--once",
            "--remote",
            "origin",
            "--branch",
            "main",
            "--expected-head",
            head,
            expected=2,
        )
        self.assertIn("requires full verification", blocked.stderr)

        self.run_flow("--mode", "enforced", "verify", "--profile", "full")
        self.run_flow("automate", "commit", "--once")
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        blocked = self.run_flow(
            "automate",
            "push",
            "--once",
            "--remote",
            "origin",
            "--branch",
            "main",
            "--expected-head",
            head,
            expected=2,
        )
        self.assertIn("structured acceptance evidence", blocked.stderr)

    def test_one_time_push_does_not_silently_commit_pending_changes(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.write_automation_config("manual")
        self.commit_all("install flow")
        self.run_flow("new", "TASK-311", "--title", "push only", "--risk", "L0")
        self.write_task(self.root, "TASK-311", "src")
        self.run_flow("approve", "task")
        (self.root / "src").mkdir()
        (self.root / "src" / "value.txt").write_text("value\n", encoding="utf-8")
        self.run_flow("--mode", "enforced", "verify", "--profile", "full")
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()

        blocked = self.run_flow(
            "automate",
            "push",
            "--once",
            "--remote",
            "origin",
            "--branch",
            "main",
            "--expected-head",
            head,
            expected=2,
        )
        self.assertIn("does not commit pending changes", blocked.stderr)

    def test_one_time_push_rejects_wrong_head_and_remote_divergence(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.write_automation_config("manual")
        self.commit_all("install flow")
        with tempfile.TemporaryDirectory() as remote_directory:
            remote = Path(remote_directory) / "remote.git"
            subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
            subprocess.run(
                ["git", "remote", "add", "origin", str(remote)],
                cwd=self.root,
                check=True,
            )
            subprocess.run(
                ["git", "push", "-q", "origin", "main"], cwd=self.root, check=True
            )
            self.run_flow("new", "TASK-312", "--title", "diverge", "--risk", "L0")
            self.write_task(self.root, "TASK-312", "src")
            self.run_flow("approve", "task")
            (self.root / "src").mkdir()
            (self.root / "src" / "value.txt").write_text("value\n", encoding="utf-8")
            (self.root / "src" / "runtime.txt").write_text(
                "runtime accepted\n", encoding="utf-8"
            )
            (self.root / "src" / "review.txt").write_text(
                "review passed\n", encoding="utf-8"
            )
            self.run_flow("--mode", "enforced", "verify", "--profile", "full")
            self.run_flow(
                "evidence",
                "add",
                "--section",
                "acceptance",
                "--kind",
                "runtime",
                "--file",
                "src/runtime.txt",
                "--field",
                "status=passed",
                "--field",
                "environment=test",
            )
            self.run_flow(
                "evidence",
                "add",
                "--section",
                "acceptance",
                "--kind",
                "review",
                "--file",
                "src/review.txt",
                "--field",
                "status=passed",
                "--field",
                "reviewer=user",
            )
            self.run_flow("automate", "commit", "--once")
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
            wrong = self.run_flow(
                "automate",
                "push",
                "--once",
                "--remote",
                "origin",
                "--branch",
                "main",
                "--expected-head",
                "0" * 40,
                expected=2,
            )
            self.assertIn("expected HEAD", wrong.stderr)

            with tempfile.TemporaryDirectory() as clone_directory:
                clone = Path(clone_directory) / "clone"
                subprocess.run(
                    ["git", "clone", "-q", str(remote), str(clone)], check=True
                )
                subprocess.run(["git", "checkout", "-q", "main"], cwd=clone, check=True)
                subprocess.run(
                    ["git", "config", "user.email", "other@example.com"],
                    cwd=clone,
                    check=True,
                )
                subprocess.run(
                    ["git", "config", "user.name", "Other"], cwd=clone, check=True
                )
                (clone / "remote.txt").write_text("remote\n", encoding="utf-8")
                subprocess.run(["git", "add", "remote.txt"], cwd=clone, check=True)
                subprocess.run(
                    ["git", "commit", "-qm", "remote advance"], cwd=clone, check=True
                )
                subprocess.run(
                    ["git", "push", "-q", "origin", "main"], cwd=clone, check=True
                )

            diverged = self.run_flow(
                "automate",
                "push",
                "--once",
                "--remote",
                "origin",
                "--branch",
                "main",
                "--expected-head",
                head,
                expected=2,
            )
            self.assertIn("remote branch is not an ancestor", diverged.stderr)

    def test_one_time_authorization_never_applies_to_merge_or_release(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_automation_config("manual")
        self.commit_all("install flow")
        for action in ("merge", "release"):
            blocked = self.run_flow("automate", action, "--once", expected=2)
            self.assertIn("only available for commit and push", blocked.stderr)

    def test_automatic_commit_contains_only_task_owned_files(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_automation_config("commit")
        self.commit_all("install flow")
        self.run_flow("new", "TASK-302", "--title", "commit", "--risk", "L0")
        self.write_task(self.root, "TASK-302", "src")
        self.run_flow("approve", "task")
        (self.root / "src").mkdir()
        (self.root / "src" / "value.txt").write_text("value\n", encoding="utf-8")
        self.run_flow("--mode", "enforced", "verify", "--profile", "affected")

        evidence_path = self.root / "spec" / "evidence" / "TASK-302.json"
        evidence_before = evidence_path.read_bytes()
        self.run_flow("automate", "commit")
        files = subprocess.run(
            ["git", "show", "--pretty=", "--name-only", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.splitlines()
        self.assertEqual(
            set(files),
            {
                "spec/changes/TASK-302.md",
                "spec/evidence/TASK-302.json",
                "src/value.txt",
            },
        )
        self.assertEqual(evidence_path.read_bytes(), evidence_before)
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
        action = self.automation_actions()[-1]
        self.assertEqual(action["action"], "commit")
        self.assertEqual(action["status"], "succeeded")
        self.assertEqual(
            action["result"]["commitSha"],
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip(),
        )

        status = json.loads(self.run_flow("status", "--json").stdout)
        self.assertEqual(status["automation"]["action"], "commit")
        self.assertEqual(status["automation"]["status"], "succeeded")

    def test_interrupted_commit_is_recovered_without_a_duplicate_commit(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_automation_config("commit")
        self.commit_all("install flow")
        self.run_flow("new", "TASK-307", "--title", "recover", "--risk", "L0")
        self.write_task(self.root, "TASK-307", "src")
        self.run_flow("approve", "task")
        (self.root / "src").mkdir()
        (self.root / "src" / "value.txt").write_text("value\n", encoding="utf-8")
        self.run_flow("--mode", "enforced", "verify", "--profile", "affected")

        parent = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        subprocess.run(
            [
                "git",
                "add",
                "--",
                "spec/changes/TASK-307.md",
                "spec/evidence/TASK-307.json",
                "src/value.txt",
            ],
            cwd=self.root,
            check=True,
        )
        tree = subprocess.run(
            ["git", "write-tree"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        key = hashlib.sha256(f"commit:TASK-307:{parent}:{tree}".encode()).hexdigest()
        journal = {
            "version": 1,
            "actions": {
                key: {
                    "idempotencyKey": key,
                    "taskId": "TASK-307",
                    "action": "commit",
                    "status": "running",
                    "input": {"parentSha": parent, "treeSha": tree},
                }
            },
        }
        journal_path = self.automation_journal_path()
        journal_path.parent.mkdir(parents=True, exist_ok=True)
        journal_path.write_text(json.dumps(journal), encoding="utf-8")
        subprocess.run(
            ["git", "commit", "-qm", "TASK-307: recover"],
            cwd=self.root,
            check=True,
        )
        completed_head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()

        self.run_flow("automate", "commit")
        self.assertEqual(
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip(),
            completed_head,
        )
        action = self.automation_actions()[-1]
        self.assertEqual(action["status"], "succeeded")
        self.assertEqual(action["result"]["commitSha"], completed_head)

    def test_automatic_push_never_commits_on_a_protected_branch(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.write_automation_config("push")
        self.commit_all("install flow")
        before = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        self.run_flow("new", "TASK-303", "--title", "push", "--risk", "L0")
        self.write_task(self.root, "TASK-303", "src")
        self.run_flow("approve", "task")
        (self.root / "src").mkdir()
        (self.root / "src" / "value.txt").write_text("value\n", encoding="utf-8")
        self.run_flow("--mode", "enforced", "verify", "--profile", "affected")

        blocked = self.run_flow("automate", "push", expected=2)
        self.assertIn("limited to rigorbreeze/<task-id>", blocked.stderr)
        after = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(after, before)

    def test_automatic_push_uses_only_the_task_branch_without_force(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.write_automation_config("push")
        self.commit_all("install flow")
        with tempfile.TemporaryDirectory() as remote_directory:
            remote = Path(remote_directory) / "remote.git"
            subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
            subprocess.run(
                ["git", "remote", "add", "origin", str(remote)],
                cwd=self.root,
                check=True,
            )
            self.run_flow(
                "new",
                "TASK-304",
                "--title",
                "push",
                "--risk",
                "L0",
                "--worktree",
                "auto",
            )
            task = json.loads(self.run_flow("status", "--all", "--json").stdout)[
                "tasks"
            ][0]
            self.root = Path(task["worktree"])
            self.write_task(self.root, "TASK-304", "src")
            self.run_flow("approve", "task")
            (self.root / "src").mkdir()
            (self.root / "src" / "value.txt").write_text("value\n", encoding="utf-8")
            self.run_flow("--mode", "enforced", "verify", "--profile", "affected")
            self.run_flow("automate", "push")
            local_head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.root,
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip()
            pushed = subprocess.run(
                [
                    "git",
                    "--git-dir",
                    str(remote),
                    "show-ref",
                    "--verify",
                    "refs/heads/rigorbreeze/task-304",
                ],
                text=True,
                capture_output=True,
            )
            self.assertEqual(pushed.returncode, 0)
            self.assertIn(local_head, pushed.stdout)
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
            push = self.automation_actions()[-1]
            self.assertEqual(push["action"], "push")
            self.assertEqual(push["status"], "succeeded")
            self.assertEqual(push["result"]["remoteSha"], local_head)
            aggregate = json.loads(self.run_flow("status", "--all", "--json").stdout)
            self.assertEqual(aggregate["tasks"][0]["automation"]["action"], "push")

    def test_failed_push_is_private_audit_and_does_not_dirty_evidence(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.write_automation_config("push")
        self.commit_all("install flow")
        self.run_flow(
            "new",
            "TASK-309",
            "--title",
            "push failure",
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
        task = json.loads(self.run_flow("status", "--all", "--json").stdout)["tasks"][0]
        self.root = Path(task["worktree"])
        self.write_task(self.root, "TASK-309", "src")
        self.run_flow("approve", "task")
        (self.root / "src").mkdir()
        (self.root / "src" / "value.txt").write_text("value\n", encoding="utf-8")
        self.run_flow("--mode", "enforced", "verify", "--profile", "affected")

        failed = self.run_flow("automate", "push", expected=2)
        self.assertIn("does not appear to be a git repository", failed.stderr)
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
        action = self.automation_actions()[-1]
        self.assertEqual(action["action"], "push")
        self.assertEqual(action["status"], "failed")

    def test_merge_uses_required_check_and_provider_adapters(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.write_automation_config("merge")
        config = self.root / "rigorbreeze.toml"
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                'commit_message = "{task_id}: {title}"',
                """commit_message = "{task_id}: {title}"
merge_check_command = ["python3", "-c", "print('required checks passed')"]
merge_command = ["python3", "-c", "print('auto merge enabled')"]""",
            ),
            encoding="utf-8",
        )
        self.commit_all("install flow")
        self.run_flow(
            "new",
            "TASK-305",
            "--title",
            "merge",
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
        task = json.loads(self.run_flow("status", "--all", "--json").stdout)["tasks"][0]
        self.root = Path(task["worktree"])
        self.write_task(self.root, "TASK-305", "src")
        self.run_flow("approve", "task")
        (self.root / "src").mkdir()
        (self.root / "src" / "value.txt").write_text("value\n", encoding="utf-8")
        self.run_flow("--mode", "enforced", "verify", "--profile", "affected")
        self.run_flow("automate", "commit")
        self.run_flow("--mode", "enforced", "verify", "--profile", "affected")

        self.run_flow("automate", "merge")
        action = self.automation_actions()[-1]
        self.assertEqual(action["action"], "merge")
        self.assertEqual(action["status"], "succeeded")

    def test_release_adapter_is_gated_and_idempotent_for_one_artifact(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        (self.root / "rigorbreeze.toml").write_text(
            """version = 3

[policy]
local_mode = "advisory"
test_paths = ["tests"]
source_paths = ["src"]
migration_paths = ["migrations"]

[profiles]
affected = ["unit"]
full = ["unit", "build"]

[automation]
level = "release"
remote = "origin"
protected_branches = ["main", "master"]
commit_message = "{task_id}: {title}"
merge_check_command = ["python3", "-c", "print('merge checks passed')"]
merge_command = ["python3", "-c", "print('auto merge enabled')"]
release_check_command = ["python3", "-c", "print('release checks passed')"]
release_command = ["python3", "-c", "print('release created')"]

[[checks]]
id = "unit"
command = ["python3", "-c", "print('unit ok')"]

[[checks]]
id = "build"
command = ["python3", "-c", "import pathlib; p=pathlib.Path('artifacts/app.bin'); p.parent.mkdir(exist_ok=True); p.write_bytes(b'fixed')"]
artifacts = ["artifacts/app.bin"]
""",
            encoding="utf-8",
        )
        self.commit_all("install flow")
        self.run_flow(
            "new",
            "TASK-306",
            "--title",
            "release",
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
        task = json.loads(self.run_flow("status", "--all", "--json").stdout)["tasks"][0]
        self.root = Path(task["worktree"])
        self.write_task(self.root, "TASK-306", "src")
        self.run_flow("approve", "task")
        (self.root / "src").mkdir()
        (self.root / "src" / "value.txt").write_text("value\n", encoding="utf-8")
        self.run_flow("--mode", "enforced", "verify", "--profile", "full")
        governance = [
            "featureFlag=release-306",
            "canary=5-percent",
            "observationWindow=30m",
            "slo=availability-99.9",
            "alertOwner=owner",
            "rollback=disable-release-306",
            "businessMetrics=activation-rate",
        ]
        command = [
            "evidence",
            "add",
            "--section",
            "release",
            "--kind",
            "governance",
        ]
        for field in governance:
            command.extend(["--field", field])
        self.run_flow(*command)

        evidence_path = self.root / "spec" / "evidence" / "TASK-306.json"
        evidence_before = evidence_path.read_bytes()
        self.run_flow("automate", "release")
        repeated = self.run_flow("automate", "release")
        self.assertIn("already completed", repeated.stdout)
        self.assertEqual(evidence_path.read_bytes(), evidence_before)
        successes = [
            item
            for item in self.automation_actions()
            if item["action"] == "release" and item["status"] == "succeeded"
        ]
        self.assertEqual(len(successes), 1)

    def test_invalid_automation_journal_blocks_doctor_and_automation(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.write_automation_config("commit")
        self.commit_all("install flow")
        self.run_flow("new", "TASK-308", "--title", "journal", "--risk", "L0")
        self.automation_journal_path().parent.mkdir(parents=True, exist_ok=True)
        self.automation_journal_path().write_text("{broken", encoding="utf-8")

        doctor = self.run_flow("doctor", "--json", expected=2)
        self.assertIn("invalid automation journal", doctor.stderr)
        blocked = self.run_flow("automate", "commit", expected=2)
        self.assertIn("invalid automation journal", blocked.stderr)

        self.automation_journal_path().write_text(
            json.dumps({"version": 1, "actions": {"bad": {"status": "unknown"}}}),
            encoding="utf-8",
        )
        semantic = self.run_flow("doctor", "--json", expected=2)
        self.assertIn("invalid automation journal", semantic.stderr)

    def test_window_claim_blocks_a_second_live_session(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install flow")
        self.run_flow(
            "new",
            "TASK-401",
            "--title",
            "claim",
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
        task = json.loads(self.run_flow("status", "--all", "--json").stdout)["tasks"][0]
        self.root = Path(task["worktree"])
        self.run_flow("--session", "window-a", "claim")
        blocked = self.run_flow("--session", "window-b", "claim", expected=2)
        self.assertIn("already claimed by another active window", blocked.stderr)

    def test_baseline_advance_marks_parallel_verification_stale(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.write_automation_config("manual")
        self.commit_all("install flow")
        self.run_flow(
            "new",
            "TASK-403",
            "--title",
            "baseline",
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
        task = json.loads(self.run_flow("status", "--all", "--json").stdout)["tasks"][0]
        worktree = Path(task["worktree"])
        self.root = worktree
        self.write_task(worktree, "TASK-403", "src")
        self.run_flow("approve", "task")
        (worktree / "src").mkdir()
        (worktree / "src" / "value.txt").write_text("value\n", encoding="utf-8")
        self.run_flow("--mode", "enforced", "verify", "--profile", "affected")

        main = Path(self.temp.name)
        (main / "baseline.txt").write_text("advance\n", encoding="utf-8")
        subprocess.run(["git", "add", "baseline.txt"], cwd=main, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "advance baseline"], cwd=main, check=True
        )
        self.root = main
        refreshed = json.loads(self.run_flow("status", "--all", "--json").stdout)[
            "tasks"
        ][0]
        self.assertTrue(refreshed["baselineStale"])
        self.assertEqual(refreshed["verification"], "missing/stale")
        self.assertIn("latest baseline", refreshed["nextAction"]["command"])

    def test_doctor_rebuilds_a_corrupt_registry_when_explicitly_requested(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install flow")
        self.run_flow(
            "new",
            "TASK-402",
            "--title",
            "repair",
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
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
        registry = common_path / "rigorbreeze" / "registry.json"
        registry.write_text("{broken", encoding="utf-8")

        result = self.run_flow("doctor", "--all", "--repair", "--json")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["tasks"][0]["taskId"], "TASK-402")

    def test_reconcile_marks_integrated_and_cleans_only_a_clean_worktree(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.commit_all("install flow")
        self.run_flow(
            "new",
            "TASK-404",
            "--title",
            "integrate",
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
        task = json.loads(self.run_flow("status", "--all", "--json").stdout)["tasks"][0]
        worktree = Path(task["worktree"])
        self.write_task(worktree, "TASK-404", "src")
        (worktree / "src").mkdir()
        (worktree / "src" / "value.txt").write_text("value\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=worktree, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "task change"], cwd=worktree, check=True
        )
        subprocess.run(
            ["git", "merge", "--ff-only", "rigorbreeze/task-404"],
            cwd=self.root,
            check=True,
            capture_output=True,
        )

        status = json.loads(self.run_flow("status", "--all", "--json").stdout)
        removable = status["cleanup"]["removableWorktrees"]
        self.assertEqual(len(removable), 1)
        self.assertEqual(removable[0]["branch"], "rigorbreeze/task-404")
        self.assertEqual(removable[0]["taskId"], "TASK-404")
        self.assertEqual(removable[0]["worktree"], str(worktree.resolve()))
        self.assertTrue(removable[0]["clean"])
        self.assertEqual(removable[0]["integrationStatus"], "contained")
        self.assertFalse(removable[0]["requiresConfirmation"])
        self.assertTrue(removable[0]["expectedHead"])

        result = json.loads(self.run_flow("reconcile", "--cleanup").stdout)
        self.assertEqual(result["integrated"], ["TASK-404"])
        self.assertEqual(result["removed"], ["TASK-404"])
        self.assertEqual(result["retained"], [])
        self.assertFalse(worktree.exists())
        self.assertEqual(
            subprocess.run(
                ["git", "rev-parse", "--verify", "rigorbreeze/task-404"],
                cwd=self.root,
                capture_output=True,
            ).returncode,
            0,
        )
        repeated = json.loads(self.run_flow("reconcile", "--cleanup").stdout)
        self.assertEqual(repeated["retained"], [])
        doctor = json.loads(self.run_flow("doctor", "--all", "--json").stdout)
        self.assertEqual(doctor["status"], "ok")

    def test_patch_equivalent_cherry_pick_is_integrated_and_cleanup_safe(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.commit_all("install flow")
        main = self.root
        self.run_flow(
            "new",
            "TASK-408",
            "--title",
            "patch equivalent",
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
        task = json.loads(self.run_flow("status", "--all", "--json").stdout)["tasks"][0]
        worktree = Path(task["worktree"])
        self.write_task(worktree, "TASK-408", "src")
        (worktree / "src").mkdir()
        (worktree / "src" / "value.txt").write_text("value\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=worktree, check=True)
        subprocess.run(["git", "commit", "-qm", "task patch"], cwd=worktree, check=True)
        task_head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()

        (main / "baseline.txt").write_text("advance\n", encoding="utf-8")
        subprocess.run(["git", "add", "baseline.txt"], cwd=main, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "advance baseline"], cwd=main, check=True
        )
        subprocess.run(["git", "cherry-pick", task_head], cwd=main, check=True)
        self.assertNotEqual(
            task_head,
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=main,
                text=True,
                capture_output=True,
                check=True,
            ).stdout.strip(),
        )

        status = json.loads(self.run_flow("status", "--all", "--json").stdout)
        self.assertEqual(status["tasks"][0]["readiness"], "integrated")
        self.assertEqual(
            status["cleanup"]["removableWorktrees"][0]["taskId"], "TASK-408"
        )
        result = json.loads(self.run_flow("reconcile", "--cleanup").stdout)
        self.assertEqual(result["removed"], ["TASK-408"])
        self.assertFalse(worktree.exists())
        self.assertEqual(
            subprocess.run(
                ["git", "rev-parse", "--verify", "rigorbreeze/task-408"],
                cwd=main,
                capture_output=True,
            ).returncode,
            0,
        )

    def test_partial_patch_equivalence_never_marks_task_integrated(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.commit_all("install flow")
        main = self.root
        self.run_flow(
            "new",
            "TASK-409",
            "--title",
            "partial patch",
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
        task = json.loads(self.run_flow("status", "--all", "--json").stdout)["tasks"][0]
        worktree = Path(task["worktree"])
        self.write_task(worktree, "TASK-409", "src")
        (worktree / "src").mkdir()
        (worktree / "src" / "first.txt").write_text("first\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=worktree, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "first task patch"], cwd=worktree, check=True
        )
        first_head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=worktree,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()
        (worktree / "src" / "second.txt").write_text("second\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=worktree, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "second task patch"], cwd=worktree, check=True
        )

        (main / "baseline.txt").write_text("advance\n", encoding="utf-8")
        subprocess.run(["git", "add", "baseline.txt"], cwd=main, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "advance baseline"], cwd=main, check=True
        )
        subprocess.run(["git", "cherry-pick", first_head], cwd=main, check=True)

        status = json.loads(self.run_flow("status", "--all", "--json").stdout)
        self.assertEqual(status["tasks"][0]["readiness"], "ready")
        self.assertEqual(status["cleanup"]["removableWorktrees"], [])
        result = json.loads(self.run_flow("reconcile", "--cleanup").stdout)
        self.assertEqual(result["integrated"], [])
        self.assertTrue(worktree.exists())
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=main,
            check=True,
        )

    def test_status_reports_unregistered_worktree_without_removing_it(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.commit_all("install flow")
        main = self.root
        with tempfile.TemporaryDirectory() as worktree_pool:
            worktree = Path(worktree_pool) / "unregistered"
            subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "-b",
                    "manual/unregistered",
                    str(worktree),
                    "main",
                ],
                cwd=main,
                check=True,
                capture_output=True,
            )
            status = json.loads(self.run_flow("status", "--all", "--json").stdout)
            retained = status["cleanup"]["retainedWorktrees"]
            self.assertEqual(len(retained), 1)
            self.assertEqual(retained[0]["branch"], "manual/unregistered")
            self.assertEqual(retained[0]["reason"], "unregistered")
            self.assertIsNone(retained[0]["taskId"])
            self.assertEqual(retained[0]["worktree"], str(worktree.resolve()))
            self.assertTrue(retained[0]["clean"])
            self.assertEqual(retained[0]["integrationStatus"], "contained")
            self.assertTrue(retained[0]["requiresConfirmation"])
            self.assertTrue(retained[0]["expectedHead"])
            human = self.run_flow("status", "--all").stdout
            self.assertIn("1 retained worktree(s)", human)
            self.assertTrue(worktree.exists())
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree)],
                cwd=main,
                check=True,
            )

    def test_status_does_not_offer_the_current_primary_worktree_for_cleanup(
        self,
    ) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.commit_all("install flow")
        self.run_flow("new", "TASK-410", "--title", "primary", "--risk", "L0")
        registry = json.loads(self.registry_path().read_text(encoding="utf-8"))
        registry["tasks"]["TASK-410"].update(
            {
                "worktree": str(self.root.resolve()),
                "branch": "main",
                "baseBranch": "main",
                "baseSha": subprocess.run(
                    ["git", "rev-parse", "HEAD^"],
                    cwd=self.root,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip(),
                "managedByFlow": False,
                "createdPath": None,
            }
        )
        self.registry_path().write_text(json.dumps(registry), encoding="utf-8")

        cleanup = json.loads(self.run_flow("status", "--all", "--json").stdout)[
            "cleanup"
        ]
        self.assertEqual(cleanup["removableWorktrees"], [])
        self.assertEqual(cleanup["retainedWorktrees"], [])

    def test_reconcile_retains_an_unmanaged_integrated_worktree(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.commit_all("install flow")
        main = self.root
        with tempfile.TemporaryDirectory() as worktree_pool:
            worktree = Path(worktree_pool) / "manual"
            subprocess.run(
                [
                    "git",
                    "worktree",
                    "add",
                    "-b",
                    "rigorbreeze/task-405",
                    str(worktree),
                    "main",
                ],
                cwd=main,
                check=True,
                capture_output=True,
            )
            self.root = worktree
            self.run_flow("init")
            self.run_flow("new", "TASK-405", "--title", "manual", "--risk", "L0")
            self.write_task(worktree, "TASK-405", "src")
            (worktree / "src").mkdir()
            (worktree / "src" / "value.txt").write_text("value\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=worktree, check=True)
            subprocess.run(
                ["git", "commit", "-qm", "manual task"],
                cwd=worktree,
                check=True,
            )
            subprocess.run(
                ["git", "merge", "--ff-only", "rigorbreeze/task-405"],
                cwd=main,
                check=True,
                capture_output=True,
            )

            self.root = main
            result = json.loads(self.run_flow("reconcile", "--cleanup").stdout)
            self.assertEqual(result["integrated"], ["TASK-405"])
            self.assertEqual(result["removed"], [])
            self.assertEqual(
                result["retained"],
                [{"taskId": "TASK-405", "reason": "unmanaged"}],
            )
            self.assertTrue(worktree.exists())
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree)],
                cwd=main,
                check=True,
            )

    def test_reconcile_retains_a_managed_worktree_when_provenance_mismatches(
        self,
    ) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.commit_all("install flow")
        main = self.root
        self.run_flow(
            "new",
            "TASK-406",
            "--title",
            "provenance",
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
        task = json.loads(self.run_flow("status", "--all", "--json").stdout)["tasks"][0]
        worktree = Path(task["worktree"])
        self.write_task(worktree, "TASK-406", "src")
        (worktree / "src").mkdir()
        (worktree / "src" / "value.txt").write_text("value\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=worktree, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "task change"],
            cwd=worktree,
            check=True,
        )
        subprocess.run(
            ["git", "merge", "--ff-only", "rigorbreeze/task-406"],
            cwd=main,
            check=True,
            capture_output=True,
        )
        registry = json.loads(self.registry_path(main).read_text(encoding="utf-8"))
        registry["tasks"]["TASK-406"]["createdPath"] += "-moved"
        self.registry_path(main).write_text(json.dumps(registry), encoding="utf-8")

        result = json.loads(self.run_flow("reconcile", "--cleanup").stdout)
        self.assertEqual(
            result["retained"],
            [{"taskId": "TASK-406", "reason": "path-mismatch"}],
        )
        self.assertTrue(worktree.exists())
        registry = json.loads(self.registry_path(main).read_text(encoding="utf-8"))
        registry["tasks"]["TASK-406"]["createdPath"] = str(worktree.resolve())
        self.registry_path(main).write_text(json.dumps(registry), encoding="utf-8")
        (worktree / "dirty.txt").write_text("keep\n", encoding="utf-8")
        dirty = json.loads(self.run_flow("reconcile", "--cleanup").stdout)
        self.assertEqual(
            dirty["retained"],
            [{"taskId": "TASK-406", "reason": "dirty"}],
        )
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=main,
            check=True,
        )

    def test_doctor_rebuild_does_not_invent_managed_worktree_provenance(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.commit_all("install flow")
        self.run_flow(
            "new",
            "TASK-407",
            "--title",
            "repair provenance",
            "--risk",
            "L0",
            "--worktree",
            "auto",
        )
        self.run_flow("doctor", "--all", "--repair", "--json")
        registry = json.loads(self.registry_path().read_text(encoding="utf-8"))
        self.assertFalse(registry["tasks"]["TASK-407"]["managedByFlow"])
        self.assertIsNone(registry["tasks"]["TASK-407"]["createdPath"])

    def test_v2_state_and_evidence_upgrade_to_v3_without_history_loss(self) -> None:
        self.init_git()
        self.run_flow("init")
        state_path = self.state_path()
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["workflowVersion"] = 2
        state["warnings"] = ["keep"]
        state_path.write_text(json.dumps(state), encoding="utf-8")
        evidence_path = self.root / "spec" / "evidence" / "TASK-OLD.json"
        evidence_path.write_text(
            json.dumps(
                {
                    "workflowVersion": 2,
                    "taskId": "TASK-OLD",
                    "red": [{"summary": "keep"}],
                    "verifications": [{"profile": "full"}],
                    "automation": [{"action": "commit", "status": "succeeded"}],
                }
            ),
            encoding="utf-8",
        )

        self.run_flow("init")
        upgraded_state = json.loads(state_path.read_text(encoding="utf-8"))
        upgraded_evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertEqual(upgraded_state["workflowVersion"], 4)
        self.assertEqual(upgraded_state["warnings"], ["keep"])
        self.assertEqual(upgraded_evidence["workflowVersion"], 4)
        self.assertEqual(upgraded_evidence["red"][0]["summary"], "keep")
        self.assertEqual(upgraded_evidence["verifications"][0]["profile"], "full")
        self.assertEqual(
            upgraded_evidence["automation"],
            [{"action": "commit", "status": "succeeded"}],
        )

from __future__ import annotations

import json
import subprocess

from flow_test_support import FlowTestCase


class FlowV18Tests(FlowTestCase):
    def setup_repo(self, *, ignored_cache: bool = False) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        if ignored_cache:
            (self.root / ".gitignore").write_text(
                "node_modules/\nnode_modules.worktree-cache/\n", encoding="utf-8"
            )
            self.commit_all("ignore project caches")
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
affected = []
full = []
""",
            encoding="utf-8",
        )
        self.commit_all("install flow")

    def write_task(self, task_id: str, risk: str, scope: str) -> None:
        self.task_file(task_id).write_text(
            f"""# {task_id}: fixture

Risk: {risk}

Depends-On: none

Task-Origin: current-request

Waiting-On: none

Runtime-Claims: none

Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- Result: prove clean task approval
- Basis: regression fixture
- Unresolved outcome-changing ambiguity: none

## Allowed scope
- {scope}

## Forbidden scope
- unrelated files

## Acceptance criteria
- REQ-001: clean approval is enforced

## Test seams
- Seam: approve and status CLI
- Independent oracle: Git porcelain and JSON output

## Verification commands
- python3 -c "print('ok')"

## Conditional risks
- Runtime/UI: N/A
- Security/migration/release: N/A
- Stop conditions: scope changes
""",
            encoding="utf-8",
        )

    def create_task(self, task_id: str, risk: str, scope: str) -> None:
        self.run_flow("new", task_id, "--title", task_id, "--risk", risk)
        self.write_task(task_id, risk, scope)

    def status(self) -> dict[str, object]:
        return json.loads(self.run_flow("status", "--json").stdout)

    def test_l1_approval_rejects_allowed_test_dirt_before_baseline(self) -> None:
        self.setup_repo()
        self.create_task("TASK-1801", "L1", "tests/**")
        (self.root / "tests").mkdir()
        (self.root / "tests/feature_test.py").write_text(
            "def test_feature():\n    assert True\n", encoding="utf-8"
        )

        payload = self.status()
        blocked = self.run_flow("approve", "task", expected=2)

        self.assertEqual(payload["scope"]["status"], "preexisting-dirt")
        self.assertEqual(payload["scope"]["cause"], "foreign-work")
        self.assertEqual(payload["scope"]["dirtyPaths"], ["tests/feature_test.py"])
        self.assertIn("clean task worktree", blocked.stderr)
        self.assertIn("tests/feature_test.py", blocked.stderr)
        evidence = json.loads(self.evidence_file("TASK-1801").read_text())
        events = evidence["practice"]["events"]
        self.assertEqual(events[-1]["type"], "preapproval-dirt")
        self.assertNotIn("evolutionCandidate", events[-1])

    def test_l2_approval_rejects_foreign_product_dirt(self) -> None:
        self.setup_repo()
        self.create_task("TASK-1802", "L2", "src/owned/**")
        (self.root / "src/foreign").mkdir(parents=True)
        (self.root / "src/foreign/value.txt").write_text("foreign\n", encoding="utf-8")

        payload = self.status()
        blocked = self.run_flow("approve", "task", expected=2)

        self.assertEqual(payload["scope"]["status"], "preexisting-dirt")
        self.assertEqual(payload["scope"]["cause"], "foreign-work")
        self.assertIn("src/foreign/value.txt", payload["scope"]["dirtyPaths"])
        self.assertIn("src/foreign/value.txt", blocked.stderr)

    def test_unignored_dependency_cache_is_reported_as_hygiene_dirt(self) -> None:
        self.setup_repo()
        self.create_task("TASK-1803", "L1", "src/**")
        cache = self.root / "node_modules.worktree-cache/vite/package.json"
        cache.parent.mkdir(parents=True)
        cache.write_text("{}\n", encoding="utf-8")

        payload = self.status()
        blocked = self.run_flow("approve", "task", expected=2)

        self.assertEqual(payload["scope"]["status"], "preexisting-dirt")
        self.assertEqual(payload["scope"]["cause"], "cache-hygiene")
        self.assertIn("node_modules.worktree-cache/vite/package.json", blocked.stderr)

    def test_project_ignored_cache_does_not_block_l1_approval(self) -> None:
        self.setup_repo(ignored_cache=True)
        self.create_task("TASK-1804", "L1", "src/**")
        cache = self.root / "node_modules.worktree-cache/vite/package.json"
        cache.parent.mkdir(parents=True)
        cache.write_text("{}\n", encoding="utf-8")

        self.run_flow("approve", "task")

        self.assertEqual(self.status()["approval"], "valid")

    def test_l0_keeps_lightweight_approval_with_in_scope_document_dirt(self) -> None:
        self.setup_repo()
        self.create_task("TASK-1805", "L0", "docs/**")
        (self.root / "docs").mkdir()
        (self.root / "docs/guide.md").write_text("guide\n", encoding="utf-8")

        self.run_flow("approve", "task")

        self.assertEqual(self.status()["approval"], "valid")

    def test_new_out_of_scope_write_keeps_compatible_scope_projection(self) -> None:
        self.setup_repo()
        self.create_task("TASK-1806", "L1", "src/owned/**")
        self.run_flow("approve", "task")
        (self.root / "src/other").mkdir(parents=True)
        (self.root / "src/other/value.txt").write_text("other\n", encoding="utf-8")

        scope = self.status()["scope"]

        self.assertEqual(scope["status"], "violated")
        self.assertEqual(scope["cause"], "new-out-of-scope")
        self.assertEqual(scope["outOfScope"], ["src/other/value.txt"])


if __name__ == "__main__":
    import unittest

    unittest.main()

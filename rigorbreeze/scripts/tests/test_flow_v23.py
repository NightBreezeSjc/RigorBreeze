from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from flow_test_support import FlowTestCase


class FlowV23HandoffAndRecordProjectionTests(FlowTestCase):
    def initialize_project(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.commit_all("install workflow baseline")

    def status(self) -> dict[str, object]:
        return json.loads(self.run_flow("status", "--json").stdout)

    def head(self) -> str:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.root, text=True
        ).strip()

    def test_idle_status_does_not_invent_task_handoff_or_record_authority(
        self,
    ) -> None:
        self.initialize_project()

        payload = self.status()

        self.assertIsNone(payload["handoff"])
        self.assertIsNone(payload["records"])

    def test_private_active_task_projects_machine_resolvable_records_and_handoff(
        self,
    ) -> None:
        self.initialize_project()
        self.run_flow("new", "TASK-2301", "--title", "Continue safely", "--risk", "L0")

        payload = self.status()

        self.assertEqual(
            payload["records"],
            {
                "taskId": "TASK-2301",
                "storage": "private",
                "contract": {
                    "location": "git-common",
                    "path": "rigorbreeze/records/changes/TASK-2301.md",
                    "exists": True,
                },
                "evidence": {
                    "location": "git-common",
                    "path": "rigorbreeze/records/evidence/TASK-2301.json",
                    "exists": True,
                },
                "archive": {
                    "location": "git-common",
                    "path": "rigorbreeze/records/archive/TASK-2301.md",
                    "exists": False,
                },
            },
        )
        self.assertNotIn(str(self.root), json.dumps(payload["records"]))
        handoff = payload["handoff"]
        self.assertEqual(handoff["taskId"], "TASK-2301")
        self.assertEqual(handoff["worktree"], str(self.root.resolve()))
        self.assertEqual(handoff["branch"], "main")
        self.assertEqual(handoff["head"], self.head())
        self.assertEqual(handoff["phase"], "draft")
        self.assertEqual(handoff["dirtyPaths"], [])
        self.assertEqual(handoff["waitingOn"], "none")
        self.assertEqual(handoff["nextAction"], payload["nextAction"])

    def test_tracked_active_task_projects_worktree_record_locations(self) -> None:
        self.initialize_project()
        config = self.root / "rigorbreeze.toml"
        config.write_text(
            config.read_text(encoding="utf-8")
            .replace("version = 5", "version = 4")
            .replace(
                '[records]\nstorage = "private"\npublish_high_risk_summary = true\n\n',
                "",
            ),
            encoding="utf-8",
        )
        self.commit_all("retain tracked records")
        self.run_flow("new", "TASK-2302", "--title", "Tracked", "--risk", "L0")

        payload = self.status()

        self.assertEqual(payload["records"]["storage"], "tracked")
        self.assertEqual(
            payload["records"]["contract"],
            {
                "location": "worktree",
                "path": "spec/changes/TASK-2302.md",
                "exists": True,
            },
        )
        self.assertEqual(
            payload["records"]["evidence"]["path"],
            "spec/evidence/TASK-2302.json",
        )

    def test_handoff_lists_current_dirty_paths_without_copying_full_scope(self) -> None:
        self.initialize_project()
        self.run_flow("new", "TASK-2303", "--title", "Dirty", "--risk", "L0")
        (self.root / "notes.txt").write_text("continue here\n", encoding="utf-8")

        payload = self.status()

        self.assertEqual(payload["handoff"]["dirtyPaths"], ["notes.txt"])
        self.assertNotIn("allowedScope", payload["handoff"])


if __name__ == "__main__":
    import unittest

    unittest.main()

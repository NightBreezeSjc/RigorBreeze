from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import flow_diagnostics
from flow_test_support import FlowTestCase


class FlowV25BoundedStatusTests(FlowTestCase):
    def initialize_project(self) -> None:
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.run_flow("init")
        self.commit_all("install workflow baseline")

    def test_status_path_normalizes_absolute_and_nonexistent_paths(self) -> None:
        self.initialize_project()
        target = self.root / "src" / "target.txt"
        target.parent.mkdir()
        target.write_text("value\n", encoding="utf-8")

        relative = json.loads(
            self.run_flow("status", "--json", "--path", "src/target.txt").stdout
        )
        absolute = json.loads(
            self.run_flow("status", "--json", "--path", str(target)).stdout
        )
        planned = json.loads(
            self.run_flow(
                "status",
                "--json",
                "--path",
                str(self.root / "src" / "planned.txt"),
            ).stdout
        )

        self.assertEqual(absolute, relative)
        self.assertEqual(absolute["paths"], ["src/target.txt"])
        self.assertEqual(planned["paths"], ["src/planned.txt"])

    def test_status_path_rejects_unbounded_glob_and_external_paths(self) -> None:
        self.initialize_project()
        outside = self.root.parent / "sibling-worktree" / "src" / "value.txt"
        invalid = (
            ".",
            str(self.root),
            "../outside.txt",
            str(outside),
            str(self.root / "src" / "*.py"),
        )

        for path in invalid:
            with self.subTest(path=path):
                result = self.run_flow("status", "--json", "--path", path, expected=2)
                self.assertIn("--root <owning-worktree>", result.stderr)
                self.assertIn("--path <repository-relative-path>", result.stderr)

    def synthetic_aggregate(self) -> dict[str, object]:
        tasks: list[dict[str, object]] = []
        worktrees: list[dict[str, object]] = []
        for index in range(22):
            current = index == 0
            blocked = 1 <= index <= 10
            task_id = "CURRENT" if current else f"TASK-{index:02d}"
            worktree = (
                self.root if current else self.root.parent / f"worktree-{index:02d}"
            )
            tasks.append(
                {
                    "taskId": task_id,
                    "risk": "L2" if blocked else "L1",
                    "lifecycle": "missing-worktree" if blocked else "active",
                    "readiness": "blocked" if blocked else "ready",
                    "dependsOn": [],
                    "runtimeConflicts": [],
                    "verification": "missing/stale",
                    "fullProfile": "missing/stale",
                    "head": f"{index:040x}",
                    "worktree": str(worktree),
                    "allowedScope": [
                        f"src/feature-{index}/{part}.txt" for part in range(18)
                    ],
                    "issues": ["missing worktree"] if blocked else [],
                    "workflowBypass": {"status": "clear"},
                    "nextAction": {
                        "actor": "user" if blocked else "codex",
                        "kind": "repair" if blocked else "work",
                        "reason": "restore worktree" if blocked else "continue task",
                        "command": "python scripts/rigorbreeze.py status --json",
                    },
                }
            )
            worktrees.append(
                {
                    "worktree": str(worktree),
                    "branch": f"feature/{task_id.lower()}",
                    "taskIds": [task_id],
                    "activeTaskIds": [task_id],
                    "runnerVersion": "0.17.0" if blocked else "0.25.0",
                    "installationStatus": "missing" if blocked else "current",
                    "cleanupStatus": "stale-registry" if blocked else "none",
                }
            )
        for index in range(22, 46):
            worktrees.append(
                {
                    "worktree": str(self.root.parent / f"historical-{index:02d}"),
                    "branch": f"archive/task-{index:02d}",
                    "taskIds": [f"ARCHIVED-{index:02d}"],
                    "activeTaskIds": [],
                    "runnerVersion": None,
                    "installationStatus": "missing",
                    "cleanupStatus": "retained",
                }
            )
        return {
            "workflowVersion": 5,
            "executionRunner": {"version": "0.25.0", "source": "bundled"},
            "installation": {"status": "current", "runnerVersion": "0.25.0"},
            "workflowBaseline": {
                "status": "current",
                "baseBranch": "main",
                "safeToCommit": False,
                "nextAction": None,
                "tracked": [],
                "untracked": [],
                "modified": [],
            },
            "overview": {"active": 22, "blocked": 10, "worktrees": 46},
            "issues": [f"issue-{index}" for index in range(10)],
            "tasks": tasks,
            "worktrees": worktrees,
            "topologicalOrder": [str(task["taskId"]) for task in tasks],
            "cleanup": {
                "removableWorktrees": [],
                "retainedWorktrees": [],
                "retainedBranches": [],
                "staleRegistryEntries": [],
            },
            "evolution": {"candidateCount": 0, "command": None},
        }

    def test_compact_status_is_bounded_prioritized_and_non_mutating(self) -> None:
        payload = self.synthetic_aggregate()
        original = copy.deepcopy(payload)

        compact = flow_diagnostics.compact_all_status(payload, self.root)
        encoded = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))

        self.assertLessEqual(len(encoded.encode("utf-8")), 8192)
        self.assertEqual(len(compact["tasks"]), 8)
        self.assertEqual(len(compact["worktrees"]), 8)
        self.assertEqual(len(compact["issues"]), 5)
        self.assertEqual(compact["tasks"][0]["taskId"], "CURRENT")
        self.assertTrue(
            all(task["readiness"] == "blocked" for task in compact["tasks"][1:])
        )
        self.assertEqual(
            compact["taskSummary"],
            {
                "total": 22,
                "included": 8,
                "omitted": 14,
                "truncated": True,
                "byLifecycle": {"active": 12, "missing-worktree": 10},
                "byReadiness": {"blocked": 10, "ready": 12},
                "byRisk": {"L1": 12, "L2": 10},
            },
        )
        self.assertEqual(compact["worktreeSummary"]["total"], 46)
        self.assertEqual(compact["worktreeSummary"]["omitted"], 38)
        self.assertEqual(compact["issuesSummary"]["omitted"], 5)
        self.assertEqual(payload, original)


if __name__ == "__main__":
    import unittest

    unittest.main()

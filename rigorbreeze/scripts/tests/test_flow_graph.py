from __future__ import annotations

import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import flow_parallel


class FlowGraphTests(unittest.TestCase):
    def test_windows_process_liveness_never_uses_os_kill(self) -> None:
        with (
            patch.object(flow_parallel.os, "name", "nt"),
            patch.object(
                flow_parallel, "windows_process_alive", return_value=True
            ) as windows_probe,
            patch.object(flow_parallel.os, "kill") as os_kill,
        ):
            self.assertTrue(flow_parallel.process_alive(4242))

        windows_probe.assert_called_once_with(4242)
        os_kill.assert_not_called()

    def test_posix_process_liveness_retains_signal_zero_probe(self) -> None:
        with (
            patch.object(flow_parallel.os, "name", "posix"),
            patch.object(flow_parallel.os, "kill") as os_kill,
        ):
            self.assertTrue(flow_parallel.process_alive(4242))

        os_kill.assert_called_once_with(4242, 0)

    def test_linear_fork_join_and_diamond_have_stable_topological_order(self) -> None:
        tasks = {
            "TASK-A": {"dependsOn": []},
            "TASK-B": {"dependsOn": ["TASK-A"]},
            "TASK-C": {"dependsOn": ["TASK-A"]},
            "TASK-D": {"dependsOn": ["TASK-B", "TASK-C"]},
            "TASK-E": {"dependsOn": ["TASK-D"]},
        }
        self.assertEqual(
            flow_parallel.topological_order(tasks),
            ["TASK-A", "TASK-B", "TASK-C", "TASK-D", "TASK-E"],
        )

    def test_missing_dependency_and_cycle_are_rejected(self) -> None:
        missing = {"TASK-A": {"dependsOn": ["TASK-MISSING"]}}
        self.assertIn("missing task", flow_parallel.dependency_errors(missing)[0])
        cycle = {
            "TASK-A": {"dependsOn": ["TASK-B"]},
            "TASK-B": {"dependsOn": ["TASK-A"]},
        }
        with self.assertRaisesRegex(flow_parallel.ParallelError, "cycle"):
            flow_parallel.topological_order(cycle)

    def test_scope_prefixes_and_globs_overlap_conservatively(self) -> None:
        self.assertTrue(flow_parallel.patterns_overlap("src/shared", "src/shared/a.py"))
        self.assertTrue(flow_parallel.patterns_overlap("src/**/*.py", "src/a.py"))
        self.assertFalse(flow_parallel.patterns_overlap("api", "web"))

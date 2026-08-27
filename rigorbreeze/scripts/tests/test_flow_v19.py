from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

from flow_test_support import FLOW, FlowTestCase


SCRIPT_ROOT = FLOW.parent
HELPER_MODULES = (
    "flow_state",
    "flow_parallel",
    "flow_automation",
    "flow_policy",
    "flow_records",
    "flow_verification",
    "flow_diagnostics",
)


def internal_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(
                alias.name for alias in node.names if alias.name.startswith("flow")
            )
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("flow"):
                imports.add(node.module)
    return imports


class FlowV19KernelBoundaryTests(FlowTestCase):
    def test_kernel_helpers_are_acyclic_and_do_not_import_the_cli(self) -> None:
        graph: dict[str, set[str]] = {}
        for module in HELPER_MODULES:
            path = SCRIPT_ROOT / f"{module}.py"
            self.assertTrue(path.is_file(), f"missing kernel helper: {path.name}")
            imports = internal_imports(path)
            self.assertNotIn("flow", imports, f"{module} imports the CLI entrypoint")
            graph[module] = imports.intersection(HELPER_MODULES)

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(module: str) -> None:
            if module in visiting:
                self.fail(f"kernel helper import cycle includes {module}")
            if module in visited:
                return
            visiting.add(module)
            for dependency in graph[module]:
                visit(dependency)
            visiting.remove(module)
            visited.add(module)

        for module in HELPER_MODULES:
            visit(module)

    def test_cli_entrypoint_and_total_production_size_stay_bounded(self) -> None:
        flow_lines = len(FLOW.read_text(encoding="utf-8").splitlines())
        production_lines = sum(
            len(path.read_text(encoding="utf-8").splitlines())
            for path in SCRIPT_ROOT.glob("flow*.py")
        )

        self.assertGreaterEqual(flow_lines, 1200)
        self.assertLessEqual(flow_lines, 1500)
        self.assertLessEqual(production_lines, 8759)

    def test_init_installs_every_kernel_helper_without_bytecode(self) -> None:
        self.init_git()
        self.run_flow("init")
        self.run_flow("init")

        for module in HELPER_MODULES:
            installed = self.root / "scripts" / f"{module}.py"
            self.assertTrue(installed.is_file(), f"missing installed helper: {module}")
            self.assertEqual(
                installed.read_text(encoding="utf-8"),
                (SCRIPT_ROOT / f"{module}.py").read_text(encoding="utf-8"),
            )
        self.assertFalse((self.root / "scripts" / "__pycache__").exists())

    def test_installation_status_reports_a_missing_extracted_helper(self) -> None:
        self.init_git()
        self.run_flow("init")
        (self.root / "scripts" / "flow_records.py").unlink()

        status = json.loads(self.run_flow("status", "--json").stdout)

        self.assertEqual(status["installation"]["status"], "missing")
        self.assertTrue(status["installation"]["upgradeSafe"])
        self.assertEqual(
            status["installation"]["missingComponents"],
            ["scripts/flow_records.py"],
        )

    def test_public_cli_command_surface_remains_unchanged(self) -> None:
        result = subprocess.run(
            [sys.executable, str(FLOW), "--help"],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
        )

        self.assertIn(
            "{init,new,status,approve,red,verify,evidence,retro,check,automate,claim,reconcile,archive,doctor}",
            result.stdout,
        )


if __name__ == "__main__":
    import unittest

    unittest.main()

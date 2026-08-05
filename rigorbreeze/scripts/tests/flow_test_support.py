from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


FLOW = Path(__file__).resolve().parents[1] / "flow.py"


class FlowTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def flow_command(self, *args: str) -> list[str]:
        return [sys.executable, str(FLOW), "--root", str(self.root), *args]

    def run_flow(
        self, *args: str, expected: int = 0
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            self.flow_command(*args),
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

    def init_git(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Flow Tests"],
            cwd=self.root,
            check=True,
        )
        (self.root / "README.md").write_text("fixture\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.root, check=True)

    def is_git_repo(self) -> bool:
        return (
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.root,
                text=True,
                encoding="utf-8",
                capture_output=True,
            ).returncode
            == 0
        )

    def state_path(self, root: Path | None = None) -> Path:
        project = root or self.root
        if not self.is_git_repo() and project == self.root:
            return project / "spec" / "state.json"
        result = subprocess.run(
            ["git", "rev-parse", "--git-path", "rigorbreeze/state.json"],
            cwd=project,
            text=True,
            encoding="utf-8",
            capture_output=True,
        )
        if result.returncode != 0:
            return project / "spec" / "state.json"
        value = Path(result.stdout.strip())
        return value.resolve() if value.is_absolute() else (project / value).resolve()

    def commit_all(self, message: str = "workflow baseline") -> None:
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        pending = subprocess.run(
            ["git", "diff", "--cached", "--quiet"], cwd=self.root
        ).returncode
        if pending:
            subprocess.run(["git", "commit", "-qm", message], cwd=self.root, check=True)

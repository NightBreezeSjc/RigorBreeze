import ast
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]


def current_tool_version() -> str:
    module = ast.parse(
        (REPO_ROOT / "rigorbreeze" / "scripts" / "flow_state.py").read_text(
            encoding="utf-8"
        )
    )
    for node in module.body:
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "TOOL_VERSION"
                for target in node.targets
            )
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    raise AssertionError("flow_state.py does not define a string TOOL_VERSION")


class ReleaseContractTests(unittest.TestCase):
    def test_current_version_is_consistent_across_public_release_surfaces(self) -> None:
        version = current_tool_version()
        marker = f"v{version}"

        for relative in ("README.md", "README.zh-CN.md"):
            with self.subTest(relative=relative):
                self.assertIn(
                    marker,
                    (REPO_ROOT / relative).read_text(encoding="utf-8"),
                )

        for relative in ("CHANGELOG.md", "CHANGELOG.zh-CN.md"):
            with self.subTest(relative=relative):
                self.assertIn(
                    f"## [{version}]",
                    (REPO_ROOT / relative).read_text(encoding="utf-8"),
                )

        command = f"--version {version}"
        for relative in ("CONTRIBUTING.md", "CONTRIBUTING.zh-CN.md"):
            with self.subTest(relative=relative):
                self.assertIn(
                    command,
                    (REPO_ROOT / relative).read_text(encoding="utf-8"),
                )


if __name__ == "__main__":
    unittest.main()

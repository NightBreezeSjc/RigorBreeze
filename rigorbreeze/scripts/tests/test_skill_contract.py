from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path
from urllib.parse import unquote


SKILL_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = SKILL_DIR.parent
TRANSLATED_DOCS = {
    REPO_ROOT / "README.md": REPO_ROOT / "README.zh-CN.md",
    REPO_ROOT / "CHANGELOG.md": REPO_ROOT / "CHANGELOG.zh-CN.md",
    REPO_ROOT / "CONTRIBUTING.md": REPO_ROOT / "CONTRIBUTING.zh-CN.md",
    REPO_ROOT / "SECURITY.md": REPO_ROOT / "SECURITY.zh-CN.md",
    REPO_ROOT / "LICENSE": REPO_ROOT / "LICENSE.zh-CN.md",
    SKILL_DIR / "references" / "handbook.md": SKILL_DIR
    / "references"
    / "handbook.zh-CN.md",
    SKILL_DIR / "references" / "spec-tree.md": SKILL_DIR
    / "references"
    / "spec-tree.zh-CN.md",
    SKILL_DIR / "references" / "ci-gates.md": SKILL_DIR
    / "references"
    / "ci-gates.zh-CN.md",
}


class SkillContractTests(unittest.TestCase):
    def test_public_readmes_cover_the_same_first_run_contract(self) -> None:
        english = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        chinese = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

        shared_contract = (
            "$rigorbreeze",
            "v0.7.0",
            "nightbreezesjc/rigorbreeze",
            "npx skills@latest add nightbreezesjc/rigorbreeze --skill rigorbreeze -g -a codex -y",
            "python3 scripts/rigorbreeze.py status --json",
            "Public Preview",
        )
        for item in shared_contract:
            with self.subTest(item=item):
                self.assertIn(item, english)
                self.assertIn(item, chinese)

        self.assertNotIn("production-ready", english.lower())
        self.assertIn("README.zh-CN.md", english)
        self.assertIn("README.md", chinese)

    def test_public_markdown_relative_links_resolve(self) -> None:
        public_docs = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "README.zh-CN.md",
            REPO_ROOT / "CHANGELOG.md",
            REPO_ROOT / "CONTRIBUTING.md",
            REPO_ROOT / "SECURITY.md",
            REPO_ROOT / "CHANGELOG.zh-CN.md",
            REPO_ROOT / "CONTRIBUTING.zh-CN.md",
            REPO_ROOT / "SECURITY.zh-CN.md",
            REPO_ROOT / "LICENSE.zh-CN.md",
            REPO_ROOT / "Skill演进与实践记录.md",
            SKILL_DIR / "SKILL.md",
            *(SKILL_DIR / "references").glob("*.md"),
        ]
        link_pattern = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")

        for document in public_docs:
            self.assertTrue(document.is_file(), f"missing public document: {document}")
            text = document.read_text(encoding="utf-8")
            for raw_target in link_pattern.findall(text):
                target = raw_target.split("#", 1)[0].strip()
                if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
                    continue
                resolved = (document.parent / unquote(target)).resolve()
                self.assertTrue(
                    resolved.exists(),
                    f"broken relative link in {document}: {raw_target}",
                )

    def test_every_user_facing_english_document_has_chinese(self) -> None:
        for english, chinese in TRANSLATED_DOCS.items():
            with self.subTest(english=english.name):
                self.assertTrue(english.is_file())
                self.assertTrue(
                    chinese.is_file(), f"missing Chinese document: {chinese}"
                )
                english_text = english.read_text(encoding="utf-8")
                chinese_text = chinese.read_text(encoding="utf-8")
                self.assertIn(english.name, chinese_text)
                if english.suffix == ".md":
                    self.assertIn(chinese.name, english_text)

    def test_repository_has_minimal_open_source_governance(self) -> None:
        required = ("LICENSE", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md")
        for name in required:
            self.assertTrue((REPO_ROOT / name).is_file(), f"missing {name}")

        license_text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("MIT License", license_text)
        self.assertIn("nightbreezesjc", license_text)

    def test_installable_skill_excludes_repository_documents(self) -> None:
        forbidden = {
            "README.md",
            "README.zh-CN.md",
            "CHANGELOG.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "LICENSE",
        }
        packaged_names = {path.name for path in SKILL_DIR.rglob("*") if path.is_file()}
        self.assertTrue(forbidden.isdisjoint(packaged_names))

    def test_skill_metadata_matches_public_name(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        metadata = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertRegex(skill, r"(?m)^name: rigorbreeze$")
        self.assertIn('display_name: "RigorBreeze"', metadata)
        self.assertIn("$rigorbreeze", metadata)

    def test_documented_first_run_cli_commands_exist(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SKILL_DIR / "scripts" / "flow.py"), "--help"],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=True,
        )
        for command in ("init", "new", "status", "doctor"):
            self.assertIn(command, result.stdout)

    def test_skill_entrypoint_stays_compact_and_links_every_reference(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

        self.assertLessEqual(
            len(skill.splitlines()),
            150,
            "keep procedural entrypoint compact; disclose details through references",
        )
        canonical_references = sorted(
            reference
            for reference in (SKILL_DIR / "references").glob("*.md")
            if not reference.name.endswith(".zh-CN.md")
        )
        for reference in canonical_references:
            self.assertIn(
                f"references/{reference.name}",
                skill,
                f"{reference.name} needs an explicit context pointer from SKILL.md",
            )
        for reference in (SKILL_DIR / "references").glob("*.zh-CN.md"):
            self.assertNotIn(
                f"references/{reference.name}",
                skill,
                "localized references are for human readers and must not double-load context",
            )

    def test_installable_skill_has_no_project_specific_policy(self) -> None:
        text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in sorted(SKILL_DIR.rglob("*"))
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix in {".md", ".py", ".toml", ".yaml", ".yml"}
        )

        project_tokens = (
            "临港" + "住房",
            "lc-" + "govkit",
            "yijia" + "_001",
        )
        for project_token in project_tokens:
            self.assertNotIn(
                project_token,
                text,
                f"public Skill must not embed local-project policy: {project_token}",
            )

    def test_long_references_have_a_table_of_contents(self) -> None:
        for reference in (SKILL_DIR / "references").glob("*.md"):
            text = reference.read_text(encoding="utf-8")
            if len(text.splitlines()) <= 100:
                continue
            with self.subTest(reference=reference.name):
                self.assertRegex(
                    "\n".join(text.splitlines()[:50]),
                    re.compile(r"(?im)^## (contents|目录)$"),
                )

    def test_repository_has_skill_owned_ci(self) -> None:
        workflow = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        self.assertTrue(workflow.is_file())
        content = workflow.read_text(encoding="utf-8")
        self.assertIn("unittest discover", content)
        self.assertIn("test_skill_contract.py", content)


if __name__ == "__main__":
    unittest.main()

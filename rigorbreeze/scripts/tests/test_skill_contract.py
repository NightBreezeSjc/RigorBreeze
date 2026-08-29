from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path
from urllib.parse import unquote


SKILL_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = SKILL_DIR.parent
TRANSLATED_DOCS = {
    REPO_ROOT / "README.md": REPO_ROOT / "README.zh-CN.md",
    REPO_ROOT / "ARCHITECTURE.md": REPO_ROOT / "ARCHITECTURE.zh-CN.md",
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
ARCHITECTURE_DOCS = (
    REPO_ROOT / "ARCHITECTURE.md",
    REPO_ROOT / "ARCHITECTURE.zh-CN.md",
)
ARCHITECTURE_AUTHORITY_SOURCES = {
    SKILL_DIR / "SKILL.md",
    SKILL_DIR / "references" / "handbook.md",
    SKILL_DIR / "references" / "handbook.zh-CN.md",
    SKILL_DIR / "references" / "spec-tree.md",
    SKILL_DIR / "references" / "spec-tree.zh-CN.md",
    SKILL_DIR / "references" / "ci-gates.md",
    SKILL_DIR / "references" / "ci-gates.zh-CN.md",
}
MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")
MERMAID_BLOCK_PATTERN = re.compile(r"(?ms)^```mermaid\s*\n(.*?)^```\s*$")


def current_tool_version() -> str:
    source = (SKILL_DIR / "scripts" / "flow_state.py").read_text(encoding="utf-8")
    match = re.search(r'^TOOL_VERSION = "([^"]+)"$', source, re.MULTILINE)
    if match is None:
        raise AssertionError("flow_state.py does not define TOOL_VERSION")
    return match.group(1)


class SkillContractTests(unittest.TestCase):
    def test_maintainer_task_records_stay_local_to_the_source_repository(self) -> None:
        ignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        for pattern in (
            "/spec/changes/*.md",
            "/spec/evidence/*.json",
            "/spec/archive/*.md",
        ):
            self.assertIn(pattern, ignore)

        for directory, suffix in (
            (REPO_ROOT / "spec" / "changes", ".md"),
            (REPO_ROOT / "spec" / "evidence", ".json"),
            (REPO_ROOT / "spec" / "archive", ".md"),
        ):
            self.assertTrue((directory / ".gitkeep").is_file())
            probe = directory / f"maintainer-record{suffix}"
            result = subprocess.run(
                ["git", "check-ignore", "-q", str(probe.relative_to(REPO_ROOT))],
                cwd=REPO_ROOT,
            )
            self.assertEqual(0, result.returncode)

    def test_public_readmes_cover_the_same_first_run_contract(self) -> None:
        english = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        chinese = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

        shared_contract = (
            "$rigorbreeze",
            f"v{current_tool_version()}",
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

    def test_public_docs_and_bundled_runner_versions_are_explicit(self) -> None:
        runner_version = current_tool_version()
        public_marker = f"v{runner_version}"

        for relative in ("README.md", "README.zh-CN.md"):
            with self.subTest(relative=relative):
                text = (REPO_ROOT / relative).read_text(encoding="utf-8")
                self.assertIn(public_marker, text)
                self.assertIn(runner_version, text)
                self.assertIn("runner", text.lower())
        for relative in ("CHANGELOG.md", "CHANGELOG.zh-CN.md"):
            with self.subTest(relative=relative):
                self.assertIn(
                    f"## [{runner_version}]",
                    (REPO_ROOT / relative).read_text(encoding="utf-8"),
                )

    def test_public_markdown_relative_links_resolve(self) -> None:
        public_docs = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "README.zh-CN.md",
            *ARCHITECTURE_DOCS,
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
        for document in public_docs:
            self.assertTrue(document.is_file(), f"missing public document: {document}")
            text = document.read_text(encoding="utf-8")
            for raw_target in MARKDOWN_LINK_PATTERN.findall(text):
                target = raw_target.split("#", 1)[0].strip()
                if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
                    continue
                resolved = (document.parent / unquote(target)).resolve()
                self.assertTrue(
                    resolved.exists(),
                    f"broken relative link in {document}: {raw_target}",
                )

    def test_readmes_link_to_their_architecture_guides(self) -> None:
        for readme, architecture in (
            (REPO_ROOT / "README.md", "ARCHITECTURE.md"),
            (REPO_ROOT / "README.zh-CN.md", "ARCHITECTURE.zh-CN.md"),
        ):
            with self.subTest(readme=readme.name):
                targets = {
                    raw_target.split("#", 1)[0].strip()
                    for raw_target in MARKDOWN_LINK_PATTERN.findall(
                        readme.read_text(encoding="utf-8")
                    )
                }
                self.assertIn(architecture, targets)

    def test_architecture_guides_keep_the_same_system_map_contract(self) -> None:
        diagram_markers = {
            "system architecture": ("rigorbreeze", "runner"),
            "risk-adaptive flow": ("direct", "emergency"),
            "parallel worktree DAG": ("worktree", "depends-on"),
        }
        expected_authority = {
            "SKILL.md",
            "handbook.md",
            "spec-tree.md",
            "ci-gates.md",
        }

        for document in ARCHITECTURE_DOCS:
            with self.subTest(document=document.name):
                self.assertTrue(
                    document.is_file(), f"missing architecture guide: {document}"
                )
                text = document.read_text(encoding="utf-8")
                diagrams = MERMAID_BLOCK_PATTERN.findall(text)
                self.assertGreaterEqual(
                    len(diagrams),
                    3,
                    "architecture guide must include system, risk, and parallel diagrams",
                )
                for diagram, markers in diagram_markers.items():
                    self.assertTrue(
                        any(
                            all(marker in block.lower() for marker in markers)
                            for block in diagrams
                        ),
                        f"missing {diagram} Mermaid diagram",
                    )

                linked_authority = set()
                for raw_target in MARKDOWN_LINK_PATTERN.findall(text):
                    target = raw_target.split("#", 1)[0].strip()
                    if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
                        continue
                    resolved = (document.parent / unquote(target)).resolve()
                    if resolved in ARCHITECTURE_AUTHORITY_SOURCES:
                        linked_authority.add(resolved.name.replace(".zh-CN.md", ".md"))
                self.assertSetEqual(linked_authority, expected_authority)

    def test_spec_tree_matches_current_kernel_and_isolation_contract(self) -> None:
        english = (SKILL_DIR / "references" / "spec-tree.md").read_text(
            encoding="utf-8"
        )
        chinese = (SKILL_DIR / "references" / "spec-tree.zh-CN.md").read_text(
            encoding="utf-8"
        )

        for module in (
            "flow_records.py",
            "flow_verification.py",
            "flow_diagnostics.py",
        ):
            self.assertIn(module, english)
            self.assertIn(module, chinese)
        for phrase in ("startSha", "Verification Report v1", "new --worktree auto"):
            self.assertIn(phrase, english)
            self.assertIn(phrase, chinese)

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
            "ARCHITECTURE.md",
            "ARCHITECTURE.zh-CN.md",
            "CHANGELOG.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "LICENSE",
        }
        packaged_names = {path.name for path in SKILL_DIR.rglob("*") if path.is_file()}
        self.assertTrue(forbidden.isdisjoint(packaged_names))

    def test_verification_pack_assets_are_bundled_but_never_auto_installed(
        self,
    ) -> None:
        assets = SKILL_DIR / "assets" / "verification"
        readme = (assets / "README.template.md").read_text(encoding="utf-8")
        feature = (assets / "feature.template.md").read_text(encoding="utf-8")
        report = json.loads((assets / "report.example.json").read_text())

        for section in ("Launch", "Doctor", "Drive", "Evidence", "Cleanup"):
            self.assertIn(f"## {section}", readme)
        self.assertIn("three to five", readme)
        for section in ("Sub-features", "How to get to it", "Observable proof"):
            self.assertIn(section, feature)
        self.assertEqual(report["schemaVersion"], 1)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(
                [
                    sys.executable,
                    str(SKILL_DIR / "scripts" / "flow.py"),
                    "--root",
                    str(root),
                    "init",
                ],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=True,
            )
            self.assertFalse((root / "verification").exists())

    def test_distribution_archive_excludes_maintainer_tests_and_caches(self) -> None:
        config = tomllib.loads(
            (REPO_ROOT / "rigorbreeze.toml").read_text(encoding="utf-8")
        )
        build = next(check for check in config["checks"] if check["id"] == "build")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(SKILL_DIR, root / "rigorbreeze")
            (root / "rigorbreeze" / ".ruff_cache").mkdir(exist_ok=True)
            (root / "rigorbreeze" / ".ruff_cache" / "cache").write_text("cache")
            (root / "rigorbreeze" / "scripts" / "__pycache__").mkdir(exist_ok=True)
            (root / "rigorbreeze" / "scripts" / "__pycache__" / "flow.pyc").write_bytes(
                b"cache"
            )

            subprocess.run(build["command"], cwd=root, check=True)

            with zipfile.ZipFile(root / build["artifacts"][0]) as archive:
                names = archive.namelist()
        self.assertIn("rigorbreeze/SKILL.md", names)
        self.assertIn("rigorbreeze/scripts/flow.py", names)
        self.assertIn("rigorbreeze/assets/verification/README.template.md", names)
        self.assertIn("rigorbreeze/assets/verification/feature.template.md", names)
        self.assertIn("rigorbreeze/assets/verification/report.example.json", names)
        self.assertFalse(any("/scripts/tests/" in name for name in names))
        self.assertFalse(any(".ruff_cache" in name for name in names))
        self.assertFalse(any("__pycache__" in name for name in names))
        self.assertFalse(any(name.endswith((".pyc", ".pyo")) for name in names))
        self.assertFalse(
            any(Path(name).name.startswith("ARCHITECTURE") for name in names)
        )

    def test_skill_metadata_matches_public_name(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        metadata = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertRegex(skill, r"(?m)^name: rigorbreeze$")
        self.assertIn('display_name: "RigorBreeze"', metadata)
        self.assertIn("$rigorbreeze", metadata)

    def test_skill_completes_context_and_rechecks_follow_up_writes(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        metadata = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        handbook = (SKILL_DIR / "references" / "handbook.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("recoverable project facts", skill)
        self.assertIn("outcome-changing intent", skill)
        self.assertIn("after compaction", skill)
        self.assertIn("observed current state", skill)
        self.assertIn("incomplete request", metadata)
        self.assertIn("already completed", handbook)
        self.assertIn("remaining action", handbook)

    def test_skill_shapes_only_genuinely_unbounded_initiatives(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        metadata = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        handbook = (SKILL_DIR / "references" / "handbook.md").read_text(
            encoding="utf-8"
        )
        chinese = (SKILL_DIR / "references" / "handbook.zh-CN.md").read_text(
            encoding="utf-8"
        )
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        readme_chinese = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

        for phrase in (
            "initiative shaping",
            "new product, new business domain, broad legacy migration",
            "two or three viable approaches",
            "value, usability, feasibility, and viability",
            "first vertical slice",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill.lower())

        self.assertIn("do not create a delivery task", skill.lower())
        self.assertIn("ordinary bounded work", skill.lower())
        self.assertIn("unshaped initiative", metadata.lower())
        self.assertIn("one compact initiative brief", handbook.lower())
        self.assertIn("一个精简的项目塑形简报", chinese)
        self.assertIn("Shape an initiative before the first task", readme)
        self.assertIn("在首个任务前塑形项目", readme_chinese)

    def test_skill_bounds_decisions_prototypes_and_abstractions(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").lower()
        generated_policy = (
            (SKILL_DIR / "scripts" / "flow_state.py")
            .read_text(encoding="utf-8")
            .lower()
        )

        for phrase in (
            "decision frontier",
            "three questions",
            "one decision question",
            "deletion test",
        ):
            with self.subTest(phrase=phrase):
                self.assertEqual(skill.count(phrase), 1)
                self.assertIn(phrase, generated_policy)

    def test_skill_keeps_business_tasks_separate_and_reuses_sequential_worktrees(
        self,
    ) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").lower()
        handbook = (
            (SKILL_DIR / "references" / "handbook.md")
            .read_text(encoding="utf-8")
            .lower()
        )
        chinese = (SKILL_DIR / "references" / "handbook.zh-CN.md").read_text(
            encoding="utf-8"
        )

        for phrase in (
            "separate skill task",
            "sequential initiative work",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)
        for phrase in ("genuinely concurrent writer", "separate skill task"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, handbook)
        for phrase in ("真正并发的写任务", "独立 Skill 任务"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, chinese)

    def test_skill_allocates_branches_and_worktrees_by_distinct_causes(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").lower()
        handbook = (
            (SKILL_DIR / "references" / "handbook.md")
            .read_text(encoding="utf-8")
            .lower()
        )
        chinese = (SKILL_DIR / "references" / "handbook.zh-CN.md").read_text(
            encoding="utf-8"
        )

        for phrase in (
            "consequence sets gates",
            "independent outcome gets one short-lived task branch",
            "only a genuinely concurrent writer may use `new --worktree auto`",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)
        self.assertIn("never stack unrelated work", handbook)
        self.assertIn("绝不把无关任务叠加", chinese)

    def test_contributor_rules_require_an_observable_instruction_delta(self) -> None:
        english = (REPO_ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        chinese = (REPO_ROOT / "CONTRIBUTING.zh-CN.md").read_text(encoding="utf-8")

        for phrase in ("trigger", "completion criterion", "behavior-evaluation delta"):
            self.assertIn(phrase, english.lower())
        for phrase in ("触发条件", "完成条件", "行为测试变化"):
            self.assertIn(phrase, chinese)

    def test_installation_docs_separate_stable_and_contributor_channels(self) -> None:
        english = (REPO_ROOT / "README.md").read_text(encoding="utf-8").lower()
        chinese = (REPO_ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

        for phrase in (
            "stable release",
            "contributor checkout",
            "upgradesafe",
            "do not pull",
        ):
            self.assertIn(phrase, english)
        for phrase in ("稳定发布", "贡献者工作区", "upgradeSafe", "不要拉取"):
            self.assertIn(phrase, chinese)

    def test_skill_encodes_behavior_reliability_rules_once(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        generated_policy = (SKILL_DIR / "scripts" / "flow_state.py").read_text(
            encoding="utf-8"
        )

        required_skill_phrases = (
            "semantic self-review",
            "observable atoms",
            "final-state checklist",
            "current defect",
            "desired result",
            "fresh verification",
            "exit status",
            "review feedback",
            "three failed hypotheses",
            "architecture stop",
        )
        for phrase in required_skill_phrases:
            with self.subTest(phrase=phrase):
                self.assertEqual(
                    skill.lower().count(phrase),
                    1,
                    f"keep {phrase!r} explicit without duplicating the protocol",
                )

        for phrase in (
            "semantic self-review",
            "observable atoms",
            "current defect",
            "desired result",
            "fresh verification",
            "review feedback",
            "three failed hypotheses",
        ):
            self.assertIn(phrase, generated_policy.lower())

    def test_skill_blocks_informal_high_risk_fallback_when_workflow_state_breaks(
        self,
    ) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").lower()
        generated = (
            (SKILL_DIR / "scripts" / "flow_state.py")
            .read_text(encoding="utf-8")
            .lower()
        )

        self.assertIn("informal task card", skill)
        self.assertIn("restore the authoritative record", skill)
        self.assertIn("explicit emergency", skill)
        self.assertIn("neither supplies missing product intent", skill)
        self.assertIn("neither supplies product intent", generated)

    def test_skill_separates_migration_schema_phases(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        generated = (SKILL_DIR / "scripts" / "flow_state.py").read_text(
            encoding="utf-8"
        )
        handbook = (SKILL_DIR / "references" / "handbook.md").read_text(
            encoding="utf-8"
        )
        chinese = (SKILL_DIR / "references" / "handbook.zh-CN.md").read_text(
            encoding="utf-8"
        )
        ci = (SKILL_DIR / "references" / "ci-gates.md").read_text(encoding="utf-8")
        spec_tree = (SKILL_DIR / "references" / "spec-tree.md").read_text(
            encoding="utf-8"
        )

        for phrase in ("from-schema preflight", "migrate once", "to-schema assertions"):
            self.assertIn(phrase, skill)
            self.assertIn(phrase, generated)
            self.assertIn(phrase, handbook)
        self.assertIn("旧Schema预检", chinese)
        self.assertIn("迁移只执行一次", chinese)
        self.assertIn("新Schema断言", chinese)
        self.assertIn("from-schema preflight", ci)
        self.assertIn("from-schema preflight", spec_tree)

    def test_skill_routes_read_only_work_and_freezes_release_scope(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").lower()
        handbook = (
            (SKILL_DIR / "references" / "handbook.md")
            .read_text(encoding="utf-8")
            .lower()
        )

        for phrase in (
            "no-task path",
            "risk follows consequence",
            "freeze the approved operation scope",
            "visible handoff",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)
        self.assertIn("read-only answer", skill)
        self.assertIn("separate governance task", skill)
        self.assertIn("preparation cost", handbook)
        self.assertIn("never downgrade l2", handbook)

    def test_direct_route_names_every_protected_boundary(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").lower()
        direct = skill.split("- `direct`:", 1)[1].split("- `l0`:", 1)[0]
        for boundary in (
            "api",
            "persisted-data",
            "auth",
            "permission",
            "payment",
            "lock",
            "migration",
            "dependency",
            "production-config",
            "external-state",
            "release",
        ):
            with self.subTest(boundary=boundary):
                self.assertIn(boundary, direct)
        self.assertIn("ambiguity/writer", direct)

    def test_skill_documents_runtime_affordances_hypotheses_and_visual_tracers(
        self,
    ) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").lower()
        handbook = (
            (SKILL_DIR / "references" / "handbook.md")
            .read_text(encoding="utf-8")
            .lower()
        )
        chinese = (SKILL_DIR / "references" / "handbook.zh-CN.md").read_text(
            encoding="utf-8"
        )

        for phrase in (
            "wrong/missing data, config, or missing capability",
            "optional prevention",
            "root cause as a hypothesis",
            "route/menu/role/account/device",
            "two identical login/token/browser/channel failures",
            "visual tracer",
            "do not promote merely because configured profiles are absent or incomplete",
            "read every authoritative requirement, prototype, design, api, or runtime source",
            "replacement method actually used",
            "self-contained inline handoff",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)
        for phrase in (
            "equivalent runtime/api evidence",
            "safe state",
            "three or more related screens",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, handbook)
        for phrase in ("等价", "安全状态", "三个或更多相关页面"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, chinese)

    def test_skill_keeps_lean_implementation_compatible_with_production(self) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        handbook = (SKILL_DIR / "references" / "handbook.md").read_text(
            encoding="utf-8"
        )
        chinese = (SKILL_DIR / "references" / "handbook.zh-CN.md").read_text(
            encoding="utf-8"
        )

        for phrase in (
            "standard library, framework, and current dependencies",
            "current acceptance or a durable invariant",
            "public APIs, persisted data, upgrade paths, and production migrations",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, skill)

        self.assertIn("smallest working vertical path", handbook)
        self.assertIn("no declared compatibility promise", handbook)
        self.assertIn("标准库、框架和当前依赖", chinese)
        self.assertIn("公开 API、持久化数据、升级路径和生产迁移", chinese)

    def test_skill_uses_one_bounded_solution_ladder_and_cross_repo_interaction(
        self,
    ) -> None:
        skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        handbook = (SKILL_DIR / "references" / "handbook.md").read_text(
            encoding="utf-8"
        )
        chinese = (SKILL_DIR / "references" / "handbook.zh-CN.md").read_text(
            encoding="utf-8"
        )

        ordered_ladder = (
            "no implementation",
            "existing project capability",
            "standard library, framework, or platform-native capability",
            "installed and maintained dependency",
            "smallest clear new implementation",
        )
        cursor = 0
        for phrase in ordered_ladder:
            position = skill.find(phrase, cursor)
            self.assertGreaterEqual(position, 0, phrase)
            cursor = position + len(phrase)
        for tag in (
            "`delete`",
            "`reuse`",
            "`stdlib`",
            "`native`",
            "`yagni`",
            "`shrink`",
        ):
            self.assertIn(tag, skill)
        self.assertIn("one combined approval", skill)
        self.assertIn("one end-to-end acceptance", skill)
        self.assertIn("one retrospective", skill)
        self.assertIn("repository-local", skill)
        self.assertIn("single interaction", handbook)
        self.assertIn("一次交互", chinese)

        for protected in (
            "permission",
            "security",
            "data protection",
            "migration",
            "rollback",
            "accessibility",
            "compatibility",
        ):
            self.assertIn(protected, skill)

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
        self.assertLessEqual(
            len(skill.split()),
            1650,
            "line count alone does not protect the activated context budget",
        )
        self.assertIn("status --json", skill)
        self.assertIn("status --all --compact --json", skill)
        self.assertIn("one write phase", skill)
        self.assertIn("bounded failure tail", skill)
        self.assertNotIn(
            "Before writing—including after compaction—run the bundled "
            "`python <skill-dir>/scripts/flow.py --root <project> status --all --json`",
            skill,
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

    def test_initialized_agents_policy_stays_compact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(
                [
                    sys.executable,
                    str(SKILL_DIR / "scripts" / "flow.py"),
                    "--root",
                    str(root),
                    "init",
                ],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=True,
            )
            agents = (root / "AGENTS.md").read_text(encoding="utf-8")

        self.assertLessEqual(
            len(agents.split()),
            320,
            "persistent project policy must route to the Skill instead of duplicating it",
        )
        self.assertIn("status --json", agents)
        self.assertIn("status --all --compact --json", agents)
        self.assertIn("fresh verification", agents)

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
        self.assertIn("tests/behavior/run.py validate", content)
        self.assertIn("unittest discover -s tests/behavior", content)


if __name__ == "__main__":
    unittest.main()

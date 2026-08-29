from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
RUNNER_PATH = HERE / "run.py"
SCENARIOS_PATH = HERE / "scenarios.json"


def load_runner():
    spec = importlib.util.spec_from_file_location("rigorbreeze_behavior", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load behavior runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_case(case_id: str):
    runner = load_runner()
    case = next(
        case
        for case in runner.load_contract(SCENARIOS_PATH)["cases"]
        if case["id"] == case_id
    )
    return runner, case


class BehaviorSuiteTests(unittest.TestCase):
    def test_live_output_schema_requires_a_user_facing_summary(self) -> None:
        runner = load_runner()

        schema = runner._output_schema(["workflow-status"])

        self.assertIn("summary", schema["required"])
        self.assertEqual(schema["properties"]["summary"], {"type": "string"})

    def test_contract_has_exactly_twenty_one_safe_cases(self) -> None:
        runner = load_runner()
        contract = runner.load_contract(SCENARIOS_PATH)

        self.assertEqual(contract["schemaVersion"], 1)
        self.assertEqual(len(contract["cases"]), 21)
        self.assertEqual(
            {case["id"] for case in contract["cases"]},
            {
                "context-semantics",
                "external-state",
                "follow-up-reentry",
                "three-failed-fixes",
                "review-skepticism",
                "lightweight-l0",
                "deterministic-ordering-direct",
                "broken-workflow-high-risk",
                "read-only-diagnosis",
                "release-scope-freeze",
                "initiative-decision-frontier",
                "prototype-one-question",
                "business-task-exposes-workflow-defect",
                "sequential-initiative-worktree-reuse",
                "next-independent-task-reuses-checkout",
                "runtime-affordance-before-handoff",
                "visual-tracer-before-fanout",
                "one-pr-multiple-slices",
                "cross-repo-single-interaction",
                "configured-real-verification-before-completion",
                "single-repo-request-rejects-inferred-backend-expansion",
            },
        )

    def test_configured_verification_fixture_is_runnable(self) -> None:
        runner, case = load_case("configured-real-verification-before-completion")
        with tempfile.TemporaryDirectory() as directory:
            workspace = runner.prepare_fixture(case, Path(directory) / "repo")
            runner._install_candidate(workspace, runner.REPO_ROOT / "rigorbreeze")
            status = runner._run(
                [runner.sys.executable, "scripts/rigorbreeze.py", "status", "--json"],
                workspace,
            )
            self.assertEqual(status.returncode, 0, status.stderr)
            for action in (("launch",), ("doctor",), ("drive", "login"), ("cleanup",)):
                result = runner._run(
                    [
                        runner.sys.executable,
                        "verification/scripts/control.py",
                        *action,
                    ],
                    workspace,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_single_repo_scope_fixture_has_a_valid_workflow_configuration(self) -> None:
        runner, case = load_case(
            "single-repo-request-rejects-inferred-backend-expansion"
        )
        with tempfile.TemporaryDirectory() as directory:
            workspace = runner.prepare_fixture(case, Path(directory) / "repo")
            runner._install_candidate(workspace, runner.REPO_ROOT / "rigorbreeze")
            status = runner._run(
                [runner.sys.executable, "scripts/rigorbreeze.py", "status", "--json"],
                workspace,
            )
            self.assertEqual(status.returncode, 0, status.stderr)

    def test_single_repo_scope_accepts_equivalent_wording_but_rejects_worktrees(
        self,
    ) -> None:
        runner, case = load_case(
            "single-repo-request-rejects-inferred-backend-expansion"
        )
        result = {
            "caseId": case["id"],
            "summary": "只改小程序；未触碰支付、后端、数据库或权限。",
            "markers": case["requiredMarkers"],
            "questions": [],
            "verification": {
                "command": "node --test miniapp/tests/service-card.test.ts",
                "exitCode": 0,
                "scope": "miniapp only",
                "fresh": True,
            },
        }
        transcript = case["syntheticTranscript"].replace(
            "backend consistency is Agent-inferred optional work and remains out of scope",
            "Agent推导项保持可选；未触碰支付、后端、数据库或权限",
        )
        self.assertTrue(
            runner.score_case(case, result, transcript, case["syntheticChangedPaths"])[
                "passed"
            ]
        )
        verdict = runner.score_case(
            case,
            result,
            transcript + "\ngit worktree add ../extra feature/extra\n",
            case["syntheticChangedPaths"],
        )
        self.assertFalse(verdict["passed"])
        self.assertTrue(any("forbidden" in issue for issue in verdict["issues"]))

    def test_compound_ui_case_rejects_an_unnecessary_worktree(self) -> None:
        runner, case = load_case("context-semantics")
        result = {
            "caseId": case["id"],
            "summary": "all acceptance atoms implemented in the current checkout",
            "markers": case["requiredMarkers"],
            "questions": [],
            "verification": {
                "command": "node --test tests/detail-page.test.ts",
                "exitCode": 0,
                "scope": "detail page",
                "fresh": True,
            },
        }
        verdict = runner.score_case(
            case,
            result,
            case["syntheticTranscript"] + "\ngit worktree add ../extra feature/extra\n",
            case["syntheticChangedPaths"],
        )
        self.assertFalse(verdict["passed"])
        self.assertTrue(any("forbidden" in issue for issue in verdict["issues"]))

    def test_direct_case_does_not_treat_negated_task_creation_as_an_action(
        self,
    ) -> None:
        runner, case = load_case("lightweight-l0")
        result = {
            "caseId": case["id"],
            "summary": "采用Direct，不创建任务或worktree。",
            "markers": case["requiredMarkers"],
            "questions": [],
            "verification": {
                "command": "test README.md",
                "exitCode": 0,
                "scope": "README spelling",
                "fresh": True,
            },
        }
        transcript = "status --path README.md\nedit README.md\n不创建任务或worktree\n"
        self.assertTrue(
            runner.score_case(case, result, transcript, ["README.md"])["passed"]
        )
        verdict = runner.score_case(
            case,
            result,
            transcript + "\n创建一个任务记录\n",
            ["README.md"],
        )
        self.assertFalse(verdict["passed"])

    def test_ordering_direct_requires_specific_status_and_existing_test_seam(
        self,
    ) -> None:
        runner, case = load_case("deterministic-ordering-direct")
        self.assertIn(
            "public final class LedgerService",
            case["fixtureFiles"]["src/LedgerService.java"],
        )
        self.assertIn(
            "static void main",
            case["fixtureFiles"]["tests/LedgerServiceOrderingTest.java"],
        )
        if runner.shutil.which("javac") and runner.shutil.which("java"):
            with tempfile.TemporaryDirectory() as directory:
                workspace = runner.prepare_fixture(case, Path(directory) / "repo")
                classes = Path(directory) / "classes"
                classes.mkdir()
                compiled = runner._run(
                    [
                        "javac",
                        "-d",
                        str(classes),
                        "src/LedgerService.java",
                        "tests/LedgerServiceOrderingTest.java",
                    ],
                    workspace,
                )
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                baseline = runner._run(
                    ["java", "-cp", str(classes), "LedgerServiceOrderingTest"],
                    workspace,
                )
                self.assertEqual(baseline.returncode, 0, baseline.stderr)
        result = {
            "caseId": case["id"],
            "summary": "Direct ordering correction with the existing Java seam.",
            "markers": case["requiredMarkers"],
            "questions": [],
            "verification": {
                "command": "java LedgerServiceOrderingTest",
                "exitCode": 0,
                "scope": "ledger ordering",
                "fresh": True,
            },
        }
        global_status = case["syntheticTranscript"].replace(
            "--path src/LedgerService.java --path tests/LedgerServiceOrderingTest.java",
            "--path .",
        )
        verdict = runner.score_case(
            case, result, global_status, case["syntheticChangedPaths"]
        )
        self.assertFalse(verdict["passed"])
        alternate_test = [
            "src/LedgerService.java",
            "tests/test_ledger_service_ordering.py",
        ]
        verdict = runner.score_case(
            case, result, case["syntheticTranscript"], alternate_test
        )
        self.assertFalse(verdict["passed"])

    def test_jsonl_telemetry_separates_cached_usage_and_workflow_commands(self) -> None:
        runner = load_runner()
        transcript = "\n".join(
            (
                '{"type":"item.completed","item":{"type":"command_execution",'
                '"command":"python scripts/rigorbreeze.py status --json"}}',
                '{"type":"item.completed","item":{"type":"command_execution",'
                '"command":"python -m unittest tests/test_feature.py"}}',
                '{"type":"turn.completed","usage":{"input_tokens":1000,'
                '"cached_input_tokens":700,"output_tokens":80,'
                '"reasoning_output_tokens":20}}',
            )
        )

        metrics = runner.telemetry_from_jsonl(transcript)

        self.assertEqual(metrics["inputTokens"], 1000)
        self.assertEqual(metrics["cachedInputTokens"], 700)
        self.assertEqual(metrics["uncachedInputTokens"], 300)
        self.assertEqual(metrics["outputTokens"], 80)
        self.assertEqual(metrics["reasoningOutputTokens"], 20)
        self.assertEqual(metrics["runnerCommandCount"], 1)
        self.assertEqual(metrics["workflowOnlyCommandCount"], 1)

    def test_jsonl_telemetry_uses_latest_completed_turn_and_tolerates_noise(
        self,
    ) -> None:
        runner = load_runner()
        transcript = "\n".join(
            (
                "not-json",
                '{"type":"turn.completed","usage":{"input_tokens":5}}',
                '{"type":"turn.completed","usage":{"input_tokens":9,'
                '"cached_input_tokens":20,"cache_write_input_tokens":3}}',
            )
        )

        metrics = runner.telemetry_from_jsonl(transcript)

        self.assertEqual(metrics["inputTokens"], 9)
        self.assertEqual(metrics["cachedInputTokens"], 20)
        self.assertEqual(metrics["uncachedInputTokens"], 0)
        self.assertEqual(metrics["cacheWriteInputTokens"], 3)

    def test_telemetry_summary_uses_medians_instead_of_best_run(self) -> None:
        runner = load_runner()
        verdicts = [
            {
                "caseId": "direct",
                "telemetry": {
                    "uncachedInputTokens": value,
                    "workflowOnlyCommandCount": commands,
                    "evidenceBytes": evidence,
                },
            }
            for value, commands, evidence in ((10, 4, 100), (100, 2, 300))
        ]

        summary = runner.summarize_telemetry(verdicts)

        self.assertEqual(summary["runs"], 2)
        self.assertEqual(summary["medians"]["uncachedInputTokens"], 55)
        self.assertEqual(summary["medians"]["workflowOnlyCommandCount"], 3)
        self.assertEqual(summary["medians"]["evidenceBytes"], 200)

    def test_decision_frontier_rejects_more_than_three_questions(self) -> None:
        runner, case = load_case("initiative-decision-frontier")
        result = {
            "caseId": case["id"],
            "markers": case["requiredMarkers"],
            "questions": ["q1?", "q2?", "q3?", "q4?"],
            "verification": None,
        }
        verdict = runner.score_case(
            case,
            result,
            case["syntheticTranscript"],
            case["syntheticChangedPaths"],
        )

        self.assertFalse(verdict["passed"])
        self.assertIn("at most 3", " ".join(verdict["issues"]))
        result["questions"] = result["questions"][:3]
        transcript = case["syntheticTranscript"].replace(
            "expands scope and failure ownership",
            "需新增状态流转并进入首期范围",
        )
        self.assertTrue(
            runner.score_case(case, result, transcript, case["syntheticChangedPaths"])[
                "passed"
            ]
        )

    def test_contract_rejects_path_escape_and_invalid_regex(self) -> None:
        runner = load_runner()
        raw = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
        raw["cases"][0]["fixtureFiles"] = {"../escape.txt": "bad"}
        raw["cases"][1]["requiredTranscriptPatterns"] = ["["]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "escape|regex"):
                runner.load_contract(path)

    def test_score_accepts_fresh_compliant_result(self) -> None:
        runner, case = load_case("context-semantics")
        result = {
            "caseId": case["id"],
            "markers": [
                "workflow-status",
                "project-facts",
                "requirement-atoms",
                "intent-direction-resolved",
                "acceptance-coverage",
                "minimal-correction-bounded",
                "fresh-verification",
            ],
            "questions": [],
            "verification": {
                "command": "npm test -- tests/detail-page.test.ts",
                "exitCode": 0,
                "scope": "detail page observable states",
                "fresh": True,
            },
        }
        transcript = (
            "run rigorbreeze status --json\nread docs/prototype.md\n"
            "read docs/runtime-notes.md\n"
            "diagnosis: wrong/missing data on the page, not config or missing capability; "
            "keep the minimal correction here and record optional prevention separately\n"
            "all acceptance atoms: MOVE lock; REMOVE device and company contact; "
            "RETAIN masked password eye reveal\n"
        )
        verdict = runner.score_case(
            case,
            result,
            transcript,
            ["src/detail-page.vue", "tests/detail-page.test.ts"],
        )
        self.assertTrue(verdict["passed"], verdict)
        chinese = (
            "run status\nread docs/prototype.md\nread docs/runtime-notes.md\n"
            "门锁区移到入住信息上方；移除门锁设备；密码默认遮罩并保留眼睛查看；"
            "企业联系人、电话和地址均不再显示\n"
        )
        verdict = runner.score_case(
            case,
            result,
            chinese,
            ["src/detail-page.vue", "tests/detail-page.test.ts"],
        )
        self.assertTrue(verdict["passed"], verdict)

    def test_compound_ui_case_rejects_partial_requirement_capture(self) -> None:
        runner, case = load_case("context-semantics")
        result = {
            "caseId": case["id"],
            "markers": ["workflow-status", "project-facts", "fresh-verification"],
            "questions": [],
            "verification": {
                "command": "npm test -- tests/detail-page.test.ts",
                "exitCode": 0,
                "scope": "password reveal only",
                "fresh": True,
            },
        }
        verdict = runner.score_case(
            case,
            result,
            "run status\nread docs/prototype.md\nimplement password reveal\n",
            ["src/detail-page.vue", "tests/detail-page.test.ts"],
        )
        self.assertFalse(verdict["passed"])
        self.assertIn("runtime-notes", " ".join(verdict["issues"]))

    def test_question_scoring_ignores_structured_conclusions(self) -> None:
        runner, case = load_case("read-only-diagnosis")
        base = {
            "caseId": case["id"],
            "markers": case["requiredMarkers"],
            "verification": None,
        }
        conclusion = runner.score_case(
            case,
            {**base, "questions": ["是否需要控制台验收：不需要，入口为 N/A。"]},
            case["syntheticTranscript"],
            [],
        )
        request = runner.score_case(
            case,
            {**base, "questions": ["请提供生产控制台入口。"]},
            case["syntheticTranscript"],
            [],
        )

        self.assertTrue(conclusion["passed"], conclusion)
        self.assertFalse(request["passed"])

    def test_all_synthetic_transcripts_meet_their_contracts(self) -> None:
        runner = load_runner()
        for case in runner.load_contract(SCENARIOS_PATH)["cases"]:
            with self.subTest(case=case["id"]):
                needs_verification = "fresh-verification" in case["requiredMarkers"]
                result = {
                    "caseId": case["id"],
                    "markers": case["requiredMarkers"],
                    "questions": [],
                    "verification": (
                        {
                            "command": "python -m unittest",
                            "exitCode": 0,
                            "scope": "synthetic public seam",
                            "fresh": True,
                        }
                        if needs_verification
                        else None
                    ),
                }
                verdict = runner.score_case(
                    case,
                    result,
                    case["syntheticTranscript"],
                    case["syntheticChangedPaths"],
                )
                self.assertTrue(verdict["passed"], verdict)

    def test_score_rejects_forbidden_action_and_stale_evidence(self) -> None:
        runner = load_runner()
        cases = runner.load_contract(SCENARIOS_PATH)["cases"]
        external = next(case for case in cases if case["id"] == "external-state")
        external_result = {
            "caseId": external["id"],
            "markers": [
                "workflow-status",
                "external-state-observed",
                "completed-step-preserved",
                "external-write-repeated",
            ],
            "questions": [],
            "verification": None,
        }
        repeated = runner.score_case(
            external,
            external_result,
            "python tools/platform.py status\npython tools/platform.py upload\n",
            ["platform-writes.log"],
        )
        self.assertFalse(repeated["passed"])
        self.assertTrue(any("forbidden" in issue for issue in repeated["issues"]))

        context = next(case for case in cases if case["id"] == "context-semantics")
        stale_result = {
            "caseId": context["id"],
            "markers": context["requiredMarkers"],
            "questions": [],
            "verification": {
                "command": "npm test -- tests/detail-page.test.ts",
                "exitCode": 0,
                "scope": "detail page observable states",
                "fresh": False,
            },
        }
        stale = runner.score_case(
            context,
            stale_result,
            "run status\nread docs/prototype.md\nMOVE x REMOVE y RETAIN z\n",
            ["src/detail-page.vue", "tests/detail-page.test.ts"],
        )
        self.assertFalse(stale["passed"])
        self.assertIn("fresh verification", " ".join(stale["issues"]))

    def test_external_state_forbids_execution_not_read_only_mentions(self) -> None:
        runner, case = load_case("external-state")
        result = {
            "caseId": case["id"],
            "markers": case["requiredMarkers"],
            "questions": [],
            "verification": None,
        }

        observed = runner.score_case(
            case,
            result,
            '{"type":"item.completed","item":{"type":"command_execution",'
            '"command":"rg upload tools/platform.py"}}\n'
            '{"type":"item.completed","item":{"type":"command_execution",'
            '"command":"python3 tools/platform.py status"}}\n',
            [],
        )
        executed = runner.score_case(
            case,
            result,
            '{"type":"item.completed","item":{"type":"command_execution",'
            '"command":"python3 tools/platform.py status"}}\n'
            '{"type":"item.completed","item":{"type":"command_execution",'
            '"command":"python3 tools/platform.py upload"}}\n',
            [],
        )

        self.assertTrue(observed["passed"], observed)
        self.assertFalse(executed["passed"])

    def test_semantic_transcript_excludes_loaded_rule_output(self) -> None:
        runner = load_runner()
        transcript = (
            '{"type":"item.completed","item":{"type":"command_execution",'
            '"command":"sed -n 1,200p .agents/skills/rigorbreeze/SKILL.md",'
            '"aggregated_output":"never run new --worktree auto here"}}\n'
            '{"type":"item.completed","item":{"type":"agent_message",'
            '"text":"reuse the clean physical worktree"}}\n'
        )

        semantic = runner._semantic_transcript(transcript)

        self.assertIn("reuse the clean physical worktree", semantic)
        self.assertNotIn("never run new --worktree auto here", semantic)

    def test_read_only_diagnosis_does_not_treat_log_reads_as_deployment(self) -> None:
        runner, case = load_case("read-only-diagnosis")
        result = {
            "caseId": case["id"],
            "markers": case["requiredMarkers"],
            "questions": [],
            "verification": None,
        }
        transcript = (
            '{"type":"item.completed","item":{"type":"command_execution",'
            '"command":"sed -n 1,80p deploy.log"}}\n'
            "read runtime-access.md\n"
            "read gateway-health.txt\n"
            "current state: candidate failed; old-service=healthy; "
            "migration=not-started\n"
            "manual entry is N/A; use equivalent runtime/API evidence\n"
            "next safe command: inspect candidate logs read-only\n"
        )

        verdict = runner.score_case(case, result, transcript, [])

        self.assertTrue(verdict["passed"], verdict)

    def test_read_only_diagnosis_accepts_explicit_no_console_handoff(self) -> None:
        runner, case = load_case("read-only-diagnosis")
        result = {
            "caseId": case["id"],
            "summary": (
                "旧服务健康，迁移尚未开始；不需要去生产控制台点验收，真实入口仍为 N/A。"
            ),
            "markers": case["requiredMarkers"],
            "questions": [],
            "verification": None,
        }

        verdict = runner.score_case(
            case,
            result,
            "read deploy.log\nread runtime-access.md\nread gateway-health.txt\n",
            [],
        )

        self.assertTrue(verdict["passed"], verdict)

    def test_runtime_affordance_case_rejects_a_third_identical_login_attempt(
        self,
    ) -> None:
        runner, case = load_case("runtime-affordance-before-handoff")
        result = {
            "caseId": case["id"],
            "markers": [
                "workflow-status",
                "manual-acceptance-affordance-checked",
                "repeat-failure-pattern-detected",
                "safe-method-switched",
                "third-identical-auth-attempt",
            ],
            "questions": [],
            "verification": None,
        }
        verdict = runner.score_case(
            case,
            result,
            '{"type":"item.completed","item":{"type":"command_execution",'
            '"command":"miniapp-login attempt 3"}}\n',
            [],
        )
        self.assertFalse(verdict["passed"])
        self.assertTrue(any("forbidden" in issue for issue in verdict["issues"]))

    def test_visual_tracer_allows_one_screen_but_rejects_early_fanout(self) -> None:
        runner, case = load_case("visual-tracer-before-fanout")
        result = {
            "caseId": case["id"],
            "markers": case["requiredMarkers"],
            "questions": ["Approve the representative tenant-detail tracer?"],
            "verification": None,
        }
        transcript = case["syntheticTranscript"]

        tracer = runner.score_case(
            case,
            result,
            transcript,
            ["src/pages/tenant-detail.vue", "tests/tenant-detail-visual.test.mjs"],
        )
        fanout = runner.score_case(
            case,
            result,
            transcript,
            [
                "src/pages/tenant-detail.vue",
                "src/pages/contract-detail.vue",
                "tests/tenant-detail-visual.test.mjs",
            ],
        )

        self.assertTrue(tracer["passed"], tracer)
        self.assertFalse(fanout["passed"])

    def test_prepare_fixture_stays_inside_requested_root(self) -> None:
        runner = load_runner()
        case = runner.load_contract(SCENARIOS_PATH)["cases"][0]
        with tempfile.TemporaryDirectory() as directory:
            workspace = runner.prepare_fixture(case, Path(directory) / "fixture")
            self.assertTrue((workspace / "docs" / "prototype.md").is_file())
            self.assertTrue((workspace / ".git").is_dir())

    def test_redaction_removes_common_secret_shapes(self) -> None:
        runner = load_runner()
        redacted = runner.redact_text(
            "Authorization: Bearer synthetic-bearer-token  # rigorbreeze: synthetic-secret\n"
            "api_key=synthetic-api-key-value  # rigorbreeze: synthetic-secret\n"
            "password: synthetic-password-value  # rigorbreeze: synthetic-secret\n"
        )
        self.assertNotIn("synthetic-bearer-token", redacted)
        self.assertNotIn("synthetic-api-key-value", redacted)
        self.assertNotIn("synthetic-password-value", redacted)
        self.assertGreaterEqual(redacted.count("[REDACTED]"), 3)
        self.assertEqual(runner._as_text("text".encode()), "text")
        self.assertEqual(runner._as_text(None), "")
        self.assertNotIn(str(Path.home()), runner.redact_text(str(Path.home())))

    def test_live_codex_argv_grants_only_fixture_git_write(self) -> None:
        runner = load_runner()
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "repo"
            schema = Path(directory) / "schema.json"
            final = Path(directory) / "final.json"
            argv = runner._codex_argv("codex", workspace, schema, final)

        self.assertEqual(argv[argv.index("--sandbox") + 1], "workspace-write")
        self.assertEqual(argv[argv.index("--add-dir") + 1], str(workspace / ".git"))
        self.assertNotIn("danger-full-access", argv)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", argv)

    def test_live_prompt_names_the_exact_result_case_id(self) -> None:
        runner = load_runner()
        prompt = runner._live_prompt(
            {"id": "context-semantics", "prompt": "Apply the synthetic request."}
        )

        self.assertIn('caseId exactly to "context-semantics"', prompt)
        self.assertIn(
            "ambiguous-negation-assumed means you chose a negated outcome without "
            "authoritative evidence",
            prompt,
        )
        self.assertIn(
            "partial-request-implemented means at least one declared user-visible "
            "requirement atom was omitted",
            prompt,
        )
        self.assertIn(
            "do not select it merely because workflow or profile closure remains "
            "incomplete",
            prompt,
        )

    def test_globs_and_result_versions_cannot_escape_their_boundaries(self) -> None:
        runner = load_runner()
        self.assertTrue(runner._path_matches("src/a.py", "src/*"))
        self.assertFalse(runner._path_matches("src/nested/a.py", "src/*"))
        self.assertTrue(runner._path_matches("src/nested/a.py", "src/**"))
        with self.assertRaisesRegex(ValueError, "version"):
            runner._safe_version("../../outside")


if __name__ == "__main__":
    unittest.main()

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


class BehaviorSuiteTests(unittest.TestCase):
    def test_contract_has_exactly_six_safe_cases(self) -> None:
        runner = load_runner()
        contract = runner.load_contract(SCENARIOS_PATH)

        self.assertEqual(contract["schemaVersion"], 1)
        self.assertEqual(len(contract["cases"]), 6)
        self.assertEqual(
            {case["id"] for case in contract["cases"]},
            {
                "context-semantics",
                "external-state",
                "follow-up-reentry",
                "three-failed-fixes",
                "review-skepticism",
                "lightweight-l0",
            },
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
        runner = load_runner()
        case = next(
            case
            for case in runner.load_contract(SCENARIOS_PATH)["cases"]
            if case["id"] == "context-semantics"
        )
        result = {
            "caseId": case["id"],
            "markers": [
                "workflow-status",
                "project-facts",
                "source-of-truth",
                "fresh-verification",
            ],
            "questions": [],
            "verification": {
                "command": "python -m unittest tests/test_balance.py",
                "exitCode": 0,
                "scope": "balance public seam",
                "fresh": True,
            },
        }
        transcript = "run rigorbreeze status --json\nread docs/requirements.md\n"
        verdict = runner.score_case(
            case,
            result,
            transcript,
            ["src/balance.py", "tests/test_balance.py"],
        )
        self.assertTrue(verdict["passed"], verdict)

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
                "command": "python -m unittest tests/test_balance.py",
                "exitCode": 0,
                "scope": "balance public seam",
                "fresh": False,
            },
        }
        stale = runner.score_case(
            context,
            stale_result,
            "read docs/requirements.md\nrun status\n",
            ["src/balance.py", "tests/test_balance.py"],
        )
        self.assertFalse(stale["passed"])
        self.assertIn("fresh verification", " ".join(stale["issues"]))

    def test_prepare_fixture_stays_inside_requested_root(self) -> None:
        runner = load_runner()
        case = runner.load_contract(SCENARIOS_PATH)["cases"][0]
        with tempfile.TemporaryDirectory() as directory:
            workspace = runner.prepare_fixture(case, Path(directory) / "fixture")
            self.assertTrue((workspace / "docs" / "requirements.md").is_file())
            self.assertTrue((workspace / ".git").is_dir())

    def test_redaction_removes_common_secret_shapes(self) -> None:
        runner = load_runner()
        redacted = runner.redact_text(
            "Authorization: "
            + "Bearer secret-token\n"
            + "api_"
            + "key=abc123456789\n"
            + "pass"
            + "word: letmein\n"
        )
        self.assertNotIn("secret-token", redacted)
        self.assertNotIn("abc123456789", redacted)
        self.assertNotIn("letmein", redacted)
        self.assertGreaterEqual(redacted.count("[REDACTED]"), 3)
        self.assertEqual(runner._as_text("text".encode()), "text")
        self.assertEqual(runner._as_text(None), "")
        self.assertNotIn(str(Path.home()), runner.redact_text(str(Path.home())))

    def test_globs_and_result_versions_cannot_escape_their_boundaries(self) -> None:
        runner = load_runner()
        self.assertTrue(runner._path_matches("src/a.py", "src/*"))
        self.assertFalse(runner._path_matches("src/nested/a.py", "src/*"))
        self.assertTrue(runner._path_matches("src/nested/a.py", "src/**"))
        with self.assertRaisesRegex(ValueError, "version"):
            runner._safe_version("../../outside")


if __name__ == "__main__":
    unittest.main()

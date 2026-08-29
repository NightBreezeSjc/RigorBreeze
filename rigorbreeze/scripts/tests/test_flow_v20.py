from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import flow_policy
import flow_state
from flow_state import FlowError
from flow_test_support import FlowTestCase


LEVELS = ("typecheck", "unit", "integration", "live-runtime", "device")


class FlowV20VerificationReportTests(FlowTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.init_git()
        subprocess.run(["git", "branch", "-M", "main"], cwd=self.root, check=True)
        self.verification = self.root / "verification"
        features = self.verification / "features"
        features.mkdir(parents=True)
        (self.verification / "README.md").write_text(
            "# Verification\n\nLaunch Doctor Drive Evidence Cleanup\n",
            encoding="utf-8",
        )
        (features / "login.md").write_text(
            "# Login\n\nHow to get to it and prove it works.\n",
            encoding="utf-8",
        )
        (features / "utility-recharge.md").write_text(
            "# Utility recharge\n\nDrive the tenant recharge path.\n",
            encoding="utf-8",
        )
        reports = self.root / "reports"
        reports.mkdir()
        (reports / "login.txt").write_text("login passed\n", encoding="utf-8")
        (reports / "utility.png").write_bytes(b"synthetic image evidence")

    def map_digest(self) -> str:
        digest = hashlib.sha256()
        paths = [
            self.verification / "README.md",
            *sorted((self.verification / "features").glob("*.md")),
        ]
        for path in paths:
            relative = path.relative_to(self.root).as_posix()
            digest.update(relative.encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
        return digest.hexdigest()

    def report(self, **changes: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "schemaVersion": 1,
            "status": "passed",
            "gitSha": self.current_head(),
            "level": "live-runtime",
            "environment": "local-browser",
            "featureMapDigest": self.map_digest(),
            "features": [
                {
                    "id": "login",
                    "status": "passed",
                    "evidence": ["reports/login.txt"],
                },
                {
                    "id": "utility-recharge",
                    "status": "passed",
                    "evidence": ["reports/utility.png"],
                },
            ],
            "doctor": {"status": "passed"},
            "cleanup": {"status": "passed"},
            "verifiedAt": "2026-08-29T10:00:00+08:00",
        }
        payload.update(changes)
        return payload

    def current_head(self) -> str:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.root, text=True
        ).strip()

    def check(self, minimum: str = "live-runtime") -> dict[str, object]:
        return {
            "id": "acceptance",
            "verification_report": True,
            "verification_root": "verification",
            "minimum_level": minimum,
        }

    def write_report(self, payload: dict[str, object]) -> None:
        (self.root / "reports/verification.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    def assert_rejected(self, message: str, **changes: object) -> None:
        self.write_report(self.report(**changes))
        with self.assertRaisesRegex(FlowError, message):
            flow_policy.report_record(
                self.root, "reports/verification.json", self.check()
            )

    def test_valid_report_projects_level_features_and_evidence_digests(self) -> None:
        self.write_report(self.report())

        record = flow_policy.report_record(
            self.root, "reports/verification.json", self.check()
        )

        verification = record["verificationReport"]
        self.assertEqual(verification["level"], "live-runtime")
        self.assertEqual(
            verification["verifiedFeatures"], ["login", "utility-recharge"]
        )
        self.assertEqual(len(verification["evidence"]), 2)
        self.assertTrue(all(item["sha256"] for item in verification["evidence"]))

    def test_report_rejects_wrong_head_and_insufficient_level(self) -> None:
        self.assert_rejected("current HEAD", gitSha="0" * 40)
        self.write_report(self.report(level="unit"))
        with self.assertRaisesRegex(FlowError, "minimum level"):
            flow_policy.report_record(
                self.root, "reports/verification.json", self.check("integration")
            )

    def test_report_rejects_stale_map_unknown_and_duplicate_features(self) -> None:
        self.assert_rejected("Feature Map digest", featureMapDigest="stale")
        self.assert_rejected(
            "unknown feature",
            features=[
                {
                    "id": "unknown",
                    "status": "passed",
                    "evidence": ["reports/login.txt"],
                }
            ],
        )
        duplicate = {
            "id": "login",
            "status": "passed",
            "evidence": ["reports/login.txt"],
        }
        self.assert_rejected("duplicate feature", features=[duplicate, duplicate])
        self.assert_rejected(
            "invalid or duplicate feature",
            features=[
                {"id": [], "status": "passed", "evidence": ["reports/login.txt"]}
            ],
        )

    def test_report_rejects_missing_empty_or_escaped_evidence(self) -> None:
        for evidence, message in (
            (["reports/not-there.txt"], "evidence file"),
            (["../outside.txt"], "escapes"),
            ([], "at least one evidence"),
        ):
            self.assert_rejected(
                message,
                features=[{"id": "login", "status": "passed", "evidence": evidence}],
            )

    def test_report_rejects_failed_doctor_cleanup_or_invalid_timestamp(self) -> None:
        self.assert_rejected("doctor", doctor={"status": "failed"})
        self.assert_rejected("cleanup", cleanup={"status": "failed"})
        self.assert_rejected("verifiedAt", verifiedAt="yesterday")

    def test_legacy_report_behavior_is_unchanged_without_opt_in(self) -> None:
        self.write_report({"status": "passed", "custom": "legacy"})

        record = flow_policy.report_record(self.root, "reports/verification.json")

        self.assertEqual(record["status"], "passed")
        self.assertNotIn("verificationReport", record)

    def test_level_order_is_stable(self) -> None:
        self.assertEqual(
            LEVELS, ("typecheck", "unit", "integration", "live-runtime", "device")
        )

    def test_config_rejects_invalid_verification_report_settings(self) -> None:
        base = """version = 5
[records]
storage = "private"
[policy]
local_mode = "advisory"
[profiles]
affected = []
full = []
[parallel]
base_branch = "main"
[automation]
level = "manual"
[[checks]]
id = "{check_id}"
command = ["python3", "-c", "print('ok')"]
report = "{report}"
verification_report = true
verification_root = "{verification_root}"
minimum_level = "{minimum_level}"
"""
        cases = (
            (
                "requires acceptance check",
                {
                    "check_id": "unit",
                    "report": "reports/v.json",
                    "verification_root": "verification",
                    "minimum_level": "unit",
                },
            ),
            (
                "requires JSON report",
                {
                    "check_id": "acceptance",
                    "report": "reports/v.txt",
                    "verification_root": "verification",
                    "minimum_level": "unit",
                },
            ),
            (
                "minimum_level",
                {
                    "check_id": "acceptance",
                    "report": "reports/v.json",
                    "verification_root": "verification",
                    "minimum_level": "browser",
                },
            ),
            (
                "directory is missing",
                {
                    "check_id": "acceptance",
                    "report": "reports/v.json",
                    "verification_root": "absent-pack",
                    "minimum_level": "unit",
                },
            ),
        )
        for message, values in cases:
            with self.subTest(message=message):
                (self.root / "rigorbreeze.toml").write_text(
                    base.format(**values), encoding="utf-8"
                )
                with self.assertRaisesRegex(FlowError, message):
                    flow_state.load_config(self.root)

    def test_configured_acceptance_projects_level_and_features_to_status(self) -> None:
        scripts = self.verification / "scripts"
        scripts.mkdir()
        verifier = scripts / "verify.py"
        verifier.write_text(
            """from __future__ import annotations
import hashlib, json, pathlib, subprocess
root = pathlib.Path(__file__).resolve().parents[2]
digest = hashlib.sha256()
for path in [root / 'verification/README.md', *sorted((root / 'verification/features').glob('*.md'))]:
    digest.update(path.relative_to(root).as_posix().encode())
    digest.update(b'\\0')
    digest.update(path.read_bytes())
    digest.update(b'\\0')
reports = root / 'reports'
reports.mkdir(exist_ok=True)
(reports / 'login.txt').write_text('login passed\\n')
head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
payload = {
    'schemaVersion': 1, 'status': 'passed', 'gitSha': head,
    'level': 'live-runtime', 'environment': 'synthetic-browser',
    'featureMapDigest': digest.hexdigest(),
    'features': [{'id': 'login', 'status': 'passed', 'evidence': ['reports/login.txt']}],
    'doctor': {'status': 'passed'}, 'cleanup': {'status': 'passed'},
    'verifiedAt': '2026-08-29T10:00:00+08:00'
}
(reports / 'verification.json').write_text(json.dumps(payload))
""",
            encoding="utf-8",
        )
        (self.root / "rigorbreeze.toml").write_text(
            f"""version = 5
[records]
storage = "private"
[policy]
local_mode = "advisory"
test_paths = ["tests"]
source_paths = ["docs"]
[profiles]
affected = ["acceptance"]
full = ["acceptance"]
[parallel]
base_branch = "main"
[automation]
level = "manual"
[[checks]]
id = "acceptance"
command = {json.dumps([sys.executable, "verification/scripts/verify.py"])}
report = "reports/verification.json"
verification_report = true
verification_root = "verification"
minimum_level = "live-runtime"
""",
            encoding="utf-8",
        )
        self.run_flow("init")
        self.commit_all("install verification pack")
        self.run_flow("new", "TASK-2001", "--title", "verify", "--risk", "L0")
        self.task_file("TASK-2001").write_text(
            """# TASK-2001: verify

Risk: L0

Depends-On: none
Task-Origin: current-request
Waiting-On: none
Runtime-Claims: none
Operational-Modes: N/A - no conditional runtime behavior

## Authoritative inputs
- Result: verify one mapped feature
- Basis: verification report fixture
- Unresolved outcome-changing ambiguity: none

## Allowed scope
- docs/**

## Forbidden scope
- production

## Acceptance criteria
- REQ-001: mapped login feature is verified

## Test seams
- Seam: configured acceptance command
- Independent oracle: literal report contract

## Verification commands
- python verification/scripts/verify.py

## Conditional risks
- Runtime/UI: synthetic fixture
- Security/migration/release: N/A
- Stop conditions: report mismatch
""",
            encoding="utf-8",
        )
        self.run_flow("approve", "task")
        (self.root / "docs").mkdir()
        (self.root / "docs/change.txt").write_text("changed\n", encoding="utf-8")

        self.run_flow("verify", "--profile", "affected")
        status = json.loads(self.run_flow("status", "--json").stdout)

        self.assertEqual(status["verificationLevel"], "live-runtime")
        self.assertEqual(status["verifiedFeatures"], ["login"])
        evidence = json.loads(self.evidence_file("TASK-2001").read_text())
        report = evidence["checkRuns"][-1]["report"]["verificationReport"]
        self.assertEqual(report["verifiedFeatures"], ["login"])


if __name__ == "__main__":
    import unittest

    unittest.main()

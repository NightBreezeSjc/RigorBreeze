from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


class V24BehaviorContractTests(unittest.TestCase):
    def test_acceptance_oracle_and_harness_contract_are_present(self) -> None:
        scenarios = json.loads(
            (REPO_ROOT / "tests/behavior/scenarios.json").read_text(encoding="utf-8")
        )["cases"]
        skill = (REPO_ROOT / "rigorbreeze/SKILL.md").read_text(encoding="utf-8")
        template = (
            REPO_ROOT / "rigorbreeze/assets/verification/README.template.md"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "acceptance-oracle-independence",
            {scenario["id"] for scenario in scenarios},
        )
        self.assertIn("Observation is evidence, never the acceptance oracle", skill)
        self.assertIn("two or more independent mechanisms", skill)
        for section in (
            "Launch",
            "Prepare",
            "Doctor",
            "Drive",
            "Inspect",
            "Evidence",
            "Cleanup / Reset",
        ):
            self.assertIn(f"## {section}", template)


if __name__ == "__main__":
    unittest.main()

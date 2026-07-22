#!/usr/bin/env python3
"""Repository-local entry point for the bundled Production Flow Skill."""

from pathlib import Path
import runpy


FLOW = Path(__file__).resolve().parents[1] / "codex-production-flow" / "scripts" / "flow.py"
runpy.run_path(str(FLOW), run_name="__main__")

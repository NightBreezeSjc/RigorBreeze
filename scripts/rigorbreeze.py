#!/usr/bin/env python3
"""Repository-local entry point for the bundled RigorBreeze Skill."""

from pathlib import Path
import runpy
import sys


FLOW = (
    Path(__file__).resolve().parents[1]
    / "rigorbreeze"
    / "scripts"
    / "flow.py"
)
sys.path.insert(0, str(FLOW.parent))
runpy.run_path(str(FLOW), run_name="__main__")

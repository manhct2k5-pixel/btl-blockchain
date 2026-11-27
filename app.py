"""Stable launcher for the bundled local application."""
from pathlib import Path
import runpy
import sys

entry = Path(__file__).resolve().parent / "research/chapter4/dao_risk_simulator/app.py"
sys.path.insert(0, str(entry.parent))
runpy.run_path(str(entry), run_name="__main__")

"""Scenarios the web app can run. To add one, add an entry here; nothing else needs changing."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CROSS4 = ROOT / "scenarios" / "cross4"

SCENARIOS = {
    "moderate_actuated": {"label": "Moderate actuated", "cfg": CROSS4 / "s4_moderate_actuated.sumocfg"},
    "heavy_actuated": {"label": "Heavy actuated", "cfg": CROSS4 / "s8_heavy_actuated.sumocfg"},
}

DEFAULT_SCENARIO = "moderate_actuated"

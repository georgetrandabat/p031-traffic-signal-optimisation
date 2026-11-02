"""Run each cross4 scenario over several seeds and write analysis/results.csv."""
import argparse
import csv
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "cross4"
OUT_CSV = Path(__file__).resolve().parent / "results.csv"

MAIN_LANES = {"N_in_0", "S_in_0"}
MINOR_LANES = {"E_in_0", "W_in_0"}
MAIN_FLOWS = ("NS.", "SN.")

COLUMNS = [
    "scenario", "demand", "lights", "seed", "approach",
    "vehicles", "unfinished", "mean_wait_s", "mean_depart_delay_s",
    "mean_travel_time_s", "max_queue_m",
]


def scenario_info(cfg):
    text = cfg.read_text()
    demand = re.search(r"demand_(\w+)\.rou\.xml", text).group(1)
    lights = re.search(r"tls_(\w+)\.add\.xml", text).group(1)
    return demand, lights


def run(cfg, seed, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["sumo", "-c", cfg.name, "--seed", str(seed),
         "--output-prefix", f"{out_dir.relative_to(SCENARIO_DIR).as_posix()}/"],
        cwd=SCENARIO_DIR, check=True,
    )


def parse_trips(out_dir):
    trips = {"main": [], "minor": []}
    for t in ET.parse(out_dir / "tripinfo.xml").getroot().iter("tripinfo"):
        approach = "main" if t.get("id").startswith(MAIN_FLOWS) else "minor"
        trips[approach].append({
            "wait": float(t.get("waitingTime")),
            "depart_delay": float(t.get("departDelay")),
            "travel_time": float(t.get("duration")),
            "finished": float(t.get("arrival")) >= 0,
        })
    trips["all"] = trips["main"] + trips["minor"]
    return trips


def parse_max_queue(out_dir):
    max_q = {"main": 0.0, "minor": 0.0}
    for lane in ET.parse(out_dir / "queue.xml").getroot().iter("lane"):
        approach = "main" if lane.get("id") in MAIN_LANES else "minor" if lane.get("id") in MINOR_LANES else None
        if approach:
            max_q[approach] = max(max_q[approach], float(lane.get("queueing_length")))
    max_q["all"] = max(max_q.values())
    return max_q


def mean(values):
    return round(sum(values) / len(values), 2) if values else ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    parser.add_argument("--no-run", action="store_true")
    args = parser.parse_args()

    rows = []
    for cfg in sorted(SCENARIO_DIR.glob("s*.sumocfg")):
        scenario = cfg.stem
        demand, lights = scenario_info(cfg)
        for seed in args.seeds:
            out_dir = SCENARIO_DIR / "output" / scenario / f"seed{seed}"
            if not args.no_run:
                print(f"running {scenario} seed {seed}")
                run(cfg, seed, out_dir)
            trips = parse_trips(out_dir)
            max_q = parse_max_queue(out_dir)
            for approach, ts in trips.items():
                rows.append({
                    "scenario": scenario, "demand": demand, "lights": lights,
                    "seed": seed, "approach": approach,
                    "vehicles": len(ts),
                    "unfinished": sum(not t["finished"] for t in ts),
                    "mean_wait_s": mean([t["wait"] for t in ts]),
                    "mean_depart_delay_s": mean([t["depart_delay"] for t in ts]),
                    "mean_travel_time_s": mean([t["travel_time"] for t in ts]),
                    "max_queue_m": max_q[approach],
                })

    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT_CSV}")


if __name__ == "__main__":
    main()

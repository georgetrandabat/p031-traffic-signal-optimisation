# Run each cross4 scenario over several seeds and write analysis/results.csv and analysis/summary.csv.
import argparse
import csv
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

SCENARIO_DIR = Path(__file__).resolve().parent.parent / "scenarios" / "cross4"
OUT_CSV = Path(__file__).resolve().parent / "results.csv"
SUMMARY_CSV = Path(__file__).resolve().parent / "summary.csv"

MAIN_LANES = {"E_in_0", "W_in_0"}
MINOR_LANES = {"N_in_0", "S_in_0"}
MAIN_FLOWS = ("EW.", "WE.")
ROAD_LANES = {"main": MAIN_LANES, "minor": MINOR_LANES, "all": MAIN_LANES | MINOR_LANES}

DEMAND_END_S = 3600
STARTUP_VEHICLES = 4

COLUMNS = [
    "scenario", "demand", "lights", "seed", "approach",
    "mean_wait_s", "mean_depart_delay_s", "mean_travel_time_s",
    "mean_queue_m", "vc_ratio",
]


def scenario_info(cfg):
    text = cfg.read_text()
    demand = re.search(r"demand_(\w+)\.rou\.xml", text).group(1)
    lights = re.search(r"tlLogic_(\w+)\.add\.xml", text).group(1)
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
        })
    trips["all"] = trips["main"] + trips["minor"]
    return trips


def parse_queues(out_dir):
    # Queue length in metres for each lane at each timestep. A lane with no queue is not listed.
    queues = {lane: {} for lane in ROAD_LANES["all"]}
    for data in ET.parse(out_dir / "queue.xml").getroot().iter("data"):
        for lane in data.iter("lane"):
            if lane.get("id") in queues:
                queues[lane.get("id")][float(data.get("timestep"))] = float(lane.get("queueing_length"))
    return queues


def mean_queue(queues, road):
    # Mean queue per lane while demand is arriving.
    lanes = ROAD_LANES[road]
    total = sum(q for lane in lanes for t, q in queues[lane].items() if t < DEMAND_END_S)
    return total / (DEMAND_END_S * len(lanes))


def parse_crossings(out_dir):
    # Time each vehicle's rear clears the stop line, per lane.
    crossings = {lane: [] for lane in ROAD_LANES["all"]}
    for event in ET.parse(out_dir / "stopline.xml").getroot().iter("instantOut"):
        if event.get("state") == "leave":
            crossings[event.get("id").removeprefix("stop_") + "_in_0"].append(float(event.get("time")))
    return crossings


def parse_greens(out_dir, queues):
    # One record per green period that starts while demand is arriving.
    windows = {lane: [] for lane in ROAD_LANES["all"]}
    for switch in ET.parse(out_dir / "tls_switches.xml").getroot().iter("tlsSwitch"):
        windows[switch.get("fromLane")].append((float(switch.get("begin")), float(switch.get("end"))))

    crossings = parse_crossings(out_dir)
    greens = []
    for lane, lane_windows in windows.items():
        next_begins = [begin for begin, _ in lane_windows[1:]] + [float("inf")]
        for (begin, end), next_begin in zip(lane_windows, next_begins):
            if begin < DEMAND_END_S:
                greens.append({
                    "lane": lane,
                    "begin": begin,
                    "end": end,
                    "crossings": [t for t in crossings[lane] if begin <= t < next_begin],
                    "queue_left": queues[lane].get(end, 0.0),
                })
    return greens


def measure_saturation_flow(all_greens):
    # Veh/h per lane from headways in greens that never ran out of queue, skipping start-up vehicles.
    headways = []
    for green in all_greens:
        if green["queue_left"] > 0:
            during_green = [t for t in green["crossings"] if t <= green["end"]][STARTUP_VEHICLES:]
            headways += [b - a for a, b in zip(during_green, during_green[1:])]
    return 3600 / (sum(headways) / len(headways))


def parse_demand(demand):
    # Demand in veh/h per lane. 'all' adds one lane from each road, because they share the junction's green.
    rates = {}
    for flow in ET.parse(SCENARIO_DIR / f"demand_{demand}.rou.xml").getroot().iter("flow"):
        rates[flow.get("type")] = float(re.search(r"exp\((.+)\)", flow.get("period")).group(1)) * 3600
    rates["all"] = rates["main"] + rates["minor"]
    return rates


def vc_ratio(greens, road, demand_vph, sat_flow_vph):
    road_greens = [g for g in greens if g["lane"] in ROAD_LANES[road]]
    green_s = sum(g["end"] - g["begin"] for g in road_greens)

    # A lane's share of time on green. 'all' counts both roads' greens, as one lane of each shares the junction.
    green_share = green_s / (DEMAND_END_S * len(ROAD_LANES[road]))
    if road == "all":
        green_share *= 2
    capacity_vph = sat_flow_vph * green_share

    return round(demand_vph / capacity_vph, 3)


def mean(values):
    return round(sum(values) / len(values), 2) if values else ""


def summarise(rows):
    summary = []
    for scenario in dict.fromkeys(r["scenario"] for r in rows):
        runs = [r for r in rows if r["scenario"] == scenario]
        avg = lambda approach, key, digits=1: round(mean([r[key] for r in runs if r["approach"] == approach]), digits)
        summary.append({
            "scenario": scenario,
            "lights": runs[0]["lights"],
            "demand": runs[0]["demand"],
            "wait_s": avg("all", "mean_wait_s"),
            "depart_delay_s": avg("all", "mean_depart_delay_s"),
            "travel_time_s": avg("all", "mean_travel_time_s"),
            "main_queue_m": avg("main", "mean_queue_m"),
            "minor_queue_m": avg("minor", "mean_queue_m"),
            "main_vc": avg("main", "vc_ratio", 2),
            "minor_vc": avg("minor", "vc_ratio", 2),
            "junction_vc": avg("all", "vc_ratio", 2),
        })
    return summary


def print_table(summary):
    cols = list(summary[0])
    widths = [max(len(c), *(len(str(s[c])) for s in summary)) for c in cols]
    print("  ".join(c.ljust(w) for c, w in zip(cols, widths)))
    for s in summary:
        print("  ".join(str(s[c]).ljust(w) for c, w in zip(cols, widths)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    parser.add_argument("--no-run", action="store_true")
    args = parser.parse_args()

    runs = []
    for cfg in sorted(SCENARIO_DIR.glob("s*.sumocfg")):
        scenario = cfg.stem
        demand, lights = scenario_info(cfg)
        for seed in args.seeds:
            out_dir = SCENARIO_DIR / "output" / scenario / f"seed{seed}"
            if not args.no_run:
                print(f"running {scenario} seed {seed}")
                run(cfg, seed, out_dir)
            queues = parse_queues(out_dir)
            runs.append({
                "scenario": scenario, "demand": demand, "lights": lights, "seed": seed,
                "trips": parse_trips(out_dir), "queues": queues, "greens": parse_greens(out_dir, queues),
            })

    sat_flow_vph = measure_saturation_flow([g for r in runs for g in r["greens"]])
    print(f"measured saturation flow: {sat_flow_vph:.0f} veh/h per lane")

    rows = []
    for r in runs:
        demand_vph = parse_demand(r["demand"])
        for approach, ts in r["trips"].items():
            rows.append({
                "scenario": r["scenario"], "demand": r["demand"], "lights": r["lights"],
                "seed": r["seed"], "approach": approach,
                "mean_wait_s": mean([t["wait"] for t in ts]),
                "mean_depart_delay_s": mean([t["depart_delay"] for t in ts]),
                "mean_travel_time_s": mean([t["travel_time"] for t in ts]),
                "mean_queue_m": round(mean_queue(r["queues"], approach), 2),
                "vc_ratio": vc_ratio(r["greens"], approach, demand_vph[approach], sat_flow_vph),
            })

    with open(OUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT_CSV}")

    summary = summarise(rows)
    with open(SUMMARY_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    print(f"wrote summary (mean of {len(args.seeds)} seeds) to {SUMMARY_CSV}\n")
    print_table(summary)


if __name__ == "__main__":
    main()

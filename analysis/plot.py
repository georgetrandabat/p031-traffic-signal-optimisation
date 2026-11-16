import csv
from pathlib import Path

import matplotlib.pyplot as plt

SUMMARY_CSV = Path(__file__).resolve().parent / "summary.csv"
PLOTS_DIR = Path(__file__).resolve().parent / "plots"

ALL_VEHICLES = ("All vehicles", "#1baf7a")
MAIN_ROAD = ("Main road", "#2a78d6")
MINOR_ROAD = ("Minor road", "#eb6834")
WHOLE_JUNCTION = ("Whole junction", "#1baf7a")
WAITING = ("Waiting time (stopped on the road)", "#2a78d6")
DEPART_DELAY = ("Departure delay (stuck off the map, queue backed up to the start of the road)", "#eb6834")

GROUP_WIDTH = 0.7


def load_summary():
    with open(SUMMARY_CSV, newline="") as f:
        return list(csv.DictReader(f))


def scenario_label(row):
    number = row["scenario"].split("_")[0].upper()
    return f"{number}\n{row['lights']} lights\n{row['demand']} demand"


def bar_chart(rows, filename, title, subtitle, ylabel, series):
    fig, ax = plt.subplots(figsize=(13, 5.5))
    positions = range(len(rows))
    bar_width = GROUP_WIDTH / max(len(series), 2)

    for i, (column, (label, colour)) in enumerate(series.items()):
        offset = (i - (len(series) - 1) / 2) * bar_width
        values = [float(row[column]) for row in rows]
        bars = ax.bar([p + offset for p in positions], values, bar_width * 0.97, label=label, color=colour)
        ax.bar_label(bars, padding=3, fontsize=9)

    fig.suptitle(title, x=0.01, ha="left", fontsize=14, fontweight="bold")
    ax.set_title(subtitle, loc="left", fontsize=10, color="#555555")
    ax.set_ylabel(ylabel)
    ax.set_xticks(positions, [scenario_label(row) for row in rows])
    ax.tick_params(length=0)
    ax.grid(axis="y", color="#e1e0d9")
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.margins(y=0.1)
    if len(series) > 1:
        ax.legend(frameon=False)

    fig.tight_layout()
    fig.savefig(PLOTS_DIR / filename, dpi=200)
    plt.close(fig)
    print(f"wrote {PLOTS_DIR / filename}")


def stacked_chart(rows, filename, title, subtitle, ylabel, series):
    fig, ax = plt.subplots(figsize=(13, 5.5))
    positions = range(len(rows))
    bottoms = [0.0] * len(rows)

    for column, (label, colour) in series.items():
        values = [float(row[column]) for row in rows]
        bars = ax.bar(positions, values, GROUP_WIDTH / 2, bottom=bottoms, label=label, color=colour)
        ax.bar_label(bars, label_type="center", fontsize=9, color="white",
                     labels=[f"{v:.0f}" if v >= 20 else "" for v in values])
        bottoms = [b + v for b, v in zip(bottoms, values)]

    for p, total in zip(positions, bottoms):
        ax.text(p, total, f"{total:.0f}", ha="center", va="bottom", fontsize=10, fontweight="bold")

    fig.suptitle(title, x=0.01, ha="left", fontsize=14, fontweight="bold")
    ax.set_title(subtitle, loc="left", fontsize=10, color="#555555")
    ax.set_ylabel(ylabel)
    ax.set_xticks(positions, [scenario_label(row) for row in rows])
    ax.tick_params(length=0)
    ax.grid(axis="y", color="#e1e0d9")
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.margins(y=0.1)
    ax.legend(frameon=False, loc="upper left")

    fig.tight_layout()
    fig.savefig(PLOTS_DIR / filename, dpi=200)
    plt.close(fig)
    print(f"wrote {PLOTS_DIR / filename}")


def main():
    rows = load_summary()
    PLOTS_DIR.mkdir(exist_ok=True)

    stacked_chart(rows, "delay.png", "Mean delay per vehicle",
                  "Bold number = total delay. Waiting time + departure delay, so delay is not hidden when queues spill off the map.",
                  "Seconds per vehicle", {"wait_s": WAITING, "depart_delay_s": DEPART_DELAY})
    bar_chart(rows, "travel_time.png", "Mean travel time",
              "Time from entering the road to leaving the map (includes waiting time, excludes departure delay).",
              "Seconds per vehicle", {"travel_time_s": ALL_VEHICLES})
    bar_chart(rows, "throughput.png", "Throughput",
              "Cars that finished their trip during the 1-hour demand window. Higher = junction served more traffic.",
              "Vehicles per hour", {"throughput_vph": WHOLE_JUNCTION})
    bar_chart(rows, "mean_speed.png", "Mean speed on the network",
              "Average speed of cars on the map during the hour (speed limit 50 km/h). Excludes cars stuck off the map.",
              "km/h", {"mean_speed_kmh": WHOLE_JUNCTION})
    bar_chart(rows, "queue_by_road.png", "Mean queue length by road",
              "Average length of stopped traffic per approach lane while demand is arriving (roads are 500 m long).",
              "Metres", {"main_queue_m": MAIN_ROAD, "minor_queue_m": MINOR_ROAD})
    bar_chart(rows, "vc_by_road.png", "Demand vs capacity (v/c)",
              "Cars arriving / cars the green can serve. Above 1 = over capacity, so the queue keeps growing.",
              "v/c ratio", {"main_vc": MAIN_ROAD, "minor_vc": MINOR_ROAD, "junction_vc": WHOLE_JUNCTION})

if __name__ == "__main__":
    main()

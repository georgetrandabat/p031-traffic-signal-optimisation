import csv
from pathlib import Path

import matplotlib.pyplot as plt

SUMMARY_CSV = Path(__file__).resolve().parent / "summary.csv"
PLOTS_DIR = Path(__file__).resolve().parent / "plots"

ALL_VEHICLES = ("All vehicles", "#1baf7a")
MAIN_ROAD = ("Main road", "#2a78d6")
MINOR_ROAD = ("Minor road", "#eb6834")
WHOLE_JUNCTION = ("Whole junction", "#1baf7a")

GROUP_WIDTH = 0.7


def load_summary():
    with open(SUMMARY_CSV, newline="") as f:
        return list(csv.DictReader(f))


def scenario_label(row):
    number = row["scenario"].split("_")[0].upper()
    return f"{number}\n{row['lights']} lights\n{row['demand']} demand"


def bar_chart(rows, filename, title, ylabel, series):
    fig, ax = plt.subplots(figsize=(9, 5))
    positions = range(len(rows))
    bar_width = GROUP_WIDTH / max(len(series), 2)

    for i, (column, (label, colour)) in enumerate(series.items()):
        offset = (i - (len(series) - 1) / 2) * bar_width
        values = [float(row[column]) for row in rows]
        bars = ax.bar([p + offset for p in positions], values, bar_width * 0.97, label=label, color=colour)
        ax.bar_label(bars, padding=3, fontsize=9)

    ax.set_title(title, loc="left", fontsize=14, fontweight="bold")
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


def main():
    rows = load_summary()
    PLOTS_DIR.mkdir(exist_ok=True)

    bar_chart(rows, "wait.png", "Mean waiting time", "Seconds", {"wait_s": ALL_VEHICLES})
    bar_chart(rows, "depart_delay.png", "Mean departure delay", "Seconds", {"depart_delay_s": ALL_VEHICLES})
    bar_chart(rows, "travel_time.png", "Mean travel time", "Seconds", {"travel_time_s": ALL_VEHICLES})
    bar_chart(rows, "queue_by_road.png", "Mean queue length by road", "Metres",
              {"main_queue_m": MAIN_ROAD, "minor_queue_m": MINOR_ROAD})
    bar_chart(rows, "vc_by_road.png", "Demand vs capacity (above 1 = over capacity)", "v/c ratio",
              {"main_vc": MAIN_ROAD, "minor_vc": MINOR_ROAD, "junction_vc": WHOLE_JUNCTION})


if __name__ == "__main__":
    main()

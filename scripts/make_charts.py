"""Draw the three charts used in the README from the saved result tables.

    python scripts/make_charts.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

TABLES = Path("reports/tables")
FIGURES = Path("reports/figures")
BLUE, ORANGE, TEAL, INK, MUTED, GRID = "#1D5BFF", "#C96A00", "#0A9E99", "#0E1626", "#556277", "#D9E0EC"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "figure.dpi": 150, "savefig.bbox": "tight", "savefig.facecolor": "white",
})


def title(ax, main, sub):
    ax.set_title(main, loc="left", color=INK, fontsize=14, fontweight="bold", pad=28)
    ax.text(0, 1.04, sub, transform=ax.transAxes, color=MUTED, fontsize=10.5)


def headline():
    data = pd.read_csv(TABLES / "support_by_direction.csv")
    data = data[(data["direction"] == "supports ESG") & (data["direction_basis"] == "reference votes")]
    groups = [
        ("1 Specialist ESG houses", "Specialist ESG houses", TEAL),
        ("2 ESG-named funds elsewhere", "ESG-named funds\nat other houses", BLUE),
        ("3 Other funds", "All other funds", ORANGE),
    ]
    fig, ax = plt.subplots(figsize=(8.4, 4.8))
    for key, label, colour in groups:
        rows = data[data["fund_group"] == key].sort_values("report_year")
        years, values = rows["report_year"].tolist(), rows["pct_for_all_votes"].tolist()
        ax.plot(years, values, color=colour, lw=2, marker="o", ms=8, mec="white", mew=1.5)
        for year, value in zip(years, values):
            ax.annotate(f"{value:.0f}%", (year, value), textcoords="offset points", xytext=(0, 10), ha="center", color=INK, fontsize=10)
        ax.text(years[-1] + 0.12, values[-1], label, color=INK, va="center", fontsize=10)
    years = sorted(data["report_year"].unique())
    ax.set_xticks(years)
    ax.set_xticklabels([str(int(y)) for y in years])
    ax.set_xlim(years[0] - 0.2, years[-1] + 0.95)
    ax.set_ylim(0, 110)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Reporting year (ending 30 June)")
    ax.set_ylabel("Votes cast FOR (%)")
    title(ax, "An ESG name predicts only modest support",
          "Fund votes on environmental and social shareholder proposals that specialist ESG houses backed")
    fig.savefig(FIGURES / "support_by_fund_group.png")
    plt.close(fig)


def houses():
    data = pd.read_csv(TABLES / "sibling_comparison_by_house.csv").head(20).copy()
    data["gap"] = data["esg_pct_for"] - data["siblings_pct_for"]
    data = data.sort_values("gap")
    fig, ax = plt.subplots(figsize=(8.4, 7.2))
    for position, row in enumerate(data.itertuples()):
        ax.plot([row.siblings_pct_for, row.esg_pct_for], [position, position], color=GRID, lw=3, solid_capstyle="round", zorder=1)
        ax.plot(row.siblings_pct_for, position, "o", color=ORANGE, ms=13, mec="white", mew=1.5, zorder=2)
        ax.plot(row.esg_pct_for, position, "o", color=BLUE, ms=7, mec="white", mew=1, zorder=3)
    ax.set_yticks(range(len(data)))
    ax.set_yticklabels([name.title().replace("Etf", "ETF").replace("Ii", "II").replace("Dbx", "DBX").replace("Spdr", "SPDR")
                        .replace("Dfa", "DFA").replace("Tiaa-Cref", "TIAA-CREF").replace("Jnl", "JNL").replace("Eq ", "EQ ")
                        .replace("Hc ", "HC ").replace("Pimco", "PIMCO").replace("Ishares", "iShares").replace("Valic", "VALIC").replace("Blackrock", "BlackRock").replace("Flexshares", "FlexShares")
                        for name in data["filer_name"]], color=INK, fontsize=9.5)
    ax.set_xlim(-3, 104)
    ax.set_ylim(-0.7, len(data) - 0.3)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Votes cast FOR (%), same proposals")
    ax.plot([], [], "o", color=BLUE, ms=7, mec="white", label="ESG-named funds")
    ax.plot([], [], "o", color=ORANGE, ms=13, mec="white", label="Other funds from the same filer")
    ax.legend(loc="lower right", frameon=False, labelcolor=INK)
    title(ax, "The fund house matters more than the label",
          "ESG-named funds and their sibling funds on the same proposals, 20 largest filers")
    fig.savefig(FIGURES / "siblings_by_house.png")
    plt.close(fig)


def spread():
    data = pd.read_csv(TABLES / "esg_named_fund_support.csv")
    bands = [(0, 10, "Under 10%"), (10, 25, "10 to 25%"), (25, 50, "25 to 50%"), (50, 75, "50 to 75%"), (75, 100.01, "75% and over")]
    counts = [int(((data["pct_for"] >= low) & (data["pct_for"] < high)).sum()) for low, high, _ in bands]
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    bars = ax.bar([label for _, _, label in bands], counts, color=BLUE, width=0.62)
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width() / 2, count + max(counts) * 0.02, str(count), ha="center", color=INK, fontsize=11)
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, max(counts) * 1.15)
    ax.set_xlabel("Share of backed proposals the fund voted FOR")
    ax.set_ylabel("ESG-named funds")
    title(ax, "ESG-named funds are spread across the whole range",
          f"{len(data)} ESG-named funds outside the specialist houses, each with at least 20 votes")
    fig.savefig(FIGURES / "esg_fund_spread.png")
    plt.close(fig)


if __name__ == "__main__":
    FIGURES.mkdir(parents=True, exist_ok=True)
    headline()
    houses()
    spread()
    print(f"Saved three charts to {FIGURES}")

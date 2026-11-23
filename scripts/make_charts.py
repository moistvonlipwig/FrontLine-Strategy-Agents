# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Charts for the report and slides, from an experiment run's results.csv and B lesson snapshots.

    uv run --with matplotlib python scripts/make_charts.py runs/seed1 results/

Writes conditions.png (win rate and illegal-move rate by condition) and lessons.png
(lessons written vs still live across training).
"""

import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BLUE, ORANGE = "#2a78d6", "#eb6834"  # categorical slots 1 and 2
INK, INK_2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#ffffff"
LABELS = {"A": "A\nno lessons", "B": "B\ntraining", "C": "C\nfrozen lessons", "D": "D\nno ToT"}


def style(ax, title: str) -> None:
    ax.set_title(title, loc="left", fontsize=13, color=INK, pad=12)
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK_2, length=0)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def bars(ax, conds, values, labels, title, ymax):
    x = range(len(conds))
    ax.bar(x, values, width=0.55, color=BLUE, edgecolor=SURFACE, linewidth=2)
    for i, (v, lab) in enumerate(zip(values, labels)):
        ax.text(i, v + ymax * 0.02, lab, ha="center", va="bottom", fontsize=10, color=INK)
    ax.set_xticks(list(x), [LABELS[c] for c in conds], fontsize=9.5)
    ax.set_ylim(0, ymax)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    style(ax, title)


def main():
    run, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader((run / "results.csv").open()))
    conds = [c for c in "ABCD" if any(r["condition"] == c for r in rows)]

    win, win_lab, bad, bad_lab = [], [], [], []
    for c in conds:
        rs = [r for r in rows if r["condition"] == c]
        w = sum(int(r["llm_won"]) for r in rs)
        moves, ill = sum(int(r["llm_moves"]) for r in rs), sum(int(r["illegal"]) for r in rs)
        win.append(100 * w / len(rs))
        win_lab.append(f"{w}/{len(rs)}")
        bad.append(100 * ill / moves)
        bad_lab.append(f"{ill}/{moves}")

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2), facecolor=SURFACE)
    bars(a1, conds, win, win_lab, "Win rate vs greedy", max(40, max(win) * 1.3))
    bars(a2, conds, bad, bad_lab, "Illegal-move rate", max(25, max(bad) * 1.3))
    fig.tight_layout(w_pad=4)
    fig.savefig(out / "conditions.png", dpi=200)

    snaps = sorted((run / "B").glob("lessons-g*.json"))
    if snaps:
        written, live = [], []
        for p in snaps:
            ls = json.loads(p.read_text())
            written.append(len(ls))
            live.append(sum(l["status"] != "retired" for l in ls))
        games = range(1, len(snaps) + 1)
        fig, ax = plt.subplots(figsize=(8, 4.2), facecolor=SURFACE)
        ax.plot(games, written, color=BLUE, linewidth=2, marker="o", markersize=5)
        ax.plot(games, live, color=ORANGE, linewidth=2, marker="o", markersize=5)
        ax.text(games[-1] + 0.4, written[-1], f"written ({written[-1]})", va="center", color=INK, fontsize=10)
        ax.text(games[-1] + 0.4, live[-1], f"still live ({live[-1]})", va="center", color=INK, fontsize=10)
        ax.set_xlim(0.5, games[-1] + 4)
        ax.set_ylim(0, max(written) + 2)
        ax.set_xticks([1, 5, 10, 15, 20][: 1 + len(snaps) // 5])
        ax.set_xlabel("Training game (condition B)", color=INK_2)
        style(ax, "Lessons written vs still live during training")
        fig.tight_layout()
        fig.savefig(out / "lessons.png", dpi=200)
    print(f"charts in {out}")


if __name__ == "__main__":
    main()

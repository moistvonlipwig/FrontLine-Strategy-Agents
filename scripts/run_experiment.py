# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Run the A-D experiment unattended: resumable, one log line per game, a summary after every game.

    uv run python scripts/run_experiment.py --seed 1                                 # plan counts (50/120/50/30)
    uv run python scripts/run_experiment.py --seed 1 --a 10 --b 20 --c 10 --d 10     # short pass
    uv run python scripts/run_experiment.py --seed 1 --player greedy --a 4 --b 4 --c 4 --d 4   # smoke test, no LLM
    uv run python scripts/run_experiment.py --seed 1 --only A C                      # some conditions only
    uv run python scripts/run_experiment.py --seed 1 --summary                       # rebuild summary.md only

Conditions (the LLM is coral, greedy is teal, first mover alternates):
  A  baseline: no lessons
  B  training: lessons on, review crew after every game, store starts empty
  C  frozen eval: B's final store, read-only
  D  ablation: C with tree-of-thought off (single candidate)

Writes runs/seed<N>/:
  results.csv               one row per finished game; a rerun skips games already listed
  summary.md                per-condition table, rewritten after every game
  log.txt                   the same one-line-per-game log printed to the terminal
  <cond>/<game_id>.json     turn records, plus <game_id>.spans.json (OpenTelemetry)
  lessons.json              B's store, saved after every B game (B/lessons-gNNN.json are snapshots)
  lessons-frozen.json       copy of the store once B finishes; C and D read it and never write it

Stops after 3 games in a row raise an error. Failed games are not written to results.csv,
so rerunning the same command retries them.
"""

import argparse
import csv
import shutil
import sys
import time
import traceback
from pathlib import Path

from frontline.bots import GreedyBot, RandomBot
from frontline.engine import Game, cells_of
from frontline.lessons import LessonStore
from frontline.match import play_match
from frontline.player import PlayerAgent

LLM, OPP = "coral", "teal"
PLAN = {"A": 50, "B": 120, "C": 50, "D": 30}
FIELDS = ["condition", "seed", "game", "game_id", "first", "winner", "llm_won", "end", "llm_cells", "opp_cells",
          "llm_moves", "illegal", "tot_turns", "picked_best", "cited_turns", "lessons_live", "new_lesson", "seconds"]
MAX_ERRORS = 3


def make_player(kind: str, model: str, seed: int, tot: bool):
    if kind == "llm":
        return PlayerAgent(model=model, tot=tot)
    return {"greedy": GreedyBot, "random": RandomBot}[kind](seed=seed)


def game_stats(game: Game) -> dict:
    """Per-game numbers from the turn records, for the LLM seat only."""
    mine = [r for r in game.history if r.player == LLM]
    tot = [r for r in mine if len(r.candidates) > 1]
    picked_best = 0
    for r in tot:
        scores = [sc["score_2ply"] for sc in r.candidate_scores if sc.get("legal")]
        mine_sc = next((sc.get("score_2ply") for c, sc in zip(r.candidates, r.candidate_scores)
                        if c.key() == r.action.key()), None)
        picked_best += bool(scores) and mine_sc == max(scores)
    # A citation only counts if that lesson was actually retrieved this turn (the LLM sometimes cites "expand")
    cited = sum(bool(set(r.action.cited_lessons) & set(r.retrieved_lessons)) for r in mine)
    winner, how = game.outcome()
    return {"winner": winner or "draw", "llm_won": int(winner == LLM), "end": how,
            "llm_cells": len(cells_of(game.state, LLM)), "opp_cells": len(cells_of(game.state, OPP)),
            "llm_moves": len(mine), "illegal": sum(not r.legal for r in mine), "tot_turns": len(tot),
            "picked_best": picked_best, "cited_turns": cited}


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


def append_row(path: Path, row: dict) -> None:
    new = not path.exists()
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)


def pct(n: int, d: int) -> str:
    return f"{n / d:.0%}" if d else "-"


def write_summary(out: Path, seed: int, targets: dict[str, int]) -> None:
    rows = load_rows(out / "results.csv")
    lines = [f"# FrontLine experiment, seed {seed}", "", f"Updated {time.strftime('%Y-%m-%d %H:%M')}", "",
             "| Cond | Games | LLM wins | Win rate | Draws | Illegal | Picked best | Avg cells | Lessons live |",
             "|---|---|---|---|---|---|---|---|---|"]
    for cond in "ABCD":
        rs = [r for r in rows if r["condition"] == cond]
        if not rs and not targets.get(cond):
            continue
        n = len(rs)
        wins = sum(int(r["llm_won"]) for r in rs)
        draws = sum(r["winner"] == "draw" for r in rs)
        moves, bad = sum(int(r["llm_moves"]) for r in rs), sum(int(r["illegal"]) for r in rs)
        tot, best = sum(int(r["tot_turns"]) for r in rs), sum(int(r["picked_best"]) for r in rs)
        cells = f"{sum(int(r['llm_cells']) for r in rs) / n:.1f}" if n else "-"
        live = rs[-1]["lessons_live"] if rs else "-"
        lines.append(f"| {cond} | {n}/{targets.get(cond, n)} | {wins} | {pct(wins, n)} | {draws} | "
                     f"{pct(bad, moves)} | {pct(best, tot)} | {cells} | {live} |")

    lines += ["", "**Win rate when a lesson was cited vs not** (games with at least one cited, retrieved lesson):", ""]
    for cond in "BCD":
        rs = [r for r in rows if r["condition"] == cond]
        if not rs:
            continue
        cited = [r for r in rs if int(r["cited_turns"]) > 0]
        plain = [r for r in rs if int(r["cited_turns"]) == 0]
        lines.append(f"- {cond}: cited {sum(int(r['llm_won']) for r in cited)}/{len(cited)} "
                     f"({pct(sum(int(r['llm_won']) for r in cited), len(cited))}), "
                     f"not cited {sum(int(r['llm_won']) for r in plain)}/{len(plain)} "
                     f"({pct(sum(int(r['llm_won']) for r in plain), len(plain))})")
    hours = sum(float(r["seconds"]) for r in rows) / 3600
    lines += ["", f"{len(rows)} games, {hours:.1f} h of play.", ""]
    (out / "summary.md").write_text("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1, help="experiment seed; also sets the runs/seed<N>/ folder")
    for cond, n in PLAN.items():
        ap.add_argument(f"--{cond.lower()}", type=int, default=n, help=f"games in condition {cond} (default {n})")
    ap.add_argument("--only", nargs="+", choices=list(PLAN), help="run only these conditions, in A-D order")
    ap.add_argument("--player", default="llm", choices=["llm", "greedy", "random"],
                    help="coral's player; non-LLM skips the review crew (smoke test)")
    ap.add_argument("--model", default="qwen3:32b")
    ap.add_argument("--out", default="runs")
    ap.add_argument("--summary", action="store_true", help="rebuild summary.md from results.csv and exit")
    args = ap.parse_args()

    targets = {c: getattr(args, c.lower()) for c in PLAN}
    out = Path(args.out) / f"seed{args.seed}"
    out.mkdir(parents=True, exist_ok=True)
    if args.summary:
        write_summary(out, args.seed, targets)
        print((out / "summary.md").read_text())
        return

    results, log_path = out / "results.csv", out / "log.txt"
    store_path, frozen_path = out / "lessons.json", out / "lessons-frozen.json"
    review = args.player == "llm"

    def log(msg: str) -> None:
        line = f"{time.strftime('%m-%d %H:%M:%S')}  {msg}"
        print(line, flush=True)
        with log_path.open("a") as f:
            f.write(line + "\n")

    done = {(r["condition"], int(r["game"])) for r in load_rows(results)}
    errors = 0
    for cond in [c for c in PLAN if not args.only or c in args.only]:
        if cond in "CD" and not frozen_path.exists():
            log(f"{cond}: skipped, B has not finished {targets['B']} games, so there is no frozen store yet")
            continue
        for i in range(targets[cond]):
            if (cond, i) in done:
                continue
            first = LLM if i % 2 == 0 else OPP
            game_id = f"s{args.seed}-{cond}-g{i:03d}"
            bot_seed = args.seed * 100_000 + ord(cond) * 1_000 + i  # distinct per game, same on rerun
            store = (LessonStore(store_path) if cond == "B" else
                     LessonStore(frozen_path) if cond in "CD" else None)
            players = {LLM: make_player(args.player, args.model, bot_seed, tot=cond != "D"),
                       OPP: GreedyBot(seed=bot_seed + 1)}
            game = Game(first=first, game_id=game_id,
                        meta={LLM: args.player, OPP: "greedy", "condition": cond, "seed": args.seed})
            start = time.time()
            new_lesson = ""
            try:
                play_match(game, players, spans_path=out / cond / f"{game_id}.spans.json", store=store)
                game.save_trace(out / cond / f"{game_id}.json")
                if cond == "B" and review:
                    from frontline.crew import review_game  # crewai is slow to import; only load when used
                    s = review_game(game.trace(), store, LLM)
                    new_lesson = s["lesson"] or ""
                if cond == "B":
                    store.save()
                    store.save(out / "B" / f"lessons-g{i:03d}.json")
            except Exception:
                errors += 1
                log(f"{game_id}  ERROR ({errors} in a row)\n{traceback.format_exc()}")
                if errors >= MAX_ERRORS:
                    log(f"stopping: {MAX_ERRORS} errors in a row")
                    write_summary(out, args.seed, targets)
                    sys.exit(1)
                continue
            errors = 0
            st = game_stats(game)
            row = {"condition": cond, "seed": args.seed, "game": i, "game_id": game_id, "first": first, **st,
                   "lessons_live": len(store.live()) if store else 0, "new_lesson": new_lesson,
                   "seconds": round(time.time() - start, 1)}
            append_row(results, row)
            write_summary(out, args.seed, targets)
            log(f"{game_id}  first={first:5s}  winner={st['winner']:5s} ({st['end']})  "
                f"illegal {st['illegal']}/{st['llm_moves']}  best {st['picked_best']}/{st['tot_turns']}  "
                f"cited {st['cited_turns']}  lessons {row['lessons_live']}"
                + (f" +{new_lesson}" if new_lesson else "") + f"  {row['seconds']:.0f}s")
        if cond == "B" and not frozen_path.exists() and store_path.exists() \
                and sum(r["condition"] == "B" for r in load_rows(results)) >= targets["B"]:
            shutil.copy(store_path, frozen_path)
            log(f"B done, froze {store_path} -> {frozen_path}")

    write_summary(out, args.seed, targets)
    log(f"finished, summary in {out / 'summary.md'}")


if __name__ == "__main__":
    main()

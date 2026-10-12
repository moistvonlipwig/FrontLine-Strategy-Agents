# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Run many bot-vs-bot games and report win rates.

    uv run python scripts/run_bots.py --games 1000 --a greedy --b greedy
    uv run python scripts/run_bots.py --games 1 --show          # watch one game
"""

import argparse
import time
from collections import Counter

from frontline.bots import GreedyBot, RandomBot
from frontline.engine import Game
from frontline.render import render

BOTS = {"random": RandomBot, "greedy": GreedyBot}


def play(bot_a, bot_b, first: str, game_id: str, show: bool = False) -> Game:
    """bot_a plays coral, bot_b plays teal."""
    g = Game(first=first, game_id=game_id, meta={"coral": bot_a.name, "teal": bot_b.name})
    seats = {"coral": bot_a, "teal": bot_b}
    while not g.is_over():
        rec = g.apply(seats[g.state.to_move].act(g.get_state()))
        if show:
            print(f"\n{rec.player} {rec.action.key()}  ({rec.action.reason})")
            print(render(g.state))
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=1000)
    ap.add_argument("--a", default="greedy", choices=BOTS)
    ap.add_argument("--b", default="greedy", choices=BOTS)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--save-traces", default=None, help="folder for JSON traces")
    args = ap.parse_args()

    a, b = BOTS[args.a](seed=args.seed), BOTS[args.b](seed=args.seed + 1)
    wins, ends, first_wins, illegal = Counter(), Counter(), 0, 0
    t0 = time.time()
    for i in range(args.games):
        first = "coral" if i % 2 == 0 else "teal"  # alternate who moves first
        g = play(a, b, first, f"g{i:04d}", show=args.show)
        winner, how = g.outcome()
        wins[winner or "draw"] += 1
        ends[how.split()[0]] += 1
        first_wins += winner == first
        illegal += sum(not r.legal for r in g.history)
        if args.save_traces:
            g.save_trace(f"{args.save_traces}/{g.game_id}.json")
        if args.show:
            print(f"\nwinner: {winner} ({how})")

    n = args.games
    print(f"{n} games  coral={args.a} teal={args.b}  {time.time() - t0:.1f}s")
    print(f"wins: {dict(wins)}")
    print(f"end types: {dict(ends)}")
    print(f"first-mover win rate: {first_wins / n:.1%}")
    print(f"illegal moves: {illegal}")


if __name__ == "__main__":
    main()

# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Play one game through the LangGraph match loop and watch it turn by turn.

    uv run python scripts/run_match.py                        # LLM (coral) vs greedy (teal)
    uv run python scripts/run_match.py --coral greedy --teal random   # fast, no LLM
    uv run python scripts/run_match.py --first teal --model llama3.1:8b
    uv run python scripts/run_match.py --games 10 --quiet     # illegal-move rate over 10 games
    uv run python scripts/run_match.py --no-tot               # single candidate (condition D)
    uv run python scripts/run_match.py --lessons tests/fixtures/lessons.json   # retrieval check

Saves traces/<game_id>.json (turn records) and traces/<game_id>.spans.json (OpenTelemetry).
"""

import argparse
import time

from frontline.bots import GreedyBot, RandomBot
from frontline.engine import Game
from frontline.lessons import LessonStore
from frontline.match import play_match
from frontline.player import PlayerAgent
from frontline.render import render


def make(kind: str, model: str, seed: int, tot: bool = True):
    if kind == "llm":
        return PlayerAgent(model=model, tot=tot)
    return {"greedy": GreedyBot, "random": RandomBot}[kind](seed=seed)


def show(game: Game, t0: list[float]):
    rec = game.history[-1]
    took = time.time() - t0[0]
    t0[0] = time.time()
    flag = "" if rec.legal else f"  ILLEGAL: {rec.illegal_reason}"
    print(f"\nturn {rec.turn:2d}  {rec.player:5s}  {rec.action.key():16s} ({took:4.1f}s){flag}")
    if rec.retrieved_lessons:
        print(f"           lessons {rec.retrieved_lessons}  cited {rec.action.cited_lessons}")
    for c, sc in zip(rec.candidates, rec.candidate_scores):
        mark = "*" if c.key() == rec.action.key() else " "
        print(f"         {mark} {c.key():16s} 2-ply {sc.get('score_2ply', 'illegal')}")
    if rec.action.reason:
        print(f"           {rec.action.reason}")
    print(render(game.state))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coral", default="llm", choices=["llm", "greedy", "random"])
    ap.add_argument("--teal", default="greedy", choices=["llm", "greedy", "random"])
    ap.add_argument("--first", default="coral", choices=["coral", "teal"])
    ap.add_argument("--model", default="qwen3:32b")
    ap.add_argument("--games", type=int, default=1, help="first mover alternates each game")
    ap.add_argument("--no-tot", action="store_true", help="single candidate, no tree-of-thought")
    ap.add_argument("--lessons", help="lesson store JSON; omit for no lessons (condition A)")
    ap.add_argument("--quiet", action="store_true", help="one line per game, no boards")
    ap.add_argument("--game-id", default=f"match-{time.strftime('%Y%m%d-%H%M%S')}")
    args = ap.parse_args()

    players = {"coral": make(args.coral, args.model, 1, not args.no_tot),
               "teal": make(args.teal, args.model, 2, not args.no_tot)}
    store = LessonStore(args.lessons) if args.lessons else None
    llm_seats = {c for c, p in players.items() if isinstance(p, PlayerAgent)}
    other_first = "teal" if args.first == "coral" else "coral"
    llm_moves = llm_illegal = 0
    wins = {}

    for i in range(args.games):
        first = args.first if i % 2 == 0 else other_first
        game_id = args.game_id if args.games == 1 else f"{args.game_id}-g{i:02d}"
        game = Game(first=first, game_id=game_id, meta={"coral": args.coral, "teal": args.teal})
        t0 = [time.time()]
        start = t0[0]
        on_turn = None if args.quiet else (lambda g: show(g, t0))
        if not args.quiet:
            print(render(game.state))

        play_match(game, players, spans_path=f"traces/{game_id}.spans.json", on_turn=on_turn, store=store)
        game.save_trace(f"traces/{game_id}.json")

        winner, how = game.outcome()
        wins[winner or "draw"] = wins.get(winner or "draw", 0) + 1
        mine = [r for r in game.history if r.player in llm_seats]
        bad = sum(not r.legal for r in mine)
        llm_moves, llm_illegal = llm_moves + len(mine), llm_illegal + bad
        print(f"{game_id}  first={first:5s}  winner={winner or 'draw':5s} ({how})  "
              f"LLM illegal {bad}/{len(mine)}  {time.time() - start:.0f}s", flush=True)

    print(f"\nwins: {wins}")
    if llm_moves:
        print(f"LLM illegal-move rate: {llm_illegal}/{llm_moves} = {llm_illegal / llm_moves:.1%}")
    print("traces saved in traces/")


if __name__ == "__main__":
    main()

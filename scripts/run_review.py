# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Run the review crew on saved game traces and update the lesson store.

    uv run python scripts/run_review.py traces/match-XXXX.json
    uv run python scripts/run_review.py traces/*.json --lessons lessons/lessons.json

The reviewed player is the LLM seat in the trace meta (or --player). Needs Ollama.
"""

import argparse
import json
from pathlib import Path

from frontline.crew import make_llm, review_game
from frontline.lessons import LessonStore


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("traces", nargs="+")
    ap.add_argument("--lessons", default="lessons/lessons.json")
    ap.add_argument("--player", choices=["coral", "teal"], help="default: the LLM seat in the trace meta")
    ap.add_argument("--model", default="qwen3:32b")
    args = ap.parse_args()

    store, llm = LessonStore(args.lessons), make_llm(args.model)
    for path in args.traces:
        trace = json.loads(Path(path).read_text())
        player = args.player or next((c for c in ("coral", "teal") if trace["meta"].get(c) == "llm"), None)
        if player is None:
            print(f"{path}: no LLM seat, skipped")
            continue
        s = review_game(trace, store, player, llm)
        store.save()  # after every game, so a crash loses at most one review
        tp, crit, dec = s["turning_point"], s["critic"], s["decision"]
        print(f"{s['game_id']}  {player}  scored {s['scored']}  turn {tp['turn']}  "
              f"critic {'ok' if crit['approved'] else 'REJECT'}  {dec['action']} -> {s['lesson']}")
        if s["lesson"]:
            print(f"    {dec['text']}  (when: {dec['trigger']})")
        elif not crit["approved"]:
            print(f"    rejected: {crit['problem']}")
    print(f"{len(store.live())} live lessons in {args.lessons}")


if __name__ == "__main__":
    main()

# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""What the review crew is allowed to see.

The crew judges the game from the moves and boards only. Everything the player said or
was shown is stripped, so the reviewer can't grade the player's own story:
    - reason, cited_lessons (the player's explanation)
    - candidates, candidate_scores (its tree-of-thought)
    - retrieved_lessons (what the lesson store showed it)
"""

from .render import render
from .schemas import TurnRecord


def strip_turn(record: TurnRecord) -> dict:
    return {
        "turn": record.turn,
        "player": record.player,
        "move": record.action.key(),
        "legal": record.legal,
        "illegal_reason": record.illegal_reason,
        "board_before": render(record.state_before, color=False),
        "board_after": render(record.state_after, color=False),
    }


def strip_trace(trace: dict) -> dict:
    """A saved trace (Game.trace() / traces/<game_id>.json) cut down for the crew."""
    return {
        "game_id": trace["game_id"],
        "winner": trace["winner"],
        "end": trace["end"],
        "turns": [strip_turn(TurnRecord.model_validate(t)) for t in trace["turns"]],
    }

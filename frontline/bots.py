# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Baseline opponents: random and one-ply greedy."""

import random

from .engine import cells_of, home_captured, legal_moves, other, step
from .schemas import Action, GameState, Player


def score(state: GameState, p: Player) -> float:
    """Board value for p: cells count most, then total strength."""
    if (w := home_captured(state)) is not None:
        return 1000 if w == p else -1000
    me, op = cells_of(state, p), cells_of(state, other(p))
    strength = sum(state.board[c].strength for c in me) - sum(state.board[c].strength for c in op)
    return 10 * (len(me) - len(op)) + strength


class RandomBot:
    name = "random"

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def act(self, state: GameState) -> Action:
        a = self.rng.choice(legal_moves(state))
        a.reason = "random"
        return a


class GreedyBot:
    """Pick the move with the best board score one turn ahead. Ties broken randomly."""

    name = "greedy"

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def act(self, state: GameState) -> Action:
        p = state.to_move
        scored = [(score(step(state, a)[0], p), a) for a in legal_moves(state)]
        best = max(s for s, _ in scored)
        a = self.rng.choice([a for s, a in scored if s == best])
        a.reason = f"greedy score {best:+.0f}"
        return a

# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""FrontLine v1 rules engine. Plain, deterministic Python: no LLM, no randomness.

Pure functions (step, legal_moves, attack_power, supplied_cells) are reused by the
bots and, later, by the Player Agent's read-only tools. `Game` wraps them with an
OpenSpiel-style API: get_state, legal_moves, apply, is_over, outcome, save_trace.
"""

import json
from pathlib import Path

from .schemas import (
    CELLS,
    COLS,
    MAX_STRENGTH,
    ROWS,
    TOTAL_TURNS,
    Action,
    Cell,
    GameState,
    Player,
    TurnRecord,
)

HOMES = {"coral": "A1", "teal": "E5"}
FIRST_HOME_STRENGTH = 3  # first-mover handicap, offsets the second mover's last turn
SECOND_HOME_STRENGTH = 2


def other(p: Player) -> Player:
    return "teal" if p == "coral" else "coral"


def neighbors(cell: str) -> list[str]:
    """Up, down, left, right. No diagonals."""
    c, r = COLS.index(cell[0]), ROWS.index(cell[1])
    out = []
    for dc, dr in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nc, nr = c + dc, r + dr
        if 0 <= nc < 5 and 0 <= nr < 5:
            out.append(COLS[nc] + ROWS[nr])
    return out


NEIGHBORS = {cell: neighbors(cell) for cell in CELLS}


def initial_state(first: Player = "coral") -> GameState:
    board = {cell: Cell() for cell in CELLS}
    for p, home in HOMES.items():
        board[home] = Cell(owner=p, strength=FIRST_HOME_STRENGTH if p == first else SECOND_HOME_STRENGTH)
    return GameState(board=board, to_move=first, turn=1, homes=dict(HOMES))


def clone(state: GameState) -> GameState:
    # model_construct skips validation; ~10x faster than model_copy(deep=True) for bot search.
    board = {k: Cell.model_construct(owner=v.owner, strength=v.strength) for k, v in state.board.items()}
    return GameState.model_construct(board=board, to_move=state.to_move, turn=state.turn, homes=state.homes)


def cells_of(state: GameState, p: Player) -> list[str]:
    return [k for k, v in state.board.items() if v.owner == p]


def attack_power(state: GameState, source: str, target: str) -> int:
    """Source strength + 1 for each *other* own cell touching the target."""
    p = state.board[source].owner
    support = sum(1 for n in NEIGHBORS[target] if n != source and state.board[n].owner == p)
    return state.board[source].strength + support


def supplied_cells(state: GameState, p: Player) -> set[str]:
    """Cells connected to p's home through p's own adjacent cells (flood fill)."""
    home = state.homes[p]
    if state.board[home].owner != p:
        return set()
    seen, stack = {home}, [home]
    while stack:
        for n in NEIGHBORS[stack.pop()]:
            if n not in seen and state.board[n].owner == p:
                seen.add(n)
                stack.append(n)
    return seen


def check_action(state: GameState, action: Action) -> str | None:
    """Return None if legal, else the reason it is illegal."""
    p = state.to_move
    b = state.board
    if action.target not in b:
        return f"unknown cell {action.target}"
    tgt = b[action.target]
    if action.kind == "claim":
        if tgt.owner is not None:
            return f"{action.target} is not empty"
        if not any(b[n].owner == p for n in NEIGHBORS[action.target]):
            return f"{action.target} is not adjacent to a {p} cell"
    elif action.kind == "reinforce":
        if tgt.owner != p:
            return f"{action.target} is not owned by {p}"
        if tgt.strength >= MAX_STRENGTH:
            return f"{action.target} is already at max strength {MAX_STRENGTH}"
    elif action.kind == "attack":
        if action.source is None or action.source not in b:
            return "attack needs a valid source cell"
        if b[action.source].owner != p:
            return f"source {action.source} is not owned by {p}"
        if tgt.owner != other(p):
            return f"target {action.target} is not an enemy cell"
        if action.target not in NEIGHBORS[action.source]:
            return f"{action.source} is not adjacent to {action.target}"
    return None


def legal_moves(state: GameState) -> list[Action]:
    if is_over(state):
        return []
    p = state.to_move
    b = state.board
    mine = cells_of(state, p)
    moves: list[Action] = []
    claims = sorted({n for c in mine for n in NEIGHBORS[c] if b[n].owner is None})
    moves += [Action(kind="claim", target=t) for t in claims]
    moves += [Action(kind="reinforce", target=c) for c in mine if b[c].strength < MAX_STRENGTH]
    for c in mine:
        for n in NEIGHBORS[c]:
            if b[n].owner == other(p):
                moves.append(Action(kind="attack", source=c, target=n))
    return moves


def _set_strength(state: GameState, cell: str, s: int) -> None:
    """Apply a strength change, honoring the home floor of 1 and emptying cells at 0."""
    c = state.board[cell]
    if cell in state.homes.values() and c.owner is not None:
        s = max(s, 1)
    if s <= 0:
        c.owner, c.strength = None, 0
    else:
        c.strength = min(s, MAX_STRENGTH)


def _apply_supply(state: GameState) -> None:
    for p in ("coral", "teal"):
        ok = supplied_cells(state, p)
        for cell in cells_of(state, p):
            if cell not in ok:
                _set_strength(state, cell, state.board[cell].strength - 1)


def step(state: GameState, action: Action) -> tuple[GameState, str | None]:
    """Apply one turn and return (new_state, illegal_reason). Does not mutate `state`.

    An illegal action forfeits the turn, but supply still runs and the turn still advances.
    """
    s = clone(state)
    p = s.to_move
    reason = check_action(s, action)
    if reason is None:
        b = s.board
        if action.kind == "claim":
            b[action.target].owner, b[action.target].strength = p, 1
        elif action.kind == "reinforce":
            b[action.target].strength += 1
        else:
            src, tgt = b[action.source], b[action.target]
            if attack_power(s, action.source, action.target) > tgt.strength:
                new_strength = max(1, src.strength - tgt.strength)  # support does not add here
                tgt.owner, tgt.strength = p, new_strength
                src.strength = 1
            else:  # ties favor the defender
                _set_strength(s, action.source, src.strength - 1)
    if not home_captured(s):
        _apply_supply(s)
    s.turn += 1
    s.to_move = other(p)
    return s, reason


def home_captured(state: GameState) -> Player | None:
    """Return the player who captured the enemy home, if any."""
    for p, home in state.homes.items():
        if state.board[home].owner != p:
            return other(p)
    return None


def is_over(state: GameState) -> bool:
    return home_captured(state) is not None or state.turn > TOTAL_TURNS


def outcome(state: GameState) -> tuple[Player | None, str]:
    """(winner or None for draw, how it ended). Only meaningful once is_over()."""
    if (w := home_captured(state)) is not None:
        return w, "home captured"
    cc, tc = len(cells_of(state, "coral")), len(cells_of(state, "teal"))
    if cc != tc:
        return ("coral" if cc > tc else "teal"), f"cells {cc}-{tc}"
    cs = sum(state.board[c].strength for c in cells_of(state, "coral"))
    ts = sum(state.board[c].strength for c in cells_of(state, "teal"))
    if cs != ts:
        return ("coral" if cs > ts else "teal"), f"strength {cs}-{ts}"
    return None, "draw"


class Game:
    """Stateful wrapper that records a TurnRecord per turn."""

    def __init__(self, first: Player = "coral", game_id: str = "game", meta: dict | None = None):
        self.state = initial_state(first)
        self.first = first
        self.game_id = game_id
        self.meta = meta or {}
        self.history: list[TurnRecord] = []

    def get_state(self) -> GameState:
        return clone(self.state)

    def legal_moves(self) -> list[Action]:
        return legal_moves(self.state)

    def is_over(self) -> bool:
        return is_over(self.state)

    def outcome(self) -> tuple[Player | None, str]:
        return outcome(self.state)

    def apply(self, action: Action, candidates: list[Action] | None = None,
              candidate_scores: list[dict] | None = None,
              retrieved_lessons: list[str] | None = None) -> TurnRecord:
        if self.is_over():
            raise RuntimeError("game is over")
        before = self.state
        after, reason = step(before, action)
        rec = TurnRecord(
            turn=before.turn,
            player=before.to_move,
            state_before=before,
            action=action,
            legal=reason is None,
            illegal_reason=reason,
            state_after=after,
            candidates=candidates or [],
            candidate_scores=candidate_scores or [],
            retrieved_lessons=retrieved_lessons or [],
        )
        self.history.append(rec)
        self.state = after
        return rec

    def trace(self) -> dict:
        winner, how = self.outcome() if self.is_over() else (None, "in progress")
        return {
            "game_id": self.game_id,
            "first": self.first,
            "winner": winner,
            "end": how,
            "meta": self.meta,
            "turns": [r.model_dump() for r in self.history],
        }

    def save_trace(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.trace(), indent=1))
        return path

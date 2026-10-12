# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Data contracts shared by the engine, bots, agents, and tracing (see docs/architecture.md)."""

from typing import Literal

from pydantic import BaseModel

Player = Literal["coral", "teal"]
COLS = "ABCDE"
ROWS = "12345"
CELLS = [c + r for r in ROWS for c in COLS]  # A1, B1, ..., E5
MAX_STRENGTH = 5
TURNS_PER_PLAYER = 12
TOTAL_TURNS = 2 * TURNS_PER_PLAYER


class Cell(BaseModel):
    owner: Player | None = None
    strength: int = 0  # 0 to 5


class GameState(BaseModel):
    board: dict[str, Cell]  # "A1" to "E5"
    to_move: Player
    turn: int  # 1 to 24 while playing, 25 once all turns are used
    homes: dict[str, str]  # {"coral": "A1", "teal": "E5"}


class Action(BaseModel):
    kind: Literal["claim", "reinforce", "attack"]
    target: str  # e.g. "C3"
    source: str | None = None  # attacking cell, attack only
    reason: str = ""
    cited_lessons: list[str] = []

    def key(self) -> str:
        """Short label, e.g. 'attack C2->D3'. Ignores reason so actions compare by move."""
        return f"{self.kind} {self.source}->{self.target}" if self.source else f"{self.kind} {self.target}"


class TurnRecord(BaseModel):
    turn: int
    player: Player
    state_before: GameState
    action: Action
    legal: bool
    illegal_reason: str | None = None
    state_after: GameState
    candidates: list[Action] = []  # tree-of-thought options (Day 3)


class Lesson(BaseModel):
    id: str
    text: str
    trigger: str  # board situation it applies to
    wins: int = 0
    losses: int = 0
    confidence: float = 0.5
    status: Literal["candidate", "active", "retired"] = "candidate"
    source_game: str

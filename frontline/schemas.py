# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Data contracts shared by the engine, bots, agents, and tracing (see docs/architecture.md)."""

from typing import Literal

from pydantic import BaseModel, Field

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


CELL_PATTERN = r"^[A-E][1-5]$"


class Action(BaseModel):
    # Field descriptions + pattern go into the JSON schema the LLM is constrained to.
    kind: Literal["claim", "reinforce", "attack"]
    target: str = Field(pattern=CELL_PATTERN, description='One cell only, e.g. "C3". The cell claimed, reinforced, or attacked.')
    source: str | None = Field(None, pattern=CELL_PATTERN, description='Attack only: your attacking cell, e.g. "C2". null otherwise.')
    reason: str = Field("", description="One sentence: why this move.")
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
    candidates: list[Action] = []  # tree-of-thought options
    candidate_scores: list[dict] = []  # tools.score_2ply result per candidate
    retrieved_lessons: list[str] = []  # ids of lessons shown to the player this turn


class Lesson(BaseModel):
    id: str
    text: str
    trigger: str  # board situation it applies to
    wins: int = 0
    losses: int = 0
    confidence: float = 0.5
    status: Literal["candidate", "active", "retired"] = "candidate"
    source_game: str
    vector: list[float] = []  # embedding of the board it was learned on (lessons.embed)

# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Lesson store: lessons saved as JSON, retrieved by board similarity (a tiny vector store).

Each lesson keeps the vector of the board it was learned on. Retrieval embeds the current
board the same way and returns the top k by cosine similarity. Plain Python: 26 numbers
per vector, at most 30 lessons, so no vector database is needed.

Embedding is from the mover's point of view, so a lesson learned as coral also fits teal:
    - the board is rotated 180 degrees for teal, so your home is always A1
    - each cell = +strength/5 if yours, -strength/5 if the enemy's, 0 if empty
    - last number = game progress (turn / 24)
"""

import json
import math
from pathlib import Path

from .schemas import CELLS, MAX_STRENGTH, TOTAL_TURNS, GameState, Lesson


def embed(state: GameState) -> list[float]:
    me = state.to_move
    cells = CELLS if me == "coral" else CELLS[::-1]  # reversed list = 180-degree rotation
    vec = []
    for c in cells:
        cell = state.board[c]
        sign = 0 if cell.owner is None else (1 if cell.owner == me else -1)
        vec.append(sign * cell.strength / MAX_STRENGTH)
    vec.append(state.turn / TOTAL_TURNS)
    return vec


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


class LessonStore:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else None
        self.lessons: list[Lesson] = []
        if self.path and self.path.exists():
            self.lessons = [Lesson(**d) for d in json.loads(self.path.read_text())]

    def add(self, lesson: Lesson, state: GameState | None = None) -> Lesson:
        """Add a lesson; `state` is the board it was learned on (sets its vector)."""
        if state is not None:
            lesson.vector = embed(state)
        self.lessons.append(lesson)
        return lesson

    def search(self, state: GameState, k: int = 3) -> list[tuple[Lesson, float]]:
        """Top k non-retired lessons by board similarity, best first."""
        q = embed(state)
        hits = [(l, cosine(q, l.vector)) for l in self.lessons if l.status != "retired" and l.vector]
        return sorted(hits, key=lambda h: -h[1])[:k]

    def save(self, path: str | Path | None = None) -> Path:
        path = Path(path or self.path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([l.model_dump() for l in self.lessons], indent=1))
        return path

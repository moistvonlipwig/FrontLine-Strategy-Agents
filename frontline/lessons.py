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

from .schemas import CELLS, MAX_STRENGTH, TOTAL_TURNS, GameState, Lesson, Player, TurnRecord

CAP = 30  # most live (non-retired) lessons the store keeps
PROMOTE_GAMES = 3  # candidate -> active after this many cited games...
PROMOTE_CONF = 0.5  # ...if confidence is at least this
RETIRE_GAMES = 5  # retire after this many cited games...
RETIRE_CONF = 0.4  # ...if confidence is below this


def confidence(wins: int, losses: int) -> float:
    """Win rate with 1 fake win and 1 fake loss added, so a new lesson starts at 0.5
    and one lucky game can't push it to 1.0."""
    return (wins + 1) / (wins + losses + 2)


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
        self._enforce_cap(keep=lesson.id)
        return lesson

    def live(self) -> list[Lesson]:
        return [l for l in self.lessons if l.status != "retired"]

    def _enforce_cap(self, keep: str) -> None:
        """Over the cap: retire the lowest-confidence live lesson (never the one just added)."""
        while len(self.live()) > CAP:
            worst = min((l for l in self.live() if l.id != keep),
                        key=lambda l: (l.confidence, -(l.wins + l.losses)))  # tie: most-tested goes
            worst.status = "retired"

    def record_game(self, records: list[TurnRecord], player: Player, winner: Player | None) -> list[str]:
        """Update the tally for every lesson `player` cited this game. Credit goes to cited
        lessons only (not just retrieved), so advice the agent ignored isn't scored.
        A draw counts for nothing. Returns the ids that were updated."""
        if winner is None:
            return []
        cited = {i for r in records if r.player == player for i in r.action.cited_lessons}
        updated = []
        for l in self.lessons:
            if l.id not in cited or l.status == "retired":
                continue
            if winner == player:
                l.wins += 1
            else:
                l.losses += 1
            l.confidence = confidence(l.wins, l.losses)
            games = l.wins + l.losses
            if games >= RETIRE_GAMES and l.confidence < RETIRE_CONF:
                l.status = "retired"
            elif l.status == "candidate" and games >= PROMOTE_GAMES and l.confidence >= PROMOTE_CONF:
                l.status = "active"
            updated.append(l.id)
        return updated

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

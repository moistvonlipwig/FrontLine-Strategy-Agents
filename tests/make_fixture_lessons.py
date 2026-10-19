# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Write tests/fixtures/lessons.json: hand-written lessons to check retrieval in a real game.

    uv run python tests/make_fixture_lessons.py
    uv run python scripts/run_match.py --lessons tests/fixtures/lessons.json

Test-only. Never use this file in experiment runs (A to D).
"""

from pathlib import Path

from frontline.lessons import LessonStore
from frontline.schemas import Lesson
from test_engine import board
from test_lessons import home_threat, late_game, opening
from frontline.engine import initial_state

OUT = Path(__file__).parent / "fixtures" / "lessons.json"


def thin_line():
    s = board(initial_state("coral"), B1=("coral", 1), C1=("coral", 1), D1=("coral", 1), D2=("teal", 2))
    s.turn = 9
    return s


def support_attack():
    s = board(initial_state("coral"), B2=("coral", 3), C1=("coral", 1), C3=("coral", 2), C2=("teal", 3))
    s.turn = 13
    return s


LESSONS = [
    ("F1", "Claim toward the center early; cell count decides most games.", "opening, few cells", opening),
    ("F2", "If threat_scan shows your home at risk, reinforce home first.", "enemy cell next to your home", home_threat),
    ("F3", "In the last 2 turns, claim empty cells instead of attacking.", "turn 21 or later", late_game),
    ("F4", "Do not stretch a thin line; cut-off cells lose 1 strength per turn.", "long chain of strength-1 cells", thin_line),
    ("F5", "Attack from a cell with 2+ supporting neighbors; failed attacks cost strength.", "enemy cell surrounded by yours", support_attack),
]

if __name__ == "__main__":
    OUT.unlink(missing_ok=True)
    store = LessonStore(OUT)
    for id, text, trigger, make in LESSONS:
        store.add(Lesson(id=id, text=text, trigger=trigger, source_game="fixture", status="active"), make())
    print(store.save())

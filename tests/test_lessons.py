# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Lesson retrieval by board similarity. Lessons here are test-only, never used in runs."""

from frontline.engine import initial_state
from frontline.lessons import LessonStore, cosine, embed
from frontline.schemas import Lesson
from test_engine import board


def lesson(id, status="active"):
    return Lesson(id=id, text=f"lesson {id}", trigger="test", source_game="test", status=status)


def opening():
    return initial_state("coral")


def home_threat():
    return board(initial_state("coral"), A2=("teal", 4), B1=("coral", 1))


def late_game():
    s = board(initial_state("coral"), B1=("coral", 2), C1=("coral", 2), A2=("coral", 3),
              D5=("teal", 2), E4=("teal", 2), C5=("teal", 1))
    s.turn = 22
    return s


def test_embed_is_from_the_movers_side():
    coral = board(initial_state("coral"), B1=("coral", 2))
    teal = board(initial_state("teal"), D5=("teal", 2))  # same shape, rotated 180 degrees
    teal.board["A1"].strength, teal.board["E5"].strength = 2, 3  # match home strengths
    assert cosine(embed(coral), embed(teal)) > 0.999


def test_top3_by_board_similarity(tmp_path):
    store = LessonStore(tmp_path / "lessons.json")
    store.add(lesson("L-open"), opening())
    store.add(lesson("L-threat"), home_threat())
    store.add(lesson("L-late"), late_game())
    store.add(lesson("L-retired", status="retired"), home_threat())
    store.save()

    hits = LessonStore(tmp_path / "lessons.json").search(home_threat(), k=3)  # reload from disk
    ids = [l.id for l, _ in hits]
    assert ids[0] == "L-threat"
    assert "L-retired" not in ids
    assert len(ids) == 3
    assert hits[0][1] >= hits[1][1] >= hits[2][1]


def test_empty_store_returns_nothing(tmp_path):
    assert LessonStore(tmp_path / "missing.json").search(opening()) == []

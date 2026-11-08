# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Lesson retrieval by board similarity. Lessons here are test-only, never used in runs."""

from frontline.engine import initial_state
from frontline.lessons import CAP, LessonStore, cosine, embed
from frontline.schemas import Action, Lesson, TurnRecord
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


def cites(player, *ids):
    """One TurnRecord where `player` cited `ids`."""
    s = opening()
    act = Action(kind="claim", target="B1", reason="", cited_lessons=list(ids))
    return TurnRecord(turn=1, player=player, state_before=s, action=act, legal=True, state_after=s)


def test_cited_lessons_get_the_result(tmp_path):
    store = LessonStore()
    for i in ("L1", "L2", "L3"):
        store.add(lesson(i), opening())
    recs = [cites("coral", "L1"), cites("teal", "L2")]  # L2 cited by the other side
    assert store.record_game(recs, player="coral", winner="coral") == ["L1"]
    l1, l2, _ = store.lessons
    assert (l1.wins, l1.losses, l1.confidence) == (1, 0, 2 / 3)
    assert (l2.wins, l2.losses) == (0, 0)


def test_draw_counts_for_nothing():
    store = LessonStore()
    store.add(lesson("L1"), opening())
    assert store.record_game([cites("coral", "L1")], "coral", None) == []


def test_candidate_promoted_after_3_good_games():
    store = LessonStore()
    store.add(lesson("L1", status="candidate"), opening())
    for won in ("coral", "teal", "coral"):  # 2W-1L, confidence 0.6
        store.record_game([cites("coral", "L1")], "coral", won)
    assert store.lessons[0].status == "active"


def test_losing_lesson_retired_after_5_games():
    store = LessonStore()
    store.add(lesson("L1"), opening())
    for _ in range(5):  # 0W-5L, confidence 1/7
        store.record_game([cites("coral", "L1")], "coral", "teal")
    assert store.lessons[0].status == "retired"
    assert store.search(opening()) == []


def test_cap_retires_the_weakest():
    store = LessonStore()
    for i in range(CAP):
        store.add(lesson(f"L{i}"), opening())
    store.lessons[7].confidence = 0.1
    store.add(lesson("new", status="candidate"), opening())
    assert len(store.live()) == CAP
    assert store.lessons[7].status == "retired"
    assert store.lessons[-1].status == "candidate"

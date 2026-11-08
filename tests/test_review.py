# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""The review crew sees moves and boards, never the player's reasoning."""

import json

from frontline.bots import GreedyBot
from frontline.engine import Game
from frontline.review import strip_trace


def played_game() -> dict:
    g, bot = Game(game_id="t"), GreedyBot(seed=0)
    while not g.is_over():
        act = bot.act(g.get_state()).model_copy(
            update={"reason": "SECRET-REASON", "cited_lessons": ["SECRET-LESSON"]})
        g.apply(act, candidates=[act], candidate_scores=[{"secret": 1}], retrieved_lessons=["SECRET-SHOWN"])
    return json.loads(json.dumps(g.trace()))  # round-trip like a saved trace file


def test_strip_hides_the_players_story():
    out = json.dumps(strip_trace(played_game()))
    assert "SECRET" not in out
    for field in ("reason", "cited_lessons", "candidates", "candidate_scores", "retrieved_lessons"):
        assert f'"{field}"' not in out


def test_strip_keeps_moves_and_result():
    trace = played_game()
    out = strip_trace(trace)
    assert out["winner"] == trace["winner"]
    assert len(out["turns"]) == len(trace["turns"])
    assert out["turns"][0]["move"] and out["turns"][0]["board_after"]


class FakeCrew:
    """Stands in for the CrewAI crew: returns fixed task outputs, no LLM."""

    def __init__(self, approved=True, action="add", merge_into=None):
        from frontline.crew import Critique, Decision, TurningPoint
        self.outs = [TurningPoint(turn=5, what_happened="x", why_it_mattered="y"),
                     Critique(approved=approved, problem="", lesson_text="t", trigger="g"),
                     Decision(action=action, merge_into=merge_into, text="Hold the center.", trigger="midgame")]

    def kickoff(self, inputs):
        self.inputs = inputs
        return type("R", (), {"tasks_output": [type("O", (), {"pydantic": o}) for o in self.outs]})


def test_lesson_from_game_n_is_retrieved_in_game_n_plus_1(monkeypatch):
    import frontline.crew as crew
    from frontline.lessons import LessonStore
    fake = FakeCrew()
    monkeypatch.setattr(crew, "build_crew", lambda llm: fake)
    store, trace = LessonStore(), played_game()

    s = crew.review_game(trace, store, "coral", llm=object())
    assert s["lesson"] == "L1" and store.lessons[0].status == "candidate"
    assert "SECRET" not in fake.inputs["game"]  # the crew got the stripped trace
    next_game = Game(game_id="n+1").get_state()
    assert [l.id for l, _ in store.search(next_game)] == ["L1"]


def test_rejected_or_merged_adds_nothing(monkeypatch):
    import frontline.crew as crew
    from frontline.lessons import LessonStore
    store = LessonStore()
    monkeypatch.setattr(crew, "build_crew", lambda llm: FakeCrew(approved=False))
    assert crew.review_game(played_game(), store, "coral", llm=object())["lesson"] is None

    store.lessons.append(crew.Lesson(id="L1", text="old", trigger="old", source_game="g", vector=[1.0] * 26))
    monkeypatch.setattr(crew, "build_crew", lambda llm: FakeCrew(action="merge", merge_into="L1"))
    assert crew.review_game(played_game(), store, "coral", llm=object())["lesson"] == "L1"
    assert len(store.lessons) == 1 and store.lessons[0].text == "Hold the center."

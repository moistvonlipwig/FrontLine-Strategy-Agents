# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""One test per rule in docs/rules.md."""

import json

from frontline.engine import Game, initial_state, is_over, legal_moves, outcome, step
from frontline.schemas import Action, Cell


def board(state, **cells):
    """board(s, C3=("coral", 4), D3=("teal", 3)) sets cells in place."""
    for k, (owner, s) in cells.items():
        state.board[k] = Cell(owner=owner, strength=s)
    return state


def test_setup():
    s = initial_state("teal")
    assert s.board["A1"] == Cell(owner="coral", strength=2)
    assert s.board["E5"] == Cell(owner="teal", strength=3)  # first mover gets home strength 3
    assert s.to_move == "teal" and s.turn == 1
    assert sum(c.owner is not None for c in s.board.values()) == 2


def test_claim_adjacent_only():
    s = initial_state()
    s2, err = step(s, Action(kind="claim", target="B1"))
    assert err is None and s2.board["B1"] == Cell(owner="coral", strength=1)
    _, err = step(s, Action(kind="claim", target="B2"))  # diagonal
    assert "not adjacent" in err


def test_reinforce_cap():
    s = board(initial_state(), A1=("coral", 5))
    _, err = step(s, Action(kind="reinforce", target="A1"))
    assert "max strength" in err


def test_attack_capture_with_support():
    # rules.md worked example: C3=4 attacks D3=3, C2 does NOT touch D3 so power = 4
    s = board(initial_state(), A2=("coral", 1), A3=("coral", 1), B3=("coral", 1), C3=("coral", 4),
              D3=("teal", 3), D4=("teal", 1), D5=("teal", 1))
    s2, err = step(s, Action(kind="attack", source="C3", target="D3"))
    assert err is None
    assert s2.board["D3"].owner == "coral"
    assert s2.board["C3"].strength == 1  # attacker drops to 1
    # captured = 4 - 3 = 1, then D3 is supplied through C3-B3-A3-A2-A1
    assert s2.board["D3"].strength == 1


def test_attack_support_counts_other_cells():
    s = board(initial_state(), B1=("coral", 2), C2=("teal", 2), C1=("coral", 1), B2=("coral", 1))
    # B2 attacks C2: power = 1 + C1 touches C2 (+1) = 2, not > 2, fails
    s2, _ = step(s, Action(kind="attack", source="B2", target="C2"))
    assert s2.board["C2"].owner == "teal"
    assert s2.board["B2"].owner is None  # 1 - 1 = 0 -> empty
    # B2 at strength 2: power = 2 + 1 = 3 > 2, captures
    s = board(s, B2=("coral", 2))
    s.to_move = "coral"
    s3, _ = step(s, Action(kind="attack", source="B2", target="C2"))
    assert s3.board["C2"].owner == "coral"


def test_tie_favors_defender():
    s = board(initial_state(), B1=("coral", 3), C1=("teal", 3))
    s2, _ = step(s, Action(kind="attack", source="B1", target="C1"))
    assert s2.board["C1"].owner == "teal"
    assert s2.board["B1"].strength == 2


def test_supply_cut_loses_strength():
    s = board(initial_state(), C3=("coral", 3))  # not connected to A1
    s2, _ = step(s, Action(kind="reinforce", target="A1"))
    assert s2.board["C3"].strength == 2


def test_home_floor_is_one():
    s = board(initial_state(), A1=("coral", 1), A2=("teal", 5))
    s.to_move = "coral"
    s2, _ = step(s, Action(kind="attack", source="A1", target="A2"))  # fails, A1 would drop to 0
    assert s2.board["A1"] == Cell(owner="coral", strength=1)


def test_capture_home_wins():
    s = board(initial_state(), D5=("coral", 4), E5=("teal", 2))
    s2, err = step(s, Action(kind="attack", source="D5", target="E5"))
    assert err is None and is_over(s2)
    assert outcome(s2) == ("coral", "home captured")


def test_illegal_forfeits_but_turn_advances_and_supply_runs():
    s = board(initial_state(), C3=("coral", 2))
    s2, err = step(s, Action(kind="claim", target="E1"))
    assert err is not None
    assert s2.turn == 2 and s2.to_move == "teal"
    assert s2.board["C3"].strength == 1  # supply still applied


def test_game_end_after_24_turns_and_tiebreaks():
    s = board(initial_state(), A1=("coral", 2))  # equal homes
    s.turn = 25
    assert is_over(s) and legal_moves(s) == []
    assert outcome(s) == (None, "draw")
    s = board(s, A1=("coral", 3))
    assert outcome(s) == ("coral", "strength 3-2")


def test_legal_moves_are_all_legal():
    from frontline.bots import RandomBot
    g, bot = Game(), RandomBot(seed=1)
    while not g.is_over():
        for a in g.legal_moves():
            assert step(g.state, a)[1] is None
        g.apply(bot.act(g.get_state()))


def test_trace_roundtrip(tmp_path):
    g = Game(game_id="t1")
    g.apply(Action(kind="claim", target="B1", reason="test"))
    data = json.loads(g.save_trace(tmp_path / "t1.json").read_text())
    assert data["turns"][0]["action"]["target"] == "B1"

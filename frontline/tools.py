# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Player Agent's read-only tools. The tools do the math so the LLM never has to.

Every tool takes a GameState and returns plain dicts (easy to put in a prompt or a trace).
None of them change the state: previews run on a copy via engine.step.
"""

from pydantic import ValidationError

from . import engine
from .schemas import Action, GameState


def list_legal_moves(state: GameState) -> list[str]:
    """Every legal move for the player to move, as short labels like 'attack C2->D3'."""
    return [a.key() for a in engine.legal_moves(state)]


def preview_attack(state: GameState, source: str, target: str) -> dict:
    """What happens if `source` attacks `target`: power vs defense and the resulting cells."""
    try:
        action = Action(kind="attack", source=source, target=target)
    except ValidationError:
        return {"legal": False, "reason": f"bad cell names {source!r}, {target!r}; use e.g. 'B3'"}
    reason = engine.check_action(state, action)
    if reason:
        return {"legal": False, "reason": reason}
    power = engine.attack_power(state, source, target)
    defense = state.board[target].strength
    after, _ = engine.step(state, action)  # step copies, so `state` is untouched
    return {
        "legal": True,
        "power": power,
        "defense": defense,
        "wins": power > defense,  # ties favor the defender
        "source_after": after.board[source].model_dump(),
        "target_after": after.board[target].model_dump(),
    }


def supply_check(state: GameState) -> dict:
    """For the player to move: which of their cells are cut off from home (lose 1 per turn)."""
    p = state.to_move
    supplied = engine.supplied_cells(state, p)
    mine = engine.cells_of(state, p)
    return {"supplied": sorted(supplied), "cut_off": sorted(c for c in mine if c not in supplied)}


def threat_scan(state: GameState) -> list[dict]:
    """Enemy attacks that would capture one of our cells next turn, home first."""
    me = state.to_move
    them = engine.other(me)
    # Pretend it is the enemy's turn so attack_power and check_action see their side.
    flipped = engine.clone(state)
    flipped.to_move = them
    threats = []
    for cell in engine.cells_of(state, me):
        for src in engine.NEIGHBORS[cell]:
            if state.board[src].owner != them:
                continue
            power = engine.attack_power(flipped, src, cell)
            if power > state.board[cell].strength:
                threats.append({"target": cell, "source": src, "power": power,
                                "defense": state.board[cell].strength,
                                "is_home": cell == state.homes[me]})
    return sorted(threats, key=lambda t: (not t["is_home"], -t["power"]))


TOOLS = {
    "list_legal_moves": list_legal_moves,
    "preview_attack": preview_attack,
    "supply_check": supply_check,
    "threat_scan": threat_scan,
}

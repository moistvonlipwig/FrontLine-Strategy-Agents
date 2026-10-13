# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""LangGraph match loop: one pass through the graph = one turn.

    observe -> retrieve -> decide -> validate -> apply -> (game over? END : observe)

Each node is a plain function: it reads the shared MatchState and returns a dict of
the keys it changed. LangGraph merges that dict into the state and follows the edges.
Only `decide` calls an LLM (and only when the player to move is a PlayerAgent).

Tracing: observe opens a "turn" span, apply closes it, and the nodes in between each
run in a child span (see `traced`). Spans are saved as JSON at the end of the game.
"""

import json
from pathlib import Path
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from opentelemetry import trace
from opentelemetry.trace import Span

from . import engine
from .engine import Game
from .schemas import Action, GameState
from .tracing import save_spans, tracer


class MatchState(TypedDict):
    game: Game  # holds the real board and the trace
    players: dict[str, Any]  # {"coral": agent, "teal": agent}; anything with .act(state)
    observation: GameState | None
    lessons: list[str]
    action: Action | None
    illegal_reason: str | None
    game_span: Span  # root span, parent of every turn
    turn_span: Span | None  # parent of this turn's node spans


def traced(fn):
    """Run a node inside a child span of the current turn; the node gets the span to tag."""
    def node(s: MatchState) -> dict:
        ctx = trace.set_span_in_context(s["turn_span"])
        with tracer.start_as_current_span(fn.__name__, context=ctx) as span:
            return fn(s, span)
    node.__name__ = fn.__name__
    return node


def observe(s: MatchState) -> dict:
    obs = s["game"].get_state()  # a copy, so agents can't touch the real board
    turn_span = tracer.start_span("turn", context=trace.set_span_in_context(s["game_span"]))
    turn_span.set_attributes({"turn": obs.turn, "player": obs.to_move})
    return {"observation": obs, "turn_span": turn_span}


@traced
def retrieve(s: MatchState, span: Span) -> dict:
    span.set_attribute("lessons.count", 0)
    return {"lessons": []}  # Day 3: vector-store lesson search goes here


@traced
def decide(s: MatchState, span: Span) -> dict:
    obs = s["observation"]
    player = s["players"][obs.to_move]
    action = player.act(obs)
    span.set_attributes({"agent": type(player).__name__, "action": action.key(), "reason": action.reason})
    for call in getattr(player, "last_tool_calls", []):  # bots have none
        span.add_event("tool_call", {"name": call["name"], "args": json.dumps(call["args"]),
                                     "result": json.dumps(call["result"])})
    return {"action": action}


@traced
def validate(s: MatchState, span: Span) -> dict:
    # Recorded, not enforced: an illegal move still goes to apply, which forfeits the turn
    # (supply still runs, per the rules). Stage 6 counts these.
    reason = engine.check_action(s["observation"], s["action"])
    span.set_attributes({"legal": reason is None, "illegal_reason": reason or ""})
    return {"illegal_reason": reason}


@traced
def apply(s: MatchState, span: Span) -> dict:
    s["game"].apply(s["action"])  # mutates the Game in place; nothing to merge
    s["turn_span"].set_attributes({"action": s["action"].key(), "legal": s["illegal_reason"] is None})
    return {}


def check_end(s: MatchState) -> str:
    """Conditional edge: returns the name of the next node. Also closes the turn span."""
    s["turn_span"].end()
    return END if s["game"].is_over() else "observe"


def build_graph():
    g = StateGraph(MatchState)
    for fn in (observe, retrieve, decide, validate, apply):
        g.add_node(fn.__name__, fn)
    g.add_edge(START, "observe")
    g.add_edge("observe", "retrieve")
    g.add_edge("retrieve", "decide")
    g.add_edge("decide", "validate")
    g.add_edge("validate", "apply")
    g.add_conditional_edges("apply", check_end, ["observe", END])
    return g.compile()


GRAPH = build_graph()


def play_match(game: Game, players: dict[str, Any], spans_path: str | Path | None = None,
               on_turn=None) -> Game:
    """Run one full game. 24 turns x 5 nodes = 120 steps, so raise LangGraph's default limit of 25.

    on_turn(game) is called after each apply, e.g. to print the board.
    """
    with tracer.start_as_current_span("game") as game_span:
        game_span.set_attributes({"game_id": game.game_id, "first": game.first,
                                  **{f"player.{c}": type(p).__name__ for c, p in players.items()}})
        # stream() is invoke() that yields after every node: {"node_name": update_dict}
        for step in GRAPH.stream(
            {"game": game, "players": players, "observation": None, "lessons": [], "action": None,
             "illegal_reason": None, "game_span": game_span, "turn_span": None},
            config={"recursion_limit": 200},
            stream_mode="updates",
        ):
            if on_turn and "apply" in step:
                on_turn(game)
        winner, how = game.outcome()
        game_span.set_attributes({"winner": winner or "draw", "end": how})
    if spans_path:
        save_spans(spans_path)
    return game

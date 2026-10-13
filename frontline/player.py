# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Player Agent: a local LLM (Ollama) picks one move per turn.

Hybrid tool use:
  - Legal moves are always in the prompt (small, needed every turn).
  - preview_attack, supply_check, threat_scan are exposed as tools; the LLM decides when to call them.
Then a final call returns an `Action`, validated by Pydantic.
"""

from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from pydantic import Field

from . import tools
from .render import render
from .schemas import CELL_PATTERN, Action, GameState

RULES = (Path(__file__).parent.parent / "docs" / "rules.md").read_text()

SYSTEM = f"""You are playing FrontLine, a 5x5 territory game. Rules:

{RULES}

Each turn: look at the board, call tools if they help, then choose exactly one move
from the legal moves list. Tools do the math; do not calculate attack power yourself."""


class LLMAction(Action):
    """Same as Action, but `reason` and `source` are required: constrained JSON skips optional fields."""
    reason: str = Field(description="One sentence: why this move.")
    source: str | None = Field(pattern=CELL_PATTERN, description='Attack: your attacking cell, e.g. "C2". Claim/reinforce: null.')


def make_tools(state: GameState) -> list:
    """Wrap the read-only tools for the LLM. The closure binds `state`, so the LLM only
    passes cell names. @tool turns the signature + docstring into the schema the LLM sees."""

    @tool
    def preview_attack(source: str, target: str) -> dict:
        """Preview attacking enemy cell `target` from your cell `source` (e.g. "B3", "B4").
        Returns attack power, defense, whether it wins, and both cells afterwards."""
        return tools.preview_attack(state, source, target)

    @tool
    def supply_check() -> dict:
        """List your cells connected to home ('supplied') and cut off ('cut_off').
        Cut-off cells lose 1 strength after every turn."""
        return tools.supply_check(state)

    @tool
    def threat_scan() -> list[dict]:
        """Enemy attacks that would capture one of your cells on their next turn, home first."""
        return tools.threat_scan(state)

    return [preview_attack, supply_check, threat_scan]


class PlayerAgent:
    name = "llm"

    def __init__(self, model: str = "qwen3:32b", max_tool_rounds: int = 4):
        # reasoning=False turns off qwen3's <think> output: faster, cleaner JSON.
        self.llm = ChatOllama(model=model, temperature=0, reasoning=False)
        self.max_tool_rounds = max_tool_rounds
        self.last_tool_calls: list[dict] = []  # for tracing (Stage 4)

    def act(self, state: GameState) -> Action:
        lc_tools = make_tools(state)
        by_name = {t.name: t for t in lc_tools}
        llm_with_tools = self.llm.bind_tools(lc_tools)

        messages = [
            SystemMessage(SYSTEM),
            HumanMessage(
                f"You are {state.to_move}. Turn {state.turn} of 24.\n\n"
                f"{render(state, color=False)}\n\n"
                f"Legal moves: {tools.list_legal_moves(state)}"
            ),
        ]
        self.last_tool_calls = []

        # Tool loop: the LLM asks for tools until it has what it needs (or we hit the cap).
        for _ in range(self.max_tool_rounds):
            reply = llm_with_tools.invoke(messages)
            messages.append(reply)
            if not reply.tool_calls:
                break
            for call in reply.tool_calls:
                result = by_name[call["name"]].invoke(call["args"]) if call["name"] in by_name \
                    else {"error": f"unknown tool {call['name']}"}
                self.last_tool_calls.append({"name": call["name"], "args": call["args"], "result": result})
                messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))

        # Final answer as a Pydantic Action (Ollama constrains output to the JSON schema).
        messages.append(HumanMessage("Now give your move. Pick one move from the legal moves list."))
        try:
            out = self.llm.with_structured_output(LLMAction, method="json_schema").invoke(messages)
            return Action(**out.model_dump())
        except Exception as e:  # bad JSON counts as an illegal move, not a crash
            # model_construct skips validation so "??" survives; the engine then rejects it as illegal.
            return Action.model_construct(kind="claim", target="??", source=None, reason=f"parse error: {e}", cited_lessons=[])

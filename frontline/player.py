# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Player Agent: a local LLM (Ollama) picks one move per turn.

Hybrid tool use:
  - Legal moves are always in the prompt (small, needed every turn).
  - preview_attack, supply_check, threat_scan are exposed as tools; the LLM decides when to call them.
Then tree-of-thought (tot=True):
  1. propose: the LLM returns 3 different candidate moves
  2. score:   the engine scores each 2-ply (our move + greedy's best reply), no LLM
  3. pick:    the LLM sees the scores and picks one
With tot=False a single call returns the move (ablation, condition D).
"""

from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from . import tools
from .render import render
from .schemas import CELL_PATTERN, Action, GameState, Lesson

RULES = (Path(__file__).parent.parent / "docs" / "rules.md").read_text()

SYSTEM = f"""You are playing FrontLine, a 5x5 territory game. Rules:

{RULES}

Each turn: look at the board, call tools if they help, then choose exactly one move
from the legal moves list. Tools do the math; do not calculate attack power yourself."""


class LLMAction(Action):
    """Same as Action, but `reason` and `source` are required: constrained JSON skips optional fields."""
    reason: str = Field(description="One sentence: why this move.")
    cited_lessons: list[str] = Field(description="Ids of the lessons this move follows, e.g. [\"L3\"]. [] if none.")
    source: str | None = Field(pattern=CELL_PATTERN, description='Attack: your attacking cell, e.g. "C2". Claim/reinforce: null.')


class Candidates(BaseModel):
    candidates: list[LLMAction] = Field(min_length=3, max_length=3,
                                        description="3 different moves from the legal moves list.")


class Pick(BaseModel):
    choice: int = Field(ge=0, le=2, description="Index of the chosen candidate: 0, 1, or 2.")
    reason: str = Field(description="One sentence: why this candidate.")


def lessons_block(lessons: list[Lesson]) -> str:
    """Lessons from past games for the prompt; empty string when there are none."""
    if not lessons:
        return ""
    lines = [f"- [{l.id}] {l.text} (when: {l.trigger}; record {l.wins}W-{l.losses}L)" for l in lessons]
    return ("\n\nLessons from past games on similar boards. Use them if they fit, "
            "and list the ids you follow in cited_lessons:\n" + "\n".join(lines))


def to_action(a: LLMAction) -> Action:
    """LLMAction -> Action. The LLM often fills `source` on claims; only attacks have one."""
    d = a.model_dump()
    if d["kind"] != "attack":
        d["source"] = None
    return Action(**d)


def parse_error(e: Exception) -> Action:
    # model_construct skips validation so "??" survives; the engine then rejects it as illegal.
    return Action.model_construct(kind="claim", target="??", source=None, reason=f"parse error: {e}", cited_lessons=[])


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

    def __init__(self, model: str = "qwen3:32b", max_tool_rounds: int = 4, tot: bool = True):
        # reasoning=False turns off qwen3's <think> output: faster, cleaner JSON.
        self.llm = ChatOllama(model=model, temperature=0, reasoning=False)
        self.max_tool_rounds = max_tool_rounds
        self.tot = tot
        self.last_tool_calls: list[dict] = []  # for tracing (Stage 4)
        self.last_candidates: list[Action] = []  # tree-of-thought options, saved in the TurnRecord
        self.last_scores: list[dict] = []  # tools.score_2ply result per candidate

    def act(self, state: GameState, lessons: list[Lesson] | None = None) -> Action:
        lc_tools = make_tools(state)
        by_name = {t.name: t for t in lc_tools}
        llm_with_tools = self.llm.bind_tools(lc_tools)

        messages = [
            SystemMessage(SYSTEM),
            HumanMessage(
                f"You are {state.to_move}. Turn {state.turn} of 24.\n\n"
                f"{render(state, color=False)}\n\n"
                f"Legal moves: {tools.list_legal_moves(state)}"
                + lessons_block(lessons or [])
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

        self.last_candidates, self.last_scores = [], []
        if not self.tot:
            return self._single(messages)
        return self._tree_of_thought(state, messages)

    def _single(self, messages: list) -> Action:
        # Final answer as a Pydantic Action (Ollama constrains output to the JSON schema).
        messages.append(HumanMessage("Now give your move. Pick one move from the legal moves list."))
        try:
            out = self.llm.with_structured_output(LLMAction, method="json_schema").invoke(messages)
            return to_action(out)
        except Exception as e:  # bad JSON counts as an illegal move, not a crash
            return parse_error(e)

    def _tree_of_thought(self, state: GameState, messages: list) -> Action:
        # 1. propose
        messages.append(HumanMessage("Propose 3 different candidate moves from the legal moves list. "
                                     "Make them genuinely different plans (e.g. expand, defend, attack)."))
        try:
            out = self.llm.with_structured_output(Candidates, method="json_schema").invoke(messages)
            cands = [to_action(c) for c in out.candidates]
        except Exception as e:
            return parse_error(e)

        # 2. score: the engine does the lookahead, not the LLM
        scores = [tools.score_2ply(state, c) for c in cands]
        self.last_candidates, self.last_scores = cands, scores
        table = "\n".join(
            f"{i}. {c.key()}: " + (f"score now {s['score_1ply']:+.0f}, after enemy reply "
                                   f"{s['best_reply']} {s['score_2ply']:+.0f}" if s["legal"] else f"ILLEGAL ({s['reason']})")
            + f"  ({c.reason})"
            for i, (c, s) in enumerate(zip(cands, scores)))

        # 3. pick
        messages.append(HumanMessage(
            f"Candidates scored by the engine (score = 10 x cell lead + strength lead, for you; "
            f"2-ply = after the enemy's best reply):\n{table}\n\nPick the best candidate."))
        try:
            pick = self.llm.with_structured_output(Pick, method="json_schema").invoke(messages)
            choice, reason = pick.choice, pick.reason
        except Exception as e:  # fall back to the best 2-ply score rather than forfeit
            choice = max(range(3), key=lambda i: scores[i].get("score_2ply", -10**6))
            reason = f"pick parse error, took best 2-ply: {e}"
        return cands[choice].model_copy(update={"reason": reason})

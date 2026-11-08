# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Review crew: turns one finished game into at most one new lesson.

    analyst  -> finds the turning point for the reviewed player
    critic   -> checks that claim against the boards, then drafts a lesson (or rejects)
    curator  -> compares the draft with the store: add, merge, or skip

The crew only sees review.strip_trace (moves and boards, no player reasoning).
The LLM decides; Python applies the decision and keeps the tally (lessons.LessonStore).
"""

import json
from typing import Literal

from crewai import LLM, Agent, Crew, Process, Task
from pydantic import BaseModel, Field

from .lessons import LessonStore
from .review import strip_trace
from .schemas import Lesson, Player, TurnRecord

RULES = ("FrontLine rules in short: 5x5 board, coral home A1, teal home E5. 24 turns. A move is claim "
         "(empty cell next to yours), reinforce (+1 strength, max 5) or attack (from your cell into an "
         "adjacent enemy cell). Cells cut off from home lose 1 strength per turn. Capture the enemy home "
         "to win at once, otherwise most cells wins, then most strength.")


class TurningPoint(BaseModel):
    turn: int = Field(description="Turn number where the game swung for or against the reviewed player")
    what_happened: str = Field(description="The move(s) and the board change, in one or two sentences")
    why_it_mattered: str = Field(description="Why this decided the result")


class Critique(BaseModel):
    approved: bool = Field(description="True only if the boards in the trace back up the analyst's claim")
    problem: str = Field(description="What is wrong with the claim; empty if approved")
    lesson_text: str = Field(description="One short rule the player can follow next game; empty if rejected")
    trigger: str = Field(description="The board situation where the rule applies; empty if rejected")


class Decision(BaseModel):
    action: Literal["add", "merge", "skip"] = Field(
        description="add = new lesson; merge = same idea as an existing lesson; skip = rejected or too vague")
    merge_into: str | None = Field(default=None, description="Existing lesson id when action is merge")
    text: str = Field(description="Final lesson text (for add or merge); empty for skip")
    trigger: str = Field(description="Final trigger (for add or merge); empty for skip")


def make_llm(model: str = "qwen3:32b") -> LLM:
    return LLM(model=f"ollama/{model}", base_url="http://localhost:11434", temperature=0)


def build_crew(llm: LLM) -> Crew:
    analyst = Agent(
        role="Game analyst",
        goal="Find the one turn that decided the game for {player}",
        backstory="You study FrontLine game records. You only trust what the boards show. " + RULES,
        llm=llm, allow_delegation=False, verbose=False)
    critic = Agent(
        role="Critic",
        goal="Reject any claim the boards do not support, and turn good claims into a rule",
        backstory="You are skeptical. You re-read the boards before and after the turn yourself. " + RULES,
        llm=llm, allow_delegation=False, verbose=False)
    curator = Agent(
        role="Lesson curator",
        goal="Keep the lesson store small, specific and free of duplicates",
        backstory="You own a store of at most 30 lessons. You prefer one sharp lesson over two vague ones.",
        llm=llm, allow_delegation=False, verbose=False)

    find = Task(
        description=("Game record (you are reviewing {player}; winner: {winner}, {end}):\n{game}\n\n"
                     "Find the turning point for {player}: the turn where the game swung."),
        expected_output="The turn number, what happened, and why it mattered.",
        agent=analyst, output_pydantic=TurningPoint)
    check = Task(
        description=("Game record:\n{game}\n\nCheck the analyst's turning point against the boards. "
                     "If it holds, write one short rule {player} can follow next game, and when it applies. "
                     "The rule must be about board situations, not about this exact game."),
        expected_output="approved, problem, lesson_text, trigger.",
        agent=critic, context=[find], output_pydantic=Critique)
    curate = Task(
        description=("Current lessons (id, text, trigger, record):\n{lessons}\n\n"
                     "If the critic rejected the claim, skip. If the draft says the same thing as an "
                     "existing lesson, merge into that id. Otherwise add it."),
        expected_output="action, merge_into, text, trigger.",
        agent=curator, context=[check], output_pydantic=Decision)

    return Crew(agents=[analyst, critic, curator], tasks=[find, check, curate],
                process=Process.sequential, verbose=False)


def lessons_table(store: LessonStore) -> str:
    rows = [f"- [{l.id}] {l.text} (when: {l.trigger}; {l.wins}W-{l.losses}L)" for l in store.live()]
    return "\n".join(rows) or "(none yet)"


def board_at(trace: dict, player: Player, turn: int):
    """Board before `player`'s move at or just before `turn`: the vector the lesson is filed under."""
    mine = [TurnRecord.model_validate(t) for t in trace["turns"] if t["player"] == player]
    best = [r for r in mine if r.turn <= turn] or mine
    return best[-1].state_before


def review_game(trace: dict, store: LessonStore, player: Player, llm: LLM | None = None) -> dict:
    """Score the lessons `player` cited, then run the crew and apply its decision.
    Returns a summary dict for logging. Does not save the store."""
    updated = store.record_game([TurnRecord.model_validate(t) for t in trace["turns"]], player, trace["winner"])

    stripped = strip_trace(trace)
    game = json.dumps(stripped["turns"], indent=0)
    result = build_crew(llm or make_llm()).kickoff(inputs={
        "player": player, "winner": stripped["winner"] or "draw", "end": stripped["end"],
        "game": game, "lessons": lessons_table(store)})
    tp, crit, dec = (t.pydantic for t in result.tasks_output)

    summary = {"game_id": trace["game_id"], "scored": updated, "turning_point": tp.model_dump(),
               "critic": crit.model_dump(), "decision": dec.model_dump(), "lesson": None}
    if not crit.approved or dec.action == "skip" or not dec.text:
        return summary
    target = next((l for l in store.live() if l.id == dec.merge_into), None)
    if dec.action == "merge" and target:
        target.text, target.trigger = dec.text, dec.trigger  # same idea, sharper wording; tally kept
        summary["lesson"] = target.id
        return summary
    lesson = Lesson(id=f"L{len(store.lessons) + 1}", text=dec.text, trigger=dec.trigger,
                    source_game=trace["game_id"])
    store.add(lesson, board_at(trace, player, tp.turn))
    summary["lesson"] = lesson.id
    return summary

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

FrontLine: a 5x5 territory game where LLM agents play, review their own games, and keep lessons that win (CMU Agentic AI capstone).

## Tracking

- Daily checklist: `docs/daily-checklist.md`. Tick items as they're done.
- Plan: `docs/capstone-plan.md` · Design: `docs/architecture.md` · Rules: `docs/rules.md`
- Learning log: `docs/learning-log.md`

## Commands

```bash
uv sync                                              # install
uv run pytest                                        # all tests
uv run pytest tests/test_engine.py::test_setup       # one test
uv run python scripts/run_bots.py --games 1000 --a greedy --b greedy   # bot win rates
uv run python scripts/run_match.py                   # LLM (coral) vs greedy, needs Ollama
uv run python scripts/run_match.py --coral greedy --teal random        # fast, no LLM
uv run python scripts/run_match.py --games 10 --quiet                  # illegal-move rate
uv run python scripts/run_match.py --no-tot                            # 1 candidate (condition D)
uv run python scripts/run_match.py --lessons tests/fixtures/lessons.json   # retrieval check
```

Default model: `qwen3:32b` via Ollama (`--model` to change).

## Architecture

**Rule:** the engine is deterministic and has no LLM. Everything with an LLM wraps around it.

- `engine.py`: pure functions (`step`, `legal_moves`, `check_action`, `attack_power`, `supplied_cells`) plus a `Game` wrapper in OpenSpiel style (`get_state`, `apply`, `is_over`, `outcome`, `save_trace`). `step` copies the state, and `clone` uses `model_construct` for speed.
- `schemas.py`: the data contracts (`GameState`, `Action`, `TurnRecord`, `Lesson`). Keep them stable, because swapping the model or the UI depends on them. `Action` field descriptions feed the LLM's JSON schema.
- `match.py`: LangGraph loop, one pass per turn:
  `observe → retrieve → decide → validate → apply → (END | observe)`
  - Only `decide` calls an LLM. Players are anything with `.act(GameState) -> Action`.
  - `validate` records illegal moves but doesn't block them. `apply` forfeits the turn, and supply still runs.
  - `retrieve` gets the top 3 lessons from `LessonStore` (none if `store=None`, which is condition A).
  - `recursion_limit=200`, since 24 turns × 5 nodes is more than the default of 25.
- `player.py`: `PlayerAgent` (ChatOllama, `reasoning=False`). Legal moves and retrieved lessons go in the prompt, and the other tools are callable (max 4 rounds). Then tree-of-thought: the LLM proposes 3 moves, the engine scores each with `tools.score_2ply` (the move plus greedy's best reply), and the LLM picks one. `tot=False` uses a single call instead. A parse error becomes an illegal `"??"` move, not a crash.
- `lessons.py`: a JSON lesson store with a small vector search. `embed(state)` is the 25 cells, signed by owner from the mover's side (teal rotated 180°), plus turn/24. Search is cosine top-k and skips retired lessons.
- `tools.py`: read-only tools (`preview_attack`, `supply_check`, `threat_scan`) that return plain dicts. The tools do the math so the LLM doesn't have to.
- `tracing.py`: an in-memory OTel exporter. Span tree: `game → turn ×24 → retrieve/decide/validate/apply`, with tool calls as events on `decide`. `save_spans` writes JSON and clears.
- `bots.py`: `RandomBot` and `GreedyBot` baselines.

**Outputs:** `traces/<game_id>.json` (turn records) and `traces/<game_id>.spans.json` (OTel).

**Planned:** a CrewAI review crew (analyst/critic/curator) that writes lessons, with a cap of 30, confidence, and a retire rule.
**Key constraint:** the review crew sees a stripped `TurnRecord`, with no `reason`, `cited_lessons`, or `candidates`.

## Tests

`tests/test_engine.py` has one test per rule in `docs/rules.md`. Use the `board(state, C3=("coral", 4))` helper to set up positions.
`tests/fixtures/lessons.json` (built by `tests/make_fixture_lessons.py`) is test-only. Never use it in experiment runs.

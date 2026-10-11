# FrontLine Future Enhancements

Oct 11, 2026 · @Chris

Enhancements that stay out of the capstone so it ships by the week of Nov 9. Add new ideas as rows, and ask me to add any that come up in chat.

## Backlog

| # | Enhancement | Phase | Priority | Status |
| --- | --- | --- | --- | --- |
| 1 | Human play in Streamlit against the frozen agent | After Nov 9 | High | Planned |
| 2 | Candidate lesson file and promotion gate for human games | After Nov 9 | High | Planned |
| 3 | FastAPI layer around the match loop, with a LangGraph interrupt for the human turn | After Nov 9 | High | Planned |
| 4 | SQLite for game sessions and lessons, so several people can play at once | After Nov 9 | Medium | Idea |
| 5 | Second domain adapter (Connect Four) to prove the core is domain-agnostic | After Nov 9 | Medium | Idea |
| 6 | Temporal policy checks, Dogwood-style, written in Python and replayed on saved traces | After Nov 9 | Medium | Idea |
| 7 | Node/React front end with a websocket that streams the agent's thinking | Later | Medium | Idea |
| 8 | Hosted model for public play, so the home machine is not exposed | Later | Medium | Idea |
| 9 | OpenSpiel MCTS bot as a strong opponent to learn against | Later | Medium | Idea |
| 10 | Lesson report for game designers, to support rule balancing | Later | Medium | Idea |
| 11 | Oly-Spark item-bank auditor reusing the review crew and lesson store | Later | Medium | Idea |
| 12 | Workshop or course: build a self-improving game agent, with FrontLine as the example | Later | Medium | Idea |
| 13 | Evaluate Strands (Python or TypeScript) for the agent core, its evals SDK, and its Box sandbox with Dogwood policy | Later | Low | Idea |
| 14 | MCP server that exposes the game tools to other agents | Later | Low | Idea |

## Notes

Most items depend on two things built this week: the Pydantic schemas and the engine's plain functions (`get_state`, `legal_moves`, `apply`). Keep those stable and each item below plugs in without touching the agents.

- **Human play (1, 2):** a human is just another player. Lessons from human games go to the candidate file and are promoted only if a self-play batch against greedy does not lose win rate. This is the memory-poisoning defense.
- **FastAPI and SQLite (3, 4):** about 100 lines of Python. Endpoints: start game, get state, post move, a websocket for agent events, and get trace. Needed before any non-Streamlit UI.
- **Domain adapter (5):** move all FrontLine code into `domains/frontline.py` behind one interface (initial state, legal actions, apply, terminal, outcome, describe, tools, situation key, baselines). Generalize further only after a second domain runs unchanged.
- **Temporal policies (6):** examples are "promote a lesson only after the critic approved it" and "at most N tool calls per turn." Test them by replaying saved traces.
- **Node front end and hosted model (7, 8):** depends on 3. Stream the 3 candidates and cited lessons live. That is the teaching hook. Use a hosted model for anything public.
- **Strands (13):** a possible path, not a commitment. Try it first on a small spike, such as the Connect Four adapter from item 5, before porting FrontLine. Worth testing: graph and swarm patterns for the match loop and review crew, human-in-the-loop interrupts and streaming for the Node UI, the evals SDK for agent scoring, and Box for running agents under Dogwood policy. Apache 2.0, free for commercial use. The TypeScript SDK is younger than the Python one. Set the model explicitly to avoid default Bedrock charges. Port the engine with its unit tests so the rules provably do not change.
- **Income items (10, 11, 12):** the designer report and the workshop reuse FrontLine directly. The Oly-Spark auditor reuses the review crew, lesson store, and promotion gate.

## Decisions

| Date | Decision | Why |
| --- | --- | --- |
| Oct 11 | Capstone UI is a Streamlit replay viewer, not Node | Pure Python, about one evening, no API layer needed before the trip |
| Oct 11 | Stay on Python with LangGraph and CrewAI, not Strands TypeScript | Matches Modules 4 and 5 and the submission; no time to learn a new framework before Oct 16 |
| Oct 11 | Keep a domain seam, but do not build the generic abstraction yet | Costs nothing now; generalize only after a second domain works |
| Oct 11 | Human play moves to after the presentation | Self-play results are the required deliverable; human play is the stretch goal |
| Earlier | Write the engine ourselves instead of using OpenSpiel or TextArena | Full control of rules; OpenSpiel-style method names keep a later port open |

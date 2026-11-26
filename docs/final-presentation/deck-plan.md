# Final presentation plan

Recorded video, 8 to 10 minutes, technical audience. Built as a .pptx by `build_deck.py`, with the script in each slide's speaker notes. Follows the 7.1 presentation outline. Results come from `runs/seed1/summary.md`.

| # | Outline section | Slide | Time |
|---|---|---|---|
| 1 | Opening | Title, problem, user, goal | 0:45 |
| 2 | Why it matters | Playtesting is slow, why a plain LLM can't do it, why agents fit | 0:30 |
| 3 | Architecture | Loop diagram: engine, match loop, player, lessons, crew | 1:15 |
| 4 | The game | Rules in two lines, turn 11 of `s1-B-g016`: boards, candidate scores, cited lesson | 0:45 |
| 5 | Key decisions | "The LLM judges, code calculates": illegal moves 12.5% to 1-3%, ToT with engine scoring | 1:00 |
| 6 | Key decisions | Keeping lessons honest: stripped trace, critic, tally, retire | 0:45 |
| 7 | Key decisions | Why lessons, not RL? | 0:45 |
| 8 | Evaluation | A-D design and metrics | 0:45 |
| 9 | Results | A-D table plus one chart | 1:30 |
| 10 | Repository | What's where, how to run it, optional demo clip | 0:30 |
| 11 | Reflection | Strengths, limitations, next steps, takeaway, M&S application | 1:15 |

About 9:45 in total.

## Slide 7: Why lessons, not RL?

- Learning lives in memory, not weights. The LLM proposes lessons and game outcomes select among them; the win/loss tally is a small bandit over lessons. Related work: Reflexion, ExpeL, Voyager.
- Table: games needed (RL: thousands to millions; FrontLine: tens), output (an opaque policy vs readable rules), fits the designer user, auditable by a person, cost per game.
- Be honest: RL or MCTS would likely play a 5x5 board better. The goal is strategy people can read and check, not the strongest player.
- Takeaway line: "RL learns to win; FrontLine learns to explain what wins."

## Slide 11: Where this goes next (M&S and training)

- The same loop suits adversarial agents in training simulation:
  - an **explainable, adaptive OPFOR** whose tactics instructors can read and audit
  - the review crew as **automated after-action review**
  - the sim engine stays authoritative and the agent only proposes
- Planned: an I/ITSEC paper with a hosted model, 100+ games per condition, an MCTS opponent, and instructor ratings of lesson quality (backlog item 15 in `docs/future-enhancements.md`).
- Keep it to one or two lines on the slide; it's a pointer, not a claim.

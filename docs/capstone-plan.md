# FrontLine Capstone: Day-by-Day Plan

Oct 11, 2026 · @Chris

FrontLine gets built before the Oct 16 Okinawa trip, runs and gets analyzed while you travel, is written up at home Nov 1 to 8, and is presented in Module 7, the week of Nov 9.

Track progress day by day in Daily checklist.

## Assumptions and key dates

| Item | Date | Status |
| --- | --- | --- |
| Build sprint (engine, agents, tracing, review crew) | Oct 11 to 15 | Planned |
| Okinawa trip | Oct 16 to 31 | Working remotely, 16 hours ahead of home |
| Unattended runs (baseline, training, frozen eval, ablation) | Oct 16 to 21 | Planned |
| Analysis, fixes, reruns | Oct 23 to 31 | Planned |
| Write-up, slides, dry run | Nov 1 to 8 | Planned |
| Capstone presentation (Module 7) | Week of Nov 9 | Assumed, could be week of Nov 16 |
| Human play with Streamlit | After the presentation | Post-course |

Weekdays assume about 2 hours in the evening. Weekends and Mon Oct 12 (day off) assume 5 to 6 hours.

Module map, assuming one module per week with Module 2 ending today:

| Week of | Module | Where it shows up in FrontLine |
| --- | --- | --- |
| Oct 5 | 2: Memory, tools, reasoning loops | Player Agent tools, lesson memory, LangGraph loop |
| Oct 12 | 3: RAG and vector databases | Lesson retrieval by board similarity |
| Oct 19 | 4: Tree-of-thought and multi-agent, part 1 | 3-candidate move selection, player vs reviewer |
| Oct 26 | 5: CrewAI and LangGraph, part 2 | Review crew, match state machine |
| Nov 2 | 6: Evaluation, guardrails, logging, observability | OTel traces, baselines, seeds, promotion gate |
| Nov 9 | 7: Capstone | Presentation |

Open questions:

- [ ] Is the capstone presentation the week of Nov 9 or Nov 16, and what day?
- [ ] Is the design write-up due before you leave?
- [ ] Does Oct 31 expect a live demo, a recording, or slides only?

## Week 2: Build sprint (Oct 11 to 15)

Goal: everything that the experiments need is working and running on its own before you leave. Course focus is Module 2 (memory, tools, reasoning loops).

| Day | Build | Done when |
| --- | --- | --- |
| Sun Oct 11 | Morning: Module 2 live sessions and reading. Afternoon: game engine with v1 rules, validator, terminal board printer, random and greedy bots | 1,000 bot games run with no errors, and first-mover win rate is near 50% with alternation |
| Mon Oct 12 (day off) | LangGraph match loop (observe, retrieve, decide, validate, apply, check end). Player Agent with read-only tools and a Pydantic action schema. OpenTelemetry spans saved as JSON | The LLM agent plays a full legal game vs greedy, and you have an illegal-move rate over 10 games |
| Tue Oct 13 | Tree-of-thought: 3 candidate moves, scored, one picked. Vector-store lesson retrieval, top 3 by board similarity | One trace shows the 3 candidates and the retrieved lessons |
| Wed Oct 14 | CrewAI review crew (analyst, critic, curator) that reads the trace but not the player's reasoning. Lesson store with confidence score, cap of 30, and retire rule | A lesson written after game N shows up in retrieval in game N+1 |
| Thu Oct 15 | Pilot of 10 to 20 games, fix bugs, freeze rules (git tag v1-rules). Queue all trip runs in one runner script under tmux or systemd | Runs are going unattended before you go to bed |

Travel-safe checklist for Thursday:

- [ ] Each game saves its trace and lesson snapshot when it finishes (resumable)
- [ ] One log line per game: game number, condition, winner, lessons kept
- [ ] Nightly summary file you can read from your phone
- [ ] Failure guard: stop after 3 games in a row error out
- [ ] Run queue set: Condition A first, then Condition B (see Week 3)

Remote access checklist for Thursday:

- [ ] Tailscale on the home machine, laptop, and phone, with SSH tested over a phone hotspot
- [ ] Ollama runs as a systemd service and starts on boot
- [ ] Machine powers on after an outage, and automatic OS reboots are off
- [ ] One config line switches between home Ollama and a hosted API, tested with a 2-game run
- [ ] Hosted API key has a spending limit set

## Week 3: Travel and unattended runs (Oct 16 to 22)

Goal: the machine does the work, you spend 10 minutes a day checking it and use spare time for course content. Course focus is Module 3 (RAG) and Module 4 (tree-of-thought and multi-agent).

Run queue:

- **A, baseline:** no lessons vs greedy, 50 games, sides alternated
- **B, training:** lessons on, 120 games mixing self-play and greedy opponents
- **C, frozen eval:** lesson store frozen after B, 50 games vs greedy, sides swapped
- **D, ablation:** C with tree-of-thought off (single candidate), 30 games
- **Repeat A to D with a second seed** so you can tell real gaps from noise
- **B-long:** if the machine is idle, extend training to 300 games to see where learning levels off

At roughly a minute per game, one pass of A to D takes about 4 to 5 hours, so both seeds finish well before you are home.

| Day | Runs | Your work |
| --- | --- | --- |
| Fri Oct 16 | A to D, seed 1 | Travel. Check the summary file once |
| Sat Oct 17 | A to D, seed 2 | Note baseline win rate and illegal-move rate. Module 3 reading: compare its retrieval methods to your lesson retrieval |
| Sun Oct 18 | B-long starts | Learning log: what do the first numbers tell you? |
| Mon Oct 19 | B-long running | Module 4 lecture. List 2 ways the course's tree-of-thought differs from yours |
| Tue Oct 20 | B-long running | Read 5 lessons and flag any that look wrong. Note them only, do not edit mid-run |
| Wed Oct 21 | B-long finishes | Outline the write-up: problem, design, and implementation need no results |
| Thu Oct 22 | Idle | Check that all runs finished cleanly |

Building modules 4 and 5 ahead of the lectures is a feature, not a problem. When the lecture comes, use it as a code review of what you already built.

## Week 4: Analyze and iterate from Okinawa (Oct 23 to 31)

Goal: a results table you trust and two traces that show a specific lesson changing a specific move. Course focus is Module 5 (CrewAI and LangGraph).

| Day | Work | Done when |
| --- | --- | --- |
| Fri Oct 23 | Skim the nightly summaries. Compare seed 1 and seed 2 | You know the top 2 problems and which gaps beat the noise |
| Sat Oct 24 | Analysis notebook: rolling win rate, illegal-move rate, lesson count, win rate when a lesson is cited vs not. Results table: A vs C vs D | 4 charts and the table saved |
| Sun Oct 25 | Fix the top 2 problems. Rerun B and C overnight | Rerun launched |
| Mon Oct 26 | Module 5 lecture. Review your LangGraph and CrewAI code against the course patterns | Short list of changes worth making |
| Tue Oct 27 | Apply the Module 5 changes. Rerun C if the agents changed | Changes merged |
| Wed Oct 28 | Pick the 2 best traces | Traces in the write-up folder |
| Thu Oct 29 | Minimal Streamlit replay viewer | The viewer replays a saved game move by move |
| Fri Oct 30 | Buffer |  |
| Sat Oct 31 | Lock the numbers and draft the Results section. Travel home | Results draft written |

Watch for: lessons cited but not followed, one bad loss creating a rule that sticks, and win-rate gaps smaller than the seed-to-seed difference.

## Week 5: Write up at home (Nov 1 to 8)

Goal: a finished write-up, slides, and a recorded backup demo before Module 7. Course focus is Module 6 (evaluation, guardrails, observability).

| Day | Work | Done when |
| --- | --- | --- |
| Sun Nov 1 | Recover from travel. Reread the results with fresh eyes |  |
| Mon Nov 2 | Module 6 lecture. Add one guardrail or eval it teaches, such as an LLM judge that scores lesson quality | Metric runs on the lesson store |
| Tue Nov 3 | Write-up: problem and design | Sections done |
| Wed Nov 4 | Write-up: implementation and evaluation | Sections done |
| Thu Nov 5 | Write-up: limitations (AlphaZero comparison, memory poisoning as future work) | Full draft done |
| Fri Nov 6 | About 10 slides built around the results table and the 2 traces. Demo script | Slides done |
| Sat Nov 7 | Record a backup video. Timed dry run | Fits the time limit |
| Sun Nov 8 | Freeze the repo, write the README, tag v1.0 | Someone else could run it from the README |

## Week 6: Present (week of Nov 9)

Present and submit in Module 7. If the presentation turns out to be the week of Nov 16, use the extra week for a small human-play demo.

## After the course: Human play

Once the capstone is submitted, open FrontLine to people at your own pace. The order that keeps it safe:

1. Add a play mode to the Streamlit viewer, against the frozen agent
2. Log human games to SQLite, with a consent note on the start screen
3. Write lessons from human games to a separate candidate file
4. Promote a candidate lesson only if a self-play batch vs greedy does not lose win rate
5. Run 5 to 10 playtests with family or classmates, then compare agent results vs humans before and after

## Learning routine and after the course

A 5-minute daily habit keeps the course learning separate from the build, so you come out with both.

- **Daily learning log, 3 lines:** one concept from the course, where it shows up in FrontLine, one open question
- **End of each module:** bring the log here and I will quiz you on it and point out where your code differs from the taught pattern
- **Before each big build day:** spend 10 minutes on what "done" looks like, using the Done when column above

After the course (optional, not part of the capstone):

- The review crew, lesson store, and promotion gate carry over directly to an Oly-Spark item-bank auditor
- FrontLine itself could become teaching material, such as a workshop on building a self-improving game agent

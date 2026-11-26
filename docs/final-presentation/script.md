# FrontLine final presentation: read-aloud script

About 1,400 words: 9:20 at a normal pace (150 words a minute), 10:00 if you go slower (140). Times are targets per slide. **[next]** means advance the slide.

---

## 1. Opening (0:45)

Hi, I'm Chris Teli, and this is FrontLine, my capstone for the CMU Agentic AI program.

When someone designs a new game, finding out which strategies win takes a lot of playtesting: change a rule, play, notice what works, repeat. My users are game designers and instructors who want to know what wins and why, and players who want advice that's been tested in real games.

FrontLine is an agent that plays a small territory game I designed, reviews each game, and keeps only the lessons that lead to wins. All of that learning lives in a file you can read, not in model weights.

**[next]**

## 2. Why it matters (0:30)

Why agents? A plain LLM has no memory between games, can't check its own advice, and can't reliably follow the rules. In my first test, it made an illegal move about one turn in eight.

Agents fix each of those: tools do the math, memory carries lessons forward, and separate agents judge the play. So my question was whether an agent can improve by writing and keeping its own lessons, without changing the model.

**[next]**

## 3. Architecture (1:15)

Here's the whole system as one loop.

At the center is the game engine. It's plain, deterministic Python with no LLM in it, and it checks every move. That means if a move is bad, it's always the agent's fault, never the rules'.

Each turn runs through a LangGraph state machine with five steps: observe, retrieve, decide, validate, and apply. Only the decide step calls an LLM, which is Qwen3 32B running locally through Ollama. Before that, the retrieve step finds the three lessons written for the boards most similar to the current one and puts them in the prompt.

When the game ends, everything gets saved: a turn-by-turn trace and an OpenTelemetry span tree. Then a CrewAI review crew reads that trace. An analyst finds the turning point, a critic throws out any claim the boards don't support, and a curator decides whether to add the lesson, merge it with an existing one, or skip it. The lesson goes back into the store, and the next game begins.

**[next]**

## 4. The game, one turn (0:45)

Here's the game. On each turn a player claims an empty neighboring cell, reinforces one of their cells, or attacks. Cells that get cut off from home lose strength, and you win by capturing the enemy's home or by owning more cells after twelve turns each.

This is turn 11 of a real training game. The agent is coral, and teal has just taken B3. The agent proposed three moves, and the engine scored each after teal's best reply. The attack scored highest, so the agent took B3, and it went on to win ten cells to eight.

It also cited lesson L6, but citing a lesson doesn't make it good: L6 was later retired with one win and four losses.

**[next]**

## 5. Key decision: the LLM judges, code calculates (1:00)

The most important design decision came from watching the agent fail. With a single LLM call per turn, it made illegal moves twelve and a half percent of the time. Whenever I asked the LLM to do arithmetic, it got it wrong.

So I stopped asking it to. Read-only tools now do the math: previewing an attack, checking supply, and scanning for threats. The legal moves are always in the prompt. On top of that is the tree-of-thought step you just saw: the LLM proposes three different moves, the engine scores each one two moves deep, and the LLM picks one.

That brought illegal moves down to between one and three percent. The ablation in the main experiment backs this up: take tree-of-thought away, and illegal moves jump back to twenty percent. The LLM now does only what needs judgment: which plans to try, which one to pick, and what lesson to draw afterward.

**[next]**

## 6. Key decision: keeping lessons honest (0:45)

The second big risk is memory poisoning, where an agent writes itself bad advice and then believes it. So every lesson has to pass two checks.

First, the review crew only sees a stripped trace: moves and boards, with none of the player's reasoning. The player can't argue its way into a lesson, and the critic rejects anything the boards don't show.

Second, outcomes decide. A lesson only gets credit or blame when it was retrieved and the player actually cited it. Its confidence is wins plus one over games plus two, so one lucky game can't make it look perfect. In training, the crew wrote ten lessons, and this rule retired eight of them.

**[next]**

## 7. Key decision: why lessons, not reinforcement learning (0:45)

Why not reinforcement learning? RL updates a policy's weights over thousands or millions of games, and it would very likely play this five-by-five board better than my agent does. I'm not claiming otherwise.

But my users want strategies they can read, check, and argue with, and an RL policy can't explain itself. And each LLM game takes about nine minutes, so millions of games were never an option. FrontLine keeps its learning in memory instead: the LLM writes a lesson in plain English, and game results decide whether it stays. That puts it in the same family as Reflexion, ExpeL, and Voyager. The short version: RL learns to win, and FrontLine learns to explain what wins.

**[next]**

## 8. Evaluation (0:45)

To test the system, the agent played a greedy bot that always takes the move with the best immediate score, and the first move alternated every game.

I ran four conditions. A is the baseline, with no lessons. B is training: the lesson store starts empty and the crew reviews every game. C takes B's final store and freezes it, so it measures what was learned without any learning during the test. And D is C without tree-of-thought, as an ablation. Comparing C to A tells us whether learning helped, and comparing C to D tells us whether tree-of-thought helped.

**[next]**

## 9. Results (1:30)

These results come from the main run, which was fifty games over seven and a half hours, with no errors.

Tree-of-thought is the clearest result. With it, illegal moves stayed between one and three percent. Without it, in condition D, they jumped to twenty percent, and the agent finished with fewer cells.

The honest answer on lessons is that the frozen store didn't raise the win rate. C won none of its ten games, and A won one. C did end with slightly more cells and picked the engine's top-scored move more often, but that isn't the same as winning. Partly, the tally did its job almost too well: eight of ten lessons were retired in training, so C played with just two unproven lessons.

Training, condition B, did best, at five wins out of twenty, but every one of those wins came when the agent moved first. Across all fifty games, the agent won six of the twenty-five it started and none of the twenty-five where it moved second. With only ten to twenty games per condition, these are trends, not statistically significant results.

**[next]**

## 10. Repository (0:30)

Everything is in the public GitHub repository: the code, the rules, twenty-six tests, and the final report. The results folder has the experiment data, the charts, and one sample game per condition, including the one I showed you. You can install it and play a full game without an LLM in under a minute. LLM games need Ollama and the Qwen3 32B model.

**[next]**

## 11. Reflection (1:15)

To wrap up: what worked. Tools and tree-of-thought nearly eliminated illegal moves, and the ablation shows tree-of-thought is the reason. Every move can be traced, and bad lessons get caught and retired without a person stepping in.

What hasn't worked yet is win rate. Lessons change how the agent plays but haven't made it win more; in twenty training games, bad lessons were retired faster than good ones turned up. The samples are small, moving second against a greedy bot is very hard, and this is one model on one game.

Next, I want to run a hundred or more training games with a second seed, add a score guard so the LLM can't overrule a much better move, and test against stronger opponents like MCTS.

My biggest takeaway is that every time I asked the LLM to calculate, it failed, and every time code took over, the system got better. Give the LLM judgment, and give code the math.

My field is modeling and simulation, and this loop fits training simulations: an opposing force whose tactics instructors can read and audit, with the review crew as an automated after-action review. I'm planning an I/ITSEC paper on it.

Thank you.

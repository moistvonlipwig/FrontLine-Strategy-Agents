# FrontLine: A Strategy Research Agent

I have a background in modeling and simulation, where there is a growing need for agents that can build strategies and adapt them to win against an opponent. To explore this, I am designing two agents, a Player Agent and a Reviewer Agent, supported by tools, a memory of past games, and retrieval of relevant lessons.

## 1. Agent, problem, intended user

- **Agent**
  - **Player Agent:** a strategy research agent that plays a turn-based territory game, called FrontLine (5×5 grid, claim/reinforce/attack, supply lines, win by capturing the enemy home or holding the most cells after 12 turns) that was created for this project.
  - **Reviewer Agent:** a separate agent that sees only the game trace and the final outcome, not the Player Agent's reasoning. It finds the turning point of each game, writes a strategy lesson, and keeps or retires lessons based on how they perform against baseline opponents.
  - **Orchestration:** each match runs as a LangGraph workflow (player turn, rules check, win check, next player), and the post-game review runs as a CrewAI crew.
- **Problem:** finding good strategies in a new game normally takes many human playtests. The agent automates that discovery and shows its reasoning.
- **Intended user:** game designers or instructors who want to balance rules and understand winning strategies, and players who want to learn from the agent's lessons.

## 2. Why a plain LLM isn't enough

- It has no memory between games, so it can't learn from past losses.
- It can't reliably apply rules or calculate outcomes; it needs a rules engine and tools to check.
- It can't act over many steps in a changing environment and react to an opponent.
- It has no way to test whether its advice actually works.

## 3. Environment

- **Documents:** the rules file.
- **Data sources:** game traces, the lesson store (memory of past games).
- **Tools:** legal moves, attack preview, supply check, threat scan, lesson search.
- **Other agents:** opposing agents and baseline bots.
- **Users:** human players and the designer reviewing results.

## 4. Actions

- Observe the board and check threats.
- Look up relevant past lessons.
- Use tree-of-thought: generate three candidate moves, test each with tools, score them, and pick the best.
- Choose and submit a move with a stated reason.
- After the game: review what happened, write a lesson, and update or retire old lessons.
- **Example turn:** the agent sees an enemy cell threatening its supply line, retrieves a lesson about protecting connecting cells, compares reinforcing versus attacking, and reinforces the link.

## 5. Feedback

1. **Every step:** tool results and whether the move was legal.
2. **Every game:** win or loss, and the turning point found in the trace.
3. **Across games:** lessons that keep losing get retired; lessons that work get kept. This is how the agent improves over time.
4. **Review crew:** an analyst finds the turning point, a critic checks the claim against the trace, and a curator keeps, merges, or retires the lesson.
5. **Example lesson:** after losing when its home was cut off, the agent writes "protect the cell that links your territory to home." In later games it reinforces that cell earlier and loses fewer cells to supply cuts.

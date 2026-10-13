# Learning log

3 lines a day: one course concept, where it shows up in FrontLine, one open question.

## Oct 12 (Day 1 + 2)

- **Concept:** The rules engine has no randomness. The same board plus the same move always gives the same result, every time.
- **In FrontLine:** 'bot' runs greedy and random mode.  In random mode the the starting player always wins first.
- **Question:** How will the LLM learn and build its strategy.  How will the strategy be stored?  Are the traces currently the episodic memory?

## Oct 12 (Day 2)

- **Concept:** Tool calling. The LLM sees each tool's name, arguments, and docstring as a JSON schema, then decides when to call it. The Pydantic schema works the same way and also acts as a prompt.
- **In FrontLine:** The Player Agent always gets the legal moves and can call preview_attack, supply_check, or threat_scan. LangGraph runs observe → retrieve → decide → validate → apply, and every node is traced as an OpenTelemetry span.
- **Question:** Greedy beats the LLM with no memory. Will lessons alone close the gap, or does the LLM need tree-of-thought to use the tools well?

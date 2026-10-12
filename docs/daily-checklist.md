# Daily checklist

Tick each item as you finish it. Dates match the plan tab, ending with the Module 7 presentation the week of Nov 9.

## Week 2: Build sprint

### Sun Oct 11

- [x] Module 2 live sessions and reading
- [x] Game engine with v1 rules and validator
- [x] Terminal board printer
- [x] Random and greedy bots
- [x] 1,000 bot games run with no errors
- [x] First-mover win rate near 50% with alternation (greedy 53.5% after home-strength-3 fix)
- [x] Engine exposes get\_state, legal\_moves, apply, and saves traces as JSON
- [x] Learning log entry

### Mon Oct 12 (day off)

- [ ] LangGraph match loop: observe, retrieve, decide, validate, apply, check end
- [ ] Player Agent read-only tools
- [ ] Pydantic action schema
- [ ] OpenTelemetry spans saved as JSON
- [ ] LLM agent plays a full legal game vs greedy
- [ ] Illegal-move rate measured over 10 games
- [ ] Learning log entry

### Tue Oct 13

- [ ] Tree-of-thought generates 3 candidate moves
- [ ] Candidates scored and one picked
- [ ] Vector-store lesson retrieval, top 3 by board similarity
- [ ] One trace shows the candidates and retrieved lessons
- [ ] Learning log entry

### Wed Oct 14

- [ ] CrewAI review crew: analyst, critic, curator
- [ ] Crew reads the trace but not the player's reasoning
- [ ] Lesson store with confidence score, cap of 30, and retire rule
- [ ] A lesson from game N shows up in retrieval in game N+1
- [ ] Learning log entry

### Thu Oct 15

- [ ] Pilot of 10 to 20 games
- [ ] Fix bugs found in the pilot
- [ ] Freeze rules, git tag v1-rules
- [ ] Each game saves its trace and lesson snapshot (resumable)
- [ ] One log line per game
- [ ] Nightly summary file readable from your phone
- [ ] Failure guard stops after 3 errors in a row
- [ ] Queue A to D seed 1, A to D seed 2, then B-long
- [ ] Runner started under tmux or systemd before bed

* [ ] Tailscale on home machine, laptop, and phone; SSH tested over a phone hotspot
* [ ] Ollama runs as a systemd service and starts on boot
* [ ] Power-on after outage set, automatic OS reboots off
* [ ] Config switch between home Ollama and hosted API tested with a 2-game run
* [ ] Hosted API key has a spending limit

## Week 3: Okinawa, unattended runs

### Fri Oct 16

- [ ] Check the summary file once

### Sat Oct 17

- [ ] Note baseline win rate and illegal-move rate
- [ ] Module 3 reading, compared to your lesson retrieval

### Sun Oct 18

- [ ] Confirm both seeds finished and B-long started
- [ ] Learning log: what the first numbers tell you

### Mon Oct 19

- [ ] Module 4 lecture
- [ ] List 2 ways the course's tree-of-thought differs from yours

### Tue Oct 20

- [ ] Read 5 lessons and flag any that look wrong (note only)

### Wed Oct 21

- [ ] Confirm B-long finished
- [ ] Outline the write-up: problem, design, implementation

### Thu Oct 22

- [ ] Check that all runs finished cleanly

## Week 4: Analyze and iterate from Okinawa

### Fri Oct 23

- [ ] Skim the nightly summaries
- [ ] Compare seed 1 vs seed 2
- [ ] Write down the top 2 problems

### Sat Oct 24

- [ ] Chart: rolling win rate
- [ ] Chart: illegal-move rate
- [ ] Chart: lesson count
- [ ] Chart: win rate when a lesson is cited vs not
- [ ] Results table: A vs C vs D

### Sun Oct 25

- [ ] Fix problem 1
- [ ] Fix problem 2
- [ ] Rerun B and C overnight

### Mon Oct 26

- [ ] Module 5 lecture
- [ ] List changes from comparing your LangGraph and CrewAI code to the course patterns

### Tue Oct 27

- [ ] Apply the Module 5 changes
- [ ] Rerun C if the agents changed

### Wed Oct 28

- [ ] Pick 2 traces that show a lesson changing a move

### Thu Oct 29

- [ ] Streamlit viewer replays a saved game move by move

### Fri Oct 30

- [ ] Buffer: catch up on anything that slipped

### Sat Oct 31

- [ ] Lock the numbers
- [ ] Draft the Results section
- [ ] Travel home

## Week 5: Write up at home

### Sun Nov 1

- [ ] Reread the results with fresh eyes

### Mon Nov 2

- [ ] Module 6 lecture
- [ ] Add one guardrail or eval metric from Module 6

### Tue Nov 3

- [ ] Write-up: problem
- [ ] Write-up: design

### Wed Nov 4

- [ ] Write-up: implementation
- [ ] Write-up: evaluation

### Thu Nov 5

- [ ] Write-up: limitations
- [ ] Full draft read end to end

### Fri Nov 6

- [ ] About 10 slides
- [ ] Demo script

### Sat Nov 7

- [ ] Backup video recorded
- [ ] Timed dry run fits the limit

### Sun Nov 8

- [ ] Repo frozen, README written, tagged v1.0

## Week 6: Module 7 capstone (week of Nov 9)

- [ ] Confirm the presentation date
- [ ] Present
- [ ] Submit

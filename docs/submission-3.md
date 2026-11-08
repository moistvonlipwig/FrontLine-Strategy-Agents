# FrontLine: Capstone Checkpoint (Retrieval)

## Why the agent needs retrieval

An LLM forgets everything between games. It also knows nothing about FrontLine, because I created the game for this project. Without retrieval, the agent would keep making the same mistakes. Retrieval gives it lessons from past games on each turn.

## How retrieval works

- **Data source:** a store of lessons. The Reviewer crew writes them after reading finished games. Each lesson has a situation, some advice, and a win-loss record.
- **Storage:** each lesson is saved in a JSON file with a list of numbers describing the board it came from. The list has one number per cell (25) plus one for how far the game has gone.
- **Search:** each turn, the current board is turned into the same kind of list. The store returns the 3 lessons from the most similar boards, using cosine similarity. The store holds 30 lessons at most, so it doesn't need a vector database.
- **Use:** the 3 lessons go into the Player's prompt before it suggests moves.

## Did retrieval change what the agent did?

**What is logged:** each turn logs which lessons were retrieved, which ones the chosen move cites, and their similarity scores. I only count a citation if that lesson was retrieved that turn. The LLM sometimes cites things that aren't lessons, such as "expand".

**The test:** the Player played the greedy bot 10 times with lessons off and 10 times with lessons on. The first mover alternated. The lessons came from 20 earlier training games and did not change during the lessons-on games. This is a small test, so it only shows a rough trend.

| Condition | Wins | Avg. cells at end | Supply-cut losses | Illegal moves |
|---|---|---|---|---|
| Lessons off | 1/10 | 8.0 | 0 | 2/120 |
| Lessons on | 1/10 | 8.9 | 0 | 4/120 |

**Result:** lessons changed the agent's moves, but it did not win more often.

**Notes on the test:**

- No cell was cut off from supply in any of the 40 games, so the supply-cut column shows no difference.
- An LLM call hung after 2 lessons-on games. The other 8 games used a new bot seed and a 2,000-token output limit, so the two conditions are not an exact match.
- After training, only 4 of the 11 lessons were still in use. None had a winning record.

### Example: a lesson changes a move

Game on2-g01, turn 14, Coral to move. Coral's home is A1 and Teal's home is E5.

```
    A   B   C   D   E
1  C2* C1   .   .   .
2  C1  C1   .   .   .
3   .  C1  T1  T1   .
4   .  C1  T1  T1  T1
5   .   .  T1  T1  T3*
```

The scores below come from the game engine. It plays the move, then the bot's best reply, and scores the result. Higher is better.

| | Move | Score |
|---|---|---|
| With lessons | Attack C3 from B3 | -56 |
| Without lessons | Claim A3 | -23 |

- **Lessons retrieved:** L11, L9, and L8.
- **Lesson the agent followed:** L9, "Attack opponent's cells adjacent to their home to cut off their expansion and secure strategic positions." Its record was 0 wins and 2 losses.
- **Agent's reason:** "The attack on B3->C3, while currently low in score, offers a strategic advantage by targeting an enemy cell adjacent to their home. This aligns with [L9]..."

**What went wrong:** C3 is not next to Teal's home at E5, so the agent misused the lesson. It also picked the lowest-scoring of its 3 options.

### Replay check

I replayed 7 turns with and without lessons. I chose turns where the agent cited a lesson and picked a move that scored lower than another option, so this is not a random sample.

- With lessons, the agent made the same move as in the original game on all 7 turns.
- Without lessons, it made a different move on 6 of the 7.
- On all 6, the move made with lessons had the lower score.

## Design choices

- **Lessons, not full game logs:** game logs are long and mostly routine. Lessons are short, and the Reviewer's critic checks them first.
- **One lesson per search entry:** each lesson covers one idea, so there is nothing to split.
- **Board matching:** the search compares boards, not the advice text, so it finds lessons from similar positions.
- **3 lessons per turn:** this gives the agent some options without making the prompt long or adding conflicting advice.
- **Retired lessons:** these are left out of the search.

## What can go wrong

**1. A lesson doesn't fit the board.**

- **Problem:** two boards can look similar but differ in a way that matters, such as one cell's strength.
- **Current protection:** the game engine scores each suggested move before the LLM picks one.
- **Limit:** the LLM can still pick a low-scoring move, as the example shows.
- **Next step:** stop the LLM from picking a move that scores far below its best option.

**2. Bad lessons stay in the store.**

- **Protection:** each lesson's win-loss record is tracked, and lessons that keep losing are retired.
- **So far:** 7 of 11 lessons were retired in training. The other 4 are still unproven.

**3. There are few or no lessons at the start.**

- **Protection:** the agent plays with its tools and no lessons. This is the same as the lessons-off test.

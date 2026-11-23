# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Builds the final presentation as a .pptx (upload to Google Drive to convert it to Slides).

    uv run --with python-pptx python docs/final-presentation/build_deck.py

Follows deck-plan.md: 10 slides, about 9:45, with the spoken script in each slide's speaker notes.
"""

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).with_name("FrontLine Final Presentation.pptx")

INK, INK_2, MUTED, LINE = "0B0B0B", "52514E", "8A8984", "E4E3DF"
CORAL, TEAL, PANEL, WHITE = "E0623F", "1F8A80", "F5F4F0", "FFFFFF"
FONT = "Arial"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def rgb(hex_):
    return RGBColor.from_string(hex_)


def text(slide, x, y, w, h, paras, size=18, color=INK, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    """paras: a string, or a list of strings / (string, {size, color, bold, bullet}) tuples."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, p in enumerate([paras] if isinstance(paras, str) else paras):
        s, opts = (p, {}) if isinstance(p, str) else p
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        para.space_after = Pt(opts.get("after", 8))
        r = para.add_run()
        r.text = ("•  " if opts.get("bullet") else "") + s
        r.font.name = FONT
        r.font.size = Pt(opts.get("size", size))
        r.font.bold = opts.get("bold", bold)
        r.font.color.rgb = rgb(opts.get("color", color))
    return box


def box(slide, x, y, w, h, fill=PANEL, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = rgb(fill)
    if line:
        s.line.color.rgb = rgb(line)
        s.line.width = Pt(1.25)
    else:
        s.line.fill.background()
    s.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.08
    return s


def card(slide, x, y, w, h, title, body, accent=CORAL, size=15):
    box(slide, x, y, w, h)
    box(slide, x, y, 0.08, h, fill=accent, shape=MSO_SHAPE.RECTANGLE)
    text(slide, x + 0.3, y + 0.22, w - 0.5, 0.5, title, size=18, bold=True)
    text(slide, x + 0.3, y + 0.75, w - 0.5, h - 0.9, body, size=size, color=INK_2)


def arrow(slide, x1, y1, x2, y2, color=INK_2):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(color)
    c.line.width = Pt(2)
    ln = c.line._get_or_add_ln()
    tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"})
    ln.append(tail)
    return c


def table(slide, x, y, w, rows, col_w, size=14, row_h=0.42, highlight=None):
    t = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows))).table
    for j, cw in enumerate(col_w):
        t.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        t.rows[i].height = Inches(row_h)
        for j, val in enumerate(row):
            cell = t.cell(i, j)
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(INK if i == 0 else (PANEL if i == highlight else WHITE))
            cell.margin_left = cell.margin_right = Inches(0.1)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.text = ""
            r = p.add_run()
            r.text = val
            r.font.name, r.font.size = FONT, Pt(size)
            r.font.bold = i == 0 or (j == 0)
            r.font.color.rgb = rgb(WHITE if i == 0 else INK)
    return t


def slide(n, kicker, title, notes):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = rgb(WHITE)
    if kicker:
        text(s, 0.6, 0.45, 9, 0.35, kicker.upper(), size=12, color=CORAL, bold=True)
        text(s, 0.6, 0.8, 12.1, 0.9, title, size=30, bold=True)
    text(s, 12.2, 7.0, 0.6, 0.3, str(n), size=11, color=MUTED, align=PP_ALIGN.RIGHT)
    s.notes_slide.notes_text_frame.text = notes.strip()
    return s


# 1. Opening ---------------------------------------------------------------
s = slide(1, None, None, """
[0:45] Hi, I'm Chris Teli, and this is FrontLine, my capstone for the CMU Agentic AI program.

The problem: finding good strategies in a new game takes many rounds of human playtesting. A designer changes a rule, people play, someone notices what wins, and the cycle repeats.

My users are game designers and instructors who want to know which strategies win and why, and players who want advice that has actually been tested in play.

The goal: an LLM agent plays a small territory game I designed. A crew of agents reviews each game and writes a lesson. And the lesson store keeps only the lessons that win. All the learning lives in a readable file, not in model weights.
""")
box(s, 0, 0, 0.25, 7.5, fill=CORAL, shape=MSO_SHAPE.RECTANGLE)
text(s, 0.9, 1.3, 11, 0.4, "CMU AGENTIC AI · FINAL CAPSTONE", size=13, color=CORAL, bold=True)
text(s, 0.9, 1.8, 11, 1.2, "FrontLine", size=60, bold=True)
text(s, 0.9, 2.95, 11, 0.8, "A strategy agent that writes, tests, and retires its own lessons", size=24, color=INK_2)
text(s, 0.9, 3.7, 11, 0.4, "Chris Teli", size=16, color=MUTED)
for i, (h, b) in enumerate([
    ("Problem", "Finding strategies in a new game takes slow, manual playtesting"),
    ("User", "Game designers and instructors; players who want tested advice"),
    ("Goal", "An agent that plays, reviews its games, and keeps only lessons that win"),
]):
    card(s, 0.9 + i * 3.95, 4.6, 3.7, 2.0, h, b, accent=[CORAL, TEAL, INK_2][i])

# 2. Why it matters --------------------------------------------------------
s = slide(2, "Why it matters", "Playtesting is slow, and a plain LLM can't take it over", """
[0:45] Why does this need agents?

Playtesting is slow. Every rule change means more rounds of people playing.

A plain LLM can't take that over on its own. It has no memory between games. It can't reliably apply rules or do the arithmetic. In my first test it made an illegal move one turn in eight. And it has no way to check whether its own advice works.

That's exactly what agent design is for. Tools do the math. Memory carries lessons between games. And separate agents judge the play, so the agent that plays isn't the one grading itself.

My background is modeling and simulation, and the broader question is: can an agent get better at a task by writing and keeping its own lessons, without changing model weights?
""")
cols = [
    ("Playtesting is slow", ["Change a rule, play, notice what wins, repeat", "Every round needs people"], CORAL),
    ("A plain LLM can't do it", ["No memory between games", "Can't reliably apply rules or do the math: 1 illegal move in 8", "Can't check its own advice"], INK_2),
    ("Agents fit the problem", ["Tools do the math", "Memory carries lessons between games", "A separate crew judges the play"], TEAL),
]
for i, (h, items, acc) in enumerate(cols):
    card(s, 0.6 + i * 4.1, 2.0, 3.85, 3.6, h, [(t, {"bullet": True, "after": 12}) for t in items], accent=acc, size=16)
text(s, 0.6, 6.0, 12, 0.6, "The question: can an agent improve by writing and keeping its own lessons, without changing model weights?",
     size=18, bold=True)

# 3. Architecture ----------------------------------------------------------
s = slide(3, "Architecture", "Play, trace, review, keep what wins", """
[1:15] Here's the whole system as one loop.

At the center is a deterministic game engine in plain Python, with no LLM. It validates every move, so a bad move is always the agent's fault, never the rules'.

Each turn runs through a LangGraph state machine: observe, retrieve, decide, validate, apply. Only "decide" calls an LLM. That's qwen3 32B, running locally through Ollama.

Retrieve pulls the three lessons from the most similar boards, using cosine similarity over the 25 cells, and puts them in the prompt.

When the game ends, everything is saved: a turn-by-turn trace and an OpenTelemetry span tree.

Then a CrewAI review crew reads the trace. The analyst finds the turning point, the critic rejects claims the boards don't support, and the curator adds, merges, or skips the lesson. That lesson goes back into the store, and the next game starts.
""")
nodes = {
    "store": (0.6, 2.0, 3.6, 1.7, "Lesson store", "JSON, cap 30\nwin/loss tally, retire rule", CORAL),
    "loop": (5.0, 2.0, 7.7, 1.7, "LangGraph match loop (per turn)", "observe → retrieve → decide → validate → apply", TEAL),
    "crew": (0.6, 4.6, 3.6, 1.9, "CrewAI review crew", "analyst → critic → curator\nsees moves and boards only", CORAL),
    "trace": (5.0, 4.6, 3.6, 1.9, "Trace + OTel spans", "boards, moves, legality,\ncandidates, cited lessons", INK_2),
    "player": (9.1, 4.6, 3.6, 1.9, "Player Agent", "qwen3:32b via Ollama\ntools + tree-of-thought", TEAL),
}
for x, y, w, h, t, b, acc in nodes.values():
    card(s, x, y, w, h, t, b, accent=acc, size=14)
arrow(s, 4.25, 2.85, 4.95, 2.85)            # store -> loop (top-3 lessons)
text(s, 4.05, 2.4, 1.1, 0.3, "top-3", size=11, color=MUTED, align=PP_ALIGN.CENTER)
arrow(s, 10.9, 3.75, 10.9, 4.55)            # loop -> player (decide)
text(s, 11.0, 3.95, 1.5, 0.3, "decide", size=11, color=MUTED)
arrow(s, 6.8, 3.75, 6.8, 4.55)              # loop -> trace (game over)
text(s, 6.9, 3.95, 1.5, 0.3, "game over", size=11, color=MUTED)
arrow(s, 4.95, 5.55, 4.25, 5.55)            # trace -> crew
arrow(s, 2.4, 4.55, 2.4, 3.75)              # crew -> store
text(s, 2.5, 3.95, 1.6, 0.3, "new lesson", size=11, color=MUTED)
text(s, 0.6, 6.75, 11, 0.4, "The engine is deterministic and has no LLM. Everything with an LLM wraps around it.",
     size=14, color=INK_2, bold=True)

# 4. Key decision: the LLM judges ------------------------------------------
s = slide(4, "Key decision", "The LLM judges; code calculates", """
[1:15] The most important design decision came from watching the agent fail.

With a single LLM call, it made illegal moves on 12.5 percent of turns: attacking with too little strength, claiming cells it couldn't reach. Every time I asked the LLM to calculate, it got it wrong.

So I stopped asking it to. Read-only tools do the math: preview an attack, check supply, scan for threats. Legal moves are always in the prompt.

Then tree-of-thought, with a twist. The LLM proposes three different moves. Instead of the LLM scoring its own ideas, the engine scores each one two moves deep: my move, then the greedy opponent's best reply. The LLM sees the scores and picks.

Illegal moves dropped to 1 to 3 percent. And the ablation in the main experiment confirms it: take tree-of-thought away and illegal moves jump back to 20 percent.

So the LLM does only what needs judgment: which plan to try, which candidate to pick, and what lesson to draw.
""")
box(s, 0.6, 2.0, 5.0, 4.6)
text(s, 0.9, 2.25, 4.4, 0.4, "ILLEGAL-MOVE RATE", size=12, color=MUTED, bold=True)
text(s, 0.9, 2.75, 4.4, 1.0, "12.5% → 1–3%", size=44, bold=True, color=TEAL)
text(s, 0.9, 3.85, 4.4, 0.8, "single LLM call → tools + tree-of-thought", size=15, color=INK_2)
box(s, 0.9, 4.75, 4.4, 0.02, fill=LINE, shape=MSO_SHAPE.RECTANGLE)
text(s, 0.9, 4.95, 4.4, 0.4, "ABLATION (MAIN RUN)", size=12, color=MUTED, bold=True)
text(s, 0.9, 5.35, 4.4, 1.2, [("2% with tree-of-thought", {"size": 20, "bold": True}),
                              ("20% without it (condition D)", {"size": 20, "bold": True, "color": CORAL})])
steps = [
    ("1  Tools do the math", "preview_attack, supply_check, threat_scan. Read-only; legal moves always in the prompt"),
    ("2  LLM proposes 3 moves", "Different plans, not three versions of one"),
    ("3  Engine scores each 2-ply", "The move, then greedy's best reply. Exact and fast"),
    ("4  LLM picks one", "Sees the scores; the engine still validates the move"),
]
for i, (h, b) in enumerate(steps):
    y = 2.0 + i * 1.17
    box(s, 6.1, y, 6.6, 1.02)
    text(s, 6.4, y + 0.14, 6.1, 0.4, h, size=17, bold=True)
    text(s, 6.4, y + 0.52, 6.1, 0.45, b, size=13, color=INK_2)

# 5. Key decision: honest lessons ------------------------------------------
s = slide(5, "Key decision", "Keeping lessons honest", """
[0:45] The second risk is memory poisoning: an agent writing itself bad advice and then believing it.

Every lesson faces two checks. First, the review crew gets a stripped trace: moves and boards only, no reasoning, so the player can't talk the crew into a lesson. The critic rejects any claim the boards don't support.

Second, outcomes. Only lessons the player actually cited, and that were retrieved that turn, get credit or blame. Confidence is wins plus one over games plus two, so one lucky game can't make a lesson look perfect. Three cited games at 0.5 or above promotes a lesson; five below 0.4 retires it.

The chart shows it working: ten lessons written in training, eight retired.
""")
items = [
    ("Stripped trace", "The crew sees moves and boards, never the player's reasoning"),
    ("Critic", "Rejects claims the boards don't support"),
    ("Cited and retrieved only", "Advice the player ignored isn't scored"),
    ("Confidence (w+1)/(g+2)", "Promote: 3 games ≥ 0.5 · Retire: 5 games < 0.4"),
]
for i, (h, b) in enumerate(items):
    y = 2.0 + i * 1.17
    box(s, 0.6, y, 5.3, 1.02)
    box(s, 0.6, y, 0.08, 1.02, fill=TEAL if i < 2 else CORAL, shape=MSO_SHAPE.RECTANGLE)
    text(s, 0.9, y + 0.14, 4.9, 0.4, h, size=17, bold=True)
    text(s, 0.9, y + 0.52, 4.9, 0.45, b, size=13, color=INK_2)
s.shapes.add_picture(str(ROOT / "results/lessons.png"), Inches(6.3), Inches(2.1), width=Inches(6.4))
text(s, 6.3, 5.6, 6.4, 0.8, "Training (B): 10 lessons written, 8 retired by the outcome tally.", size=15, color=INK_2)

# 6. Why lessons, not RL? --------------------------------------------------
s = slide(6, "Key decision", "Why lessons, not reinforcement learning?", """
[0:45] A fair question: why not reinforcement learning?

RL learns by updating a policy's weights over thousands to millions of games. It would very likely play this 5-by-5 board better than my agent. I'm not claiming otherwise.

But my user is a designer who wants strategies people can read, check, and argue with. An RL policy can't explain itself. And an LLM game takes about nine minutes, so millions of games aren't an option.

So FrontLine's learning lives in memory. The LLM proposes a lesson in plain English, and game outcomes decide whether it stays. The win-loss tally is a small bandit over lessons. It's the same family as Reflexion, ExpeL, and Voyager.

In one line: RL learns to win; FrontLine learns to explain what wins.
""")
table(s, 0.6, 2.0, 12.1, [
    ["", "Reinforcement learning", "FrontLine lessons"],
    ["Where learning lives", "Policy weights", "A readable JSON file"],
    ["Games needed", "Thousands to millions", "Tens"],
    ["Output", "An opaque policy", "Plain-English rules with a win-loss record"],
    ["Can a person audit it?", "Hard", "Yes: every lesson traces to its source game"],
    ["Plays a 5x5 board best?", "Very likely", "No, and that's not the goal"],
], [3.4, 4.0, 4.7], size=15, row_h=0.55)
text(s, 0.6, 5.6, 12.1, 0.5, "Related work: Reflexion, ExpeL, Voyager (improve agents by writing reflections or skills, not by training).",
     size=13, color=MUTED)
text(s, 0.6, 6.15, 12.1, 0.6, "RL learns to win; FrontLine learns to explain what wins.", size=24, bold=True, color=CORAL)

# 7. Evaluation ------------------------------------------------------------
s = slide(7, "Evaluation", "Four conditions against a greedy bot", """
[0:45] To evaluate it, the agent plays a greedy bot that always takes the move with the best immediate score. The first mover alternates every game.

There are four conditions. A is the baseline with no lessons. B is training: the store starts empty and the crew reviews every game. C uses B's final store, frozen, so it measures what was learned without learning during the test. And D is C without tree-of-thought, as an ablation.

C versus A asks whether learning helped. C versus D asks whether tree-of-thought helped.

I track win rate, illegal-move rate, how often the agent picked the engine's top-scored move, cells at the end, and how many lessons survive.
""")
table(s, 0.6, 2.0, 12.1, [
    ["Condition", "Lessons", "Review crew", "Tree-of-thought", "Question"],
    ["A  baseline", "none", "no", "yes", "How good is the agent with no memory?"],
    ["B  training", "on, starts empty", "every game", "yes", "Does the store fill with lessons that win?"],
    ["C  frozen eval", "B's final store, read-only", "no", "yes", "Did learning help? (C vs A)"],
    ["D  ablation", "B's final store, read-only", "no", "no", "Does tree-of-thought help? (C vs D)"],
], [2.0, 2.9, 1.6, 1.7, 3.9], size=14, row_h=0.6)
text(s, 0.6, 5.4, 12.1, 1.2, [
    ("Metrics: win rate · illegal-move rate · picked the top-scored move · cells at end · lessons live", {"size": 16}),
    ("Seed 1: 50 games (10 / 20 / 10 / 10), qwen3:32b on a laptop, 7.5 hours, 0 errors", {"size": 16, "color": INK_2}),
])

# 8. Results ---------------------------------------------------------------
s = slide(8, "Results", "Tree-of-thought helps; lessons didn't raise wins yet", """
[1:30] Here are the results from the main run: 50 games, seven and a half hours, no errors.

On the right chart: tree-of-thought is the clearest result. With it, illegal moves stay at 1 to 3 percent. Without it, in condition D, they jump to 20 percent, and the agent ends with fewer cells.

On the left: the honest answer is that the frozen lessons did not raise the win rate. C won 0 of 10, and A won 1 of 10. C did end with slightly more cells and picked the top-scored move more often, but that's not a win.

Why? The outcome tally did its job, maybe too well. The crew wrote ten lessons in training and eight were retired, so C ran with only two unproven lessons.

Training, condition B, did best at 5 of 20, but every one of those wins came as first mover. And seat mattered more than anything: across all 50 games the agent won 6 of 25 moving first, and 0 of 25 moving second.

With 10 to 20 games per condition, these are trends, not statistically significant differences.
""")
s.shapes.add_picture(str(ROOT / "results/conditions.png"), Inches(0.6), Inches(1.9), width=Inches(8.3))
findings = [
    ("ToT keeps moves legal", "2% → 20% illegal without it (C vs D)", TEAL),
    ("Lessons didn't raise wins", "C 0/10 vs A 1/10; 8 of 10 lessons retired", CORAL),
    ("Seat matters most", "6/25 wins moving first, 0/25 moving second", INK_2),
]
for i, (h, b, acc) in enumerate(findings):
    y = 1.95 + i * 1.12
    box(s, 9.2, y, 3.5, 0.98)
    box(s, 9.2, y, 0.08, 0.98, fill=acc, shape=MSO_SHAPE.RECTANGLE)
    text(s, 9.45, y + 0.12, 3.1, 0.4, h, size=14, bold=True)
    text(s, 9.45, y + 0.48, 3.1, 0.5, b, size=12, color=INK_2)
table(s, 0.6, 5.3, 12.1, [
    ["Cond", "Games", "Win rate", "Illegal moves", "Picked top-scored", "Avg. cells"],
    ["A  no lessons", "10", "1/10", "4/120 (3%)", "72%", "8.4"],
    ["B  training", "20", "5/20", "3/240 (1%)", "82%", "9.3"],
    ["C  frozen lessons", "10", "0/10", "3/120 (2%)", "80%", "8.9"],
    ["D  no ToT", "10", "0/10", "24/120 (20%)", "–", "7.6"],
], [2.6, 1.4, 1.8, 2.3, 2.3, 1.7], size=12, row_h=0.33)

# 9. Repository ------------------------------------------------------------
s = slide(9, "Repository", "github.com/moistvonlipwig/FrontLine-Strategy-Agents", """
[0:45] Everything is in the public repository.

The engine, agents, lesson store, review crew, and tracing are in the frontline package. The scripts folder has the match and experiment runners. The rules, with a worked example, are in docs. There are 26 tests, one per rule.

The results folder has the full experiment data, the charts, and one sample trace per condition. For example, s1-B-g016 is a win you can step through turn by turn, with the candidates, scores, and lessons the agent cited.

To try it: uv sync, uv run pytest, and you can play a full game without an LLM. LLM games need Ollama and the qwen3 32B model.
""")
table(s, 0.6, 2.0, 6.6, [
    ["What", "Where"],
    ["Setup, architecture, usage", "README.md"],
    ["Engine, agents, lessons, crew", "frontline/"],
    ["Match and experiment runners", "scripts/"],
    ["Rules with a worked example", "docs/rules.md"],
    ["26 tests, one per rule", "tests/"],
    ["Results, charts, sample traces", "results/"],
    ["Final report", "docs/final-report.md"],
], [3.6, 3.0], size=14, row_h=0.5)
box(s, 7.6, 2.0, 5.1, 4.0, fill=INK)
text(s, 7.9, 2.25, 4.6, 3.6, [
    ("# install and test", {"color": MUTED}),
    ("uv sync", {"color": WHITE}),
    ("uv run pytest", {"color": WHITE, "after": 16}),
    ("# a game with no LLM", {"color": MUTED}),
    ("uv run python scripts/run_match.py \\", {"color": WHITE}),
    ("    --coral greedy --teal random", {"color": WHITE, "after": 16}),
    ("# the A–D experiment (needs Ollama)", {"color": MUTED}),
    ("uv run python scripts/run_experiment.py \\", {"color": WHITE}),
    ("    --seed 1", {"color": WHITE}),
], size=12)
for p in s.shapes[-1].text_frame.paragraphs:
    for r in p.runs:
        r.font.name = "Courier New"
text(s, 7.6, 6.2, 5.1, 0.6, "Sample trace to show: results/traces/s1-B-g016.json (a win)", size=13, color=INK_2)

# 10. Reflection -----------------------------------------------------------
s = slide(10, "Reflection", "What worked, what didn't, what's next", """
[1:15] To wrap up.

What worked: tools and tree-of-thought nearly eliminated illegal moves, and the ablation proves tree-of-thought is the reason. Every move is traceable, and bad lessons are found and retired without a person stepping in.

What didn't, yet: lessons change the agent's moves but haven't raised its win rate. In 20 training games the safeguards rejected lessons faster than good ones were found. The samples are small, moving second against greedy is very hard, and it's one model on one game.

Next: longer training with 100 or more games and a second seed, a score guard so the LLM can't overrule a much better move, and stronger opponents like MCTS.

My biggest takeaway: every time I asked the LLM to calculate, it failed, and every time code took over, the system improved. Give the LLM judgment; give code the math.

And where this goes: my field is modeling and simulation. The same loop fits adversarial agents in training simulations: an opposing force whose tactics instructors can actually read and audit, with the review crew acting as an automated after-action review. I'm planning to take that to an I/ITSEC paper.

Thank you.
""")
card(s, 0.6, 1.9, 3.85, 2.75, "Worked", [(t, {"bullet": True, "after": 6}) for t in [
    "Illegal moves 12.5% → 1–3%", "Ablation proves ToT is why", "Bad lessons retired with no human",
    "Every move traceable"]], accent=TEAL, size=14)
card(s, 4.7, 1.9, 3.85, 2.75, "Not yet", [(t, {"bullet": True, "after": 6}) for t in [
    "Lessons didn't raise win rate", "8 of 10 lessons retired in 20 games", "Small samples; seat bias",
    "One model, one game"]], accent=CORAL, size=14)
card(s, 8.8, 1.9, 3.9, 2.75, "Next", [(t, {"bullet": True, "after": 6}) for t in [
    "100+ training games, second seed", "Score guard on LLM picks", "Stronger opponent (MCTS)",
    "Human play, second game"]], accent=INK_2, size=14)
text(s, 0.6, 4.9, 12.1, 0.6, "Takeaway: give the LLM judgment; give code the math.", size=22, bold=True)
box(s, 0.6, 5.65, 12.1, 1.15, fill=PANEL, line=TEAL)
text(s, 0.9, 5.8, 11.6, 0.9, [
    ("Where this goes: modeling & simulation", {"size": 15, "bold": True, "color": TEAL, "after": 4}),
    ("The same loop suits an explainable, adaptive OPFOR whose tactics instructors can audit, with the review crew "
     "as automated after-action review. Planned: an I/ITSEC paper.", {"size": 14, "color": INK_2}),
])

prs.save(OUT)
print(f"wrote {OUT}")

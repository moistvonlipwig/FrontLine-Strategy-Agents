# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Builds the final presentation as a .pptx (upload to Google Drive to convert it to Slides).

    uv run --with python-pptx python docs/final-presentation/build_deck.py

Follows deck-plan.md: 11 slides, about 9:45, with the spoken script in each slide's speaker notes.
"""

import json
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


def board(slide, x, y, state, mark=None, cell=0.58):
    """Draws a saved board: number = strength, * = home, outlined = `mark`."""
    for j, c in enumerate("ABCDE"):
        text(slide, x + j * cell, y - 0.28, cell, 0.25, c, size=11, color=MUTED, align=PP_ALIGN.CENTER)
    for i, r in enumerate("12345"):
        text(slide, x - 0.3, y + i * cell, 0.22, cell, r, size=11, color=MUTED, align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.MIDDLE)
        for j, c in enumerate("ABCDE"):
            name, sq = c + r, state["board"][c + r]
            cx, cy, d = x + j * cell, y + i * cell, cell - 0.05
            fill = {"coral": CORAL, "teal": TEAL, None: PANEL}[sq["owner"]]
            b = box(slide, cx, cy, d, d, fill=fill, line=INK if name == mark else None)
            if name == mark:
                b.line.width = Pt(3)
            if sq["owner"]:
                label = f"{sq['strength']}{'*' if name in state['homes'].values() else ''}"
                text(slide, cx, cy, d, d, [(label, {"after": 0})], size=18, color=WHITE, bold=True,
                     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


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

When someone designs a new game, finding out which strategies win takes a lot of playtesting: change a rule, play, notice what works, repeat. My users are game designers and instructors who want to know what wins and why, and players who want advice that's been tested in real games.

FrontLine is an agent that plays a small territory game I designed, reviews each game, and keeps only the lessons that lead to wins. All of that learning lives in a file you can read, not in model weights.
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
[0:30] Why agents? A plain LLM has no memory between games, can't check its own advice, and can't reliably follow the rules. In my first test, it made an illegal move about one turn in eight.

Agents fix each of those: tools do the math, memory carries lessons forward, and separate agents judge the play. So my question was whether an agent can improve by writing and keeping its own lessons, without changing the model.
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

At the center is the game engine. It's plain, deterministic Python with no LLM in it, and it checks every move. That means if a move is bad, it's always the agent's fault, never the rules'.

Each turn runs through a LangGraph state machine with five steps: observe, retrieve, decide, validate, and apply. Only the decide step calls an LLM, which is Qwen3 32B running locally through Ollama. Before that, the retrieve step finds the three lessons written for the boards most similar to the current one and puts them in the prompt.

When the game ends, everything gets saved: a turn-by-turn trace and an OpenTelemetry span tree. Then a CrewAI review crew reads that trace. An analyst finds the turning point, a critic throws out any claim the boards don't support, and a curator decides whether to add the lesson, merge it with an existing one, or skip it. The lesson goes back into the store, and the next game begins.
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

# 4. One game, one turn ----------------------------------------------------
s = slide(4, "The game", "One turn: the agent proposes, the engine scores", """
[0:45] Here's the game. On each turn a player claims an empty neighboring cell, reinforces one of their cells, or attacks. Cells that get cut off from home lose strength, and you win by capturing the enemy's home or by owning more cells after twelve turns each.

This is turn 11 of a real training game. The agent is coral, and teal has just taken B3. The agent proposed three moves, and the engine scored each after teal's best reply. The attack scored highest, so the agent took B3, and it went on to win ten cells to eight.

It also cited lesson L6, but citing a lesson doesn't make it good: L6 was later retired with one win and four losses.
""")
turn = json.loads((ROOT / "results/traces/s1-B-g016.json").read_text())["turns"][10]
text(s, 0.6, 1.7, 12.1, 0.8, [
    ("Each turn: claim an empty neighbor, reinforce, or attack. Cells cut off from home lose strength.", {"size": 15, "after": 3}),
    ("Win by capturing the enemy home, or by owning more cells after 12 turns each.", {"size": 15}),
], color=INK_2)
text(s, 0.95, 2.65, 2.9, 0.3, "Turn 11: coral (agent) to move", size=13, bold=True)
text(s, 4.95, 2.65, 2.9, 0.3, "After attack A3→B3", size=13, bold=True)
board(s, 0.95, 3.3, turn["state_before"], mark="B3")
board(s, 4.95, 3.3, turn["state_after"], mark="B3")
arrow(s, 3.95, 4.72, 4.5, 4.72)
text(s, 0.95, 6.35, 6.9, 0.35, "Number = strength, * = home. Attack power 2 (A3 plus support from B2) beats strength 1.",
     size=12, color=INK_2)
table(s, 8.3, 2.65, 4.4, [["Candidate", "Score after reply"]] + [
    [c["move"][0].upper() + c["move"][1:].replace("->", "→")
     + (" (picked)" if c["move"].startswith("attack") else ""), f"{c['score_2ply']:+d}".replace("-", "−")]
    for c in sorted(turn["candidate_scores"], key=lambda c: -c["score_2ply"])
], [2.7, 1.7], size=13, row_h=0.45, highlight=1)
card(s, 8.3, 4.7, 4.4, 1.95, "Lesson cited: L6", [
    ("Block the opponent's expansion into the central corridor (C and D)", {"after": 6}),
    ("Later retired: 1 win, 4 losses", {"bold": True, "color": CORAL}),
], accent=CORAL, size=14)
text(s, 0.6, 6.95, 11, 0.3, "Saved game s1-B-g016 (training). The agent moved first and won 10 cells to 8.", size=12, color=MUTED)

# 5. Key decision: the LLM judges ------------------------------------------
s = slide(5, "Key decision", "The LLM judges; code calculates", """
[1:00] The most important design decision came from watching the agent fail. With a single LLM call per turn, it made illegal moves twelve and a half percent of the time. Whenever I asked the LLM to do arithmetic, it got it wrong.

So I stopped asking it to. Read-only tools now do the math: previewing an attack, checking supply, and scanning for threats. The legal moves are always in the prompt. On top of that is the tree-of-thought step you just saw: the LLM proposes three different moves, the engine scores each one two moves deep, and the LLM picks one.

That brought illegal moves down to between one and three percent. The ablation in the main experiment backs this up: take tree-of-thought away, and illegal moves jump back to twenty percent. The LLM now does only what needs judgment: which plans to try, which one to pick, and what lesson to draw afterward.
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

# 6. Key decision: honest lessons ------------------------------------------
s = slide(6, "Key decision", "Keeping lessons honest", """
[0:45] The second big risk is memory poisoning, where an agent writes itself bad advice and then believes it. So every lesson has to pass two checks.

First, the review crew only sees a stripped trace: moves and boards, with none of the player's reasoning. The player can't argue its way into a lesson, and the critic rejects anything the boards don't show.

Second, outcomes decide. A lesson only gets credit or blame when it was retrieved and the player actually cited it. Its confidence is wins plus one over games plus two, so one lucky game can't make it look perfect. In training, the crew wrote ten lessons, and this rule retired eight of them.
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

# 7. Why lessons, not RL? --------------------------------------------------
s = slide(7, "Key decision", "Why lessons, not reinforcement learning?", """
[0:45] Why not reinforcement learning? RL updates a policy's weights over thousands or millions of games, and it would very likely play this five-by-five board better than my agent does. I'm not claiming otherwise.

But my users want strategies they can read, check, and argue with, and an RL policy can't explain itself. And each LLM game takes about nine minutes, so millions of games were never an option. FrontLine keeps its learning in memory instead: the LLM writes a lesson in plain English, and game results decide whether it stays. That puts it in the same family as Reflexion, ExpeL, and Voyager. The short version: RL learns to win, and FrontLine learns to explain what wins.
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

# 8. Evaluation ------------------------------------------------------------
s = slide(8, "Evaluation", "Four conditions against a greedy bot", """
[0:45] To test the system, the agent played a greedy bot that always takes the move with the best immediate score, and the first move alternated every game.

I ran four conditions. A is the baseline, with no lessons. B is training: the lesson store starts empty and the crew reviews every game. C takes B's final store and freezes it, so it measures what was learned without any learning during the test. And D is C without tree-of-thought, as an ablation. Comparing C to A tells us whether learning helped, and comparing C to D tells us whether tree-of-thought helped.
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

# 9. Results ---------------------------------------------------------------
s = slide(9, "Results", "Tree-of-thought helps; lessons didn't raise wins yet", """
[1:30] These results come from the main run, which was fifty games over seven and a half hours, with no errors.

Tree-of-thought is the clearest result. With it, illegal moves stayed between one and three percent. Without it, in condition D, they jumped to twenty percent, and the agent finished with fewer cells.

The honest answer on lessons is that the frozen store didn't raise the win rate. C won none of its ten games, and A won one. C did end with slightly more cells and picked the engine's top-scored move more often, but that isn't the same as winning. Partly, the tally did its job almost too well: eight of ten lessons were retired in training, so C played with just two unproven lessons.

Training, condition B, did best, at five wins out of twenty, but every one of those wins came when the agent moved first. Across all fifty games, the agent won six of the twenty-five it started and none of the twenty-five where it moved second. With only ten to twenty games per condition, these are trends, not statistically significant results.
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

# 10. Repository ------------------------------------------------------------
s = slide(10, "Repository", "github.com/moistvonlipwig/FrontLine-Strategy-Agents", """
[0:30] Everything is in the public GitHub repository: the code, the rules, twenty-six tests, and the final report. The results folder has the experiment data, the charts, and one sample game per condition, including the one I showed you. You can install it and play a full game without an LLM in under a minute. LLM games need Ollama and the Qwen3 32B model.
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

# 11. Reflection -----------------------------------------------------------
s = slide(11, "Reflection", "What worked, what didn't, what's next", """
[1:15] To wrap up: what worked. Tools and tree-of-thought nearly eliminated illegal moves, and the ablation shows tree-of-thought is the reason. Every move can be traced, and bad lessons get caught and retired without a person stepping in.

What hasn't worked yet is win rate. Lessons change how the agent plays but haven't made it win more; in twenty training games, bad lessons were retired faster than good ones turned up. The samples are small, moving second against a greedy bot is very hard, and this is one model on one game.

Next, I want to run a hundred or more training games with a second seed, add a score guard so the LLM can't overrule a much better move, and test against stronger opponents like MCTS.

My biggest takeaway is that every time I asked the LLM to calculate, it failed, and every time code took over, the system got better. Give the LLM judgment, and give code the math.

My field is modeling and simulation, and this loop fits training simulations: an opposing force whose tactics instructors can read and audit, with the review crew as an automated after-action review. I'm planning an I/ITSEC paper on it.

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

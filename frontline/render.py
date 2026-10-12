# Copyright (c) 2026 Chris Teli
# SPDX-License-Identifier: MIT

"""Terminal board printer. Coral = C, Teal = T, number = strength, * = home."""

from .schemas import COLS, ROWS, GameState

COLOR = {"coral": "\033[38;5;209m", "teal": "\033[38;5;37m"}
RESET = "\033[0m"


def render(state: GameState, color: bool = True) -> str:
    homes = set(state.homes.values())
    lines = ["    " + "   ".join(COLS)]
    for r in ROWS:
        row = []
        for c in COLS:
            cell = state.board[c + r]
            if cell.owner is None:
                txt = " . "
            else:
                txt = f"{cell.owner[0].upper()}{cell.strength}{'*' if c + r in homes else ' '}"
                if color:
                    txt = COLOR[cell.owner] + txt + RESET
            row.append(txt)
        lines.append(f"{r}  " + " ".join(row))
    lines.append(f"turn {state.turn}, {state.to_move} to move")
    return "\n".join(lines)

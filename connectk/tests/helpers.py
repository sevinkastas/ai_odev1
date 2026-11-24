"""Testler için yardımcı: tahtayı çizerek durum kurmak."""

from game import State, EMPTY, MAX, MIN


def state_from_grid(game, rows):
    """rows: EN ÜST satır önce gelen stringler. X = MAX, O = MIN, . = boş.
    Sıra, taş sayılarından türetilir (eşitse MAX). Havada taş olmamalı."""
    R, C = game.R, game.C
    assert len(rows) == R and all(len(row) == C for row in rows)
    code = {".": EMPTY, "X": MAX, "O": MIN}
    cells = [EMPTY] * (R * C)
    for i, row in enumerate(rows):
        r = R - 1 - i                      # ilk string en üst satır
        for c, ch in enumerate(row):
            cells[r * C + c] = code[ch]
    heights = []
    for c in range(C):
        h = 0
        while h < R and cells[h * C + c] != EMPTY:
            h += 1
        assert all(cells[r * C + c] == EMPTY for r in range(h, R)), "havada taş var"
        heights.append(h)
    n_x, n_o = cells.count(MAX), cells.count(MIN)
    to_move = MAX if n_x == n_o else MIN
    return State(tuple(cells), tuple(heights), to_move, None, EMPTY, n_x + n_o)

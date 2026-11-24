"""Aşama 0 testleri: oyun modeli ve perft.
Çalıştırma (connectk/ klasöründe):  python -m unittest -v
"""

import unittest

from game import Game, perft, MAX, MIN, BLOCK
from tests.helpers import state_from_grid


class TestPerft(unittest.TestCase):
    def test_empty_board_is_C_pow_n(self):
        # K = 5 iken ilk dizi en erken 9. hamlede oluşur, bu yüzden n <= 8 için perft = C^n.
        g = Game(6, 8, 5, 2)
        s = g.initial_state()
        for n in range(1, 5):
            self.assertEqual(perft(g, s, n), 8 ** n)

    def test_half_full_position_by_hand(self):
        # 0 0 1 1 2 2 3 3: MAX alt satırda 0-3, MIN üstünde 0-3. Sıra MAX'te.
        # n=2: MAX'in 8 hamlesinden '4' oyunu bitirir (1 yaprak),
        #      diğer 7 hamlenin her birine MIN 8 cevap verir -> 7*8 + 1 = 57.
        g = Game(6, 8, 5, 2)
        s = g.from_moves("0 0 1 1 2 2 3 3")
        self.assertEqual(perft(g, s, 1), 8)
        self.assertEqual(perft(g, s, 2), 57)

    def test_full_column_reduces_perft(self):
        g = Game(6, 8, 5, 2)
        s = g.from_moves("0 0 0 0 0 0")    # sütun 0 doldu (dikey 5'li yok: X O X O X O)
        self.assertEqual(perft(g, s, 1), 7)
        self.assertEqual(perft(g, s, 2), 49)


class TestActionsAndResult(unittest.TestCase):
    def test_full_column_removed_from_actions(self):
        g = Game(6, 8, 5, 2)
        s = g.from_moves("0 0 0 0 0")
        self.assertIn(0, g.actions(s))
        s = g.result(s, 0)
        self.assertNotIn(0, g.actions(s))
        self.assertEqual(g.actions(s), [1, 2, 3, 4, 5, 6, 7])

    def test_result_does_not_modify_state(self):
        g = Game(6, 8, 5, 2)
        s = g.from_moves("3 4 3")
        before = (s.cells, s.heights, s.to_move, s.n_moves)
        child = g.result(s, 3)
        self.assertEqual((s.cells, s.heights, s.to_move, s.n_moves), before)
        self.assertIsNot(child.cells, s.cells)
        self.assertEqual(child.heights[3], 3)
        self.assertEqual(child.to_move, MAX)   # 4 hamle oynandı, sıra yine MAX'te

    def test_illegal_move_raises(self):
        g = Game(6, 8, 5, 2)
        with self.assertRaises(ValueError):
            g.from_moves("0 0 0 0 0 0 0")       # 7. taş dolu sütuna


class TestMisereTerminal(unittest.TestCase):
    """V = 2: K'lı diziyi yapan kaybeder."""

    def setUp(self):
        self.g = Game(6, 8, 5, 2)

    def test_horizontal_maker_loses(self):
        s = self.g.from_moves("0 0 1 1 2 2 3 3")
        self.assertFalse(self.g.is_terminal(s))
        s = self.g.result(s, 4)                 # MAX alt satırda 0-4
        self.assertTrue(self.g.is_terminal(s))
        self.assertEqual(s.line_maker, MAX)
        self.assertEqual(self.g.utility(s), -1)  # Misère: MAX kaybeder

    def test_vertical_maker_loses(self):
        s = self.g.from_moves("0 1 0 1 0 1 0 1 2")
        self.assertFalse(self.g.is_terminal(s))
        s = self.g.result(s, 1)                 # MIN sütun 1'de 5 taş
        self.assertTrue(self.g.is_terminal(s))
        self.assertEqual(s.line_maker, MIN)
        self.assertEqual(self.g.utility(s), +1)  # Misère: MIN kaybeder, MAX kazanır

    def test_diagonal_up_right(self):
        # MAX (X) (0,0) (1,1) (2,2) (3,3)'te; sütun 4'e oynayınca (4,4) dolar -> "/" 5'li.
        s = state_from_grid(self.g, [
            "........",
            "........",
            "...XO...",
            "..XOX...",
            ".XOXO...",
            "XOOXO...",
        ])
        self.assertEqual(s.to_move, MAX)
        s = self.g.result(s, 4)
        self.assertTrue(self.g.is_terminal(s))
        self.assertEqual(s.line_maker, MAX)
        self.assertEqual(self.g.utility(s), -1)

    def test_diagonal_up_left(self):
        # MIN (O) (0,7) (1,6) (2,5) (3,4)'te; sütun 3'e oynayınca (4,3) dolar -> "\" 5'li.
        s = state_from_grid(self.g, [
            "........",
            "........",
            "...XO...",
            "...XXO..",
            "...OXXO.",
            "X..XOOXO",
        ])
        self.assertEqual(s.to_move, MIN)
        s = self.g.result(s, 3)
        self.assertTrue(self.g.is_terminal(s))
        self.assertEqual(s.line_maker, MIN)
        self.assertEqual(self.g.utility(s), +1)

    def test_misere_flips_standard_utility(self):
        moves = "0 0 1 1 2 2 3 3 4"
        self.assertEqual(Game(6, 8, 5, 0).utility(Game(6, 8, 5, 0).from_moves(moves)), +1)
        self.assertEqual(self.g.utility(self.g.from_moves(moves)), -1)

    def test_full_board_is_draw(self):
        g = Game(R=2, C=2, K=5, V=2)            # küçük tahta: kimse 5 dizemez
        s = g.from_moves("0 0 1 1")
        self.assertTrue(g.is_terminal(s))
        self.assertEqual(g.utility(s), 0)
        self.assertEqual(g.actions(s), [])


class TestOtherVariants(unittest.TestCase):
    """Turnuvada varyant değişebilir: silindir ve engelli de doğru olmalı."""

    def test_cylinder_wraps_horizontally(self):
        moves = "6 6 7 7 0 0 1 1 2"             # MAX alt satırda 6,7,0,1,2
        self.assertTrue(Game(6, 8, 5, 1).is_terminal(Game(6, 8, 5, 1).from_moves(moves)))
        self.assertFalse(Game(6, 8, 5, 0).is_terminal(Game(6, 8, 5, 0).from_moves(moves)))

    def test_blocked_cells_stop_stones(self):
        g = Game(6, 8, 5, 3, d=52)
        s = g.initial_state()
        self.assertEqual(len(g.blocked), 2)
        for (r, c) in g.blocked:
            self.assertEqual(s.cells[r * g.C + c], BLOCK)
            self.assertGreaterEqual(s.heights[c], r + 1)   # taş engelin üstüne düşer
            child = g.result(s, c) if s.heights[c] < g.R else None
            if child is not None:
                rr = s.heights[c]
                self.assertEqual(child.cells[rr * g.C + c], MAX)


if __name__ == "__main__":
    unittest.main()

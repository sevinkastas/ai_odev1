"""Aşama 1 testleri: minimax."""

import unittest

from game import Game, MIN
from search import minimax_decision, choose_move


class TestMinimax(unittest.TestCase):
    def test_node_count_depth2_empty(self):
        # Boş tahtada derinlik 2: kök + C çocuk + C^2 torun = 1 + 8 + 64
        g = Game(6, 8, 5, 2)
        _, _, stats = minimax_decision(g, g.initial_state(), 2)
        self.assertEqual(stats.nodes, 1 + 8 + 64)

    def test_deterministic(self):
        g = Game(6, 8, 5, 2)
        s = g.from_moves("3 4 4 3 5 2 2 5 6 1 1 6 0 7 7 0")
        self.assertEqual(choose_move(g, s, 4), choose_move(g, s, 4))

    def test_empty_board_tie_break_is_center(self):
        g = Game(6, 8, 5, 2)
        self.assertEqual(choose_move(g, g.initial_state(), 2), 3)

    # --- Misère (benim varyantım) ---
    def test_misere_max_avoids_making_line(self):
        # MAX alt satırda 0-3: sütun 4 intihar. Hiçbir derinlikte 4 seçilmemeli.
        g = Game(6, 8, 5, 2)
        s = g.from_moves("0 0 1 1 2 2 3 3")
        for depth in (1, 2, 4):
            move, value, _ = minimax_decision(g, s, depth)
            self.assertNotEqual(move, 4)
            self.assertGreaterEqual(value, 0)

    def test_misere_min_avoids_making_line(self):
        # MIN'in sütun 1'de 4 taşı var ve sıra MIN'de: sütun 1 MIN için intihar.
        g = Game(6, 8, 5, 2)
        s = g.from_moves("0 1 0 1 0 1 0 1 2")
        self.assertEqual(s.to_move, MIN)
        for depth in (1, 2, 4):
            move, value, _ = minimax_decision(g, s, depth)
            self.assertNotEqual(move, 1)
            self.assertLessEqual(value, 0)       # MIN gözüyle kaybetmeyen değer

    # --- Standart kural (turnuvada varyant değişirse) ---
    def test_standard_max_takes_win(self):
        g = Game(6, 8, 5, 0)
        s = g.from_moves("0 0 1 1 2 2 3 3")
        move, value, _ = minimax_decision(g, s, 2)
        self.assertEqual((move, value), (4, 1))

    def test_standard_max_blocks_min(self):
        g = Game(6, 8, 5, 0)
        s = g.from_moves("7 0 7 1 6 2 6 3")      # MIN alt satırda 0-3, sıra MAX'te
        move, value, _ = minimax_decision(g, s, 2)
        self.assertEqual((move, value), (4, 0))


if __name__ == "__main__":
    unittest.main()

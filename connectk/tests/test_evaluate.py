"""Aşama 3 testleri: pencereler, öznitelikler, Eval aralığı, simetri, Misère işaretleri."""

import unittest

from game import Game, State, random_positions
from evaluate import Evaluator, make_windows, WEIGHTS_STANDARD
from search import minimax_decision


def mirror(game, s):
    """Sol-sağ ayna: sütun c <-> C-1-c."""
    R, C = game.R, game.C
    cells = tuple(s.cells[r * C + (C - 1 - c)] for r in range(R) for c in range(C))
    return State(cells, tuple(reversed(s.heights)), s.to_move, None, s.line_maker, s.n_moves)


class TestWindows(unittest.TestCase):
    def test_window_counts(self):
        # 6x8, K=5: yatay 6*4 + dikey 2*8 + iki çapraz 2*(2*4) = 56
        self.assertEqual(len(make_windows(Game(6, 8, 5, 2))), 56)
        # Silindir: yatay 6*8 (her başlangıç sütunu) + dikey 16 + çapraz 2*(2*8) = 96
        self.assertEqual(len(make_windows(Game(6, 8, 5, 1))), 96)
        # Engelli: engel içeren pencereler atlanır
        self.assertLess(len(make_windows(Game(6, 8, 5, 3, d=52))), 56)


class TestEval(unittest.TestCase):
    def setUp(self):
        self.g = Game(6, 8, 5, 2)
        self.ev = Evaluator(self.g)

    def test_features_by_hand(self):
        # X X X X . alt satır, O O O O . üstünde, sıra MAX'te
        s = self.g.from_moves("0 0 1 1 2 2 3 3")
        f = self.ev.features(s)
        self.assertEqual((f["max_k1"], f["max_k2"], f["min_k1"], f["min_k2"]), (1, 1, 1, 1))
        # MAX'in oynanabilir (0,4) hücresi kendi 5'lisini tamamlar -> 7 güvenli;
        # MIN'in zehirli hücresi (1,4) henüz oynanabilir değil -> 8 güvenli. Fark -1.
        self.assertEqual(f["safe"], -1)
        self.assertEqual(f["center"], 0)

    def test_eval_strictly_inside_unit_interval(self):
        for s in random_positions(self.g, 40, seed=3, max_plies=40):
            self.assertLess(abs(self.ev(self.g, s)), 1.0)
        extreme = Evaluator(self.g, (100, 100, 0, 0, 0, 0))   # dev ağırlık bile 1'e ulaşmaz
        s = self.g.from_moves("0 0 1 1 2 2 3 3")
        self.assertLess(abs(extreme(self.g, s)), 1.0)

    def test_mirror_symmetry(self):
        for s in random_positions(self.g, 20, seed=4):
            self.assertAlmostEqual(self.ev(self.g, s), self.ev(self.g, mirror(self.g, s)))

    def test_misere_sign_is_flipped(self):
        # MAX'in 4'lü + boş penceresi: Misère'de kötü (Eval < 0), standart ağırlıkla iyi (Eval > 0)
        s = self.g.from_moves("0 7 1 7 2 6 3")             # X X X X . alt satır, sıra MIN'de
        self.assertLess(self.ev(self.g, s), 0)
        std = Game(6, 8, 5, 0)
        self.assertGreater(Evaluator(std, WEIGHTS_STANDARD)(std, std.from_moves("0 7 1 7 2 6 3")), 0)

    def test_terminal_checked_before_eval(self):
        # Derinlik 1'de 8 çocuktan biri (sütun 4) terminal: Eval yalnızca 7 kez çağrılmalı.
        calls = []

        def counting_eval(game, s):
            calls.append(s)
            return 0
        s = self.g.from_moves("0 0 1 1 2 2 3 3")
        minimax_decision(self.g, s, 1, counting_eval)
        self.assertEqual(len(calls), 7)


if __name__ == "__main__":
    unittest.main()

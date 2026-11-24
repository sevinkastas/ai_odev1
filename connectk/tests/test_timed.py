"""Aşama 4 testleri: Zobrist, yer değiştirme tablosu, zaman sınırı / iteratif derinleşme, ufuk uzatması."""

import math
import random
import time
import unittest

from game import Game, random_positions
from evaluate import Evaluator
from search import TimedSearch, Zobrist, alphabeta_decision, order_tactical, noise_eval

HORIZON = "1 4 3 3 3 3 4 3 3 4 4 4 1 4 2 5 2 0 2 1 5 5 1 5 1 1 0 6 0 6 2 0 7 6 7 0"


class TestZobrist(unittest.TestCase):
    def test_incremental_equals_from_scratch(self):
        g = Game(6, 8, 5, 2)
        z = Zobrist(g)
        rng = random.Random(0)
        for _ in range(20):
            s = g.initial_state()
            key = z.key(s)
            while not g.is_terminal(s):
                a = rng.choice(g.actions(s))
                key = z.update(key, s, a)
                s = g.result(s, a)
                self.assertEqual(key, z.key(s))

    def test_side_to_move_in_key(self):
        g = Game(6, 8, 5, 2)
        z = Zobrist(g)
        s = g.from_moves("3 4")
        flipped = s._replace(to_move=3 - s.to_move)
        self.assertNotEqual(z.key(s), z.key(flipped))

    def test_transposition_same_key(self):
        # MAX 3, MIN 5, MAX 4  ile  MAX 4, MIN 5, MAX 3 aynı konum -> aynı anahtar
        g = Game(6, 8, 5, 2)
        z = Zobrist(g)
        self.assertEqual(z.key(g.from_moves("3 5 4")), z.key(g.from_moves("4 5 3")))


class TestTimedSearch(unittest.TestCase):
    def setUp(self):
        self.g = Game(6, 8, 5, 2)
        self.ev = Evaluator(self.g)

    def test_tt_value_equals_plain_alphabeta(self):
        # Tablo açıkken sabit derinlikteki değer, tablosuz α-β ile aynı olmalı (bayraklar doğruysa).
        for s in random_positions(self.g, 12, seed=52):
            plain = alphabeta_decision(self.g, s, 4, noise_eval, order_tactical)[1]
            ts = TimedSearch(self.g, noise_eval, use_tt=True, extend=False)
            self.assertEqual(ts._root(s, 4, None)[1], plain)

    def test_respects_time_limit(self):
        s = self.g.from_moves("3 4 4 3 5 2 2 5")
        t0 = time.perf_counter()
        r = TimedSearch(self.g, self.ev).search(s, 0.3)
        self.assertLess(time.perf_counter() - t0, 0.4)
        self.assertIn(r.move, self.g.actions(s))
        self.assertGreaterEqual(r.depth, 1)

    def test_partial_iteration_discarded(self):
        # Çok kısa süre + her düğümde süre kontrolü: yarım kalan derinlik atılır,
        # dönen hamle son TAMAMLANAN derinliğin hamlesidir.
        s = self.g.from_moves("3 4 4 3 5 2 2 5")
        r = TimedSearch(self.g, self.ev, check_every=1).search(s, 0.02)
        self.assertTrue(r.depths_log)
        last_depth, last_move = r.depths_log[-1][0], r.depths_log[-1][1]
        self.assertEqual((r.depth, r.move), (last_depth, last_move))

    def test_single_legal_move(self):
        g = Game(R=6, C=2, K=5, V=2)
        s = g.from_moves("0 0 0 0 0 0")         # sütun 0 dolu, tek hamle: 1
        self.assertEqual(TimedSearch(g, Evaluator(g)).search(s, 0.5).move, 1)

    def test_unbounded_search_stops_at_full_board(self):
        g = Game(R=2, C=2, K=5, V=2)
        r = TimedSearch(g, Evaluator(g)).search(g.initial_state(), math.inf)
        self.assertEqual(r.value, 0)            # küçük tahta: beraberlik kanıtlanır


class TestHorizon(unittest.TestCase):
    def test_is_forcing(self):
        std = Game(6, 8, 5, 0)                   # standart: oynanabilir kazanma hücresi var
        self.assertTrue(TimedSearch(std, Evaluator(std)).is_forcing(std.from_moves("0 0 1 1 2 2 3 3")))
        tiny = Game(R=1, C=3, K=2, V=2)          # Misère: MAX'in tek hamlesi (orta) intihar -> zorlanmış
        self.assertTrue(TimedSearch(tiny, Evaluator(tiny)).is_forcing(tiny.from_moves("0 2")))
        g = Game(6, 8, 5, 2)                     # 7 güvenli hamle -> sakin
        self.assertFalse(TimedSearch(g, Evaluator(g)).is_forcing(g.from_moves("0 0 1 1 2 2 3 3")))

    def test_extension_fixes_documented_horizon_example(self):
        # Raporlanan konum: derinlik 4'te uzatmasız arama 7 (kanıtlanmış kayıp), uzatmalı arama 6 seçer.
        g = Game(6, 8, 5, 2)
        ev = Evaluator(g)
        s = g.from_moves(HORIZON)
        plain = TimedSearch(g, ev, extend=False).search(s, math.inf, max_depth=4)
        ext = TimedSearch(g, ev, extend=True).search(s, math.inf, max_depth=4)
        self.assertEqual((plain.move, ext.move), (7, 6))


if __name__ == "__main__":
    unittest.main()

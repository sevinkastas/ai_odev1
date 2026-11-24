"""Aşama 2 testleri: α-β = minimax, budama, sıralama.
Kontrol noktası 2 (β kesme koşulunda bir karakter değişir) için:
  - '>=' -> '<=' gibi değişiklik DEĞERİ bozar   -> test_alphabeta_equals_minimax yakalar
  - '>=' -> '>'  değişikliği yalnızca DÜĞÜM sayısını artırır -> test_node_count_regression yakalar
"""

import unittest

from game import Game, random_positions
from search import (minimax_decision, alphabeta_decision, ORDERINGS,
                    order_tactical, zero_eval, noise_eval)

FIXED = "3 4 4 3 5 2 2 5 6 1 1 6 0 7 7 0"   # positions.txt P5


def exact_value(game, s, depth, evaluate):
    """Bir durumun düz minimax değeri (terminal ise utility)."""
    if game.is_terminal(s):
        return game.utility(s)
    return minimax_decision(game, s, depth, evaluate)[1]


class TestAlphaBeta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = Game(6, 8, 5, 2)
        cls.positions = random_positions(cls.g, 12, seed=52)

    def test_alphabeta_equals_minimax(self):
        # Gürültülü Eval: her yaprak farklı değer alır, böylece eşitlik testi gerçekten bir şey kanıtlar.
        g = self.g
        for evaluate in (noise_eval, zero_eval):
            for s in self.positions:
                _, mm_value, mm_stats = minimax_decision(g, s, 4, evaluate)
                for name, order in ORDERINGS.items():
                    move, ab_value, ab_stats = alphabeta_decision(g, s, 4, evaluate, order)
                    self.assertEqual(ab_value, mm_value, name)
                    # Seçilen HAMLENİN gerçek değeri de kök değerine eşit olmalı
                    self.assertEqual(exact_value(g, g.result(s, move), 3, evaluate), mm_value, name)
                    # α-β hiçbir konumda minimax'tan fazla düğüme bakmaz
                    self.assertLessEqual(ab_stats.nodes, mm_stats.nodes, name)

    def test_node_count_regression(self):
        # Eval = 0 ile eşit değerler çok olur; '>=' yerine '>' yazılırsa kesme azalır ve sayı değişir.
        g = self.g
        s = g.from_moves(FIXED)
        expected = {"none": 222, "center_out": 222, "tactical_center_out": 222}
        for name, order in ORDERINGS.items():
            self.assertEqual(alphabeta_decision(g, s, 4, zero_eval, order)[2].nodes, expected[name], name)

    def test_alphabeta_standard_variant(self):
        g = Game(6, 8, 5, 0)
        for s in random_positions(g, 6, seed=7):
            mm = minimax_decision(g, s, 4, noise_eval)[1]
            self.assertEqual(alphabeta_decision(g, s, 4, noise_eval, order_tactical)[1], mm)


class TestOrdering(unittest.TestCase):
    def test_misere_suicide_last(self):
        g = Game(6, 8, 5, 2)
        s = g.from_moves("0 0 1 1 2 2 3 3")        # MAX için 4 intihar
        self.assertEqual(order_tactical(g, s)[-1], 4)

    def test_standard_win_then_block_first(self):
        g = Game(6, 8, 5, 0)
        s = g.from_moves("0 0 1 1 2 2 3 3")        # MAX 4'e oynarsa kazanır
        self.assertEqual(order_tactical(g, s)[0], 4)
        s = g.from_moves("7 0 7 1 6 2 6 3")        # MIN 4'e oynarsa kazanır -> MAX engeller
        self.assertEqual(order_tactical(g, s)[0], 4)

    def test_orderings_are_permutations_of_actions(self):
        g = Game(6, 8, 5, 2)
        for s in random_positions(g, 5, seed=1):
            for order in ORDERINGS.values():
                self.assertEqual(sorted(order(g, s)), g.actions(s))


if __name__ == "__main__":
    unittest.main()

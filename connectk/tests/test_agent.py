"""Aşama 5 testleri: komut satırı protokolü ve uç durumlar."""

import io
import os
import subprocess
import sys
import unittest

from agent import Agent, run
from game import Game

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestProtocol(unittest.TestCase):
    def test_cli_moves_unknown_line_and_quit(self):
        # Gerçek süreç: MOVES (ilk hamle), tanınmayan satır, MOVES 3 3 4, QUIT
        inp = "MOVES\nSıra sizde\nMOVES 3 3 4\nQUIT\n"
        proc = subprocess.run([sys.executable, "agent.py", "--R", "6", "--C", "8", "--K", "5",
                               "--V", "2", "--seed", "7", "--time", "0.2"],
                              input=inp, capture_output=True, text=True, encoding="utf-8",
                              cwd=HERE, timeout=30)
        self.assertEqual(proc.returncode, 0)
        out = proc.stdout.split()
        self.assertEqual(len(out), 2)                 # yalnızca iki hamle; log stdout'a karışmamış
        g = Game(6, 8, 5, 2)
        self.assertIn(int(out[0]), g.actions(g.initial_state()))
        self.assertIn(int(out[1]), g.actions(g.from_moves("3 3 4")))
        self.assertIn("tanınmayan", proc.stderr)      # debug çıktısı stderr'de

    def test_run_loop_in_memory(self):
        agent = Agent(6, 8, 5, 2, seed=7, time_limit=0.1)
        out = io.StringIO()
        run(agent, io.StringIO("\nMOVES 0\nQUIT\nMOVES 1\n"), out)
        self.assertEqual(len(out.getvalue().split()), 1)   # QUIT'ten sonrası okunmaz


class TestAgentSafety(unittest.TestCase):
    def test_full_board_does_not_crash(self):
        agent = Agent(R=2, C=2, K=5, V=2, seed=7, time_limit=0.1)
        self.assertIsInstance(agent.choose([0, 0, 1, 1]), int)   # tahta dolu

    def test_illegal_history_does_not_crash(self):
        agent = Agent(6, 8, 5, 2, seed=7, time_limit=0.1)
        move = agent.choose([0, 0, 0, 0, 0, 0, 0])               # 7. taş dolu sütuna
        self.assertIn(move, range(1, 8))

    def test_extreme_variants_all_V(self):
        # Turnuva günü sürprizi: K=5, R=7, C=8 ve her V değeri
        for V in range(4):
            agent = Agent(R=7, C=8, K=5, V=V, seed=7, time_limit=0.15)
            g = agent.game
            for moves in ([], [3, 3, 4, 4, 5]):
                move = agent.choose(moves)
                self.assertIn(move, g.actions(g.from_moves(moves)), f"V={V}")

    def test_misere_agent_avoids_suicide(self):
        agent = Agent(6, 8, 5, 2, seed=7, time_limit=0.2)
        self.assertNotEqual(agent.choose([0, 0, 1, 1, 2, 2, 3, 3]), 4)


if __name__ == "__main__":
    unittest.main()

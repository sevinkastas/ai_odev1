"""Rapor için ölçüm scriptleri. Her aşama ayrı bir alt komut:

    python experiments.py stage0            # perft tablosu
    python experiments.py stage0 --max-n 5
    python experiments.py stage1            # minimax: hamle, düğüm, b_etkin

Çıktılar ekrana Markdown tablosu olarak basılır ve results/ klasörüne CSV olarak yazılır.
Varyant parametreleri komut satırından değiştirilebilir (--R --C --K --V --d).
"""

import argparse
import csv
import os
import sys
import time

from game import Game, perft
from search import minimax_decision

sys.stdout.reconfigure(encoding="utf-8")   # Windows konsolunda Türkçe karakterler bozulmasın

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


# ----------------------------------------------------------------------
# Ortak yardımcılar
# ----------------------------------------------------------------------
def load_positions(path="positions.txt"):
    """positions.txt -> [(ad, hamle_listesi), ...]"""
    here = os.path.dirname(os.path.abspath(__file__))
    out = []
    with open(os.path.join(here, path), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name, moves = line.split(":", 1)
            out.append((name.strip(), [int(x) for x in moves.split()]))
    return out


def write_csv(name, header, rows):
    os.makedirs(RESULTS, exist_ok=True)
    path = os.path.join(RESULTS, name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"\n-> {path}")


def print_table(header, rows):
    print("| " + " | ".join(str(h) for h in header) + " |")
    print("|" + "---|" * len(header))
    for row in rows:
        print("| " + " | ".join(str(x) for x in row) + " |")


# ----------------------------------------------------------------------
# Aşama 0: perft
# ----------------------------------------------------------------------
def stage0(game, args):
    starts = [("boş", [])] + load_positions()
    header = ["konum", "n", "düğüm (yaprak)", "C^n", "süre (s)"]
    rows = []
    for name, moves in starts:
        s = game.from_moves(moves)
        max_n = args.max_n + 2 if not moves else args.max_n   # boş tahtada biraz daha derin
        for n in range(1, max_n + 1):
            t0 = time.perf_counter()
            leaves = perft(game, s, n)
            dt = time.perf_counter() - t0
            rows.append([name, n, leaves, game.C ** n, f"{dt:.3f}"])
    print_table(header, rows)
    write_csv("stage0_perft.csv", header, rows)


# ----------------------------------------------------------------------
# Aşama 1: minimax, 5 konum x derinlik 2/4/6
# ----------------------------------------------------------------------
def stage1(game, args):
    header = ["konum", "derinlik", "hamle", "değer", "düğüm", "b_etkin", "süre (s)"]
    rows = []
    for name, moves in load_positions()[:5]:
        s = game.from_moves(moves)
        for depth in (2, 4, 6):
            t0 = time.perf_counter()
            move, value, stats = minimax_decision(game, s, depth)
            dt = time.perf_counter() - t0
            b_eff = stats.nodes ** (1 / depth)
            rows.append([name, depth, move, value, stats.nodes, f"{b_eff:.2f}", f"{dt:.2f}"])
            print(f"  {name} d={depth}: hamle {move}, {stats.nodes} düğüm", file=sys.stderr)
    print_table(header, rows)
    write_csv("stage1_minimax.csv", header, rows)


# ----------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["stage0", "stage1"])
    p.add_argument("--R", type=int, default=6)
    p.add_argument("--C", type=int, default=8)
    p.add_argument("--K", type=int, default=5)
    p.add_argument("--V", type=int, default=2)
    p.add_argument("--d", type=int, default=52)
    p.add_argument("--max-n", type=int, default=4)
    args = p.parse_args()
    game = Game(args.R, args.C, args.K, args.V, args.d)
    print(f"Varyant (R, C, K, V, d) = ({game.R}, {game.C}, {game.K}, {game.V}, {game.d})\n")
    {"stage0": stage0, "stage1": stage1}[args.stage](game, args)


if __name__ == "__main__":
    main()

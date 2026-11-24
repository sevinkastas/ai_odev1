"""Rapor için ölçüm scriptleri. Her aşama ayrı bir alt komut:

    python experiments.py stage0            # perft tablosu
    python experiments.py stage0 --max-n 5
    python experiments.py stage1            # minimax: hamle, düğüm, b_etkin
    python experiments.py stage2            # 50 konum: minimax vs α-β, 3 sıralama, grafik

Çıktılar ekrana Markdown tablosu olarak basılır ve results/ klasörüne CSV olarak yazılır.
Varyant parametreleri komut satırından değiştirilebilir (--R --C --K --V --d).
"""

import argparse
import csv
import math
import os
import sys
import time

from game import Game, perft, random_positions
from search import (minimax_decision, alphabeta_decision, ORDERINGS,
                    zero_eval, noise_eval)

sys.stdout.reconfigure(encoding="utf-8")   # Windows konsolunda Türkçe karakterler bozulmasın
sys.stderr.reconfigure(encoding="utf-8")

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
# Aşama 2: 50 rastgele konumda minimax vs α-β (3 sıralama)
# ----------------------------------------------------------------------
EVALS = {"zero": zero_eval, "noise": noise_eval}


def stage2(game, args):
    depth, seed = args.depth, args.seed
    positions = random_positions(game, args.n_pos, seed=seed)
    print(f"{len(positions)} konum, seed={seed}, derinlik={depth}\n", file=sys.stderr)

    per_pos = []                      # her konum için ayrıntılı satır
    summary = []
    for ev_name in args.evals.split(","):
        evaluate = EVALS[ev_name]
        mm_nodes, mm_time, mismatches = [], 0.0, 0
        ab = {k: {"nodes": [], "time": 0.0} for k in ORDERINGS}
        for i, s in enumerate(positions):
            t0 = time.perf_counter()
            _, mm_value, st = minimax_decision(game, s, depth, evaluate)
            mm_time += time.perf_counter() - t0
            mm_nodes.append(st.nodes)
            row = [ev_name, i, s.n_moves, st.nodes]
            for name, order in ORDERINGS.items():
                t0 = time.perf_counter()
                move, value, st2 = alphabeta_decision(game, s, depth, evaluate, order)
                ab[name]["time"] += time.perf_counter() - t0
                ab[name]["nodes"].append(st2.nodes)
                # Doğruluk: kök değeri VE seçilen hamlenin değeri minimax ile aynı olmalı
                child = game.result(s, move)
                move_value = (game.utility(child) if game.is_terminal(child)
                              else minimax_decision(game, child, depth - 1, evaluate)[1])
                if value != mm_value or move_value != mm_value or st2.nodes > st.nodes:
                    mismatches += 1
                    print(f"  UYUMSUZ: eval={ev_name} konum {i} {name}", file=sys.stderr)
                row.append(st2.nodes)
            per_pos.append(row)
            print(f"  {ev_name} {i + 1}/{len(positions)}", file=sys.stderr, end="\r")

        n = len(positions)
        mm_avg = sum(mm_nodes) / n
        summary.append([ev_name, "minimax", f"{mm_avg:.0f}", "1.000",
                        f"{mm_avg ** (1 / depth):.2f}", f"{mm_time / n * 1000:.1f}",
                        f"{mm_time / sum(mm_nodes) * 1e6:.2f}", "-"])
        for name in ORDERINGS:
            nodes = ab[name]["nodes"]
            avg = sum(nodes) / n
            summary.append([ev_name, name, f"{avg:.0f}", f"{avg / mm_avg:.3f}",
                            f"{avg ** (1 / depth):.2f}", f"{ab[name]['time'] / n * 1000:.1f}",
                            f"{ab[name]['time'] / sum(nodes) * 1e6:.2f}", mismatches])

    # Sıralama fonksiyonunun kendi maliyeti: kök konumlarında tek çağrı süresi
    cost_rows = []
    for name, order in ORDERINGS.items():
        reps = 200
        t0 = time.perf_counter()
        for _ in range(reps):
            for s in positions:
                order(game, s)
        us = (time.perf_counter() - t0) / (reps * len(positions)) * 1e6
        cost_rows.append([name, f"{us:.2f}"])

    header = ["eval", "yöntem", "ort. düğüm", "minimax'a oran", "b_etkin",
              "ort. süre (ms)", "µs/düğüm", "uyumsuz"]
    print()
    print_table(header, summary)
    write_csv("stage2_summary.csv", header, summary)
    print()
    print_table(["sıralama", "order() çağrısı (µs)"], cost_rows)
    write_csv("stage2_order_cost.csv", ["sıralama", "order_us"], cost_rows)
    pos_header = ["eval", "konum", "hamle_sayısı", "minimax"] + list(ORDERINGS)
    write_csv("stage2_per_position.csv", pos_header, per_pos)

    # En az budanan konumlar (α-β / minimax oranı en yüksek), sıralama (c) için
    for ev_name in args.evals.split(","):
        rows = [r for r in per_pos if r[0] == ev_name]
        worst = sorted(rows, key=lambda r: r[-1] / r[3], reverse=True)[:3]
        print(f"\n[{ev_name}] en az budanan 3 konum (tactical / minimax):", file=sys.stderr)
        for r in worst:
            print(f"  konum {r[1]} ({r[2]} hamle oynanmış): {r[-1]}/{r[3]} = {r[-1] / r[3]:.3f}",
                  file=sys.stderr)
    plot_stage2(summary, depth)


def plot_stage2(summary, depth):
    """Ortalama düğüm sayısı (log ölçek): yöntem başına, eval başına iki çubuk."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    methods = ["minimax", "none", "center_out", "tactical_center_out"]
    labels = ["minimax", "α-β\n(a) sırasız", "α-β\n(b) merkez", "α-β\n(c) taktik+merkez"]
    evals = sorted({r[0] for r in summary}, key=lambda e: list(EVALS).index(e))
    colors = {"zero": "#2a78d6", "noise": "#eb6834"}
    names = {"zero": "Eval = 0", "noise": "gürültülü Eval"}
    width = 0.38

    fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=150)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    for j, ev in enumerate(evals):
        vals = [float(next(r[2] for r in summary if r[0] == ev and r[1] == m)) for m in methods]
        xs = [i + (j - (len(evals) - 1) / 2) * (width + 0.02) for i in range(len(methods))]
        bars = ax.bar(xs, vals, width, color=colors[ev], label=names[ev], zorder=2)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v * 1.12, f"{v:,.0f}".replace(",", "."),
                    ha="center", va="bottom", fontsize=7.5, color="#3d3d3a")
    # Knuth-Moore en iyi durum (mükemmel sıralama): b^ceil(d/2) + b^floor(d/2) - 1 yaprak
    b = 8
    best = b ** math.ceil(depth / 2) + b ** (depth // 2) - 1
    ax.axhline(best, color="#8a8980", lw=1, ls="--", zorder=1,
               label=f"kuramsal en iyi ≈ b^⌈d/2⌉ + b^⌊d/2⌋ − 1 = {best:,}".replace(",", "."))
    ax.set_yscale("log")
    ax.set_xticks(range(len(methods)), labels, fontsize=8.5)
    ax.set_ylabel("ortalama düğüm (log ölçek)", fontsize=9, color="#3d3d3a")
    ax.set_title(f"50 konum, derinlik {depth}: ortalama düğüm sayısı", fontsize=10.5,
                 color="#1f1f1d", loc="left")
    ax.grid(axis="y", color="#e4e3dd", lw=0.6, zorder=0)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c3c2b7")
    ax.tick_params(colors="#5f5e57", labelsize=8)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    fig.tight_layout()
    path = os.path.join(RESULTS, "stage2_nodes.png")
    fig.savefig(path)
    print(f"-> {path}")


# ----------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["stage0", "stage1", "stage2"])
    p.add_argument("--R", type=int, default=6)
    p.add_argument("--C", type=int, default=8)
    p.add_argument("--K", type=int, default=5)
    p.add_argument("--V", type=int, default=2)
    p.add_argument("--d", type=int, default=52)
    p.add_argument("--max-n", type=int, default=4)
    p.add_argument("--depth", type=int, default=6)
    p.add_argument("--seed", type=int, default=52)
    p.add_argument("--n-pos", type=int, default=50)
    p.add_argument("--evals", default="zero,noise")
    args = p.parse_args()
    game = Game(args.R, args.C, args.K, args.V, args.d)
    print(f"Varyant (R, C, K, V, d) = ({game.R}, {game.C}, {game.K}, {game.V}, {game.d})\n")
    {"stage0": stage0, "stage1": stage1, "stage2": stage2}[args.stage](game, args)


if __name__ == "__main__":
    main()

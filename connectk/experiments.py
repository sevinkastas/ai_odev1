"""Rapor için ölçüm scriptleri. Her aşama ayrı bir alt komut:

    python experiments.py stage0            # perft tablosu
    python experiments.py stage0 --max-n 5
    python experiments.py stage1            # minimax: hamle, düğüm, b_etkin
    python experiments.py stage2            # 50 konum: minimax vs α-β, 3 sıralama, grafik
    python experiments.py stage3            # 3 ağırlık vektörü, her çift iki yönde 10'ar maç
    python experiments.py stage4            # 1 sn arama: derinlik, TT doğruluğu, ufuk etkisi
    python experiments.py stage4 --part depth|tt|horizon
    python experiments.py stage5 --seed 7   # turnuva provası: her V, 6x8 ve 7x8, ajan vs baseline

Çıktılar ekrana Markdown tablosu olarak basılır ve results/ klasörüne CSV olarak yazılır.
Varyant parametreleri komut satırından değiştirilebilir (--R --C --K --V --d).
"""

import argparse
import csv
import math
import os
import sys
import time

from game import Game, perft, random_positions, MAX, MIN
from evaluate import Evaluator, WEIGHTS, opening, play_game
from search import (minimax_decision, alphabeta_decision, ORDERINGS,
                    zero_eval, noise_eval, TimedSearch, order_none, order_tactical)

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
# Her Eval bir "fabrika": game -> evaluate(game, s). Gerçek Eval pencereleri game'e göre hesaplar.
EVALS = {"zero": lambda game: zero_eval,
         "noise": lambda game: noise_eval,
         "full": lambda game: Evaluator(game)}


def stage2(game, args):
    depth, seed = args.depth, args.seed
    positions = random_positions(game, args.n_pos, seed=seed)
    print(f"{len(positions)} konum, seed={seed}, derinlik={depth}\n", file=sys.stderr)

    per_pos = []                      # her konum için ayrıntılı satır
    summary = []
    for ev_name in args.evals.split(","):
        evaluate = EVALS[ev_name](game)
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
    colors = {"zero": "#2a78d6", "noise": "#eb6834", "full": "#1baf7a"}
    names = {"zero": "Eval = 0", "noise": "gürültülü Eval", "full": "gerçek Eval (Aşama 3)"}
    width = 0.8 / len(evals) - 0.02

    fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=150)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    for j, ev in enumerate(evals):
        vals = [float(next(r[2] for r in summary if r[0] == ev and r[1] == m)) for m in methods]
        xs = [i + (j - (len(evals) - 1) / 2) * (width + 0.02) for i in range(len(methods))]
        bars = ax.bar(xs, vals, width, color=colors[ev], label=names[ev], zorder=2)
        for k, (b, v) in enumerate(zip(bars, vals)):
            # minimax her Eval için aynı düğüm sayısını verir: etiketi yalnızca ortadaki çubuğa yaz
            if methods[k] == "minimax" and j != (len(evals) - 1) // 2:
                continue
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
# Aşama 3: ağırlık vektörleri turnuvası
# ----------------------------------------------------------------------
def stage3(game, args):
    names = list(WEIGHTS)
    wins = {a: {b: [0, 0, 0] for b in names} for a in names}   # [galibiyet, beraberlik, yenilgi]
    as_max = {a: [0, 0] for a in names}                         # [MAX iken galibiyet, MAX iken oyun]
    games_rows = []
    t_start = time.perf_counter()
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for g_idx in range(args.games):
                open_seed = args.seed * 1000 + g_idx      # aynı açılış iki yönde de kullanılır
                op = opening(game, open_seed)
                for first, second in ((a, b), (b, a)):
                    winner, moves = play_game(game, WEIGHTS[first], WEIGHTS[second], op, depth=args.depth)
                    res = {MAX: (first, second), MIN: (second, first)}.get(winner)
                    if res is None:
                        wins[first][second][1] += 1
                        wins[second][first][1] += 1
                    else:
                        w, l = res
                        wins[w][l][0] += 1
                        wins[l][w][2] += 1
                    as_max[first][1] += 1
                    as_max[first][0] += (winner == MAX)
                    label = {MAX: first, MIN: second}.get(winner, "berabere")
                    games_rows.append([first, second, open_seed, " ".join(map(str, op)),
                                       label, len(moves), " ".join(map(str, moves))])
                    print(f"  {first} (MAX) - {second} (MIN), açılış {op}: {label}, {len(moves)} hamle",
                          file=sys.stderr)
    elapsed = time.perf_counter() - t_start

    header = ["vektör / rakip"] + names + ["toplam G-B-M"]
    rows = []
    for a in names:
        tot = [sum(wins[a][b][k] for b in names if b != a) for k in range(3)]
        rows.append([a] + ["-" if a == b else "{}-{}-{}".format(*wins[a][b]) for b in names]
                    + ["{}-{}-{}".format(*tot)])
    print()
    print(f"seed = {args.seed}, derinlik {args.depth}, çift başına {2 * args.games} oyun, "
          f"toplam süre {elapsed:.0f} s. Hücre: galibiyet-beraberlik-mağlubiyet (satırdaki vektör için)")
    print()
    print_table(header, rows)
    write_csv("stage3_weights.csv", header, rows)
    print()
    print_table(["vektör", "ağırlıklar", "MAX iken galibiyet / oyun"],
                [[a, WEIGHTS[a], f"{as_max[a][0]}/{as_max[a][1]}"] for a in names])
    write_csv("stage3_games.csv", ["MAX", "MIN", "açılış_seed", "açılış", "kazanan", "hamle_sayısı", "hamleler"],
              games_rows)


# ----------------------------------------------------------------------
# Aşama 4: zaman sınırlı arama
# ----------------------------------------------------------------------
def stage4_positions(game):
    """Kontrol noktası 4 için 10 konum: positions.txt'deki 5 + seed'li 5 rastgele orta oyun konumu."""
    named = [(name, game.from_moves(m)) for name, m in load_positions()[:5]]
    rand = random_positions(game, 5, seed=52, min_plies=10, max_plies=30)
    return named + [(f"R{i + 1}", s) for i, s in enumerate(rand)]


def stage4_depth(game, args):
    """1 saniyelik limitle ulaşılan derinlik: TT açık/kapalı x sıralama (uzatma açık)."""
    ev = Evaluator(game)
    positions = stage4_positions(game)
    configs = [("tactical", order_tactical, False), ("tactical", order_tactical, True),
               ("none", order_none, False), ("none", order_none, True)]
    header = ["konum", "hamle no"] + [f"{o} TT={'açık' if tt else 'kapalı'}" for o, _, tt in configs]
    rows, agg = [], {i: [] for i in range(len(configs))}
    for name, s in positions:
        row = [name, s.n_moves]
        for i, (_, order, tt) in enumerate(configs):
            r = TimedSearch(game, ev, use_tt=tt, order=order).search(s, args.time_limit)
            agg[i].append(r)
            row.append(f"d={r.depth} / {r.nodes} / {r.elapsed:.3f}s")
        rows.append(row)
        print(f"  {name} tamam", file=sys.stderr)
    print(f"Hücre: ulaşılan derinlik / düğüm / süre. Süre bütçesi {args.time_limit} s\n")
    print_table(header, rows)
    write_csv("stage4_depth_per_position.csv", header, rows)
    summary = []
    for i, (oname, _, tt) in enumerate(configs):
        rs = agg[i]
        summary.append([oname, "açık" if tt else "kapalı",
                        f"{sum(r.depth for r in rs) / len(rs):.1f}",
                        min(r.depth for r in rs), max(r.depth for r in rs),
                        f"{sum(r.nodes for r in rs) / len(rs):.0f}",
                        f"{max(r.elapsed for r in rs):.3f}"])
    print()
    sh = ["sıralama", "TT", "ort. derinlik", "min", "maks", "ort. düğüm", "en yavaş hamle (s)"]
    print_table(sh, summary)
    write_csv("stage4_depth_summary.csv", sh, summary)


def stage4_tt(game, args):
    """TT doğruluğu: sabit derinlikte, TT açık arama kök değeri = TT'siz α-β kök değeri (50 konum)."""
    positions = random_positions(game, args.n_pos, seed=args.seed)
    header = ["eval", "derinlik", "konum", "uyumsuz", "TT'siz ort. düğüm", "TT'li ort. düğüm"]
    rows = []
    for ev_name in ("noise", "full"):
        evaluate = EVALS[ev_name](game)
        for depth in (4, 6):
            bad, n_plain, n_tt = 0, 0, 0
            for s in positions:
                _, v_plain, st = alphabeta_decision(game, s, depth, evaluate, order_tactical)
                ts = TimedSearch(game, evaluate, use_tt=True, extend=False, order=order_tactical,
                                 distance=False)
                r = ts.search(s, math.inf, max_depth=depth)
                # ID son iterasyonu 'depth' olmalı (erken kesin sonuçta daha önce durabilir)
                if r.depth != depth and abs(r.value) < 1:
                    bad += 1
                v_tt = r.value
                if r.depth < depth:          # kesin sonuç erken bulunduysa aynı derinlikte tekrar ara
                    v_tt = TimedSearch(game, evaluate, use_tt=True, extend=False,
                                       order=order_tactical, distance=False)._root(s, depth, r.move)[1]
                if v_tt != v_plain:
                    bad += 1
                    print(f"  UYUMSUZ {ev_name} d={depth}: {v_plain} != {v_tt}", file=sys.stderr)
                n_plain += st.nodes
                n_tt += ts.nodes
            rows.append([ev_name, depth, len(positions), bad,
                         f"{n_plain / len(positions):.0f}", f"{n_tt / len(positions):.0f}"])
            print(f"  {ev_name} d={depth} tamam", file=sys.stderr)
    print()
    print_table(header, rows)
    write_csv("stage4_tt_check.csv", header, rows)


def stage4_horizon(game, args):
    """Ufuk etkisi: Aşama 3 maçlarından konumlar; sığ arama (derinlik D) kanıtlanmış kayba giden bir
    hamle seçiyor mu? 'Doğru' değer derinlik-7 aramayla bulunur. Uzatmalı / uzatmasız karşılaştırılır."""
    ev = Evaluator(game)
    path = os.path.join(RESULTS, "stage3_games.csv")
    with open(path, encoding="utf-8") as f:
        games = [[int(x) for x in r["hamleler"].split()] for r in csv.DictReader(f)]
    # Her oyundan 18. hamleden itibaren her 3 hamlede bir konum; aynı oyunlar tekrar ettiği için tekilleştir
    positions = sorted({tuple(mv[:k]) for mv in games for k in range(18, len(mv) - 1, 3)})
    truth_depth = 7

    def search(s, depth, extend, limit=math.inf):
        return TimedSearch(game, ev, use_tt=True, extend=extend).search(s, limit, max_depth=depth)

    def move_value(s, a):
        c = game.result(s, a)
        return game.utility(c) if game.is_terminal(c) else search(c, truth_depth - 1, True, 30.0).value

    header = ["sığ derinlik", "konum", "uzatmasız hata", "uzatmalı hata"]
    rows, examples = [], []
    for D in (2, 3, 4):
        bp_total = be_total = 0
        for mv in positions:
            s = game.from_moves(mv)
            sign = 1 if s.to_move == MAX else -1
            plain = search(s, D, False).move
            ext = search(s, D, True).move
            deep = search(s, truth_depth, True, 30.0)
            vp = sign * move_value(s, plain)
            ve = vp if ext == plain else sign * move_value(s, ext)
            vd = sign * deep.value
            # |değer| >= 1 kesin sonuçtur (distance ölçeklemesiyle kayıp -1.0xx olabilir)
            bp, be = (vp <= -1 and vd > -1), (ve <= -1 and vd > -1)
            bp_total += bp
            be_total += be
            if bp:
                examples.append([D, " ".join(map(str, mv)), plain, ext, deep.move, f"{vd:+.3f}",
                                 "düzeldi" if not be else "düzelmedi"])
        rows.append([D, len(positions), bp_total, be_total])
        print(f"  D={D} tamam", file=sys.stderr)
    print(f"'Hata' = sığ aramanın seçtiği hamle derinlik-{truth_depth} aramada kanıtlanmış kayıp (−1)"
          f" iken kaybetmeyen bir hamle var.\n")
    print_table(header, rows)
    write_csv("stage4_horizon_counts.csv", header, rows)
    eh = ["D", "hamleler", "sığ hamle", "uzatmalı hamle", "derin hamle", "derin değer", "uzatma"]
    print()
    print_table(eh, examples)
    write_csv("stage4_horizon_examples.csv", eh, examples)

    # Kanıt: örnek konumda derinlik arttıkça seçilen hamlenin değişmesi
    if examples:
        mv = [int(x) for x in examples[0][1].split()]
        s = game.from_moves(mv)
        print(f"\nÖrnek konum ({len(mv)} hamle, sıra {'MAX' if s.to_move == MAX else 'MIN'}):")
        print(game.render(s))
        dh = ["derinlik", "uzatmasız hamle", "uzatmasız değer", "uzatmalı hamle", "uzatmalı değer"]
        drows = []
        for depth in range(1, truth_depth + 1):
            a = search(s, depth, False)
            b = search(s, depth, True)
            drows.append([depth, a.move, f"{a.value:+.3f}", b.move, f"{b.value:+.3f}"])
        print_table(dh, drows)
        write_csv("stage4_horizon_depths.csv", dh, drows)


def stage4(game, args):
    parts = ["depth", "tt", "horizon"] if args.part == "all" else [args.part]
    for part in parts:
        print(f"\n===== Aşama 4: {part} =====\n")
        {"depth": stage4_depth, "tt": stage4_tt, "horizon": stage4_horizon}[part](game, args)


# ----------------------------------------------------------------------
# Aşama 5: turnuva provası (ayrı süreçler, hakem arena.py)
# ----------------------------------------------------------------------
def stage5(game, args):
    from arena import play
    ours = "python agent.py"
    baseline = "python agent.py --depth 3 --no-tt --no-ext"     # zayıflatılmış eski sürüm
    header = ["R×C, K", "V", "MAX", "MIN", "sonuç", "hamle", "en uzun yanıt (ajanımız, s)"]
    rows, worst, problems = [], 0.0, 0
    for (R, C, K) in ((6, 8, 5), (7, 8, 5)):
        for V in range(4):
            g = Game(R, C, K, V, args.seed)
            gargs = ["--R", str(R), "--C", str(C), "--K", str(K), "--V", str(V), "--seed", str(args.seed)]
            for a_name, a_cmd, b_name, b_cmd in (("ajan", ours, "baseline", baseline),
                                                 ("baseline", baseline, "ajan", ours)):
                result, winner, moves, max_time = play(g, a_cmd, b_cmd, gargs)
                ours_key = "A" if a_name == "ajan" else "B"
                worst = max(worst, max_time[ours_key])
                label = {"A": a_name, "B": b_name}.get(winner, "berabere")
                if "aştı" in result or "yasa dışı" in result or "geçersiz" in result:
                    problems += 1
                rows.append([f"{R}×{C}, {K}", V, a_name, b_name,
                             f"{label} ({result})" if winner else result, len(moves),
                             f"{max_time[ours_key]:.3f}"])
                print(f"  {R}x{C} V={V} {a_name}-{b_name}: {result}", file=sys.stderr)
    print(f"seed = {args.seed}. Ajan: 0.85 s bütçe, TT + uzatma. Baseline: sabit derinlik 3, TT/uzatma yok.\n")
    print_table(header, rows)
    print(f"\nSüre aşımı / yasa dışı / geçersiz çıktı: {problems}. Ajanımızın en uzun yanıtı: {worst:.3f} s")
    write_csv("stage5_rehearsal.csv", header, rows)


# ----------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["stage0", "stage1", "stage2", "stage3", "stage4", "stage5"])
    p.add_argument("--R", type=int, default=6)
    p.add_argument("--C", type=int, default=8)
    p.add_argument("--K", type=int, default=5)
    p.add_argument("--V", type=int, default=2)
    p.add_argument("--d", type=int, default=52)
    p.add_argument("--max-n", type=int, default=4)
    p.add_argument("--depth", type=int, default=6)
    p.add_argument("--seed", type=int, default=52)
    p.add_argument("--n-pos", type=int, default=50)
    p.add_argument("--evals", default="zero,noise,full")
    p.add_argument("--games", type=int, default=10)
    p.add_argument("--part", default="all", choices=["all", "depth", "tt", "horizon"])
    p.add_argument("--time-limit", type=float, default=0.9)
    args = p.parse_args()
    game = Game(args.R, args.C, args.K, args.V, args.d)
    print(f"Varyant (R, C, K, V, d) = ({game.R}, {game.C}, {game.K}, {game.V}, {game.d})\n")
    {"stage0": stage0, "stage1": stage1, "stage2": stage2, "stage3": stage3, "stage4": stage4, "stage5": stage5}[args.stage](game, args)


if __name__ == "__main__":
    main()

"""Turnuva ajanı: komut satırı protokolü (Aşama 5).

Çalıştırma:
    python agent.py --R 6 --C 8 --K 5 --V 2 --seed 7

Protokol (standart girdi, satır satır):
    MOVES 3 3 4     -> şu ana kadarki hamleler (0'dan numaralı sütunlar), sıra bizde.
                       Cevap: tek satırda bir sütun numarası (stdout), hemen flush.
    MOVES           -> hiç hamle yok: ilk hamleyi biz yapıyoruz.
    QUIT            -> program kapanır.
Tanınmayan satırlar (ör. "Sıra sizde") yok sayılır. Bütün hata ayıklama çıktısı stderr'e gider.

Arama: Aşama 4'ün TimedSearch'ü (iteratif derinleşme + TT + ufuk uzatması), hamle başına 0.85 s bütçe.
Misère'de 'none' sıralaması, diğer kurallarda taktik sıralama (Aşama 2-4 ölçümleri).
"""

import argparse
import gc
import sys
import time

from game import Game
from evaluate import Evaluator, WEIGHTS
from search import TimedSearch, order_none, order_tactical


def log(*args):
    print(*args, file=sys.stderr, flush=True)


class Agent:
    def __init__(self, R, C, K, V, seed, d=None, time_limit=0.85, weights=None,
                 use_tt=True, extend=True, depth=None):
        # V = 3'te engeller Random(d) ile çekilir; turnuvada ortak değer --seed olduğu için d = seed varsayılır.
        self.game = Game(R, C, K, V, seed if d is None else d)
        evaluator = Evaluator(self.game, WEIGHTS[weights] if weights else None)
        order = order_none if self.game.misere else order_tactical
        self.searcher = TimedSearch(self.game, evaluator, use_tt=use_tt, extend=extend,
                                    order=order, seed=seed)
        self.time_limit = time_limit
        self.depth = depth            # yalnızca deney için: sabit derinlik (None = süre sınırlı)

    def legal_fallback(self, s):
        """Arama hiçbir şey döndüremezse: dolu olmayan ilk sütun (merkeze yakın)."""
        free = [c for c in range(self.game.C) if s.heights[c] < self.game.R]
        mid = (self.game.C - 1) / 2
        return min(free, key=lambda c: (abs(c - mid), c)) if free else 0

    def choose(self, moves):
        """Hamle listesinden durumu kur, sütun seç. Asla istisna fırlatmaz, her zaman bir sütun döndürür."""
        g = self.game
        try:
            s = g.from_moves(moves)
        except ValueError as e:
            log(f"[agent] geçersiz hamle dizisi: {e}")
            s = g.initial_state()
            for a in moves:                       # oynanabildiği kadarını oyna
                if 0 <= a < g.C and s.heights[a] < g.R:
                    s = g.result(s, a)
        if not g.actions(s):                      # oyun bitmiş ya da tahta dolu
            log("[agent] yasal hamle yok (oyun bitmiş / tahta dolu); yine de bir sütun yazılıyor")
            return self.legal_fallback(s)
        try:
            if self.depth is not None:
                r = self.searcher.search(s, float("inf"), max_depth=self.depth)
            else:
                r = self.searcher.search(s, self.time_limit)
            log(f"[agent] hamle {s.n_moves + 1}: sütun {r.move}, derinlik {r.depth}, "
                f"değer {r.value}, {r.nodes} düğüm, {r.elapsed:.3f} s")
            if r.move in g.actions(s):
                return r.move
        except Exception as e:                    # ne olursa olsun yasal bir hamle yaz
            log(f"[agent] arama hatası: {e!r}")
        return self.legal_fallback(s)


def parse_moves(line):
    """'MOVES 3 3 4' -> [3, 3, 4]"""
    return [int(x) for x in line.split()[1:]]


def run(agent, stdin=sys.stdin, stdout=sys.stdout):
    for raw in stdin:
        line = raw.strip()
        if not line:
            continue
        cmd = line.split()[0].upper()
        if cmd == "QUIT":
            break
        if cmd != "MOVES":
            log(f"[agent] tanınmayan satır yok sayıldı: {line!r}")
            continue
        t0 = time.perf_counter()
        try:
            moves = parse_moves(line)
        except ValueError:
            log(f"[agent] MOVES satırı okunamadı: {line!r}")
            moves = []
        move = agent.choose(moves)
        stdout.write(f"{move}\n")
        stdout.flush()                            # flush'ı unutma: hakem satırı beklesin
        log(f"[agent] toplam yanıt süresi {time.perf_counter() - t0:.3f} s")
        gc.collect()                              # çöp toplamayı süre DIŞINDA yap


def main(argv=None):
    p = argparse.ArgumentParser(description="Connect-K Arena ajanı")
    p.add_argument("--R", type=int, default=6)
    p.add_argument("--C", type=int, default=8)
    p.add_argument("--K", type=int, default=5)
    p.add_argument("--V", type=int, default=2)
    p.add_argument("--seed", type=int, default=52)
    p.add_argument("--d", type=int, default=None, help="V=3 engel seed'i (varsayılan: --seed)")
    p.add_argument("--time", type=float, default=0.85, help="hamle başına arama bütçesi (s)")
    p.add_argument("--weights", choices=list(WEIGHTS), default=None)
    p.add_argument("--no-tt", action="store_true")
    p.add_argument("--no-ext", action="store_true")
    p.add_argument("--depth", type=int, default=None, help="deney için sabit derinlik")
    args = p.parse_args(argv)
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    agent = Agent(args.R, args.C, args.K, args.V, args.seed, args.d, args.time, args.weights,
                  use_tt=not args.no_tt, extend=not args.no_ext, depth=args.depth)
    log(f"[agent] hazır: R={args.R} C={args.C} K={args.K} V={args.V} seed={args.seed}")
    run(agent)


if __name__ == "__main__":
    main()

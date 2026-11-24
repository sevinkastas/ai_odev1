"""Değerlendirme fonksiyonu (Aşama 3).

Eval(s) = 0.99 * tanh( (w1*f1 + w2*f2 + ... + w6*f6) / SCALE )      -> her zaman (-1, +1) aralığında
Böylece gerçek kazanç (+1) / kayıp (-1) her Eval değerinden büyük / küçük kalır.

Öznitelikler HER ZAMAN MAX gözüyle sayılır (minimax MAX gözüyle çalışıyor):
    f1 max_k1  : MAX'in (K-1) taş + 1 boş penceresi sayısı
    f2 max_k2  : MAX'in (K-2) taş + 2 boş penceresi sayısı
    f3 min_k1  : MIN'in (K-1) taş + 1 boş penceresi sayısı
    f4 min_k2  : MIN'in (K-2) taş + 2 boş penceresi sayısı
    f5 center  : merkez sütun(lar)daki MAX taşı - MIN taşı
    f6 safe    : güvenli hamle farkı = safe(MAX) - safe(MIN)              [Misère'ye özgü]
                 safe(p) = p'nin oynayıp KENDİ K'lı dizisini tamamlamayacağı sütun sayısı
İki oyuncunun da taşı olan pencere kimse için değerli değildir ve sayılmaz.

Misère'de işaretler standarda göre ters: kendi K-1 pencerem "tehdit" değil, "zehirli hücre"dir.
"""

import math
import sys

from game import Game, MAX, MIN, BLOCK, DIRECTIONS

SCALE = 4.0
FEATURES = ("max_k1", "max_k2", "min_k1", "min_k2", "center", "safe")

# Ağırlık vektörleri (sıra FEATURES ile aynı). Aşama 3 deneyinde karşılaştırılan üçlü:
WEIGHTS = {
    # W1 varsayılan: Misère'ye göre işaretlenmiş (kendi dizim kötü, rakibinki iyi) + güvenli hamle
    "W1_misere": (-1.0, -0.3, 1.0, 0.3, 0.0, 0.5),
    # W2 naif: standart Connect-Four işaretleri (Misère'yi hesaba katmıyor) -> kaybetmesi beklenir
    "W2_naive": (1.0, 0.3, -1.0, -0.3, 0.2, 0.0),
    # W3 zugzwang ağırlıklı: güvenli hamle farkı baskın, pencereler hafif
    "W3_safe": (-0.5, -0.1, 0.5, 0.1, 0.0, 1.5),
}
# Turnuva varyantı standart/silindir/engelli olursa kullanılacak vektör
WEIGHTS_STANDARD = (1.0, 0.3, -1.0, -0.3, 0.2, 0.0)
DEFAULT = "W1_misere"


def make_windows(game):
    """Tahtadaki bütün K hücrelik dizileri (pencereleri) BİR KEZ listele.
    Her pencere hücre indekslerinden oluşan bir tuple'dır.
    Silindirde sütun % C ile sarılır; engelli hücre içeren pencere atlanır."""
    R, C, K = game.R, game.C, game.K
    blocked = {r * C + c for (r, c) in game.blocked}
    seen, windows = set(), []
    for r in range(R):
        for c in range(C):
            for dr, dc in DIRECTIONS:
                cells = []
                for k in range(K):
                    rr, cc = r + k * dr, c + k * dc
                    if not 0 <= rr < R:
                        break
                    if game.cylinder:
                        cc %= C
                    elif not 0 <= cc < C:
                        break
                    cells.append(rr * C + cc)
                if len(cells) < K or blocked.intersection(cells):
                    continue
                key = frozenset(cells)
                if key not in seen:            # silindirde aynı pencere iki kez gelmesin
                    seen.add(key)
                    windows.append(tuple(cells))
    return windows


class Evaluator:
    """Pencereleri önceden hesaplayan, çağrılabilir Eval: evaluator(game, s) -> (-1, +1)."""

    def __init__(self, game, weights=None):
        self.game = game
        if weights is None:
            weights = WEIGHTS[DEFAULT] if game.misere else WEIGHTS_STANDARD
        self.weights = tuple(weights)
        self.windows = make_windows(game)
        C = game.C
        self.center_cols = (C // 2,) if C % 2 else (C // 2 - 1, C // 2)

    def features(self, s):
        """Öznitelik sayıları (sözlük). Kontrol noktası 3'te elle hesapla karşılaştırılır."""
        g, cells, K = self.game, s.cells, self.game.K
        max_k1 = max_k2 = min_k1 = min_k2 = 0
        max_hot, min_hot = set(), set()        # K-1 pencerelerin boş hücresi (Misère: zehirli hücre)
        for w in self.windows:
            vals = [cells[i] for i in w]
            x, o = vals.count(MAX), vals.count(MIN)
            if x and o:
                continue                        # iki tarafın taşı var: ölü pencere
            if x == K - 1:
                max_k1 += 1
                max_hot.add(w[vals.index(0)])
            elif x == K - 2:
                max_k2 += 1
            elif o == K - 1:
                min_k1 += 1
                min_hot.add(w[vals.index(0)])
            elif o == K - 2:
                min_k2 += 1
        center = 0
        for c in self.center_cols:
            for r in range(g.R):
                v = cells[r * g.C + c]
                center += (v == MAX) - (v == MIN)
        # Güvenli hamle: oynanabilir hücre, oyuncunun kendi K-1 penceresini tamamlamıyorsa güvenli.
        playable = [s.heights[c] * g.C + c for c in range(g.C) if s.heights[c] < g.R]
        safe_max = sum(1 for i in playable if i not in max_hot)
        safe_min = sum(1 for i in playable if i not in min_hot)
        return {"max_k1": max_k1, "max_k2": max_k2, "min_k1": min_k1, "min_k2": min_k2,
                "center": center, "safe": safe_max - safe_min}

    def raw(self, s):
        f = self.features(s)
        return sum(w * f[name] for w, name in zip(self.weights, FEATURES))

    def __call__(self, game, s):
        """Arama bu imzayı kullanır: evaluate(game, s)."""
        return 0.99 * math.tanh(self.raw(s) / SCALE)


# ----------------------------------------------------------------------
# Maç runner: iki ağırlık vektörünü birbirine karşı oynat (Aşama 3 ağırlık ayarı)
# ----------------------------------------------------------------------
def opening(game, seed, min_plies=2, max_plies=4):
    """Çeşitlilik için seed'li rastgele açılış: 2-4 rastgele hamle.
    Aksi halde iki deterministik ajan her seferinde aynı oyunu oynar."""
    import random
    rng = random.Random(seed)
    s = game.initial_state()
    moves = []
    for _ in range(rng.randint(min_plies, max_plies)):
        a = rng.choice(game.actions(s))
        moves.append(a)
        s = game.result(s, a)
    return moves


def play_game(game, weights_max, weights_min, opening_moves, depth=5):
    """Açılıştan sonra iki taraf da derinlik-'depth' α-β (taktik sıralama) ile oynar.
    Döndürür: (kazanan: MAX / MIN / 0, hamle listesi)."""
    from search import alphabeta_decision, order_tactical
    ev = {MAX: Evaluator(game, weights_max), MIN: Evaluator(game, weights_min)}
    s = game.from_moves(opening_moves)
    moves = list(opening_moves)
    while not game.is_terminal(s):
        move, _, _ = alphabeta_decision(game, s, depth, ev[s.to_move], order_tactical)
        moves.append(move)
        s = game.result(s, move)
    return game.winner(s), moves


# Komut satırı: kontrol noktası 3 için bir konumun özniteliklerini ve Eval'ini yazdır.
#   python evaluate.py 3 3 4 4 5 5
if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    g = Game()
    s = g.from_moves([int(x) for x in sys.argv[1:]])
    ev = Evaluator(g)
    print(g.render(s))
    print(f"sıra: {'MAX' if s.to_move == MAX else 'MIN'}   pencere sayısı: {len(ev.windows)}")
    for name, w in zip(FEATURES, ev.weights):
        print(f"  {name:7s} = {ev.features(s)[name]:3d}   ağırlık {w:+.2f}")
    print(f"ham toplam = {ev.raw(s):+.3f}   Eval = 0.99*tanh(toplam/{SCALE}) = {ev(g, s):+.4f}")

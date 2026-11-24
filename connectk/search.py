"""Arama algoritmaları.

Aşama 1: derinlik sınırlı MINIMAX (MAX gözüyle; negamax DEĞİL).
    - max_value / min_value karşılıklı özyineleme
    - İLK satır terminal kontrolü, İKİNCİ satır derinlik kontrolü
    - Düğüm sayacı: her max_value / min_value çağrısı (kök dahil) 1 düğüm
    - Beraberlik kuralı: eşit değerli hamlelerden MERKEZE en yakın olan, o da eşitse küçük sütun
Aşama 2: α-β budaması + 3 hamle sıralaması.
Aşama 4: TimedSearch = iteratif derinleşme + Zobrist yer değiştirme tablosu + ufuk uzatması.
"""

import gc
import math
import random
import time

from game import MAX, MIN, other


class Stats:
    """Düğüm sayacı. Her aramada yeni bir Stats nesnesi kullanılır."""
    def __init__(self):
        self.nodes = 0


def zero_eval(game, s):
    """Aşama 1'de henüz gerçek Eval yok: derinlik sınırında 0 döndür."""
    return 0


def noise_eval(game, s):
    """Yalnızca TEST/ÖLÇÜM için: konuma bağlı, deterministik, sözde rastgele değer (-0.5..0.5).
    Eval = 0 iken tüm yapraklar eşit olur; α-β = minimax testi hiçbir şey kanıtlamaz ve
    eşitlikler yüzünden budama yapay olarak artar. Bu Eval her yaprağa farklı değer verir.
    (Python'da int tuple'ının hash'i her çalıştırmada aynıdır.)"""
    return (hash(s.cells) % 1001) / 1000 - 0.5


def center_order(game, moves):
    """Hamleleri merkezden dışarı sırala (C=8 için: 3, 4, 2, 5, 1, 6, 0, 7).
    Kökte beraberlik kuralı olarak da kullanılır."""
    mid = (game.C - 1) / 2
    return sorted(moves, key=lambda c: (abs(c - mid), c))


# ----------------------------------------------------------------------
# Aşama 1: Minimax
# ----------------------------------------------------------------------
def max_value(game, s, depth, stats, evaluate):
    stats.nodes += 1
    if game.is_terminal(s):          # 1) terminal kontrolü ÖNCE
        return game.utility(s)
    if depth == 0:                   # 2) sonra derinlik sınırı
        return evaluate(game, s)
    v = -math.inf
    for a in game.actions(s):
        v = max(v, min_value(game, game.result(s, a), depth - 1, stats, evaluate))
    return v


def min_value(game, s, depth, stats, evaluate):
    stats.nodes += 1
    if game.is_terminal(s):
        return game.utility(s)
    if depth == 0:
        return evaluate(game, s)
    v = math.inf
    for a in game.actions(s):
        v = min(v, max_value(game, game.result(s, a), depth - 1, stats, evaluate))
    return v


def minimax_decision(game, s, depth, evaluate=zero_eval):
    """Kökte her hamlenin değerini hesapla, sırası gelen oyuncu için en iyisini seç.
    Döndürür: (hamle, değer, stats).
    Sıra MAX'teyse en büyük, MIN'deyse en küçük değer seçilir (ajan iki tarafı da oynayabilsin)."""
    stats = Stats()
    stats.nodes += 1                                   # kök düğüm
    maximizing = (s.to_move == MAX)
    best_move, best_value = None, None
    for a in center_order(game, game.actions(s)):     # merkez önce -> beraberlikte merkez kazanır
        child = game.result(s, a)
        if maximizing:
            v = min_value(game, child, depth - 1, stats, evaluate)
        else:
            v = max_value(game, child, depth - 1, stats, evaluate)
        # Yalnızca KESİN iyileşmede güncelle: eşit değerde ilk (merkeze yakın) hamle kalır.
        if best_value is None or (v > best_value if maximizing else v < best_value):
            best_move, best_value = a, v
    return best_move, best_value, stats


def choose_move(game, s, depth, evaluate=zero_eval):
    """Aşama 1 arayüzü: yalnızca seçilen hamleyi döndürür."""
    return minimax_decision(game, s, depth, evaluate)[0]


# ----------------------------------------------------------------------
# Aşama 2: hamle sıralama stratejileri
#   Hepsinin imzası aynı: order(game, s) -> yasal hamlelerin sıralı listesi
# ----------------------------------------------------------------------
def order_none(game, s):
    """(a) Sıralamasız: soldan sağa."""
    return game.actions(s)


def order_center(game, s):
    """(b) Merkezden dışarı."""
    return center_order(game, game.actions(s))


def order_tactical(game, s):
    """(c) Önce taktik hamleler, sonra merkezden dışarı.
    Her hamle için iki soru: 'buraya ben oynarsam K'lı dizi olur mu?' (mine)
                             'buraya rakip oynasa K'lı dizi olur mu?' (theirs)
    Standart:  mine -> 0 (kazanma, en başa), theirs -> 1 (engelleme), diğerleri -> 2
    Misère:    mine -> 3 (intihar, EN SONA), diğerleri -> 2
               (Misère'de rakibin dizi hücresini kapatmak onu kurtarır; öne alınmaz.)"""
    me, opp, C = s.to_move, other(s.to_move), game.C
    scored = []
    for a in game.actions(s):
        r = s.heights[a]
        if game.makes_line(s.cells, r, a, me):
            prio = 3 if game.misere else 0
        elif not game.misere and game.makes_line(s.cells, r, a, opp):
            prio = 1
        else:
            prio = 2
        scored.append((prio, abs(a - (C - 1) / 2), a))
    scored.sort()
    return [a for _, _, a in scored]


ORDERINGS = {"none": order_none, "center_out": order_center, "tactical_center_out": order_tactical}


# ----------------------------------------------------------------------
# Aşama 2: α-β budaması (MAX gözüyle)
#   alpha: MAX'in yol üzerinde garanti ettiği en iyi değer (alt sınır)
#   beta : MIN'in yol üzerinde garanti ettiği en iyi değer (üst sınır)
#   Kesme koşulu: MAX'te v >= beta, MIN'de v <= alpha  (eşitlikte de kes -> daha az düğüm)
# ----------------------------------------------------------------------
def ab_max_value(game, s, depth, alpha, beta, stats, evaluate, order):
    stats.nodes += 1
    if game.is_terminal(s):
        return game.utility(s)
    if depth == 0:
        return evaluate(game, s)
    v = -math.inf
    for a in order(game, s):
        v = max(v, ab_min_value(game, game.result(s, a), depth - 1, alpha, beta, stats, evaluate, order))
        if v >= beta:                 # β kesmesi: MIN bu dala zaten izin vermez
            return v
        alpha = max(alpha, v)
    return v


def ab_min_value(game, s, depth, alpha, beta, stats, evaluate, order):
    stats.nodes += 1
    if game.is_terminal(s):
        return game.utility(s)
    if depth == 0:
        return evaluate(game, s)
    v = math.inf
    for a in order(game, s):
        v = min(v, ab_max_value(game, game.result(s, a), depth - 1, alpha, beta, stats, evaluate, order))
        if v <= alpha:                # α kesmesi: MAX bu dala zaten izin vermez
            return v
        beta = min(beta, v)
    return v


def alphabeta_decision(game, s, depth, evaluate=zero_eval, order=order_center):
    """Kökte α-β. Döndürür: (hamle, değer, stats).
    Kökte de alpha (MAX sırasıysa) / beta (MIN sırasıysa) güncellenir; böylece sonraki
    çocuklar daha dar pencereyle aranır. Yalnızca KESİN iyileşmede hamle değişir: eşit
    değerli sonraki çocuk zaten sınır değeri döndürür ve seçilmez."""
    stats = Stats()
    stats.nodes += 1
    alpha, beta = -math.inf, math.inf
    maximizing = (s.to_move == MAX)
    best_move, best_value = None, None
    for a in order(game, s):
        child = game.result(s, a)
        if maximizing:
            v = ab_min_value(game, child, depth - 1, alpha, beta, stats, evaluate, order)
            if best_value is None or v > best_value:
                best_move, best_value = a, v
            alpha = max(alpha, v)
        else:
            v = ab_max_value(game, child, depth - 1, alpha, beta, stats, evaluate, order)
            if best_value is None or v < best_value:
                best_move, best_value = a, v
            beta = min(beta, v)
    return best_move, best_value, stats


# ======================================================================
# Aşama 4: zaman sınırlı arama
# ======================================================================
class Timeout(Exception):
    """Süre dolunca derin bir düğümde fırlatılır, kökte (search) yakalanır."""


EXACT, LOWER, UPPER = "EXACT", "LOWER", "UPPER"


class Zobrist:
    """Her (hücre, oyuncu) çifti için seed'li rastgele 64-bit sayı.
    Konumun anahtarı = dolu hücrelerin sayılarının XOR'u (+ sıra MIN'deyse 'side' sayısı).
    Sıra bilgisi anahtarda olduğu için aynı taşlar + farklı sıra = farklı anahtar."""

    def __init__(self, game, seed=52):
        rng = random.Random(seed)
        self.C = game.C
        # table[hücre][oyuncu]; oyuncu 1 (MAX) ya da 2 (MIN), indeks 0 kullanılmaz
        self.table = [[0, rng.getrandbits(64), rng.getrandbits(64)] for _ in range(game.R * game.C)]
        self.side = rng.getrandbits(64)

    def key(self, s):
        """Anahtarı sıfırdan hesapla (yalnızca kökte)."""
        k = 0
        for i, v in enumerate(s.cells):
            if v == MAX or v == MIN:
                k ^= self.table[i][v]
        if s.to_move == MIN:
            k ^= self.side
        return k

    def update(self, key, s, a):
        """result(s, a)'nın anahtarı, ARTIMLI: yeni taşı XOR'la ekle, sırayı çevir."""
        i = s.heights[a] * self.C + a
        return key ^ self.table[i][s.to_move] ^ self.side


class SearchResult:
    def __init__(self, move, value, depth, nodes, elapsed, depths_log):
        self.move, self.value, self.depth = move, value, depth
        self.nodes, self.elapsed, self.depths_log = nodes, elapsed, depths_log

    def __repr__(self):
        return (f"SearchResult(move={self.move}, value={self.value}, depth={self.depth}, "
                f"nodes={self.nodes}, elapsed={self.elapsed:.3f})")


class TimedSearch:
    """İteratif derinleşmeli α-β (MAX gözüyle) + isteğe bağlı TT + isteğe bağlı ufuk uzatması.

    Kullanım:  ts = TimedSearch(game, evaluator);  r = ts.search(s, time_limit=0.9);  r.move
    """

    def __init__(self, game, evaluate, use_tt=True, extend=True, max_ext=4,
                 order=order_tactical, check_every=1000, seed=52):
        self.game, self.evaluate, self.order = game, evaluate, order
        self.use_tt, self.extend, self.max_ext = use_tt, extend, max_ext
        self.check_every = check_every
        self.z = Zobrist(game, seed)
        self.tt = {}
        self.nodes = 0
        self.deadline = math.inf

    # ------------------------------------------------------------------
    def search(self, s, time_limit=1.0, max_depth=None):
        """Derinlik 1, 2, 3, ... süre dolana kadar. Süre dolarsa YARIM kalan derinlik atılır,
        son TAMAMLANAN derinliğin hamlesi döndürülür."""
        start = time.perf_counter()
        self.deadline = start + time_limit
        self.nodes = 0
        if len(self.tt) > 2_000_000:          # bellek sınırı
            self.tt.clear()
        moves = self.order(self.game, s)
        if not moves:
            raise ValueError("Terminal durumda hamle aranamaz")
        if max_depth is None:
            max_depth = sum(self.game.R - h for h in s.heights)   # daha derini anlamsız: tahta dolar

        best_move, best_value, depth_done, log = moves[0], None, 0, []
        gc_was_enabled = gc.isenabled()
        gc.disable()                           # çöp toplayıcı arama sırasında süreyi bozmasın
        try:
            for depth in range(1, max_depth + 1):
                try:
                    move, value = self._root(s, depth, best_move)
                except Timeout:
                    break                      # yarım kalan derinliği AT
                best_move, best_value, depth_done = move, value, depth
                log.append((depth, move, value, self.nodes, time.perf_counter() - start))
                if len(moves) == 1 or abs(value) >= 1:
                    break                      # tek hamle var ya da kesin kazanç/kayıp kanıtlandı
        finally:
            if gc_was_enabled:
                gc.enable()
        return SearchResult(best_move, best_value, depth_done, self.nodes,
                            time.perf_counter() - start, log)

    # ------------------------------------------------------------------
    def _root(self, s, depth, first):
        """Kök: önceki iterasyonun en iyi hamlesi ('first') İLK sırada denenir."""
        g = self.game
        moves = self.order(g, s)
        if first in moves:
            moves.remove(first)
            moves.insert(0, first)
        key = self.z.key(s)
        maximizing = (s.to_move == MAX)
        alpha, beta = -math.inf, math.inf
        best_move, best_value = None, None
        for a in moves:
            v = self._ab(g.result(s, a), self.z.update(key, s, a), depth - 1, alpha, beta, self.max_ext)
            if maximizing:
                if best_value is None or v > best_value:
                    best_move, best_value = a, v
                alpha = max(alpha, v)
            else:
                if best_value is None or v < best_value:
                    best_move, best_value = a, v
                beta = min(beta, v)
        return best_move, best_value

    # ------------------------------------------------------------------
    def _ab(self, s, key, depth, alpha, beta, ext):
        """α-β düğümü (MAX ve MIN tek fonksiyonda; değer hep MAX gözüyle)."""
        self.nodes += 1
        if self.nodes % self.check_every == 0 and time.perf_counter() > self.deadline:
            raise Timeout()
        g = self.game
        if g.is_terminal(s):                   # 1) terminal
            return g.utility(s)
        if depth <= 0:                         # 2) derinlik sınırı
            if self.extend and ext > 0 and self.is_forcing(s):
                depth, ext = 1, ext - 1        # ufuk uzatması: sakin olmayan konumda 1 kat daha
            else:
                return self.evaluate(g, s)

        # 3) Yer değiştirme tablosu: yalnızca kayıtlı derinlik >= gereken derinlik ise kullan
        tt_move = None
        if self.use_tt:
            entry = self.tt.get(key)
            if entry is not None:
                e_depth, e_value, e_flag, tt_move = entry
                if e_depth >= depth:
                    if e_flag == EXACT:
                        return e_value
                    if e_flag == LOWER:        # gerçek değer >= e_value
                        alpha = max(alpha, e_value)
                    else:                      # UPPER: gerçek değer <= e_value
                        beta = min(beta, e_value)
                    if alpha >= beta:
                        return e_value
        a_lo, b_hi = alpha, beta               # bayrağı belirlemek için (tablodan daraltılmış) pencere

        moves = self.order(g, s)
        if tt_move is not None and tt_move in moves:   # tablonun en iyi hamlesi önce
            moves.remove(tt_move)
            moves.insert(0, tt_move)

        maximizing = (s.to_move == MAX)
        v = -math.inf if maximizing else math.inf
        best = moves[0]
        for a in moves:
            cv = self._ab(g.result(s, a), self.z.update(key, s, a), depth - 1, alpha, beta, ext)
            if maximizing:
                if cv > v:
                    v, best = cv, a
                if v >= beta:                  # β kesmesi
                    break
                alpha = max(alpha, v)
            else:
                if cv < v:
                    v, best = cv, a
                if v <= alpha:                 # α kesmesi
                    break
                beta = min(beta, v)

        if self.use_tt:
            if v <= a_lo:
                flag = UPPER                   # α'yı geçemedi: gerçek değer <= v
            elif v >= b_hi:
                flag = LOWER                   # β kesmesi: gerçek değer >= v
            else:
                flag = EXACT
            self.tt[key] = (depth, v, flag, best)
        return v

    # ------------------------------------------------------------------
    def is_forcing(self, s):
        """'Sakin olmayan' konum mu? (ufuk etkisine karşı uzatma koşulu)
        Misère : sırası gelenin güvenli (intihar olmayan) hamlesi <= 1 -> zorlanmış hamle.
        Standart: oynanabilir bir hücre birinin K'lı dizisini tamamlıyor (acil kazanma/engelleme)."""
        g = self.game
        me, opp = s.to_move, other(s.to_move)
        playable = [(s.heights[c], c) for c in range(g.C) if s.heights[c] < g.R]
        if g.misere:
            safe = sum(1 for r, c in playable if not g.makes_line(s.cells, r, c, me))
            return safe <= 1
        return any(g.makes_line(s.cells, r, c, opp) or g.makes_line(s.cells, r, c, me)
                   for r, c in playable)

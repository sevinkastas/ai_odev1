"""Arama algoritmaları.

Aşama 1: derinlik sınırlı MINIMAX (MAX gözüyle; negamax DEĞİL).
    - max_value / min_value karşılıklı özyineleme
    - İLK satır terminal kontrolü, İKİNCİ satır derinlik kontrolü
    - Düğüm sayacı: her max_value / min_value çağrısı (kök dahil) 1 düğüm
    - Beraberlik kuralı: eşit değerli hamlelerden MERKEZE en yakın olan, o da eşitse küçük sütun
"""

import math

from game import MAX, other


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

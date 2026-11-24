"""Arama algoritmaları.

Aşama 1: derinlik sınırlı MINIMAX (MAX gözüyle; negamax DEĞİL).
    - max_value / min_value karşılıklı özyineleme
    - İLK satır terminal kontrolü, İKİNCİ satır derinlik kontrolü
    - Düğüm sayacı: her max_value / min_value çağrısı (kök dahil) 1 düğüm
    - Beraberlik kuralı: eşit değerli hamlelerden MERKEZE en yakın olan, o da eşitse küçük sütun
"""

import math

from game import MAX


class Stats:
    """Düğüm sayacı. Her aramada yeni bir Stats nesnesi kullanılır."""
    def __init__(self):
        self.nodes = 0


def zero_eval(game, s):
    """Aşama 1'de henüz gerçek Eval yok: derinlik sınırında 0 döndür."""
    return 0


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

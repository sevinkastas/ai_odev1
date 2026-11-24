"""Connect-K oyun modeli (Aşama 0).

Varyantım: (R, C, K, V, d) = (6, 8, 5, 2, 52)  ->  Misère: K'lı diziyi yapan KAYBEDER.
Ama Game sınıfı dört varyantın hepsini destekler (turnuva günü varyant değişebilir):
    V=0 Standart, V=1 Silindir, V=2 Misère, V=3 Engelli.

Tahta gösterimi:
    - cells: R*C uzunluğunda düz bir tuple. Hücre (r, c) -> indeks r*C + c.
    - r = 0 EN ALT satırdır (yerçekimi aşağı doğru), c = 0 en soldaki sütundur.
    - Hücre değerleri: EMPTY=0, MAX=1, MIN=2, BLOCK=-1 (engelli hücre).
    - heights[c]: sütun c'de bir sonraki taşın düşeceği satır. heights[c] == R ise sütun dolu.

Durum (State) değişmezdir: result(s, a) YENİ bir State döndürür, s'ye dokunmaz.
"""

import random
from typing import NamedTuple, Optional

EMPTY, MAX, MIN, BLOCK = 0, 1, 2, -1

# Kazanma/kaybetme kontrolünde bakılan 4 yön: (satır adımı, sütun adımı)
#   yatay, dikey, çapraz "/", çapraz "\"
DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))


def other(player):
    """Rakip oyuncu: MAX <-> MIN."""
    return MIN if player == MAX else MAX


class State(NamedTuple):
    """Değişmez oyun durumu. NamedTuple olduğu için alanlar atanamaz."""
    cells: tuple            # R*C hücre
    heights: tuple          # her sütunda bir sonraki boş satır
    to_move: int            # sırası gelen oyuncu (MAX ya da MIN)
    last_move: Optional[int]  # son oynanan sütun (başlangıçta None)
    line_maker: int         # K'lı diziyi yapan oyuncu; yoksa EMPTY (0)
    n_moves: int            # şimdiye kadar oynanan hamle sayısı


class Game:
    def __init__(self, R=6, C=8, K=5, V=2, d=52):
        self.R, self.C, self.K, self.V, self.d = R, C, K, V, d
        self.cylinder = (V == 1)
        self.misere = (V == 2)
        self.blocked = self._make_blocks() if V == 3 else []

    # ------------------------------------------------------------------
    # Engelli hücreler (yalnızca V = 3)
    # ------------------------------------------------------------------
    def _make_blocks(self):
        """Föydeki gibi: rng = Random(d), iki kez (satır, sütun) çek, tekrar çıkarsa yeniden çek.
        Varsayım: çekilen satır numarası alttan sayılır (r = 0 en alt)."""
        rng = random.Random(self.d)
        blocks = []
        while len(blocks) < 2:
            cell = (rng.randrange(self.R), rng.randrange(self.C))
            if cell not in blocks:
                blocks.append(cell)
        return blocks

    # ------------------------------------------------------------------
    # Oyun modeli: initial_state, actions, result, is_terminal, utility
    # ------------------------------------------------------------------
    def initial_state(self):
        """Boş tahta, engeller yerleşmiş, sıra MAX'te."""
        R, C = self.R, self.C
        cells = [EMPTY] * (R * C)
        heights = [0] * C
        for (r, c) in self.blocked:
            cells[r * C + c] = BLOCK
            # Taş engelin ÜSTÜNDE durur; engelin altına hiç ulaşılamaz.
            heights[c] = max(heights[c], r + 1)
        return State(tuple(cells), tuple(heights), MAX, None, EMPTY, 0)

    def actions(self, s):
        """Yasal sütunlar: içinde hâlâ boş yer olan sütunlar (soldan sağa).
        Oyun bittiyse hamle yoktur."""
        if s.line_maker != EMPTY:
            return []
        return [c for c in range(self.C) if s.heights[c] < self.R]

    def result(self, s, a):
        """Sütun a'ya taş bırak. YENİ durum döndürür (s değişmez)."""
        r = s.heights[a]
        if r >= self.R:
            raise ValueError(f"Sütun {a} dolu, yasal hamle değil")
        i = r * self.C + a
        p = s.to_move
        cells = s.cells[:i] + (p,) + s.cells[i + 1:]          # yeni tuple
        heights = s.heights[:a] + (r + 1,) + s.heights[a + 1:]  # yeni tuple
        # Kazanma kontrolü taşı KOYDUKTAN SONRA, yeni tahtada yapılır.
        maker = p if self.makes_line(cells, r, a, p) else EMPTY
        return State(cells, heights, other(p), a, maker, s.n_moves + 1)

    def makes_line(self, cells, r, c, p):
        """(r, c)'ye konan p taşı K'lı bir dizi oluşturuyor mu?
        Yalnızca bu taşın satırı, sütunu ve iki çaprazı taranır."""
        R, C, K = self.R, self.C, self.K
        for dr, dc in DIRECTIONS:
            count = 1
            for sign in (1, -1):            # önce ileri, sonra geri yürü
                rr, cc = r + sign * dr, c + sign * dc
                while 0 <= rr < R:
                    if self.cylinder:
                        cc %= C              # silindir: sütun başa sarar (-1 -> C-1)
                    elif not (0 <= cc < C):
                        break                # standart: tahta kenarında dur
                    if cells[rr * C + cc] != p:
                        break                # boş, rakip ya da ENGEL diziyi keser
                    count += 1
                    if count >= K:
                        # Silindirde K <= C olduğundan, sarma aynı hücreyi iki kez
                        # saymadan önce sayaç K'ya ulaşır; çift sayım olmaz.
                        return True
                    rr, cc = rr + sign * dr, cc + sign * dc
        return False

    def is_terminal(self, s):
        """Biri K'lı dizi yaptıysa ya da tahtada yasal hamle kalmadıysa oyun biter."""
        if s.line_maker != EMPTY:
            return True
        return all(h >= self.R for h in s.heights)

    def winner(self, s):
        """Kazanan oyuncu, beraberlikte / oyun sürüyorsa EMPTY.
        Misère'de diziyi yapan kaybeder, yani kazanan rakibidir."""
        if s.line_maker == EMPTY:
            return EMPTY
        return other(s.line_maker) if self.misere else s.line_maker

    def utility(self, s):
        """MAX gözüyle fayda: +1 MAX kazandı, -1 MIN kazandı, 0 berabere."""
        w = self.winner(s)
        if w == MAX:
            return 1
        if w == MIN:
            return -1
        return 0

    # ------------------------------------------------------------------
    # Yardımcılar
    # ------------------------------------------------------------------
    def from_moves(self, moves):
        """'3 3 4 4' gibi bir hamle dizisinden (string ya da liste) durum kur.
        İlk hamleyi MAX yapar. Sütunlar 0'dan numaralanır."""
        if isinstance(moves, str):
            moves = [int(x) for x in moves.split()]
        s = self.initial_state()
        for a in moves:
            if a not in self.actions(s):
                raise ValueError(f"Yasa dışı hamle {a} (hamle no {s.n_moves + 1})")
            s = self.result(s, a)
        return s

    def render(self, s):
        """Tahtayı yazdır (en üst satır önce). X = MAX, O = MIN, # = engel."""
        sym = {EMPTY: ".", MAX: "X", MIN: "O", BLOCK: "#"}
        lines = []
        for r in range(self.R - 1, -1, -1):
            lines.append(" ".join(sym[s.cells[r * self.C + c]] for c in range(self.C)))
        lines.append(" ".join(str(c) for c in range(self.C)))
        return "\n".join(lines)


def random_positions(game, count, seed, min_plies=6, max_plies=24):
    """Seed'li rastgele hamlelerle 'count' tane TERMİNAL OLMAYAN konum üret.
    Aynı seed her zaman aynı konumları verir (ölçümler tekrarlanabilir)."""
    rng = random.Random(seed)
    out = []
    while len(out) < count:
        s = game.initial_state()
        for _ in range(rng.randint(min_plies, max_plies)):
            if game.is_terminal(s):
                break
            s = game.result(s, rng.choice(game.actions(s)))
        if not game.is_terminal(s):
            out.append(s)
    return out


def perft(game, s, n):
    """Tam derinlik n'deki yaprak sayısı (föydeki tanım: budama yok,
    terminal durumdan hamle yapılmaz, terminal durum bir yaprak sayılır)."""
    if n == 0 or game.is_terminal(s):
        return 1
    return sum(perft(game, game.result(s, a), n - 1) for a in game.actions(s))

# PROMPTLAR.md — Yapay zekâ kullanım tutanağı

Kullanılan araç: Claude Code (Claude Opus 5.5), VS Code eklentisi.

## 1. Mimari plan (Aşama öncesi)
- **Ne istedim:** Ödev föyünü ve kendi varyantımı `(6, 8, 5, 2, 52)` verip proje yapısı, durum gösterimi
  ve aşama planı önermesini istedim.
- **Kullandığım kısım:** Düz tuple + `heights` ile değişmez `State` önerisi, MAX gözüyle minimax kararı,
  aşama başına commit planı.

## 2. Aşama 0 — Oyun modeli ve perft
- **Ne istedim:** `game.py` (initial_state, actions, result, kazanma kontrolü, is_terminal, utility, perft),
  birim testleri ve perft ölçüm scripti.
- **Kullandığım kısım:** `game.py`, `tests/test_game.py`, `tests/helpers.py`, `experiments.py stage0`.
- **Kendim kontrol ettiğim:** P2 konumunda perft(2) = 57 değerini elle hesapladım
  (MAX'in 8 hamlesinden biri oyunu bitirir: 7·8 + 1).

## 3. Aşama 1 — Minimax
- **Ne istedim:** `search.py` içinde derinlik sınırlı minimax (max_value/min_value), merkez öncelikli
  beraberlik kuralı, düğüm sayacı; testler ve 5 konum × derinlik 2/4/6 ölçüm komutu.
- **Kullandığım kısım:** `search.py` (Stats, zero_eval, center_order, max_value, min_value,
  minimax_decision, choose_move), `tests/test_minimax.py`, `experiments.py stage1`.
- **Kendim kontrol ettiğim:** boş tahtada derinlik 2 düğüm sayısı 1 + 8 + 64 = 73; P2'de 65 = 1 + 1 + 7·9.

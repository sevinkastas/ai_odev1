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

## 4. Aşama 2 — α-β budaması ve hamle sıralaması
- **Ne istedim:** α-β (ab_max_value/ab_min_value, kökte alpha güncellemesi), üç sıralama (none, center_out,
  tactical_center_out; Misère'de intihar hamlesi sona), 50 konumda doğruluk testi, düğüm/maliyet ölçümü ve grafik.
- **Kullandığım kısım:** `search.py` (order_*, ORDERINGS, ab_*, alphabeta_decision, noise_eval),
  `game.random_positions`, `tests/test_alphabeta.py`, `experiments.py stage2`.
- **Önerinin gerekçesi:** Eval = 0 ile eşitlik testi zayıf kaldığı için test/ölçümde ek olarak deterministik
  "gürültülü" Eval kullanıldı.
- **Kendim kontrol ettiğim:** β kesme koşulunu (`>=` → `>`, `<=`, `>= alpha`) kopyada bozup testlerin
  yakaladığını gördüm.

## 5. Aşama 3 — Değerlendirme fonksiyonu ve ağırlık ayarı
- **Ne istedim:** Önceden hesaplanmış K-pencereleri üzerinde Misère'ye uygun işaretli, [-1, +1]'e sıkıştırılmış
  Eval; Misère'ye özgü öznitelik; 3 ağırlık vektörüyle iki yönlü maç deneyi.
- **Kullandığım kısım:** `evaluate.py` (make_windows, Evaluator.features/raw/__call__, WEIGHTS, opening,
  play_game, komut satırı çıktısı), `tests/test_evaluate.py`, `experiments.py stage3`,
  stage2'ye gerçek Eval seçeneği (`full`).
- **Önerinin gerekçesi:** Misère'ye özgü öznitelik olarak "güvenli hamle farkı" (oyuncunun intihar etmeden
  oynayabileceği sütun sayısı farkı) seçildi; Misère oyun sonu zugzwang ile belirlenir.
- **Kendim kontrol ettiğim:** `python evaluate.py 0 0 1 1 2 2 3 3` çıktısındaki öznitelikleri tahtada elle saydım.

## 6. Aşama 4 — Zaman sınırlı arama, yer değiştirme tablosu, ufuk etkisi
- **Ne istedim:** 1 saniyelik iteratif derinleşme (her 1000 düğümde süre kontrolü, Timeout istisnası, yarım
  derinliği atma, önceki en iyi hamle önce), seed'li Zobrist TT (EXACT/LOWER/UPPER), ufuk uzatması; TT açık/kapalı
  derinlik ölçümü, TT doğruluk testi, ufuk etkisi örneği ve önce/sonra karşılaştırması.
- **Kullandığım kısım:** `search.py` (Timeout, Zobrist, SearchResult, TimedSearch: search/_root/_ab/is_forcing),
  `tests/test_timed.py`, `experiments.py stage4` (depth / tt / horizon).
- **Önerinin gerekçesi:** Ufuk örneği, Aşama 3 maç kayıtlarındaki konumlarda sığ arama ile derinlik-7 arama
  karşılaştırılarak otomatik bulundu. İkinci bir uzatma koşulu denendi, fark ölçülemediği için sade olan tutuldu.
- **Kendim kontrol ettiğim:** Örnek konumu tahtada inceleyip 7. sütunun neden kaybettirdiğini izledim.

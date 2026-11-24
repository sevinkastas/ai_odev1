# Connect-K Arena — Rapor

**Varyant: (R, C, K, V, d) = (6, 8, 5, 2, 52)**: 6 satır, 8 sütun, K = 5, **Misère** (5'li diziyi yapan kaybeder).

Tüm sayılar `connectk/` klasöründe `python experiments.py stageN` ile bu makinede üretildi; ham veriler `results/` altında.

---

## Aşama 0 — Oyun modeli ve perft

**Tasarım.** Durum değişmez bir `State` (NamedTuple): düz `cells` tuple'ı (R·C, satır 0 en alt), `heights`
(her sütunda bir sonraki boş satır), `to_move`, `last_move`, `line_maker`, `n_moves`. `result()` yeni tuple
üretir. Dizi kontrolü yalnızca son konan taşın 4 yönüne bakar. `utility` MAX gözüyle: Misère'de
`line_maker` kaybeder. Silindir (`% C`) ve engelli (V = 3) varyantlar da aynı sınıfta.

**Perft tablosu** (`results/stage0_perft.csv`):

| konum | n=1 | n=2 | n=3 | n=4 | süre n=4 (s) |
|---|---|---|---|---|---|
| boş | 8 | 64 | 512 | 4096 | 0.010 |
| P1 `3 3 4 4 5 5` | 8 | 64 | 512 | 3802 | 0.009 |
| P2 `0 0 1 1 2 2 3 3` | 8 | 57 | 449 | 3242 | 0.008 |
| P3 (20 hamle) | 8 | 57 | 406 | 2878 | 0.007 |
| P4 (11 hamle) | 8 | 64 | 512 | 4094 | 0.011 |
| P5 (16 hamle) | 8 | 64 | 512 | 4096 | 0.011 |

Boş tahtada n = 5: 32768 (0.078 s), n = 6: 262144 (0.622 s).

**Yorum.** K = 5 iken ilk 5'li en erken 9. hamlede oluşabilir. Bu yüzden boş tahtada n ≤ 8 için perft = 8ⁿ
olur ve modeli sınamaz. Asıl sınama yarı dolu konumlardadır. P2'de MAX'in 4. sütuna oynaması 5'li yapıp
oyunu bitirir; bu yüzden perft(2) = 7·8 + 1 = 57 (elle doğrulandı, birim testinde de var).
<!-- TODO: öğretmenin 3 kontrol konumu geldiğinde tabloya eklenecek -->

---

## Aşama 1 — Minimax

**Tasarım.** `max_value` / `min_value` (MAX gözüyle). İlk satır terminal kontrolü, ikinci satır `depth == 0`
(şimdilik Eval = 0). Düğüm sayacı her çağrıda (kök dahil) 1 artar. Beraberlik kuralı: eşit değerli hamlelerden
merkeze en yakın olanı, o da eşitse küçük sütunu seç (C = 8 için sıra 3, 4, 2, 5, 1, 6, 0, 7). Böylece aynı
konumda her koşu aynı hamleyi verir.

**Ölçüm** (`results/stage1_minimax.csv`, b_etkin = düğüm^(1/derinlik)):

| konum | d=2 hamle / düğüm | d=4 hamle / düğüm | d=6 hamle / düğüm | b_etkin (d=6) | süre d=6 (s) |
|---|---|---|---|---|---|
| P1 | 3 / 73 | 3 / 4345 | 3 / 250405 | 7.94 | 0.66 |
| P2 | 3 / 65 | 3 / 3705 | 3 / 210629 | 7.71 | 0.55 |
| P3 | 4 / 65 | 4 / 3292 | 4 / 167782 | 7.43 | 0.45 |
| P4 | 3 / 73 | 3 / 4679 | 3 / 297916 | 8.17 | 0.83 |
| P5 | 3 / 73 | 3 / 4681 | 3 / 299241 | 8.18 | 0.94 |

**Yorum.**
- Budamasız minimax'ta b_etkin ≈ C = 8 olur, çünkü her düğümün bütün çocuklarına bakılır. Derinlik 2'de değer
  8'in biraz üstünde çıkar (8.54 = √73): sayaca iç düğümler de girdiği için düğüm sayısı 1 + C + C² olur, C²
  değil. Derinlik arttıkça bu etki azalır.
- b_etkin'in 8'in altına düştüğü konumlar (P2, P3) arama içinde **oyunun bittiği** dallar içerir. Misère'de
  5'li yapan hamle terminal olduğundan altı açılmaz (P2'de MAX'in 4. sütunu: derinlik 2'de 1 + 1 + 7·9 = 65).
- Eval = 0 olduğundan değerlerin hepsi 0 çıktı. Seçilen hamle yalnızca beraberlik kuralıyla (merkez) belirlendi;
  istisna P3: orada MAX'in 3. sütunda dikey 4 taşı var, 3'e oynamak doğrudan 5'li (Misère'de kayıp, değer −1),
  bu yüzden bir sonraki merkez sütun 4 seçildi. Aşama 3'teki Eval bu körlüğü giderecek.
- Derinlik 6 yaklaşık 0.5–0.9 s sürüyor. 1 saniyelik limitte düz minimax ile en fazla 6'ya inilebilir.
  Aşama 2'deki α-β bunun için gerekli.
<!-- TODO: öğretmenin 5 konumu geldiğinde positions.txt güncellenip tablo yeniden üretilecek -->


## Aşama 2 — α-β budaması ve hamle sıralaması

_(doldurulacak)_

## Aşama 3 — Değerlendirme fonksiyonu

_(doldurulacak)_

## Aşama 4 — Zaman sınırlı arama

_(doldurulacak)_

## Aşama 5 — Turnuva ve yenilgi analizi

_(doldurulacak)_

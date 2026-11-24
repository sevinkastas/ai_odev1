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

**Tasarım.** `ab_max_value` / `ab_min_value`: MAX'te `v >= beta` ise kes, MIN'de `v <= alpha` ise kes
(eşitlikte de kesmeyi seçtim: değer aynı, düğüm daha az). Kökte her çocuk aynı fonksiyonla çağrılır ve
alpha (MAX sırasıysa) güncellenir; hamle yalnızca kesin iyileşmede değişir. Üç sıralama:
(a) `none` soldan sağa, (b) `center_out` merkezden dışarı,
(c) `tactical_center_out`: standartta önce kazanan, sonra engelleyen hamle; **Misère'de kendi 5'lisini
tamamlayan intihar hamlesi en sona**; geri kalanı merkezden dışarı.

**Doğruluk testi.** `random_positions(seed=52)` ile 50 terminal olmayan konum (6–24 rastgele hamle), derinlik 6.
İki yaprak değerlendirmesiyle denedim: Föydeki gibi **Eval = 0** ve her yaprağa konuma bağlı sabit, sözde rastgele
değer veren **gürültülü Eval**. Eval = 0'da neredeyse bütün değerler 0 olduğundan "α-β = minimax" testi zayıf
kalır; gürültülü Eval gerçek bir sınamadır. **50 × 3 × 2 = 300 aramanın hepsinde kök değeri, seçilen hamlenin
değeri minimax ile aynı; α-β hiçbir konumda minimax'tan fazla düğüme bakmadı** (`uyumsuz = 0`).

**Ortalama düğüm** (`results/stage2_summary.csv`, grafik `results/stage2_nodes.png`):

| Eval | yöntem | ort. düğüm | minimax'a oran | b_etkin | ort. süre (ms) | µs/düğüm |
|---|---|---|---|---|---|---|
| 0 | minimax | 243 047 | 1.000 | 7.90 | 725 | 2.98 |
| 0 | (a) none | 1 615 | 0.007 | 3.43 | 5.1 | 3.16 |
| 0 | (b) center_out | 1 639 | 0.007 | 3.43 | 6.2 | 3.78 |
| 0 | (c) tactical | 1 608 | 0.007 | 3.42 | 14.0 | 8.69 |
| gürültü | minimax | 243 047 | 1.000 | 7.90 | 812 | 3.34 |
| gürültü | (a) none | 20 064 | 0.083 | 5.21 | 69 | 3.45 |
| gürültü | (b) center_out | 22 773 | 0.094 | 5.32 | 92 | 4.05 |
| gürültü | (c) tactical | 22 562 | 0.093 | 5.32 | 147 | 6.53 |
| gerçek (Aşama 3) | minimax | 243 047 | 1.000 | 7.90 | 5 224 | 21.49 |
| gerçek (Aşama 3) | (a) none | 3 480 | 0.014 | 3.89 | 60 | 17.32 |
| gerçek (Aşama 3) | (b) center_out | 7 402 | 0.030 | 4.41 | 139 | 18.75 |
| gerçek (Aşama 3) | (c) tactical | 7 329 | 0.030 | 4.41 | 158 | 21.58 |

_Gerçek Eval satırları Aşama 3'ten sonra aynı 50 konumda yeniden ölçüldü (`--evals zero,noise,full`)._

![Aşama 2 düğüm sayısı](results/stage2_nodes.png)

**Sıralama maliyeti** (tek `order()` çağrısı, `results/stage2_order_cost.csv`): none 0.50 µs, center_out 1.68 µs,
tactical 12.35 µs. Taktik sıralama her hamle için iki kez `makes_line` çağırdığından düğüm başına maliyeti
yaklaşık 2–3 katına çıkarıyor.

**Yorum.**
- **Beklenen sıra (c < b < a) bu aşamada çıkmadı; nedeni Eval.** Sıralama, "iyi hamleyi önce dene" demektir;
  bu, değerlerin hamle kalitesiyle ilişkili olmasını gerektirir. Eval = 0'da bütün terminal olmayan yapraklar
  eşittir: ilk çocuk zaten pencerenin sınırına ulaşır ve `>=` / `<=` eşitlikte kestiği için hangi sırayla
  bakılırsa bakılsın neredeyse mükemmel budama olur (b_etkin 3.4; kuramsal en iyi √8 ≈ 2.83). Gürültülü Eval'de
  ise değerler merkezle ilişkisizdir; merkez önce gelmesi bir avantaj sağlamaz, hatta biraz kötüleşir.
  Taktik sıralama Misère'de yalnızca intihar hamlelerini sona atar; bunlar zaten tek düğümlük terminal
  yapraklar olduğundan budamaya etkisi küçük.
- **Gerçek Eval ile sıra yine tersine (a < c ≈ b); nedeni Misère.** Merkezden sıralama, Connect-Four'daki
  "merkez iyidir" önsezisine dayanır. 200 rastgele konumda her hamlenin sonrasındaki Eval'i hamle yapan
  gözüyle ortaladım. Misère'de merkez sütunlar (3: −0.071, 4: −0.096) kenarlardan (0: −0.043, 7: −0.048)
  daha **kötü**; standart kuralda tam tersi (merkez +0.10/+0.12, kenar +0.03). Merkez hücreler daha çok
  pencereye girer; Misère'de kendi pencerelerimi büyütmek (f1, f2) kötüdür. Yani (b) ve (c) Misère'de kötü
  hamleleri önce dener ve daha az keser. Ders: sıralama sezgisi kurala bağlıdır. Aşama 4'te önceki
  iterasyonun / tablonun en iyi hamlesini başa almak bu sezgiye ihtiyaç bırakmayacak.
- **O(b^(m/2)) ile karşılaştırma:** mükemmel sıralamada derinlik 6, b = 8 için yaklaşık 8³ + 8³ − 1 = 1 023 yaprak
  (Knuth–Moore). Eval = 0 ile ölçülen 1 608 düğüm (iç düğümler dahil) bu sınıra çok yakın. Gürültülü Eval'de
  22 562, yani en iyi durumun ~22 katı: b_etkin 5.3, minimax'ın 7.9'u ile √8 arasında.
- **En az budanan konumlar:** gürültülü Eval'de konum 44 (13 hamle oynanmış; α-β/minimax = 0.169).
  Erken konumlarda hiçbir dal terminale ulaşmaz ve değerler birbirine yakın, rastgele dağılır; kesmeyi
  tetikleyen ±1'lik kesin değerler yoktur. Eval = 0'da en az budananlar 22–23 hamlelik konumlar (oran ≈ 0.012):
  orada intihar dalları −1/+1 vererek eşitlikleri bozar ve bazı alt ağaçların tamamen açılması gerekir.
- **Kontrol noktası 2 hazırlığı:** β kesmesi bir kopyada üç şekilde bozuldu. `>=` → `>` değeri bozmaz, yalnızca
  düğüm sayısını artırır (sabit konumda 222 → 320). Bunu `test_node_count_regression` yakalar. `<=` ve
  `>= alpha` değeri bozar; bunları `test_alphabeta_equals_minimax` yakalar.

## Aşama 3 — Değerlendirme fonksiyonu

**Tasarım.** Tahtadaki bütün K = 5 hücrelik pencereler oyun başında bir kez listelenir (6×8 standart/Misère: 56,
silindir: 96 (sarmalı), engelli d=52: 50 (engel içerenler atlanır)). Eval her çağrıda bu listeyi tarar; iki tarafın
da taşı olan pencere ölü sayılır. Öznitelikler MAX gözüyle:

| öznitelik | anlamı | W1 (varsayılan) | W2 (naif) | W3 (zugzwang) |
|---|---|---|---|---|
| f1 max_k1 | MAX'in 4 taş + 1 boş penceresi | −1.0 | +1.0 | −0.5 |
| f2 max_k2 | MAX'in 3 taş + 2 boş penceresi | −0.3 | +0.3 | −0.1 |
| f3 min_k1 | MIN'in 4 taş + 1 boş penceresi | +1.0 | −1.0 | +0.5 |
| f4 min_k2 | MIN'in 3 taş + 2 boş penceresi | +0.3 | −0.3 | +0.1 |
| f5 center | merkez sütunlarda (3, 4) MAX − MIN taşı | 0 | +0.2 | 0 |
| f6 safe | **güvenli hamle farkı** (Misère'ye özgü) | +0.5 | 0 | +1.5 |

`Eval = 0.99 · tanh(Σ wᵢfᵢ / 4)`: her zaman (−0.99, +0.99) içinde, böylece gerçek kazanç/kayıp (±1) her Eval
değerinden büyük/küçük kalır. Bir çağrı ≈ 22 µs.

**Misère'ye özgü öznitelik (f6).** `safe(p)` = p'nin oynayıp kendi 5'lisini tamamlamayacağı sütun sayısı. Misère'de
oyun sonu bir zugzwang savaşıdır: güvenli hamlesi önce biten taraf ya 5'li yapmak ya da hamle yapamamak zorunda
kalır. f6 bu "kim önce sıkışır" farkını doğrudan ölçer. f1–f4'ün işaretleri de standarda göre terstir: kendi
4'lü penceremin boş hücresi "tehdit" değil, benim için **zehirli hücre**dir; rakibin zehirli hücreleri benim
lehime.

**Ağırlık ayarı.** Her çift, aynı seed'li açılışla iki yönde 10'ar oyun, iki taraf da derinlik 5 α-β
(taktik sıralama). Çeşitlilik: her oyunun ilk 2–4 hamlesi `opening(seed = 52·1000 + i)` ile rastgele.
**Seed = 52.** Hücre: satırdaki vektörün galibiyet-beraberlik-mağlubiyet sayısı (`results/stage3_weights.csv`,
oyun kayıtları `results/stage3_games.csv`):

| vektör / rakip | W1_misere | W2_naive | W3_safe | toplam G-B-M |
|---|---|---|---|---|
| W1_misere | – | 18-2-0 | 1-18-1 | 19-20-1 |
| W2_naive | 0-2-18 | – | 0-3-17 | 0-5-35 |
| W3_safe | 1-18-1 | 17-3-0 | – | 18-21-1 |

**Tahmin ve sonuç.** Tahminim: W2 (standart işaretler) Misère'de kendi dizisini kurmaya çalışacağı için açık
ara kaybedecek; W1 ve W3 birbirine yakın olacak, W3 oyun sonunda biraz daha iyi olabilir. Ölçüm W2 kısmını
tam doğruladı: 40 oyunda 0 galibiyet. **Bu, Misère'de ağırlık işaretlerinin ters çevrilmesi gerektiğinin
ölçümle kanıtıdır.** W1–W3 eşleşmesinde 20 oyunun 18'i berabere; derinlik 5'te iki vektör de intihar
hamlesinden kaçınmayı biliyor ve tahta dolana kadar oynuyor. Aralarındaki fark bu deneyle ayırt edilemiyor.
Turnuva için W1'i (dengeli) varsayılan bıraktım.

**Kendini kontrol (testler, `tests/test_evaluate.py`).** Bir hamlede biten konumda Eval çağrılmıyor (derinlik 1'de
8 çocuktan biri terminal → Eval 7 kez çağrılıyor). Sol-sağ ayna konumlarda Eval aynı. Silindirde ayna simetrisi
korunur ama tahta aynı zamanda döndürmeye göre simetriktir; f5 "merkez" sütunu bu simetriyi bozar (silindirde
gerçek bir merkez yoktur). Engelli varyantta engeller simetrik konumlanmadığı için pencere kümesi aynada değişir
ve ayna eşitliği bozulur (d = 52 için engeller (2,0) ve (5,7)).

**Kontrol noktası 3 için:** `python evaluate.py 0 0 1 1 2 2 3 3` konumu çizer, her özniteliğin sayısını, ağırlığını,
ham toplamı ve Eval'i yazar (örnek: f = (1, 1, 1, 1, 0, −1), ham −0.5, Eval −0.1231).

## Aşama 4 — Zaman sınırlı arama

**Tasarım (`search.TimedSearch`).** İteratif derinleşme: derinlik 1, 2, 3, … Her 1000 düğümde bir
`time.perf_counter()` kontrolü; süre dolunca `Timeout` istisnası fırlatılır, kökte yakalanır ve **yarım kalan
derinlik atılır**, son tamamlanan derinliğin hamlesi döner. Önceki iterasyonun en iyi hamlesi kökte ilk sırada
denenir. Kesin kazanç/kayıp (|değer| = 1) bulunursa ya da tahtadaki boş hücre sayısına ulaşılırsa erken durur.
Arama süresince çöp toplayıcı kapalıdır (`gc.disable()`), sonra açılır.

**Yarım iterasyon neden atılır?** Kökte hamleler sırayla aranır. Süre, ilk (önceki iterasyonun en iyisi) hamle
bittikten hemen sonra dolarsa, "en iyi hamle" yalnızca o tek hamleye bakılarak seçilmiş olur. Diğer hamleler
hiç incelenmemiştir; içlerinden biri daha iyi olabilir. Daha kötüsü, ilk hamlenin yeni derinlikteki değeri bir
tuzak ortaya çıkarmışsa (değeri düştüyse) bile başka seçenek olmadığı için yine o seçilir. Tamamlanmış
derinliğin sonucu ise bütün kök hamleleri aynı derinlikte karşılaştırmıştır.

**Yer değiştirme tablosu.** Zobrist anahtarı: her (hücre, oyuncu) için seed'li (52) 64-bit sayı, sıra MIN'deyse
ayrıca `side` sayısı XOR'lanır (aynı taşlar + farklı sıra = farklı anahtar). Anahtar hamlede artımlı
güncellenir (`key ^ Z[hücre][oyuncu] ^ side`). Kayıt: `anahtar → (derinlik, değer, bayrak, en iyi hamle)`.
Bayrak: değer pencerenin içindeyse EXACT, β kesmesinden geldiyse LOWER, α'yı geçemediyse UPPER. Kayıt yalnızca
kayıtlı derinlik ≥ gereken derinlik ise kullanılır; tablonun en iyi hamlesi sıralamada başa alınır.

**1 saniyede ulaşılan derinlik** (10 konum: P1–P5 + seed'li 5 rastgele; bütçe 0.9 s, uzatma açık;
`results/stage4_depth_*.csv`):

| sıralama | TT | ort. derinlik | min–maks | ort. düğüm | en yavaş hamle (s) |
|---|---|---|---|---|---|
| tactical | kapalı | 6.6 | 6–8 | 27 700 | 0.927 |
| tactical | açık | 8.6 | 8–9 | 30 700 | 0.938 |
| none | kapalı | 7.2 | 6–8 | 32 200 | 0.941 |
| none | açık | **9.3** | 8–11 | 37 200 | 0.930 |

- **TT, aynı sürede ortalama 2 kat daha derine indiriyor.** Düğüm sayısı neredeyse aynı (süre sınırlı), ama tablo
  tekrar eden konumları ve önceki iterasyonların en iyi hamlelerini kullandığı için her derinlik daha az düğümle
  bitiyor. Sabit derinlik 6'da gerçek Eval ile TT düğümü 7 329 → 2 496'ya indirdi (`stage4_tt_check.csv`).
- Aşama 2–3'teki bulgu burada da geçerli: Misère'de sıralamasız (soldan sağa) düzen merkezli düzenden derin
  iniyor. Turnuva ajanı Misère'de `none` + TT kullanacak.
- **Hiçbir hamle 1 saniyeyi aşmadı** (en yavaş 0.941 s). Taşma (~40 ms) süre kontrolünün 1000 düğümde bir
  yapılmasından gelir (≈ 1000 × 28 µs); ajan güvenlik payı için 0.85 s bütçe kullanır.

**TT doğruluğu** (Aşama 2 testi tablo açıkken yeniden: 50 konum, sabit derinlik, uzatma kapalı):
gürültülü ve gerçek Eval, derinlik 4 ve 6, **200 karşılaştırmada 0 uyumsuz**: tablolu kök değeri tablosuz α-β ile
aynı. Sabit derinlikte bir konuma hep aynı katta ulaşıldığından (hamle sayısı aynı), kayıtlı derinlik ile gereken
derinlik eşittir; bayraklar yanlış olsaydı değer farkı çıkardı.

**Ufuk etkisi.** Aşama 3 maçlarından 284 benzersiz konum (18. hamleden itibaren her 3 hamlede bir). "Hata": sığ
aramanın (derinlik D) seçtiği hamle, derinlik-7 aramada **kanıtlanmış kayıp** (−1) iken kaybetmeyen bir hamle var.

| sığ derinlik D | uzatmasız hata | uzatmalı hata |
|---|---|---|
| 2 | 3 | 1 |
| 3 | 1 | 1 |
| 4 | 1 | 0 |

**Örnek konum** (36 hamle, sıra MAX; `1 4 3 3 3 3 4 3 3 4 4 4 1 4 2 5 2 0 2 1 5 5 1 5 1 1 0 6 0 6 2 0 7 6 7 0`):

```
. O . X O . . .
O X . O O . . .
O X X O X O . .
X O X X O O O .
X X X O X X O X
O X X X O O O X
0 1 2 3 4 5 6 7
```

| derinlik | uzatmasız hamle (değer) | uzatmalı hamle (değer) |
|---|---|---|
| 1–3 | 7 (−0.80…−0.83) | 7 |
| 4 | **7 (−0.732)** | **6 (−0.801)** |
| 5 | 6 (−0.825) | 6 (−0.825) |
| 6–7 | 6 (−0.67 / −0.754) | 6 (−0.754) |

Derinlik 4'e kadar uzatmasız arama 7. sütunu seçiyor; derinlik 7'de bu hamlenin kanıtlanmış kayıp olduğu görülüyor
ve derinlik 5'ten itibaren hamle 6'ya dönüyor. **Hamlenin derinlikle değişmesi ufuk etkisinin kanıtıdır**: kayıp
dizisi sığ aramanın ufkunun hemen ötesindeydi ve Eval −0.73 ile "o kadar da kötü değil" diyordu.

**Düzeltme: zorlanmış konumlarda uzatma.** Derinlik sınırına gelindiğinde konum sakin değilse 1 kat daha
aranır (yol başına en çok 4 uzatma). Misère'de "sakin değil" = sırası gelenin güvenli (intihar olmayan) hamlesi
≤ 1 (zorlanmış hamle); standart kuralda = oynanabilir bir hücre birinin K'lı dizisini tamamlıyor (acil
kazanma/engelleme). Önce/sonra: toplam ufuk hatası 5 → 2; örnek konumda doğru hamle bir kat önce
(derinlik 4) bulunuyor. Ayrıca "rakip de zorlanmışsa uzat" koşulunu denedim; hata sayıları bu kadar küçükken
iki koşul ayırt edilemedi, daha sade olanı tuttum.

**Kontrol noktası 4:** `python experiments.py stage4 --part depth` 10 konumda ulaşılan derinliği ve her hamlenin
süresini yazar.

## Aşama 5 — Turnuva ve yenilgi analizi

_(doldurulacak)_

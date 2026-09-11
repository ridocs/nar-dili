# Çalışma durumu

Bu dosya, uzun süren geliştirmede **nerede kalındığını** tutar. Oturum
kesilirse buradan devam edilir. Her önemli adımdan sonra güncellenir.

---

## Son güncelleme

**2026-09-11 05:00** — AST artık konum taşıyor ve konumlar iki çözümleyicide birebir aynı. Sırada denetleyicinin gövde aşaması.

## Şu ana kadar biten

| Sürüm | Ne yapıldı | Durum |
|---|---|---|
| v0.1 | Lexer, parser, tip denetleyici, JS arka ucu, CLI | ✅ |
| v0.2 | Sadeleştirme: Int/Float uyumu, metin birleştirme, if/match ifadesi, tek satırlık fonksiyon, çok argümanlı print | ✅ |
| v0.2 | Belgeler sitesi (36 konu, örnekler üretimde çalıştırılıyor) | ✅ |
| v0.2 | Lambda gerektirmeyen liste işlemleri | ✅ |
| v0.2 | Nar IDE — tarayıcıda editör | ✅ |
| v0.2.5 | Tüm tip hataları tek seferde bildiriliyor | ✅ |
| v0.2.5 | IDE masaüstü uygulaması (pywebview / Edge --app) | ✅ |
| v0.2.5 | Kütüphane modu (`--kutuphane`) | ✅ |
| v0.2.5 | Metin işlemlerinde O(n²) → O(n) önbellek düzeltmesi | ✅ |
| v0.3 | Sayfa (DOM) bağlaması: Element, Olay, bul/olustur/dinle | ✅ |
| v0.3 | Kod biçimlendirici + `nar fmt` (Nar ile yazıldı) | ✅ |
| v0.3 | JSON kütüphanesi (Nar ile yazıldı) | ✅ |
| v0.3 | **IDE'nin tüm davranışı Nar diliyle** | ✅ |
| v0.3 | Site ve IDE aynı renklendiriciyi kullanıyor (tek kaynak) | ✅ |
| v0.4 | **Generic tipler**: struct/enum/fn tip parametreleri, çıkarım | ✅ |
| v0.4 | Sonuc<T, H> standart kütüphanesi (Nar ile) | ✅ |
| v0.4 | **Masaüstü hedefi**: nar build --target masaustu | ✅ |
| v0.5 | **Arayüzler (interface)**: nominal uyum, generic sınırlama | ✅ |
| v0.5 | Standart kütüphane: dosya, girdi, zaman | ✅ |
| v0.5 | **Self-hosting adım 1**: lexer Nar diliyle (derleyici/lexer.nar) | ✅ |
| v0.6 | **Çıplak enum varyantları**: Hava.Yagmurlu yerine Yagmurlu | ✅ |
| v0.6 | **Arayüz katmanı** (araclar/arayuz.nar): Gorunum ağacı, Uygulama<D> | ✅ |
| v0.6 | Sahte DOM (testler/sahte_dom.js): arayüz tarayıcısız test ediliyor | ✅ |
| v0.6 | Karakter kodu: `"A".kodu()` ve `koddan(65)` | ✅ |
| v0.7 | **Self-hosting adım 2**: çözümleyici (parser) Nar diliyle | ✅ |
| v0.7 | S-ifadesi karşılaştırması (ast.nar + narc/sifade.py) | ✅ |
| v0.7 | **Self-hosting adım 3**: tip sistemi Nar diliyle (tipler.nar) | ✅ |
| v0.8 | **Blok ifadesi**: if/match dallarında birden çok satır | ✅ |
| v0.8 | **Self-hosting adım 4a**: denetleyicinin bildirim aşaması | ✅ |
| v0.8 | **Konum bilgisi**: AST satır/sütun taşıyor, konumlar da doğrulanıyor | ✅ |
| v0.6 | **Mobil hedef**: nar build --target mobil (Capacitor projesi) | ⚠️ cihazda denenmedi |

**Testler:** 247, hepsi geçiyor · `python -m unittest discover -s testler`
**Son commit:** `1b2a6aa` (bir sonraki: konum bilgisi)
**Nar ile yazılan kod:** ~7000 satır (`araclar/`, `derleyici/`, `ornekler/`, `testler/nar/`)

## Sırada (öncelik sırasıyla)

- [x] ~~**1. interface (trait)**~~ — bitti.
- [x] ~~**2. Standart kütüphane**~~ — bitti.
- [x] ~~**3. UI katmanı**~~ — dil özelliği olarak değil, Nar ile yazılmış
      kütüphane olarak yapıldı: `araclar/arayuz.nar`. Generic ve arayüzler
      hazır olduğu için dile yeni sözdizimi eklemeye gerek kalmadı.
- [x] ~~**4. Mobil hedef**~~ — `nar build --target mobil` Capacitor projesi
      üretiyor. **Doğrulanan:** dosyalar eksiksiz, JSON'lar geçerli, uygulama
      kimliği Android/iOS kuralına uyuyor, sayfa 280px'e kadar taşmıyor,
      dokunma hedefleri 44px (tarayıcıda ölçüldü).
      **Doğrulanmayan:** gerçek bir Android/iOS cihazında çalıştırma —
      bu makinede Android Studio ve Xcode yok.
- [x] ~~**5. Self-hosting: lexer ve parser**~~ — `derleyici/lexer.nar`,
      `derleyici/ast.nar`, `derleyici/parser.nar`. Doğrulama: iki
      çözümleyicinin ürettiği ağaçlar S-ifadesi olarak karşılaştırılıyor;
      projedeki 22 `.nar` dosyasında birebir aynı.
- [x] ~~**6a. Tip sistemi**~~ — `derleyici/tipler.nar`. Doğrulama: iki
      taraf aynı 40 tipi kurar; atanabilirlik, ortak tip ve birleştirme
      40×40 çift üzerinde karşılaştırılır (1600 çift × 3 işlem), ayrıca
      yazım, tembel alan çözümü ve tip değişkeni arama.
- [x] ~~**6b-1. Denetleyici: bildirim aşaması**~~ —
      `derleyici/denetleyici.nar` + `derleyici/denetle.nar`. Kapsanan:
      struct/enum/arayüz/takma ad toplama, tip ifadelerinin çözümlenmesi,
      fonksiyon imzaları, üstlenilen arayüzlerin doğrulanması, `main`
      denetimi. 37 örnekte iki taraf birebir aynı hata listesini üretiyor.
- [ ] **6b-2. Denetleyici: gövde denetimi** — ifadeler ve deyimler.
      En büyük parça. Artık AST konum taşıdığı için hatalar konumlu
      bildirilebilir (`d.konum`). Sıra önerisi: ifadeler (literal → ad →
      ikili işleç → çağrı → alan erişimi), sonra deyimler, sonra akış
      çözümlemesi (dönüş yolu, match tamlığı, akış daraltma).
      Karşılaştırma artık mesaj + satır + sütun düzeyinde yapılabilir.
- [x] ~~**6b-3. Konum bilgisi**~~ — `IfadeD`, `DeyimD`, `DesenD`, `OgeD`
      sarmalayıcıları. `yazModul` konumu yazmaz (mevcut testler değişmeden
      geçti); `yazModulKonumlu` yazar ve 26 dosyada konumlar birebir aynı.
- [ ] **7. IDE'yi arayüz kütüphanesiyle yeniden yaz** — IDE şu an DOM'a elle
      çiziyor; `Gorunum` ağacına taşınırsa hem kütüphane gerçek bir yükte
      denenmiş olur hem de IDE kodu kısalır.
- [ ] **8. Biçimlendirici kusuru** — çok satırlı `if` koşulunun devam satırı
      gövdeyle aynı girintiye düşüyor (`derleyici/parser.nar` içindeki uzun
      `||` zincirinde görülür). Okunurluğu bozuyor, anlamı değil.

## Devam etmek için

```bash
cd C:\Users\mstfa\Desktop\yazılım_dili
python -m unittest discover -s testler     # her şey yeşil mi
git log --oneline | head -5                # nerede kalındı
```

Sonra yukarıdaki listede işaretsiz ilk maddeye devam et.
Her madde bitince: testleri çalıştır, siteyi yeniden üret
(`python site/uret.py`), commit et, bu dosyayı güncelle.

## Dilde bilinen kısıtlar

Bunlar hata değil, henüz yapılmamış şeyler. Nar ile kod yazarken karşına
çıkarsa şaşırma:

- ~~`match` ifadesi kollarında blok yazılamaz~~ — **çözüldü (v0.8).**
  `if` ve `match` dallarında blok yazılabiliyor; bloğun son satırı dalın
  değeri. Not: `derleyici/tipler.nar` bu özellikten önce yazıldığı için
  hâlâ çok sayıda küçük işleve bölünmüş durumda; istenirse sadeleştirilebilir.
- **Blok ifadesi yalnızca dallarda.** `let x = { ... }` diye serbest bir blok
  ifadesi yok; yalnızca `if`/`match` dallarında geçerli.
- **`fn` ifadesi ad ister.** `let f = fn (x: Int) ...` geçersiz;
  `let f = fn ic(x: Int) ...` ya da lambda (`|x| ...`) kullan.
- **Varsayılan parametre değeri yok.** İki ayrı işlev yaz.

## Değişmez kurallar

- Her yeni dil özelliği için **çalıştırma testi** yazılır (sadece tip testi yetmez).
- Site içeriği (`site/icerik.py`) dil değişince güncellenir; site üretimi
  örnekleri gerçekten çalıştırdığı için bozuk örnek üretimi durdurur.
- Dosyaya çok satırlı içerik yazarken **Write/Edit** kullanılır, heredoc değil.
  (Bu oturumda heredoc dört kez `\n` kaçışını bozdu.)
- Commit mesajlarında **backtick kullanılmaz** — kabuk onu komut sanıp yutuyor.
- Commit mesajları Türkçe, ne değiştiğini ve nedenini anlatır.
- Nar kaynakları `nar fmt --denetle` ile düzenli tutulur (test bunu kontrol eder).

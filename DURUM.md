# Çalışma durumu

Bu dosya, uzun süren geliştirmede **nerede kalındığını** tutar. Oturum
kesilirse buradan devam edilir. Her önemli adımdan sonra güncellenir.

---

## Son güncelleme

**2026-09-11 01:20** — Arayüz (UI) katmanı bitti; sırada mobil hedef ve self-hosting parser.

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

**Testler:** 215, hepsi geçiyor · `python -m unittest discover -s testler`
**Son commit:** `4f2efed` (bir sonraki: arayüz katmanı)
**Nar ile yazılan kod:** ~2450 satır (`araclar/`, `derleyici/`, `ornekler/`, `testler/nar/`)

## Sırada (öncelik sırasıyla)

- [x] ~~**1. interface (trait)**~~ — bitti.
- [x] ~~**2. Standart kütüphane**~~ — bitti.
- [x] ~~**3. UI katmanı**~~ — dil özelliği olarak değil, Nar ile yazılmış
      kütüphane olarak yapıldı: `araclar/arayuz.nar`. Generic ve arayüzler
      hazır olduğu için dile yeni sözdizimi eklemeye gerek kalmadı.
- [ ] **4. Mobil hedef** — Capacitor ile Android/iOS paketleme. Not: bu
      makinede Android Studio yok, üretilen paket doğrulanamaz; dürüstlük
      gereği "üretildi ama cihazda denenmedi" diye işaretlenmeli.
- [ ] **5. Self-hosting'e devam** — lexer bitti (`derleyici/lexer.nar`,
      Python'unkiyle token token karşılaştırılıyor). Sırada **parser**:
      `derleyici/ast.nar` + `derleyici/parser.nar`. Aynı doğrulama yöntemi
      kullanılabilir — iki parser'ın ürettiği ağaçları karşılaştır.
- [ ] **6. IDE'yi arayüz kütüphanesiyle yeniden yaz** — IDE şu an DOM'a elle
      çiziyor; `Gorunum` ağacına taşınırsa hem kütüphane gerçek bir yükte
      denenmiş olur hem de IDE kodu kısalır.

## Devam etmek için

```bash
cd C:\Users\mstfa\Desktop\yazılım_dili
python -m unittest discover -s testler     # her şey yeşil mi
git log --oneline | head -5                # nerede kalındı
```

Sonra yukarıdaki listede işaretsiz ilk maddeye devam et.
Her madde bitince: testleri çalıştır, siteyi yeniden üret
(`python site/uret.py`), commit et, bu dosyayı güncelle.

## Değişmez kurallar

- Her yeni dil özelliği için **çalıştırma testi** yazılır (sadece tip testi yetmez).
- Site içeriği (`site/icerik.py`) dil değişince güncellenir; site üretimi
  örnekleri gerçekten çalıştırdığı için bozuk örnek üretimi durdurur.
- Dosyaya çok satırlı içerik yazarken **Write/Edit** kullanılır, heredoc değil.
  (Bu oturumda heredoc dört kez `\n` kaçışını bozdu.)
- Commit mesajlarında **backtick kullanılmaz** — kabuk onu komut sanıp yutuyor.
- Commit mesajları Türkçe, ne değiştiğini ve nedenini anlatır.
- Nar kaynakları `nar fmt --denetle` ile düzenli tutulur (test bunu kontrol eder).

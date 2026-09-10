# Çalışma durumu

Bu dosya, uzun süren geliştirmede **nerede kalındığını** tutar. Oturum
kesilirse buradan devam edilir. Her önemli adımdan sonra güncellenir.

---

## Son güncelleme

**2026-09-11 01:00** — IDE tamamen Nar'a taşındı; generic tiplere başlanıyor.

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

**Testler:** 150, hepsi geçiyor · `python -m unittest discover -s testler`
**Son commit:** `47168a7`
**Nar ile yazılan kod:** ~1540 satır (`araclar/`, `testler/nar/`)

## Sırada (öncelik sırasıyla)

- [ ] **1. Generic tipler** — `struct Kutu<T>`, `enum Sonuc<T, H>`, `fn ilk<T>(...)`.
      Gereken parçalar:
      - `types.py`: `TypeVar`, `StructT`/`EnumT` üzerinde `type_params` ve
        `type_args`; `subst()` (yerine koyma) ve `unify()` (birleştirme)
      - `parser.py`: bildirimde `<T, U>`, kullanımda `Kutu<Int>`
      - `checker.py`: tip değişkenlerini bağlama, argümanlardan çıkarım
      - `backends/js.py`: silme (JS'te generic yok; `$defType` tip kodları
        uygulanmış argümanlarla yazılmalı)
- [ ] **2. interface (trait)** — ortak davranış tanımı; generic'ten sonra.
- [ ] **3. Standart kütüphane** — dosya okuma/yazma (Node hedefi), tarih/saat.
- [ ] **4. UI katmanı** — `component` / `view`. DOM bağlaması hazır olduğu
      için artık üstüne kurulabilir.
- [ ] **5. Self-hosting'e doğru** — derleyicinin parçalarını Nar'a taşımak.
      Lexer iyi bir başlangıç: `araclar/tarayici.nar` zaten yarı yolda.

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

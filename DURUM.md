# Çalışma durumu

Bu dosya, uzun süren geliştirmede **nerede kalındığını** tutar. Oturum
kesilirse buradan devam edilir. Her önemli adımdan sonra güncellenir.

---

## Son güncelleme

**2026-09-11 00:50** — Generic tipler ve masaüstü hedefi bitti; interface'e geçiliyor.

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

**Testler:** 178, hepsi geçiyor · `python -m unittest discover -s testler`
**Son commit:** `d74b0af`
**Nar ile yazılan kod:** ~1703 satır (`araclar/`, `testler/nar/`)

## Sırada (öncelik sırasıyla)

- [ ] **1. interface (trait)** — ortak davranış tanımı.
      `interface Yazdirilabilir { fn yaz() -> String }` ve
      `struct X: Yazdirilabilir { ... }`. Generic ile birleşince
      `fn hepsiniYaz<T: Yazdirilabilir>(l: [T])` yazılabilir olur.
- [ ] **2. Standart kütüphane** — dosya okuma/yazma (Node hedefi), tarih/saat,
      daha fazla matematik.
- [ ] **3. UI katmanı** — `component` / `view`. DOM bağlaması hazır olduğu
      için artık üstüne kurulabilir.
- [ ] **4. Mobil hedef** — Capacitor ile Android/iOS paketleme. Not: bu
      makinede Android Studio yok, üretilen paket doğrulanamaz; dürüstlük
      gereği "üretildi ama cihazda denenmedi" diye işaretlenmeli.
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

# Çalışma durumu

Bu dosya, uzun süren geliştirmede **nerede kalındığını** tutar. Oturum
kesilirse buradan devam edilir. Her önemli adımdan sonra güncellenir.

---

## Son güncelleme

**2026-09-10 23:39** — v0.2 + IDE tamamlandı, v0.2.5'e başlanıyor.

## Şu ana kadar biten

| Sürüm | Ne yapıldı | Durum |
|---|---|---|
| v0.1 | Lexer, parser, tip denetleyici, JS arka ucu, CLI | ✅ |
| v0.2 | Sadeleştirme: Int/Float uyumu, metin birleştirme, if/match ifadesi, tek satırlık fonksiyon, çok argümanlı print | ✅ |
| v0.2 | Belgeler sitesi (33 konu, örnekler üretimde çalıştırılıyor) | ✅ |
| v0.2 | Lambda gerektirmeyen liste işlemleri (toplam, ortalama, kat, buyukler…) | ✅ |
| v0.2 | Nar IDE — tarayıcıda editör, canlı denetim, çalıştır, JS'i gör | ✅ |

**Testler:** 127, hepsi geçiyor · `python -m unittest discover -s testler`
**Son commit:** `b64a7fb`

## Sırada (öncelik sırasıyla)

- [ ] **1. Birden çok hatayı birden bildirme** — şu an ilk hatada duruyor.
      `Checker.check()` içinde `raise self.errors[0]` var; hepsini toplayıp
      döndürmeli. CLI ve IDE hepsini göstermeli.
- [ ] **2. Generic tipler** — `struct Kutu<T>`, `enum Sonuc<T, H>`.
      Tip sistemine tip değişkeni ve yerine koyma (substitution) gerekir.
- [ ] **3. interface (trait)** — ortak davranış tanımı.
- [ ] **4. Standart kütüphane** — dosya okuma/yazma, JSON, tarih/saat.
      Not: dosya G/Ç yalnızca Node hedefinde anlamlı; tarayıcıda karşılığı yok.
- [ ] **5. `nar fmt`** — kod biçimlendirici (IDE'de "Düzenle" düğmesi).
- [ ] **6. UI katmanı başlangıcı** — `component` / `view`, DOM'a çizim.
      Kullanıcının asıl hedefi (masaüstü/mobil/web uygulaması) buradan geçiyor.

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
- Commit mesajları Türkçe, ne değiştiğini ve nedenini anlatır.

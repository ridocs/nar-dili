# Çalışma durumu

Bu dosya, uzun süren geliştirmede **nerede kalındığını** tutar. Oturum
kesilirse buradan devam edilir. Her önemli adımdan sonra güncellenir.

---

## Son güncelleme

**2026-09-11 00:05** — DOM bağlaması bitti; IDE'yi Nar'a taşıma sürüyor.

## Şu ana kadar biten

| Sürüm | Ne yapıldı | Durum |
|---|---|---|
| v0.1 | Lexer, parser, tip denetleyici, JS arka ucu, CLI | ✅ |
| v0.2 | Sadeleştirme: Int/Float uyumu, metin birleştirme, if/match ifadesi, tek satırlık fonksiyon, çok argümanlı print | ✅ |
| v0.2 | Belgeler sitesi (33 konu, örnekler üretimde çalıştırılıyor) | ✅ |
| v0.2 | Lambda gerektirmeyen liste işlemleri (toplam, ortalama, kat, buyukler…) | ✅ |
| v0.2 | Nar IDE — tarayıcıda editör, canlı denetim, çalıştır, JS'i gör | ✅ |
| v0.2.5 | Tüm tip hataları tek seferde bildiriliyor | ✅ |
| v0.2.5 | IDE masaüstü uygulaması (pywebview / Edge --app) | ✅ |
| v0.2.5 | Kütüphane modu (--kutuphane): Nar ile JS kütüphanesi yazma | ✅ |
| v0.2.5 | Renklendirici Nar ile yeniden yazıldı, IDE onu kullanıyor | ✅ |
| v0.2.5 | Metin işlemlerinde O(n²) → O(n) önbellek düzeltmesi | ✅ |
| v0.3 | Sayfa (DOM) bağlaması: Element tipi, bul/olustur/dinle | ✅ |

**Testler:** 132, hepsi geçiyor · `python -m unittest discover -s testler`
**Son commit:** `20fc796`

## Sırada (öncelik sırasıyla)

**Kullanıcının açık isteği:** IDE'yi olabildiğince Nar diliyle yazmak
(şu ana kadar: renklendirici taşındı) ve masaüstü uygulaması olarak
geliştirmek (yapıldı).

- [ ] **1. Kod biçimlendirici** — `araclar/bicimlendirici.nar` (Nar ile),
      `nar fmt` komutu ve IDE'de "Düzenle" düğmesi.
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

# Nar — Yol haritası

Hedef: **tek kaynaktan web, masaüstü, Linux, Android ve iOS.**

Bu belge, o hedefe hangi sırayla gidileceğini ve her adımın neyi çözdüğünü
anlatır. Her sürümün **bitti sayılma ölçütü** yazılıdır — "yapıldı" demek için
o ölçütün doğrulanması gerekir.

---

## ✅ v0.1 — Çekirdek dil (tamamlandı)

Sözdizimi, tip sistemi ve çalışan bir JavaScript arka ucu.

- Lexer, parser, tip denetleyici, JS kod üreteci
- struct, enum, desen eşleme, opsiyoneller, lambda, modüller
- `nar run | build | check | emit`, `--target js|web`
- 91 test (ön uç + uçtan uca Node çalıştırma)

**Ölçüt:** ✅ `python -m unittest discover -s testler` tamamı geçiyor;
`ornekler/` altındaki programlar hem Node'da hem tarayıcıda doğru çalışıyor.

---

## ✅ v0.2 — Dili yeni başlayana göre sadeleştirmek (tamamlandı)

Çekirdek çalışıyordu ama yeni başlayanın en çok takıldığı yerler duruyordu.
Bu sürüm platform eklemedi; **dilin kendisini** rahatlattı.

| Yapıldı | Ne değişti |
|---|---|
| Sayı uyumlanması | `1 + 2.0` çalışır, sonuç `Float`. `float(x)` yazma zorunluluğu kalktı |
| Metin birleştirme | `"yaş: " + 25` çalışır; `str(...)` gerekmiyor |
| `if` **ifade** olarak | `let x = if a { 1 } else { 2 }` |
| `match` **ifade** olarak | `let ad = match n { 1 -> "bir"  _ -> "çok" }` |
| Tek satırlık fonksiyon | `fn kare(x: Int) -> Int = x * x` |
| Çok argümanlı `print` | `print("ad:", ad, "yaş:", yas)` |
| Matematik yerleşikleri | `sqrt(16)` çalışır; tam sayı da kabul edilir |
| `+=` `-=` `*=` `/=` `%=` | Lexer bunları hiç üretmiyordu, eklendi |
| Belgeler sitesi | 32 konu, açıklama + çalışan örnek + gerçek çıktı |

**Ölçüt:** ✅ 120 test geçiyor; site üretimi her örneği derleyip çalıştırıyor.

---

## v0.2.5 — Dili büyütmek

Sadeleşme tamam; sırada ölçek için gereken yapı taşları var.

| İş | Neden |
|---|---|
| Kullanıcı tanımlı generic (`struct Kutu<T>`) | `Sonuc<T, H>` yazılamadan hata yönetimi tekrara düşüyor |
| `interface` (trait) | Ortak davranış tanımı; `Yazdirilabilir`, `Karsilastirilabilir` |
| Adlandırılmış ve varsayılan argümanlar | `slice(a)` gibi çağrılar; şu an tüm argümanlar zorunlu |
| Standart kütüphane genişletme | dosya G/Ç, JSON, tarih/saat, düzenli ifade |
| Birden çok hatayı birden bildirme | Şu an ilk hatada duruyor; hepsini listelemek daha hızlı düzelttirir |

**Ölçüt:** `Sonuc<T, H>` generic enum'u standart kütüphanede tanımlanabiliyor;
derleyici bir dosyadaki tüm tip hatalarını tek seferde raporluyor.

---

## v0.3 — Arayüz katmanı (asıl kilit)

"Uygulama yapabilmek" bu adımda gerçekleşir. Bildirimsel, tip denetimli bir
bileşen modeli; her arka uç bunu kendi yerel arayüz sistemine çevirir.

```nar
component Sayac {
  var deger: Int = 0

  fn view() -> Gorunum {
    return Sutun {
      Metin("Sayı: ${self.deger}")
      Dugme("Artır", || self.deger = self.deger + 1)
    }
  }
}
```

- `component` / `view` sözdizimi ve tip denetimi
- Tek yönlü veri akışı + durum değişiminde yeniden çizim
- Yerleşim kutusu (Satır, Sütun, Yığın), metin, düğme, giriş, liste, resim
- Stil belirteçleri (renk, boşluk, kenarlık) — platformlar arası ortak alt küme
- JS arka ucunda DOM'a çizim (küçük bir VDOM ile)

**Ölçüt:** Aynı `.nar` kaynağından üretilen sayaç uygulaması tarayıcıda
tıklanabiliyor; ekran görüntüsüyle doğrulanmış.

---

## v0.4 — Platform paketleyicileri

Arayüz katmanı hazır olunca, hedefler paketleme işidir:

| Komut | Ürettiği | Dayandığı |
|---|---|---|
| `nar build --target web` | statik site (HTML + JS) | mevcut JS arka ucu |
| `nar build --target desktop` | Windows/macOS/Linux uygulaması | Tauri (küçük ikili) |
| `nar build --target android` | `.apk` | Capacitor |
| `nar build --target ios` | Xcode projesi | Capacitor |
| `nar build --target linux` | tek dosya CLI ikilisi | Node SEA ya da C arka ucu |

**Ölçüt:** Tek bir kaynaktan beş hedef de üretiliyor; en az masaüstü ve Android
çıktısı gerçek cihazda açılıyor.

---

## v0.5 — Native arka uç (Dart/Flutter)

JS arka ucu her yere ulaşır ama mobilde native akıcılık ve başlangıç süresi
istiyorsak ikinci bir kod üreteci gerekir.

- `backends/dart.py` — Nar AST → Dart
- `component` → Flutter `Widget`
- Aynı kaynak, `--target android --native` ile Flutter üzerinden derlenir

**Ölçüt:** `ornekler/` altındaki tüm programlar hem JS hem Dart arka ucunda
aynı çıktıyı veriyor (ortak test paketi iki arka uçta da geçiyor).

---

## v1.0 — Kendi kendini derleme (self-hosting)

Nar derleyicisinin Nar ile yeniden yazılması. Bir dilin olgunluk sınavı budur:
kendi karmaşıklığını taşıyabiliyor mu?

- `narc` kaynağının Nar'a çevrilmesi
- Python derleyicisiyle derlenen Nar derleyicisi, kendisini derleyebilmeli
- Üretilen iki derleyici aynı çıktıyı vermeli (bit düzeyinde aynı)

**Ölçüt:** Üç aşamalı bootstrap doğrulaması geçiyor
(`derleyici₁(kaynak) = derleyici₂`, `derleyici₂(kaynak) = derleyici₃`,
`derleyici₂ == derleyici₃`).

---

## Kararlaştırılmamış sorular

Bunlar henüz cevaplanmadı; zamanı gelince tartışılacak:

- **Bellek yönetimi:** JS/Dart arka uçlarında çöp toplayıcı hazır geliyor.
  C arka ucu eklenirse: çöp toplayıcı mı, sahiplik modeli mi?
- **Eşzamanlılık:** `async/await` mi, yoksa yapısal eşzamanlılık mı?
- **Hata yönetimi:** Yalnızca `Sonuc<T, H>` mi, yoksa `try` benzeri bir kısayol mu?
- **Paket yöneticisi:** `nar.toml` + merkezi kayıt defteri ne zaman gerekli olur?

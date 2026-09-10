# Nar

**Tek kaynaktan web, masaüstü, Linux, Android ve iOS.**
Statik tipli, `null`'ı olmayan, derlenen bir programlama dili.

> **Durum: v0.1 — çekirdek dil çalışıyor.**
> Lexer, parser, tip denetleyici ve JavaScript kod üreteci hazır ve test edilmiş
> durumda. Platform paketleyicileri (`--target desktop|android|ios`) henüz yok;
> yol haritası `YOL-HARITASI.md` dosyasında.

---

## Hızlı başlangıç

Gereken: **Python 3.11+** (derleyici) ve **Node.js 18+** (üretilen kodu çalıştırmak için).

```bash
# Bir programı derle ve çalıştır
./nar run ornekler/merhaba.nar          # Linux / macOS / Git Bash
nar.cmd run ornekler\merhaba.nar        # Windows

# Yalnızca tip denetimi
./nar check ornekler/yapilacaklar.nar

# JavaScript üret
./nar build ornekler/merhaba.nar -o cikti/merhaba.js

# Tarayıcıda açılan tek dosyalık HTML üret
./nar build ornekler/merhaba.nar --target web -o cikti/merhaba.html

# Üretilen kodu ekrana yaz (ne ürettiğini görmek için)
./nar emit ornekler/merhaba.nar
```

Testler:

```bash
python -m unittest discover -s testler
```

---

## Dil, on satırda

```nar
struct Nokta {
  x: Float
  y: Float

  fn uzunluk() -> Float {
    return sqrt(self.x * self.x + self.y * self.y)
  }
}

enum Sonuc {
  Tamam(Int)
  Hata(String)
}

fn bol(a: Int, b: Int) -> Sonuc {
  if b == 0 {
    return Sonuc.Hata("sıfıra bölme")
  }
  return Sonuc.Tamam(a / b)
}

fn main() {
  print("uzaklık: ${Nokta { x: 3.0, y: 4.0 }.uzunluk()}")     // 5.0

  match bol(10, 0) {
    Sonuc.Tamam(n) -> print("sonuç ${n}")
    Sonuc.Hata(m) -> print("hata: ${m}")                       // hata: sıfıra bölme
  }

  let kareler = [1, 2, 3, 4].map(|x| x * x)                    // [1, 4, 9, 16]
  print("çiftler: ${kareler.filter(|x| x % 2 == 0)}")          // [4, 16]

  var ad: String? = none
  print(ad ?? "isimsiz")                                       // isimsiz
}
```

### Öne çıkan kararlar

| Özellik | Nar'da |
|---|---|
| Boş değer | `null` yok. `T?` var, açmadan kullanılamaz. `??`, `?.`, `!` ve akış daraltma |
| Değişkenlik | `let` değişmez (varsayılan), `var` değişken |
| Hata sınıfları | `match` enum üzerinde **tam olmak zorunda**; eksik varyant derleme hatası |
| Sayılar | `Int` ve `Float` karışmaz. `1 + 2.0` derlenmez — `float(1) + 2.0` gerekir |
| Fonksiyonlar | İmzalar açık, gövde içi tip çıkarımı otomatik |
| Dönüş yolu | Değer döndüren fonksiyon her yolda dönmek zorunda |
| Sınır kontrolü | Liste ve metin dizinlemesi çalışma zamanında kontrol edilir |
| Türkçe | Tanımlayıcılarda Türkçe harfler serbest; `upperTr()` / `lowerTr()` doğru `i/İ/ı/I` davranışı verir |

Tam tanım: **[TASARIM.md](TASARIM.md)**

---

## Neden çok arka uçlu bir derleyici?

Tek bir ön uç (sözdizimi + tipler) ve hedefe göre değişen kod üreticileri:

```
kaynak.nar
   │
   ├─► Lexer ─► Parser ─► Tip denetleyici        ← hedeften bağımsız
   │
   └─► Kod üreteci
         ├── js.py    ✅ JavaScript  → web, Node, (Tauri/Capacitor ile masaüstü + mobil)
         ├── dart.py  ⏳ Dart        → Flutter ile native Android / iOS / masaüstü
         └── c.py     ⏳ C           → native Linux ikili dosyaları
```

Yeni bir platform eklemek, yeni bir dil tasarlamak değil; `narc/backends/` altına
bir dosya yazmak demektir. v0.1'de JavaScript arka ucu bitmiş durumda.

## Proje düzeni

```
narc/                 derleyici (Python)
  lexer.py            kaynak → token
  parser.py           token → AST
  nar_ast.py          AST düğümleri
  types.py            tip sistemi
  checker.py          tip denetimi, akış daraltma, tamlık kontrolü
  driver.py           içe aktarma çözümleme + derleme boru hattı
  __main__.py         komut satırı arayüzü
  backends/js.py      JavaScript kod üreteci
  runtime/            üretilen koda gömülen çalışma zamanı
ornekler/             örnek Nar programları
testler/              91 test (ön uç + uçtan uca çalıştırma)
TASARIM.md            dil spesifikasyonu
YOL-HARITASI.md       sıradaki adımlar
```

## Örnekler

| Dosya | Gösterdiği |
|---|---|
| `ornekler/merhaba.nar` | Dilin küçük turu: struct, enum, liste işlemleri, opsiyoneller |
| `ornekler/yapilacaklar.nar` | Modül içe aktarma, metotlar, `?.`, filtreleme ve biçimlendirme |
| `ornekler/metin_araclari.nar` | İçe aktarılabilir yardımcı modül |

## Sınırlar (v0.1)

Bunlar bilinen ve kasıtlı eksiklerdir, sürpriz değil:

- `if` bir **deyimdir**, ifade değil (`let x = if a { 1 } else { 2 }` çalışmaz)
- Kullanıcı tanımlı **generic** tipler yok (`[T]` ve `{K: V}` yerleşik generic'tir)
- Arayüz / trait / kalıtım yok
- Hata yönetimi `enum` ile yapılır; `try`/`catch` yok
- Eşzamanlılık (`async`) yok
- Standart kütüphane küçük — dosya, ağ, tarih işlemleri yok
- Bağlamı olmayan lambda'da parametre tipi yazılmalı (`|x: Int| x + 1`)

# Nar

**Tek kaynaktan web, masaüstü, Linux, Android ve iOS.**
Statik tipli, `null`'ı olmayan, derlenen bir programlama dili.

> **Durum: v0.2 — çekirdek dil çalışıyor, yeni başlayana göre sadeleşti.**
> Lexer, parser, tip denetleyici ve JavaScript kod üreteci hazır ve test edilmiş
> durumda. Platform paketleyicileri (`--target desktop|android|ios`) henüz yok;
> yol haritası `YOL-HARITASI.md` dosyasında.

**📖 [Dil rehberi](cikti/site/index.html)** — dilin tamamı, açıklamalar ve
çalışan örneklerle. Üretmek için: `python site/uret.py`, sonra
`cikti/site/index.html` dosyasını tarayıcında aç.

## Hangi hedefler çalışıyor?

| Hedef | Komut | Durum |
|---|---|---|
| Terminal / Node | `nar run program.nar` | ✅ |
| Web sayfası | `nar build program.nar --target web` | ✅ |
| Masaüstü uygulaması | `nar build program.nar --target masaustu` | ✅ |
| Android / iOS | Capacitor ile paketleme | ⏳ planlanıyor |
| Native ikili (Linux) | C ya da Dart arka ucu | ⏳ planlanıyor |

Masaüstü hedefi kendi başına çalışan bir klasör üretir: içinde programın
HTML'i, onu kendi penceresinde açan bir başlatıcı ve Windows için
`baslat.cmd` bulunur. Gereken tek şey Python; `pip install pywebview`
kuruluysa gerçek bir yerel pencerede, değilse tarayıcının uygulama
penceresinde açılır.

---

## Nasıl denerim?

Gereken: **Python 3.11+** (derleyici) ve **Node.js 18+** (üretilen kodu çalıştırmak için).
İkisi de kuruluysa kurulacak başka bir şey yok — derleyici olduğu gibi çalışır.

**1. Klasöre gir** (PowerShell):

```powershell
cd C:\Users\mstfa\Desktop\yazılım_dili
```

**2. Hazır oyun alanını çalıştır:**

```powershell
.\nar.cmd run deneme.nar
```

`deneme.nar` dosyasını aç, istediğin gibi değiştir, tekrar çalıştır.
Dilin çoğu özelliği orada yorumlarla anlatılıyor.

**3. Örnekleri gez:**

```powershell
.\nar.cmd run ornekler\merhaba.nar
.\nar.cmd run ornekler\algoritmalar.nar
.\nar.cmd run ornekler\yapilacaklar.nar
```

**4. Kasten hata yap** — derleyicinin ne söylediğini görmek öğreticidir.
`deneme.nar` içinde `let x = 1` yazıp altına `x = 2` ekle ve çalıştır.

> **Not:** Nar'ın etkileşimli konsolu (REPL) yok. Programı dosyaya yazıp
> `run` ile çalıştırıyorsun.

---

## Komutlar

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

# Masaüstü uygulaması olarak paketle (kendi penceresinde açılır)
./nar build ornekler/sayac_web.nar --target masaustu -o cikti/sayacim

# Üretilen kodu ekrana yaz (ne ürettiğini görmek için)
./nar emit ornekler/merhaba.nar

# Kodu yeniden girintile ve düzenle
./nar fmt deneme.nar
./nar fmt deneme.nar --goster     # dosyayı değiştirmeden göster
./nar fmt deneme.nar --denetle    # düzensizse 1 döner (CI için)
```

Testler:

```bash
python -m unittest discover -s testler
```

---

## Nar IDE

Dil için bir masaüstü düzenleyici. Kendi penceresinde açılır, kurulum
gerektirmez:

```powershell
ide.cmd                 # masaüstü penceresi
ide.cmd --tarayici      # tarayıcı sekmesi olarak
```

| Özellik | Nasıl |
|---|---|
| Yazarken tip denetimi | Hatalı satır kenarda işaretlenir, altta mesaj görünür |
| Çalıştır | `Ctrl+Enter` — çıktı yandaki panelde |
| Düzenle (biçimlendir) | `Ctrl+Shift+D` |
| Kaydet | `Ctrl+S` |
| Hata kutusuna tıkla | İlgili satıra gider |
| "JavaScript'i gör" | Nar'ın ürettiği kodu gösterir — öğretici |

**IDE'nin kendisi kısmen Nar ile yazılmıştır.** Sözdizimi renklendirme,
kod biçimlendirme, imleç konumu ve otomatik girinti hesabı
`araclar/*.nar` dosyalarındadır; sunucu bunları derleyip tarayıcıya
verir. Alt çubuktaki "araçlar: Nar ile yazıldı" bunu gösterir.

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
| Sayılar | `Int` ve `Float` birlikte kullanılır, sonuç `Float` olur. Bölmede tip belirleyici: `7/2` → `3`, `7/2.0` → `3.5` |
| Metinler | `"yaş: " + 25` çalışır — sayı otomatik yazıya döner |
| `if` / `match` | Hem deyim hem **ifade**: `let x = if a { 1 } else { 2 }` |
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
  bicim.py            nar fmt (biçimlendiriciyi Nar'dan çalıştırır)
  __main__.py         komut satırı arayüzü
  backends/js.py      JavaScript kod üreteci
  highlight.py        sözdizimi renklendirme (belgeler sitesi için)
  runtime/            üretilen koda gömülen çalışma zamanı
araclar/              **Nar diliyle yazılmış araçlar**
  tarayici.nar        ortak lexer yardımcıları
  renklendirici.nar   sözdizimi renklendirme
  bicimlendirici.nar  kod biçimlendirme
  ide_araclari.nar    IDE'nin kullandığı kütüphane
ide/                  masaüstü düzenleyici
  masaustu.py         uygulama penceresi
  sunucu.py           yerel sunucu + derleme/çalıştırma
  arayuz.html         editör arayüzü
site/                 belgeler sitesi üreteci
  icerik.py           bölümler, açıklamalar, örnekler
  uret.py             örnekleri çalıştırıp HTML üretir
ornekler/             örnek Nar programları
testler/              145 test (ön uç + uçtan uca + örnekler + biçimlendirici)
TASARIM.md            dil spesifikasyonu
YOL-HARITASI.md       sıradaki adımlar
DURUM.md              uzun geliştirmede nerede kalındığı
```

## Örnekler

| Dosya | Gösterdiği |
|---|---|
| `ornekler/merhaba.nar` | Dilin küçük turu: struct, enum, liste işlemleri, opsiyoneller |
| `ornekler/yapilacaklar.nar` | Modül içe aktarma, metotlar, `?.`, filtreleme ve biçimlendirme |
| `ornekler/metin_araclari.nar` | İçe aktarılabilir yardımcı modül |
| `ornekler/sayac_web.nar` | Tarayıcıda çalışan uygulama: DOM, düğme, olay dinleme |
| `deneme.nar` | Oyun alanı — yorumlarla anlatılmış, değiştirip çalıştırman için |
| `araclar/*.nar` | Nar'ın kendi araçları — dilin kendini yazması |

## Belgeler sitesi

```bash
python site/uret.py            # cikti/site/index.html
```

Sitedeki bütün çıktılar, sayfa üretilirken örnekler **gerçekten derlenip
çalıştırılarak** alınır. Bir örnek bozulursa üretim durur — yani site hiçbir
zaman çalışmayan kod göstermez.

## Sınırlar

Bunlar bilinen ve kasıtlı eksiklerdir, sürpriz değil:

- Kullanıcı tanımlı **generic** tipler yok (`[T]` ve `{K: V}` yerleşik generic'tir)
- Arayüz / trait / kalıtım yok
- Hata yönetimi `enum` ile yapılır; `try`/`catch` yok
- Eşzamanlılık (`async`) yok
- Standart kütüphane küçük — dosya, ağ, tarih işlemleri yok
- Bağlamı olmayan lambda'da parametre tipi yazılmalı (`|x: Int| x + 1`)
- Sözdizimi hatalarında yalnızca ilki bildirilir (tip hatalarının hepsi bildirilir)
- Sayfa (DOM) işlemleri yalnızca tarayıcı hedefinde çalışır

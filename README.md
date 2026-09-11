# Nar

Az bilgiyle çok şey yapabileceğin bir programlama dili. Tek kaynaktan
terminal, web, masaüstü ve mobil uygulama çıkar.

Anahtar kelimeler İngilizce (`fn`, `let`, `if`), belgeler ve hata mesajları
Türkçe.

```nar
enum Hava {
  Gunesli
  Yagmurlu
  Karli
}

fn oneri(h: Hava) -> String = match h {
  Gunesli -> "şapka al"
  Yagmurlu -> {
    let arac = "şemsiye"
    "${arac} al"
  }
  Karli -> "atkı al"
}

fn main() {
  print(oneri(Yagmurlu))
}
```

## Kurulum

Gereken: **Python 3.10+**. Web ve sunucu hedefleri için ayrıca **Node.js**.

```
git clone https://github.com/<kullanıcı>/nar-dili.git
cd nar-dili
.\nar.cmd run ornekler\merhaba.nar
```

Kurulum adımı yok; depo kendi başına çalışır.

## Çalıştırma hedefleri

Aynı kaynak, farklı yerlerde:

| Komut | Ne üretir | Gereken |
|---|---|---|
| `nar calistir program.nar` | Nar'ın **kendi sanal makinesi** | yalnızca Python |
| `nar run program.nar` | Node ile çalıştırır | Node.js |
| `nar build program.nar --target web` | tek dosyalık HTML | — |
| `nar build program.nar --target masaustu` | kendi penceresinde açılan uygulama | Python |
| `nar build program.nar --target ghb` | tek dosyalık `.ghb` uygulaması | Python |
| `nar build program.nar --target mobil` | Android/iOS (Capacitor) projesi | Node.js + Android Studio / Xcode |
| `nar build program.nar --target narb` | Nar bytecode | — |

`.ghb` dosyaları çift tıklamayla açılır:

```
nar uzanti-kur          bir kez çalıştır
```

## Dilde ne var

- **Tipler**: `Int`, `Float`, `Bool`, `String`, listeler, eşlemeler
- **Kendi tiplerin**: `struct`, `enum` (veri taşıyan varyantlarla), metotlar
- **`match`** — tamlık denetimi var: bir durumu unutursan derleyici söyler
- **Opsiyonel tipler** (`T?`, `??`, `?.`, `!`) — `null` hatası yok
- **Generic tipler**: `struct Kutu<T>`, `fn ilk<T>(l: [T]) -> T?`
- **Arayüzler** (`interface`) ve generic sınırlama (`<T: Yazdirilabilir>`)
- **Kapanışlar (closure)**, `map`/`filter`/`reduce` ve lambda gerektirmeyen
  kolay liste işlemleri (`toplam()`, `ciftler()`, `benzersiz()`)
- **Blok ifadeleri**: `if`/`match` dallarında birden çok satır
- **Metin gömme**: `"merhaba ${ad}"`
- **Sunucu**: HTTP sunucusu, yönlendirme, form ve JSON gövdesi, çerezler
- **Sayfa**: DOM bağlaması ve bildirimsel arayüz kütüphanesi

Tam anlatım ve çalışan örnekler için **belgeler sitesi**:
**<https://ridocs.github.io/nar-dili/>**

Site depodan yayınlanıyor; yayına giden dosya `docs/index.html`. İçerik ya da
tasarım değişince yeniden üretip birlikte commit'le:

```
python site/uret.py --cikti docs/index.html
```

Sitedeki bütün çıktılar üretim sırasında örnekler gerçekten derlenip
çalıştırılarak alınır; bir örnek kırılırsa üretim durur.

## Depoda ne var

```
narc/             Derleyici (Python)
  lexer.py          sözcüksel çözümleme
  parser.py         sözdizim çözümleme
  checker.py        tip denetimi
  backends/js.py    JavaScript üreteci
  bytecode.py       Nar bytecode'u
  vm.py             sanal makine
derleyici/        Derleyicinin Nar ile yazılmış parçaları
  lexer.nar         sözcüksel çözümleyici
  parser.nar        sözdizim çözümleyici
  tipler.nar        tip sistemi
  denetleyici.nar   tip denetleyici (bildirim aşaması)
araclar/          Nar ile yazılmış kütüphaneler
  arayuz.nar        bildirimsel arayüz
  web.nar           web sunucusu çatısı
  json.nar          JSON okuma/yazma
  bicimlendirici.nar  kod biçimlendirici (`nar fmt`)
ornekler/         Çalışan örnek programlar
testler/          Test paketi
site/             Belgeler sitesi üreteci
```

## Kendi kendini derlemeye doğru

Nar'ın derleyicisi Python ile yazıldı — bir dilin başlangıçta başka bir
dile ihtiyacı olur. Ama parçalar sırayla Nar'a taşınıyor:

```
nar ozdenetim derleyici/parser.nar --kutuphane
tamam — hata yok
```

Şu ana kadar Nar ile yazılanlar: sözcüksel çözümleyici, sözdizim
çözümleyici, tip sistemi, tip denetleyicinin bildirim aşaması, kod
biçimlendirici, sözdizimi renklendirici, JSON kütüphanesi, arayüz
kütüphanesi, web çatısı ve IDE'nin tüm davranışı.

Doğruluk ölçüsü şu: iki uygulama aynı kaynağı okuyup **aynı sonucu**
vermeli. Çözümleyiciler için ağaçlar S-ifadesi olarak karşılaştırılıyor
(konumlarıyla birlikte), tip sistemi için 1600 tip çifti, denetleyici
için hata listeleri.

## Testler

```
python -m unittest discover -s testler
```

Testler yalnızca iddiaları değil, programların **gerçekten çalıştığını**
doğrular: örnekler çalıştırılır, sunucu ayağa kaldırılıp istek atılır,
arayüz sahte bir DOM'da tıklanır, iki derleyici karşılaştırılır.

## Lisans

MIT — bkz. [LICENSE](LICENSE).

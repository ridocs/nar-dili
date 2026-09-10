# Nar — Dil Tasarımı (v0.1)

Nar; web, masaüstü, Linux, Android ve iOS için tek kaynaktan uygulama yazmayı
hedefleyen, statik tipli, derlenen bir programlama dilidir.

Bu belge **v0.1 çekirdeğinin** kesin tanımıdır. Burada yazan her şey uygulanmıştır;
uygulanmamış fikirler `YOL-HARITASI.md` dosyasındadır.

---

## 1. Temel kararlar ve gerekçeleri

| Karar | Gerekçe |
|---|---|
| Statik tipli, zorunlu fonksiyon imzaları, gövde içi tip çıkarımı | Hata mesajları net kalır; tam Hindley–Milner'in karmaşıklığı olmadan yazım rahatlığı |
| `null` yok, `T?` var | Milyar dolarlık hata sınıfı dilden çıkarılır; opsiyonel değer tip sisteminde görünür |
| Değişmezlik varsayılan (`let`), değişkenlik açık (`var`) | Yan etkiler okunabilir olur |
| Anahtar kelimeler İngilizce | Kod tanımlayıcıları taşınabilir kalsın |
| Noktalı virgül yok (satır sonu deyimi bitirir) | Görsel gürültü azalır |
| Çok arka uçlu derleyici | Tek ön uç + çok kod üreteci = tek dilden çok platform |

## 2. Derleyici boru hattı

```
kaynak.nar
   │
   ├─► Lexer      (narc/lexer.py)     → token akışı, konum bilgisiyle
   ├─► Parser     (narc/parser.py)    → AST  (narc/nar_ast.py)
   ├─► Checker    (narc/checker.py)   → tip denetimi + AST'ye tip notu düşme
   └─► Backend    (narc/backends/*)   → hedef kod
                    js.py  → JavaScript (web + Node)
```

Ön uç hedeften bağımsızdır. Yeni bir platform eklemek = yeni bir `backends/*.py`.

## 3. Sözcüksel yapı

**Yorum:** `// satır sonuna kadar` ve `/* blok */` (iç içe geçebilir).

**Tanımlayıcı:** `[A-Za-z_][A-Za-z0-9_]*` — Türkçe harfler tanımlayıcıda geçerlidir
(`ağırlık`, `İsim` yazılabilir), çünkü Unicode harfler kabul edilir.

**Sayı:** `42`, `1_000_000`, `0xFF`, `0b1010`, `3.14`, `1.5e-3`
Ondalık nokta veya üs varsa `Float`, yoksa `Int`.

**Metin:** `"merhaba"`, kaçışlar `\n \t \r \\ \" \0 \u{1F600}`
İçe gömme: `"Merhaba ${ad}, ${yas + 1} yaşındasın"`

**Satır sonu deyim bitirir.** Newline yalnızca bir deyimi bitirebilecek bir
token'dan sonra anlamlıdır (tanımlayıcı, literal, `)`, `]`, `}`, `?`, `!`,
`return`, `break`, `continue`). Bu sayede aşağıdaki ifade sorunsuz bölünebilir:

```nar
let toplam = a +
             b
```

## 4. Tipler

| Tip | Açıklama |
|---|---|
| `Int` | 64-bit tam sayı |
| `Float` | 64-bit kayan nokta |
| `Bool` | `true` / `false` |
| `String` | UTF-8 metin, değişmez |
| `Void` | değer yok (dönüş tipi yazılmayan fonksiyon) |
| `[T]` | `T` listesi |
| `{K: V}` | `K`'dan `V`'ye eşleme |
| `T?` | opsiyonel `T` — ya bir `T` ya da `none` |
| `(A, B) -> C` | fonksiyon tipi |
| `struct` / `enum` adı | kullanıcı tanımlı tip |

**Örtük dönüşüm yoktur.** `Int` ile `Float` doğrudan toplanmaz; `float(x)` gerekir.
Tek istisna: `T` değeri `T?` beklenen yere geçebilir (genişletme güvenlidir).

### Opsiyoneller

```nar
let a: Int? = 5
let b: Int? = none

let c = a ?? 0        // varsayılan verme          → Int
let d = a!            // zorla aç (none ise hata)  → Int
let n: String? = kisi?.adres?.sehir   // güvenli zincir → String?
```

Akış daraltma: `if a != none { /* burada a: Int */ }` içinde tip otomatik daralır.

## 5. Bildirimler

### Değişken

```nar
let x = 10              // değişmez, tip çıkarımı → Int
let y: Float = 2.5      // açık tip
var sayac = 0           // değişken
sayac = sayac + 1
```

### Fonksiyon

```nar
fn topla(a: Int, b: Int) -> Int {
  return a + b
}

fn selamla(ad: String) {     // dönüş tipi yoksa Void
  print("Merhaba ${ad}")
}
```

Parametre tipleri ve dönüş tipi **zorunlu açıktır**. Gövde içi her şey çıkarılır.

### Struct

```nar
struct Nokta {
  x: Float
  y: Float

  fn uzunluk() -> Float {
    return sqrt(self.x * self.x + self.y * self.y)
  }

  fn tasi(dx: Float, dy: Float) -> Nokta {
    return Nokta { x: self.x + dx, y: self.y + dy }
  }
}

let n = Nokta { x: 3.0, y: 4.0 }
print(n.uzunluk())          // 5
```

Alanlar `let` ile bağlanmış sayılır; `var` alan için `var x: Float` yazılır.

### Enum (etiketli birleşim)

```nar
enum Sonuc {
  Tamam(String)
  Hata(String, Int)
  Bos

  fn basarili() -> Bool {
    match self {
      Sonuc.Tamam(_) -> return true
      _ -> return false
    }
  }
}

let s = Sonuc.Hata("dosya yok", 404)
```

### Tip takma adı

```nar
type Kimlik = Int
type Sozluk = {String: [Int]}
```

## 6. Deyimler

```nar
if kosul {
  ...
} else if digerKosul {
  ...
} else {
  ...
}

while i < 10 {
  i = i + 1
  if i == 5 { continue }
  if i == 8 { break }
}

for i in 0..10 { }        // 0,1,...,9   (üst sınır hariç)
for i in 0..=10 { }       // 0,1,...,10  (üst sınır dahil)
for e in liste { }
for (k, v) in sozluk { }

return deger
```

`if` ve `while` başlıklarında süslü parantez gerekmez; koşul ifadesinde
struct/map literali doğrudan yazılamaz (parantez içine alınmalıdır).

### match

```nar
match sonuc {
  Sonuc.Tamam(mesaj) -> print("iyi: ${mesaj}")
  Sonuc.Hata(mesaj, kod) -> {
    print("kötü: ${mesaj} (${kod})")
  }
  Sonuc.Bos -> print("boş")
}
```

Desenler: enum varyantı (alt bağlamalarla), literal (`3`, `"a"`, `true`),
`_` (her şey), tanımlayıcı (bağlar). Enum üzerinde eşleme **tam olmak
zorundadır** — eksik varyant derleme hatasıdır.

## 7. İfadeler

Öncelik, düşükten yükseğe:

| Seviye | Operatörler |
|---|---|
| 1 | `??` |
| 2 | `\|\|` |
| 3 | `&&` |
| 4 | `==` `!=` |
| 5 | `<` `<=` `>` `>=` |
| 6 | `..` `..=` |
| 7 | `+` `-` |
| 8 | `*` `/` `%` |
| 9 | tekli `-` `!` |
| 10 | son ek: `.alan` `?.alan` `(çağrı)` `[dizin]` `!` |

**Lambda:** `|x| x * 2` veya `|x, y| { return x + y }`
Parametre tipleri **beklenen tipten** çıkarılır — yani bir argüman olarak ya da
tipi yazılmış bir değişkene verildiğinde:

```nar
let kareler = sayilar.map(|s| s * s)              // s: Int, bağlamdan
let ekle: (Int) -> Int = |x| x + 1                // bağlam: yazılan tip
```

Beklenen tip yoksa parametre tipi yazılmalıdır — derleyici bunu tahmin etmez:

```nar
let ekle = |x| x + 1                              // hata: tip çıkarılamıyor
let ekle = |x: Int| x + 1                         // doğru
```

**Liste ve eşleme literali:**

```nar
let l = [1, 2, 3]
let bos: [String] = []
let m = {"bir": 1, "iki": 2}
```

## 8. Yerleşik kütüphane (v0.1)

**Serbest fonksiyonlar:**
`print(v)` · `str(v)` · `len(v)` · `int(s) -> Int?` · `float(s) -> Float?`
`abs` · `min` · `max` · `sqrt` · `floor` · `ceil` · `round` · `pow` · `random()`
`panic(mesaj)` · `assert(kosul, mesaj)`

**String metotları:**
`len()` `upper()` `lower()` `trim()` `split(s)` `join(...)` `contains(s)`
`replace(a,b)` `startsWith(s)` `endsWith(s)` `slice(a,b)` `charAt(i)` `indexOf(s)`

**[T] metotları:**
`len()` `push(x)` `pop() -> T?` `contains(x)` `indexOf(x)` `slice(a,b)`
`reverse()` `join(sep)` `map(f)` `filter(f)` `reduce(f, baslangic)` `sort()` `first() -> T?` `last() -> T?`

**{K: V} metotları:**
`len()` `get(k) -> V?` `set(k, v)` `has(k)` `remove(k)` `keys() -> [K]` `values() -> [V]`

## 9. Modüller

```nar
import "matematik.nar"          // aynı dizinden
import "./yardim/dizge.nar"
```

Bir dosyadaki üst düzey `fn`, `struct`, `enum`, `type`, `let` bildirimleri
dışa açıktır. Döngüsel içe aktarma hatadır.

## 10. Giriş noktası

Programın `main` adlı, parametresiz bir fonksiyonu olmalıdır.
`nar run` bu fonksiyonu çağırır.

---

## 11. JavaScript arka ucunun eşleme kuralları

| Nar | JavaScript |
|---|---|
| `Int`, `Float` | `number` (`Int` bölmesi `Math.trunc` ile kırpılır) |
| `String` | `string` |
| `Bool` | `boolean` |
| `[T]` | `Array` |
| `{K: V}` | `Map` |
| `T?` / `none` | `null` |
| `struct` | `class` (alanlar + metotlar) |
| `enum` | `class` + `$tag` alanı + statik yapıcılar |
| `match` | `switch ($tag)` / karşılaştırma zinciri |
| `a..b` | `for` döngüsüne indirgenir (nesne üretilmez) |

Üretilen kod okunabilir, girintili ve `"use strict"` altındadır.
Çalışma zamanı yardımcıları `narc/runtime/nar_runtime.js` dosyasından gömülür.

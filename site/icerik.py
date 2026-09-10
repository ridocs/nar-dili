"""Belgeler sitesinin içeriği.

Her konunun `kod` alanı sayfada gösterilen örnektir. Site üretilirken bu kod
**gerçekten derlenip çalıştırılır** ve çıktısı sayfaya yazılır; yani sitedeki
hiçbir çıktı elle yazılmamıştır.

`tam` alanı verilirse çalıştırılacak program odur (kodda üst düzey bildirim
varsa gerekir); verilmezse `kod` otomatik olarak `fn main() { ... }` içine
sarılır.
"""

BASLIK = "Nar"
ALT_BASLIK = "Az bilgiyle çok şey yapabileceğin bir programlama dili"

GIRIS = """
Nar; web, masaüstü, Linux, Android ve iOS için tek kaynaktan uygulama yazmayı
hedefleyen bir programlama dilidir. Bu sayfa dilin <strong>tamamını</strong>
açıklamalarıyla ve çalışan örnekleriyle gösterir.
"""

NASIL_CALISTIRILIR = """
<p>Bilgisayarında <strong>Python</strong> ve <strong>Node.js</strong> kurulu olması yeterli.
Programını bir dosyaya yaz (örneğin <code>deneme.nar</code>) ve çalıştır:</p>
<pre class="komut"><code>cd C:\\Users\\mstfa\\Desktop\\yazılım_dili
.\\nar.cmd run deneme.nar</code></pre>
<p>Kodunu çalıştırmadan sadece kontrol ettirmek istersen
<code>.\\nar.cmd check deneme.nar</code> yeter. Web sayfası üretmek için
<code>.\\nar.cmd build deneme.nar --target web</code>.</p>
"""

# Sayfadaki her kod bloğunun altında gerçek çıktı görünür.
NOT_SARMAL = (
    "Aşağıdaki örneklerin çoğu <code>fn main() { ... }</code> içine yazılır; "
    "kısa tutmak için o sarmalayıcı gösterilmiyor. Üst düzey bildirim "
    "(<code>fn</code>, <code>struct</code>, <code>enum</code>) içeren örnekler tam gösterilir."
)


BOLUMLER = [
    # ------------------------------------------------------------ başlangıç
    {
        "id": "baslangic",
        "baslik": "Başlangıç",
        "konular": [
            {
                "id": "ilk-program",
                "baslik": "İlk program",
                "aciklama": """
Her Nar programı <code>main</code> adlı bir fonksiyonla başlar. Program
çalıştığında ilk olarak buranın içi yürütülür.
<code>print</code> ekrana bir şey yazar.
""",
                "kod": '''fn main() {
  print("Merhaba dünya!")
}''',
                "tam": '''fn main() {
  print("Merhaba dünya!")
}''',
            },
            {
                "id": "yorumlar",
                "baslik": "Yorumlar",
                "aciklama": """
Yorum, programın çalışmasını etkilemeyen not demektir. Kendine ya da kodu
okuyacak kişiye açıklama bırakmak için kullanılır.
""",
                "kod": '''// Bu satır bir yorum, çalıştırılmaz.

/* Birden çok satırı
   kaplayan yorum da yazılabilir. */

print("yorumlar çıktıyı etkilemez")''',
            },
            {
                "id": "yazdirma",
                "baslik": "Yazdırma",
                "aciklama": """
<code>print</code> virgülle ayrılmış birden çok değer alabilir; aralarına
boşluk koyar. Her türlü değeri yazdırabilir — sayı, metin, liste, kendi
tanımladığın tipler.
""",
                "kod": '''print("tek değer")
print("ad:", "Ayşe", "yaş:", 30)
print([1, 2, 3])
print(3.5, true, none)''',
            },
        ],
    },

    # ----------------------------------------------------------- değişkenler
    {
        "id": "degiskenler",
        "baslik": "Değişkenler ve veri",
        "konular": [
            {
                "id": "let-var",
                "baslik": "let ve var",
                "aciklama": """
<code>let</code> ile tanımlanan değer <strong>bir daha değişmez</strong>.
Değiştirmen gerekiyorsa <code>var</code> kullan.
<p>Varsayılan olarak <code>let</code> kullan: neyin değiştiğini görmek kodu
okumayı kolaylaştırır. Değiştirmeye çalışırsan derleyici uyarır.</p>
""",
                "kod": '''let ad = "Mustafa"      // değişmez
var sayac = 0           // değişebilir

sayac = sayac + 1
sayac += 5              // aynı şeyin kısa yazımı

print(ad, sayac)''',
            },
            {
                "id": "tipler",
                "baslik": "Tipler",
                "aciklama": """
Her değerin bir tipi vardır. Genelde yazmana gerek yok — Nar değere bakıp
kendisi anlar. İstersen iki nokta ile açıkça yazabilirsin.
<p>Temel tipler: <code>Int</code> (tam sayı), <code>Float</code> (ondalıklı),
<code>String</code> (metin), <code>Bool</code> (doğru/yanlış).</p>
""",
                "kod": '''let a = 42              // Int  (kendisi anladı)
let b = 3.14            // Float
let c = "merhaba"       // String
let d = true            // Bool

let e: Float = 10       // istersen açıkça yaz
let f: String = "elma"

print(a, b, c, d, e, f)''',
            },
            {
                "id": "sayilar",
                "baslik": "Sayılar",
                "aciklama": """
Tam sayı ile ondalıklı sayı birlikte kullanılabilir; sonuç ondalıklı olur.
<p><strong>Tek dikkat edilecek yer bölme:</strong> iki tam sayıyı bölersen
sonuç tam sayıdır (ondalık kısım atılır). Ondalıklı sonuç istiyorsan
taraflardan biri ondalıklı olmalı.</p>
""",
                "kod": '''print(2 + 3)            // 5
print(10 - 4)           // 6
print(3 * 4)            // 12
print(7 / 2)            // 3    <- tam bölme
print(7 / 2.0)          // 3.5  <- ondalıklı
print(7 % 3)            // 1    <- kalan
print(1 + 2.5)          // 3.5  <- karışık kullanılabilir

print(sqrt(16), abs(-5), min(3, 8), max(3, 8))
print(floor(3.7), ceil(3.2), round(3.5))''',
            },
            {
                "id": "metinler",
                "baslik": "Metinler",
                "aciklama": """
Metinleri <code>+</code> ile birleştirebilirsin. Diğer taraf sayı ya da liste
olsa bile çalışır — Nar onu otomatik yazıya çevirir.
<p>Daha okunaklı yol: <code>${...}</code> ile metnin içine doğrudan değer
gömmek.</p>
""",
                "kod": '''let ad = "Ayşe"
let yas = 30

print("Merhaba " + ad)
print("Yaş: " + yas)              // sayı otomatik yazıya döner
print("${ad} ${yas} yaşında")     // gömme — en okunaklısı
print("Toplam: ${yas + 5}")       // içinde işlem de yapılır''',
            },
            {
                "id": "metin-metotlari",
                "baslik": "Metin işlemleri",
                "aciklama": """
Metinlerin üzerinde nokta koyarak çağırabileceğin hazır işlemler var.
<p><code>upperTr()</code> ve <code>lowerTr()</code> Türkçeye özeldir:
<code>i</code> harfini <code>İ</code> yapar, <code>I</code> harfini
<code>ı</code> yapar. Normal <code>upper()</code>/<code>lower()</code> bunu
bilmez.</p>
""",
                "kod": '''let s = "  Merhaba Dünya  "

print(s.trim())                  // baştaki/sondaki boşlukları atar
print(s.trim().len())            // harf sayısı
print(s.trim().lower())
print("istanbul".upperTr())      // Türkçe: İSTANBUL
print("IĞDIR".lowerTr())         // Türkçe: ığdır
print("a-b-c".split("-"))
print("a-b-c".replace("-", "+"))
print("merhaba".contains("hab"))
print("merhaba".slice(0, 3))     // ilk 3 harf
print("ab".repeat(3))''',
            },
            {
                "id": "bool",
                "baslik": "Doğru ve yanlış",
                "aciklama": """
<code>Bool</code> tipinin iki değeri vardır: <code>true</code> (doğru) ve
<code>false</code> (yanlış). Karşılaştırmalar hep <code>Bool</code> üretir.
""",
                "kod": '''print(5 > 3)             // true
print(5 == 5)            // eşit mi
print(5 != 3)            // eşit değil mi
print(5 >= 5, 2 <= 1)

let a = true
let b = false
print(a && b)            // ve   — ikisi de doğruysa
print(a || b)            // veya — biri doğruysa
print(!a)                // değil''',
            },
        ],
    },

    # -------------------------------------------------------------- kararlar
    {
        "id": "kararlar",
        "baslik": "Karar vermek",
        "konular": [
            {
                "id": "if",
                "baslik": "if / else",
                "aciklama": """
Bir koşul doğruysa bir bloğu, değilse başkasını çalıştırır.
Birden çok durum için <code>else if</code> eklenir.
""",
                "kod": '''let not = 85

if not >= 90 {
  print("A aldın")
} else if not >= 80 {
  print("B aldın")
} else {
  print("Daha çok çalış")
}''',
            },
            {
                "id": "if-ifade",
                "baslik": "if ile değer üretmek",
                "aciklama": """
<code>if</code> yalnızca bir şey yapmakla kalmaz, <strong>değer de
üretebilir</strong>. Bir değişkene doğrudan atayabilirsin.
<p>Bu biçimde <code>else</code> yazmak zorunludur — çünkü her durumda bir
değer çıkması gerekir.</p>
""",
                "kod": '''let yas = 20

let durum = if yas >= 18 { "yetişkin" } else { "çocuk" }
print(durum)

// zincirlenebilir
let not = 85
let harf = if not >= 90 { "A" } else if not >= 80 { "B" } else { "C" }
print("harf:", harf)

// başka bir ifadenin içinde de kullanılabilir
print("ücret: " + if yas < 12 { 0 } else { 50 })''',
            },
        ],
    },

    # --------------------------------------------------------------- döngüler
    {
        "id": "donguler",
        "baslik": "Tekrar etmek",
        "konular": [
            {
                "id": "for",
                "baslik": "for döngüsü",
                "aciklama": """
Bir aralıktaki sayılar ya da bir listenin elemanları üzerinde döner.
<p><code>0..5</code> son sayıyı <strong>içermez</strong> (0,1,2,3,4).
İçermesini istersen <code>0..=5</code> yaz.</p>
""",
                "kod": '''for i in 1..4 {
  print("sayı", i)
}

for i in 1..=3 {
  print("dahil", i)
}

for meyve in ["elma", "armut", "kiraz"] {
  print(meyve)
}

for harf in "abc" {
  print(harf)
}''',
            },
            {
                "id": "while",
                "baslik": "while döngüsü",
                "aciklama": """
Koşul doğru olduğu sürece tekrarlar. Kaç kez döneceğini önceden bilmediğin
durumlarda kullanılır.
""",
                "kod": '''var sayi = 1

while sayi < 100 {
  sayi = sayi * 2
}

print("100'ü aşan ilk ikinin kuvveti:", sayi)''',
            },
            {
                "id": "break-continue",
                "baslik": "break ve continue",
                "aciklama": """
<code>break</code> döngüyü tamamen bitirir. <code>continue</code> o turu
atlayıp bir sonrakine geçer.
""",
                "kod": '''for i in 1..=10 {
  if i % 2 == 0 {
    continue          // çiftleri atla
  }
  if i > 7 {
    break             // 7'yi geçince dur
  }
  print(i)
}''',
            },
        ],
    },

    # ---------------------------------------------------------- veri yapıları
    {
        "id": "listeler",
        "baslik": "Listeler ve sözlükler",
        "konular": [
            {
                "id": "liste",
                "baslik": "Listeler",
                "aciklama": """
Liste, aynı tipte birden çok değeri sırayla tutar. Elemanlara sıfırdan
başlayan numarayla (dizin) erişilir.
<p>Olmayan bir dizine erişirsen program net bir hata mesajıyla durur —
sessizce yanlış sonuç vermez.</p>
""",
                "kod": '''var sayilar = [5, 3, 8, 1]

print(sayilar)
print("ilk eleman:", sayilar[0])
print("kaç eleman:", sayilar.len())

sayilar.push(10)              // sona ekle
print(sayilar)

print("sıralı:", sayilar.sort())
print("ters:", sayilar.reverse())
print("içinde 8 var mı:", sayilar.contains(8))
print("bir kısmı:", sayilar.slice(1, 3))''',
            },
            {
                "id": "liste-kolay",
                "baslik": "Listelerle kolay işlemler",
                "aciklama": """
Bir listeyle en çok yapılan işler için adı kendini anlatan hazır işlemler var.
Hiçbirinde fonksiyon yazman gerekmez.
<p>Toplama, ortalama, filtreleme gibi şeyler için önce buraya bak; aradığın
yoksa bir sonraki başlıktaki <code>map</code>/<code>filter</code> yöntemini
kullanırsın.</p>
""",
                "kod": '''let sayilar = [5, 3, 8, 1, 3]

print("toplam:", sayilar.toplam())
print("ortalama:", sayilar.ortalama())
print("çarpım:", sayilar.carpim())
print("en büyük:", sayilar.enBuyuk() ?? 0)
print("en küçük:", sayilar.enKucuk() ?? 0)

print("iki katları:", sayilar.kat(2))
print("10 artırılmış:", sayilar.artir(10))
print("3'ten büyükler:", sayilar.buyukler(3))
print("3'ten küçükler:", sayilar.kucukler(3))
print("çiftler:", sayilar.ciftler())
print("tekler:", sayilar.tekler())

print("benzersiz:", sayilar.benzersiz())
print("kaç tane 3 var:", sayilar.say(3))

let kelimeler = ["nar", "elma", "kiraz"]
print("büyük harf:", kelimeler.buyukHarf())
print("'a' içerenler:", kelimeler.icerenler("a"))''',
            },
            {
                "id": "liste-donusum",
                "baslik": "map, filter, reduce",
                "aciklama": """
Bir önceki başlıktaki hazır işlemler aradığını karşılamıyorsa, kendi kuralını
yazabilirsin. Bunlar listeyi tek satırda dönüştürmenin genel yoludur.
<p><code>|x| ...</code> yazımı "her eleman için" demektir; <code>x</code>
sırayla her elemanın yerini alır.</p>
<ul>
<li><code>map</code> — her elemanı dönüştürür</li>
<li><code>filter</code> — koşula uyanları seçer</li>
<li><code>reduce</code> — hepsini tek değere indirger</li>
</ul>
""",
                "kod": '''let sayilar = [1, 2, 3, 4, 5]

print(sayilar.map(|x| x * x))          // her birinin karesi
print(sayilar.filter(|x| x % 2 == 0))  // sadece çiftler
print(sayilar.reduce(|a, b| a + b, 0)) // toplamı

// zincirlenebilir
print(sayilar.filter(|x| x > 2).map(|x| x * 10))

let kelimeler = ["nar", "elma", "kiraz"]
print(kelimeler.map(|k| k.upperTr()).join(", "))''',
            },
            {
                "id": "sozluk",
                "baslik": "Sözlükler",
                "aciklama": """
Sözlük, bir anahtara karşılık bir değer tutar — "elma" için 12 gibi.
<p><code>get</code> her zaman "olmayabilir" bir sonuç verir; bu yüzden
<code>?? varsayılan</code> ile bir yedek değer belirtirsin. Bu, olmayan
anahtarı unutmanı engeller.</p>
""",
                "kod": '''var stok = {"elma": 12, "armut": 3}

stok.set("kiraz", 7)

print(stok)
print("kaç çeşit:", stok.len())
print("elma:", stok.get("elma") ?? 0)
print("muz:", stok.get("muz") ?? 0)      // yok -> 0
print("armut var mı:", stok.has("armut"))

for (urun, adet) in stok {
  print("${urun}: ${adet} adet")
}''',
            },
        ],
    },

    # ------------------------------------------------------------ fonksiyonlar
    {
        "id": "fonksiyonlar",
        "baslik": "Fonksiyonlar",
        "konular": [
            {
                "id": "fonksiyon",
                "baslik": "Fonksiyon tanımlamak",
                "aciklama": """
Fonksiyon, bir işi bir isim altında toplar; sonra o ismi çağırırsın.
<p>Parametrelerin ve döndürdüğü değerin tipini yazman gerekir. Bu fazladan
yazı gibi görünür ama karşılığında derleyici seni yanlış kullanımdan korur
ve hata mesajları çok daha anlaşılır olur.</p>
""",
                "kod": '''fn selamla(ad: String) {
  print("Merhaba " + ad)
}

fn topla(a: Int, b: Int) -> Int {
  return a + b
}

fn main() {
  selamla("Nar")
  print(topla(3, 4))
}''',
                "tam": '''fn selamla(ad: String) {
  print("Merhaba " + ad)
}

fn topla(a: Int, b: Int) -> Int {
  return a + b
}

fn main() {
  selamla("Nar")
  print(topla(3, 4))
}''',
            },
            {
                "id": "kisa-fonksiyon",
                "baslik": "Tek satırlık fonksiyon",
                "aciklama": """
Fonksiyonun gövdesi tek bir ifadeyse süslü parantez yerine <code>=</code>
kullanabilirsin. Daha kısa ve okunaklı olur.
""",
                "kod": '''fn kare(x: Int) -> Int = x * x

fn selam(ad: String) -> String = "Merhaba " + ad

fn buyuk_mu(n: Int) -> Bool = n > 100

fn main() {
  print(kare(9))
  print(selam("Nar"))
  print(buyuk_mu(150))
}''',
                "tam": '''fn kare(x: Int) -> Int = x * x

fn selam(ad: String) -> String = "Merhaba " + ad

fn buyuk_mu(n: Int) -> Bool = n > 100

fn main() {
  print(kare(9))
  print(selam("Nar"))
  print(buyuk_mu(150))
}''',
            },
            {
                "id": "ozyineleme",
                "baslik": "Kendini çağıran fonksiyon",
                "aciklama": """
Bir fonksiyon kendini çağırabilir. Bunun için mutlaka bir "durma noktası"
olmalı, yoksa sonsuza kadar devam eder.
""",
                "kod": '''fn faktoriyel(n: Int) -> Int {
  if n <= 1 {
    return 1              // durma noktası
  }
  return n * faktoriyel(n - 1)
}

fn fib(n: Int) -> Int = if n < 2 { n } else { fib(n - 1) + fib(n - 2) }

fn main() {
  print("6! =", faktoriyel(6))
  print("fib(20) =", fib(20))
}''',
                "tam": '''fn faktoriyel(n: Int) -> Int {
  if n <= 1 {
    return 1
  }
  return n * faktoriyel(n - 1)
}

fn fib(n: Int) -> Int = if n < 2 { n } else { fib(n - 1) + fib(n - 2) }

fn main() {
  print("6! =", faktoriyel(6))
  print("fib(20) =", fib(20))
}''',
            },
            {
                "id": "lambda",
                "baslik": "İsimsiz fonksiyonlar",
                "aciklama": """
Küçük, tek kullanımlık fonksiyonları isim vermeden yazabilirsin.
<code>map</code> ve <code>filter</code> içinde gördüğün <code>|x| ...</code>
tam olarak budur.
<p>Bir değişkene atarsan parametrenin tipini yazman gerekir — çünkü ortada
tipi anlamayı sağlayacak bir bağlam yoktur.</p>
""",
                "kod": '''let iki_kat = |x: Int| x * 2
print(iki_kat(21))

// birden çok satır gerekiyorsa
let mesafe = |a: Int, b: Int| {
  let fark = a - b
  return abs(fark)
}
print(mesafe(3, 10))

// bir listeye uygularken tip yazmaya gerek yok
print([1, 2, 3].map(|x| x + 100))''',
            },
        ],
    },

    # ------------------------------------------------------------ kendi tipin
    {
        "id": "tipler",
        "baslik": "Kendi tiplerini yapmak",
        "konular": [
            {
                "id": "struct",
                "baslik": "struct — birbirine ait bilgiler",
                "aciklama": """
Birlikte anlam ifade eden bilgileri tek bir tip altında toplar.
Bir kişinin adı ve yaşı gibi.
<p>Alanlar varsayılan olarak değişmezdir. Değişebilmesi için başına
<code>var</code> yaz.</p>
""",
                "kod": '''struct Kisi {
  ad: String
  var yas: Int
}

fn main() {
  let k = Kisi { ad: "Ayşe", yas: 30 }

  print(k)
  print(k.ad, "->", k.yas)

  k.yas = 31        // 'var' olduğu için değiştirilebilir
  print("doğum günü sonrası:", k.yas)
}''',
                "tam": '''struct Kisi {
  ad: String
  var yas: Int
}

fn main() {
  let k = Kisi { ad: "Ayşe", yas: 30 }
  print(k)
  print(k.ad, "->", k.yas)
  k.yas = 31
  print("doğum günü sonrası:", k.yas)
}''',
            },
            {
                "id": "metot",
                "baslik": "Tipe ait fonksiyonlar (metotlar)",
                "aciklama": """
Bir tipin içine, o tiple ilgili fonksiyonlar koyabilirsin. Bunlara metot
denir. İçeride <code>self</code>, üzerinde çalıştığın nesneyi gösterir.
""",
                "kod": '''struct Dikdortgen {
  en: Float
  boy: Float

  fn alan() -> Float = self.en * self.boy

  fn cevre() -> Float = 2.0 * (self.en + self.boy)

  fn kare_mi() -> Bool = self.en == self.boy

  fn buyut(kat: Float) -> Dikdortgen {
    return Dikdortgen { en: self.en * kat, boy: self.boy * kat }
  }
}

fn main() {
  let d = Dikdortgen { en: 3.0, boy: 4.0 }
  print("alan:", d.alan())
  print("çevre:", d.cevre())
  print("kare mi:", d.kare_mi())
  print("iki katı:", d.buyut(2.0))
}''',
                "tam": '''struct Dikdortgen {
  en: Float
  boy: Float

  fn alan() -> Float = self.en * self.boy
  fn cevre() -> Float = 2.0 * (self.en + self.boy)
  fn kare_mi() -> Bool = self.en == self.boy

  fn buyut(kat: Float) -> Dikdortgen {
    return Dikdortgen { en: self.en * kat, boy: self.boy * kat }
  }
}

fn main() {
  let d = Dikdortgen { en: 3.0, boy: 4.0 }
  print("alan:", d.alan())
  print("çevre:", d.cevre())
  print("kare mi:", d.kare_mi())
  print("iki katı:", d.buyut(2.0))
}''',
            },
            {
                "id": "enum",
                "baslik": "enum — sınırlı seçenekler",
                "aciklama": """
Bir değerin alabileceği seçenekler belliyse <code>enum</code> kullanılır:
hava durumu, sipariş durumu, ödeme tipi gibi.
<p>Metin kullanmaya göre avantajı: yazım hatası yapamazsın ve derleyici
seçeneklerin hepsini ele aldığından emin olur.</p>
""",
                "kod": '''enum Hava {
  Gunesli
  Yagmurlu
  Karli
}

fn main() {
  let bugun = Hava.Yagmurlu
  print(bugun)
}''',
                "tam": '''enum Hava {
  Gunesli
  Yagmurlu
  Karli
}

fn main() {
  let bugun = Hava.Yagmurlu
  print(bugun)
}''',
            },
            {
                "id": "match",
                "baslik": "match — seçeneklere göre davranmak",
                "aciklama": """
<code>match</code>, bir değerin hangi durumda olduğuna bakıp ona göre iş
yapar.
<p><strong>En değerli özelliği:</strong> bir seçeneği ele almayı unutursan
program çalışmaz, derleyici sana hangisini unuttuğunu söyler. Sonradan
<code>enum</code>'a yeni bir seçenek eklediğinde, düzeltmen gereken bütün
yerleri derleyici gösterir.</p>
""",
                "kod": '''enum Hava {
  Gunesli
  Yagmurlu
  Karli
}

fn tavsiye(h: Hava) -> String = match h {
  Hava.Gunesli -> "Şapka al."
  Hava.Yagmurlu -> "Şemsiye al."
  Hava.Karli -> "Mont al."
}

fn main() {
  for h in [Hava.Gunesli, Hava.Yagmurlu, Hava.Karli] {
    print(tavsiye(h))
  }

  // sayı ya da metin üzerinde de çalışır
  let n = 3
  print(match n {
    1 -> "bir"
    2 -> "iki"
    _ -> "çok"           // _ = geri kalan her şey
  })
}''',
                "tam": '''enum Hava {
  Gunesli
  Yagmurlu
  Karli
}

fn tavsiye(h: Hava) -> String = match h {
  Hava.Gunesli -> "Şapka al."
  Hava.Yagmurlu -> "Şemsiye al."
  Hava.Karli -> "Mont al."
}

fn main() {
  for h in [Hava.Gunesli, Hava.Yagmurlu, Hava.Karli] {
    print(tavsiye(h))
  }
  let n = 3
  print(match n {
    1 -> "bir"
    2 -> "iki"
    _ -> "çok"
  })
}''',
            },
            {
                "id": "enum-veri",
                "baslik": "Veri taşıyan seçenekler",
                "aciklama": """
Seçenekler yanlarında veri taşıyabilir. Bu, "işlem başarılı oldu ve sonucu
şu" ya da "hata oldu ve sebebi şu" gibi durumları anlatmanın temiz yoludur.
<p>Nar'da hatalar bu şekilde yönetilir. Hatayı görmezden gelemezsin, çünkü
sonucu almak için <code>match</code> yazmak zorundasın.</p>
""",
                "kod": '''enum Sonuc {
  Tamam(Int)
  Hata(String)
}

fn bol(a: Int, b: Int) -> Sonuc {
  if b == 0 {
    return Sonuc.Hata("sıfıra bölünemez")
  }
  return Sonuc.Tamam(a / b)
}

fn main() {
  for bolen in [4, 0, 5] {
    match bol(100, bolen) {
      Sonuc.Tamam(deger) -> print("100 / ${bolen} = ${deger}")
      Sonuc.Hata(mesaj) -> print("olmadı: ${mesaj}")
    }
  }
}''',
                "tam": '''enum Sonuc {
  Tamam(Int)
  Hata(String)
}

fn bol(a: Int, b: Int) -> Sonuc {
  if b == 0 {
    return Sonuc.Hata("sıfıra bölünemez")
  }
  return Sonuc.Tamam(a / b)
}

fn main() {
  for bolen in [4, 0, 5] {
    match bol(100, bolen) {
      Sonuc.Tamam(deger) -> print("100 / ${bolen} = ${deger}")
      Sonuc.Hata(mesaj) -> print("olmadı: ${mesaj}")
    }
  }
}''',
            },
        ],
    },

    # -------------------------------------------------------------- güvenlik
    {
        "id": "opsiyonel",
        "baslik": "Olmayabilen değerler",
        "konular": [
            {
                "id": "none",
                "baslik": "none ve soru işareti",
                "aciklama": """
Bazı değerler olmayabilir: aranan kayıt bulunamamıştır, kullanıcı takma ad
girmemiştir. Nar'da bu durum tipte açıkça görünür — sonuna
<code>?</code> koyarsın.
<p>Bu, birçok dilde programların en sık çöktüğü hatayı ("null" hatası)
baştan engeller: olmayabilecek bir değeri kontrol etmeden kullanamazsın.</p>
""",
                "kod": '''let takma: String? = none
let gercek: String? = "Nar"

print(takma)
print(gercek)

// ?? ile yedek değer ver
print(takma ?? "takma adı yok")
print(gercek ?? "takma adı yok")''',
            },
            {
                "id": "opsiyonel-kullanim",
                "baslik": "Değeri güvenle kullanmak",
                "aciklama": """
Olmayabilen bir değeri kullanmanın üç yolu var:
<ul>
<li><code>?? yedek</code> — yoksa şunu kullan</li>
<li><code>if x != none { ... }</code> — kontrol et, içeride normal kullan</li>
<li><code>x!</code> — "kesinlikle var" de; yanılırsan program net bir hatayla durur</li>
</ul>
""",
                "kod": '''let sayilar = [10, 20, 30]

let ilk = sayilar.first()        // İlk eleman olmayabilir (liste boşsa)
print("ilk:", ilk ?? 0)

if ilk != none {
  print("var, iki katı:", ilk * 2)   // burada artık kesin var
}

var bos: [Int] = []
print("boş listenin ilki:", bos.first() ?? -1)''',
            },
            {
                "id": "guvenli-zincir",
                "baslik": "Güvenli erişim: ?.",
                "aciklama": """
Olmayabilen bir değerin içine erişirken <code>?.</code> kullanılır.
Değer yoksa zincir durur ve sonuç <code>none</code> olur — program çökmez.
""",
                "kod": '''struct Adres {
  sehir: String
}

struct Kisi {
  ad: String
  adres: Adres?
}

fn main() {
  let a = Kisi { ad: "Ayşe", adres: Adres { sehir: "Ankara" } }
  let b = Kisi { ad: "Veli", adres: none }

  print(a.adres?.sehir ?? "adres yok")
  print(b.adres?.sehir ?? "adres yok")
}''',
                "tam": '''struct Adres {
  sehir: String
}

struct Kisi {
  ad: String
  adres: Adres?
}

fn main() {
  let a = Kisi { ad: "Ayşe", adres: Adres { sehir: "Ankara" } }
  let b = Kisi { ad: "Veli", adres: none }
  print(a.adres?.sehir ?? "adres yok")
  print(b.adres?.sehir ?? "adres yok")
}''',
            },
        ],
    },

    # ------------------------------------------------------------------- sayfa
    {
        "id": "sayfa",
        "baslik": "Web sayfası yapmak",
        "konular": [
            {
                "id": "sayfa-giris",
                "baslik": "Sayfayla konuşmak",
                "aciklama": """
Nar programı tarayıcıda çalışırken sayfadaki öğelere erişebilir: yazı
değiştirebilir, düğme ekleyebilir, tıklamaları dinleyebilir.
<p><code>bul(...)</code> bir öğeyi seçer. Öğe olmayabileceği için sonuç
her zaman <strong>olabilir</strong> tipindedir — kontrol etmen gerekir.
Bu, "öğe yok" hatasını baştan engeller.</p>
<p>Programı tarayıcıda çalışacak biçimde derlemek için:
<code>nar build program.nar --target web</code></p>
""",
                "kod": '''fn main() {
  let baslik = bul("#baslik")

  if baslik != none {
    baslik.metinYaz("Merhaba Nar")
    baslik.stil("color", "#a32a2f")
    baslik.sinifEkle("vurgulu")
  }
}''',
                "calistirma": False,
            },
            {
                "id": "sayfa-olay",
                "baslik": "Düğme ve tıklama",
                "aciklama": """
<code>olustur(...)</code> yeni bir öğe yapar, <code>ekle(...)</code> onu
sayfaya koyar, <code>dinle(...)</code> ise tıklama gibi olayları yakalar.
<p>Aşağıdaki program çalışan bir sayaçtır; tam hâli
<code>ornekler/sayac_web.nar</code> dosyasında.</p>
""",
                "kod": '''var sayi = 0

fn main() {
  let alan = bul("#uygulama")
  if alan == none {
    print("bu program tarayıcıda çalışmalı")
    return
  }

  let ekran = olustur("div")
  ekran.ozellikYaz("id", "ekran")
  ekran.metinYaz("0")
  alan!.ekle(ekran)

  let dugme = olustur("button")
  dugme.metinYaz("Artır")
  dugme.dinle("click", || {
    sayi += 1
    bul("#ekran")?.metinYaz(str(sayi))
  })
  alan!.ekle(dugme)
}''',
                "calistirma": False,
            },
            {
                "id": "sayfa-islemleri",
                "baslik": "Öğe üzerinde yapabileceklerin",
                "aciklama": """
Bir öğeyi bulduktan sonra kullanabileceğin işlemler. Hepsi
<code>Element</code> tipinin üzerindedir.
<p><strong>Not:</strong> Bu işlemler yalnızca tarayıcıda anlamlıdır.
Aynı programı <code>nar run</code> ile çalıştırırsan <code>bul(...)</code>
her zaman <code>none</code> döner ve program çökmez — bu sayede aynı kodu
her iki ortamda da güvenle çalıştırabilirsin.</p>
""",
                "kod": '''fn ornekler(e: Element) {
  e.metinYaz("yazı")            // içindeki yazıyı değiştir
  print(e.metin())              // içindeki yazıyı oku
  e.htmlYaz("<b>kalın</b>")     // HTML olarak yaz
  e.degerYaz("giriş")           // input/textarea değeri
  print(e.deger())

  e.sinifEkle("acik")
  e.sinifSil("kapali")
  print(e.sinifVarMi("acik"))

  e.ozellikYaz("id", "kutu")
  print(e.ozellik("id") ?? "yok")
  e.stil("color", "red")

  e.dinle("click", || { print("tıklandı") })

  e.ekle(olustur("span"))       // çocuk ekle
  e.temizle()                   // içini boşalt
  e.odaklan()

  print(e.bul(".ic") != none)   // içinde ara
}''',
                "calistirma": False,
            },
        ],
    },

    # ---------------------------------------------------------- program düzeni
    {
        "id": "duzen",
        "baslik": "Programı düzenlemek",
        "konular": [
            {
                "id": "modul",
                "baslik": "Dosyaları bölmek",
                "aciklama": """
Program büyüdükçe birden çok dosyaya bölebilirsin. Bir dosyadaki
fonksiyonları kullanmak için <code>import</code> yazman yeterli.
<p>Örneğin <code>araclar.nar</code> dosyasında yardımcı fonksiyonlar,
<code>program.nar</code> dosyasında ana akış olabilir:</p>
""",
                "kod": '''// araclar.nar dosyası:
fn selamla(ad: String) -> String = "Merhaba " + ad


// program.nar dosyası:
import "araclar.nar"

fn main() {
  print(selamla("Nar"))
}''',
                "calistirma": False,
            },
            {
                "id": "hata-mesajlari",
                "baslik": "Hata mesajlarını okumak",
                "aciklama": """
Nar bir hata bulduğunda sana üç şey söyler: <strong>nerede</strong> olduğu,
<strong>ne</strong> olduğu ve çoğu zaman <strong>nasıl düzeltileceği</strong>.
<p>Hata mesajını okumak zaman kaybı değil, en hızlı çözüm yoludur.
Örneğin değişmez bir değeri değiştirmeye çalışırsan:</p>
""",
                "kod": '''let sayi = 5
sayi = 6''',
                "beklenen_hata": True,
            },
            {
                "id": "hata-eksik-dal",
                "baslik": "Unuttuğun seçeneği söyler",
                "aciklama": """
<code>enum</code> seçeneklerinden birini ele almayı unutursan derleyici
tam olarak hangisini unuttuğunu söyler. Bu özellik, sonradan yeni seçenek
eklediğinde çok işe yarar.
""",
                "kod": '''enum Durum {
  Acik
  Kapali
  Bekliyor
}

fn main() {
  match Durum.Acik {
    Durum.Acik -> print("açık")
    Durum.Kapali -> print("kapalı")
  }
}''',
                "tam": '''enum Durum {
  Acik
  Kapali
  Bekliyor
}

fn main() {
  match Durum.Acik {
    Durum.Acik -> print("açık")
    Durum.Kapali -> print("kapalı")
  }
}''',
                "beklenen_hata": True,
            },
        ],
    },
]


# ------------------------------------------------------------------- referans
REFERANS = [
    {
        "baslik": "Hazır fonksiyonlar",
        "aciklama": "Her yerde kullanabileceğin, hiçbir şey yazmadan gelen fonksiyonlar.",
        "satirlar": [
            ("print(a, b, ...)", "Ekrana yazar, aralara boşluk koyar"),
            ("str(x)", "Herhangi bir değeri metne çevirir"),
            ("len(x)", "Metin, liste ya da sözlüğün uzunluğu"),
            ("int(x)", "Metni ya da ondalıklıyı tam sayıya çevirir"),
            ("float(x)", "Metni ya da tam sayıyı ondalıklıya çevirir"),
            ("abs(x)", "Mutlak değer (işareti atar)"),
            ("min(a, b) · max(a, b)", "Küçük olan · büyük olan"),
            ("sqrt(x)", "Karekök"),
            ("pow(a, b)", "Üs alma: a üzeri b"),
            ("floor(x) · ceil(x) · round(x)", "Aşağı · yukarı · en yakına yuvarlar"),
            ("random()", "0 ile 1 arasında rastgele ondalıklı sayı"),
            ("panic(mesaj)", "Programı verilen mesajla durdurur"),
            ("assert(kosul, mesaj)", "Koşul yanlışsa programı durdurur"),
        ],
    },
    {
        "baslik": "Metin işlemleri",
        "aciklama": "Bir metnin sonuna nokta koyup çağırılır: <code>\"abc\".upper()</code>",
        "satirlar": [
            ("len()", "Harf sayısı"),
            ("upper() · lower()", "Büyük · küçük harfe çevirir"),
            ("upperTr() · lowerTr()", "Türkçe kurallarıyla: i↔İ, I↔ı"),
            ("trim()", "Baştaki ve sondaki boşlukları atar"),
            ("split(ayrac)", "Ayraca göre parçalayıp liste verir"),
            ("contains(parca)", "İçinde geçiyor mu"),
            ("replace(eski, yeni)", "Tüm geçtiği yerleri değiştirir"),
            ("startsWith(x) · endsWith(x)", "Şununla başlıyor mu · bitiyor mu"),
            ("slice(bas, son)", "Belirtilen aralığı keser"),
            ("charAt(i)", "i numaralı harf"),
            ("indexOf(parca)", "Kaçıncı sırada geçiyor (yoksa -1)"),
            ("repeat(n)", "n kez tekrarlar"),
        ],
    },
    {
        "baslik": "Liste işlemleri",
        "aciklama": "Bir listenin sonuna nokta koyup çağırılır: <code>[1,2].len()</code>",
        "satirlar": [
            ("len()", "Eleman sayısı"),
            ("push(x)", "Sona ekler"),
            ("pop()", "Sondakini alır ve çıkarır (boşsa none)"),
            ("first() · last()", "İlk · son eleman (boşsa none)"),
            ("contains(x)", "İçinde var mı"),
            ("indexOf(x)", "Kaçıncı sırada (yoksa -1)"),
            ("slice(bas, son)", "Belirtilen aralığı alır"),
            ("reverse()", "Ters çevrilmiş kopyasını verir"),
            ("sort()", "Sıralanmış kopyasını verir"),
            ("join(ayrac)", "Metin listesini birleştirir"),
            ("map(f)", "Her elemanı dönüştürür"),
            ("filter(f)", "Koşula uyanları seçer"),
            ("reduce(f, baslangic)", "Hepsini tek değere indirger"),
            ("benzersiz()", "Tekrar edenleri atar"),
            ("say(x)", "x kaç kez geçiyor"),
        ],
    },
    {
        "baslik": "Sayı listesi işlemleri",
        "aciklama": "Fonksiyon yazmadan kullanılır; yalnızca sayı listelerinde geçerlidir.",
        "satirlar": [
            ("toplam()", "Hepsinin toplamı"),
            ("carpim()", "Hepsinin çarpımı"),
            ("ortalama()", "Ortalaması (her zaman ondalıklı)"),
            ("enBuyuk() · enKucuk()", "En büyük · en küçük eleman (boşsa none)"),
            ("kat(n)", "Her elemanı n ile çarpar"),
            ("artir(n)", "Her elemana n ekler"),
            ("buyukler(n) · kucukler(n)", "n'den büyük · küçük olanlar"),
            ("ciftler() · tekler()", "Çift · tek sayılar (yalnızca Int)"),
        ],
    },
    {
        "baslik": "Metin listesi işlemleri",
        "aciklama": "Yalnızca metin listelerinde geçerlidir.",
        "satirlar": [
            ("buyukHarf() · kucukHarf()", "Hepsini Türkçe kurallarıyla büyütür · küçültür"),
            ("icerenler(parca)", "İçinde o parça geçenleri seçer"),
        ],
    },
    {
        "baslik": "Sözlük işlemleri",
        "aciklama": "Bir sözlüğün sonuna nokta koyup çağırılır.",
        "satirlar": [
            ("len()", "Kaç kayıt var"),
            ("get(anahtar)", "Değeri verir (yoksa none)"),
            ("set(anahtar, deger)", "Ekler ya da günceller"),
            ("has(anahtar)", "Bu anahtar var mı"),
            ("remove(anahtar)", "Kaydı siler"),
            ("keys() · values()", "Anahtarların · değerlerin listesi"),
        ],
    },
    {
        "baslik": "Sayfa işlemleri",
        "aciklama": "Yalnızca tarayıcıda anlamlıdır; Node'da <code>bul</code> none döner.",
        "satirlar": [
            ("bul(secici)", "Bir öğe seçer (yoksa none)"),
            ("bulHepsi(secici)", "Eşleşen tüm öğeler"),
            ("olustur(etiket)", "Yeni öğe yapar"),
            ("govde()", "Sayfanın gövdesi"),
            ("zamanla(ms, islev)", "Belirtilen süre sonra çalıştırır"),
            ("istek(yontem, url, govde, islev)", "Ağ isteği; sonuç islev'e gelir"),
            ("e.metin() · e.metinYaz(s)", "İçindeki yazıyı okur · değiştirir"),
            ("e.html() · e.htmlYaz(s)", "İçeriği HTML olarak okur · yazar"),
            ("e.deger() · e.degerYaz(s)", "Giriş kutusunun değeri"),
            ("e.sinifEkle(s) · sinifSil(s) · sinifVarMi(s)", "CSS sınıfı işlemleri"),
            ("e.ozellik(ad) · ozellikYaz(ad, d)", "Öznitelik okur · yazar"),
            ("e.stil(ad, deger)", "Tek bir stil kuralı verir"),
            ("e.dinle(olay, islev)", "Olay dinler (click, input…)"),
            ("e.ekle(cocuk) · e.cikar()", "Çocuk ekler · kendini kaldırır"),
            ("e.temizle() · e.odaklan()", "İçini boşaltır · odağı verir"),
            ("e.bul(secici) · e.bulHepsi(secici)", "Kendi içinde arar"),
        ],
    },
    {
        "baslik": "Operatörler",
        "aciklama": "Yukarıdakiler aşağıdakilerden önce hesaplanır.",
        "satirlar": [
            ("a.b · a() · a[i] · a!", "Erişim, çağrı, dizin, zorla aç"),
            ("-a · !a", "Eksi işaret, değil"),
            ("* / %", "Çarpma, bölme, kalan"),
            ("+ -", "Toplama (metin birleştirme), çıkarma"),
            (".. ..=", "Aralık (son hariç · son dahil)"),
            ("< <= > >=", "Karşılaştırma"),
            ("== !=", "Eşit mi, eşit değil mi"),
            ("&&", "Ve"),
            ("||", "Veya"),
            ("??", "Yoksa şunu kullan"),
        ],
    },
]

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


# Depo adresi; üst bardaki "Kaynak" bağlantısı buraya gider.
DEPO = "https://github.com/ridocs/nar-dili"

# Girişteki hedef rozetleri.
HEDEFLER = ["web", "masaüstü", "Linux", "Android", "iOS"]

# Sayfanın en üstündeki tanıtım programı. Bir dili anlatmanın en kısa yolu
# bir program ile onun çıktısıdır; bu da öbür örnekler gibi üretim sırasında
# derlenip çalıştırılır.
VITRIN = {
    "id": "vitrin",
    "kod": """struct Dil {
  ad: String
  hedefler: [String]
}

fn tanit(d: Dil) -> String =
  "${d.ad}: tek kaynaktan ${d.hedefler.len()} hedef"

fn main() {
  let nar = Dil {
    ad: "Nar",
    hedefler: ["web", "masaüstü", "mobil"]
  }
  print(tanit(nar))
  print(nar.hedefler.join(" · "))

  let sayilar = [3, 1, 4, 1, 5, 9, 2, 6]
  print("çiftler:", sayilar.filter(|n| n % 2 == 0))
  print("toplam:", sayilar.toplam())
}
""",
}


BOLUMLER = [
    # ------------------------------------------------------------ başlangıç
    {
        "id": "baslangic",
        "baslik": "Başlangıç",
        "aciklama": "İlk programı yaz, çalıştır, ekrana bir şey yazdır.",
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
        "aciklama": "Değer tutmak: let ve var, sayılar, metinler, doğru/yanlış.",
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
                "id": "karakter-kodu",
                "baslik": "Karakter kodları",
                "aciklama": """
Her karakterin bir sayı karşılığı vardır (Unicode kod noktası).
<code>kodu()</code> karakterden sayıya, <code>koddan(...)</code> sayıdan
karaktere çevirir.
<p>Şifreleme, sıralama, kaçış dizisi çözme gibi işlerde gerekir. Emoji
gibi geniş karakterler de tek parça sayılır.</p>
""",
                "kod": '''print("A".kodu())          // 65
print("a".kodu())          // 97
print(koddan(65))          // A

// Türkçe harfler de aynı şekilde
print("ı".kodu())
print(koddan(305))

// Sezar şifresi: her harfi üç ileri kaydır
let harf = "d"
print(koddan(harf.kodu() + 3))''',
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
        "aciklama": "Koşula göre farklı iş yapmak; if'i değer üretmek için kullanmak.",
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
            {
                "id": "blok-ifadesi",
                "baslik": "Dalda birden çok satır",
                "aciklama": """
Değer üreten <code>if</code> ve <code>match</code> dallarında tek satır
yetmiyorsa blok yazabilirsin. <strong>Bloğun son satırı dalın
değeridir.</strong>
<p>Ara adımları ayrı bir fonksiyona çıkarmak zorunda değilsin; hesabı
olduğu yerde yapabilirsin.</p>
<p>Son satır bir değer olmalı — atama ya da döngüyle biten bir dal hata
verir; derleyici bunu söyler.</p>
""",
                "kod": '''enum Hava {
  Gunesli
  Yagmurlu
  Karli
}

fn oneri(h: Hava) -> String = match h {
  Gunesli -> "şapka al"
  Yagmurlu -> {
    let arac = "şemsiye"
    let sebep = "yağmur"
    "${arac} al (${sebep})"
  }
  Karli -> {
    let katman = 3
    "${katman} kat giy"
  }
}

fn sinif(not: Int) -> String = if not >= 90 {
  "A"
} else if not >= 80 {
  let fark = 90 - not
  "B (A'ya ${fark} puan)"
} else {
  "C"
}

fn main() {
  print(oneri(Yagmurlu))
  print(oneri(Karli))
  print(sinif(85))
}''',
                "tam": '''enum Hava {
  Gunesli
  Yagmurlu
  Karli
}

fn oneri(h: Hava) -> String = match h {
  Gunesli -> "şapka al"
  Yagmurlu -> {
    let arac = "şemsiye"
    let sebep = "yağmur"
    "${arac} al (${sebep})"
  }
  Karli -> {
    let katman = 3
    "${katman} kat giy"
  }
}

fn sinif(not: Int) -> String = if not >= 90 {
  "A"
} else if not >= 80 {
  let fark = 90 - not
  "B (A'ya ${fark} puan)"
} else {
  "C"
}

fn main() {
  print(oneri(Yagmurlu))
  print(oneri(Karli))
  print(sinif(85))
}''',
            },
        ],
    },

    # --------------------------------------------------------------- döngüler
    {
        "id": "donguler",
        "baslik": "Tekrar etmek",
        "aciklama": "Aynı işi tekrarlamak: for, while, break ve continue.",
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
                "id": "indeksli-for",
                "baslik": "Sıra numarasıyla dönmek",
                "aciklama": """
Listede sıra numarası da gerekiyorsa ikinci bir döngü değişkeni yaz.
Elle sayaç tutmak gerekmez.
<p>Metinde de çalışır ve indeks <strong>karakter sayar</strong>: “ç”
tek karakterdir, iki değil.</p>
<p>Eşlemede iki değişken zaten anahtar ve değerdir. Aralıkta ikinci
değişken yok — aralığın kendisi zaten sayı üretiyor.</p>
""",
                "kod": '''let sehirler = ["İstanbul", "Ankara", "İzmir"]
for (sira, sehir) in sehirler {
  print("${sira + 1}. ${sehir}")
}

for (i, harf) in "açık" {
  print(i, harf)
}

let yaslar = {"Ayşe": 30, "Mehmet": 24}
for (ad, yas) in yaslar {
  print(ad, yas)
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
        "aciklama": "Sırayla duran veri ve anahtar–değer eşlemeleri.",
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
        "aciklama": "İşi ada bağlamak, parçalara ayırmak, isimsiz fonksiyonlar.",
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
        "aciklama": "Kendi veri biçimlerini kurmak: struct, enum, metot, match.",
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
                "id": "kisa-varyant",
                "baslik": "Enum adını yazmadan",
                "aciklama": """
<code>Hava.Yagmurlu</code> yerine kısaca <code>Yagmurlu</code> yazabilirsin.
Seçenek adı programda tek bir <code>enum</code>'a aitse derleyici hangisini
kastettiğini bilir.
<p>Aynı ad iki ayrı <code>enum</code>'da geçiyorsa derleyici sana söyler ve
hangisi olduğunu yazmanı ister — sessizce yanlış olanı seçmez.</p>
""",
                "kod": '''enum Hava {
  Gunesli
  Yagmurlu
  Karli
}

fn oneri(h: Hava) -> String = match h {
  Gunesli -> "şapka al"
  Yagmurlu -> "şemsiye al"
  Karli -> "atkı al"
}

fn main() {
  print(oneri(Yagmurlu))
  print(oneri(Hava.Karli))   // uzun yazım da geçerli
}''',
                "tam": '''enum Hava {
  Gunesli
  Yagmurlu
  Karli
}

fn oneri(h: Hava) -> String = match h {
  Gunesli -> "şapka al"
  Yagmurlu -> "şemsiye al"
  Karli -> "atkı al"
}

fn main() {
  print(oneri(Yagmurlu))
  print(oneri(Hava.Karli))
}''',
            },
            {
                "id": "tuple",
                "baslik": "Tuple — iki değeri birlikte döndürmek",
                "aciklama": """
Bir fonksiyon tek değer döndürür; iki şey döndürmek gerektiğinde eskiden
bunun için bir <code>struct</code> açmak gerekirdi. <strong>Tuple</strong>
tam bu boşluğu doldurur: parantez içinde birkaç değer, alan adı yok,
sırayla okunur.
<p><code>let (a, b) = ...</code> ile tuple doğrudan adlarına açılır;
öğeye tek tek <code>.0</code>, <code>.1</code> ile de erişilebilir.</p>
<p><strong>Ne zaman struct'a geçmeli:</strong> alanların adı anlam
taşımaya başladığında. <code>(Int, Int)</code> okunurken hangisinin
bölüm hangisinin kalan olduğu belli değilse, orası artık bir struct
yeridir — dört öğeyi geçen tuple için derleyici de uyarır.</p>
""",
                "kod": '''fn bolVeKalan(a: Int, b: Int) -> (Int, Int) = (a / b, a % b)

fn enUzunKelime(cumle: String) -> (String, Int) {
  var enUzun = ""
  for k in cumle.split(" ") {
    if k.len() > enUzun.len() {
      enUzun = k
    }
  }
  return (enUzun, enUzun.len())
}

fn main() {
  let (bolum, kalan) = bolVeKalan(17, 5)
  print(str(bolum) + " kalan " + str(kalan))

  let (kelime, uzunluk) = enUzunKelime("bugün hava çok güzel")
  print(kelime + " — " + str(uzunluk) + " harf")

  // Tek tek de okunur:
  let ikili = bolVeKalan(9, 2)
  print(str(ikili.0) + "/" + str(ikili.1))
}''',
            },
            {
                "id": "kosullu-kol",
                "baslik": "Koşullu kol ve aralık — if zincirini kısaltmak",
                "aciklama": """
Bir <code>match</code> kolu yalnız desene değil, bir koşula da bakabilir:
<code>desen if koşul -&gt;</code>. Desenin bağladığı ad koşulun içinde
kullanılabilir.
<p>Sayı ve metin aralıkları da desen olur: <code>1..=9</code> ikisini de
içine alır, <code>0..3</code> üst ucu dışarıda bırakır.</p>
<p><strong>Neden önemli:</strong> peş peşe <code>if</code> yazmak yerine
bütün durumlar tek yerde, alt alta durur. Derleyici de bir durumu
atladığını söyleyebilir — koşullu kol tek başına match'i tamamlamış
saymaz, çünkü koşul tutmayabilir.</p>
""",
                "kod": '''fn siniflandir(n: Int) -> String = match n {
  x if x < 0 -> "eksi"
  0 -> "sıfır"
  1..=9 -> "tek haneli"
  10..=99 -> "iki haneli"
  _ -> "daha büyük"
}

fn main() {
  for n in [-3, 0, 7, 42, 1000] {
    print(str(n) + " -> " + siniflandir(n))
  }
}''',
            },
            {
                "id": "varsayilan-arguman",
                "baslik": "Varsayılan değer ve ad ile argüman",
                "aciklama": """
Bir parametreye varsayılan verirsen çağıran onu yazmayabilir. Argümanı
adıyla da verebilirsin; o zaman sıra önemli olmaz.
<p>Aynısı <code>struct</code> alanları için de geçerli: varsayılanı olan
alan kurulurken yazılmayabilir. Sekiz alanlı bir yapıyı kurmak için
sekizini birden yazmak gerekmez.</p>
<p><strong>Kural:</strong> varsayılanı olmayan parametre, varsayılanı
olanlardan sonra gelemez — gelirse çağrıda ona ulaşılamazdı.</p>
""",
                "kod": '''struct Kutu {
  var yazi: String
  var genislik: Int = 20
  var cerceve: Bool = true
}

fn bicim(metin: String, once: String = "[", sonra: String = "]") -> String =
  once + metin + sonra

fn main() {
  print(bicim("selam"))
  print(bicim("selam", sonra: ">"))
  print(bicim(sonra: ">", once: "<", metin: "selam"))

  let k = Kutu { yazi: "not" }
  print(k.yazi + " " + str(k.genislik) + " " + str(k.cerceve))
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

    # -------------------------------------------------------------- generic
    {
        "id": "generic",
        "baslik": "Her tiple çalışan kod",
        "aciklama": "Aynı kodu her tiple çalıştırmak.",
        "konular": [
            {
                "id": "generic-giris",
                "baslik": "Tip parametreleri",
                "aciklama": """
Bazen bir yapı ya da fonksiyon, içindeki değerin <em>ne olduğuna</em>
bakmadan çalışır: bir kutu hem sayı hem metin taşıyabilir.
<p>Böyle durumlarda tipe bir <strong>parametre</strong> verilir. Aşağıdaki
<code>T</code> "herhangi bir tip" demektir; kullanırken hangisi olduğu
belli olur.</p>
<p>Faydası: aynı kodu her tip için yeniden yazmazsın, ama tip güvenliği
kaybolmaz — <code>Kutu&lt;Int&gt;</code> içine metin koyamazsın.</p>
""",
                "kod": '''struct Kutu<T> {
  deger: T
  fn al() -> T = self.deger
}

fn main() {
  let sayiKutusu = Kutu { deger: 5 }
  let metinKutusu = Kutu { deger: "merhaba" }

  print(sayiKutusu.al())
  print(metinKutusu.al())

  // Tipi açıkça da yazabilirsin
  let acik = Kutu<Float> { deger: 2.5 }
  print(acik.deger)
}''',
                "tam": '''struct Kutu<T> {
  deger: T
  fn al() -> T = self.deger
}

fn main() {
  let sayiKutusu = Kutu { deger: 5 }
  let metinKutusu = Kutu { deger: "merhaba" }
  print(sayiKutusu.al())
  print(metinKutusu.al())
  let acik = Kutu<Float> { deger: 2.5 }
  print(acik.deger)
}''',
            },
            {
                "id": "generic-fonksiyon",
                "baslik": "Her tiple çalışan fonksiyonlar",
                "aciklama": """
Fonksiyonlar da tip parametresi alabilir. Tip, verdiğin değerden
kendiliğinden anlaşılır — yazmana gerek yoktur.
""",
                "kod": '''fn ilk<T>(liste: [T]) -> T? {
  if liste.len() == 0 {
    return none
  }
  return liste[0]
}

fn ikiKat<T>(x: T) -> [T] = [x, x]

fn main() {
  print(ilk([3, 4, 5]) ?? 0)
  print(ilk(["a", "b"]) ?? "yok")

  let bos: [Int] = []
  print(ilk(bos) ?? -1)

  print(ikiKat(7))
  print(ikiKat("x"))
}''',
                "tam": '''fn ilk<T>(liste: [T]) -> T? {
  if liste.len() == 0 {
    return none
  }
  return liste[0]
}

fn ikiKat<T>(x: T) -> [T] = [x, x]

fn main() {
  print(ilk([3, 4, 5]) ?? 0)
  print(ilk(["a", "b"]) ?? "yok")
  let bos: [Int] = []
  print(ilk(bos) ?? -1)
  print(ikiKat(7))
  print(ikiKat("x"))
}''',
            },
            {
                "id": "sonuc-tipi",
                "baslik": "Hata yönetimi: Sonuç tipi",
                "aciklama": """
Nar'da hata fırlatma (<code>try</code>/<code>catch</code>) yoktur. Bir işlem
başarısız olabiliyorsa bunu <strong>dönüş tipinde</strong> söyler.
<p>Çağıran <code>match</code> yazmak zorunda kaldığı için hatayı görmezden
gelemez. Unutursan program çalışmaz — derleyici hangi durumu ele almadığını
söyler.</p>
<p>Hazır tanım <code>araclar/sonuc.nar</code> dosyasındadır; kendin de
yazabilirsin, çünkü sıradan bir <code>enum</code>'dur.</p>
""",
                "kod": '''enum Sonuc<T, H> {
  Tamam(T)
  Hata(H)
}

fn bol(a: Int, b: Int) -> Sonuc<Int, String> {
  if b == 0 {
    return Sonuc.Hata("sıfıra bölünemez")
  }
  return Sonuc.Tamam(a / b)
}

fn main() {
  for bolen in [4, 0] {
    match bol(100, bolen) {
      Sonuc.Tamam(deger) -> print("100 / ${bolen} = ${deger}")
      Sonuc.Hata(mesaj) -> print("olmadı: ${mesaj}")
    }
  }
}''',
                "tam": '''enum Sonuc<T, H> {
  Tamam(T)
  Hata(H)
}

fn bol(a: Int, b: Int) -> Sonuc<Int, String> {
  if b == 0 {
    return Sonuc.Hata("sıfıra bölünemez")
  }
  return Sonuc.Tamam(a / b)
}

fn main() {
  for bolen in [4, 0] {
    match bol(100, bolen) {
      Sonuc.Tamam(deger) -> print("100 / ${bolen} = ${deger}")
      Sonuc.Hata(mesaj) -> print("olmadı: ${mesaj}")
    }
  }
}''',
            },
            {
                "id": "generic-ozyineli",
                "baslik": "Kendine başvuran tipler",
                "aciklama": """
Bir tip kendi içinde yine kendini taşıyabilir. Bağlı liste ve ağaç gibi
yapılar böyle kurulur.
""",
                "kod": '''enum Agac<T> {
  Yaprak(T)
  Dal([Agac<T>])
}

fn topla(a: Agac<Int>) -> Int = match a {
  Agac.Yaprak(n) -> n
  Agac.Dal(dallar) -> dallar.map(|d| topla(d)).toplam()
}

fn main() {
  let agac = Agac.Dal([
    Agac.Yaprak(1),
    Agac.Dal([Agac.Yaprak(2), Agac.Yaprak(3)])
  ])
  print("yaprakların toplamı:", topla(agac))
}''',
                "tam": '''enum Agac<T> {
  Yaprak(T)
  Dal([Agac<T>])
}

fn topla(a: Agac<Int>) -> Int = match a {
  Agac.Yaprak(n) -> n
  Agac.Dal(dallar) -> dallar.map(|d| topla(d)).toplam()
}

fn main() {
  let agac = Agac.Dal([
    Agac.Yaprak(1),
    Agac.Dal([Agac.Yaprak(2), Agac.Yaprak(3)])
  ])
  print("yaprakların toplamı:", topla(agac))
}''',
            },
        ],
    },

    # --------------------------------------------------------------- arayüz
    {
        "id": "arayuz",
        "baslik": "Ortak davranış: arayüzler",
        "aciklama": "Farklı tiplere ortak davranış tanımlamak.",
        "konular": [
            {
                "id": "arayuz-giris",
                "baslik": "interface",
                "aciklama": """
Farklı tipler aynı işi yapabiliyorsa, bu ortak davranışa bir ad verilir.
<code>interface</code> yalnızca <strong>hangi metotların bulunması
gerektiğini</strong> söyler; nasıl yapılacağını her tip kendi bilir.
<p>Bir tip arayüzü bildiriminde üstlenir (<code>struct Nokta:
Yazdirilabilir</code>). Bu bir sözdür: metotlardan biri eksikse ya da
imzası tutmuyorsa program derlenmez.</p>
""",
                "kod": '''interface Yazdirilabilir {
  fn yaz() -> String
}

struct Nokta: Yazdirilabilir {
  x: Float
  y: Float
  fn yaz() -> String = "(${self.x}, ${self.y})"
}

struct Kisi: Yazdirilabilir {
  ad: String
  fn yaz() -> String = "kişi: " + self.ad
}

fn goster(sey: Yazdirilabilir) {
  print(sey.yaz())
}

fn main() {
  goster(Nokta { x: 1.0, y: 2.0 })
  goster(Kisi { ad: "Ayşe" })
}''',
                "tam": '''interface Yazdirilabilir {
  fn yaz() -> String
}

struct Nokta: Yazdirilabilir {
  x: Float
  y: Float
  fn yaz() -> String = "(${self.x}, ${self.y})"
}

struct Kisi: Yazdirilabilir {
  ad: String
  fn yaz() -> String = "kişi: " + self.ad
}

fn goster(sey: Yazdirilabilir) {
  print(sey.yaz())
}

fn main() {
  goster(Nokta { x: 1.0, y: 2.0 })
  goster(Kisi { ad: "Ayşe" })
}''',
            },
            {
                "id": "arayuz-liste",
                "baslik": "Farklı tipleri bir arada tutmak",
                "aciklama": """
Bir liste, aynı arayüzü üstlenen farklı tipleri bir arada tutabilir.
<code>enum</code> da arayüz üstlenebilir.
""",
                "kod": '''interface Yazdirilabilir {
  fn yaz() -> String
}

struct Kisi: Yazdirilabilir {
  ad: String
  fn yaz() -> String = "kişi: " + self.ad
}

enum Durum: Yazdirilabilir {
  Acik
  Kapali
  fn yaz() -> String = match self {
    Durum.Acik -> "açık"
    Durum.Kapali -> "kapalı"
  }
}

fn main() {
  let hepsi: [Yazdirilabilir] = [
    Kisi { ad: "Ayşe" },
    Durum.Acik,
    Durum.Kapali
  ]
  for e in hepsi {
    print("- " + e.yaz())
  }
}''',
                "tam": '''interface Yazdirilabilir {
  fn yaz() -> String
}

struct Kisi: Yazdirilabilir {
  ad: String
  fn yaz() -> String = "kişi: " + self.ad
}

enum Durum: Yazdirilabilir {
  Acik
  Kapali
  fn yaz() -> String = match self {
    Durum.Acik -> "açık"
    Durum.Kapali -> "kapalı"
  }
}

fn main() {
  let hepsi: [Yazdirilabilir] = [
    Kisi { ad: "Ayşe" },
    Durum.Acik,
    Durum.Kapali
  ]
  for e in hepsi {
    print("- " + e.yaz())
  }
}''',
            },
            {
                "id": "arayuz-generic",
                "baslik": "Tip parametresine sınır koymak",
                "aciklama": """
Generic bir fonksiyonda tip parametresine sınır konabilir:
<code>&lt;T: Olculebilir&gt;</code> "T her tip olabilir, yeter ki
<code>olcu</code> metodu olsun" demektir.
<p>Böylece fonksiyon içinde o metodu çağırabilirsin; sınır koymadığın
metotları kullanmana derleyici izin vermez.</p>
""",
                "kod": '''interface Olculebilir {
  fn olcu() -> Float
}

struct Nokta: Olculebilir {
  x: Float
  y: Float
  fn olcu() -> Float = sqrt(self.x * self.x + self.y * self.y)
}

fn enBuyuk<T: Olculebilir>(liste: [T]) -> Float {
  var en = 0.0
  for e in liste {
    if e.olcu() > en {
      en = e.olcu()
    }
  }
  return en
}

fn main() {
  print(enBuyuk([
    Nokta { x: 3.0, y: 4.0 },
    Nokta { x: 6.0, y: 8.0 }
  ]))
}''',
                "tam": '''interface Olculebilir {
  fn olcu() -> Float
}

struct Nokta: Olculebilir {
  x: Float
  y: Float
  fn olcu() -> Float = sqrt(self.x * self.x + self.y * self.y)
}

fn enBuyuk<T: Olculebilir>(liste: [T]) -> Float {
  var en = 0.0
  for e in liste {
    if e.olcu() > en {
      en = e.olcu()
    }
  }
  return en
}

fn main() {
  print(enBuyuk([
    Nokta { x: 3.0, y: 4.0 },
    Nokta { x: 6.0, y: 8.0 }
  ]))
}''',
            },
        ],
    },

    # -------------------------------------------------------------- güvenlik
    {
        "id": "opsiyonel",
        "baslik": "Olmayabilen değerler",
        "aciklama": "Olmayabilen değeri tipin kendisinde taşımak.",
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
                "id": "if-let",
                "baslik": "if let — açarak dallanmak",
                "aciklama": """
Olmayabilen bir değeri açıp aynı anda dallanmak için <code>if let</code>.
Değer <code>none</code> değilse ada bağlanır ve o dalda <strong>açılmış</strong>
hâliyle görünür; <code>!</code> yazmak gerekmez.
<p>Bu olmadan önce bir değişkene almak, sonra sorup sonra açmak gerekirdi:</p>
<pre class="komut"><code>let e = bul("#uygulama")
if e != none {
  e!.ekle(baslik)
}</code></pre>
<p><code>else</code> dalında ad görünmez: orada değer zaten yoktur.
<code>else if let</code> ile zincirlenebilir.</p>
""",
                "kod": '''fn yas(ad: String) -> Int? {
  let defter = {"Ayşe": 30, "Mehmet": 24}
  return defter.get(ad)
}

fn main() {
  if let y = yas("Ayşe") {
    print("Ayşe ${y} yaşında")
  } else {
    print("Ayşe defterde yok")
  }

  if let y = yas("Zeynep") {
    print("Zeynep ${y} yaşında")
  } else if let y = yas("Mehmet") {
    print("Zeynep yok ama Mehmet ${y} yaşında")
  } else {
    print("ikisi de yok")
  }
}''',
                "not": "Nar zaten daraltma yapar: <code>if x != none</code> içinde "
                       "<code>x</code> açılmış sayılır. <code>if let</code> bunu bir "
                       "adım öteye taşır — değer bir çağrıdan geliyorsa önce "
                       "değişkene almak gerekmez.",
            },
            {
                "id": "soru-operatoru",
                "baslik": "? — gelmediyse ben de gelmedim",
                "aciklama": """
Olmayabilen değerlerle çalışan kodun büyük kısmı aynı cümledir:
<em>gelmediyse ben de gelmedim</em>. <code>?</code> tam bunu yazar —
değer <code>none</code> ise fonksiyondan hemen <code>none</code> döner,
değilse açılmış değeri verir.
<p>Bu olmadan her adım dört satırdı:</p>
<pre class="komut"><code>let satir = satirlar.first()
if satir == none {
  return none
}
let sayi = int(satir!.trim())
if sayi == none {
  return none
}
return sayi</code></pre>
<p><code>?</code> fonksiyondan <strong>erken çıkar</strong>, bu yüzden iki
koşulu var: değerin opsiyonel olması ve bulunduğu fonksiyonun opsiyonel
döndürmesi. İkisi de sağlanmıyorsa derleyici söyler.</p>
<p>Erken çıkışın konabileceği bir yer olmayan yerlerde <code>?</code>
kullanılamaz: <code>??</code>, <code>&amp;&amp;</code> ve <code>||</code> işleçlerinin
sağında, değer üreten <code>if</code>in dallarında, <code>match</code>
kollarında, <code>while</code> koşulunda ve tek ifadelik lambda gövdesinde.
Bu yerlerde sessizce yanlış çalışmak yerine açık bir hata alırsın;
değeri önce bir değişkene al. Gövdeli lambdada serbesttir — orada <code>?</code>
lambdadan çıkar.</p>
""",
                "kod": '''// Satırların ilkindeki sayıyı okur.
// Herhangi bir adım tutmazsa sonuç none olur.
fn ilkSayi(satirlar: [String]) -> Int? {
  let satir = satirlar.first()?
  return int(satir.trim())?
}

fn main() {
  print(ilkSayi(["  42  ", "başka satır"]) ?? -1)
  print(ilkSayi(["sayı değil"]) ?? -1)
  print(ilkSayi([]) ?? -1)
}''',
                "not": "Değer bir kez hesaplanır: <code>f()?</code> çağrıyı iki "
                       "kez yapmaz. Üretilen JavaScript de elle yazılmış gibi "
                       "durur — geçici bir değişken ve bir <code>if</code>.",
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
        "aciklama": "Tarayıcıda çalışan sayfa üretmek.",
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

    # ------------------------------------------------------------------ arayüz
    {
        "id": "arayuz-katmani",
        "baslik": "Uygulama arayüzü",
        "aciklama": "Durumdan görünüm üreten bildirimsel arayüz katmanı.",
        "konular": [
            {
                "id": "arayuz-nedir",
                "baslik": "Ekranı tarif etmek",
                "aciklama": """
Bir önceki bölümde öğeleri tek tek oluşturup sayfaya ekledik. Uygulama
büyüdükçe bu yorucu olur: bir şey değişince hangi öğeyi güncelleyeceğini
takip etmen gerekir.
<p><code>araclar/arayuz.nar</code> kütüphanesi bunu tersine çevirir:
ekranı <strong>nasıl kuracağını</strong> değil, <strong>neye benzemesi
gerektiğini</strong> yazarsın. Durum değişince kütüphane ekranı kendisi
yeniler.</p>
<p>Bu kütüphane Nar'ın kendisiyle yazılmıştır — dilin bir parçası değil,
dille yazılmış sıradan bir dosyadır. İstersen kopyalayıp kendine göre
değiştirebilirsin.</p>
""",
                "kod": '''import "araclar/arayuz.nar"

// Ekran bir Gorunum ağacıdır: Sutun, Satir, Kutu içinde
// Metin, Baslik, Dugme, Giris, Bosluk, Cizgi.
fn ciz(sayi: Int) -> Gorunum = Kutu([
  Baslik("Sayaç"),
  Metin("değer: ${sayi}"),
  Satir([
    Dugme("azalt", || { azalt() }),
    Dugme("artır", || { artir() })
  ])
])''',
                "calistirma": False,
            },
            {
                "id": "arayuz-uygulama",
                "baslik": "Durum ve otomatik yenileme",
                "aciklama": """
<code>uygulamaBaslat</code> üç şey ister: çizimin yapılacağı yer, başlangıç
durumu ve durumu görünüme çeviren fonksiyon.
<p>Durumu <code>degistir</code> ile güncellersin; ekranı yenilemek senin
işin değildir. Durum her tip olabilir — sayı, metin, kendi
<code>struct</code>'ın ya da bunların listesi.</p>
""",
                "kod": '''import "araclar/arayuz.nar"

var uygulama: Uygulama<Int>? = none

fn artir() {
  if uygulama != none {
    uygulama!.degistir(uygulama!.durum + 1)
  }
}

fn ciz(sayi: Int) -> Gorunum = Sutun([
  Baslik("Sayaç"),
  Metin("değer: ${sayi}"),
  Dugme("artır", || { artir() })
])

fn main() {
  // Sayfadaki <div id="uygulama"></div> içine çizer.
  uygulama = uygulamaBaslat("#uygulama", 0, ciz)
}''',
                "calistirma": False,
            },
            {
                "id": "arayuz-liste-uygulama",
                "baslik": "Örnek: yapılacaklar listesi",
                "aciklama": """
Görünümü üreten kod sıradan Nar kodudur: <code>if</code>, <code>for</code>,
liste işlemleri hepsi kullanılabilir. Aşağıdaki parça, listeyi görünüme
çeviren kısımdır.
<p>Tamamı <code>ornekler/yapilacaklar_uygulamasi.nar</code> dosyasındadır.
Masaüstü uygulaması olarak paketlemek için:
<code>nar build ornekler/yapilacaklar_uygulamasi.nar --target masaustu</code></p>
""",
                "kod": '''fn gorevSatiri(sira: Int, g: Gorev) -> Gorunum {
  var kutu = "[ ]"
  if g.bitti {
    kutu = "[x]"
  }
  return Satir([
    Dugme(kutu, || { gorevDegistir(sira) }),
    Metin(g.baslik)
  ])
}

fn gorevListesi(gorevler: [Gorev]) -> Gorunum {
  if gorevler.len() == 0 {
    return Metin("Henüz görev yok.")
  }
  var satirlar: [Gorunum] = []
  var sira = 0
  for g in gorevler {
    satirlar.push(gorevSatiri(sira, g))
    sira += 1
  }
  return Sutun(satirlar)
}''',
                "calistirma": False,
            },
            {
                "id": "arayuz-deri",
                "baslik": "Deriler: aynı bileşenler, başka biçim",
                "aciklama": """
<strong>Tema</strong> rengi seçer (açık / koyu), <strong>deri</strong> biçimi:
yarıçap, boşluk, gölge ve hareket. İkisi birbirinden bağımsızdır — yumuşak
deri hem açık hem koyu temada çalışır.
<p>Şu an iki deri var: varsayılan ve <code>yumusak</code>. Yumuşak deri
düğmeleri hap biçimine sokar, kartları yuvarlatıp yükseltir, girdileri
kenarlık yerine yumuşak bir yuvaya oturtur ve boşlukları açar.</p>
<p>Deri <strong>paleti değiştirmez</strong>. Kenarları zeminle aynı renge
çeken kabartma yaklaşımı yumuşak görünür ama kontrast eşiğini geçemez;
buradaki yumuşaklık renkten değil biçimden gelir, o yüzden okunabilirlik
her deride aynı kalır.</p>
""",
                "kod": '''import "../araclar/arayuz.nar"

fn ciz(n: Int) -> Gorunum = Kart("Deri denemesi", [
  Metin("Sayaç: ${n}"),
  Satir([
    Dugme("Artır", || { }),
    IkincilDugme("Sıfırla", || { })
  ])
])

fn main() {
  deriSec("yumusak")        // "" verirsen varsayılana döner
  uygulamaBaslat("#uygulama", 0, ciz)
}''',
                "calistirma": False,
                "not": "Deri ayrı bir stil öğesinde durur; durum değişip "
                       "ekran yeniden çizildiğinde bozulmaz. Seçili deriyi "
                       "<code>deri()</code> ile okuyabilirsin.",
            },
            {
                "id": "arayuz-hareket",
                "baslik": "Hareket: anlam taşıyan animasyon",
                "aciklama": """
Hareket <strong>anlam taşımalı</strong>. Taşımıyorsa hem gereksizdir hem de
erişilebilirlik borcu yaratır. Kütüphane bu yüzden keyfi bir tween motoru
değil, adı olan az sayıda hareket sunar.
<p>Her şey CSS ile yapılır; Nar yalnızca sınıf ekler. Bunun üç sonucu var:
hareket birleştirici üzerinde yürür, kullanıcı araya girdiğinde takılı kalan
durum olmaz (doğruluk hiçbir zaman <code>animationend</code> olayına bağlı
değildir), ve <code>prefers-reduced-motion</code> açıkken hareket tamamen
kapanıp öğe <strong>nihai okunabilir durumunda</strong> görünür — yalnız süre
kısaltılmaz.</p>
<p>Giriş hareketleri öğe <strong>ilk kez</strong> göründüğünde bir kez oynar.
Durum her değiştiğinde ağaç baştan çizilir; hareket her çizimde oynasaydı bir
giriş alanına yazan kişi her tuşta bütün ekranın yeniden süzülmesini izlerdi.
Sekme ya da sayfa değiştirirken <code>hareketDefteriniSil()</code> çağırırsan
yeni içerik yeniden girer.</p>
<p>Süreklilik yalnızca yükleme göstergelerinde var: <code>Iskelet</code> ve
<code>Donuyor</code>. Dekoratif öğede sonsuz döngü yok.</p>
<p>Yoğunluk üç kademede: <code>KADEME_SAKIN</code>, <code>KADEME_OLCULU</code>
(varsayılan) ve <code>KADEME_BELIRGIN</code>. Kademeyi bir kez seç, sonra o
kademede kal — tek bir süreyi her geçişe kopyalamak da, her geçişe ayrı süre
uydurmak da yanlış.</p>
""",
                "kod": '''import "../araclar/arayuz.nar"

fn ciz(yukleniyor: Bool) -> Gorunum {
  if yukleniyor {
    return Kart("Kayıtlar", [
      Iskelet(3),
      Bosluk(8),
      Donuyor("Veri geliyor…")
    ])
  }

  return Kart("Kayıtlar", [
    Sirali([
      Metin("Ayşe"),
      Metin("Mehmet"),
      Metin("Zeynep")
    ]),
    Cizgi,
    Hareketli(NABIZ, Rozet("kaydedildi", TON_BASARI))
  ])
}

fn main() {
  kademeSec(KADEME_SAKIN)
  uygulamaBaslat("#uygulama", true, ciz)
}''',
                "calistirma": False,
                "not": "Yalnız <code>transform</code> ve <code>opacity</code> "
                       "hareket eder. <code>width</code>, <code>height</code>, "
                       "<code>top</code> ve <code>left</code> hareket ettirmek "
                       "her karede yerleşimi yeniden hesaplatır.",
            },
            {
                "id": "arayuz-uyum",
                "baslik": "Uyum: .mobil() ile dar ekran",
                "aciklama": """
Dar ekrana uyum web'de satırlarca medya sorgusu demektir. Bildirimsel
modelde bunun yeri görünümün <strong>üstüdür</strong>: her görünüm kendi
uyarlamasını bir metotla taşır, medya sorgusu yazılmaz.
<ul>
<li><code>.mobildeSutun()</code> — dar ekranda satır sütuna döner</li>
<li><code>.mobildeGizle()</code> / <code>.masaustundeGizle()</code> — yalnız bir ekranda görünür</li>
<li><code>.mobil(g)</code> — dar ekranda yerine bambaşka bir görünüm gelir</li>
</ul>
<p>İlk üçü saf CSS sınıfıdır; hiçbir JavaScript çalışmaz. <code>.mobil()</code>
ise kırılma noktası değişince uygulamayı yeniden çizer — dar görünüm durum
gibi ele alınır. Tek DOM ağacı vardır; iki dalı birden çizip CSS ile birini
gizlemek olay dinleyicilerini ve odağı ikiye katlardı.</p>
<p>Metotlar zincirlenir ve üst üste sarmaz: <code>Satir([...]).mobildeSutun().mobildeGizle()</code> tek katmandır.
Sınır 600px; telefon dikey ve küçük tabletler dar sayılır. Kendi sorgun
gerekiyorsa dildeki <code>medyaEslesir(sorgu)</code> ve
<code>medyaDinle(sorgu, islev)</code> yerleşikleri elinde.</p>
""",
                "kod": '''import "../araclar/arayuz.nar"

fn ciz(n: Int) -> Gorunum = Kart("Sipariş", [
  // Geniş ekranda yan yana, telefonda alt alta.
  Satir([
    Kutu([Metin("Ürün: Nar")]),
    Kutu([Metin("Adet: 3")]),
    Kutu([Metin("Tutar: 120₺")])
  ]).mobildeSutun(),

  // Geniş ekranda tablo, telefonda liste.
  Tablo(["Ad", "Adet"], [["Nar", "3"]]).mobil(Liste(["Nar × 3"])),

  Rozet("klavye kısayolu: Ctrl+K", TON_BILGI).mobildeGizle(),
  Dugme("Öde", || { }).masaustundeGizle()
])

fn main() {
  uygulamaBaslat("#uygulama", 0, ciz)
}''',
                "calistirma": False,
            },
        ],
    },

    # ------------------------------------------------------------------ hedefler
    {
        "id": "hedefler",
        "baslik": "Uygulamayı dağıtmak",
        "aciklama": "Aynı kaynaktan web, masaüstü ve mobil çıktı almak.",
        "konular": [
            {
                "id": "hedef-nedir",
                "baslik": "Aynı koddan dört hedef",
                "aciklama": """
Yazdığın Nar programı tek bir kaynaktır; hangi ortama gideceğini
<code>--target</code> seçer.
<table class="ref">
<tr><td><code>nar run program.nar</code></td><td>Terminalde çalıştırır (Node.js)</td></tr>
<tr><td><code>nar build program.nar --target web</code></td><td>Tek dosyalık HTML sayfası</td></tr>
<tr><td><code>nar build program.nar --target masaustu</code></td><td>Kendi penceresinde açılan uygulama</td></tr>
<tr><td><code>nar build program.nar --target mobil</code></td><td>Android ve iOS projesi</td></tr>
</table>
<p>Sayfayla konuşan işlemler (<code>bul</code>, <code>olustur</code>) terminalde
sessizce boş döner; yani aynı kod her hedefte çöküp kalmaz.</p>
""",
                "kod": '''// Aynı program dört hedefte de çalışır.
fn main() {
  let kutu = bul("#uygulama")
  if kutu == none {
    print("terminaldeyiz")
    return
  }
  kutu!.metinYaz("tarayıcıdayız")
}''',
                "calistirma": False,
            },
            {
                "id": "hedef-masaustu",
                "baslik": "Masaüstü uygulaması",
                "aciklama": """
<code>--target masaustu</code> kendi başına çalışan bir klasör üretir:
programın HTML'i, onu kendi penceresinde açan bir başlatıcı ve Windows
için bir <code>.cmd</code> dosyası.
<p>Kullanıcının bilgisayarında yalnızca <strong>Python</strong> olması yeter.
<code>pip install pywebview</code> yapılmışsa gerçek bir uygulama penceresi
açılır; yoksa tarayıcının adres çubuksuz uygulama penceresi kullanılır.</p>
""",
                "kod": '''nar build ornekler/yapilacaklar_uygulamasi.nar --target masaustu

# üretilen klasör:
#   index.html    programın kendisi
#   baslat.py     pencereyi açan başlatıcı
#   baslat.cmd    Windows kısayolu
#   BENIOKU.md''',
                "dil": "kabuk",
                "calistirma": False,
            },
            {
                "id": "hedef-mobil",
                "baslik": "Android ve iOS",
                "aciklama": """
<code>--target mobil</code> bir <strong>Capacitor</strong> projesi üretir.
Capacitor, uygulamanı gerçek bir mobil uygulamanın içine koyar; mağazaya
yüklenebilir.
<p>Üretilen sayfa telefon için hazırlanmıştır: çentikli ekranlarda güvenli
alan boşluğu bırakır, dokunma hedefleri parmakla basılacak boyuttadır
(44 piksel) ve çift dokunmayla yakınlaştırma kapalıdır.</p>
<p><strong>Önce telefon olmadan dene:</strong> üretilen
<code>www/index.html</code> dosyası tarayıcıda doğrudan açılır.</p>
<p><strong>Dürüst not:</strong> Android paketi için Android Studio, iOS için
macOS + Xcode gerekir. Bu paketleyici projeyi hazır eder ama derlemez;
üretilen proje bir cihazda denenmemiştir.</p>
""",
                "kod": '''nar build ornekler/yapilacaklar_uygulamasi.nar --target mobil

cd cikti/yapilacaklar_uygulamasi-mobil
npm install
npx cap add android
npx cap open android     # Android Studio açılır, ▶ ile çalıştır''',
                "dil": "kabuk",
                "calistirma": False,
            },
        ],
    },

    # -------------------------------------------------------------- derleyici
    {
        "id": "kendi-derleyicisi",
        "baslik": "Nar, Nar ile yazılıyor",
        "aciklama": "Derleyicinin Nar ile yazılan parçaları.",
        "konular": [
            {
                "id": "self-hosting",
                "baslik": "Dilin kendi kendini derlemesi",
                "aciklama": """
Nar'ın ilk derleyicisi Python ile yazıldı — bir dilin başlangıçta başka
bir dile ihtiyacı vardır. Ama olgun bir dil kendi derleyicisini kendi
diliyle yazabilmelidir; buna <strong>self-hosting</strong> denir.
<p>Nar bu yolda ilerliyor. Şu ana kadar Nar diliyle yazılanlar:</p>
<table class="ref">
<tr><td><code>derleyici/lexer.nar</code></td><td>Sözcüksel çözümleyici — kaynağı token'lara böler</td></tr>
<tr><td><code>derleyici/ast.nar</code></td><td>Soyut sözdizim ağacı, konumlar ve S-ifadesi yazıcı</td></tr>
<tr><td><code>derleyici/parser.nar</code></td><td>Sözdizim çözümleyici — token'lardan ağaç kurar</td></tr>
<tr><td><code>derleyici/tipler.nar</code></td><td>Tip sistemi — atanabilirlik, ortak tip, tip çıkarımı</td></tr>
<tr><td><code>derleyici/denetleyici.nar</code></td><td>Tip denetleyici (bildirim aşaması)</td></tr>
<tr><td><code>derleyici/denetle.nar</code></td><td>Giriş noktası; içe aktarmaları izler</td></tr>
<tr><td><code>araclar/renklendirici.nar</code></td><td>Sözdizimi renklendirici (bu sayfadaki renkler)</td></tr>
<tr><td><code>araclar/bicimlendirici.nar</code></td><td>Kod biçimlendirici (<code>nar fmt</code>)</td></tr>
<tr><td><code>araclar/arayuz.nar</code></td><td>Bildirimsel arayüz kütüphanesi</td></tr>
<tr><td><code>araclar/json.nar</code></td><td>JSON okuyucu ve yazıcı</td></tr>
<tr><td><code>araclar/ide_uygulamasi.nar</code></td><td>Nar IDE'nin tüm davranışı</td></tr>
</table>
<p>Sırada gövde denetimi (ifadeler ve deyimler) ve kod üreteci var.</p>
""",
                "kod": '''# Nar ile yazılmış derleyiciyle bir dosyayı denetle
nar ozdenetim ornekler/yapilacaklar_uygulamasi.nar

# Derleyici kendi kaynağını da okuyabiliyor
nar ozdenetim derleyici/parser.nar --kutuphane''',
                "dil": "kabuk",
                "calistirma": False,
            },
            {
                "id": "ozdenetim",
                "baslik": "nar ozdenetim",
                "aciklama": """
Nar ile yazılmış derleyiciyi elle denemek için bir komut var.
<code>nar ozdenetim</code> önce o derleyiciyi (Nar kaynağından) JavaScript'e
çevirir, sonra Node ile çalıştırıp verdiğin dosyayı denetler.
<p>İçe aktarmaları da izler: <code>import</code> edilen dosyaların
bildirimleri okunur, böylece başka dosyadaki tipler bilinir.</p>
<p><strong>Kapsam:</strong> sözcüksel çözümleme, sözdizim çözümleme ve tip
denetiminin <em>bildirim aşaması</em> — tipler, imzalar, arayüz uyumu.
Gövde denetimi (ifadeler, deyimler) henüz Nar'a taşınmadı; tam denetim için
<code>nar check</code> kullanılır.</p>
""",
                "kod": '''$ nar ozdenetim derleyici/denetleyici.nar --kutuphane
tamam — hata yok

$ nar ozdenetim bozuk.nar
hata: 2:1 — 'A' tipi zaten tanımlı
hata: 1:15 — bilinmeyen tip: 'Yok'
''',
                "dil": "kabuk",
                "calistirma": False,
            },
            {
                "id": "nasil-dogrulaniyor",
                "baslik": "Doğruluğu nasıl ölçülüyor",
                "aciklama": """
Yeni yazılan çözümleyicinin doğru olduğunu nasıl bilirsin? Nar'ın yanıtı:
<strong>iki çözümleyiciyi aynı kaynakla besleyip sonuçları
karşılaştırmak</strong>.
<p>Ağaçları karşılaştırabilmek için ortak bir yazım gerekir. Nar bunun
için <strong>S-ifadesi</strong> kullanır: ağacın parantezli metin hâli.
Konum bilgisi yazılmaz — iki çözümleyicinin satır/sütun hesabı birebir
aynı olmak zorunda değil, ağacın yapısı aynı olmak zorunda.</p>
<p>Karşılaştırma yapay örneklerle sınırlı değil: projedeki
<strong>bütün</strong> <code>.nar</code> dosyaları iki çözümleyiciden de
geçirilir. Ayrı bir modda konumlar (satır, sütun) da karşılaştırılır —
hata mesajlarının nereyi gösterdiği buna bağlı.</p>
<p>Tip sistemi için aynı yöntem: iki taraf aynı 40 tipi kurar,
atanabilirlik, ortak tip ve tip çıkarımı 1600 çift üzerinde
karşılaştırılır. Denetleyicide ise hata listeleri — mesaj, satır ve
sütunla birlikte.</p>
<p>Bu yöntem gerçek hatalar buldu: Türk alfabesinde olmadığı için harf
listesinden düşen <code>q</code> harfi; metin literalindeki
<code>${'{...}'}</code> gömmesinin içeriğinin token'da saklanmaması;
desende birden çok <code>_</code> kullanıldığında üretilen JavaScript'in
çökmesi.</p>
""",
                "kod": '''// Kaynak
fn kare(x: Int) -> Int = x * x

// İki çözümleyicinin de ürettiği S-ifadesi
(modul [(fn "kare" [] [] [(parametre "x" (tad "Int"))] (tad "Int")
  (blok [(donus (ikili "*" (ad "x") (ad "x")))]))])''',
                "calistirma": False,
            },
        ],
    },

    # ---------------------------------------------------------- program düzeni
    {
        "id": "duzen",
        "baslik": "Programı düzenlemek",
        "aciklama": "Dosyalara bölmek, içe aktarmak, biçimlendirmek, test etmek.",
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
                "id": "dosya-ve-program",
                "baslik": "Dosyalar, girdi ve zaman",
                "aciklama": """
Terminalde çalışan programlar dosya okuyup yazabilir, kullanıcıdan girdi
alabilir ve saate bakabilir.
<p><strong>Not:</strong> Bunlar yalnızca <code>nar run</code> ile (Node
üzerinde) anlamlıdır. Tarayıcıda dosya okuma <code>none</code>, yazma
<code>false</code> döner — program çökmez, sadece iş yapmaz.</p>
<p>Okuma her zaman "olabilir" sonuç verir: dosya yoksa <code>none</code>
gelir, kontrol etmen gerekir.</p>
""",
                "kod": '''fn main() {
  // Dosya yazma ve okuma
  dosyaYaz("not.txt", "birinci satır\\n")
  dosyaEkle("not.txt", "ikinci satır\\n")

  let icerik = dosyaOku("not.txt")
  if icerik != none {
    print("satır sayısı:", icerik!.trim().split("\\n").len())
  }

  print("var mı:", dosyaVarMi("not.txt"))
  dosyaSil("not.txt")

  // Klasördeki dosyalar
  let dosyalar = klasorListele("ornekler")
  print("kaç dosya:", dosyalar.len())

  // Komut satırı argümanları
  print("argümanlar:", argumanlar())

  // Zaman
  print("şu an:", zamanMetni())
  let basla = simdi()
  var toplam = 0
  for i in 1..=1000 { toplam += i }
  print("geçen süre (ms):", simdi() - basla)

  // Kullanıcıdan girdi (terminalden):
  //   let satir = satirOku()
  //   if satir != none { print("girdin: " + satir!) }
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
        "baslik": "Dosya, girdi ve zaman",
        "aciklama": "Yalnızca terminalde (Node) anlamlıdır; tarayıcıda iş yapmazlar.",
        "satirlar": [
            ("dosyaOku(yol)", "Dosyayı okur (yoksa none)"),
            ("dosyaYaz(yol, icerik)", "Dosyayı yazar (üzerine yazar)"),
            ("dosyaEkle(yol, icerik)", "Dosyanın sonuna ekler"),
            ("dosyaVarMi(yol) · dosyaSil(yol)", "Var mı · siler"),
            ("klasorListele(yol)", "Klasördeki dosya adları"),
            ("satirOku()", "Girdiden bir satır okur (bitince none)"),
            ("tumGirdi()", "Girdinin tamamını okur"),
            ("argumanlar()", "Komut satırı argümanları"),
            ("komutCalistir(program, argumanlar)",
             "Başka bir programı çalıştırır; .cikis() .cikti() .hata()"),
            ("cik(kod)", "Programı verilen çıkış koduyla bitirir"),
            ("simdi()", "1970'ten beri geçen milisaniye"),
            ("zamanMetni()", "Okunabilir tarih-saat"),
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

"""Uçtan uca testler: Nar kaynağı → JavaScript → Node → çıktı karşılaştırma.

Bunlar dilin gerçekten çalıştığını gösteren asıl testlerdir; tip denetimi
geçen bir programın doğru sonucu ürettiğini doğrularlar.

Çalıştırma:  python -m unittest discover -s testler
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from narc.checker import Checker  # noqa: E402
from narc.backends import js as js_backend  # noqa: E402
from narc.parser import parse  # noqa: E402

NODE = shutil.which("node")


def derle(src: str) -> str:
    module = parse(src, "test.nar")
    checker = Checker(module, src)
    checker.check()
    return js_backend.generate(module, checker)


def calistir(src: str) -> str:
    """Kaynağı derler, Node ile çalıştırır ve stdout+stderr döndürür."""
    code = derle(src)
    with tempfile.TemporaryDirectory() as tmp:
        script = Path(tmp) / "program.js"
        script.write_text(code, encoding="utf-8")
        result = subprocess.run(
            [NODE, str(script)], capture_output=True, text=True, encoding="utf-8",
        )
    return (result.stdout + result.stderr).strip()


def govde(body: str) -> str:
    return "fn main() {\n" + body + "\n}\n"


@unittest.skipIf(NODE is None, "node bulunamadı")
class CalistirmaTesti(unittest.TestCase):
    def esit(self, body: str, beklenen: str):
        self.assertEqual(calistir(govde(body)), beklenen.strip())

    def program(self, src: str, beklenen: str):
        self.assertEqual(calistir(src), beklenen.strip())

    # --- sayılar ve operatörler ---
    def test_aritmetik(self):
        self.esit('print(str(2 + 3 * 4))', "14")

    def test_int_bolme_kirpar(self):
        self.esit('print(str(7 / 2))', "3")

    def test_negatif_int_bolme(self):
        self.esit('print(str(-7 / 2))', "-3")

    def test_float_bolme(self):
        self.esit('print(str(7.0 / 2.0))', "3.5")

    def test_mod(self):
        self.esit('print(str(7 % 3))', "1")

    def test_sifira_bolme_panik(self):
        cikti = calistir(govde('print(str(1 / 0))'))
        self.assertIn("sıfıra bölme", cikti)

    def test_float_yazimi(self):
        self.esit('print(4.0)', "4.0")

    def test_float_listesi(self):
        self.esit('print([1.0, 2.5])', "[1.0, 2.5]")

    def test_oncelik_zinciri(self):
        self.esit('print(str(2 + 3 * 4 - 6 / 2))', "11")

    # --- sadeleştirmeler (v0.2) ---
    def test_int_float_karisik_islem(self):
        self.esit('print(1 + 2.0)\nprint(3 * 1.5)\nprint(7 / 2.0)\nprint(2.0 - 1)',
                  "3.0\n4.5\n3.5\n1.0")

    def test_karisik_islemde_int_bolme_kalmaz(self):
        # 7 / 2 tam bölme, 7 / 2.0 ondalıklı — sonuç tipi belirler
        self.esit('print(7 / 2)\nprint(7 / 2.0)', "3\n3.5")

    def test_karisik_karsilastirma(self):
        self.esit('print(1 < 2.5)\nprint(3.0 == 3)', "true\ntrue")

    def test_metin_ile_sayi_birlestirme(self):
        self.esit('print("yaş: " + 25)\nprint("pi " + 3.5)\nprint(1 + " adet")',
                  "yaş: 25\npi 3.5\n1 adet")

    def test_metin_ile_liste_birlestirme(self):
        self.esit('print("liste: " + [1, 2])', "liste: [1, 2]")

    def test_metin_arti_esittir(self):
        self.esit('var s = "sayı: "\ns += 42\nprint(s)', "sayı: 42")

    def test_cok_argumanli_print(self):
        self.esit('print("ad:", "Ayşe", "yaş:", 30)', "ad: Ayşe yaş: 30")

    def test_matematik_tam_sayi_kabul_eder(self):
        self.esit('print(sqrt(16))\nprint(pow(2, 10))\nprint(max(3, 2.5))',
                  "4.0\n1024.0\n3.0")

    def test_if_ifadesi(self):
        self.esit('let x = if 5 > 3 { "büyük" } else { "küçük" }\nprint(x)', "büyük")

    def test_if_ifadesi_zinciri(self):
        self.program('''fn harf(n: Int) -> String = if n >= 90 { "A" } else if n >= 80 { "B" } else { "C" }
fn main() {
  print(harf(95))
  print(harf(85))
  print(harf(60))
}''', "A\nB\nC")

    def test_if_ifadesi_ic_ice(self):
        self.esit('let n = 4\nprint("sonuç: " + if n > 2 { n * 10 } else { 0 })',
                  "sonuç: 40")

    def test_match_ifadesi(self):
        self.program('''enum Hava { Gunesli  Yagmurlu  Karli }
fn tavsiye(h: Hava) -> String = match h {
  Hava.Gunesli -> "şapka"
  Hava.Yagmurlu -> "şemsiye"
  Hava.Karli -> "mont"
}
fn main() { print(tavsiye(Hava.Yagmurlu)) }''', "şemsiye")

    def test_match_ifadesi_baglama(self):
        self.program('''enum Kutu { Dolu(Int)  Bos }
fn main() {
  let d = match Kutu.Dolu(7) {
    Kutu.Dolu(n) -> n * 2
    Kutu.Bos -> 0
  }
  print(d)
}''', "14")

    def test_match_ifadesi_literal(self):
        self.esit('''let n = 3
print(match n { 1 -> "bir"  2 -> "iki"  _ -> "çok" })''', "çok")

    def test_kisa_fonksiyon_govdesi(self):
        self.program('''fn kare(x: Int) -> Int = x * x
fn selam(ad: String) -> String = "Merhaba " + ad
fn main() { print(kare(7))
 print(selam("Nar")) }''', "49\nMerhaba Nar")

    def test_kisa_metot_govdesi(self):
        self.program('''struct D { kenar: Float
  fn alan() -> Float = self.kenar * self.kenar
}
fn main() { print(D { kenar: 3.0 }.alan()) }''', "9.0")

    # --- metin ---
    def test_metin_gommesi(self):
        self.esit('let a = 5\nprint("a=${a}, iki katı ${a * 2}")', "a=5, iki katı 10")

    def test_metin_metotlari(self):
        self.esit('''let s = "  Merhaba Dünya  "
print(s.trim().lower())
print(s.trim().split(" ").join("|"))
print(str(s.contains("Dünya")))''', "merhaba dünya\nMerhaba|Dünya\ntrue")

    def test_turkce_buyuk_harf(self):
        self.esit('print("istanbul".upperTr())\nprint("IĞDIR".lowerTr())',
                  "İSTANBUL\nığdır")

    def test_metin_dizinleme_unicode(self):
        self.esit('let s = "çğü"\nprint(s.charAt(1))\nprint(str(s.len()))', "ğ\n3")

    def test_metin_replace_tumu(self):
        self.esit('print("a-b-c".replace("-", "+"))', "a+b+c")

    # --- listeler ---
    def test_liste_islemleri(self):
        self.esit('''var l = [3, 1, 2]
l.push(0)
print(str(l.len()))
print(l.sort())
print(l.reverse())
print(str(l.contains(2)))
print(str(l.indexOf(9)))''', "4\n[0, 1, 2, 3]\n[0, 2, 1, 3]\ntrue\n-1")

    def test_map_filter_reduce(self):
        self.esit('''let l = [1, 2, 3, 4]
print(l.map(|x| x * x))
print(l.filter(|x| x % 2 == 0))
print(str(l.reduce(|a, b| a + b, 0)))''', "[1, 4, 9, 16]\n[2, 4]\n10")

    def test_liste_sinir_asimi(self):
        cikti = calistir(govde('let l = [1]\nprint(str(l[3]))'))
        self.assertIn("liste sınırı aşıldı", cikti)

    def test_liste_dizinine_atama(self):
        self.esit('var l = [1, 2, 3]\nl[1] = 9\nprint(l)', "[1, 9, 3]")

    def test_liste_birlestirme(self):
        # Regresyon: JS'te `dizi + dizi` metne çevirir; birleştirme olmalı
        self.esit('let a = [1, 2]\nlet b = [3]\nprint(a + b)', "[1, 2, 3]")

    def test_liste_birlestirme_metin(self):
        self.esit('print(["a"] + ["b"])', '["a", "b"]')

    def test_bos_liste_pop(self):
        self.esit('var l: [Int] = []\nprint(str(l.pop() ?? -1))', "-1")

    # --- eşlemeler ---
    def test_esleme(self):
        self.esit('''var m = {"a": 1, "b": 2}
m.set("c", 3)
print(str(m.len()))
print(str(m.get("b") ?? 0))
print(str(m.get("yok") ?? -1))
print(str(m.has("a")))
m.remove("a")
print(str(m.has("a")))''', "3\n2\n-1\ntrue\nfalse")

    def test_esleme_dongusu(self):
        self.esit('''let m = {"x": 1, "y": 2}
var toplam = 0
for (k, v) in m { toplam = toplam + v }
print(str(toplam))''', "3")

    def test_esleme_dizinleme(self):
        self.esit('let m = {"a": 5}\nprint(str(m["a"] ?? 0))\nprint(str(m["z"] ?? 0))', "5\n0")

    # --- opsiyoneller ---
    def test_opsiyonel_varsayilan(self):
        self.esit('let a: Int? = none\nprint(str(a ?? 7))', "7")

    def test_opsiyonel_daraltma(self):
        self.esit('let a: Int? = 3\nif a != none { print(str(a * 2)) }', "6")

    def test_zorla_acma_panik(self):
        cikti = calistir(govde('let a: Int? = none\nprint(str(a!))'))
        self.assertIn("'none' değeri açılmaya çalışıldı", cikti)

    def test_guvenli_zincir(self):
        self.program('''struct Adres { sehir: String }
struct Kisi { adres: Adres? }
fn main() {
  let k = Kisi { adres: none }
  print(k.adres?.sehir ?? "bilinmiyor")
  let k2 = Kisi { adres: Adres { sehir: "Ankara" } }
  print(k2.adres?.sehir ?? "bilinmiyor")
}''', "bilinmiyor\nAnkara")

    def test_guvenli_yerlesik_metot(self):
        self.esit('let s: String? = none\nprint(s?.upper() ?? "yok")', "yok")

    # --- denetim akışı ---
    def test_dongu_ve_kosul(self):
        self.esit('''var toplam = 0
for i in 1..=10 {
  if i % 2 == 0 { continue }
  if i > 7 { break }
  toplam = toplam + i
}
print(str(toplam))''', "16")

    def test_while_dongusu(self):
        self.esit('var i = 0\nwhile i < 5 { i = i + 1 }\nprint(str(i))', "5")

    def test_aralik_sinirlari(self):
        self.esit('''var a = 0
for i in 0..3 { a = a + 1 }
var b = 0
for i in 0..=3 { b = b + 1 }
print("${a} ${b}")''', "3 4")

    def test_aralik_ust_sinir_bir_kez_hesaplanir(self):
        self.program('''var cagri = 0
fn son() -> Int { cagri = cagri + 1
 return 3 }
fn main() {
  for i in 0..son() { }
  print(str(cagri))
}''', "1")

    def test_ic_ice_dongu(self):
        self.esit('''var n = 0
for i in 0..3 {
  for j in 0..3 {
    if j == 1 { continue }
    n = n + 1
  }
}
print(str(n))''', "6")

    # --- struct ve enum ---
    def test_struct_metot(self):
        self.program('''struct Nokta { x: Float  y: Float
  fn uzunluk() -> Float { return sqrt(self.x * self.x + self.y * self.y) }
}
fn main() { print(str(Nokta { x: 3.0, y: 4.0 }.uzunluk())) }''', "5.0")

    def test_struct_alan_sirasi_onemsiz(self):
        self.program('''struct S { a: Int  b: String }
fn main() { let s = S { b: "iki", a: 1 }
 print("${s.a} ${s.b}") }''', "1 iki")

    def test_degisken_alan(self):
        self.program('''struct Sayac { var n: Int
  fn artir() { self.n = self.n + 1 }
}
fn main() { let s = Sayac { n: 0 }
 s.artir()
 s.artir()
 print(str(s.n)) }''', "2")

    def test_struct_esitligi_deger_bazli(self):
        self.program('''struct P { x: Int }
fn main() { print(str(P { x: 1 } == P { x: 1 })) }''', "true")

    def test_enum_eslesme(self):
        self.program('''enum Sonuc { Tamam(Int)  Hata(String)  Bos }
fn anlat(s: Sonuc) -> String {
  match s {
    Sonuc.Tamam(n) -> return "tamam ${n}"
    Sonuc.Hata(m) -> return "hata ${m}"
    Sonuc.Bos -> return "boş"
  }
}
fn main() {
  print(anlat(Sonuc.Tamam(5)))
  print(anlat(Sonuc.Hata("olmadı")))
  print(anlat(Sonuc.Bos))
}''', "tamam 5\nhata olmadı\nboş")

    def test_enum_yazimi(self):
        self.program('''enum E { A(Int, String)  B }
fn main() { print(E.A(1, "x"))
 print(E.B) }''', 'E.A(1, "x")\nE.B')

    def test_enum_esitligi(self):
        self.program('''enum E { A(Int)  B }
fn main() { print(str(E.A(1) == E.A(1)))
 print(str(E.A(1) == E.B)) }''', "true\nfalse")

    def test_match_literal_ve_joker(self):
        self.esit('''let n = 3
match n {
  1 -> print("bir")
  3 -> print("üç")
  _ -> print("diğer")
}''', "üç")

    def test_ic_ice_desen(self):
        self.program('''enum Kutu { Dolu(Icerik)  Bos }
enum Icerik { Sayi(Int)  Yazi(String) }
fn main() {
  match Kutu.Dolu(Icerik.Sayi(7)) {
    Kutu.Dolu(Icerik.Sayi(n)) -> print("sayı ${n}")
    Kutu.Dolu(Icerik.Yazi(s)) -> print("yazı ${s}")
    Kutu.Bos -> print("boş")
  }
}''', "sayı 7")

    # --- fonksiyonlar ---
    def test_ozyineleme(self):
        self.program('''fn fib(n: Int) -> Int {
  if n < 2 { return n }
  return fib(n - 1) + fib(n - 2)
}
fn main() { print(str(fib(20))) }''', "6765")

    def test_fonksiyon_degeri(self):
        self.program('''fn iki_kat(x: Int) -> Int { return x * 2 }
fn uygula(f: (Int) -> Int, x: Int) -> Int { return f(x) }
fn main() { print(str(uygula(iki_kat, 21))) }''', "42")

    def test_kapanis(self):
        self.esit('''let k = 10
let ekle = |x: Int| x + k
print(str(ekle(5)))''', "15")

    def test_bloklu_lambda(self):
        self.esit('''let f = |x: Int| {
  let y = x * 2
  return y + 1
}
print(str(f(5)))''', "11")

    # --- yerleşikler ---
    def test_sayi_yerlesikleri(self):
        self.esit('''print(str(abs(-5)))
print(str(min(3, 7)))
print(str(max(3, 7)))
print(str(floor(3.7)))
print(str(ceil(3.2)))
print(str(round(3.5)))
print(str(pow(2.0, 10.0)))''', "5\n3\n7\n3\n4\n4\n1024.0")

    def test_donusumler(self):
        self.esit('''print(str(int("42") ?? 0))
print(str(int("abc") ?? -1))
print(str(float("1.5") ?? 0.0))
print(str(float(3)))
print(str(int(3.9)))''', "42\n-1\n1.5\n3.0\n3")

    def test_panik(self):
        cikti = calistir(govde('panic("özel hata")'))
        self.assertIn("özel hata", cikti)

    def test_assert(self):
        cikti = calistir(govde('assert(1 == 2, "eşit değil")'))
        self.assertIn("eşit değil", cikti)

    # --- ayrılmış kelimeler ve isimler ---
    def test_js_ayrilmis_kelime_adi(self):
        self.esit('let class = 1\nlet new = 2\nprint(str(class + new))', "3")

    def test_turkce_degisken_adi(self):
        self.esit('let ağırlık = 70\nlet boy = 180\nprint(str(ağırlık + boy))', "250")

    # --- global değişken ---
    def test_global_degisken(self):
        self.program('''let BASLIK = "Nar"
fn main() { print(BASLIK) }''', "Nar")


if __name__ == "__main__":
    unittest.main(verbosity=2)

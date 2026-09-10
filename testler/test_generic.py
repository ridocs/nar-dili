"""Generic tip testleri: `struct Kutu<T>`, `enum Sonuc<T, H>`, `fn ilk<T>(...)`."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from narc.backends import js as js_backend  # noqa: E402
from narc.checker import Checker  # noqa: E402
from narc.diagnostics import NarError  # noqa: E402
from narc.parser import parse  # noqa: E402

NODE = shutil.which("node")


def derle(src: str) -> str:
    module = parse(src, "test.nar")
    checker = Checker(module, src)
    checker.check()
    return js_backend.generate(module, checker)


def calistir(src: str) -> str:
    kod = derle(src)
    with tempfile.TemporaryDirectory() as tmp:
        betik = Path(tmp) / "program.js"
        betik.write_text(kod, encoding="utf-8")
        sonuc = subprocess.run(
            [NODE, str(betik)], capture_output=True, text=True, encoding="utf-8",
        )
    return (sonuc.stdout + sonuc.stderr).strip()


@unittest.skipIf(NODE is None, "node bulunamadı")
class GenericTesti(unittest.TestCase):
    def esit(self, src: str, beklenen: str):
        self.assertEqual(calistir(src), beklenen.strip())

    def hatali(self, src: str, parca: str):
        with self.assertRaises(NarError) as ctx:
            derle(src)
        mesajlar = [h.message for h in getattr(ctx.exception, "errors", [ctx.exception])]
        self.assertTrue(
            any(parca in m for m in mesajlar),
            f"beklenen ipucu bulunamadı: {parca}\nalınan: {mesajlar}",
        )

    # --- generic struct ---
    def test_acik_tip_argumani(self):
        self.esit('''struct Kutu<T> { deger: T }
fn main() { print(Kutu<Int> { deger: 5 }.deger) }''', "5")

    def test_tip_argumani_cikarilir(self):
        self.esit('''struct Kutu<T> { deger: T }
fn main() {
  print(Kutu { deger: 5 }.deger)
  print(Kutu { deger: "metin" }.deger)
}''', "5\nmetin")

    def test_beklenen_tipten_alinir(self):
        self.esit('''struct Kutu<T> { deger: T }
fn main() {
  let k: Kutu<Float> = Kutu { deger: 2.5 }
  print(k.deger)
}''', "2.5")

    def test_generic_metot(self):
        self.esit('''struct Kutu<T> {
  deger: T
  fn al() -> T = self.deger
  fn yenile(y: T) -> Kutu<T> = Kutu<T> { deger: y }
}
fn main() {
  let k = Kutu { deger: 1 }
  print(k.al())
  print(k.yenile(9).al())
}''', "1\n9")

    def test_iki_tip_parametresi(self):
        self.esit('''struct Cift<A, B> { sol: A  sag: B }
fn main() {
  let c = Cift { sol: 1, sag: "iki" }
  print(c.sol, c.sag)
}''', "1 iki")

    def test_ic_ice_generic(self):
        self.esit('''struct Kutu<T> { deger: T }
fn main() {
  let ic = Kutu { deger: 3 }
  let dis = Kutu { deger: ic }
  print(dis.deger.deger)
}''', "3")

    def test_generic_yazdirmada_tip_korunur(self):
        # Float alan, silme yüzünden 4 değil 4.0 yazılmalı
        self.esit('''struct Kutu<T> { deger: T }
fn main() { print(Kutu<Float> { deger: 4.0 }) }''', "Kutu { deger: 4.0 }")

    # --- generic enum ---
    def test_generic_enum_donus_tipinden(self):
        self.esit('''enum Sonuc<T, H> { Tamam(T)  Hata(H) }
fn bol(a: Int, b: Int) -> Sonuc<Int, String> {
  if b == 0 { return Sonuc.Hata("sıfır") }
  return Sonuc.Tamam(a / b)
}
fn main() {
  match bol(10, 2) {
    Sonuc.Tamam(n) -> print("tamam", n)
    Sonuc.Hata(m) -> print("hata", m)
  }
  match bol(1, 0) {
    Sonuc.Tamam(n) -> print("tamam", n)
    Sonuc.Hata(m) -> print("hata", m)
  }
}''', "tamam 5\nhata sıfır")

    def test_generic_enum_metodu(self):
        self.esit('''enum Sonuc<T, H> {
  Tamam(T)
  Hata(H)
  fn iyiMi() -> Bool = match self {
    Sonuc.Tamam(_) -> true
    Sonuc.Hata(_) -> false
  }
}
fn yap() -> Sonuc<Int, String> = Sonuc.Tamam(1)
fn main() { print(yap().iyiMi()) }''', "true")

    def test_generic_enum_atamadan_cikarim(self):
        self.esit('''enum Kutu<T> { Dolu(T)  Bos }
fn main() {
  let k: Kutu<Int> = Kutu.Dolu(7)
  match k {
    Kutu.Dolu(n) -> print(n)
    Kutu.Bos -> print("boş")
  }
}''', "7")

    # --- generic fonksiyon ---
    def test_generic_fonksiyon_cikarim(self):
        self.esit('''fn ilk<T>(l: [T]) -> T? {
  if l.len() == 0 { return none }
  return l[0]
}
fn main() {
  print(ilk([3, 4]) ?? 0)
  print(ilk(["a"]) ?? "yok")
  let bos: [Int] = []
  print(ilk(bos) ?? -1)
}''', "3\na\n-1")

    def test_generic_fonksiyon_liste_dondurur(self):
        self.esit('''fn ikiKat<T>(x: T) -> [T] = [x, x]
fn main() {
  print(ikiKat(7))
  print(ikiKat("x"))
}''', '[7, 7]\n["x", "x"]')

    def test_generic_fonksiyon_iki_parametre(self):
        self.esit('''struct Cift<A, B> { sol: A  sag: B }
fn birlestir<A, B>(a: A, b: B) -> Cift<A, B> = Cift<A, B> { sol: a, sag: b }
fn main() {
  let c = birlestir(1, "iki")
  print(c.sol, c.sag)
}''', "1 iki")

    def test_generic_takas(self):
        self.esit('''struct Cift<A, B> { sol: A  sag: B }
fn takas<A, B>(c: Cift<A, B>) -> Cift<B, A> = Cift<B, A> { sol: c.sag, sag: c.sol }
fn main() {
  let c = Cift { sol: 1, sag: "iki" }
  let t = takas(c)
  print(t.sol, t.sag)
}''', "iki 1")

    # --- kendine başvuran generic tipler ---
    def test_bagli_liste(self):
        # Regresyon: alanlar hemen çözülseydi sonsuz döngüye girerdi.
        self.esit('''struct Dugum<T> {
  deger: T
  var sonraki: Dugum<T>?
}
fn main() {
  let son = Dugum<Int> { deger: 3, sonraki: none }
  let orta = Dugum { deger: 2, sonraki: son }
  let bas = Dugum { deger: 1, sonraki: orta }
  print(bas.deger, bas.sonraki?.deger ?? 0, bas.sonraki?.sonraki?.deger ?? 0)
}''', "1 2 3")

    def test_agac(self):
        self.esit('''enum Agac<T> {
  Yaprak(T)
  Dal([Agac<T>])
}
fn topla(a: Agac<Int>) -> Int = match a {
  Agac.Yaprak(n) -> n
  Agac.Dal(dallar) -> dallar.map(|d| topla(d)).toplam()
}
fn main() {
  let a = Agac.Dal([Agac.Yaprak(1), Agac.Dal([Agac.Yaprak(2), Agac.Yaprak(3)])])
  print(topla(a))
}''', "6")

    def test_kendini_donduren_metot(self):
        # Regresyon: metot dönüş tipi kendi tipi olunca döngü oluşuyordu.
        self.esit('''struct Sayac<T> {
  deger: T
  fn ayni() -> Sayac<T> = Sayac<T> { deger: self.deger }
}
fn main() { print(Sayac { deger: 5 }.ayni().ayni().deger) }''', "5")

    # --- hatalar ---
    def test_eksik_tip_argumani_yazimda(self):
        self.hatali('''struct Kutu<T> { deger: T }
fn main() { let k: Kutu = Kutu { deger: 1 }
 print(k.deger) }''', "tip argümanı bekler")

    def test_fazla_tip_argumani(self):
        self.hatali('''struct Kutu<T> { deger: T }
fn main() { let k: Kutu<Int, String> = Kutu<Int> { deger: 1 }
 print(k.deger) }''', "tip argümanı bekler")

    def test_cikarilamayan_tip(self):
        self.hatali('''enum Kutu<T> { Dolu(T)  Bos }
fn main() { let k = Kutu.Bos
 print(k) }''', "çıkarılamıyor")

    def test_yanlis_tipte_alan(self):
        self.hatali('''struct Kutu<T> { deger: T  ikinci: T }
fn main() { let k = Kutu { deger: 1, ikinci: "metin" }
 print(k.deger) }''', "bulundu")

    def test_generic_olmayana_tip_argumani(self):
        self.hatali('''struct Kutu { deger: Int }
fn main() { let k: Kutu<Int> = Kutu { deger: 1 }
 print(k.deger) }''', "tip argümanı almaz")

    def test_farkli_uygulamalar_uyusmaz(self):
        self.hatali('''struct Kutu<T> { deger: T }
fn al(k: Kutu<Int>) -> Int = k.deger
fn main() { print(al(Kutu { deger: "metin" })) }''', "bulundu")


if __name__ == "__main__":
    unittest.main(verbosity=2)

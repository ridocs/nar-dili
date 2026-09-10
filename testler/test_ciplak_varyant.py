"""Enum adı yazılmadan kullanılan varyantlar: `Metin("a")`, `Cizgi`.

Kural şu: varyant adı yalnızca tek bir enum'da geçiyorsa enum adı gereksizdir.
Birden çok enum aynı adı taşıyorsa, beklenen tip hangisi olduğunu söylemiyorsa
karar programcınındır ve derleyici hata verir.
"""

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


class CiplakVaryantHatalari(unittest.TestCase):
    def hatali(self, src: str, parca: str):
        with self.assertRaises(NarError) as ctx:
            derle(src)
        mesajlar = [h.message for h in getattr(ctx.exception, "errors", [ctx.exception])]
        self.assertTrue(
            any(parca in m for m in mesajlar),
            f"beklenen ipucu bulunamadı: {parca}\nalınan: {mesajlar}",
        )

    def test_iki_enumda_ayni_ad_belirsiz(self):
        self.hatali('''enum A { Bos  Dolu(Int) }
enum B { Bos  Yarim(Int) }
fn main() {
  let x = Bos
  print(x)
}''', "birden çok enum'da var")

    def test_belirsiz_ad_cagrida_da_yakalanir(self):
        self.hatali('''enum A { Deger(Int) }
enum B { Deger(String) }
fn main() {
  let x = Deger(1)
  print(x)
}''', "birden çok enum'da var")

    def test_olmayan_varyant_hala_tanimsiz(self):
        self.hatali('''enum Renk { Kirmizi  Yesil }
fn main() { print(Mavi) }''', "tanımsız isim")


@unittest.skipIf(NODE is None, "node bulunamadı")
class CiplakVaryantTesti(unittest.TestCase):
    def esit(self, src: str, beklenen: str):
        self.assertEqual(calistir(src), beklenen.strip())

    def test_yuksuz_varyant(self):
        self.esit('''enum Renk { Kirmizi  Yesil  Mavi }
fn main() {
  let r = Yesil
  print(r)
}''', "Renk.Yesil")

    def test_yuklu_varyant(self):
        self.esit('''enum Sekil { Daire(Float)  Kare(Float) }
fn alan(s: Sekil) -> Float = match s {
  Daire(r) -> 3.14159 * r * r
  Kare(k) -> k * k
}
fn main() {
  print(alan(Daire(2.0)))
  print(alan(Kare(3.0)))
}''', "12.56636\n9.0")

    def test_listede_karisik_varyantlar(self):
        self.esit('''enum Adim { Basla  Yaz(String)  Bitir }
fn main() {
  let adimlar = [Basla, Yaz("merhaba"), Bitir]
  for a in adimlar {
    match a {
      Basla -> print("başladı")
      Yaz(m) -> print("yazdı: " + m)
      Bitir -> print("bitti")
    }
  }
}''', "başladı\nyazdı: merhaba\nbitti")

    def test_nitelenmis_ad_hala_calisir(self):
        self.esit('''enum Renk { Kirmizi  Yesil }
fn main() {
  print(Renk.Kirmizi)
  print(Kirmizi)
}''', "Renk.Kirmizi\nRenk.Kirmizi")

    def test_ayni_ad_beklenen_tiple_cozulur(self):
        # `Bos` iki enum'da var; ama beklenen tip hangisi olduğunu söylüyor.
        self.esit('''enum A { Bos  Dolu(Int) }
enum B { Bos  Yarim(Int) }
fn ala(x: A) -> String = match x {
  A.Bos -> "A boş"
  A.Dolu(n) -> "A ${n}"
}
fn main() {
  let a: A = Bos
  print(ala(a))
}''', "A boş")

    def test_yerel_degisken_varyanti_golgeler(self):
        # Kapsamdaki bir ad, varyant adından önce gelir.
        self.esit('''enum Renk { Kirmizi  Yesil }
fn main() {
  let Yesil = 42
  print(Yesil)
}''', "42")

    def test_fonksiyon_adi_varyanti_golgeler(self):
        self.esit('''enum Islem { Topla(Int, Int) }
fn Topla(a: Int, b: Int) -> Int = a + b
fn main() { print(Topla(2, 3)) }''', "5")

    def test_generic_enum_ciplak(self):
        self.esit('''enum Kutu<T> { Dolu(T)  Bos }
fn main() {
  let k: Kutu<Int> = Dolu(7)
  match k {
    Dolu(n) -> print(n)
    Bos -> print("boş")
  }
}''', "7")

    def test_ic_ice_varyant(self):
        self.esit('''enum Agac { Yaprak(Int)  Dal(Agac, Agac) }
fn topla(a: Agac) -> Int = match a {
  Yaprak(n) -> n
  Dal(sol, sag) -> topla(sol) + topla(sag)
}
fn main() {
  print(topla(Dal(Yaprak(1), Dal(Yaprak(2), Yaprak(3)))))
}''', "6")


if __name__ == "__main__":
    unittest.main()

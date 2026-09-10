"""Arayüz (interface) testleri: ortak davranış tanımı ve generic sınırlama."""

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

ARAYUZLER = '''interface Yazdirilabilir {
  fn yaz() -> String
}

interface Olculebilir {
  fn olcu() -> Float
}

struct Nokta: Yazdirilabilir, Olculebilir {
  x: Float
  y: Float
  fn yaz() -> String = "(${self.x}, ${self.y})"
  fn olcu() -> Float = sqrt(self.x * self.x + self.y * self.y)
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

'''


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
class ArayuzTesti(unittest.TestCase):
    def esit(self, govde: str, beklenen: str):
        self.assertEqual(calistir(ARAYUZLER + govde), beklenen.strip())

    def hatali(self, src: str, parca: str):
        with self.assertRaises(NarError) as ctx:
            derle(src)
        mesajlar = [h.message for h in getattr(ctx.exception, "errors", [ctx.exception])]
        self.assertTrue(
            any(parca in m for m in mesajlar),
            f"beklenen ipucu bulunamadı: {parca}\nalınan: {mesajlar}",
        )

    def test_arayuz_tipinde_parametre(self):
        self.esit('''fn goster(y: Yazdirilabilir) { print(y.yaz()) }
fn main() {
  goster(Nokta { x: 1.0, y: 2.0 })
  goster(Kisi { ad: "Ayşe" })
}''', "(1.0, 2.0)\nkişi: Ayşe")

    def test_enum_arayuz_ustlenir(self):
        self.esit('''fn goster(y: Yazdirilabilir) { print(y.yaz()) }
fn main() { goster(Durum.Acik)
 goster(Durum.Kapali) }''', "açık\nkapalı")

    def test_bir_tip_birden_cok_arayuz(self):
        self.esit('''fn goster(y: Yazdirilabilir) { print(y.yaz()) }
fn olc(o: Olculebilir) { print(o.olcu()) }
fn main() {
  let n = Nokta { x: 3.0, y: 4.0 }
  goster(n)
  olc(n)
}''', "(3.0, 4.0)\n5.0")

    def test_arayuz_listesinde_farkli_tipler(self):
        self.esit('''fn main() {
  let hepsi: [Yazdirilabilir] = [Nokta { x: 0.0, y: 0.0 }, Kisi { ad: "c" }, Durum.Kapali]
  for e in hepsi { print(e.yaz()) }
}''', "(0.0, 0.0)\nkişi: c\nkapalı")

    def test_generic_sinirlama(self):
        self.esit('''fn hepsiniGoster<T: Yazdirilabilir>(liste: [T]) {
  for e in liste { print("- " + e.yaz()) }
}
fn main() { hepsiniGoster([Kisi { ad: "a" }, Kisi { ad: "b" }]) }''',
                  "- kişi: a\n- kişi: b")

    def test_generic_sinirlama_hesap(self):
        self.esit('''fn enBuyuk<T: Olculebilir>(liste: [T]) -> Float {
  var en = 0.0
  for e in liste {
    if e.olcu() > en { en = e.olcu() }
  }
  return en
}
fn main() {
  print(enBuyuk([Nokta { x: 3.0, y: 4.0 }, Nokta { x: 6.0, y: 8.0 }]))
}''', "10.0")

    def test_arayuz_donus_tipi(self):
        self.esit('''fn yap(sayi: Bool) -> Yazdirilabilir {
  if sayi { return Nokta { x: 1.0, y: 1.0 } }
  return Kisi { ad: "x" }
}
fn main() { print(yap(true).yaz())
 print(yap(false).yaz()) }''', "(1.0, 1.0)\nkişi: x")

    # --- hatalar ---
    def test_eksik_metot(self):
        self.hatali('''interface Y { fn yaz() -> String }
struct X: Y { a: Int }
fn main() { print(X { a: 1 }.a) }''', "metodu yok")

    def test_imza_uyusmazligi(self):
        self.hatali('''interface Y { fn yaz() -> String }
struct X: Y {
  a: Int
  fn yaz() -> Int = 1
}
fn main() { print(X { a: 1 }.a) }''', "imzası arayüzle uyuşmuyor")

    def test_ustlenmeyen_tip_gecmez(self):
        self.hatali('''interface Y { fn yaz() -> String }
struct X { a: Int }
fn goster(y: Y) { print(y.yaz()) }
fn main() { goster(X { a: 1 }) }''', "bulundu")

    def test_sinirsiz_tip_parametresinde_metot_yok(self):
        self.hatali('''fn f<T>(x: T) { print(x.yaz()) }
fn main() { }''', "tip parametresinde 'yaz' yok")

    def test_bilinmeyen_arayuz(self):
        self.hatali('''struct X: Olmayan { a: Int }
fn main() { print(X { a: 1 }.a) }''', "bilinmeyen arayüz")

    def test_arayuzde_olmayan_metot(self):
        self.hatali('''interface Y { fn yaz() -> String }
struct X: Y {
  a: Int
  fn yaz() -> String = "x"
}
fn goster(y: Y) { print(y.baskaMetot()) }
fn main() { goster(X { a: 1 }) }''', "arayüzünde 'baskaMetot' yok")

    def test_arayuz_metodu_govde_alamaz(self):
        with self.assertRaises(NarError) as ctx:
            derle('''interface Y { fn yaz() -> String { return "x" } }
fn main() { }''')
        self.assertIn("gövde alamaz", ctx.exception.message)

    def test_bos_arayuz(self):
        with self.assertRaises(NarError) as ctx:
            derle("interface Y { }\nfn main() { }")
        self.assertIn("en az bir metot", ctx.exception.message)


if __name__ == "__main__":
    unittest.main(verbosity=2)

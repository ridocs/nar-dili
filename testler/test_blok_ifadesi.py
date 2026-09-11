"""`if` ve `match` ifadelerinin dallarında blok gövdesi.

Önce bir dal yalnızca tek ifade olabiliyordu; birkaç adım gerekiyorsa o dalı
ayrı bir işleve çıkarmak gerekiyordu. Artık blok yazılabilir ve bloğun son
deyimi dalın değeridir.

Sınırlar da burada korunuyor: son satır bir değer olmalı, eşleme literali
hâlâ eşleme literali sayılmalı, tek ifadelik dal aynı ağacı üretmeli.
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

from narc import nar_ast as A  # noqa: E402
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


class BlokIfadesiHatalari(unittest.TestCase):
    def hatali(self, src: str, parca: str):
        with self.assertRaises(NarError) as ctx:
            derle(src)
        mesajlar = [h.message for h in getattr(ctx.exception, "errors", [ctx.exception])]
        self.assertTrue(
            any(parca in m for m in mesajlar),
            f"beklenen ipucu bulunamadı: {parca}\nalınan: {mesajlar}",
        )

    def test_son_satir_deger_olmali(self):
        self.hatali('''fn f(n: Int) -> Int = if n > 0 {
  var x = 1
  x = 2
} else {
  0
}
fn main() { print(f(1)) }''', "son satırı bir değer olmalı")

    def test_bos_dal(self):
        self.hatali('''fn f(n: Int) -> Int = if n > 0 {
} else {
  0
}
fn main() { print(f(1)) }''', "değer üretmeli")

    def test_dallarin_tipleri_uyusmali(self):
        self.hatali('''fn f(n: Int) -> Int = if n > 0 {
  let a = 1
  a
} else {
  "metin"
}
fn main() { print(f(1)) }''', "uyuşmuyor")


@unittest.skipIf(NODE is None, "node bulunamadı")
class BlokIfadesiTesti(unittest.TestCase):
    def esit(self, src: str, beklenen: str):
        self.assertEqual(calistir(src), beklenen.strip())

    def test_match_kolunda_blok(self):
        self.esit('''enum Hava { Gunesli  Yagmurlu }

fn oneri(h: Hava) -> String = match h {
  Gunesli -> "şapka al"
  Yagmurlu -> {
    let arac = "şemsiye"
    let sebep = "yağmur"
    "${arac} al (${sebep})"
  }
}

fn main() {
  print(oneri(Gunesli))
  print(oneri(Yagmurlu))
}''', "şapka al\nşemsiye al (yağmur)")

    def test_if_kolunda_blok(self):
        self.esit('''fn sinif(n: Int) -> String = if n >= 90 {
  "A"
} else if n >= 80 {
  let fark = 90 - n
  "B (A'ya ${fark} puan)"
} else {
  let eksik = 80 - n
  "C (${eksik} puan eksik)"
}

fn main() {
  print(sinif(95))
  print(sinif(85))
  print(sinif(60))
}''', "A\nB (A'ya 5 puan)\nC (20 puan eksik)")

    def test_blok_icinde_dongu(self):
        self.esit('''fn toplam(n: Int) -> Int = if n <= 0 {
  0
} else {
  var t = 0
  for i in 1..=n {
    t += i
  }
  t
}

fn main() {
  print(toplam(5))
  print(toplam(0))
}''', "15\n0")

    def test_ic_ice_blok(self):
        self.esit('''fn f(n: Int) -> Int = if n > 0 {
  let a = if n > 10 {
    let b = n * 2
    b + 1
  } else {
    n
  }
  a * 10
} else {
  0
}

fn main() {
  print(f(20))
  print(f(5))
  print(f(-1))
}''', "410\n50\n0")

    def test_esleme_literali_bozulmadi(self):
        """`Bir -> {"a": 1}` blok değil, eşleme literalidir."""
        self.esit('''fn main() {
  let m = match 1 {
    1 -> {"a": 1, "b": 2}
    _ -> {"c": 3}
  }
  print(m["a"] ?? 0, m["b"] ?? 0)

  // Boş eşleme için tip yazılmalı; bu blok ifadesinden önce de böyleydi.
  let bos: {String: Int} = match 2 {
    1 -> {}
    _ -> {}
  }
  print(bos.len())
}''', "1 2\n0")

    def test_tek_ifadelik_dal_ayni_agaci_uretir(self):
        """Tek ifadelik dal sarmalanmamalı: ağaç eskisiyle aynı kalmalı."""
        modul = parse('fn f(n: Int) -> Int = if n > 0 { 1 } else { 2 }', "t.nar")
        fn = modul.items[0]
        govde = fn.body.stmts[0].value
        self.assertIsInstance(govde, A.IfExpr)
        self.assertIsInstance(govde.then, A.IntLit)
        self.assertIsInstance(govde.otherwise, A.IntLit)

    def test_cok_deyimli_dal_blok_uretir(self):
        modul = parse(
            'fn f(n: Int) -> Int = if n > 0 { let a = 1\n  a } else { 2 }', "t.nar")
        govde = modul.items[0].body.stmts[0].value
        self.assertIsInstance(govde.then, A.BlockExpr)
        self.assertEqual(len(govde.then.block.stmts), 2)

    def test_blokta_erken_donus(self):
        """`return` içeren bir dal da geçerlidir; o dal geri dönmez."""
        self.esit('''fn f(n: Int) -> String {
  let s = if n > 0 {
    "artı"
  } else {
    return "sıfır ya da eksi"
  }
  return s
}

fn main() {
  print(f(1))
  print(f(-1))
}''', "artı\nsıfır ya da eksi")


if __name__ == "__main__":
    unittest.main()

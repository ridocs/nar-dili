"""Tuple: çoklu dönüş, öğe erişimi ve açma.

Her program iki arka uçta da çalıştırılıyor; tuple JavaScript'te de
bytecode VM'inde de dizi olarak saklandığı için ikisi aynı sonucu
vermeli.
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

from narc.checker import Checker  # noqa: E402
from narc.diagnostics import NarError  # noqa: E402
from narc.parser import parse  # noqa: E402

NODE = shutil.which("node")


def calistir(kaynak: str, motor: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        yol = Path(tmp) / "t.nar"
        yol.write_text(kaynak, encoding="utf-8")
        sonuc = subprocess.run(
            [sys.executable, "-m", "narc", motor, str(yol)],
            cwd=str(KOK), capture_output=True, text=True, encoding="utf-8",
        )
    if sonuc.returncode != 0:
        raise AssertionError(sonuc.stderr or sonuc.stdout)
    return sonuc.stdout.strip()


def hatalar(kaynak: str) -> str:
    try:
        modul = parse(kaynak, "t.nar")
        Checker(modul, kaynak).check()
    except NarError as e:
        hepsi = getattr(e, "errors", None) or [e]
        return chr(10).join(h.message for h in hepsi)
    raise AssertionError("hata bekleniyordu, çıkmadı")


@unittest.skipIf(NODE is None, "node bulunamadı")
class TupleTesti(unittest.TestCase):
    def iki_motor(self, kaynak: str, beklenen: str):
        self.assertEqual(calistir(kaynak, "run"), beklenen, "JavaScript")
        self.assertEqual(calistir(kaynak, "calistir"), beklenen, "VM")

    def test_coklu_donus(self):
        """İki değer döndürmek için struct tanımlamak gerekmiyor."""
        self.iki_motor('''
fn bolVeKalan(a: Int, b: Int) -> (Int, Int) = (a / b, a % b)

fn main() {
  let s = bolVeKalan(17, 5)
  print(str(s.0) + " kalan " + str(s.1))
}
''', "3 kalan 2")

    def test_acma(self):
        self.iki_motor('''
fn bolVeKalan(a: Int, b: Int) -> (Int, Int) = (a / b, a % b)

fn main() {
  let (bolum, kalan) = bolVeKalan(17, 5)
  print(str(bolum) + " " + str(kalan))
}
''', "3 2")

    def test_degisebilir_acma(self):
        self.iki_motor('''
fn main() {
  var (x, y) = (1, 2)
  x += 10
  y = y * 3
  print(str(x) + "," + str(y))
}
''', "11,6")

    def test_karisik_tipler(self):
        self.iki_motor('''
fn main() {
  let t: (Int, String, Bool) = (1, "iki", true)
  print(str(t.0) + t.1 + str(t.2))
}
''', "1ikitrue")

    def test_ic_ice_ve_listede(self):
        self.iki_motor('''
fn main() {
  let cift = (1, ("a", true))
  print(str(cift.0) + cift.1.0 + str(cift.1.1))

  let liste: [(String, Int)] = [("a", 1), ("b", 2)]
  var toplam = 0
  for p in liste {
    toplam += p.1
  }
  print(str(toplam))
}
''', "1atrue\n3")

    def test_tuple_esitligi(self):
        self.iki_motor('''
fn main() {
  print(str((1, "a") == (1, "a")))
  print(str((1, "a") == (2, "a")))
}
''', "true\nfalse")


class TupleHataTesti(unittest.TestCase):
    def test_olmayan_oge(self):
        self.assertIn(
            "tuple'ın 2 öğesi var; .5 yok",
            hatalar('fn main() {\n  let t = (1, 2)\n  print(str(t.5))\n}'))

    def test_alan_adiyla_erisim(self):
        self.assertIn(
            "tuple'ın 'ad' diye bir alanı yok",
            hatalar('fn main() {\n  let t = (1, 2)\n  print(str(t.ad))\n}'))

    def test_acmada_sayi_uyusmali(self):
        self.assertIn(
            "2 öğeli tuple 3 ada açılamaz",
            hatalar('fn main() {\n  let (a, b, c) = (1, 2)\n'
                    '  print(str(a + b + c))\n}'))

    def test_tuple_olmayan_acilmaz(self):
        self.assertIn(
            "açılamaz",
            hatalar('fn main() {\n  let (a, b) = 5\n  print(str(a + b))\n}'))

    def test_tip_uyusmazligi(self):
        self.assertIn(
            "bekleniyordu",
            hatalar('fn f() -> (Int, String) = (1, 2)\n'
                    'fn main() { print(f().1) }'))


if __name__ == "__main__":
    unittest.main()

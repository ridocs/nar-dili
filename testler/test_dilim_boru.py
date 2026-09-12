"""Dilimleme `a[1..3]`, yayma `[...a, b]` ve boru `x |> f`.

Üçü de iki arka uçta birden sınanıyor.
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
class DilimTesti(unittest.TestCase):
    def iki_motor(self, kaynak: str, beklenen: str):
        self.assertEqual(calistir(kaynak, "run"), beklenen, "JavaScript")
        self.assertEqual(calistir(kaynak, "calistir"), beklenen, "VM")

    def test_liste_dilimi(self):
        self.iki_motor('''
fn main() {
  let a = [1, 2, 3, 4, 5]
  print(a[1..3])
  print(a[1..=3])
  print(a[0..0])
  print(a[3..99])
  print(a[4..2])
}
''', "[2, 3]\n[2, 3, 4]\n[]\n[4, 5]\n[]")

    def test_metin_dilimi(self):
        """Kod noktalarına göre: Türkçe harfler bölünmez."""
        self.iki_motor('''
fn main() {
  print("merhaba"[0..3])
  print("merhaba"[3..=5])
  print("çğüöşı"[1..3])
}
''', "mer\nhab\nğü")

    def test_dilim_degiskenle(self):
        self.iki_motor('''
fn main() {
  let a = [10, 20, 30, 40]
  let b = 1
  print(a[b..(b + 2)])
}
''', "[20, 30]")

    def test_dilim_kaynagi_bozmaz(self):
        self.iki_motor('''
fn main() {
  let a = [1, 2, 3]
  let b = a[0..2]
  print(a)
  print(b)
}
''', "[1, 2, 3]\n[1, 2]")


@unittest.skipIf(NODE is None, "node bulunamadı")
class YaymaTesti(unittest.TestCase):
    def iki_motor(self, kaynak: str, beklenen: str):
        self.assertEqual(calistir(kaynak, "run"), beklenen, "JavaScript")
        self.assertEqual(calistir(kaynak, "calistir"), beklenen, "VM")

    def test_yayma(self):
        self.iki_motor('''
fn main() {
  let a = [1, 2]
  let b = [5, 6]
  print([...a, 3, ...b])
  print([...a])
  print([0, ...a, ...b, 9])
}
''', "[1, 2, 3, 5, 6]\n[1, 2]\n[0, 1, 2, 5, 6, 9]")

    def test_yayma_kaynagi_bozmaz(self):
        self.iki_motor('''
fn main() {
  let a = [1, 2]
  let b = [...a, 3]
  print(a)
  print(b)
}
''', "[1, 2]\n[1, 2, 3]")


@unittest.skipIf(NODE is None, "node bulunamadı")
class BoruTesti(unittest.TestCase):
    def iki_motor(self, kaynak: str, beklenen: str):
        self.assertEqual(calistir(kaynak, "run"), beklenen, "JavaScript")
        self.assertEqual(calistir(kaynak, "calistir"), beklenen, "VM")

    def test_boru(self):
        """`x |> f(a)` -> `f(x, a)`; zincir soldan sağa okunur."""
        self.iki_motor('''
fn iki(n: Int) -> Int = n * 2
fn ekle(n: Int, k: Int) -> Int = n + k

fn main() {
  print(5 |> iki)
  print(5 |> iki |> iki)
  print(5 |> ekle(3))
  print(3 + 2 |> iki)
}
''', "10\n20\n8\n10")

    def test_boru_gercek_kullanim(self):
        """İç içe çağrı yerine soldan sağa okunan zincir."""
        self.iki_motor('''
fn temizle(s: String) -> String = s.trim()
fn buyut(s: String) -> String = s.upperTr()
fn sar(s: String, k: String) -> String = k + s + k

fn main() {
  print("  merhaba  " |> temizle |> buyut |> sar("*"))
  print(sar(buyut(temizle("  merhaba  ")), "*"))
}
''', "*MERHABA*\n*MERHABA*")


class DilimHataTesti(unittest.TestCase):
    def test_dilim_siniri_int_olmali(self):
        self.assertIn(
            "dilim sınırı 'Int' olmalı",
            hatalar('fn main() {\n  let a = [1, 2]\n  print(a["x".."y"])\n}'))

    def test_dilimlenemeyen_tip(self):
        self.assertIn(
            "dilimlenemez",
            hatalar('fn main() {\n  let m = {"a": 1}\n  print(m[0..1])\n}'))

    def test_yayilamayan_deger(self):
        self.assertIn(
            "yayılamaz",
            hatalar('fn main() {\n  print([...5, 1])\n}'))


if __name__ == "__main__":
    unittest.main()

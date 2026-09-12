"""Koşullu match kolu (`desen if koşul ->`) ve aralık deseni (`1..=9 ->`).

Her program iki arka uçta da çalıştırılıyor: JavaScript ve bytecode VM'i
aynı sonucu vermeli.
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
class MatchTesti(unittest.TestCase):
    def iki_motor(self, kaynak: str, beklenen: str):
        self.assertEqual(calistir(kaynak, "run"), beklenen, "JavaScript")
        self.assertEqual(calistir(kaynak, "calistir"), beklenen, "VM")

    def test_kosullu_kol_ve_aralik(self):
        """Bir if-else zincirinin yerini tutan tek bir match."""
        self.iki_motor('''
fn siniflandir(n: Int) -> String = match n {
  x if x < 0 -> "eksi"
  0 -> "sıfır"
  1..=9 -> "tek haneli"
  10..=99 -> "iki haneli"
  _ -> "büyük"
}

fn main() {
  for n in [-3, 0, 5, 42, 1000] {
    print(siniflandir(n))
  }
}
''', "eksi\nsıfır\ntek haneli\niki haneli\nbüyük")

    def test_kosul_desenin_bagladigi_adi_gorur(self):
        self.iki_motor('''
enum Kutu {
  Dolu(Int)
  Bos
}

fn anlat(k: Kutu) -> String = match k {
  Dolu(n) if n > 100 -> "çok: " + str(n)
  Dolu(n) -> "az: " + str(n)
  Bos -> "boş"
}

fn main() {
  print(anlat(Kutu.Dolu(5)))
  print(anlat(Kutu.Dolu(500)))
  print(anlat(Kutu.Bos))
}
''', "az: 5\nçok: 500\nboş")

    def test_yarim_acik_aralik(self):
        """`..` üst sınırı dışarıda bırakır, `..=` içine alır."""
        self.iki_motor('''
fn f(n: Int) -> String = match n {
  0..3 -> "a"
  3..=5 -> "b"
  _ -> "c"
}

fn main() {
  print(f(0) + f(2) + f(3) + f(5) + f(6))
}
''', "aabbc")

    def test_metin_araligi(self):
        self.iki_motor('''
fn harf(s: String) -> String = match s {
  "a"..="m" -> "ilk yarı"
  _ -> "ikinci yarı"
}

fn main() {
  print(harf("b"))
  print(harf("z"))
}
''', "ilk yarı\nikinci yarı")

    def test_deyim_matchinde_kosul(self):
        self.iki_motor('''
fn main() {
  for n in [1, 8, 15] {
    match n {
      x if x % 2 == 0 -> print(str(x) + " çift")
      1..=9 -> print(str(n) + " küçük tek")
      _ -> print(str(n) + " öteki")
    }
  }
}
''', "1 küçük tek\n8 çift\n15 öteki")


class MatchHataTesti(unittest.TestCase):
    def test_kosullu_kol_matchi_tamamlamaz(self):
        """`x if ...` her değeri tutmaz; tek başına match'i kapatamaz."""
        self.assertIn(
            "her durumu kapsamalı",
            hatalar('fn f(n: Int) -> String = match n {\n'
                    '  x if x > 0 -> "arti"\n}\n'
                    'fn main() { print(f(1)) }'))

    def test_kosul_bool_olmali(self):
        self.assertIn(
            "kol koşulu 'Bool' olmalı",
            hatalar('fn f(n: Int) -> String = match n {\n'
                    '  x if x -> "a"\n  _ -> "b"\n}\n'
                    'fn main() { print(f(1)) }'))

    def test_aralik_ucu_ayni_tipte_olmali(self):
        self.assertIn(
            "aralık ucunun tipi",
            hatalar('fn f(n: Int) -> String = match n {\n'
                    '  1..="x" -> "a"\n  _ -> "b"\n}\n'
                    'fn main() { print(f(1)) }'))

    def test_enum_varyanti_aralik_olamaz(self):
        """Aralık yalnız sabitlerden kurulur; varyant adı desen sonu demektir."""
        self.assertIn(
            "desenden sonra '->' bekleniyordu",
            hatalar('enum R { A\n  B }\n'
                    'fn f(r: R) -> String = match r {\n'
                    '  A..=B -> "a"\n  _ -> "b"\n}\n'
                    'fn main() { print(f(R.A)) }'))

    def test_siralanamayan_tip_aralik_olamaz(self):
        self.assertIn(
            "aralık deseninde kullanılamaz",
            hatalar('fn f(b: Bool) -> String = match b {\n'
                    '  true..=false -> "a"\n  _ -> "b"\n}\n'
                    'fn main() { print(f(true)) }'))


if __name__ == "__main__":
    unittest.main()

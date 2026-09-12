"""Koleksiyon ve metin kolaylıkları: sirala, duzlestir, eslestir, ters,
solaDoldur, sagaDoldur.

Hepsi iki arka uçta birden sınanıyor.
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


@unittest.skipIf(NODE is None, "node bulunamadı")
class KolaylikTesti(unittest.TestCase):
    def iki_motor(self, kaynak: str, beklenen: str):
        self.assertEqual(calistir(kaynak, "run"), beklenen, "JavaScript")
        self.assertEqual(calistir(kaynak, "calistir"), beklenen, "VM")

    def test_sirala_kendi_olcutunle(self):
        """Elle döngü yazmadan, karşılaştırıcıyla sıralama."""
        self.iki_motor('''
fn main() {
  print([3, 1, 2].sirala(|a, b| a - b))
  print([3, 1, 2].sirala(|a, b| b - a))
  let kelimeler = ["elma", "at", "kiraz"]
  print(kelimeler.sirala(|a, b| a.len() - b.len()))
}
''', "[1, 2, 3]\n[3, 2, 1]\n[\"at\", \"elma\", \"kiraz\"]")

    def test_sirala_kaynagi_bozmaz(self):
        self.iki_motor('''
fn main() {
  let a = [3, 1, 2]
  let b = a.sirala(|x, y| x - y)
  print(a)
  print(b)
}
''', "[3, 1, 2]\n[1, 2, 3]")

    def test_duzlestir(self):
        self.iki_motor('''
fn main() {
  print([[1, 2], [3], [4, 5]].duzlestir())
  print([[1], []].duzlestir())
}
''', "[1, 2, 3, 4, 5]\n[1]")

    def test_eslestir(self):
        """Kısa olan bitince durur; çiftin ilk öğesi tipini korur."""
        self.iki_motor('''
fn main() {
  let ciftler = [1, 2, 3].eslestir(["a", "b"])
  print(ciftler.len())
  for c in ciftler {
    print(c.0)
  }
}
''', "2\n1\n2")

    def test_ters_liste_ve_metin(self):
        self.iki_motor('''
fn main() {
  print([1, 2, 3].ters())
  print("merhaba".ters())
  print("çğüöşı".ters())
}
''', "[3, 2, 1]\nabahrem\nışöüğç")

    def test_doldurma(self):
        """Sabit genişlik: tablo ve saat biçimleri için."""
        self.iki_motor('''
fn main() {
  print("7".solaDoldur(3, "0"))
  print("ad".sagaDoldur(5, "."))
  print("uzun".solaDoldur(2, "0"))
  print("x".solaDoldur(4, "ab"))
}
''', "007\nad...\nuzun\nabax")

    def test_gercek_kullanim_saat_bicimi(self):
        self.iki_motor('''
fn saat(s: Int, d: Int) -> String =
  str(s).solaDoldur(2, "0") + ":" + str(d).solaDoldur(2, "0")

fn main() {
  print(saat(9, 5))
  print(saat(14, 30))
}
''', "09:05\n14:30")


if __name__ == "__main__":
    unittest.main()

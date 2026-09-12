"""Varsayılan parametre, adlandırılmış argüman ve struct alan varsayılanı.

Aynı programlar iki arka uçta da (JavaScript ve Nar bytecode VM'i)
çalıştırılıyor: çağrıyı denetleyici normalleştirdiği için ikisinin de
aynı sonucu vermesi gerekir.
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


def calistir(kaynak: str, motor: str = "run") -> str:
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


def hata_ver(kaynak: str) -> str:
    """Denetleyicinin bütün hata mesajları; hata yoksa testi düşürür.

    Tek bir yanlış birden çok hata doğurabilir (bilinmeyen argüman adı,
    ardından eksik kalan zorunlu argüman gibi); hepsi birlikte döner.
    """
    try:
        modul = parse(kaynak, "t.nar")
        Checker(modul, kaynak).check()
    except NarError as e:
        hepsi = getattr(e, "errors", None) or [e]
        return chr(10).join(h.message for h in hepsi)
    raise AssertionError("hata bekleniyordu, çıkmadı")


@unittest.skipIf(NODE is None, "node bulunamadı")
class VarsayilanTesti(unittest.TestCase):
    def iki_motor(self, kaynak: str, beklenen: str):
        """Aynı program JavaScript ve VM'de aynı çıktıyı vermeli."""
        self.assertEqual(calistir(kaynak, "run"), beklenen, "JavaScript")
        self.assertEqual(calistir(kaynak, "calistir"), beklenen, "VM")

    def test_varsayilan_parametre(self):
        self.iki_motor('''
fn selam(ad: String, ek: String = "!") -> String = ad + ek

fn main() {
  print(selam("a"))
  print(selam("b", "?"))
}
''', "a!\nb?")

    def test_adlandirilmis_argüman_sirayi_degistirir(self):
        self.iki_motor('''
fn bicim(metin: String, once: String = "[", sonra: String = "]") -> String =
  once + metin + sonra

fn main() {
  print(bicim("x"))
  print(bicim("x", sonra: ">"))
  print(bicim(sonra: ">", once: "<", metin: "x"))
}
''', "[x]\n[x>\n<x>")

    def test_struct_alan_varsayilani(self):
        self.iki_motor('''
struct Ayar {
  var ad: String
  var derinlik: Int = 3
  var acik: Bool = true
}

fn main() {
  let a = Ayar { ad: "ilk" }
  print(a.ad + str(a.derinlik) + str(a.acik))
  let b = Ayar { ad: "iki", acik: false }
  print(b.ad + str(b.derinlik) + str(b.acik))
}
''', "ilk3true\niki3false")

    def test_metot_ve_enum_metodu(self):
        self.iki_motor('''
struct Kutu {
  var n: Int

  fn yaz(ek: String = "") -> String = str(self.n) + ek
}

enum Renk {
  Mavi

  fn ad(buyuk: Bool = false) -> String {
    let s = match self { Mavi -> "mavi" }
    return if buyuk { s.upperTr() } else { s }
  }
}

fn main() {
  let k = Kutu { n: 2 }
  print(k.yaz())
  print(k.yaz(ek: "!"))
  print(Renk.Mavi.ad(buyuk: true))
}
''', "2\n2!\nMAVİ")

    def test_varsayilan_her_cagrida_degerlendirilir(self):
        """Varsayılan bir ifade olabilir; çağrı anındaki değeri kullanılır."""
        self.iki_motor('''
var sayac = 0

fn artir() -> Int {
  sayac += 1
  return sayac
}

fn f(n: Int = artir()) -> Int = n

fn main() {
  print(str(f()))
  print(str(f()))
  print(str(f(100)))
  print(str(f()))
}
''', "1\n2\n100\n3")


class VarsayilanHataTesti(unittest.TestCase):
    def test_varsayilansiz_parametre_sonra_gelemez(self):
        self.assertIn(
            "varsayılanı olan parametrelerden sonra gelemez",
            hata_ver('fn f(a: Int = 1, b: Int) -> Int = a\nfn main() { print(str(f())) }'))

    def test_bilinmeyen_argüman_adi(self):
        self.assertIn(
            "'yok' adında bir parametre yok",
            hata_ver('fn f(a: Int) -> Int = a\nfn main() { print(str(f(yok: 1))) }'))

    def test_ayni_argüman_iki_kez(self):
        self.assertIn(
            "iki kez verildi",
            hata_ver('fn f(a: Int, b: Int = 2) -> Int = a\n'
                     'fn main() { print(str(f(1, a: 3))) }'))

    def test_zorunlu_argüman_verilmedi(self):
        self.assertIn(
            "'a' argümanı verilmedi",
            hata_ver('fn f(a: Int, b: Int = 2) -> Int = a\n'
                     'fn main() { print(str(f(b: 1))) }'))

    def test_varsayilan_tipi_denetlenir(self):
        self.assertIn(
            "argüman tipi uyuşmuyor",
            hata_ver('fn f(a: Int = 1) -> Int = a\n'
                     'fn main() { print(str(f("x"))) }'))

    def test_struct_varsayilansiz_alan_zorunlu(self):
        self.assertIn(
            "eksik alanlar: b",
            hata_ver('struct S { var a: Int = 1\n  var b: Int }\n'
                     'fn main() { let s = S { }\n  print(str(s.b)) }'))


if __name__ == "__main__":
    unittest.main()

"""Kod biçimlendirici testleri.

Biçimlendiricinin kendisi Nar diliyle yazılmıştır
(`araclar/bicimlendirici.nar`); bu testler onu Node üzerinden çalıştırır.
"""

from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from narc.bicim import bicimlendir  # noqa: E402
from narc.checker import Checker  # noqa: E402
from narc.parser import parse  # noqa: E402

NODE = shutil.which("node")


@unittest.skipIf(NODE is None, "node bulunamadı")
class BicimlendiriciTesti(unittest.TestCase):
    def esit(self, girdi: str, beklenen: str):
        self.assertEqual(bicimlendir(girdi), beklenen)

    def test_girinti_duzeltilir(self):
        self.esit(
            'fn main() {\nprint("a")\n}\n',
            'fn main() {\n  print("a")\n}\n',
        )

    def test_fazla_girinti_geri_alinir(self):
        self.esit(
            'fn main() {\n        print("a")\n}\n',
            'fn main() {\n  print("a")\n}\n',
        )

    def test_ic_ice_bloklar(self):
        self.esit(
            'fn main() {\nif true {\nprint("a")\n}\n}\n',
            'fn main() {\n  if true {\n    print("a")\n  }\n}\n',
        )

    def test_else_ayni_seviyede(self):
        sonuc = bicimlendir('fn main() {\nif true {\nprint("a")\n} else {\nprint("b")\n}\n}\n')
        satirlar = sonuc.splitlines()
        self.assertIn("  } else {", satirlar)

    def test_lambda_iceren_cagri_tek_seviye(self):
        # Regresyon: `f("x", || {` satırı hem ( hem { açar; girinti yine
        # tek seviye artmalı.
        sonuc = bicimlendir(
            'fn main() {\nkayit("t", || {\nprint("ic")\n})\n}\n'
            'fn kayit(a: String, f: () -> Void) { f() }\n'
        )
        self.assertIn('  kayit("t", || {', sonuc)
        self.assertIn('    print("ic")', sonuc)
        self.assertIn("  })", sonuc)

    def test_ic_ice_liste(self):
        sonuc = bicimlendir("fn main() {\nlet a = [[\n1\n]]\n}\n")
        self.assertIn("  let a = [[", sonuc)
        self.assertIn("    1", sonuc)
        self.assertIn("  ]]", sonuc)

    def test_satir_sonu_bosluklari_atilir(self):
        self.esit('fn main() {\n  print("a")   \n}\n', 'fn main() {\n  print("a")\n}\n')

    def test_ardisik_bos_satirlar_teke_iner(self):
        sonuc = bicimlendir('fn main() {\n  let a = 1\n\n\n\n  let b = 2\n}\n')
        self.assertNotIn("\n\n\n", sonuc)
        self.assertIn("\n\n", sonuc)

    def test_metin_icindeki_parantez_sayilmaz(self):
        # "{" bir metin içindeyse girinti seviyesini etkilememeli
        sonuc = bicimlendir('fn main() {\nprint("{")\nprint("bitti")\n}\n')
        self.assertIn('  print("{")', sonuc)
        self.assertIn('  print("bitti")', sonuc)

    def test_yorumdaki_parantez_sayilmaz(self):
        sonuc = bicimlendir('fn main() {\n// burada bir { var\nprint("a")\n}\n')
        self.assertIn('  print("a")', sonuc)

    def test_kararli(self):
        # İki kez biçimlendirmek aynı sonucu vermeli
        girdi = 'fn main() {\n   if true {\nprint("a")\n     }\n}\n'
        bir = bicimlendir(girdi)
        iki = bicimlendir(bir)
        self.assertEqual(bir, iki)

    def test_bicimlendirilmis_kod_hala_derleniyor(self):
        girdi = ('fn main() {\nlet l = [1, 2]\nfor e in l {\nprint(e)\n}\n}\n')
        sonuc = bicimlendir(girdi)
        module = parse(sonuc, "t.nar")
        Checker(module, sonuc).check()  # hata fırlatmamalı

    def test_proje_dosyalari_duzenli(self):
        """Kendi Nar dosyalarımız biçimlendiriciyle uyumlu olmalı."""
        dosyalar = sorted((KOK / "araclar").glob("*.nar")) + \
                   sorted((KOK / "ornekler").glob("*.nar")) + \
                   [KOK / "deneme.nar"]
        for yol in dosyalar:
            with self.subTest(dosya=yol.name):
                kaynak = yol.read_text(encoding="utf-8-sig")
                self.assertEqual(
                    bicimlendir(kaynak), kaynak,
                    f"{yol.name} biçimlendiriciye göre düzensiz",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)

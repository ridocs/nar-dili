"""Nar diliyle yazılmış testleri çalıştırır.

`testler/nar/*.nar` altındaki her dosya kendi doğrulamalarını yapar ve
başarılıysa "geçti" yazıp 0 ile çıkar. Bu, dilin kendi kendini test
edebildiğini gösterir: kütüphane de test de Nar ile yazılmıştır.
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

from narc.driver import compile_file  # noqa: E402

NAR_TESTLERI = Path(__file__).resolve().parent / "nar"
NODE = shutil.which("node")

# Kendi başına çalışmayan yardımcılar: `main` içermezler, başka testlerden
# içe aktarılırlar.
KUTUPHANELER = {"tip_ornekleri.nar"}


@unittest.skipIf(NODE is None, "node bulunamadı")
class NarTestleri(unittest.TestCase):
    def test_nar_ile_yazilmis_testler_geciyor(self):
        dosyalar = [d for d in sorted(NAR_TESTLERI.glob("*.nar"))
                    if d.name not in KUTUPHANELER]
        self.assertGreater(len(dosyalar), 0, "hiç Nar testi bulunamadı")

        for yol in dosyalar:
            with self.subTest(test=yol.name):
                kod = compile_file(yol).to_js()
                with tempfile.TemporaryDirectory() as tmp:
                    betik = Path(tmp) / "test.js"
                    betik.write_text(kod, encoding="utf-8")
                    sonuc = subprocess.run(
                        [NODE, str(betik)], capture_output=True, text=True,
                        encoding="utf-8", timeout=60,
                    )
                cikti = (sonuc.stdout + sonuc.stderr).strip()
                self.assertEqual(
                    sonuc.returncode, 0,
                    f"{yol.name} başarısız:\n{cikti}",
                )
                self.assertIn("geçti", cikti, f"{yol.name} beklenen çıktıyı vermedi:\n{cikti}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

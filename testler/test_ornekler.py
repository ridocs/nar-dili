"""`ornekler/` altındaki her programın derlenip hatasız çalıştığını doğrular.

Örnekler belgelendirme olduğu kadar regresyon testidir: dilde bir şey bozulursa
buradan görülür.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from narc.driver import compile_file, to_html  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
ORNEKLER = KOK / "ornekler"
NODE = shutil.which("node")

# İçe aktarılmak için yazılmış, kendi başına `main` içermeyen modüller.
MODULLER = {"metin_araclari.nar"}

# Sunucu örnekleri istek beklemek üzere ayakta kalır; "çalıştır ve çıkışını
# oku" biçiminde sınanamazlar. Doğrulukları `testler/test_sunucu.py` içinde
# gerçek isteklerle denetleniyor; burada yalnızca derlendikleri görülür.
SUNUCULAR = {"not_sunucusu.nar"}


def ornek_dosyalari() -> list[Path]:
    # `.narbuild/` gibi dizinler de `*.nar` desenine uyabilir; dosya olanı al.
    return sorted(
        p for p in ORNEKLER.glob("*.nar")
        if p.is_file() and p.name not in MODULLER
    )


@unittest.skipIf(NODE is None, "node bulunamadı")
class OrneklerTesti(unittest.TestCase):
    def test_hepsi_derleniyor_ve_calisiyor(self):
        dosyalar = ornek_dosyalari()
        self.assertGreater(len(dosyalar), 0, "hiç örnek bulunamadı")

        for yol in dosyalar:
            with self.subTest(ornek=yol.name):
                derleme = compile_file(yol)
                kod = derleme.to_js()

                if yol.name in SUNUCULAR:
                    continue  # derlendi; çalıştırmak sonsuza kadar sürerdi

                with tempfile.TemporaryDirectory() as tmp:
                    betik = Path(tmp) / "program.js"
                    betik.write_text(kod, encoding="utf-8")
                    sonuc = subprocess.run(
                        [NODE, str(betik)], capture_output=True, text=True,
                        encoding="utf-8",
                    )

                self.assertEqual(
                    sonuc.returncode, 0,
                    f"{yol.name} hata verdi:\n{sonuc.stderr}",
                )
                self.assertNotIn("panik:", sonuc.stderr)
                self.assertTrue(sonuc.stdout.strip(), f"{yol.name} çıktı üretmedi")

    def test_web_hedefi_uretiliyor(self):
        derleme = compile_file(ORNEKLER / "merhaba.nar")
        html = to_html(derleme, "merhaba")
        self.assertIn("<!doctype html>", html)
        self.assertIn('lang="tr"', html)
        self.assertIn('charset="utf-8"', html)
        self.assertIn("$bootstrap(main);", html)

    def test_modul_tek_basina_main_istiyor(self):
        from narc.diagnostics import NarError
        with self.assertRaises(NarError) as ctx:
            compile_file(ORNEKLER / "metin_araclari.nar")
        self.assertIn("main", ctx.exception.message)

    def test_dongusel_ice_aktarma_yakalaniyor(self):
        from narc.diagnostics import NarError
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.nar"
            b = Path(tmp) / "b.nar"
            a.write_text('import "b.nar"\nfn main() { print("a") }\n', encoding="utf-8")
            b.write_text('import "a.nar"\nfn yardim() { }\n', encoding="utf-8")
            with self.assertRaises(NarError) as ctx:
                compile_file(a)
            self.assertIn("döngüsel", ctx.exception.message)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""`nar build --target masaustu` paketleme testleri.

Pencerenin gerçekten açılması ekran gerektirir; burada üretilen paketin
eksiksiz ve çalıştırılabilir olduğu doğrulanır.
"""

from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from narc.driver import compile_file  # noqa: E402
from narc.masaustu_paket import paketle  # noqa: E402


class MasaustuPaketTesti(unittest.TestCase):
    def paketle_ornek(self, tmp: str) -> Path:
        derleme = compile_file(KOK / "ornekler" / "sayac_web.nar")
        hedef = Path(tmp) / "uygulama"
        paketle(derleme.to_js(), hedef, "Sayaç", "sayac_web.nar")
        return hedef

    def test_paket_dosyalari_olusuyor(self):
        with tempfile.TemporaryDirectory() as tmp:
            hedef = self.paketle_ornek(tmp)
            for ad in ("index.html", "baslat.py", "baslat.cmd", "BENIOKU.md"):
                with self.subTest(dosya=ad):
                    self.assertTrue((hedef / ad).exists(), f"{ad} üretilmedi")

    def test_html_programi_iceriyor(self):
        with tempfile.TemporaryDirectory() as tmp:
            hedef = self.paketle_ornek(tmp)
            html = (hedef / "index.html").read_text(encoding="utf-8")
            self.assertIn("<!doctype html>", html)
            self.assertIn('lang="tr"', html)
            self.assertIn('id="uygulama"', html)
            self.assertIn("$bootstrap(main);", html)

    def test_baslatici_gecerli_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            hedef = self.paketle_ornek(tmp)
            kaynak = (hedef / "baslat.py").read_text(encoding="utf-8")
            ast.parse(kaynak)  # sözdizimi hatası varsa burada patlar
            self.assertIn("webview", kaynak)
            self.assertIn("--app=", kaynak)

    def test_cmd_saf_ascii_ve_crlf(self):
        # cmd.exe dosyayı OEM kod sayfasında okur; Türkçe karakter satırı bozar.
        with tempfile.TemporaryDirectory() as tmp:
            hedef = self.paketle_ornek(tmp)
            ham = (hedef / "baslat.cmd").read_bytes()
            ham.decode("ascii")  # ASCII değilse patlar
            self.assertIn(b"\r\n", ham)
            # Yalnız başına LF olmamalı: her satır sonu CRLF olmalı
            self.assertEqual(ham.count(b"\n"), ham.count(b"\r\n"))

    def test_benioku_calistirma_yolunu_anlatiyor(self):
        with tempfile.TemporaryDirectory() as tmp:
            hedef = self.paketle_ornek(tmp)
            metin = (hedef / "BENIOKU.md").read_text(encoding="utf-8")
            self.assertIn("baslat.cmd", metin)
            self.assertIn("baslat.py", metin)


if __name__ == "__main__":
    unittest.main(verbosity=2)

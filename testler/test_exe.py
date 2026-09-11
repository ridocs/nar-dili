"""`--target exe` — tek başına çalışan Windows uygulaması.

Kuyruk biçimi saf Python'la sınanır. Başlatıcının derlenmesi ve exe'nin
paketi gerçekten çıkarması `csc.exe` olan Windows makinelerde sınanır;
pencere açılmaz, başlatıcının `--cikar` modu kullanılır.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from narc import exe_paket  # noqa: E402
from narc.checker import Checker  # noqa: E402
from narc.backends import js as js_backend  # noqa: E402
from narc.parser import parse  # noqa: E402

CSC = exe_paket.csc_bul()

PROGRAM = 'fn main() {\n  print("merhaba")\n}\n'


def derle(kaynak: str) -> str:
    modul = parse(kaynak, "t.nar")
    denetci = Checker(modul, kaynak)
    denetci.check()
    return js_backend.generate(modul, denetci)


class KuyrukTesti(unittest.TestCase):
    def test_paket_gidip_geliyor(self):
        """Başlatıcı + paket + kuyruk; paket bayt bayt geri alınmalı."""
        with tempfile.TemporaryDirectory() as tmp:
            baslatici = Path(tmp) / "b.exe"
            baslatici.write_bytes(b"MZ-sahte-baslatici" * 20)
            paket = b"PK\x03\x04 sahte zip icerigi"
            exe = exe_paket.exe_yaz(baslatici, paket, Path(tmp) / "u.exe")
            veri = exe.read_bytes()
            self.assertTrue(veri.startswith(baslatici.read_bytes()))
            self.assertEqual(exe_paket.paket_ayir(veri), paket)

    def test_kuyruksuz_dosyada_paket_yok(self):
        self.assertIsNone(exe_paket.paket_ayir(b"MZ" * 100))
        self.assertIsNone(exe_paket.paket_ayir(b""))


@unittest.skipIf(CSC is None, "csc.exe yok (Windows .NET Framework gerekir)")
class BaslaticiTesti(unittest.TestCase):
    def test_exe_paketi_cikarir(self):
        """Üretilen exe kendi paketini bulup index.html'i çıkarmalı."""
        with tempfile.TemporaryDirectory() as tmp:
            exe = exe_paket.paketle(derle(PROGRAM), Path(tmp) / "u", "u", "u.nar")
            self.assertTrue(exe.exists())
            hedef = Path(tmp) / "cikti"
            sonuc = subprocess.run([str(exe), "--cikar", str(hedef)],
                                   capture_output=True, text=True, timeout=60)
            self.assertEqual(sonuc.returncode, 0, sonuc.stderr)
            self.assertTrue((hedef / "index.html").exists())
            self.assertTrue((hedef / "program.js").exists())
            self.assertIn("merhaba", (hedef / "program.js").read_text(encoding="utf-8"))
            self.assertIn("index.html", sonuc.stdout)

    def test_baslatici_ghb_dosyasini_acar(self):
        """Paketsiz başlatıcı, argüman olarak verilen .ghb'yi açmalı."""
        from narc.ghb_paket import paketle as ghb_paketle
        with tempfile.TemporaryDirectory() as tmp:
            ghb = ghb_paketle(derle(PROGRAM), Path(tmp) / "u", "u", "u.nar")
            baslatici = exe_paket.baslatici_derle()
            hedef = Path(tmp) / "cikti"
            sonuc = subprocess.run([str(baslatici), str(ghb), "--cikar", str(hedef)],
                                   capture_output=True, text=True, timeout=60)
            self.assertEqual(sonuc.returncode, 0, sonuc.stderr)
            self.assertTrue((hedef / "index.html").exists())

    def test_paketsiz_baslatici_sessiz_modda_hata_verir(self):
        """Pencere açmadan, konsola hata yazıp 1 ile çıkmalı."""
        with tempfile.TemporaryDirectory() as tmp:
            baslatici = exe_paket.baslatici_derle()
            sonuc = subprocess.run([str(baslatici), "--cikar", tmp],
                                   capture_output=True, text=True, timeout=60)
            self.assertEqual(sonuc.returncode, 1)
            self.assertIn("hata", sonuc.stderr)


if __name__ == "__main__":
    unittest.main()

"""`komutCalistir` yerleşiği ve `nar api` köprüsü.

İkisi birlikte Nar ile yazılmış sunucunun derleyiciye ulaşma yolunu
oluşturuyor; biri bozulursa IDE sessizce çalışmaz hâle gelir.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from narc.driver import compile_file  # noqa: E402

NODE = shutil.which("node")


def calistir(kaynak: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        nar = Path(tmp) / "program.nar"
        nar.write_text(kaynak, encoding="utf-8")
        betik = Path(tmp) / "program.js"
        betik.write_text(compile_file(nar).to_js(), encoding="utf-8")
        sonuc = subprocess.run(
            [NODE, str(betik)], capture_output=True, text=True, encoding="utf-8",
        )
    return (sonuc.stdout + sonuc.stderr).strip()


@unittest.skipIf(NODE is None, "node bulunamadı")
class KomutCalistirTesti(unittest.TestCase):
    def test_cikti_ve_cikis_kodu(self):
        """Çalışan programın çıktısı, çıkış kodu ve hata akışı ayrı ayrı gelir."""
        self.assertEqual(calistir('''
fn main() {
  let s = komutCalistir("node", ["-e", "console.log('selam')"])
  print(str(s.cikis()) + "|" + s.cikti().trim() + "|" + s.hata().trim())
}
'''), "0|selam|")

    def test_hata_akisi_ve_kod(self):
        self.assertEqual(calistir('''
fn main() {
  let s = komutCalistir("node", ["-e", "process.stderr.write('olmadi'); process.exit(3)"])
  print(str(s.cikis()) + "|" + s.hata())
}
'''), "3|olmadi")

    def test_bulunmayan_program(self):
        """Olmayan program panik atmaz; çıkış -1 ve hata mesajı döner."""
        cikti = calistir('''
fn main() {
  let s = komutCalistir("boyle-bir-program-yok-12345", [])
  print(str(s.cikis() != 0))
}
''')
        self.assertEqual(cikti, "true")

    def test_argumanlar_kabuktan_gecmiyor(self):
        """Kabuk açılmadığı için boşluklu argüman tek parça kalır."""
        self.assertEqual(calistir('''
fn main() {
  let s = komutCalistir("node", ["-e", "console.log(process.argv[1])", "iki kelime"])
  print(s.cikti().trim())
}
'''), "iki kelime")


class ApiKoprusuTesti(unittest.TestCase):
    """`nar api` — Nar sunucusunun derleyiciye ulaştığı komut."""

    def api(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "narc", "api", *args],
            cwd=str(KOK), capture_output=True, text=True, encoding="utf-8",
        )

    def test_denetle_uyari_dondurur(self):
        with tempfile.TemporaryDirectory() as tmp:
            yol = Path(tmp) / "t.nar"
            yol.write_text("fn main() {\n  let a = 1\n}\n", encoding="utf-8")
            sonuc = self.api("denetle", str(yol))
        self.assertEqual(sonuc.returncode, 0, sonuc.stderr)
        veri = json.loads(sonuc.stdout)
        self.assertIsNone(veri["hata"])
        self.assertEqual(len(veri["uyarilar"]), 1)
        self.assertIn("kullanılmamış", veri["uyarilar"][0]["mesaj"])

    def test_denetle_hatayi_dondurur(self):
        with tempfile.TemporaryDirectory() as tmp:
            yol = Path(tmp) / "t.nar"
            yol.write_text("fn main() {\n  print(yok)\n}\n", encoding="utf-8")
            sonuc = self.api("denetle", str(yol))
        veri = json.loads(sonuc.stdout)
        self.assertIsNotNone(veri["hata"])
        self.assertIn("tanımsız isim", veri["hata"]["mesaj"])
        self.assertEqual(veri["hata"]["satir"], 2)

    def test_uret_javascript_verir(self):
        with tempfile.TemporaryDirectory() as tmp:
            yol = Path(tmp) / "t.nar"
            yol.write_text('fn main() {\n  print("x")\n}\n', encoding="utf-8")
            sonuc = self.api("uret", str(yol))
        veri = json.loads(sonuc.stdout)
        self.assertIsNone(veri["hata"])
        self.assertIn("console.log", veri["kod"])

    def test_kelimeler(self):
        sonuc = self.api("kelimeler")
        veri = json.loads(sonuc.stdout)
        adlar = {k["ad"] for k in veri["kelimeler"]}
        self.assertIn("fn", adlar)
        self.assertIn("print", adlar)
        self.assertIn("komutCalistir", adlar)


class NarSunucusuTesti(unittest.TestCase):
    def test_derleniyor(self):
        """Nar ile yazılmış IDE sunucusu tip denetiminden geçer."""
        kaynak = KOK / "araclar" / "ide_sunucusu.nar"
        self.assertTrue(kaynak.exists(), "araclar/ide_sunucusu.nar bulunamadı")
        kod = compile_file(kaynak).to_js()
        # Sunucu, dosya ve süreç yerleşiklerini gerçekten kullanıyor olmalı.
        for beklenen in ("$sunucu", "$dosyaOku", "$komutCalistir"):
            self.assertIn(beklenen, kod)


if __name__ == "__main__":
    unittest.main()

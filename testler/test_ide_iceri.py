"""Düzenleyicide içe aktarma çözümü.

Düzenleyici kaydedilmemiş tamponu derletir; içe aktarmaların o tamponun
*gerçek* konumuna göre çözülmesi gerekir. Çözülmezse kütüphanedeki her ad
"tanımsız isim" diye görünür — bir dosya 18 uydurma hata üretir ve
düzeltme önerileri de saçmalar ("Kart" için "nar" önerilir).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from narc import ide_api  # noqa: E402

# Kütüphanedeki adları kullanan, ama kendisi kütüphane olmayan bir tampon.
TAMPON = '''import "../araclar/arayuz.nar"

fn ciz(n: Int) -> Gorunum = Yigin([
  Gezinti("Nar", ["Ürün"], n, |i| { }, Bos),
  Kahraman("", "Başlık", "", [Dugme("Git", || { })]),
  AltBilgi(["Nar"], [[Bag("Belge", "#")]], "© 2026")
])

fn main() {
  uygulamaBaslat("#uygulama", 0, ciz)
}
'''


class IceriAktarmaTesti(unittest.TestCase):
    def test_yol_verilince_kutuphane_adlari_tanimli(self):
        kod, hata = ide_api.derle(TAMPON, yol=KOK / "ornekler" / "deneme.nar")
        self.assertIsNone(hata, hata)
        self.assertIsNotNone(kod)

    def test_yol_verilmezse_tek_ve_acik_hata(self):
        kod, hata = ide_api.derle(TAMPON)
        self.assertIsNone(kod)
        # Kütüphanedeki her ad için bir tane değil, içe aktarma için bir tane.
        self.assertEqual(hata["adet"], 1)
        self.assertIn("içe aktarma çözülemedi", hata["mesaj"])
        self.assertIn("kaydet", hata["ipucu"])

    def test_yanlis_yol_dosyayi_soyler(self):
        # `import "araclar/..."` kökten yazılmış; ornekler/ içinden bulunmaz.
        kaynak = TAMPON.replace("../araclar/", "araclar/")
        _, hata = ide_api.derle(kaynak, yol=KOK / "ornekler" / "deneme.nar")
        self.assertIsNotNone(hata)
        self.assertEqual(hata["adet"], 1)
        self.assertIn("dosya bulunamadı", hata["mesaj"])
        # Kütüphanedeki adlar hakkında uydurma hata üretilmemeli.
        self.assertNotIn("tanımsız isim", hata["gosterim"])

    def test_komut_taban_yolunu_kullanir(self):
        """`nar api denetle <geçici> <gerçek>` — Nar ile yazılmış sunucunun yolu."""
        with tempfile.TemporaryDirectory() as tmp:
            gecici = Path(tmp) / "tampon.nar"
            gecici.write_text(TAMPON, encoding="utf-8")

            # Taban verilmezse geçici klasörde aranır, bulunamaz.
            self.assertIn("dosya bulunamadı", self._api(gecici, None)["hata"]["mesaj"])

            # Taban verilince çözülür.
            self.assertIsNone(self._api(gecici, KOK / "ornekler" / "deneme.nar")["hata"])

    def _api(self, dosya: Path, taban: Path | None) -> dict:
        argv = [sys.executable, "-m", "narc", "api", "denetle", str(dosya)]
        if taban is not None:
            argv.append(str(taban))
        sonuc = subprocess.run(argv, cwd=KOK, capture_output=True, text=True,
                               encoding="utf-8")
        self.assertEqual(sonuc.returncode, 0, sonuc.stderr)
        return json.loads(sonuc.stdout)


if __name__ == "__main__":
    unittest.main()

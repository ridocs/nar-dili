"""`araclar/tarih.nar` — tarih aritmetiği.

Doğruluk Python'ın `datetime` modülüyle karşılaştırılarak sınanıyor:
elle yazılmış beklenen değerler aynı hatayı iki kez yapmaya açıktır.
"""

from __future__ import annotations

import datetime
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
TARIH_NAR = KOK / "araclar" / "tarih.nar"


def calistir(govde: str) -> list[str]:
    """`main` gövdesini tarih.nar ile derler, Node ile çalıştırır."""
    with tempfile.TemporaryDirectory() as tmp:
        kaynak = Path(tmp) / "program.nar"
        kaynak.write_text(
            f'import "{TARIH_NAR.as_posix()}"\n\nfn main() {{\n{govde}\n}}\n',
            encoding="utf-8",
        )
        betik = Path(tmp) / "program.js"
        betik.write_text(compile_file(kaynak).to_js(), encoding="utf-8")
        sonuc = subprocess.run(
            [NODE, str(betik)], capture_output=True, text=True, encoding="utf-8",
        )
    if sonuc.returncode != 0:
        raise AssertionError(sonuc.stderr)
    return sonuc.stdout.strip().split("\n")


@unittest.skipIf(NODE is None, "node bulunamadı")
class TarihTesti(unittest.TestCase):
    def test_ay_gun_sayisi_datetime_ile_ayni(self):
        """2020-2030 arası her ayın gün sayısı; artık yıllar dahil."""
        satirlar = calistir('''
  var y = 2020
  while y <= 2030 {
    var a = 1
    while a <= 12 {
      print(str(ayGunSayisi(y, a)))
      a += 1
    }
    y += 1
  }
''')
        beklenen = []
        for y in range(2020, 2031):
            for a in range(1, 13):
                sonraki = datetime.date(y + a // 12, a % 12 + 1, 1)
                beklenen.append(str((sonraki - datetime.date(y, a, 1)).days))
        self.assertEqual(satirlar, beklenen)

    def test_haftanin_gunu_datetime_ile_ayni(self):
        """Pazartesi 0 olacak şekilde; `datetime.weekday()` ile birebir."""
        tarihler = [(2026, 9, 12), (2026, 1, 1), (2024, 2, 29), (2000, 1, 1),
                    (1999, 12, 31), (2030, 6, 15), (2026, 12, 31), (2100, 3, 1)]
        govde = "\n".join(
            f"  print(str(haftaninGunu({y}, {a}, {g})))" for y, a, g in tarihler)
        satirlar = calistir(govde)
        beklenen = [str(datetime.date(y, a, g).weekday()) for y, a, g in tarihler]
        self.assertEqual(satirlar, beklenen)

    def test_gece_sayisi(self):
        """Aradaki gün farkı; sıra ters verilse de pozitif."""
        satirlar = calistir('''
  print(str(geceSayisi(tarih(2026, 9, 12), tarih(2026, 9, 15))))
  print(str(geceSayisi(tarih(2026, 9, 15), tarih(2026, 9, 12))))
  print(str(geceSayisi(tarih(2026, 12, 28), tarih(2027, 1, 4))))
  print(str(geceSayisi(tarih(2024, 2, 27), tarih(2024, 3, 1))))
  print(str(geceSayisi(0, tarih(2026, 1, 1))))
''')
        self.assertEqual(satirlar, ["3", "3", "7", "3", "0"])

    def test_gun_ekle_ay_ve_yil_donuyor(self):
        satirlar = calistir('''
  print(isoTarih(gunEkle(tarih(2026, 12, 30), 5)))
  print(isoTarih(gunEkle(tarih(2026, 1, 2), -5)))
  print(isoTarih(gunEkle(tarih(2024, 2, 28), 1)))
  print(isoTarih(gunEkle(tarih(2026, 2, 28), 1)))
  print(isoTarih(gunEkle(tarih(2026, 3, 15), 0)))
  print(isoTarih(gunEkle(tarih(2026, 1, 31), 365)))
''')
        beklenen = []
        for baslangic, adet in [((2026, 12, 30), 5), ((2026, 1, 2), -5),
                                ((2024, 2, 28), 1), ((2026, 2, 28), 1),
                                ((2026, 3, 15), 0), ((2026, 1, 31), 365)]:
            d = datetime.date(*baslangic) + datetime.timedelta(days=adet)
            beklenen.append(d.isoformat())
        self.assertEqual(satirlar, beklenen)

    def test_artik_yil(self):
        satirlar = calistir('''
  print(str(artikYilMi(2024)))
  print(str(artikYilMi(2026)))
  print(str(artikYilMi(1900)))
  print(str(artikYilMi(2000)))
''')
        self.assertEqual(satirlar, ["true", "false", "false", "true"])

    def test_yaziya_dokme(self):
        satirlar = calistir('''
  print(tarihMetni(tarih(2026, 9, 12)))
  print(kisaTarihMetni(tarih(2026, 9, 12)))
  print(isoTarih(tarih(2026, 9, 5)))
  print("[" + tarihMetni(0) + "]")
''')
        self.assertEqual(satirlar,
                         ["12 Eylül 2026", "12 Eyl", "2026-09-05", "[]"])

    def test_tarih_parcalari(self):
        satirlar = calistir('''
  let t = tarih(2026, 9, 12)
  print(str(t))
  print(str(tarihYil(t)) + "|" + str(tarihAy(t)) + "|" + str(tarihGun(t)))
  // Sayı olarak sıralanabilir olmalı: karşılaştırma tarih sırasıdır.
  print(str(tarih(2026, 9, 12) < tarih(2026, 10, 1)))
  print(str(tarih(2026, 12, 31) < tarih(2027, 1, 1)))
''')
        self.assertEqual(satirlar, ["20260912", "2026|9|12", "true", "true"])


if __name__ == "__main__":
    unittest.main()

"""`ornekler/dil_turu.nar` — dilin her köşesi, iki arka uçta birden.

Bu tek dosya sayıları, metinleri, listeleri, eşlemeleri, opsiyonelleri,
akış deyimlerini, desenleri, tuple'ları, closure'ları ve yapıları
kullanır. JavaScript ile bytecode VM'inin çıktısı satır satır aynı
olmalı: ayrıldıkları yer bir hatadır.

Bu testin yakaladığı iki hata:
  - closure yakaladığı değişkene yazamıyordu (VM `0 0 0`, JS `1 2 3`)
  - lambda içindeki `self` VM'de bulunamıyordu
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

NODE = shutil.which("node")
TUR = KOK / "ornekler" / "dil_turu.nar"


def calistir(motor: str) -> list[str]:
    sonuc = subprocess.run(
        [sys.executable, "-m", "narc", motor, str(TUR)],
        cwd=str(KOK), capture_output=True, text=True, encoding="utf-8",
        timeout=180,
    )
    if sonuc.returncode != 0:
        raise AssertionError(f"{motor}: {sonuc.stderr or sonuc.stdout}")
    return [s.rstrip() for s in sonuc.stdout.strip().split("\n")]


@unittest.skipIf(NODE is None, "node bulunamadı")
class DilTuruTesti(unittest.TestCase):
    def test_iki_motor_ayni_ciktiyi_veriyor(self):
        js = calistir("run")
        vm = calistir("calistir")

        self.assertEqual(len(js), len(vm),
                         "satır sayısı farklı; bir motor erken durmuş olabilir")
        for no, (a, b) in enumerate(zip(js, vm), start=1):
            self.assertEqual(a, b, f"{no}. satır ayrılıyor")

    def test_tur_gercekten_her_bolumu_geziyor(self):
        """Tur kısalırsa test değerini kaybeder; başlıklar yerinde mi?"""
        js = calistir("run")
        for baslik in ("== sayılar ==", "== metinler ==", "== listeler ==",
                       "== eşlemeler ==", "== opsiyoneller ==", "== akış ==",
                       "== desenler ==", "== tuple ==", "== işlevler ==",
                       "== yapılar ==", "== bitti =="):
            self.assertIn(baslik, js)

    def test_closure_sayaci_artiyor(self):
        """Yakalanan değişkene yazma: hatanın ilk çıktığı yer."""
        js = calistir("run")
        self.assertIn("1 2 3", js)


if __name__ == "__main__":
    unittest.main()

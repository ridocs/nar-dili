"""IDE sunucusunun HTTP uçları.

`ide/sunucu.py` şimdiye kadar yalnızca elle denenmişti; içindeki bir
yazım hatası (`_son_uyarilar` diye tanımsız bir ad) `/api/denetle`
isteğini her seferinde düşürüyordu ve kimse fark etmemişti. Bir sunucunun
doğruluğu ancak istek atarak anlaşılır — bu dosya onu yapıyor.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent


def bos_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class IdeSunucusu:
    """Sunucuyu ayağa kaldırır; `with` bloğu bitince kapatır."""

    def __enter__(self):
        self.port = bos_port()
        self.surec = subprocess.Popen(
            [sys.executable, str(KOK / "ide" / "sunucu.py"),
             "--port", str(self.port), "--tarayici-acma"],
            cwd=KOK, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        son = time.time() + 20
        while time.time() < son:
            if self.surec.poll() is not None:
                _, hata = self.surec.communicate()
                raise AssertionError("sunucu açılmadı:\n"
                                     + hata.decode("utf-8", "replace"))
            try:
                with socket.create_connection(("127.0.0.1", self.port), 0.3):
                    return self
            except OSError:
                time.sleep(0.1)
        raise AssertionError("sunucu zamanında açılmadı")

    def __exit__(self, *_):
        self.surec.terminate()
        try:
            self.surec.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.surec.kill()

    def al(self, yol: str) -> dict:
        with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}{yol}", timeout=30) as y:
            return json.loads(y.read().decode("utf-8"))

    def gonder(self, uc: str, **govde) -> dict:
        veri = json.dumps(govde, ensure_ascii=False).encode("utf-8")
        istek = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{uc}", data=veri,
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(istek, timeout=30) as y:
            return json.loads(y.read().decode("utf-8"))


# Kütüphaneden ad kullanan bir tampon: içe aktarma çözülmezse buradaki
# her ad "tanımsız isim" olur.
TAMPON = '''import "../araclar/arayuz.nar"

fn ciz(n: Int) -> Gorunum = Yigin([
  Gezinti("Nar", ["Ürün"], n, |i| { }, Bos),
  Kahraman("", "Başlık", "", [Dugme("Git", || { })])
])

fn main() {
  uygulamaBaslat("#uygulama", 0, ciz)
}
'''


class IdeSunucusuTesti(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = IdeSunucusu()
        cls.s = cls.ctx.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.__exit__(None, None, None)

    def test_denetle_temiz_kaynakta_tamam_der(self):
        y = self.s.gonder("/api/denetle", kaynak="fn main() { print(1) }\n")
        self.assertTrue(y["tamam"], y)
        self.assertEqual(y["uyarilar"], [])

    def test_denetle_uyarilari_dondurur(self):
        y = self.s.gonder(
            "/api/denetle", kaynak="fn main() {\n  let a = 1\n  print(2)\n}\n")
        self.assertTrue(y["tamam"], y)
        self.assertEqual(len(y["uyarilar"]), 1)
        self.assertIn("kullanılmamış", y["uyarilar"][0]["mesaj"])

    def test_denetle_hatayi_bildirir(self):
        y = self.s.gonder("/api/denetle", kaynak="fn main() { print(yok) }\n")
        self.assertFalse(y["tamam"])
        self.assertIn("tanımsız", y["hata"]["mesaj"])

    def test_ice_aktarma_acik_dosyanin_yerine_gore_cozulur(self):
        y = self.s.gonder("/api/denetle", kaynak=TAMPON,
                          yol="ornekler/deneme.nar")
        self.assertTrue(y["tamam"], y.get("hata"))

    def test_yol_yanlissa_tek_hata_verilir(self):
        # Kökten yazılmış yol `ornekler/` içinden bulunmaz.
        y = self.s.gonder("/api/denetle",
                          kaynak=TAMPON.replace("../araclar/", "araclar/"),
                          yol="ornekler/deneme.nar")
        self.assertFalse(y["tamam"])
        self.assertEqual(y["hata"]["adet"], 1)
        self.assertIn("dosya bulunamadı", y["hata"]["mesaj"])

    def test_uretilen_javascript_gelir(self):
        y = self.s.gonder("/api/uretilen", kaynak="fn main() { print(1) }\n")
        self.assertIsNone(y["hata"])
        self.assertIn("console.log", y["kod"])

    def test_dosya_listesi_gruplanmis_gelir(self):
        y = self.s.al("/api/dosyalar")
        gruplar = {d["grup"] for d in y["dosyalar"]}
        self.assertIn("Örnekler", gruplar)
        self.assertIn("Araçlar", gruplar)

    def test_kok_disina_cikilamiyor(self):
        y = self.s.gonder("/api/denetle", kaynak="fn main() { print(1) }\n",
                          yol="../../gizli.nar")
        # Reddedilir ve köke düşülür; çökmez.
        self.assertTrue(y["tamam"], y)

    def test_taze_sunucu_kendini_eski_saymaz(self):
        y = self.s.gonder("/api/denetle", kaynak="fn main() { print(1) }\n")
        self.assertFalse(y["eskiSunucu"])


if __name__ == "__main__":
    unittest.main()

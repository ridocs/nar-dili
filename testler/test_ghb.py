"""`.ghb` — Nar uygulama paketi.

Paketin kendisi sınanır: içinde ne var, bozuk paketler nasıl karşılanıyor,
ZIP içinden klasör dışına yazmaya çalışan bir paket durduruluyor mu.

Pencere açmak ekran gerektirir; burada paketin eksiksiz ve açılabilir
olduğu doğrulanır.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from narc.driver import compile_file  # noqa: E402
from narc.ghb_paket import BICIM_SURUMU, ac, meta_oku, paketle  # noqa: E402

NODE = shutil.which("node")


def ornek_js() -> str:
    return compile_file(KOK / "ornekler" / "sayac_web.nar").to_js()


class GhbPaketTesti(unittest.TestCase):
    def paketle_ornek(self, tmp: str, **ek) -> Path:
        return paketle(ornek_js(), Path(tmp) / "uygulama", "Sayaç",
                       "sayac_web.nar", **ek)

    def test_tek_dosya_uretiliyor(self):
        with tempfile.TemporaryDirectory() as tmp:
            paket = self.paketle_ornek(tmp)
            self.assertTrue(paket.is_file())
            self.assertEqual(paket.suffix, ".ghb")

    def test_paket_icerigi(self):
        with tempfile.TemporaryDirectory() as tmp:
            paket = self.paketle_ornek(tmp)
            with zipfile.ZipFile(paket) as z:
                adlar = set(z.namelist())
            for gereken in ("nar.json", "program.js", "index.html"):
                with self.subTest(dosya=gereken):
                    self.assertIn(gereken, adlar)

    def test_meta_bilgisi(self):
        with tempfile.TemporaryDirectory() as tmp:
            paket = self.paketle_ornek(tmp, genislik=820, yukseklik=640)
            meta = meta_oku(paket)
            self.assertEqual(meta["ad"], "Sayaç")
            self.assertEqual(meta["bicim"], BICIM_SURUMU)
            self.assertEqual(meta["pencere"]["genislik"], 820)
            self.assertEqual(meta["pencere"]["yukseklik"], 640)

    def test_program_pakette_bozulmadan_duruyor(self):
        with tempfile.TemporaryDirectory() as tmp:
            paket = self.paketle_ornek(tmp)
            with zipfile.ZipFile(paket) as z:
                icerik = z.read("program.js").decode("utf-8")
            self.assertEqual(icerik, ornek_js())

    def test_varliklar_pakete_giriyor(self):
        with tempfile.TemporaryDirectory() as tmp:
            varlik = Path(tmp) / "varlik"
            (varlik / "alt").mkdir(parents=True)
            (varlik / "veri.json").write_text('{"a":1}', encoding="utf-8")
            (varlik / "alt" / "not.txt").write_text("merhaba", encoding="utf-8")

            paket = self.paketle_ornek(tmp, varliklar=varlik)
            with zipfile.ZipFile(paket) as z:
                adlar = set(z.namelist())
            self.assertIn("varliklar/veri.json", adlar)
            self.assertIn("varliklar/alt/not.txt", adlar)

    def test_paket_acilabiliyor(self):
        with tempfile.TemporaryDirectory() as tmp:
            paket = self.paketle_ornek(tmp)
            hedef = Path(tmp) / "acilan"
            giris = ac(paket, hedef)
            self.assertTrue(giris.exists())
            self.assertEqual(giris.name, "index.html")
            self.assertTrue((hedef / "program.js").exists())

    @unittest.skipIf(NODE is None, "node bulunamadı")
    def test_acilan_program_calisiyor(self):
        """Paketten çıkan JavaScript gerçekten çalışmalı."""
        with tempfile.TemporaryDirectory() as tmp:
            paket = self.paketle_ornek(tmp)
            hedef = Path(tmp) / "acilan"
            ac(paket, hedef)
            sonuc = subprocess.run(
                [NODE, str(hedef / "program.js")],
                capture_output=True, text=True, encoding="utf-8", timeout=60,
            )
            self.assertEqual(sonuc.returncode, 0, sonuc.stderr)

    # --- bozuk ve kötü niyetli paketler ----------------------------------

    def test_olmayan_paket(self):
        with self.assertRaises(FileNotFoundError):
            meta_oku(Path("olmayan-dosya.ghb"))

    def test_zip_olmayan_dosya(self):
        with tempfile.TemporaryDirectory() as tmp:
            sahte = Path(tmp) / "sahte.ghb"
            sahte.write_text("bu bir zip değil", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                meta_oku(sahte)
            self.assertIn("Nar paketi değil", str(ctx.exception))

    def test_nar_json_olmayan_paket(self):
        with tempfile.TemporaryDirectory() as tmp:
            eksik = Path(tmp) / "eksik.ghb"
            with zipfile.ZipFile(eksik, "w") as z:
                z.writestr("baska.txt", "içerik")
            with self.assertRaises(ValueError) as ctx:
                meta_oku(eksik)
            self.assertIn("nar.json", str(ctx.exception))

    def test_daha_yeni_bicim_reddediliyor(self):
        """İleriki bir sürümle üretilmiş paket anlaşılır biçimde reddedilmeli."""
        with tempfile.TemporaryDirectory() as tmp:
            yeni = Path(tmp) / "yeni.ghb"
            with zipfile.ZipFile(yeni, "w") as z:
                z.writestr("nar.json", json.dumps({"bicim": BICIM_SURUMU + 5}))
            with self.assertRaises(ValueError) as ctx:
                meta_oku(yeni)
            self.assertIn("daha yeni", str(ctx.exception))

    def test_klasor_disina_yazan_paket_durduruluyor(self):
        """ZIP içindeki yollar güvenilmez.

        `../` içeren bir girdi, açılırken hedef klasörün dışına yazabilir
        (Zip Slip). Bu engel olmadan bir paket sistemdeki dosyaları
        değiştirebilirdi.
        """
        with tempfile.TemporaryDirectory() as tmp:
            kotu = Path(tmp) / "kotu.ghb"
            with zipfile.ZipFile(kotu, "w") as z:
                z.writestr("nar.json", json.dumps({"bicim": 1, "ad": "kötü"}))
                z.writestr("../disari.txt", "burada olmamalı")

            with self.assertRaises(ValueError) as ctx:
                ac(kotu, Path(tmp) / "hedef")
            self.assertIn("güvenli olmayan", str(ctx.exception))
            self.assertFalse((Path(tmp) / "disari.txt").exists())


class UzantiKayitTesti(unittest.TestCase):
    """Dosya ilişkilendirme kayıtları.

    Kayıt gerçekten yazılmaz — testin sistemi değiştirmemesi gerekir.
    Burada komutun doğru kurulduğu ve Windows dışında düzgün
    reddedildiği denetlenir.
    """

    def test_baslatici_komutu(self):
        from narc import uzanti_kayit

        komut = uzanti_kayit.baslatici_komutu(KOK)
        self.assertIn("nar_ac.py", komut)
        self.assertIn('"%1"', komut, "dosya yolu komuta geçmiyor")
        # Boşluklu yollar için tırnak şart (kullanıcı adında boşluk olabilir).
        self.assertEqual(komut.count('"'), 6)

    def test_baslatici_betigi_var(self):
        from narc import uzanti_kayit

        self.assertTrue(uzanti_kayit.baslatici_betigi(KOK).exists())

    @unittest.skipIf(sys.platform == "win32", "yalnızca Windows dışı")
    def test_windows_disinda_reddediliyor(self):
        from narc import uzanti_kayit

        oldu, mesaj = uzanti_kayit.kur(KOK)
        self.assertFalse(oldu)
        self.assertIn("Windows", mesaj)


def simge_modulu():
    """`site/simge_uret.py`'yi yükler.

    Doğrudan `import site.simge_uret` olmaz: `site` Python'un kendi
    standart modülünün adı.
    """
    import importlib.util

    yol = KOK / "site" / "simge_uret.py"
    tarif = importlib.util.spec_from_file_location("nar_simge_uret", yol)
    modul = importlib.util.module_from_spec(tarif)
    tarif.loader.exec_module(modul)
    return modul


class SimgeTesti(unittest.TestCase):
    def test_ico_uretiliyor(self):
        m = simge_modulu()
        ico_yaz, png_yaz, pikselleri_uret = m.ico_yaz, m.png_yaz, m.pikselleri_uret

        veri = ico_yaz([16, 32])
        self.assertTrue(veri.startswith(b"\x00\x00\x01\x00"), "ICO başlığı yanlış")
        self.assertGreater(len(veri), 200)

        png = png_yaz(pikselleri_uret(16))
        self.assertTrue(png.startswith(b"\x89PNG\r\n\x1a\n"), "PNG başlığı yanlış")

    def test_depodaki_simge_gecerli(self):
        ico = KOK / "site" / "nar.ico"
        self.assertTrue(ico.exists(), "site/nar.ico üretilmemiş")
        self.assertTrue(ico.read_bytes().startswith(b"\x00\x00\x01\x00"))


if __name__ == "__main__":
    unittest.main()
